---
name: docs-trans
description: 文档转换单一入口，四个 mode 按转换方向分流——已有文档转 Markdown（anydoc-to-md：Word/PPT/Excel/ODF/RTF/EPUB/CSV/PDF，扫描版 PDF 三级 OCR 路由）、网页转 Markdown（url-to-md：Chrome CDP 渲染 + Defuddle/Legacy 双管道 + YouTube 字幕）、Markdown 转 PDF（md-to-pdf：Mermaid/PlantUML/HTML 图表/SVG 预渲染 + 中文排版 + 锚链）、HTML 转 PDF（html-to-pdf：自动推断纸张比例、幻灯片合成、多文件合并）。当用户说"把 docx/pdf/pptx/xlsx 转成 markdown"、"文档转 md"、"转成 md"、"扫描版 pdf 转文字"、"OCR 这本书/文档"→ anydoc-to-md；"URL 转 markdown"、"网页转 md"、"抓取网页"、"保存这个链接的内容"→ url-to-md；"md 转 pdf"、"markdown 转 pdf"、"导出 pdf"、"Mermaid 图转 pdf"、"打印这个文档"→ md-to-pdf；"HTML 转 pdf"、"幻灯片转 pdf"、"slides 转 PDF"、"合并这些 PDF"→ html-to-pdf。互斥边界：对文档内容做分析/提取数据归 data-analysis；生成公文（GB/T 9704）归 gongwen-trans；报告成稿与改写归 write-report。
---

# docs-trans — 文档转换工作台

文档格式转换的单一入口：按"输入 → 输出"方向路由到四个自包含 mode，命中后读取 `modes/<mode>.md` 并严格按该文档执行。

## 转换方向路由

| 输入 | 输出 | mode | 一句话定位 |
|------|------|------|-----------|
| 已有文档文件（Word/PPT/Excel/ODF/RTF/EPUB/CSV/PDF） | Markdown | `modes/anydoc-to-md.md` | anydoc 引擎（纯 Rust）亚 5ms 转文本型文档；扫描版 PDF 三级 OCR 路由（Windows OCR / DeepSeek-OCR / Claude 视觉）+ 幻觉清洗 + 断点续传 |
| URL / 网页 | Markdown | `modes/url-to-md.md` | Chrome CDP 渲染抓取，Defuddle/Legacy 双转换管道，YouTube 字幕提取，媒体可本地化 |
| Markdown 文件 | PDF | `modes/md-to-pdf.md` | Mermaid/PlantUML/HTML 图表/SVG 预渲染为 PNG 嵌入，中英文混排、目录、内部锚链 |
| HTML（单文件/目录/通配符，含幻灯片） | PDF | `modes/html-to-pdf.md` | 从设计尺寸自动推断纸张比例，保持布局与背景色，多文件按序合并 |

## 触发词分流

| 用户表述 | 路由 |
|---------|------|
| "转成 md"、"文档转 markdown"、"扫描版 pdf 转文字"、"OCR 这本书" | anydoc-to-md |
| "URL 转 markdown"、"网页转 md"、"抓取这个网页" | url-to-md |
| "md 转 pdf"、"导出 pdf"、"Mermaid 转 pdf"、"打印这个文档" | md-to-pdf |
| "HTML 转 pdf"、"幻灯片转 pdf"、"slides 转 PDF" | html-to-pdf |

## 未覆盖方向

上表未列的转换方向（如 md → docx、html → md）默认不支持，不进入本技能路由——唯一例外是生成公文（GB/T 9704），归 `gongwen-trans`。

## 互斥边界（不做）

- 对文档**内容**做分析、统计、提取数据 → `data-analysis`（本技能只做格式转换，不理解内容语义）
- 生成符合 GB/T 9704-2012 的公文 → `gongwen-trans`
- 报告成稿、改写、引用审计 → `write-report`（其导入引擎内部调用本文档的转换能力）

## scripts 目录索引

四个引擎子目录与 mode 一一对应，mode 文档内的脚本路径均相对 `modes/` 解析：

| 子目录 | 引擎 | 关键脚本 |
|--------|------|---------|
| `scripts/anydoc/` | 文档 → MD + OCR 路由 | `route_ocr.py`（扫描版路由评分）、`ocr_pdf.py`（DeepSeek-OCR 管线）、`clean_hallucinations.py`（幻觉八形态清洗）、`winocr.ps1`（Windows OCR） |
| `scripts/url/` | 网页 → MD | `main.ts`（bun CLI 入口；依赖见该目录 `package.json` + `bun.lock`，首次使用先 `bun install`） |
| `scripts/mdpdf/` | MD → PDF | `md_to_pdf.py`（主转换）、`diagram_renderer.py`（图表预渲染）；`assets/`（custom.css、example.md、md-to-pdf.config.json） |
| `scripts/htmlpdf/` | HTML → PDF | `convert.py`（主转换）、`merge.py`（PDF 合并） |

其他资产：`references/mermaid-syntax.md`（Mermaid 语法参考，md-to-pdf 用）；`evals/evals.json`（html-to-pdf 评测集）。

## 依赖速查

| mode | 依赖 |
|------|------|
| anydoc-to-md | `anydoc` CLI（或回退 `npx -y @firecrawl/anydoc`）；OCR 各引擎依赖见 mode 文档 |
| url-to-md | `bun`（或回退 `npx -y bun`）+ Chrome；首次使用在 `scripts/url/` 执行 `bun install` |
| md-to-pdf | `pip install playwright markdown2 pygments` + `playwright install chromium`；完整清单见 `scripts/mdpdf/requirements.txt` |
| html-to-pdf | Chrome / Chromium（可设 `CHROME_PATH`）；合并需 `pip install PyPDF2`，尺寸验证可选 `pip install pymupdf` |
