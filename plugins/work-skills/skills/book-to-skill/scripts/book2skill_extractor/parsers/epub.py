from __future__ import annotations

import posixpath
import re
import zipfile
from pathlib import Path

from .html import HTMLTextExtractor


def _opf_path(archive: zipfile.ZipFile) -> str | None:
    try:
        container = archive.read("META-INF/container.xml").decode("utf-8", errors="replace")
        match = re.search(r'full-path=["\']([^"\']+\.opf)["\']', container)
        if match:
            return match.group(1)
    except KeyError:
        pass
    return next((name for name in archive.namelist() if name.lower().endswith(".opf")), None)


def _stdlib_epub(path: Path) -> str | None:
    with zipfile.ZipFile(path) as archive:
        opf = _opf_path(archive)
        ordered: list[str] = []
        if opf:
            raw = archive.read(opf).decode("utf-8", errors="replace")
            base = posixpath.dirname(opf)
            manifest: dict[str, str] = {}
            for tag in re.findall(r"<item\b[^>]*?/?>", raw):
                item_id = re.search(r'\bid=["\']([^"\']+)["\']', tag)
                href = re.search(r'\bhref=["\']([^"\']+)["\']', tag)
                if item_id and href:
                    manifest[item_id.group(1)] = posixpath.normpath(
                        posixpath.join(base, href.group(1))
                    )
            for item_id in re.findall(r'<itemref\b[^>]*?\bidref=["\']([^"\']+)["\']', raw):
                target = manifest.get(item_id)
                if target and target not in ordered:
                    ordered.append(target)
        if not ordered:
            ordered = sorted(
                name for name in archive.namelist()
                if name.lower().endswith((".html", ".xhtml"))
            )
        parts: list[str] = []
        for name in ordered:
            try:
                parser = HTMLTextExtractor()
                parser.feed(archive.read(name).decode("utf-8", errors="replace"))
                parts.append(parser.get_text())
            except KeyError:
                continue
        return "\n\n".join(parts) if parts else None


def extract_epub(path: Path) -> tuple[str, str]:
    try:
        import ebooklib
        from bs4 import BeautifulSoup
        from ebooklib import epub
    except ImportError:
        return _stdlib_epub(path) or "", "zipfile-epub"
    book = epub.read_epub(str(path))
    parts = [
        BeautifulSoup(item.get_content(), "html.parser").get_text(separator="\n")
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
    ]
    return "\n\n".join(parts), "ebooklib"
