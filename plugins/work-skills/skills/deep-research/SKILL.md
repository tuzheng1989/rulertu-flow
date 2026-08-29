---
name: deep-research
description: 深度研究助手，通过迭代式"搜索-总结-反思"循环生成带引用的综合性研究报告。当用户说"深入研究XX"、"研究一下XX"、"调研XX"或明确表示需要全面了解某个主题时触发。支持配置循环次数（"循环N次"）与搜索区域（"中文/英文"或"us/cn"）。v0.4.0 新增意图澄清、研究简报驱动、多查询并行与摘要压缩。v0.5.0 引入多源搜索通道（deepxiv / sn-search-* 脚本 + MCP），按查询来源类型智能分派并支持通道降级。v0.6.0 新增自动落盘功能，报告完成后自动保存到文件系统。
version: 0.6.0
author: Claude Code
---

# deep-research

深度研究助手，基于 IterDRAG 方法论，通过多轮迭代循环生成结构化研究报告。

> **v0.4.0 主要变更**
> - **前置澄清**（clarify）：对宽泛主题反问 1 轮，明确范围/受众/深度
> - **研究简报**（brief）：生成贯穿全程的结构锚点，驱动 query 维度 / reflect 评分维度 / finalize 报告分段
> - **多查询并行**：query 节点输出 2-4 条查询，一条消息内并行搜索
> - **摘要压缩**（compress）：running_summary 超阈值时触发压缩，治理多轮膨胀
>
> **v0.4.1 调优（呈现层）**：分层治理"紧凑度"——**summary 仍保持精简**（去重防膨胀、防 reflect 维度退化），但 **finalize 负责重新展开**为舒展正文（每维度 3-5 句段落 + 表格 + 数据 + 引用 [n]，而非照搬 running_summary 的紧凑度）。同步把 summary 的"去重"语义从"精简"改为"**去重保细节**"——保留事例/量化/对比作为展开素材，只删冗余表述与过渡。**实测**（Fora 报告）：中文字数 ~2100 → ~3900（1.86×），无注水、无失真，舒展度显著提升。
>
> - **正文引用锚链化**：finalize 的 `[n]` 引用从裸文本改为指向文末来源的锚链 `[[n]](#ref-n)`——正文点击跳转到对应来源条目，来源条目再点跳原文；来源列表每条加 `<a id="ref-n">` 锚点。**实测**（Fora 报告）：94 处引用全部锚链化、24 个来源一一对应、0 残留裸标记。
>
> **v0.5.0 搜索层增强（多源化）**：移植 sn-deep-research 的搜索方法——三层搜索模型（广度发现→专项深挖→原始核验）+ 按查询来源类型（`source_type`）智能分派多通道 + 来源优先级 + 多源交叉验证。query 节点输出新增 `source_type` / `source_tier`；主控按 `source_type` 分派到 web(MCP) / academic(deepxiv) / code / social_cn / social_en 五通道；任一专门通道失败统一降级到 MCP web-search-prime。**不改** running_summary / 引用 [n] / finalize 链路。

## 触发条件

当用户说以下类似内容时触发此 skill：

- "帮我深入研究 **[主题]**"
- "研究一下 **[主题]**"
- "调研 **[主题]**"
- "全面分析 **[主题]**"
- "对 **[主题]** 做个研究报告"

**可选参数：**
- "循环 **N** 次" - 指定研究轮数（默认 3 次）
- "**中文/英文** 搜索" 或 "**us/cn**" - 指定搜索区域（默认按主题自动选择；英文技术资料偏 us，中文资料偏 cn）

---

## 执行流程

### 第 1 步：解析请求

从用户输入中提取：
- 研究主题 (`research_topic`)
- 最大循环次数 (`max_loops`，默认 3)
- 搜索区域 (`search_location`，默认按主题判断：英文技术资料用 `us`，中文资料用 `cn`；多区域可并行）

### 第 1.5 步：意图澄清（clarify）【v0.4.0 新增】

启动 **clarifier** subagent 判断主题是否需要澄清：

```yaml
使用 Task 工具启动 subagent:
  description: 判断研究主题是否需澄清
  subagent_type: general-purpose
  prompt: |
    按 agents/research-node-clarify.md 的定义执行。
    输入: research_topic、user_request
    输出: { need_clarification, reason, questions[] }
  返回结果保存到: clarify_result
```

**根据 clarify_result 处理：**

- 若 `need_clarification == false`：直接进入第 1.8 步
- 若 `need_clarification == true`：对每个 question 提问（**最多 1 轮**）
  - `use_ask_user_question == true`（选项可枚举 ≤4）：调用 **AskUserQuestion** 工具提问
  - `use_ask_user_question == false`（开放性问题）：直接文本提问
  - 收集用户回复，记入 `clarification_result`，进入第 1.8 步

> **载体适配**：Claude Code 会话中，澄清即"暂停流程、向用户提问、等回复"，比 LangGraph 的 goto=END 更自然。务必只问 1 轮。

### 第 1.8 步：生成研究简报（brief）【v0.4.0 新增】

启动 **brief-writer** subagent，产出贯穿全程的研究简报：

```yaml
使用 Task 工具启动 subagent:
  description: 生成研究简报
  subagent_type: general-purpose
  prompt: |
    按 agents/research-node-brief.md 的定义执行。
    输入: research_topic、clarification_result（若有）、user_request
    输出: research_brief（Markdown 文本，含范围/受众/深度/输出格式/必须覆盖的维度清单/排除项）
  返回结果保存到: research_brief
```

**research_brief 是后续所有阶段的锚点**：
- query 据其维度清单生成查询
- reflect 据其维度清单评分（替代硬编码 6 维度）
- finalize 据其输出格式与受众决定报告结构

### 第 2 步：初始化研究状态

创建 `ResearchState` 对象，包含：
- `research_topic`: 研究主题
- `research_brief`: 研究简报（第 1.8 步产出）
- `max_loops`: 最大循环次数
- `loop_count`: 当前循环次数（初始 0）
- `running_summary`: 累积摘要（初始空）
- `sources`: 来源列表（初始空）
- `knowledge_gaps`: 知识缺口（初始空）

### 第 3 步：研究循环

对 `loop_count` 从 1 到 `max_loops` 执行：

#### 3.1 生成搜索查询列表（多查询）【v0.4.0 改造】

启动 **query-generator** subagent：

```yaml
使用 Task 工具启动 subagent:
  description: 生成深度研究搜索查询 (第 {loop_count} 轮)
  subagent_type: general-purpose
  prompt: |
    按 agents/research-node-query.md 的定义执行。
    输入:
      - research_topic
      - research_brief（维度清单作为生成锚点）
      - running_summary（或"无"）
      - loop_count / max_loops
      - knowledge_gaps（后续轮）
    输出: { queries: [ {query, intent}, ... ] }
      - 首轮: 固定 3 条（核心概念/应用场景/最新进展）
      - 后续轮: 按 knowledge_gaps 逐个生成（上限 4 条）
  返回结果保存到: query_list
```

#### 3.2 执行搜索：按 source_type 分派多通道【v0.5.0 重写】

对 `query_list` 中的**每条 query**，按其 `source_type` 查「搜索通道映射表」选择通道，在**一条消息里放多个工具/Bash 调用**以实现并行。这是三层搜索模型在本步骤的落地：第 1 轮偏 `web` 广度发现，后续轮按 `source_type` 专项深挖。

**搜索通道映射表：**

| source_type | 通道 | 调用方式 |
|-------------|------|----------|
| `web` | MCP `web-search-prime` | MCP 工具 `mcp__web-search-prime__web_search_prime`（保留 v0.4 行为） |
| `academic` | deepxiv CLI | Bash：`PYTHONIOENCODING=utf-8 deepxiv search "{query}" --limit {N} --format json`（可选 `--mode hybrid` `--min-citations {n}` `--categories {cs.X}` `--date-from {YYYY-MM-DD}`） |
| `code` | sn-search-code 脚本 | Bash：`PYTHONIOENCODING=utf-8 python ../sn-search-code/scripts/{github\|stackoverflow\|hackernews\|huggingface}_search.py "{query}" --limit {N}` |
| `social_cn` | sn-search-social-cn 脚本 | Bash：`PYTHONIOENCODING=utf-8 python ../sn-search-social-cn/scripts/{zhihu\|bilibili\|douyin}_search.py "{query}" --limit {N}` |
| `social_en` | sn-search-social-en 脚本 | Bash：`PYTHONIOENCODING=utf-8 python ../sn-search-social-en/scripts/{twitter\|youtube}_search.py "{query}" --limit {N}`（reddit 已禁用，跳过） |

**子工具选择**（同一通道内多脚本时按 query 语义选最对口的）：
- `code`：仓库/模型/数据集→`github_search.py`/`huggingface_search.py`；技术问答→`stackoverflow_search.py`；技术讨论→`hackernews_search.py`
- `social_cn`：深度讨论→`zhihu_search.py`；视频→`bilibili_search.py`/`douyin_search.py`
- `social_en`：讨论→`twitter_search.py`；视频→`youtube_search.py`
- `academic`：默认 `deepxiv search`；已有 arxiv_id 想读全文→走 3.2b 的 `deepxiv paper`

**统一调用约定：**
- 所有 Bash 命令加 `PYTHONIOENCODING=utf-8` 前缀（Windows 编码，deepxiv 与 sn 脚本均需）
- `web` 通道参数沿用 v0.4：`content_size: "high"`、`location: {search_location}`、`search_recency_filter` 参考 brief 时效要求
- 输出统一映射为 `search_results`，**每条补 `source_type` 字段**（供 summary 标注来源层次与交叉验证）：
  - deepxiv：`result[].{title, arxiv_id→url: https://arxiv.org/abs/{arxiv_id}, tldr||abstract→snippet, source_type:"academic"}`
  - sn-search-*：`items[].{title, url, snippet, source_type:"<对应类型>"}`
  - web：`{title, url, snippet, source_type:"web"}`

**降级规则（关键，所有专门通道统一）：**
专门通道不稳定（deepxiv 日额度用完返 429、脚本 `success:false`、报错、缺依赖）时，该 query **立即回退 MCP `web-search-prime` 重试一次**，并在进度里 log（不静默）。这保证任意专门通道挂掉都不会让研究卡死。

```yaml
# 分派伪代码
for query in query_list:
    channel = CHANNEL_MAP[query.source_type]
    result = invoke(channel, query)
    if 专门通道 and (result 失败 or 限流 or 缺依赖):
        log("⚠ {query.source_type} 通道失败，已降级 web")
        result = invoke(MCP_web_search_prime, query)   # 降级重试
    search_results += normalize(result, query.source_type)
```

> 借鉴 open_deep_research 的并行 fan-out 思想，但限于 Skill 范式仅在"查询级"并行（一条消息多调用），不做 researcher 子图级并行。多源通道与三层搜索模型借鉴 sn-deep-research。

#### 3.2b 深度阅读关键来源（按需）【v0.5.0 增强】

对高价值结果（权威综述、论文、官方文档、厂商手册）做原始核验。**学术来源（arxiv 论文，即 academic 通道产出）优先用 deepxiv 渐进式精读**（按章节 + token 分布，比 web-reader 抓 arxiv 页面更省更准），非 arxiv 来源用 MCP web-reader：

```yaml
# 学术来源（有 arxiv_id）→ deepxiv 渐进式精读
PYTHONIOENCODING=utf-8 deepxiv paper {arxiv_id} --brief          # 先看 TLDR/引用数/GitHub，判断价值
PYTHONIOENCODING=utf-8 deepxiv paper {arxiv_id} --head           # 看章节结构与 token 分布
PYTHONIOENCODING=utf-8 deepxiv paper {arxiv_id} --section "..."  # 只读最关键章节（Method/Experiments/...）

# 非学术来源 → MCP 网页读取（严禁内置 WebFetch）
调用 MCP 工具 mcp__web-reader__webReader:
  url: {result_url}
  return_format: "markdown"

说明:
  - 输出过大时读取 Preview（前 2KB）判断价值
  - 每轮挑选 2-4 个最相关来源深读
```

**原始核验与交叉验证**：本步对应三层搜索的「原始核验」。关键数字/时间/结论/高风险判断，优先回到原始来源确认；**至少用 2 个独立来源交叉确认**，冲突无法解决时记录冲突并在 summary 标注（见 summary 节点交叉验证标记规则）。

#### 3.3a 生成本轮小结（summarize）

启动 **summarizer** subagent，对**本轮**搜索结果生成结构化小结：

```yaml
使用 Task 工具启动 subagent:
  description: 整合本轮搜索结果 (第 {loop_count} 轮)
  subagent_type: general-purpose
  prompt: |
    按 agents/research-node-summary.md 的定义执行。
    输入: research_topic、research_brief（分段维度）、本轮 search_results
    输出: 本轮结构化小结（分段遵循 brief 维度）
  返回结果保存到: loop_summary
```

#### 3.3b 融入累积摘要（merge）

将 `loop_summary` 融入 `running_summary`（保留结构、避免重复、更新 [n] 引用编号）。
- 首轮：`running_summary = loop_summary`
- 后续：融入相关段落，新增内容用新引用编号

添加来源（URL 自动去重）：
```python
added = state.add_sources(extract_urls(search_results))
save_checkpoint(state)
```

#### 3.3c 摘要压缩（compress，阈值触发）【v0.4.0 新增】

```python
# 确定性判定（不由 LLM 判断长度）
if len(running_summary) > compress_threshold_chars and loop_count > 1:
    启动 compressor subagent
```

```yaml
使用 Task 工具启动 subagent（仅当超阈值时）:
  description: 压缩研究摘要
  subagent_type: general-purpose
  prompt: |
    按 agents/research-node-compress.md 的定义执行。
    输入: research_topic、research_brief（维度）、running_summary
    输出: 压缩后的 running_summary（≤原长 50%，保留事实与 [n] 引用编号）
  返回结果保存到: running_summary   # 覆盖
```

> 首轮（loop=1）不压缩，保基础理解。`sources` 列表不受压缩影响（独立结构化字段）。

#### 3.4 反思与决策（reflect）

启动 **reflector** subagent，**评分维度由 research_brief 动态驱动**：

```yaml
使用 Task 工具启动 subagent:
  description: 反思研究进展 (第 {loop_count} 轮)
  subagent_type: general-purpose
  prompt: |
    按 agents/research-node-reflect.md 的定义执行。
    输入: research_topic、research_brief（评分维度与权重从此读取）、running_summary、loop_count/max_loops
    输出:
      {
        completeness_score: <按 brief 权重加权 1-10>,
        dimension_scores: { "<brief 维度>": <1-10>, ... },
        knowledge_gaps: [...],
        should_continue: true/false,
        reasoning: "..."
      }
  返回结果保存到: reflect_result
```

**决策准则**（沿用）：
- 继续：完整性 < 7 或有重要缺口
- 结束：完整性 ≥ 8 且主要维度已覆盖

#### 3.5 循环决策

```python
if not reflect_result["should_continue"]:
    break
```

### 第 4 步：生成最终报告（finalize）【v0.6.0 改进】

启动 **reporter** subagent，**报告分段/受众/格式引用 research_brief**，并**自动保存到文件**：

```yaml
使用 Task 工具启动 subagent:
  description: 生成最终研究报告并自动保存
  subagent_type: general-purpose
  prompt: |
    按 agents/research-node-finalize.md 的定义执行（包含自动保存功能）。
    输入:
      - research_topic
      - research_brief（报告分段维度、受众、深度、输出格式）
      - running_summary
      - sources（格式化）
      - loop_count
      - 自动保存到: {自动计算的文件路径}
    输出: 完整 Markdown 报告（详细研究分段遵循 brief 维度）
  返回结果保存到: final_report
```

**自动保存规则**：
- **报告路径**：`workspace/reports/{YYYY-MM-DD}-{主题}-{hex4}/report.md`
- **研究目录**：同一研究中包含 process.md、sources.json 等元数据
- **自动归档**：研究完成后移动到 `output/documents/` 和 `archive/{年份}/projects/`

### 第 5 步：输出报告（自动保存）【v0.6.0 改进】

**自动保存报告到文件系统**：

```bash
# 生成唯一的研究标识和目录
REPORT_ID=$(echo | od -An -tx1 | head -1 | tr -d ' ' | cut -c1-4)
CURRENT_DATE=$(date +%Y-%m-%d)
TOPIC_SAFE=$(echo "$research_topic" | sed 's/[^\w一-龥-]//g' | sed 's/\s+/-/g' | cut -c1-20)
REPORT_DIR="workspace/reports/${CURRENT_DATE}-${TOPIC_SAFE}-${REPORT_ID}"

# 创建研究目录
mkdir -p "$REPORT_DIR"

# 保存主报告
echo "$final_report" > "$REPORT_DIR/report.md"

# 生成并保存研究过程记录
cat > "$REPORT_DIR/research-process.md" << 'EOF'
# 深度研究过程记录

## 研究基本信息
- 主题: $research_topic
- 日期: $CURRENT_DATE
- 研究ID: $REPORT_ID
- 研究轮次: $loop_count

## 研究过程
[完整的研究过程记录将在后续版本中补充]

## 数据来源
- 来源数量: ${#sources[@]}
- 搜索轮次: $loop_count
EOF

# 保存来源列表（JSON格式）
echo "$sources" | jq '.' > "$REPORT_DIR/sources.json" 2>/dev/null || echo "$sources" > "$REPORT_DIR/sources.txt"
```

**向用户报告保存位置**：
- 主报告：`$REPORT_DIR/report.md`
- 过程记录：`$REPORT_DIR/research-process.md`
- 来源列表：`$REPORT_DIR/sources.json`

**用户可选择后续操作**：
- 保持当前位置（`workspace/reports/`）
- 移动到成品目录（`output/documents/`）
- 完整归档（`archive/{年份}/projects/`）

---

## 实现说明

### Subagent 任务文件

各 subagent 的详细任务定义位于 `agents/` 目录：

| 节点文件 | 角色 | 阶段 | 版本 |
|----------|------|------|------|
| `research-node-clarify.md` | 意图澄清 | 循环前 | v0.4.0 新增 |
| `research-node-brief.md` | 研究简报生成 | 循环前 | v0.4.0 新增 |
| `research-node-query.md` | 查询生成（多查询） | 循环内 | v0.4.0 改造 |
| `research-node-summary.md` | 摘要生成（brief 驱动分段） | 循环内 | v0.4.0 改造 |
| `research-node-compress.md` | 摘要压缩 | 循环内 | v0.4.0 新增 |
| `research-node-reflect.md` | 反思决策（brief 驱动维度） | 循环内 | v0.4.0 改造 |
| `research-node-finalize.md` | 报告生成（brief 驱动分段） | 循环后 | v0.4.0 改造 |

### 搜索通道与工具【v0.5.0 改】

按 query 的 `source_type` 分派（详见第 3.2 步映射表）：

| source_type | 工具 | 用途 | 关键参数 |
|-------------|------|------|----------|
| `web` | **mcp__web-search-prime__web_search_prime** | 通用网页搜索（官方/新闻/监管/综合） | search_query / content_size / location / search_recency_filter |
| `academic` | **deepxiv CLI** | 学术论文搜索 + 渐进式精读 | search: `--limit --format json --mode --min-citations --categories --date-from`；paper: `--brief/--head/--section` |
| `code` | **sn-search-code 脚本** | GitHub / Stack Overflow / Hacker News / HuggingFace | `--limit`（GitHub 另有 `--type`） |
| `social_cn` | **sn-search-social-cn 脚本** | 知乎 / B站 / 抖音 | `--limit` |
| `social_en` | **sn-search-social-en 脚本** | Twitter / YouTube（reddit 已禁用） | `--limit` |

其他工具：

| 工具 | 用途 | 关键参数 |
|------|------|----------|
| **mcp__web-reader__webReader** | 非 arxiv 网页全文抓取（严禁内置 WebFetch） | url / return_format |
| **AskUserQuestion** | 澄清提问（选项可枚举时） | questions / options |
| **state_manager.py** | 状态管理（可选，命令行编排用） | Python 模块导入 |

> **降级**：任一专门通道（academic/code/social）失败/限流/缺依赖时，回退 `mcp__web-search-prime`（见 3.2 降级规则）。

### 状态管理

使用 `scripts/state_manager.py` 中的 `ResearchState` 类管理研究状态，v0.4.0 新增字段：
- `research_brief`: 研究简报（clarify + brief 阶段产出）
- `search_queries`: 当前轮查询列表（多查询并行）

支持：保存检查点（每轮循环后）、恢复中断会话、来源 URL 去重累积。

### 搜索与抓取（多源）【v0.5.0 改】

搜索按 query 的 `source_type` 分派到 5 个通道（web=MCP / academic=deepxiv / code / social_cn / social_en=脚本），网页抓取分学术（deepxiv paper）与非学术（MCP web-reader）。遵循全局网络访问规则。

- **web 通道（MCP web-search-prime）** - 通用网页搜索，返回标题/链接/摘要
  - `location`：`us`（英文资料）或 `cn`（中文资料），可多区域并行
  - `content_size`：深度研究用 `high`
  - `search_recency_filter`：参考 brief 的时效要求
- **academic 通道（deepxiv）** - 学术论文搜索（`deepxiv search --format json`）+ 渐进式精读（`deepxiv paper`），走自有后端，10k/天额度
- **code / social 通道（sn-search-* 脚本）** - 开发者资源与社区讨论，Bash 调用，输出标准 JSON
- **mcp__web-reader__webReader** - 非学术网页全文抓取，输出 markdown

**注意**：
- 严禁使用内置 WebSearch / WebFetch，`web` 通道与网页抓取必须走上述 MCP 工具
- 所有 Bash 命令（deepxiv / sn 脚本）加 `PYTHONIOENCODING=utf-8` 前缀
- 专门通道失败统一降级到 MCP web-search-prime（见 3.2 降级规则）

---

## 示例对话

### 用户: 研究一下 AI

**AI**（第 1.5 步 clarify：判定为宽泛主题，触发澄清）

**[澄清提问]**（AskUserQuestion）
- 研究范围？→ 用户选"产业应用与落地"
- 报告受众？→ 用户选"管理层/决策者"

**[第 1.8 步 brief]** 生成研究简报（范围:AI 产业应用 / 受众:管理层 / 维度:市场规模/竞争格局/商业模式/...）

**[第 1/3 轮]**
- 多查询: ["AI industry market size 2025", "AI enterprise applications case studies", "AI adoption trends enterprise"] ×3 并行搜索
- 本轮小结 + 融入摘要
- 反思（按 brief 维度评分）: 6.0/10，继续

**[第 2/3 轮]** ...（按 knowledge_gaps 定向查询）

**[第 3/3 轮]** ... 完整性 8.5/10，完成

**[最终报告]**（分段遵循 brief 维度：市场规模/竞争格局/商业模式/...）

---

## 注意事项

1. **Subagent 隔离**：每个节点在独立的 subagent 中执行，避免上下文污染
2. **流式输出**：向用户实时报告研究进度
3. **错误恢复**：支持中断后恢复，使用 `--resume` 参数
4. **资源限制**：每轮限制搜索结果数量，避免过度消耗
5. **澄清单轮约束**：clarify 最多 1 轮，能推断则不问
6. **压缩兜底**：若 compress 结果反而更长或丢失明显信息，回退使用原摘要
7. **维度一致性**：summary / reflect / finalize 三者的分段维度必须统一来自 research_brief
