# 嵌入器：端口、配置与工厂 - agent-retrieval

> 对应库版本：agent-retrieval 0.1.0（2026-09-25）。0.x 系列 API 可能调整，使用前核对
> `pip show agent-retrieval` 的版本与随包 CHANGELOG。

## Embedder 端口

```python
from agent_retrieval import Embedder, QueryEmbeddingError

class Embedder(Protocol):
    def embed_corpus(self, texts: Sequence[str]) -> list[tuple[float, ...]]: ...
    def embed_query(self, text: str) -> tuple[float, ...]: ...
```

两条端口契约：

1. **向量按惯例 L2 归一化**：cosine 消费方按单位向量点积实现；不归一会让分数按模长静默缩放、系统性扭曲排序；
2. **失败必须抛 `QueryEmbeddingError`**（不裸穿第三方异常）：融合检索面按该类型捕获并自动退化为 BM25 单路。裸穿 requests 异常 = 降级失效、检索调用点被炸。

## 配置值对象 EmbeddingConfig

```python
from agent_retrieval import EmbeddingConfig

config = EmbeddingConfig(
    kind="api",                      # "api"（OpenAI 兼容端点）或 "local"（本地 ONNX 目录）
    provider="zhipu",
    model_name="embedding-3",
    base_url="https://open.bigmodel.cn/api/paas",
    api_key="...",                   # 宿主从自己的配置体系解析后传入（库不读 env）
    dimensions=2048,                 # 0 = 端点自报维度（api）；local 由模型决定
    # model_version="",              # 版本承诺；缺省即 model_name
    # batch_size=16, timeout_seconds=20.0,
    # model_dir="",                  # local 形态的 ONNX 模型目录
)
```

`config.identity()` 返回 `(provider, model_name, model_version or model_name)` 三元组——进入向量快照 id 与快照 meta，是"固定嵌入模型与版本"承诺的落点：**换模型/版本即换快照**（见 [[redis-snapshots.md]]）。

## 工厂与三态判定

```python
from agent_retrieval import build_embedder, vector_available

embedder = build_embedder(config)     # Embedder | None
print(vector_available(config))       # "api" | "local" | "none"
```

**`build_embedder` 返回 `None` 是正常形态，不是异常**（"本部署此刻没有可用的向量路"）：

| 情形 | 返回 |
|------|------|
| api 缺 `base_url` 或 `api_key` | `None`（未配置 ≠ 故障） |
| local 依赖未装 / 模型目录缺失 | `None`（log warning 后降级） |
| 未知 kind | `None`（log warning） |

调用方拿到 `None` 就按 BM25 现状继续——整条链路不需要特判。

`vector_available` 三态：`"none"` 覆盖三种正常形态（config 为 None、api 缺凭据、local 缺 onnxruntime/transformers）——无 key/无依赖 ≠ 故障，不告警。用于启动诊断与观测。

## ApiEmbedder（extras: `[api]`）

OpenAI 兼容 `/embeddings` 端点。构造签名：

```python
ApiEmbedder(*, base_url, api_key, model_name, batch_size=16, timeout_seconds=20.0, dimensions=0)
```

- L2 归一化（部分端点返回未归一化向量）；
- 语料按 `batch_size` 批量；按返回 `index` 重排、校验条数与维度（`dimensions` 非零时）。

## LocalEmbedder（extras: `[local]`）

本地 ONNX（信创/离线路）：ONNX Runtime + transformers tokenizer，mean-pooling + L2 归一化。

```python
LocalEmbedder(*, model_dir, max_length=512)
```

⚠ 两条限制：

- **每次实例化都建 ONNX session——构造一次、全程复用**；
- **Windows ARM64 无 onnxruntime wheel**——该平台走 `[api]` 路（这正是 ONNX 依赖被隔离在 `[local]` extra 里的原因）。

## MockEmbedder（core 内置）

`shake_256` 文本 hash → 确定性**单位向量**。同文本任意两次调用逐位一致、跨进程一致，评测与测试可离线复现。嵌入质量为零：**只证明管线，不证明检索质量**。

## 自定义嵌入器（包装第三方 SDK）

实现 Protocol 两方法、把第三方异常翻译成 `QueryEmbeddingError` 的最小骨架：

```python
from agent_retrieval import Embedder, QueryEmbeddingError

class MyEmbedder:
    def __init__(self, client):
        self._client = client

    def embed_corpus(self, texts):
        try:
            vectors = self._client.embed(texts)          # 第三方批量接口
        except Exception as exc:
            raise QueryEmbeddingError(f"corpus embed failed: {exc}") from exc
        return [self._normalize(v) for v in vectors]     # L2 归一化后返回

    def embed_query(self, text):
        return self.embed_corpus([text])[0]
```

## VectorStore 端口（存储侧）

```python
from agent_retrieval import VectorStore, InMemoryVectorStore

class VectorStore(Protocol):
    def publish(self, snapshot_id: str, vectors, meta) -> None: ...   # write-once：同 id 重复发布抛 ValueError
    def load(self, snapshot_id: str) -> dict[str, tuple[float, ...]] | None: ...
    def read_meta(self, snapshot_id: str) -> dict[str, str] | None: ...
```

`InMemoryVectorStore` 是 dict 实现的进程内替身（测试/单机）；生产 Redis 实现见 [[redis-snapshots.md]]。

## 相关文档

- 向量路注入检索面：[[ranking-api.md]]
- 快照发布与读取：[[redis-snapshots.md]]
- Run 缓存包装与降级冻结：[[run-cache.md]]
