from __future__ import annotations

import importlib.util
import shutil


def capability_report() -> dict[str, object]:
    modules = {
        "docling": "docling", "pypdf": "pypdf", "pdfminer": "pdfminer",
        "ebooklib": "ebooklib", "beautifulsoup": "bs4",
        "python-docx": "docx", "striprtf": "striprtf",
    }
    return {
        "python_modules": {
            label: importlib.util.find_spec(module) is not None
            for label, module in modules.items()
        },
        "system_commands": {
            name: shutil.which(name) is not None
            for name in ("pdftotext", "ebook-convert")
        },
        "notes": [
            "TXT, Markdown, HTML, EPUB, DOCX, and RTF have standard-library fallbacks.",
            "PDF needs docling, pdftotext, pypdf, or pdfminer.",
            "MOBI/AZW/AZW3 requires Calibre ebook-convert.",
            "Scanned documents require a host-provided OCR workflow.",
        ],
    }
