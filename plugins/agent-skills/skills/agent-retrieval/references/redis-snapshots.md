# Redis 向量快照：发布与读取 - agent-retrieval

> 对应库版本：agent-retrieval 0.1.0（2026-09-25）。0.x 系列 API 可能调整，使用前核对
> `pip show agent-retrieval` 的版本与随包 CHANGELOG。
> 本层依赖 extras：`pip install "agent-retrieval[redis]"`。接口全异步。

## 动机：一次嵌入、多方读取

发布侧（候选集版本发布时）把整批语料嵌入一次、写入 Redis；查询侧只读不嵌。内容寻址保证复用：

**同 owner 版本 + 同嵌入器 + 同语料 → 同快照 id → 重复发布仅续 TTL，零重嵌。**

任一因子变化（候选集内容、换嵌入模型/版本、语料文本）→ 新 id → 全量重嵌——这正是期望行为。

## 快照身份三因子

```python
from agent_retrieval import corpus_hash, vector_snapshot_id

# 语料 hash：{kind:id → text} 映射；键序固定排序，拼接序确定
chash = corpus_hash({f"tool:{t.id}": corpus_text(t) for t in tools})

snapshot_id = vector_snapshot_id(
    owner_version="resources-v42",            # 你的候选集版本号（宿主语义）
    identity=config.identity(),               # (provider, model_name, model_version)
    corpus_hash=chash,
)
```

## 存储构造

```python
from agent_retrieval import RedisVectorStore

store = RedisVectorStore(
    redis_url="redis://localhost:6379/0",   # 或 client= 复用调用方已有异步客户端（优先）
    key_prefix="myapp",                     # 键域前缀，缺省 "ar"
    # lock_lease_seconds=300,               # single-flight 锁租约（崩溃随 PX 自动释放）
)
```

- `client` 优先于 `redis_url`：传入即复用（连接生命周期归调用方，测试可注入替身）；
- 只传 `redis_url` 时惰性建连（`decode_responses=True`），由 `await store.aclose()` 关闭；
- 两者都缺省抛 `ValueError`。

## 发布编排（完整可运行版）

write-once：发布前 `read_meta` 预检（发布热路径可能高频触发，必须只读元数据）；缺失才在 single-flight 锁内嵌入写入。

```python
RETENTION = 7 * 24 * 3600   # 与宿主的候选集版本保留期同参

async def publish_snapshot(store, config, owner_version, corpus_texts):
    """corpus_texts: {"tool:geo-query": "geo-query Geo Query ...", ...}"""
    snapshot_id = vector_snapshot_id(
        owner_version=owner_version,
        identity=config.identity(),
        corpus_hash=corpus_hash(corpus_texts),
    )

    # 1. write-once 预检：快照已在 → 只续 TTL，零重嵌
    if await store.read_meta(snapshot_id) is not None:
        await store.extend_ttl(snapshot_id, owner_version, RETENTION)
        return snapshot_id

    # 2. single-flight 锁：多进程并发发布时只有一个真正嵌入
    if not await store.acquire_lock(snapshot_id):
        return snapshot_id   # 别的进程正在发布；查询侧稍后自然读到

    try:
        # 3. 锁内：嵌入 → 写入（向量 hash + meta + owner_version 指针，写入即挂 TTL）
        keys = list(corpus_texts)
        vectors = await asyncio.gather(
            asyncio.to_thread(embedder.embed_corpus, [corpus_texts[k] for k in keys])
        )
        await store.publish_vectors(
            snapshot_id=snapshot_id,
            owner_version=owner_version,
            vectors=dict(zip(keys, vectors[0])),
            meta={"embedding_provider": config.provider, "dim": str(config.dimensions)},
            retention_seconds=RETENTION,
        )
    finally:
        # 4. 无论成败释放锁（崩溃场景由 PX 租约过期兜底释放）
        await store.release_lock(snapshot_id)
    return snapshot_id
```

要点：

- `acquire_lock` 是 Redis SET NX + PX，锁粒度 = snapshot_id；
- `extend_ttl` 是同 id 重复发布的**唯一**动作（向量 + meta + 指针三键同续）；
- 嵌入器是同步接口，异步宿主里用 `asyncio.to_thread` 包装（示例中的 `embedder` 来自 [[embedders.md]] 的 `build_embedder`）。

## 键域契约

四个键模板是存储契约（缺省前缀 `ar`，与来源项目生产键域逐字节一致）：

| 键 | 内容 |
|----|------|
| `{prefix}:registry:vector:{snapshot_id}` | hash：`{kind}:{id}` → 向量 JSON |
| `{prefix}:registry:vector-meta:{snapshot_id}` | 元数据字段表 |
| `{prefix}:registry:vector-of:{owner_version}` | owner_version → snapshot 指针 |
| `{prefix}:registry:vector-lock:{snapshot_id}` | single-flight 锁（SET NX） |

## 读取与降级

```python
vectors = await store.load_snapshot_vectors(
    "resources-v42",
    ["tool:geo-query", "tool:doc-search"],   # {"kind}:{id}" 子集
)
# {} → 快照缺席（发布期嵌入失败 / TTL 过期 / Redis 异常）→ 向量路缺席，降级 BM25
```

三种异常情形（快照缺席、TTL 过期、Redis 不可用）**统一返回空 dict**（log warning）——查询侧绝不阻塞检索。

## 与检索面接法

读出的向量包一层 `Embedder` 注入 `rank_candidates`：

```python
class SnapshotEmbedder:
    """查询路真嵌、语料路走快照的最小装配。"""
    def __init__(self, query_embedder, corpus_vectors, corpus_texts):
        self._query = query_embedder
        self._by_text = {corpus_texts[k]: v for k, v in corpus_vectors.items()}

    def embed_corpus(self, texts):
        return [self._by_text[t] for t in texts]          # 快照缺席的文本按调用方降级策略处理

    def embed_query(self, text):
        return self._query.embed_query(text)
```

缺快照的条目会缺向量——最简做法是快照为空时整条向量路不注入（`vector=None`），与"缺席降级"语义连续。

## 相关文档

- 嵌入器与配置：[[embedders.md]]
- 查询侧缓存（避免同 Run 重复嵌查询）：[[run-cache.md]]
- 主入口：[[ranking-api.md]]
