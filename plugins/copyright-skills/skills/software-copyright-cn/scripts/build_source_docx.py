#!/usr/bin/env python3
"""Create an auditable Word source-code excerpt from an inventory JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

try:
    from docx import Document
    from docx.enum.section import WD_SECTION
    from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt
except ImportError as exc:
    raise SystemExit("python-docx is required: python -m pip install python-docx") from exc


def decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace")


def set_cell_shading(cell, fill: str) -> None:
    props = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    props.append(shading)


def add_field(paragraph, instruction: str) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    text = OxmlElement("w:instrText")
    text.set(qn("xml:space"), "preserve")
    text.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, text, separate, end])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--lines-per-page", type=int, default=50)
    args = parser.parse_args()
    if args.lines_per_page < 1:
        raise SystemExit("--lines-per-page must be positive")
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite output: {output}")

    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    repo = Path(inventory["repo"])
    records: list[dict] = []
    for entry in inventory["included_files"]:
        path = repo / entry["path"]
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != entry["sha256"]:
            raise SystemExit(f"source changed after inventory: {entry['path']}")
        lines = decode(data).splitlines()
        if entry["physical_lines"] and data.endswith((b"\n", b"\r")):
            pass
        for number, content in enumerate(lines, start=1):
            records.append({"path": entry["path"], "line": number, "text": content})
        if entry["physical_lines"] > len(lines):
            records.append({"path": entry["path"], "line": len(lines) + 1, "text": ""})

    total = len(records)
    selected = records if total <= 3000 else records[:1500] + records[-1500:]
    document = Document()
    section = document.sections[0]
    section.top_margin = Cm(1.2)
    section.bottom_margin = Cm(1.2)
    section.left_margin = Cm(1.1)
    section.right_margin = Cm(1.1)
    section.header_distance = Cm(0.4)
    section.footer_distance = Cm(0.4)
    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = header.add_run(f"{args.title} {args.version}  源代码")
    run.font.name = "宋体"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    run.font.size = Pt(8)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_field(footer, "PAGE")

    pages = [selected[i:i + args.lines_per_page] for i in range(0, len(selected), args.lines_per_page)]
    for page_index, page in enumerate(pages):
        table = document.add_table(rows=0, cols=2)
        table.autofit = False
        table.columns[0].width = Cm(5.0)
        table.columns[1].width = Cm(13.5)
        for item in page:
            cells = table.add_row().cells
            row = cells[0]._tc.getparent()
            tr_props = row.get_or_add_trPr()
            height = OxmlElement("w:trHeight")
            height.set(qn("w:val"), "235")
            height.set(qn("w:hRule"), "atLeast")
            tr_props.append(height)
            cells[0].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cells[1].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_shading(cells[0], "F2F2F2")
            for cell, value, font_name, size in (
                (cells[0], f"{item['path']}:{item['line']}", "宋体", 6.5),
                (cells[1], item["text"].replace("\t", "    "), "Consolas", 6.5),
            ):
                paragraph = cell.paragraphs[0]
                paragraph.paragraph_format.space_before = Pt(0)
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.line_spacing = 1
                run = paragraph.add_run(value)
                run.font.name = font_name
                run._element.rPr.rFonts.set(qn("w:eastAsia"), font_name)
                run.font.size = Pt(size)
        if page_index < len(pages) - 1:
            document.add_page_break()

    output.parent.mkdir(parents=True, exist_ok=True)
    document.save(output)
    manifest = {
        "inventory": str(args.inventory.resolve()),
        "title": args.title,
        "version": args.version,
        "total_physical_lines": total,
        "selected_line_count": len(selected),
        "selection": "all" if total <= 3000 else "first-1500-and-last-1500",
        "first": selected[0] if selected else None,
        "head_end": selected[min(1499, len(selected) - 1)] if selected else None,
        "tail_start": selected[-1500] if total > 3000 else None,
        "last": selected[-1] if selected else None,
        "selected_sha256": hashlib.sha256(
            json.dumps(selected, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "pages_at_configured_line_count": len(pages),
        "lines_per_page": args.lines_per_page,
    }
    output.with_suffix(output.suffix + ".manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"selected_lines={len(selected)} pages={len(pages)} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

