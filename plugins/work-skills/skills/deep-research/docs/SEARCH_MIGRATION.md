# 搜索层迁移说明：meta-search → MCP 工具

## 背景

自 v0.3.0 起，deep-research 技能的搜索与网页抓取从 `meta-search` skill（依赖 Playwright + 必应）迁移至 MCP 工具，以符合本项目全局网络访问规则：**禁止内置 WebSearch / WebFetch，必须使用 MCP 工具**。

## 新的搜索工具

| 工具 | 用途 | 关键参数 |
|------|------|----------|
| `mcp__web-search-prime__web_search_prime` | 网络搜索 | search_query / content_size / location / search_recency_filter |
| `mcp__web-reader__webReader` | 网页全文抓取 | url / return_format |

## 迁移对照

| 旧（meta-search） | 新（MCP 工具） |
|-------------------|----------------|
| `engine: bing` | `location: us`（英文资料）/ `cn`（中文资料） |
| Playwright 渲染必应、提取智能摘要 | `mcp__web-search-prime` 返回 content 摘要 |
| 摘要不够时无回退 | 对高价值来源用 `mcp__web-reader__webReader` 抓全文深读 |
| `/meta-search {query}`（skill 触发，单查询） | 直接调用 MCP 工具，可在一条消息里并行 3-5 个查询 |

## 权威来源

运行时行为以 [SKILL.md](../SKILL.md) 为准。本文档仅记录迁移要点。

`docs/ARCHITECTURE.md`、`docs/IMPLEMENTATION_PLAN.md` 与 `docs/PROMPTS.md` 描述的是迁移前的设计（基于 meta-search），其中搜索相关章节已滞后，仅供参考。

## 未迁移部分

`scripts/orchestrator.py`（命令行端到端编排，独立路径）的 `_search_with_skill` 仍通过 Claude CLI 调用 `meta-search` skill，未随本次迁移。该脚本不影响 Claude 会话内的技能运行时；会话内执行技能一律走 SKILL.md 的 MCP 流程。

---

## v0.5.0：多源搜索通道（移植 sn-deep-research 搜索方法）

### 背景

v0.4.x 的搜索层虽已迁移到 MCP 工具，但仍只有 `web-search-prime` 一个通用网页通道，缺少多源、多类型、分层核验能力。v0.5.0 移植 sn-deep-research 的搜索方法（三层搜索模型 + 技能分工 + 来源优先级 + 交叉验证），在保留 MCP web 通道的基础上新增 4 个专门通道。**不改** running_summary / 引用 `[n]` / finalize 链路。

### 通道架构

| source_type | 通道 | 入口 |
|---|---|---|
| `web` | MCP web-search-prime | 保留 v0.4 |
| `academic` | deepxiv CLI | `deepxiv search --format json` / `deepxiv paper --section` |
| `code` | sn-search-code 脚本 | github / stackoverflow / hackernews / huggingface |
| `social_cn` | sn-search-social-cn 脚本 | zhihu / bilibili / douyin |
| `social_en` | sn-search-social-en 脚本 | twitter / youtube（reddit 已禁用） |

主控按 query 节点产出的 `source_type` 分派；query 同时标注 `source_tier`（primary/secondary/supplementary）表达来源优先级。

### academic 通道为何选 deepxiv 而非 sn-search-academic

sn-search-academic 的 `arxiv_search.py` 直打 arxiv 公开 API，易被 429 限流（实测）。deepxiv 走自有后端（`data.rag.ac.cn`，qdrant 向量检索），10k/天免费额度，稳定且更强（hybrid 检索 + `--min-citations` / `--categories` / `--date-from` 过滤 + 渐进式章节阅读）。代价：舍弃 sn-search-academic 的 pubmed 搜索 / wikipedia / 引用追溯（核心移植原则下可接受）。

### 降级机制

专门通道不稳定是常态（deepxiv 日额度用完返 429、reddit 已禁用、github 未认证限速、脚本缺依赖）。任一专门通道失败 / 限流 / 缺依赖时，该 query 立即回退 MCP `web-search-prime` 重试一次并 log。这保证任意专门通道挂掉都不会让研究卡死。

### 三层搜索模型

- **广度发现**：第 1 轮优先 `web` 通道摸来源地图
- **专项深挖**：后续轮按 `source_type` 调专门通道
- **原始核验**：3.2b 深读层；学术来源用 `deepxiv paper` 渐进式精读，非学术用 MCP `web-reader`；高风险事实 ≥2 独立来源交叉确认

### 未迁移部分（延续）

`scripts/orchestrator.py` 仍未随本次多源通道改造——它仍是基于 Claude CLI + meta-search 的独立命令行编排路径，不影响会话内运行时。会话内执行技能一律走 SKILL.md 的多源通道流程。
