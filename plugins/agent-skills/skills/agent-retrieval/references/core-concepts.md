# 核心概念与行为契约 - agent-retrieval

> 对应库版本：agent-retrieval 0.1.0（2026-09-25）。0.x 系列 API 可能调整，使用前核对
> `pip show agent-retrieval` 的版本与随包 CHANGELOG。

## 库定位与出身

agent-retrieval 是**确定性 BM25 + 向量双路 RRF 融合**检索内核，面向 Agent 资源发现场景——对一组候选资源（工具、技能、Flow、Agent、文档……）做自然语言检索。

它从生产多 Agent 平台的共享检索中间件抽出（BM25 路 + GLM-Embedding-3 向量路，经三臂离线评估门禁验证），是带一套**检索纪律**的库，不是通用搜索引擎：

- Agent 检索里，坏匹配会**静默错派任务**（把任务路由给错误工具/技能），所以纪律比功能重要；
- 嵌入、快照、缓存都是**可选升级**，任何一环缺席都干净退化为纯 BM25。

## 分层架构

| 模块 | 依赖 | 内容 |
|------|------|------|
| `agent_retrieval.core` | **仅标准库**（CI 强制） | BM25 内核、RRF 融合、端口协议、资源索引、`rank_candidates` 主入口 |
| `agent_retrieval.embedders` | extras `[api]` / `[local]` | OpenAI 兼容 API 嵌入器、本地 ONNX 嵌入器、配置与工厂 |
| `agent_retrieval.stores` | extras `[redis]` | write-once 向量快照的 Redis 存取（全异步） |
| `agent_retrieval.run` | extras `[redis]` | Run 级查询缓存与降级冻结 |

重实现经 PEP 562 惰性导出：`from agent_retrieval import EmbeddingConfig` 只在真正取属性时才 import 对应模块——没装 extras 的环境里，core 照常工作，懒导出缺依赖时干净报错。

## 四大理念

### 1. 融合排序，而非阈值过滤

内核返回**带注解、确定性排序**的候选清单；准入/绑定决策留在调用方。"检索建议，调用方决定"——检索永远不能把一个调用方没放进的候选排进来，也不能替调用方决定绑定哪个。

### 2. 构造上确定性

相同输入 → 位级相同输出：固定累加顺序（先 BM25 后向量）、id 字典序平局裁决、无隐藏随机性。回放安全——重放一次执行，检索结果逐位一致。

### 3. 优雅降级，永不抛

嵌入失败、快照缺席、缓存故障——全部**静默**塌缩为 BM25 单路。向量是*升级*，不是*依赖*：没有向量路的系统与有向量路的系统用同一套代码，前者的融合形态退化为单路 RRF（`fused = 1/(K+rank)`），连续不突变。

### 4. core 零依赖

`agent_retrieval.core` 只 import 标准库（CI 强制检查）。检索数学不该拖着一串第三方依赖进每个宿主环境。

## 8 条行为契约

违反这些是检索系统悄悄腐烂的方式，内核替调用方守住：

| # | 契约 | 违反后果 | 源码落点 |
|---|------|---------|---------|
| 1 | **先过滤后融合**——准入是调用方的 job | 检索把不合格候选排进视野 | `rank_candidates` 不做准入 |
| 2 | **k 截断输出，不截断排序** | 内核内截断丢失完整视野 | 返回全量清单，`hits[:k]` 调用方做 |
| 3 | **cosine ≤ 0 无证据** | 非正余弦占排名位、挤掉正证据 | `fuse` 内滤除，`in_vector=False` |
| 4 | **exact 置顶是调用方契约** | 调用方以为"点名必中"却没喂进检索 | 排序键 `(not exact, -fused, id)`，但只看你放进的候选 |
| 5 | **缺席路 = None，不是 0.0** | 缺证据与零证据混淆（0.0 是 exact 命中的合法 BM25 值） | `CandidateHit.bm25_score: float \| None` |
| 6 | **确定性平局裁决** | 同输入两次结果不同，回放失败 | 固定顺序累加 + id 字典序 |
| 7 | **降级不抛** | 嵌入 API 抖动炸掉整个检索调用 | `QueryEmbeddingError` 捕获后退 BM25 |
| 8 | **相关性是规模相对的** | 写死的分数线随语料增长悄悄失效（不报错，只是慢慢变差） | `bm25_relevance = score / ideal_score` |

## 库纪律

包**永不读取**环境变量、配置文件、调用方的 ContextVars。一切经构造参数注入：

- 凭据：宿主从自己的配置体系（yaml/env/密钥管理）解析后构造 `EmbeddingConfig` 传入；
- `run_id`：宿主的执行模型概念，由装配层显式注入；
- 向量路总开关：宿主概念——开关关闭时宿主传 `embedder=None` 即得 BM25 现状，而不是传 flag 进库。

## 安装矩阵与平台限制

```bash
pip install agent-retrieval              # core only（stdlib，零依赖）
pip install "agent-retrieval[api]"       # + OpenAI 兼容嵌入（requests）
pip install "agent-retrieval[redis]"     # + Redis 向量快照存储与运行缓存
pip install "agent-retrieval[local]"     # + 本地 ONNX 嵌入
```

- Python ≥ 3.10，wheel 纯 Python、平台无关；
- ⚠ `[local]` extra（ONNX）**无 Windows ARM64 wheel**——该平台走 `[api]` 路；
- `LocalEmbedder` 每次实例化都建 ONNX session——**构造一次、全程复用**。

## 公开 API 总览（37 个符号）

| 模块 | 符号 | 备注 |
|------|------|------|
| core（急切导出） | `rank_candidates`, `CandidateHit` | 主入口（见 [[ranking-api.md]]） |
| core | `BM25Index`, `tokenize`, `ideal_score`, `content_length`, `BM25Score` | BM25 数学内核（见 [[bm25-internals.md]]） |
| core | `fuse`, `BM25Hit`, `VectorHit`, `FusedHit`, `RRF_K` | RRF 融合 |
| core | `ResourceBM25Index`, `ResourceHit`, `substantive_term`, `clearly_related` | 判定闸（见 [[bm25-internals.md]]） |
| core | `Embedder`, `VectorStore`, `QueryEmbeddingError`, `MockEmbedder`, `InMemoryVectorStore` | 端口与替身（见 [[embedders.md]]） |
| embedders（懒导出，`[api]`/`[local]`） | `EmbeddingConfig`, `ApiEmbedder`, `LocalEmbedder`, `build_embedder`, `vector_available` | 见 [[embedders.md]] |
| stores（懒导出，`[redis]`） | `RedisVectorStore`, `corpus_hash`, `vector_snapshot_id` | 见 [[redis-snapshots.md]] |
| run（懒导出，`[redis]`） | `query_embedder`, `RunCachedEmbedder`, `QueryCacheBackend`, `MemoryBackend`, `make_backend`, `clear_run_cache`, `record_vector_degradation`, `take_degradation_count` | 见 [[run-cache.md]] |

## 相关文档

- 主入口与语料投影：[[ranking-api.md]]
- 判定闸与阈值标定：[[bm25-internals.md]]
- 嵌入器装配：[[embedders.md]]
- 向量快照：[[redis-snapshots.md]]
- 运行缓存与端到端装配链：[[run-cache.md]]
