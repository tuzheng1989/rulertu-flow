# 引用审计报告（audit mode 冒烟）

- 审计对象：`smoke-sample.md`（同目录，B2 验收 4 冒烟样稿）
- 执行依据：`plugins/work-skills/skills/write-report/modes/audit.md`（标准全量审计流程）
- 执行日期：2026-11-13
- 核验方式：核验子代理（model: sonnet，web_search + webReader 实际联网）+ 主审对负向结论独立联网复核，全程禁止凭记忆作答
- 样稿哈希（审计前）：f79bdcb708131b67b6d11cbc95a1c5c1583aa4b0

## 总体结论

样稿存在 **1 条确定性虚构引用**（论文与载体期刊均不存在，且量化数据挂靠其上无任何出处），属内容硬伤；另检出 **1 条真实文献著录不完整**（缺年份/卷次/页码）与 **1 条真实网页引用著录小瑕疵**。整体可信度评级：**不可直接发布**——核心量化证据（47.3%/31%）建立在虚构引用之上，必须删除或替换后重新成稿。

## 逐条判定表

盘点登记：正文内引 2 处（均指向 R1）、参考文献表条目 3 条、Web 资源 URL 1 条、具名实体 2 个（Claude Code、Transformer/NeurIPS）。共 3 个引用项，全部判定如下。

| # | 引用项 | 真实性 | 可访问性 | 著录准确性 | 论断对应 | 证据链接 |
|---|---|---|---|---|---|---|
| R1 | Zhang, W., & Li, H. (2023). Adaptive context compression for large language model coding assistants. *Journal of AI Engineering Systems*, 12(3), 245-268 | ❌ 疑似虚构（论文查无） | ❌ 无 DOI/arXiv/期刊页任何信息源 | ❌ 载体期刊不存在，卷期页码无从成立 | ❌ 量化数据 47.3%/31% 无源 | 精确标题检索零命中（相近命中均为他作：arxiv.org/list/cs.AI/2025-07、arxiv.org/abs/2610.21893、aclanthology.org/2026.findings-emnlp.1614.pdf）；期刊名精确检索两次返回空，名称相近期刊（aise.cultechpub.com、kiwiresearchjournals.com）均不同名 |
| R2 | Anthropic. Claude Code Documentation. https://docs.anthropic.com/en/docs/claude-code/overview | ✅ 真实 | ✅ 可访问（实抓成功，页面标题 Claude Code overview - Anthropic） | ⚠️ 题名为描述性（页面实际标题 Claude Code overview），未注访问日期 | ✅ 相符（页面明确列出交互式编程、代码库问答、自动化变更等工作流） | docs.anthropic.com/en/docs/claude-code/overview（实抓） |
| R3 | Vaswani, A., et al. Attention is all you need. *NeurIPS*. | ✅ 真实（Transformer 奠基作，被引超 28 万） | ✅ NIPS 官方页/官方 PDF/arXiv 均可访问 | ⚠️ 缺 7 位作者、年份、会议全称、卷次、页码 | ❓ 样稿正文未给该条具体论断；正文以其支撑压缩类论述属宽泛引申，建议核查 | papers.nips.cc/paper_files/paper/2017/hash/3f5ee243547dee91fbd053c1c4a845aa-Abstract.html（8 位作者 metadata、卷 30）；dblp.org/rec/conf/nips/VaswaniSPUJGKP17（页码 5998-6008）；arxiv.org/abs/1706.03762 |

主审复核记录：R1 的"虚构"定性经主审独立联网复核确认（精确标题检索与期刊名检索均为零/无同名命中），与子代理结论一致；R1 属虚构 + 量化数据无源双模式，符合 audit.md「常见失败」中"虚构框架/术语名"与"量化数据无源"两条高频幻觉特征（常见姓氏组合 + 听起来合理的期刊名 + 过于精确的百分比）。

## 分级修正清单

### 🔴 P0（内容硬伤，必须改）

1. **删除或替换 R1 整条引用**（正文段 1、段 2 两处内引 + 参考文献表第 1 条）。论文与期刊均不存在。
2. **删除段 2 的量化数据**"补全准确率提升 47.3%，平均任务完成时间下降 31%"——挂在虚构引用上，属无源数据；若需保留量化论证，须替换为可溯源的真实文献数据。

### 🟡 P2（著录小误，建议改）

3. **补全 R3 著录**：缺年份（2017）、会议全称（Advances in Neural Information Processing Systems 30 / NIPS 2017）、卷次（30）、页码（5998-6008）。规范著录示例（APA 7）：Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł., & Polosukhin, I. (2017). Attention is all you need. In *Advances in Neural Information Processing Systems 30 (NIPS 2017)* (pp. 5998-6008). Curran Associates, Inc.

### 🟢 P3（措辞/链接，可选改）

4. **R2 题名与访问日期**：题名可改为页面实际标题 Claude Code overview，并补访问日期（2026-11-13）以保证可回溯性。

## 确认可靠的关键引用

- R2（Claude Code 官方文档 URL）：实体真实、可访问、论断相符——样稿的工具生态论述承重引用经核实属实。
- R3（Attention Is All You Need）：论文真实存在、多源可访问——理论基础的承重引用经核实属实，仅需著录补全。

## 结尾问询

以上为分级审计结论与修正建议，**未改动被审计样稿 smoke-sample.md**。是否应用修正？确认后可逐条落地（P0 建议优先处理）。
