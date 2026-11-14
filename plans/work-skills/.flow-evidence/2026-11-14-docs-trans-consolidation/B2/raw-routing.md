# B2 路由推演记录（方案 L3 · 3 条）

- 方法：独立只读 subagent（Explore），仅允许读取 `plugins/work-skills/skills/gongwen-trans/SKILL.md`，禁止读取仓库其他文件，模拟真实路由场景输出决策。
- 日期：2026-11-14
- 结果：3/3 通过

## 推演原文（subagent 输出）

1. **"转成公文 docx"** → 本技能，走 gongwen-to-docx.py。依据：frontmatter 触发词（L6 "转成公文""生成DOCX公文"）+ L9 边界句"即使用户只说'转成docx'但上下文明显是公文，也应触发"；L32 步骤 2：未明确要 PDF 默认 DOCX。形态：`python {baseDir}/scripts/gongwen-to-docx.py <input.md> -o <output.docx>`（L23）；输出未指定时输入同目录同名 .docx（L34）。

2. **"生成公文 pdf"** → 本技能，走 gongwen-to-pdf.py。依据：L8 触发词"生成公文 pdf""公文转 pdf"直接命中；L32 "用户明确要求 PDF（或 --pdf）时走 gongwen-to-pdf.py"。形态：`python {baseDir}/scripts/gongwen-to-pdf.py <input.md|input.docx> [--output <output.pdf>] [--keep-docx]`（L26）。前置：需本机 Microsoft Word（L43、L49），无 Word 按 L151 提示退出或改 DOCX。

3. **"普通说明文档转 pdf"（非公文）** → 拒绝，转交 docs-trans 技能的 md-to-pdf mode。依据："输出格式"节 L44 互斥边界句："公文的 PDF 走本技能；普通（非公文）文档转 PDF 归 docs-trans 技能的 md-to-pdf mode"。用户已明确与公文无关，命中该排除条件，本技能不处理。

## 判定

| # | 请求 | 预期 | 实际 | 判定 |
|---|---|---|---|---|
| 1 | 转成公文 docx | docx 路径（gongwen-to-docx.py） | 一致 | PASS |
| 2 | 生成公文 pdf | pdf 路径（gongwen-to-pdf.py） | 一致 | PASS |
| 3 | 普通文档转 pdf | 指 docs-trans（不进本技能） | 一致 | PASS |
