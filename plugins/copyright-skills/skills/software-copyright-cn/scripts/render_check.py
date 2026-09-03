#!/usr/bin/env python3
"""Render a docx to PDF and count rendered text lines per page.

两段式：
1. convert_to_pdf(docx, converter, out_dir, soffice) —— 转换后端二选一：
   - word：Word COM 自动化（pywin32），Windows + 本机装有 Word 时自动优先；
   - soffice：LibreOffice `soffice --headless --convert-to pdf`（PATH 查找或 --soffice 指定）。
   转到指定目录（调用方负责临时目录的创建与清理）；
2. count_pdf_lines(pdf_path, min_lines) —— 用 fitz 逐页提取文本统计行数。

行的口径：fitz `page.get_text()` 按换行拆分后的非空行数，
记录在报告 `line_definition` 字段，供人工复核对齐。

转换后端不可用（Word COM 失败或 soffice 未找到/转换失败）→ 非零退出并提示人工核对，
绝不输出 `render_checked: true` 的假成功。输出文件已存在 → 拒绝覆盖（全局红线 1）。
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LINE_DEFINITION = "fitz page.get_text() 按换行拆分后的非空行数"
HUMAN_FALLBACK = "无法渲染校验（需 Word COM 或 LibreOffice soffice 后端），需人工在 Word/PDF 中逐页核对"
WD_FORMAT_PDF = 17  # wdFormatPDF


def count_pdf_lines(pdf_path: Path, min_lines: int) -> dict:
    try:
        import fitz
    except ImportError as count_error:
        raise SystemExit("PyMuPDF is required: python -m pip install pymupdf") from count_error

    pages: dict[str, int] = {}
    with fitz.open(pdf_path) as document:
        for page_number, page in enumerate(document, start=1):
            lines = [line for line in page.get_text().splitlines() if line.strip()]
            pages[str(page_number)] = len(lines)
    return {
        "render_checked": True,
        "total_pages": len(pages),
        "pages": pages,
        "under_pages": [number for number, count in pages.items() if count < min_lines],
        "min_lines": min_lines,
        "line_definition": LINE_DEFINITION,
    }


def convert_with_word(docx: Path, out_dir: Path) -> Path:
    """用本机 Word（COM 自动化）把 docx 转成 pdf，返回产物路径；失败抛 RuntimeError。"""
    try:
        import win32com.client
    except ImportError as import_error:
        raise RuntimeError(f"pywin32 is required for the Word converter: {import_error}") from import_error

    word = None
    pdf_path = out_dir / docx.with_suffix(".pdf").name
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        document = word.Documents.Open(str(docx), ReadOnly=True)
        try:
            document.SaveAs2(str(pdf_path), FileFormat=WD_FORMAT_PDF)
        except Exception:
            # Word 2007（12.0）无 SaveAs2，退回 SaveAs + wdFormatPDF（需已装 PDF 导出组件）
            document.SaveAs(str(pdf_path), FileFormat=WD_FORMAT_PDF)
        document.Close(False)
    except Exception as conversion_error:
        raise RuntimeError(f"Word COM conversion failed: {conversion_error}") from conversion_error
    finally:
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass
    if not pdf_path.is_file():
        raise RuntimeError("Word COM produced no pdf")
    return pdf_path


def select_converter(choice: str, soffice_path) -> str | None:
    """auto：显式 --soffice 时用 soffice；否则 Word COM 可导入时优先 word，再退 soffice。"""
    soffice_found = bool(soffice_path or shutil.which("soffice"))
    if choice == "word":
        return "word"
    if choice == "soffice":
        return "soffice" if soffice_found else None
    if soffice_path:
        return "soffice"
    try:
        import win32com.client  # noqa: F401
        return "word"
    except ImportError:
        return "soffice" if soffice_found else None


def convert_to_pdf(docx: Path, converter: str, out_dir: Path, soffice=None) -> Path:
    """按选定后端把 docx 转成 pdf；失败抛 RuntimeError。本函数是接缝：测试可注入假转换器。"""
    if converter == "word":
        return convert_with_word(docx, out_dir)
    if not soffice:
        soffice = shutil.which("soffice")
    if not soffice:
        raise RuntimeError("soffice not found")
    command = [
        str(soffice), "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(docx)
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True)
    except OSError as run_error:
        raise RuntimeError(f"soffice failed to run: {run_error}") from run_error
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"soffice conversion failed: {detail}")
    produced = out_dir / docx.with_suffix(".pdf").name
    if not produced.is_file():
        raise RuntimeError(f"soffice produced no pdf: {completed.stdout.strip()}")
    return produced


def main(argv: list[str] | None = None) -> int:
    # Windows 控制台/管道默认 GBK，中文降级提示需按 utf-8 输出才能被可靠捕获
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument("--docx", type=Path)
    parser.add_argument("--min-lines", type=int, default=30)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--converter", choices=["auto", "word", "soffice"], default="auto")
    parser.add_argument("--soffice", type=Path, help="soffice 可执行文件路径（默认从 PATH 查找）")
    args = parser.parse_args(argv)
    if not args.docx or not args.output:
        parser.error("--docx and --output are required")

    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite output: {output}")
    docx = args.docx.resolve()
    if not docx.is_file():
        raise SystemExit(f"docx not found: {docx}")

    converter = select_converter(args.converter, args.soffice)
    if not converter:
        print(f"{HUMAN_FALLBACK}（未找到可用后端：Word COM 不可用且 soffice 不在 PATH，可用 --soffice 指定）", file=sys.stderr)
        return 2

    try:
        with tempfile.TemporaryDirectory(prefix="render_check_") as out_dir:
            pdf_path = convert_to_pdf(docx, converter, Path(out_dir), args.soffice)
            report = count_pdf_lines(pdf_path, args.min_lines)
    except RuntimeError as conversion_error:
        print(f"{HUMAN_FALLBACK}（{conversion_error}）", file=sys.stderr)
        return 2

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    under = ",".join(report["under_pages"]) or "none"
    print(
        f"render_checked=true converter={converter} total_pages={report['total_pages']} "
        f"under_pages={under} output={output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
