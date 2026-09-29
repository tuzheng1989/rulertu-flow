# BM25 内核与判定闸 - agent-retrieval

> 对应库版本：agent-retrieval 0.1.0（2026-09-25）。0.x 系列 API 可能调整，使用前核对
> `pip show agent-retrieval` 的版本与随包 CHANGELOG。

## 分词器

```python
from agent_retrieval import tokenize

tokenize("GeoQuery 地理查询")
# 驼峰拆分 + 中文 n-gram：('geo', 'query', '地', '理', '查', '询', '地理', '理查', '查询', ...)
```

- NFKC 归一 + 驼峰拆分（含缩写词边界）+ 标识符分隔符（`_-.:/\`）归一 + 小写；
- 英文按单词；中文每个连续片段同产**一元、二元、三元**组，四字片段另补整串；
- 无分词模型依赖，离线确定、跨进程一致（`TOKENIZER_VERSION = "bm25-natural-v3"`）。

一元组不能省：文档侧只产 n≥2 token 时，"图"这类单字中文查询必然零分、永远召回不到。代价是单字中文 token 同时也是虚词（的、于、天、关……）——长查询侧用 `substantive_term` 剔除（见下文"实词判定"），**不要从索引里删**。

## 长度归一化

`content_length(text)`：拉丁词计 1、中文按字计 1 的**语言中立**文档长度。不能直接用 `len(tokenize(text))`——中文 n-gram 展开会把同等信息量的文档撑成三倍长度，`b` 归一化会系统性压制中文条目（英文条目凭"文档短"白拿一截分）。

## BM25Index 数学内核

```python
from agent_retrieval import BM25Index

index = BM25Index([(tool, corpus_text(tool)) for tool in tools])   # k1=1.5, b=0.75（内核常数，不进配置）
scores = index.score(query)            # 按原始文档顺序返回全量分数
ideal = index.ideal_score(query)       # "理想文档"分，见下文
```

`score(query, term_filter=...)` 的 `term_filter` 只裁剪**查询**词，索引不受影响。

`ideal_score` 的关键细节（决定 relevance 刻度的正确性）：

- 查询词按**出现次数**计价不去重——否则比值随查询自身用词重复度线性抬升，啰嗦查询系统性压过简洁查询；
- 语料里没出现的词（df=0）**照常计入**（"查询大半内容本语料没有"正是不相关的证据），但按 df=1 计价——消除规模漂移。

## ResourceBM25Index：检索面与判定面分离

`rank_candidates` 内部用的是"检索面=判定面"特例。需要**正文召回**但不让正文噪声参与判定时，直接使用双面结构：

```python
from agent_retrieval import ResourceBM25Index, clearly_related

index = ResourceBM25Index(
    [(tool, f"{tool.id} {tool.name} {tool.description} {tool.manual}")],  # 检索面：含正文，管召回
    declared=lambda tool: f"{tool.id} {tool.name} {tool.description}",    # 判定面：身份字段，管"是否真相关"
)
hits = index.search(
    "帮我订一张明天去上海的机票",
    limit=10,
    identity=lambda tool: (tool.id, tool.name),
)
admissible = [h for h in hits if clearly_related(h, minimum_relevance=0.2)]
```

原理：正文长且杂，n-gram 会切出 `一张`、`的机` 这种跨词边界的噪声词——它们照样能凑够分数和重叠数（"帮我订机票"因此稳定命中推演 Flow），但**不可能**出现在资源的名称或描述里。`declared_overlap`（命中词落在声明面上的个数）就是拦这道噪声的闸。省略 `declared` 时判定面退化为检索面（无"正文"之分的场景）。

## 相关性刻度：为什么用 score / ideal_score

BM25 的 idf 是 `log(1+(N-df+0.5)/(df+0.5))`，随语料规模剧烈变化：单个命中词在 N=1 时约 0.29、N=50 时约 3.5（**12 倍**）。任何写死的绝对分数线都只在标定时那个规模上成立——资源库一长大，阈值悄悄失效、判定越来越松，**不报错，只是慢慢变差**。

`bm25_relevance = score / ideal_score` 的分子分母同随 idf 缩放，比值稳定，含义直白："这篇文档覆盖了查询证据的多大比例"。

**实测刻度**（来源项目四条 Flow 语料）：真命中 0.32–0.72，噪声命中 0.045–0.054——差一个数量级。同语料上绝对线 `1.0` 已拦不住噪声（一次"订机票"巧合命中能拿 2.29 原始分）。

注意：阈值的**绝对大小与查询长度有关**（ideal 对每个实词求和），各调用点按自己的查询形态各自标定，**不要跨调用点搬数值**。

## 判定闸 clearly_related

```python
from agent_retrieval import clearly_related

if clearly_related(hit, minimum_relevance=0.2):   # 无默认值，故意设计
    ...  # 准入/绑定
```

三个条件缺一不可（`exact` 之外）：

| 条件 | 拦截的假阳性 |
|------|-------------|
| `relevance >= minimum_relevance` | 弱相关 |
| `overlap >= 2` | 单点巧合 |
| `declared_overlap >= 1` | 正文噪声 n-gram |

**`minimum_relevance` 没有默认值是故意的**：一个能被"忘了传"的默认，等于给跨调用点搬数值开了不需要理由的口子。

## 实词判定 substantive_term

```python
from agent_retrieval import substantive_term

substantive_term("订")   # False：单字 CJK 剔除（的、于、天、关……几乎全是虚词）
substantive_term("机票")  # True
```

长查询侧剔除单字 CJK——任意两个虚词就能凑出"重叠"，会让"写一首关于秋天的诗"稳定命中推演类 Flow。索引仍保留一元组，单字中文查询的召回不受影响。

## 阈值标定流程

1. **收集真实查询样本**：目标调用点的真实查询形态（长度、语言、用词重复度）；
2. **打印 relevance 分布**：对每条样本跑检索，记录真命中与噪声的 `bm25_relevance`；
3. **取量级间隔中点**：实测参考——真命中 0.32–0.72、噪声 0.045–0.054，取 ~0.15–0.2；
4. **按调用点各自标定**：不同调用点查询形态不同（关键词式 vs 整段目标），数值不通用。

## 相关文档

- 主入口（内部已用同语料特例）：[[ranking-api.md]]
- 契约 8（相关性规模相对性）总览：[[core-concepts.md]]
