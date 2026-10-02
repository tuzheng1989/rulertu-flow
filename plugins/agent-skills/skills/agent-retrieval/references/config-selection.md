# 检索配置选型指南

为你的域选择检索配置。每条建议都有公开基准上的**配对消融实验**背书（SkillRet 6,006 技能池 / ToolRet 44,453 工具池，300/100 查询样本），完整数字见 agent-retrieval 仓库的 `experiments/jev-benchmark-findings.md`。

**核心结论一句话：没有普适最优配置**——两个基准选出了**不同**的赢家，解释它们的规律才是可迁移的资产。

## 配置面（六个旋钮）

| # | 旋钮 | 位置 | 成本 |
|---|------|------|------|
| 1 | 语料投影 `corpus_text` | 调用方函数 | 零 |
| 2 | doc2query 语料扩展（docgen，离线） | 索引构建期 | 一次性 LLM 批处理 |
| 3 | 向量路（`vector=` 开关与嵌入器选择） | `rank_candidates` | 一次性语料嵌入 + 每查询计算 |
| 4 | Jev 精排（System One，top-N 窗口） | 检索后调用方 | 每查询 ~5k tokens / ~1s |
| 5 | 精排窗口 N | 调用方参数 | 随 N 线性 |
| 6 | BM25 参数（k1/b、词过滤） | `BM25Index` 构造 | 零 |

内核保持无状态零依赖——以上全部是调用方决策，这是刻意设计：下面这些旋钮的取舍**无法硬编码**，只能按域消融。

## 三条定律（由证伪得出，非直觉）

**定律一：Jev 精排的增益与检索弱度成正比。**
SkillRet（docgen 后检索变强）：+13% recall@5 → docgen 后 **MRR 边际转负**。ToolRet（检索仍弱）：BM25 +24%、fusion MRR +17%。**二段精排只在一段检索最弱处回本。**

**定律二：docgen 的增益与词汇贫乏度成正比。**
SkillRet（一句话 description）：BM25 recall@5 **+51%**，单路反超 plain fusion。ToolRet（词汇丰富的 documentation JSON）：仅 +3.8%，且 fusion recall@50 反降 1.7pp（扩展噪声把长尾 gold 挤出深位）。

**定律三：向量路的存废只能靠域消融裁决。**
docgen 后 SkillRet 的向量路完全冗余（纯 BM25 全面反超 plain fusion）；ToolRet 仍需要它（docgen+fusion 比 docgen+BM25 高 16% recall@5——JSON 文档的参数语义不被口语问句覆盖）。**永远别假设，跑消融。**

两基准均证伪（不要伸手）：字段级多路 RRF（无权重合并让窄字段噪声登顶）；Jev 触发迭代检索（Jev 置信度不携带"gold 不在窗口内"信号——双基准 τ∈{0.3,0.5,0.7} 触发率全 0）。

## 决策表

| 你的处境 | 推荐栈 | 实测（SkillRet / ToolRet recall@5） |
|---|---|---|
| 默认均衡 | docgen + BM25 + Jev@窗口20 | 0.763 / 0.424 |
| 延迟受限（查询期不能调 LLM） | docgen + BM25（无 Jev） | 0.724 / 0.329 |
| 召回至上（答案必须在候选里） | docgen + fusion + Jev@窗口50 | 0.769 / 0.424（recall@10 0.834†） |
| 完全没有 LLM 预算 | docgen + BM25 | 0.724 / 0.329 |
| 基线（能做得更好就别止步于此） | plain fusion | 0.634 / 0.353 |

† ToolRet 实测；两基准是取值区间的两端，你的域落在中间。

## 组件使用要点

### doc2query（docgen）——描述短或术语重时优先
- 每资源离线生成 3–5 条口语化问句，**只拼进检索面**（doc2query-- 原则）；判定证据（`declared=` 投影）保持原字段——生成文本是召回线索，不是资源的身份声明。
- 关掉/跳过的时机：文档本就词汇丰富（ToolRet 型）且只关心深位召回。
- 模型坑：推理型模型（GLM-4.5/5.3）的 thinking token 计入 max_tokens，预算 500 会把正文**静默挤空**（finish_reason=length）——关 thinking 或预算 ≥2000。
- 生成结果与资源绑定持久化；语料变更的重嵌由内容寻址快照自动处理。

### 向量路——异构/术语密集域保留，短声明面域可砍
- 关掉是合法的生产选择（SkillRet 上 docgen+BM25 各指标反超 plain fusion）。
- 文档内嵌结构化语义（参数/schema）时必须开（ToolRet +16% recall@5）。
- 换嵌入器：改 `EmbeddingConfig` identity 即可——内容寻址快照让新旧并存、回滚零成本。

### Jev 精排——检索弱处用，检索强处跳过
- 判定措辞用"能力匹配"（"能否执行任务的具体步骤"），不是关键词相关性——能力维度是词面与向量分数都不具备的。
- 窗口 20 是操作点：50 窗口 +1pp recall 但 2 倍 token 且 −0.02 MRR（区分度稀释）。
- 已知边界：Jev 置信度 ≠ "gold 在窗口内"（任何部分相关候选都会拉高分数）——别拿它当召回失败的触发器。
- 每候选 description 截断 ~2000 字符——长尾文档会撑爆 System One 输入预算（HTTP 400）。

### Cross-encoder reranker API——通路已验证，模型需自验
- 客户端与两段臂是生产形态（稀疏对齐、退避重试、常量分检测）；已测唯一端点（paratera GLM-Rerank）恒返 1.0，判定无效。**信任何 reranker 前先看分数分布**——runner 的 `degraded_cases` 字段会替你检测。

## 为自己的域复跑验证（标准流程）

1. `run_benchmark --arm both --retriever single --k 5 10 20 50`：plain 与 docgen 语料各跑一遍，读 `recall@20/50`——那是各配置的召回天花板。
2. **定律一**：一段 recall@5 < ~0.5 → 加 Jev 窗口臂；> ~0.7 → 预期 MRR 边际为负，跳过。
3. **定律二**：声明面短/术语重 → 先 docgen（最便宜的大头）；文档本就丰富 → 预期个位数增益，看 recall@50 动不动再定。
4. **定律三**：胜出语料上直接对比 BM25 臂 vs fusion 臂；fusion ≤ BM25 → 砍向量路与嵌入预算。
5. 永远同抽样、同嵌入器身份内比较；内核确定性保证每个数字精确可复现。

## 值得记总裁的坑

- 推理模型 + 小 max_tokens = 静默空输出（finish_reason=length）。关 thinking 或抬预算。
- 网关把限流报成普通 400（不是 429）——除鉴权失败外任何 4xx 都退避重试，Flash 级模型压在 ~30 RPM 以下。
- 多路无权重 RRF 会让窄字段噪声登顶。字段级融合要打赢单路好投影，需要学习型权重。
- 同源分布警示：LLM 生成的评测查询会美化 LLM 生成的扩展（docgen）。方向可信，幅度按基准特定看待。
