from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _docling(path: Path) -> str | None:
    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption
    except ImportError:
        return None
    options = PdfPipelineOptions()
    options.do_ocr = False
    options.do_table_structure = True
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )
    return converter.convert(str(path)).document.export_to_markdown()


def _pdftotext(path: Path) -> str | None:
    executable = shutil.which("pdftotext")
    if executable is None:
        return None
    result = subprocess.run(
        [executable, "-layout", "-enc", "UTF-8", str(path), "-"],
        capture_output=True, text=True, timeout=180, check=False,
    )
    return result.stdout if result.returncode == 0 else None


def _pypdf(path: Path) -> str | None:
    try:
        import pypdf
    except ImportError:
        return None
    with path.open("rb") as stream:
        reader = pypdf.PdfReader(stream)
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def _pdfminer(path: Path) -> str | None:
    try:
        from pdfminer.high_level import extract_text
    except ImportError:
        return None
    return extract_text(str(path))


def extract_pdf(path: Path, *, mode: str = "auto") -> tuple[str, str, list[str]]:
    if mode not in {"auto", "technical", "text"}:
        raise ValueError("PDF mode must be auto, technical, or text")
    chain = [("docling", _docling)] if mode == "technical" else []
    chain.extend([("pdftotext", _pdftotext), ("pypdf", _pypdf), ("pdfminer", _pdfminer)])
    if mode == "auto":
        chain.append(("docling", _docling))
    warnings: list[str] = []
    for name, extractor in chain:
        try:
            text = extractor(path)
        except Exception as error:
            warnings.append(f"{name} failed: {type(error).__name__}: {error}")
            continue
        if text and text.strip():
            return text, name, warnings
    raise RuntimeError(
        "No PDF extractor produced text. Install pdftotext, pypdf, pdfminer.six, "
        "or docling; scanned PDFs need host-provided OCR."
    )
