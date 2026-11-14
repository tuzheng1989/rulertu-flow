# B1 L3 路由推演记录

- 方法：独立只读 subagent 仅读取 docs-trans/SKILL.md（模拟"会话中只有该技能入口文档"视角），对 8 条用户消息逐一给出路由决策与文档依据；判定被要求完全来自文档文本，禁止常识补全。
- 日期：2026-11-14
- 结果：8/8 与预期一致。

## 推演结果

| # | 用户消息 | 预期 | 实际判定 | 依据（subagent 引述） |
|---|---|---|---|---|
| 1 | 「把这个 Word 文档转成 Markdown」 | anydoc-to-md | anydoc-to-md | 触发词分流表命中"文档转 markdown"；路由表"已有文档文件（Word/…）→ Markdown → anydoc-to-md" |
| 2 | 「抓取这个网页的内容存成 md」 | url-to-md | url-to-md | 触发词分流表命中"抓取这个网页"→ url-to-md |
| 3 | 「把我这份 markdown 笔记转成 PDF」 | md-to-pdf | md-to-pdf | 触发词"md 转 pdf"；路由表"Markdown 文件 → PDF → md-to-pdf" |
| 4 | 「这批 HTML 幻灯片合成一个 PDF」 | html-to-pdf | html-to-pdf | 触发词"HTML 转 pdf"与"幻灯片转 pdf"；路由表含幻灯片行 |
| 5 | 「分析这份 PDF 的数据」 | data-analysis（互斥边界） | data-analysis | 互斥边界第一条"对文档内容做分析、统计、提取数据 → data-analysis" |
| 6 | 「生成一份公文 docx」 | gongwen-trans（互斥边界） | gongwen-trans | 互斥边界第二条"生成符合 GB/T 9704-2012 的公文 → gongwen-trans" |
| 7 | 「帮我改写这份报告」 | write-report（互斥边界） | write-report | 互斥边界第三条"报告成稿、改写、引用审计 → write-report" |
| 8 | 「扫描版 PDF 转成可搜索文字」 | anydoc-to-md 的 OCR 路由 | anydoc-to-md（扫描版 PDF → 三级 OCR 路由） | 触发词"扫描版 pdf 转文字"；description"扫描版 PDF 三级 OCR 路由" |

## 结论

8/8 判定均能在 SKILL.md 文本中找到唯一依据（触发词命中或边界规则），无需常识补全；4 正例 + 4 边界全部命中。L3 通过。
