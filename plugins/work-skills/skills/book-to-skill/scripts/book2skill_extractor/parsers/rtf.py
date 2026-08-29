from __future__ import annotations

import html
import re
from pathlib import Path

from .text import read_text_file


_UNICODE = re.compile(r"\\u(-?\d+)[ ]?(?:\\'[0-9a-fA-F]{2}|\?)?")


def _unicode(match: re.Match[str]) -> str:
    codepoint = int(match.group(1)) % 0x10000
    return "" if codepoint == 0 or 0xD800 <= codepoint <= 0xDFFF else chr(codepoint)


def _fallback(raw: str) -> str:
    raw = _UNICODE.sub(_unicode, raw)
    raw = re.sub(r"\\'[0-9a-fA-F]{2}", " ", raw)
    raw = re.sub(r"\\par[d]?", "\n", raw)
    raw = re.sub(r"\\tab", "\t", raw)
    raw = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", raw)
    return html.unescape(raw.replace("{", "").replace("}", ""))


def extract_rtf(path: Path) -> tuple[str, str]:
    raw = read_text_file(path)
    try:
        from striprtf.striprtf import rtf_to_text
    except ImportError:
        return _fallback(raw), "rtf-regex"
    return rtf_to_text(raw), "striprtf"
