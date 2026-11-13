# 引用审计报告 WR-E07

- **审计对象**：`plans/work-skills/2026-11-13-skill-eval/samples/smoke-sample.md`（《智能编码助手对开发效率的影响：一项简要综述》）
- **执行 mode**：write-report / audit mode（标准全量审计）
- **审计日期**：2026-11-13
- **执行方式说明**：audit mode 原流程要求按批次派子代理并行联网核验、主审复核负向结论；本次执行环境无嵌套子代理可用，适配为**主审本人按分组逐一联网核验**。B 组（Zhang & Li 2023）的负向结论通过换检索式多路交叉复核（2 轮搜索引擎 + Crossref 题录库 + Crossref 期刊库）完成原设计中"子代理核验 + 主审独立复核"两道工序，核验深度不低于原流程。全程未使用内置 WebSearch/WebFetch（遵守全局网络规则，改用 MCP web-search-prime 与 webReader，API 类查询用 curl 直连）。

---

## 一、总体结论

**报告存在 1 组疑似虚构引用，且报告的核心量化证据（§2 的 47.3% / 31%）完全挂在该虚构引用上，效率论证段落实质不成立。** 其余两条引用（Vaswani et al. Transformer 论文、Anthropic Claude Code 官方文档）经核验真实可靠，仅著录完整性有欠缺。

- 虚构引用判定依据：精确标题、标题+作者组合、期刊名、ISSN 四路检索（两轮搜索引擎 + Crossref works 题录 + Crossref journals 期刊库）均查无此文、查无此刊；47.3%/31% 两个量化数字在公开网络中无任何来源支撑。
- **整体可信度评级：低。** §1、§2 两个正文段落的所有文献支撑失效；§3、§4 段落可靠。

## 二、引用项盘点（四类登记）

| # | 类型 | 条目 | 出现位置 |
|---|---|---|---|
| C1 | 参考文献表条目 + 正文内引 ×2 | Zhang, W., & Li, H. (2023). Adaptive context compression for large language model coding assistants. *Journal of AI Engineering Systems*, 12(3), 245-268 | 参考文献 1 条；§1 (Zhang & Li, 2023)、§2 (Zhang & Li, 2023) |
| C2 | 参考文献表条目 + Web 资源 URL + 具名实体 | Anthropic. Claude Code Documentation. https://docs.anthropic.com/en/docs/claude-code/overview | 参考文献 1 条；§3 正文；具名实体「Claude Code」 |
| C3 | 参考文献表条目 + 正文内引 | Vaswani, A., et al. Attention is all you need. *NeurIPS*. | 参考文献 1 条；§4 正文括号内引 |
| C4 | 具名实体 | Transformer 架构 | §4 |
| C5 | 量化数据（无独立出处，挂靠 C1） | 补全准确率提升 47.3%、任务完成时间下降 31% | §2 |

## 三、逐条判定表

### C1：Zhang & Li (2023) — Adaptive context compression for large language model coding assistants

| 维度 | 判定 | 说明 |
|---|---|---|
| 真实性 | ❌ 疑似虚构 | 四路检索均无：① 搜索"Adaptive context compression" coding assistants Zhang Li 2023 → 无匹配；② 全标题精确搜索 → 零命中；③ Crossref works 题录检索 → 最相关结果均为其他论文（无 Zhang W. & Li H. 2023 该题录）；④ Crossref journals 检索 → 不存在名为 "Journal of AI Engineering Systems" 的期刊（唯一模糊匹配为无关期刊 *Journal of AI-Driven Trade Facilitation Engineering and Single Window Systems*，贸易便利化领域） |
| 可访问性 | ❌ 无法访问 | 无 DOI、无 arXiv、无任何公开版本 |
| 著录准确性 | ❌ 无法核验 | 期刊不存在，卷期页码 12(3), 245-268 无从对应；搜索引擎与 ISSN 库中亦无该刊 |
| 论断对应 | ❌ 无原文可对照 | §1「上下文压缩与代码库语义索引是决定补全质量的两项关键机制」、§2 的 47.3%/31% 均挂靠此文，全部失去支撑 |

**证据链接**：
- Crossref 题录检索：https://api.crossref.org/works?query.bibliographic=Adaptive+context+compression+for+large+language+model+coding+assistants （返回最相关 5 条均为其他论文）
- Crossref 期刊检索：https://api.crossref.org/journals?query=Journal+of+AI+Engineering+Systems （无此刊）
- 搜索引擎两轮检索（web-search-prime，location=us）：查询词与返回结果记录见审计过程日志（本文档「六、联网行为记录」）

> 措辞严谨性说明：判定为「疑似虚构」而非绝对断言「虚构」——尽管交叉证据极强（四路独立检索无果），形式上无法证明"不存在"。但按审计分级标准（虚构引用 → P0），该条按 P0 处理。

### C2：Anthropic — Claude Code Documentation（URL）

| 维度 | 判定 | 说明 |
|---|---|---|
| 真实性 | ✅ 真实 | 官方文档页存在，标题 "Claude Code overview - Anthropic" |
| 可访问性 | ✅ 可访问 | webReader 抓取成功，返回完整 overview 内容，无需重定向 |
| 著录准确性 | ✅ 基本准确 | 作者（Anthropic）、题名（Claude Code Documentation）、URL 均正确；可选改进：官方页面题名为 "Claude Code overview"，学术引用宜补访问日期 |
| 论断对应 | ✅ 相符 | 「终端编码代理」与官方描述 "agentic coding tool that lives in your terminal" 一致；「交互式编程、代码库问答与自动化变更」对应文档的 "Build features from descriptions / Navigate any codebase / Automate tedious tasks" 三类工作流 |

**证据链接**：https://docs.anthropic.com/en/docs/claude-code/overview （实际抓取核验）

### C3：Vaswani, A., et al. — Attention is all you need

| 维度 | 判定 | 说明 |
|---|---|---|
| 真实性 | ✅ 真实 | Transformer 开山之作，8 位作者（Vaswani, Shazeer, Parmar, Uszkoreit, Jones, Gomez, Kaiser, Polosukhin），Google |
| 可访问性 | ✅ 可访问 | arXiv:1706.03762、papers.neurips.cc/paper/7181 |
| 著录准确性 | ⚠️ 有细节缺失 | **缺年份（2017）**；出处不完整（正式出处为 *Advances in Neural Information Processing Systems 30 (NIPS 2017)*，样稿只写 "NeurIPS"——该会 2017 年当年名为 NIPS，2018 年更名 NeurIPS，现代惯用可保留 NeurIPS 但必须补 2017）；官方标题大小写为 "Attention Is All You Need" |
| 论断对应 | ✅ 相符 | 「底层能力建立在 Transformer 架构之上」「注意力机制定位相关代码片段」均为该文内容的合理表述，无张冠李戴 |

**证据链接**：
- https://arxiv.org/abs/1706.03762
- https://papers.neurips.cc/paper/7181-attention-is-all-you-need （官方著录：Advances in Neural Information Processing Systems 30 (NIPS 2017)）

### C4：Transformer 架构（具名实体）

✅ 真实。源自 C3 论文（Vaswani et al., 2017），核验通过。

### C5：量化数据 47.3% / 31%（挂靠 C1）

❌ 无源。专项搜索 "code completion accuracy improvement 47.3% context compression LLM" 及相关组合词，公开网络无任何文献给出这两个数字；它们唯一出处即虚构的 C1。按「量化数据无源」幻觉模式定性，随 C1 归入 P0。

## 四、分级修正清单

### 🔴 P0（内容硬伤，必须改）

| 编号 | 位置 | 问题 | 修正建议 |
|---|---|---|---|
| P0-1 | §1 正文、§2 正文、参考文献第 1 条 | Zhang & Li (2023) 疑似虚构引用；§1 的「两项关键机制」论断与 §2 的全部量化证据挂靠其上 | 删除该引用及其支撑的全部论断；§2 的 47.3%/31% 数据无真实来源，须替换为可溯源的真实实证数据（如公开可查的编码助手效率研究）或删除该节量化论证；§1 论断改挂真实文献或改为不做文献挂靠的表述 |

### 🟡 P2（著录小误，建议改）

| 编号 | 位置 | 问题 | 修正建议 |
|---|---|---|---|
| P2-1 | 参考文献第 3 条、§4 内引 | Vaswani 条目缺年份、出处不完整 | 补全为：Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł., & Polosukhin, I. (2017). Attention is all you need. *Advances in Neural Information Processing Systems 30* (NIPS 2017). |

### 🟢 P3（措辞/链接，可选改）

| 编号 | 位置 | 问题 | 修正建议 |
|---|---|---|---|
| P3-1 | §4 正文 | 内引格式不规范：把完整著录塞进正文括号 "(Vaswani, A., et al. Attention is all you need. NeurIPS.)" | 改为作者-年份规范内引 (Vaswani et al., 2017)，完整著录留在参考文献表 |
| P3-2 | 参考文献第 2 条 | Claude Code 文档条目可更精确 | 题名可补官方页题 "Claude Code overview"，并加访问日期（如 (accessed 2026-11-13)） |

## 五、确认可靠的关键引用

- **Anthropic Claude Code 官方文档（C2）**：实际抓取核验，可访问、著录正确、正文论断逐条相符。§3 工具生态段落的承重引用可靠。
- **Vaswani et al. Transformer 论文（C3、C4）**：真实存在、可访问，§4 理论基础段落的论断与原文相符（仅著录不全，属 P2 小误，不影响可靠性）。

## 六、联网行为记录（如实记录）

| 序号 | 工具 | 查询/URL | 结果 |
|---|---|---|---|
| 1 | web-search-prime（us） | "Adaptive context compression" coding assistants Zhang Li 2023 | 无匹配文献（返回均为其他主题） |
| 2 | web-search-prime（us） | "Journal of AI Engineering Systems" journal | 无此刊（返回名称相近的他刊） |
| 3 | web-search-prime（us） | Vaswani "Attention is all you need" NeurIPS 2017 paper | 确认真实：arXiv:1706.03762、NIPS 2017 |
| 4 | web-reader | https://docs.anthropic.com/en/docs/claude-code/overview | 抓取成功，完整 overview 内容 |
| 5 | web-reader | Semantic Scholar API（%20 编码 URL） | 失败（MCP -400 URL 格式拒绝），改走 Crossref |
| 6 | web-search-prime（us） | "Adaptive context compression for large language model coding assistants"（全标题精确） | 零命中 |
| 7 | web-search-prime（us） | "Journal of AI Engineering Systems" ISSN | 无此刊 |
| 8 | web-search-prime（us） | code completion accuracy improvement 47.3% context compression LLM | 无任何来源支撑 47.3% |
| 9 | web-reader | Crossref API ×2 | 失败（MCP -500 网络错误），改用 curl 直连 |
| 10 | curl | https://api.crossref.org/works?query.bibliographic=Adaptive+context+compression...&rows=5 | 成功；最相关 5 条均非该文 |
| 11 | curl | https://api.crossref.org/journals?query=Journal+of+AI+Engineering+Systems（首次带 select 参数报参数错误，去掉后成功） | 成功；无此刊 |

全程未调用内置 WebSearch/WebFetch。

## 七、样稿改动声明

**本次审计未对 `samples/smoke-sample.md` 做任何修改**（audit mode 边界：只出结论与建议，不自动改报告）。本报告是本次任务唯一新增产物。

---

**结尾问询**：是否需要按上述分级清单应用修正？（修正仅会在你明确确认后进行，且按硬性约束本样稿为评测样本，默认保持原样不动。）
