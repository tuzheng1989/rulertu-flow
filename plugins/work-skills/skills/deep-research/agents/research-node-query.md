# Research Node: Query Generator

## 任务描述

生成优化的搜索查询**列表**。根据研究主题、研究简报、当前摘要和循环次数，创建多条针对性的搜索查询，供主控流程并行执行。

## 输入参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `research_topic` | string | 研究主题 |
| `research_brief` | string | 研究简报（含必须覆盖的维度清单，作为生成锚点） |
| `running_summary` | string | 当前累积摘要（可能为空） |
| `loop_count` | number | 当前循环次数 |
| `max_loops` | number | 最大循环次数 |
| `knowledge_gaps` | array | 已识别的知识缺口（后续轮次） |

## 输出格式

输出 JSON 对象，包含 2-4 条搜索查询，每条标注查询意图、来源类型与来源层次。不要包含任何解释或额外内容。

```json
{
  "queries": [
    {"query": "<搜索查询1>", "intent": "<查询角度/意图>", "source_type": "<academic|code|social_cn|social_en|web>", "source_tier": "<primary|secondary|supplementary>"},
    {"query": "<搜索查询2>", "intent": "<查询角度/意图>", "source_type": "...", "source_tier": "..."},
    {"query": "<搜索查询3>", "intent": "<查询角度/意图>", "source_type": "...", "source_tier": "..."}
  ]
}
```

### 字段说明

| 字段 | 取值 | 说明 |
|------|------|------|
| `query` | string | 搜索查询 |
| `intent` | string | 查询角度/意图 |
| `source_type` | `academic` \| `code` \| `social_cn` \| `social_en` \| `web` | 该查询应走的搜索通道，决定主控调用哪个搜索工具（见「source_type 选择指南」） |
| `source_tier` | `primary` \| `secondary` \| `supplementary` | 来源优先级：`primary`=原始/官方 > `secondary`=权威二级 > `supplementary`=社区补充 |

## 执行逻辑

### 首轮循环 (loop_count == 1)

生成 **3 条**广覆盖查询，从不同角度建立基础理解。本轮定位为**三层搜索的「广度发现」**——优先摸清来源地图，识别关键实体、术语、机构、争议点与候选来源类型。

**固定三角度：**
1. **核心概念** — 主题的定义、基本原理与关键术语
2. **应用场景** — 实际应用领域、典型案例
3. **最新进展** — 当前发展状态、近期动态

**策略：**
- 三条查询覆盖不同维度，避免重叠
- **至少 1 条标注 `source_type: web`** 做广度发现（通用网页摸来源地图）
- 其余两条按主题性质选合适的 source_type（学术主题用 `academic`，技术工程用 `code` 等）
- 技术主题优先使用英文关键词
- 学术主题考虑学术表达

### 后续循环 (loop_count > 1)

基于 `knowledge_gaps` 生成定向查询，**每个缺口对应一条查询**（上限 4 条）。本轮定位为**三层搜索的「专项深挖」**——针对上一轮反思指出的缺口，换来源类型或换检索词深挖。

**策略：**
- 每个 knowledge_gap 生成一条针对性查询
- **来源覆盖缺口优先**：若 reflect 指出某维度过度依赖单一来源类型（如仅社区来源缺官方/学术交叉），相应 query 标注未覆盖的 `source_type`
- 关键数字/时间/结论类查询标注 `source_tier: primary`（原始来源优先，便于交叉验证）
- 缺口不足 2 个时，从 `research_brief` 的维度清单中补充未充分覆盖的维度
- 使用更具体的关键词组合
- 随循环进行，查询应越来越具体

## source_type 选择指南

按查询性质为每条 query 选择最合适的来源通道：

| 查询性质 | source_type | 典型场景 |
|---------|-------------|---------|
| 学术论文、理论原理、研究方法、技术综述 | `academic` | 算法原理、学术论文、理论基础（走 deepxiv） |
| 开源项目、代码实现、技术问答、模型/数据集 | `code` | GitHub 仓库、Stack Overflow、HuggingFace |
| 中文用户经验、中文社区讨论、中文视频 | `social_cn` | 知乎、B站、抖音上的使用反馈 |
| 英文社区讨论、英文视频、英文舆情 | `social_en` | Twitter、YouTube（Reddit 不可用） |
| 官方文档、监管公告、公司披露、新闻报道、机构页面 | `web` | 官方/新闻/监管/通用网页 |

**选择原则：**
- 一条 query 选**最主要**的一个 source_type（不重复搜）
- 官方/新闻/监管类事实优先 `web`（原始来源）
- 不确定时默认 `web`（通用通道覆盖最广，且是其他通道失败时的降级目标）

---

## 提示词模板

```
你是一个研究查询生成专家。你的任务是根据研究主题和当前进展，生成多条优化的搜索查询。

## 输入信息
- 研究主题: {research_topic}
- 研究简报: {research_brief}
- 当前摘要: {running_summary or "(无)"}
- 循环次数: {loop_count}/{max_loops}
- 知识缺口: {knowledge_gaps or "(无)"}

## 任务要求

{"首轮" if loop_count == 1 else "后续"}循环:
{"生成 3 条广覆盖查询，固定覆盖：核心概念 / 应用场景 / 最新进展 三个角度，避免重叠。" if loop_count == 1 else "基于知识缺口生成定向查询，每个缺口一条（上限 4 条）；缺口不足时从研究简报的维度清单补充未覆盖维度。"}

## 输出格式
输出 JSON 对象，包含 queries 数组，每条含 query 与 intent 字段。不要输出任何解释。

## 输出:
```

## 示例

### 示例 1：首轮查询

**输入：**
- research_topic: "量子计算在密码学中的应用"
- loop_count: 1

**输出：**
```json
{
  "queries": [
    {"query": "post-quantum cryptography overview", "intent": "核心概念", "source_type": "web", "source_tier": "secondary"},
    {"query": "Shor algorithm quantum threat RSA ECC", "intent": "核心概念", "source_type": "academic", "source_tier": "primary"},
    {"query": "NIST PQC standardization 2025 progress", "intent": "最新进展", "source_type": "web", "source_tier": "primary"}
  ]
}
```

### 示例 2：后续查询

**输入：**
- research_topic: "量子计算在密码学中的应用"
- loop_count: 2
- knowledge_gaps: ["NIST 标准化的具体时间表", "商业抗量子产品可用性", "性能数据仅社区来源，缺官方/学术交叉"]

**输出：**
```json
{
  "queries": [
    {"query": "NIST post-quantum cryptography standardization timeline FIPS", "intent": "补缺口:标准化时间表", "source_type": "web", "source_tier": "primary"},
    {"query": "commercial post-quantum cryptography products vendors 2025", "intent": "补缺口:商业产品", "source_type": "web", "source_tier": "primary"},
    {"query": "post-quantum cryptography benchmark performance comparison", "intent": "来源覆盖缺口:补官方/学术性能数据", "source_type": "academic", "source_tier": "primary"}
  ]
}
```

## 注意事项

1. 每条查询应简洁明确，避免过于宽泛或过于狭窄
2. 多条查询之间覆盖不同维度，避免内容重叠
3. 技术主题优先使用英文关键词
4. 考虑搜索引擎的查询语法
5. **source_type 多样性**：一轮内尽量让多条查询覆盖不同 source_type，避免全部挤在同一通道（首轮至少 1 条 `web`）

## 相关文件

- 上一节点: 循环入口 / `research-node-brief.md`（首轮前）
- 下一节点: 主控流程的并行搜索步骤
- 主控流程: `../scripts/orchestrator.py`
