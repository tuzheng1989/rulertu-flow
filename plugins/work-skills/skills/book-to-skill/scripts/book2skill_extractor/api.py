from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .parsers.docx import extract_docx
from .parsers.epub import extract_epub
from .parsers.html import extract_html_file
from .parsers.pdf import extract_pdf
from .parsers.rtf import extract_rtf
from .parsers.text import read_text_file


class ExtractionError(RuntimeError):
    """Raised when no safe extractor can produce usable text."""


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    input_format: str
    extractor: str
    warnings: tuple[str, ...] = ()


TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}
HTML_EXTENSIONS = {".html", ".htm", ".xhtml"}
CALIBRE_EXTENSIONS = {".mobi", ".azw", ".azw3"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | HTML_EXTENSIONS | CALIBRE_EXTENSIONS | {
    ".pdf", ".epub", ".docx", ".rtf"
}


def _extract_calibre(path: Path) -> tuple[str, str]:
    executable = shutil.which("ebook-convert")
    if executable is None:
        raise ExtractionError("MOBI/AZW extraction requires Calibre ebook-convert.")
    with tempfile.TemporaryDirectory(prefix="book2skill-calibre-") as tmp:
        output = Path(tmp) / "converted.txt"
        result = subprocess.run(
            [executable, str(path), str(output)], capture_output=True, text=True,
            timeout=300, check=False,
        )
        if result.returncode != 0 or not output.is_file():
            detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
            raise ExtractionError(f"ebook-convert failed: {detail}")
        return output.read_text(encoding="utf-8", errors="replace"), "ebook-convert"


def extract_book(path: str | Path, *, pdf_mode: str = "auto") -> ExtractionResult:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise ExtractionError(f"Input file not found: {source}")
    suffix = source.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ExtractionError(
            f"Unsupported input format {suffix or '<none>'}. Supported: "
            + ", ".join(sorted(SUPPORTED_EXTENSIONS))
        )

    warnings: list[str] = []
    try:
        if suffix in TEXT_EXTENSIONS:
            text, extractor = read_text_file(source), "text-decoder"
        elif suffix in HTML_EXTENSIONS:
            text, extractor = extract_html_file(source)
        elif suffix == ".pdf":
            text, extractor, warnings = extract_pdf(source, mode=pdf_mode)
        elif suffix == ".epub":
            text, extractor = extract_epub(source)
        elif suffix == ".docx":
            text, extractor = extract_docx(source)
        elif suffix == ".rtf":
            text, extractor = extract_rtf(source)
        else:
            text, extractor = _extract_calibre(source)
    except ExtractionError:
        raise
    except Exception as error:
        raise ExtractionError(f"Extraction failed: {type(error).__name__}: {error}") from error

    if not text or not text.strip():
        raise ExtractionError(
            "No usable text was extracted. The document may be scanned, encrypted, "
            "damaged, or require OCR supplied by the host agent."
        )
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    return ExtractionResult(normalized, suffix.lstrip("."), extractor, tuple(warnings))
