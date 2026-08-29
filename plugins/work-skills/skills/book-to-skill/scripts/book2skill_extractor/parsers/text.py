from __future__ import annotations

from pathlib import Path


_BOMS = (
    (b"\xef\xbb\xbf", "utf-8-sig"),
    (b"\xff\xfe\x00\x00", "utf-32"),
    (b"\x00\x00\xfe\xff", "utf-32"),
    (b"\xff\xfe", "utf-16"),
    (b"\xfe\xff", "utf-16"),
)


def read_text_file(path: str | Path) -> str:
    data = Path(path).read_bytes()
    for bom, encoding in _BOMS:
        if data.startswith(bom):
            return data.decode(encoding)
    for encoding in ("utf-8", "gb18030", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeError(f"Could not determine text encoding: {path}")
