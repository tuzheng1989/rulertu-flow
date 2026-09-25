---
name: agent-retrieval
description: agent-retrieval 检索库使用指南，支持接入实施（纯 BM25 / 真实嵌入 / Redis 向量快照 / 运行期缓存四层深度）与排查调优两个场景，当用户提到 "agent-retrieval"、"rank_candidates"、"BM25 向量融合"、"RRF 融合检索"、"候选资源检索"、"clearly_related" 时触发。覆盖确定性 BM25 内核、双路 RRF 融合、相关性判定闸、嵌入器装配、write-once 向量快照与 Run 级查询缓存。
---

# agent-retrieval - 确定性双路融合检索使用指南

本技能提供 agent-retrieval 库（确定性 BM25 + 向量双路 RRF 融合检索内核）的完整使用指南。核心理念一句话：**"检索当参谋，调用方做决定"**——库负责排序与注解，准入、绑定、截断全部留在调用方。

## 场景识别

本技能会自动检测用户需求并进入对应场景：

### 场景 A：接入实施（按深度分层）

**触发条件：**
- 用户提到"接入 / 使用 agent-retrieval"、"给工具/技能/Flow/文档加自然语言检索"、"做候选排序/资源发现"
- 正在搭建新的检索调用点（Agent 工具选择、技能路由、文档发现等）

**工作流程：**
1. **确认行为契约** → 首先参考 [[references/core-concepts.md]] 的 8 条契约——它们决定调用方义务（先过滤后融合、exact 命中要喂进检索、k 截断在展示层）
2. **定义候选模型与语料投影** → [[references/ranking-api.md]]：corpus_text 惯例（拼 id/name/description 身份字段）、检索面=判定面
3. **需要"是否相关"判定闸时** → [[references/bm25-internals.md]]：bm25_relevance 刻度 + clearly_related + minimum_relevance 标定
4. **按接入深度分层推进**（见下方路由表）
5. 请求用户确认

**接入深度路由表：**

| 深度 | 适用条件 | 参考文档 |
|------|---------|---------|
| L0 纯 BM25 | 零依赖快速起步、无嵌入预算、检索面即身份字段 | [[references/ranking-api.md]] |
| L1 真实嵌入 | 有 API 或本地嵌入资源，提升语义召回 | [[references/embedders.md]] |
| L2 Redis 快照 | 发布侧避免重复嵌入整批语料 | [[references/redis-snapshots.md]] |
| L3 运行缓存 | Run 内去重查询嵌入 + 降级冻结 | [[references/run-cache.md]]（含端到端装配链） |

### 场景 B：排查与契约理解

**触发条件：**
- 结果不符合预期（cosine 全 None、排序意外、matched_terms 为空、绑定过多噪声候选）
- 询问阈值怎么定、为什么全量返回、降级为什么不报错、确定性如何保证
- 理解或审查检索调用点是否符合 8 条行为契约

**工作流程：**
1. **契约类疑问**（截断、确定性、None vs 0.0、降级不抛）→ [[references/core-concepts.md]]
2. **分数/阈值类**（bm25_relevance 标定、真命中与噪声的实测刻度）→ [[references/bm25-internals.md]]
3. **向量路缺席类**（cosine 为 None）→ [[references/embedders.md]]（未注入/构建返回 None）→ [[references/run-cache.md]]（降级已冻结）
4. **重复嵌入类** → 发布侧 [[references/redis-snapshots.md]] / 查询侧 [[references/run-cache.md]]
5. 给出结论与修正代码

---

## 文档参考流程

| 阶段 | 任务 | 主要参考 |
|------|------|---------|
| 一：理解契约 | 明确库的边界与调用方义务 | [[references/core-concepts.md]] |
| 二：搭检索面 | 候选模型 + corpus_text + 主入口 | [[references/ranking-api.md]] |
| 三：加判定闸 | relevance 刻度 + clearly_related + 阈值标定 | [[references/bm25-internals.md]] |
| 四：升级向量路 | 按 L1→L3 深度逐层接入 | [[references/embedders.md]] → [[references/redis-snapshots.md]] → [[references/run-cache.md]] |

---

## 核心概念速查表

### 主入口签名

```python
rank_candidates(
    candidates,              # Iterable[T]：调用方已过滤的候选池
    query,                   # str：自然语言查询（调用方保证非空）
    *,
    corpus_text,             # Callable[[T], str]：语料投影（检索面=判定面）
    item_id,                 # Callable[[T], str]
    item_name=None,          # Callable[[T], str] | None：参与 exact 全等判定
    vector=None,             # Embedder | None：缺省即 BM25 单路
) -> list[CandidateHit[T]]   # 全量降序，不截断
```

### CandidateHit 字段

| 字段 | 含义 |
|------|------|
| `item` | 原始候选对象 |
| `fused_score` | RRF 融合分 |
| `matched_terms` | 查询实词 ∩ 该候选语料实词（检索理由证据） |
| `exact` | 查询串与 id/name 归一化全等 |
| `bm25_score` | BM25 原始分；**None=该路缺席 ≠ 0.0**（0.0 是 exact 命中的合法真值） |
| `bm25_relevance` | score/ideal_score 规模无关相对分（判定一律用它） |
| `cosine` | 向量路余弦分；None=向量路缺席 |

### 判定闸（调用方职责）

```python
clearly_related(hit, *, minimum_relevance=...)   # 无默认值，各调用点自行标定
# exact 或（relevance ≥ min 且 overlap ≥ 2 且 declared_overlap ≥ 1）
```

### 8 条行为契约

| # | 契约 |
|---|------|
| 1 | 先过滤后融合——准入是调用方的 job |
| 2 | k 截断输出，不截断排序（`hits[:k]` 在展示层做） |
| 3 | cosine ≤ 0 无证据，不占向量排名位 |
| 4 | exact 置顶是调用方契约——exact 命中要喂进至少一路 |
| 5 | 缺席路 = None，不是 0.0 |
| 6 | 确定性平局裁决——固定累加顺序 + id 字典序 |
| 7 | 降级不抛——嵌入失败/快照缺失退 BM25 |
| 8 | 相关性是规模相对的——用 score/ideal_score，不用原始分 |

### 安装矩阵

```bash
pip install agent-retrieval              # core 零依赖
pip install "agent-retrieval[api]"       # + OpenAI 兼容嵌入（requests）
pip install "agent-retrieval[redis]"     # + Redis 快照与运行缓存
pip install "agent-retrieval[local]"     # + 本地 ONNX（Windows ARM64 不可用）
```

Python ≥ 3.10，纯 Python 轮子。库纪律：不读环境变量/配置文件/ContextVars，一切经构造参数注入。

---

## 完整参考文档索引

### 核心文档（按使用顺序）

1. [[references/core-concepts.md]] - **优先参考**：库定位、分层架构、四大理念、8 条行为契约
2. [[references/ranking-api.md]] - **优先参考**：主入口 rank_candidates 与语料投影

### 分层接入文档

| 文档 | 说明 |
|------|------|
| [[references/embedders.md]] | L1：Embedder 端口、EmbeddingConfig、build_embedder 工厂、三态判定 |
| [[references/redis-snapshots.md]] | L2：write-once 向量快照发布编排与读取降级 |
| [[references/run-cache.md]] | L3：Run 级查询缓存、降级冻结、端到端装配链 |

### 内核细节文档

| 文档 | 说明 |
|------|------|
| [[references/bm25-internals.md]] | BM25 数学内核、检索面/判定面分离、判定闸与阈值标定 |

### 官方资源

- PyPI：`agent-retrieval`（README 与 CHANGELOG 随包分发）
