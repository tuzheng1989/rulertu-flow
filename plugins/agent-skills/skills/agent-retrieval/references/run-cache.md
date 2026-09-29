# Run 级查询缓存与降级冻结 - agent-retrieval

> 对应库版本：agent-retrieval 0.1.0（2026-09-25）。0.x 系列 API 可能调整，使用前核对
> `pip show agent-retrieval` 的版本与随包 CHANGELOG。
> 本层依赖 extras：`pip install "agent-retrieval[redis]"`（`MemoryBackend` 替身除外）。

## 动机：两个问题

1. **同 Run 重复嵌入**：一次 Agent 执行会对同一批候选发起多次检索，相同查询文本反复调嵌入 API；
2. **降级抖动**：嵌入 API 故障时，每个检索调用点都重试一遍再失败——既慢又把降级状态变成"每次调用现算"。

解法：Run 域缓存 + **首败冻结**——首次嵌入失败即写 Run 级降级标记，本 Run 内不再重试。降级决定随 Run 持久化，**重放确定**。

## 后端装配 make_backend

```python
from agent_retrieval import make_backend, MemoryBackend

backend = make_backend(
    client=redis_client,          # 同步客户端，优先于 redis_url（测试可注入替身）
    redis_url="redis://localhost:6379/0",
    key_prefix="myapp",
    retention_seconds=7 * 24 * 3600,   # 应按宿主 Run 的 Redis 保留期显式传参
)
```

- `client` 优先于 `redis_url`；两者都缺省时惰性连本机默认 Redis（**兜底路径，应显式传参**）；
- 无 Redis 的场景（单测/单机）用 `MemoryBackend()`（进程内 dict 替身）；
- 键域形状契约：`{prefix}:run:{run_id}:qvec:{sha256(text)}` 与 `{prefix}:run:{run_id}:qdegraded`；
- 后端任何失败都不阻断检索：读失败按 miss、写失败 best-effort（缓存只是省往返的旁路）。

## 装配入口 query_embedder

```python
from agent_retrieval import query_embedder

wrapped = query_embedder(
    embedder=build_embedder(config),   # 来自 [[embedders.md]]
    run_id="run-123",                  # 宿主的执行域 id，显式注入（库不读 ContextVar/tracer）
    backend=backend,
)
```

三分支返回 `None` 的语义（全部 = BM25 现状，缺席降级）：

| 分支 | 原因 |
|------|------|
| 无 `run_id` | 缓存与降级标记的键位不成立，缓存语义不可用 |
| `backend.is_degraded(run_id)` | **降级已冻结——恢复不重试**（fail-open 到重试的是"标记读不到"，不是"标记在"） |
| `embedder is None` | 本部署无向量路（宿主总开关关闭） |

## 两级缓存机制

`RunCachedEmbedder`（`query_embedder` 的返回值）的读取顺序：

1. **ContextVar 一级缓存**（进程内）：同一 Run 同文本直接命中，零往返；
2. **backend 二级缓存**（跨 worker）：换 worker 恢复时必命中；
3. **真嵌**：都未命中才调底层嵌入器，成功后回写两级。

语料路与查询路**共享同一 Run 缓存**——先被 `embed_query` 查过的文本不会再进 `embed_corpus` 的批量。

## 降级冻结

`embed_query` / `embed_corpus` 首次抛 `QueryEmbeddingError` 时（`_freeze`）：

1. 写 Run 级降级标记（与缓存同 TTL）；
2. `record_vector_degradation()` 计数（观测源）；
3. 重抛异常 → `rank_candidates` 捕获 → 本调用退化 BM25；
4. **此后该 Run 所有 `query_embedder` 直接返回 `None`**——不重试。

## 降级观测

```python
from agent_retrieval import take_degradation_count

count = take_degradation_count()   # 读走本上下文累积的降级次数（读后清零）
```

宿主把它收口进自己的观测体系，或用于判断"本次降级是否首次"（发射事件）。

## 收尾纪律

```python
clear_run_cache()   # Run 收尾必调
```

清进程内一级缓存与降级计数。ContextVar 作用域是**进程内**的——worker 复用进程处理下一个 Run 时不清就跨 Run 泄漏。

## 端到端装配链（查询侧完整代码）

```python
import logging
from agent_retrieval import (
    EmbeddingConfig, build_embedder, make_backend, query_embedder,
    rank_candidates, clear_run_cache, take_degradation_count,
)

log = logging.getLogger("myapp.retrieval")

# ① 宿主配置解析（库不读 env——这一步在你的装配层）
config = EmbeddingConfig(
    kind="api", provider="zhipu", model_name="embedding-3",
    base_url=..., api_key=...,          # 从你的配置体系解析
    dimensions=2048,
)

class RetrievalService:
    def __init__(self, tools):
        self._tools = tools
        self._embedder = build_embedder(config)          # None = 无向量路，BM25 现状
        self._backend = make_backend(redis_url=..., key_prefix="myapp")

    def search(self, run_id: str, query: str, k: int = 5):
        wrapped = query_embedder(                        # None = 无 Run 域 / 已冻结 / 无嵌入器
            embedder=self._embedder, run_id=run_id, backend=self._backend,
        )
        hits = rank_candidates(
            self._tools, query,
            corpus_text=lambda t: f"{t.id} {t.name} {t.description}",
            item_id=lambda t: t.id, item_name=lambda t: t.name,
            vector=wrapped,                              # None 也合法：BM25 单路
        )
        return hits[:k]                                  # k 截断在展示层

def run_main():
    service = RetrievalService(load_tools())
    try:
        ...  # 一次执行域内多次 service.search(run_id, ...)
    finally:
        if degraded := take_degradation_count():
            log.warning("run 向量路降级 %s 次（冻结至 run 结束）", degraded)
        clear_run_cache()                                # 防 worker 内跨 Run 泄漏
```

发布侧（候选集版本发布时嵌入语料写入快照）见 [[redis-snapshots.md]]。

## 相关文档

- 嵌入器与配置：[[embedders.md]]
- 快照发布与读取：[[redis-snapshots.md]]
- 降级语义契约（契约 7）：[[core-concepts.md]]
