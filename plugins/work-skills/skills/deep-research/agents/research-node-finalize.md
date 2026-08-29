# Research Node: Report Finalizer

## 任务描述

将研究摘要和来源整理成一份规范、专业的 Markdown 研究报告。

## 输入参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `research_topic` | string | 研究主题 |
| `research_brief` | string | 研究简报（**报告分段、受众、深度、输出格式从此读取**） |
| `running_summary` | string | 完整研究摘要 |
| `sources` | array | 所有来源列表 |
| `loop_count` | number | 实际研究轮次 |
| `sources_count` | number | 来源总数 |
| `created_at` | string | 研究开始时间 |
| `session_id` | string | 会话ID |

## 输出格式

```markdown
# 深度研究报告：{research_topic}

> 📅 **生成时间**: {YYYY-MM-DD HH:MM}
> 🔁 **研究轮次**: {loop_count} 轮迭代研究
> 📚 **来源数量**: {sources_count} 个权威来源
> 🎯 **目标受众**: {来自 research_brief} ｜ **研究深度**: {来自 research_brief}

---

## 执行摘要

{200-300 字的执行摘要，概括核心发现和结论}

---

## 详细研究

{主体内容：基于 running_summary 进行结构化优化，并**充分展开**为读者友好的详尽正文——每个维度写成 3-5 句充实段落，包含具体事例、量化数据、对比与引用 [n]，不要压缩成干瘪要点。注意：running_summary 是经过去重的精简中间态，本节点必须把它重新展开为舒展的正文，而非照搬其紧凑度}

> **v0.4.0 变更**：报告分段**遵循 research_brief 的「必须覆盖的维度」清单**，每个维度对应一个小节，维度数量与名称由 brief 决定。
> 示例（若 brief 维度为：核心概念与威胁机理 / 抗量子算法原理 / NIST 标准化 / 部署案例 / 工程挑战 / 迁移展望）：

### 1. <brief 维度1>
{内容...}

### 2. <brief 维度2>
{内容...}

### N. <brief 维度N>
{内容...}

---

## 关键发现

1. **发现一**: {简明描述}
2. **发现二**: {简明描述}
3. **发现三**: {简明描述}

---

## 参考来源

### 参考来源

1. **[标题一]**(链接一) - 简短说明
2. **[标题二]**(链接二) - 简短说明
3. **[标题三]**(链接三) - 简短说明
...

---

## 附录

### 研究方法论

本研究采用 IterDRAG（Iterative Deep Research with Aggregated Generation）方法：
- 通过多轮"搜索-总结-反思"循环迭代深化研究
- 每轮循环基于已有信息识别知识缺口
- 通过增量式总结避免重复内容
- 确保来源的权威性和可靠性

### 搜索策略

- 首轮：广泛覆盖主题核心
- 后续：针对知识缺口定向深入
- 搜索工具：mcp__web-search-prime__web_search_prime + mcp__web-reader__webReader
- 搜索区域：{search_location}
- 每轮并行 3-5 个查询，深读 2-4 个高价值来源

---

*本报告由 Deep Research Skill 自动生成*
*报告版本: 1.0*
*会话ID: {session_id}*
```

## 执行逻辑

### 1. 处理摘要内容

- 优化段落结构
- 统一标题层级
- 确保过渡自然
- 生成执行摘要

### 2. 提取关键发现

从摘要中提取 3-5 个最重要的发现或结论。

### 3. 格式化来源

将来源列表格式化为规范的引用格式：
- 按出现顺序编号
- 提取标题和链接
- 添加简短说明

### 4. 生成元数据

- 生成时间戳
- 统计研究轮次
- 统计来源数量
- 添加会话ID

### 5. 添加附录

- 研究方法论说明
- 搜索策略描述

### 6. 自动保存报告【v0.6.0 新增】

**自动保存逻辑**：
```bash
# 生成唯一的研究目录标识
REPORT_ID=$(echo | od -An -tx1 | head -1 | tr -d ' ' | cut -c1-4)
REPORT_DIR="workspace/reports/$(date +%Y-%m-%d)-${研究主题简化}-${REPORT_ID}"

# 创建研究目录
mkdir -p "$REPORT_DIR"

# 保存主报告
echo "$final_report" > "$REPORT_DIR/report.md"

# 保存研究过程记录
echo "$research_process_log" > "$REPORT_DIR/research-process.md"

# 保存来源列表（JSON格式）
echo "$sources_json" > "$REPORT_DIR/sources.json"
```

**文件命名规范**：
- 研究目录：`{日期}-{主题简述}-{4位hex}/`
- 主报告：`report.md`
- 过程记录：`research-process.md`
- 来源数据：`sources.json`

**保存路径返回**：
```json
{
  "report_path": "workspace/reports/{完整目录}/report.md",
  "process_path": "workspace/reports/{完整目录}/research-process.md",
  "sources_path": "workspace/reports/{完整目录}/sources.json",
  "report_dir": "workspace/reports/{完整目录}/"
}
```

**主题简化规则**：
- 移除特殊字符：`/[^\w一-龥-]/g` → 删除
- 空格替换：`/\s+/g` → `-`
- 长度限制：最多20字符
- 中文转拼音（可选）：保留UTF-8编码

## 提示词模板

```
你是一个专业的研究报告生成专家。你的任务是将研究摘要和来源整理成一份规范、专业的 Markdown 报告。

## 输入信息
- 研究主题: {research_topic}
- 研究简报: {research_brief}
- 完整摘要: {running_summary}
- 所有来源: {all_sources}
- 研究轮次: {loop_count}
- 生成时间: {timestamp}

## 报告结构

请按以下结构生成最终报告：

```markdown
# 深度研究报告：{research_topic}

> 📅 **生成时间**: {YYYY-MM-DD HH:MM}
> 🔁 **研究轮次**: {loop_count} 轮迭代研究
> 📚 **来源数量**: {sources_count} 个权威来源
> 🎯 **目标受众**: {来自 research_brief} ｜ **研究深度**: {来自 research_brief}

---

## 执行摘要

{200-300 字的执行摘要，概括核心发现和结论}

---

## 详细研究

{主体内容：基于 running_summary 进行结构化优化，并**充分展开**为读者友好的详尽正文——每个维度写成 3-5 句充实段落，包含具体事例、量化数据、对比与引用 [n]，不要压缩成干瘪要点。注意：running_summary 是经过去重的精简中间态，本节点必须把它重新展开为舒展的正文，而非照搬其紧凑度}

> **v0.4.0 变更**：报告分段**遵循 research_brief 的「必须覆盖的维度」清单**，每个维度对应一个小节，维度数量与名称由 brief 决定。
> 示例（若 brief 维度为：核心概念与威胁机理 / 抗量子算法原理 / NIST 标准化 / 部署案例 / 工程挑战 / 迁移展望）：

### 1. <brief 维度1>
{内容...}

### 2. <brief 维度2>
{内容...}

### N. <brief 维度N>
{内容...}

---

## 关键发现

1. **发现一**: {简明描述}
2. **发现二**: {简明描述}
3. **发现三**: {简明描述}

---

## 参考来源

{按出现顺序编号的来源列表}

---

## 附录

### 研究方法论

本研究采用 IterDRAG（Iterative Deep Research with Aggregated Generation）方法：
- 通过多轮"搜索-总结-反思"循环迭代深化研究
- 每轮循环基于已有信息识别知识缺口
- 通过增量式总结避免重复内容
- 确保来源的权威性和可靠性

### 搜索策略

- 首轮：广泛覆盖主题核心
- 后续：针对知识缺口定向深入
- 搜索工具：mcp__web-search-prime__web_search_prime + mcp__web-reader__webReader
- 搜索区域：{search_location}
- 每轮并行 3-5 个查询，深读 2-4 个高价值来源

---

*本报告由 Deep Research Skill 自动生成*
*报告版本: 1.0*
```

## 来源格式化

请将来源格式化为：

```markdown
### 参考来源

1. **[标题]**(链接) - 简短说明/来源
2. **[标题]**(链接) - 简短说明/来源
3. **[标题]**(链接) - 简短说明/来源
...
```

## 格式化要求

1. **标题层级**:
   - 一级标题 (#) 仅用于报告标题
   - 二级标题 (##) 用于主要章节
   - 三级标题 (###) 用于子章节

2. **强调格式**:
   - 关键术语使用**粗体**
   - 重要概念使用`代码格式`
   - 引用使用> 引用块

3. **列表格式**:
   - 并列项使用无序列表
   - 有序步骤使用有序列表
   - 嵌套列表使用适当缩进

4. **链接格式**:
   - 所有来源链接可点击
   - 使用描述性链接文本

5. **引用处理（锚链跳转，必做）**:
   - **正文引用**：每个 `[n]` 必须挂成指向文末参考来源的锚链，格式 `[[n]](#ref-n)`；连续多引用逐一展开，如 `[[1]](#ref-1)[[2]](#ref-2)`（渲染后显示 `[1][2]`，各自可点跳到对应来源条目）。**禁止保留裸 `[n]` 文本标记。**
   - **参考来源锚点**：来源列表每一条在编号后、标题前插入 `<a id="ref-n"></a>`，使 `#ref-n` 能定位到该条目；条目本身保留可点外链 `**[标题](url)**`。
   - **锚点 id 与编号一一对应**（ref-1 … ref-N，N = 来源总数），不得跳号或重号。
   - **示例**：
     - 正文：`Fora 以 $6000 万 D 轮跻身独角兽 [[1]](#ref-1)[[2]](#ref-2)。`
     - 来源：`1. <a id="ref-1"></a>**[TechCrunch — Fora hits unicorn](https://...)** - Series D 公告`
   - 注：此为内部锚链跳转（正文 → 文末来源条目 → 原文），适配 GitHub/本地预览/pdf 内链；部分 md 渲染器（如飞书）对锚点跳转支持有限，降级为不可点但不影响阅读。

---

## 现在请生成最终研究报告：

**研究主题**: {research_topic}
**研究摘要**: {running_summary}
**来源列表**: {formatted_sources}
**研究统计**: {loop_count} 轮，{sources_count} 个来源

---

# 深度研究报告：{research_topic}

> **📁 报告自动保存**：生成后将自动保存到 `workspace/reports/{日期}-{主题}-{hex}/report.md`
> **📋 完整研究包**：包含主报告、过程记录、来源列表
> **🔄 研究版本**：v0.6.0（支持自动落盘）

```

## 关键发现提取指南

从摘要中提取最重要的发现，每个发现应该：

1. **具体明确**: 清楚陈述发现内容
2. **有据可循**: 基于研究摘要
3. **简洁有力**: 一句话概括
4. **独立完整**: 可以独立理解

### 示例

| 原摘要内容 | 关键发现 |
|-----------|---------|
| "量子计算机能够在多项式时间内破解RSA、ECC等传统公钥密码系统，这构成了对当前网络安全的基础性威胁。" | **量子计算威胁传统密码学基础** |
| "NIST正在标准化抗量子密码算法，包括基于格、基于哈希等方案，已进入第三轮评选。" | **NIST 抗量子密码标准化进入最后阶段** |
| "抗量子算法通常需要更大的密钥尺寸和更长的计算时间，这给实际部署带来挑战。" | **抗量子密码面临性能和部署挑战** |

## 执行摘要生成指南

执行摘要应该包含：

1. **研究背景**: 1-2 句话说明主题重要性
2. **主要内容**: 2-3 句概括核心信息
3. **关键发现**: 1-2 句突出最重要的发现
4. **结论/展望**: 1 句总结或未来展望

### 示例

```markdown
## 执行摘要

量子计算对传统密码学构成了前所未有的威胁，能够在多项式时间内破解 RSA、ECC 等广泛使用的公钥密码系统。本报告深入研究了量子计算在密码学领域的应用与挑战，分析了抗量子密码技术的发展现状。

研究发现，NIST 正在推进抗量子密码算法的标准化工作，基于格的密码方案被认为是最有前景的方向之一。然而，抗量子算法在性能、部署成本和互操作性方面仍面临挑战。建议相关组织提前规划密码学迁移策略，以应对"现在窃取，未来解密"（Store Now, Decrypt Later）攻击。
```

## 来源格式化示例

### 输入来源列表

```json
[
  "**[量子计算对密码学的威胁]**(https://example.com/quantum-threat) - 详细分析量子计算如何破解传统密码系统",
  "**[抗量子密码算法介绍]**(https://example.com/post-quantum) - NIST 标准化的抗量子密码方案概述",
  "**[NIST 抗量子密码标准化进展]**(https://example.com/nist-pqc) - NIST PQC 标准化项目的最新状态"
]
```

### 格式化后

```markdown
### 参考来源

1. **[量子计算对密码学的威胁](https://example.com/quantum-threat)** - 详细分析量子计算如何破解传统密码系统
2. **[抗量子密码算法介绍](https://example.com/post-quantum)** - NIST 标准化的抗量子密码方案概述
3. **[NIST 抗量子密码标准化进展](https://example.com/nist-pqc)** - NIST PQC 标准化项目的最新状态
```

## 注意事项

1. **完整性**: 确保所有重要信息都包含在报告中
2. **准确性**: 引用和链接必须准确无误
3. **可读性**: 使用适当的分段和格式，便于阅读
4. **专业性**: 保持专业、客观的语气
5. **一致性**: 格式和风格保持一致

## 相关文件

- 上一节点: `research-node-research-node-reflect.md`
- 主控流程: `../SKILL.md` 第4步
- 状态管理: `../scripts/state_manager.py`

## 执行指令【v0.6.0 新增】

**在生成最终报告后，必须执行以下保存操作**：

1. **使用 Write 工具保存主报告**：
   - 生成文件路径：`workspace/reports/{YYYY-MM-DD}-{主题简化}-{hex}/report.md`
   - 写入完整Markdown内容

2. **使用 Write 工具保存过程记录**：
   - 文件路径：`workspace/reports/{YYYY-MM-DD}-{主题简化}-{hex}/research-process.md`
   - 写入研究过程记录

3. **返回保存结果**：
   ```json
   {
     "auto_saved": true,
     "report_path": "workspace/reports/{完整路径}/report.md",
     "process_path": "workspace/reports/{完整路径}/research-process.md",
     "sources_path": "workspace/reports/{完整路径}/sources.json",
     "report_dir": "workspace/reports/{完整路径}/"
   }
   ```

**主题简化规则**（用于文件路径）：
- 移除特殊字符：`sed 's/[^\w一-龥-]//g'`
- 空格替换为连字符：`sed 's/\s+/-/g'`
- 限制长度：最多20字符

**示例保存指令**：
```bash
# 生成研究标识和目录
REPORT_ID="a3f2"
CURRENT_DATE=$(date +%Y-%m-%d)
TOPIC_SAFE=$(echo "$research_topic" | sed 's/[^\w一-龥-]//g' | sed 's/\s+/-/g' | cut -c1-20)
REPORT_DIR="workspace/reports/${CURRENT_DATE}-${TOPIC_SAFE}-${REPORT_ID}"

# 创建目录并保存
mkdir -p "$REPORT_DIR"
echo "$final_report" > "$REPORT_DIR/report.md"
echo "$research_process" > "$REPORT_DIR/research-process.md"
```
