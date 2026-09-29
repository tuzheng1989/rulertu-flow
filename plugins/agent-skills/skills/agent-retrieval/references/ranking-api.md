# 主入口 rank_candidates 与语料投影 - agent-retrieval

> 对应库版本：agent-retrieval 0.1.0（2026-09-25）。0.x 系列 API 可能调整，使用前核对
> `pip show agent-retrieval` 的版本与随包 CHANGELOG。

## 主入口签名

```python
from agent_retrieval import rank_candidates, CandidateHit

def rank_candidates(
    candidates: Iterable[T],
    query: str,
    *,
    corpus_text: Callable[[T], str],
    item_id: Callable[[T], str],
    item_name: Callable[[T], str] | None = None,
    vector: Embedder | None = None,
) -> list[CandidateHit[T]]
```

| 参数 | 语义 |
|------|------|
| `candidates` | 调用方**已过滤**的候选池（契约 1：先过滤后融合，库不做准入） |
| `query` | 自然语言查询；空串时 BM25 全零分，**调用方保证非空**（或自行处理空结果） |
| `corpus_text` | 语料投影：这个候选"声明了什么"，见下节 |
| `item_id` | 候选唯一 id（平局裁决、exact 判定、matched_terms 键位都靠它） |
| `item_name` | 参与 exact 全等判定；缺省只按 `item_id` 判定 |
| `vector` | 向量路注入（`Embedder` 端口）；缺省即 BM25 单路 |

返回**全量**降序 `CandidateHit` 清单，不截断（契约 2：k 截断在展示层）。空池返回 `[]`。

## 语料投影（最重要的设计决策）

`corpus_text` 是调用方对候选的"声明面"投影。库对"什么算声明面"**零建模**——惯例是拼接身份字段：

```python
def corpus_text(t: Tool) -> str:
    return f"{t.id} {t.name} {t.description}"
```

三条纪律：

1. **检索面与判定面同语料**：同一个 `corpus` 函数既喂 BM25 索引又喂向量路，检索证据与准入证据口径一致；
2. **正文是否进语料是调用方的权限决策**：索引语料一旦含正文，正文里的噪声词就获得了抬分能力——正文召回与噪声抬分是同一枚硬币的两面。需要正文召回时用 `ResourceBM25Index` 的双面结构（见 [[bm25-internals.md]]）；
3. **语料一旦定下，轻易别改**：语料文本进入向量快照的 hash（见 [[redis-snapshots.md]]），改语料 = 全量重嵌。

## 最小接入示例（L0 纯 BM25）

```python
from dataclasses import dataclass
from agent_retrieval import rank_candidates

@dataclass(frozen=True)
class Tool:
    id: str
    name: str
    description: str

tools = [
    Tool("geo-query", "Geo Query", "query geospatial data by region and time range"),
    Tool("doc-search", "Doc Search", "full-text search over uploaded documents"),
]

def corpus(t: Tool) -> str:
    return f"{t.id} {t.name} {t.description}"

hits = rank_candidates(
    tools,
    "find population data for California in 2024",
    corpus_text=corpus,
    item_id=lambda t: t.id,
    item_name=lambda t: t.name,
    # vector 缺省：BM25 单路
)
for hit in hits:
    print(hit.fused_score, hit.item.name, hit.matched_terms)
```

## 双路管线验证（MockEmbedder）

同一示例注入 `MockEmbedder()` 即走双路融合，可离线复现：

```python
from agent_retrieval import MockEmbedder

hits = rank_candidates(
    tools, "find population data for California",
    corpus_text=corpus, item_id=lambda t: t.id, item_name=lambda t: t.name,
    vector=MockEmbedder(),   # 确定性 hash 单位向量——只证明管线，不证明检索质量
)
```

生产嵌入器装配见 [[embedders.md]]。

## 排序语义

排序键：**exact 置顶 → fused 降序 → id 字典序**。

契约 4 注意：exact 置顶是**调用方契约**——库只对"你放进去的候选"排序。如果你的调用点承诺"点名 id 必中"，必须保证被点名的候选进了 `candidates`，且 id/name 与查询串归一化（NFKC + casefold）后全等。

## CandidateHit 字段

| 字段 | 类型 | 含义 |
|------|------|------|
| `item` | `T` | 原始候选对象 |
| `fused_score` | `float` | RRF 融合分：`Σ 1/(60 + rank_p)`（单路即 `1/(60+rank)`） |
| `matched_terms` | `tuple[str, ...]` | 查询实词 ∩ 该候选**语料**实词（字典序）——检索理由的证据，必须落在调用方投影的语料上 |
| `exact` | `bool` | 查询串与 id 或 name 归一化全等 |
| `bm25_score` | `float \| None` | BM25 原始分；**None = 该路缺席，区别于 0.0**（0.0 是 exact 命中的合法 BM25 值） |
| `bm25_relevance` | `float \| None` | `score / ideal_score` 规模无关相对分；**判定一律用它**（见 [[bm25-internals.md]]） |
| `cosine` | `float \| None` | 向量路余弦；None = 向量路缺席（未注入或嵌入失败降级） |

## 全量返回与展示层截断

```python
hits = rank_candidates(tools, query, corpus_text=corpus, item_id=lambda t: t.id)
top = hits[:5]          # k 截断是展示层的事（契约 2）
exact_hits = [h for h in hits if h.exact]   # 点名命中不受截断限制
```

## 降级语义

`vector` 未注入，或嵌入过程抛 `QueryEmbeddingError` 时：融合**静默**退化为 BM25 单路（RRF 形态不变），`cosine` 字段为 `None`，不外抛。嵌入失败的 Run 级冻结与观测由调用方的缓存包装层处理（见 [[run-cache.md]]）。

## 相关文档

- 判定闸（"哪些候选是真的相关"）：[[bm25-internals.md]]
- 真实嵌入器装配：[[embedders.md]]
- 8 条契约总览：[[core-concepts.md]]
