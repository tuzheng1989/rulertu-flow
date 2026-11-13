# Document Analysis — Word / PDF / PPT

> 本文件为 data-analysis 的 document mode（原 Word/PDF/PPT 文档解析 skill，2026-11-13 组建）。入口与路由见 SKILL.md。

End-to-end workflow for Word, PDF, and PPT document parsing. Each format has
specific parsing pitfalls — follow the format-specific sub-skill exactly.

---

## Workflow

### Step 0 — Identify file type and input scope

```python
import os

input_path = "/mnt/data/..."  # from user

# Detect single file vs directory (multi-file scenario)
if os.path.isdir(input_path):
    all_files = [
        os.path.join(input_path, f)
        for f in os.listdir(input_path)
        if f.lower().endswith(('.docx', '.doc', '.pdf', '.pptx', '.ppt'))
    ]
    print(f"Found {len(all_files)} documents: {all_files}")
else:
    all_files = [input_path]

# Route by extension
ext = os.path.splitext(all_files[0])[-1].lower()
print(f"File type: {ext}")
```

> **Critical rule**: When `input_path` is a directory OR the user says "这些文件" / "所有文档",
> process **every file** and aggregate. Never stop at the first file.

---

### Step 1 — Load sub-skill by format

| Extension | Sub-skill to load |
|-----------|------------------|
| `.docx` / `.doc` | `doc-capability/word-analysis/SKILL.md` |
| `.pdf` | `doc-capability/pdf-analysis/SKILL.md` |
| `.pptx` / `.ppt` | `doc-capability/ppt-analysis/SKILL.md` |

```
read_file(path="<skills_root>/data-analysis/doc-capability/<format>-analysis/SKILL.md")
```

Load **only the sub-skill you need** — do not load all three at once.

---

### Step 2 — Parse and extract

Follow the sub-skill's extraction pattern. For all formats:

- **Full scan**: iterate all pages/slides/paragraphs — never stop early
- **Table extraction**: get every table, not just the first one
- **Image/chart detection**: if a page/slide yields no text, treat it as image-based and follow the visual-reading flow in the "Image Content via Visual Reading" section below

---

### Step 3 — Answer with verification

After extracting data, verify before answering:

```python
# For count/statistics questions: spot-check 3-5 items
sample = result_list[:3]
print(f"Sample check: {sample}")
print(f"Total count: {len(result_list)}")

# For numeric calculations: print intermediate values
print(f"Max={max_val}, Min={min_val}, Range={max_val - min_val}")

# For unit-sensitive answers: always include the unit
print(f"Answer: {value} {unit}")  # e.g., "475 千港元" not just "475"
```

---

## Universal Rules

### MUST DO
- **Always iterate all pages/slides/paragraphs** — `for page in doc`, `for slide in prs.slides`, `for para in doc.paragraphs`
- **When input is a directory**: collect and process all matching files, then aggregate results
- **For scanned PDFs**: detect empty text → render pages to PNG → visual reading（见下方指引）
- **For image-only slides**: text extraction returns empty → render slide as PNG → visual reading（见下方指引）
- **For calculations**: show intermediate values; confirm unit matches the question

### NEVER DO
- Do NOT use `pytesseract` or `easyocr` as primary OCR — they are not installed; use session visual reading instead
- Do NOT use PIL pixel analysis to infer chart values — use session visual reading instead
- Do NOT stop at the first file, first page, or first table
- Do NOT guess content from filenames — always parse the actual file
- Do NOT output percentage when the question asks for absolute value (and vice versa)

---

## Image Content via Visual Reading (for image/chart content in any document)

When a page, slide, or embedded image needs vision understanding, use the
session's native visual reading: render/extract the image to a PNG file,
then read it directly with the Read tool — no external API involved.
图片理解：由会话视觉直读完成，提取指引与解析/导出流程见 `image.md`（同目录）。

渲染出的每张图片按内容类型向视觉直读下达提取要点（详见 `image.md` 的视觉提取指引）：

- Table: 提取所有行列内容，Markdown 表格格式，数值不四舍五入
- Chart: 提取标题、坐标轴标签、每个数据点的数值
- Diagram: 描述所有节点和连接关系

---

## Available sub-skills

```
doc-capability/word-analysis/SKILL.md   — .docx/.doc
doc-capability/pdf-analysis/SKILL.md    — .pdf
doc-capability/ppt-analysis/SKILL.md    — .pptx/.ppt
```
