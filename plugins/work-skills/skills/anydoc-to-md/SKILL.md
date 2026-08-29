---
name: anydoc-to-md
description: EvoCenter 专用本地办公文档转 Markdown 技能。用 anydoc 引擎（纯 Rust，亚 5ms/文档）将 Word、PowerPoint、Excel、OpenDocument、RTF、EPUB、CSV、PDF 转为干净的 GitHub-Flavored Markdown。当用户说"把 docx/pdf/pptx/xlsx 转成 markdown"、"文档转 md"、"anydoc"、"转换文档"、"转成 md"、"把这个 word/ppt/excel 转一下"时触发。默认输出位置由调用决定（工具型）；用于知识库导入时输出到 inbox/ 并加 frontmatter。
version: 1.0.0
metadata:
  openclaw:
    requires:
      anyBins:
        - anydoc
---

# anydoc to Markdown（EvoCenter 专用）

用 [anydoc](https://github.com/firecrawl/anydoc) 把本地办公文档转为干净的 GitHub-Flavored Markdown。anydoc 是 Firecrawl 开源的纯 Rust 引擎，14 种格式走同一文档模型、单一序列化器，亚 5ms/文档，纯本地运行无外部服务。

## 支持格式

| 格式 | 扩展名 |
|------|--------|
| Word | `.doc` `.docx` `.docm` |
| PowerPoint | `.ppt` `.pps` `.pot` `.pptx` `.pptm` `.ppsx` `.ppsm` |
| Excel | `.xls` `.xlsx` `.xlsm` `.xlsb` |
| OpenDocument | `.odt` `.ods` `.odp` |
| RTF | `.rtf` |
| EPUB | `.epub` |
| CSV | `.csv` |
| PDF | `.pdf`（仅文本型） |

格式从文件**内容**自动检测（不看扩展名），CSV 等无签名的格式靠扩展名或 `--format` 指定。

## 用法

### A. 工具型（默认）

转换单个文档，输出位置由调用决定。不加 frontmatter，保留 anydoc 原始干净输出。

```bash
anydoc <输入文件> -o <输出路径>
```

例：把 `output/exports` 下的公文转回 md：

```bash
anydoc "output/exports/关于项目立项的请示.docx" -o "workspace/关于项目立项的请示.md"
```

读取标准输入（管道场景）：

```bash
curl -s https://example.com/paper.pdf | anydoc -
```

### B. inbox 导入型（可选，用于知识库素材）

把外部办公文档导入知识库时，输出到 `inbox/` 并注入 frontmatter。遵守 CLAUDE.md「素材处理」规则。

```bash
anydoc "<源文件>" -o "inbox/<文件名>.md"
```

转换完成后，用 Edit 在文件顶部注入 frontmatter：

```yaml
---
source_type: document
source_path: <源文件路径或来源说明>
imported: <YYYY-MM-DD>
status: inbox
---
```

落盘规则：
- `inbox/` 保持扁平，不建子目录。
- 中文文档原样保留，不翻译。
- 非中文文档触发翻译归一化（导入即转化为中文）。
- 原始附件（PDF 等）移至 `assets/files/` 存档，不视为过程产物。
- 是否消化进 wiki 由用户决定，不主动触发 /llm-wiki。

## 命令参考

```
anydoc <file> [options]
anydoc - [options] < file      从 stdin 读取
```

| 选项 | 说明 |
|------|------|
| `-o, --output <path>` | 输出到文件（默认输出到 stdout） |
| `-f, --format <fmt>` | 指定格式：doc/docx/odt/pdf/ppt/pptx/rtf/epub/xlsx/ods/odp/csv。一般不需要，自动检测 |
| `-h, --help` | 帮助 |
| `-V, --version` | 版本 |

退出码：`0` 成功；`1` 文档无法读取或转换；`2` 用法错误。

## PDF 限制

PDF 仅支持**文本型**。扫描版或纯图片 PDF 会报 `unsupported`（anydoc 不做 OCR，需 OCR 的留给 Firecrawl 托管 API 或其他工具）。遇到此类报错属预期行为。

## 环境检查

首次使用前确认 anydoc 可用：

```bash
anydoc --version
```

若全局未安装，回退到 npx（首次自动缓存二进制）：

```bash
npx -y @firecrawl/anydoc <file> -o <out>
```

## 不做（边界）

- 不做翻译归一化（那是 inbox 落盘后翻译流程与 /llm-wiki 的事，本技能只管转 md）。
- 不做 OCR（anydoc 本身不做）。
- 默认单文件转换；批量需求由调用方循环调用。
