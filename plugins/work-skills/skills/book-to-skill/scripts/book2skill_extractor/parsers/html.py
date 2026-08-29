from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from .text import read_text_file


class HTMLTextExtractor(HTMLParser):
    SKIP = {"script", "style", "head"}
    BLOCKS = {"p", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "div", "tr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.SKIP:
            self.skip_depth += 1
        elif not self.skip_depth and tag in self.BLOCKS:
            self.parts.append("\n")
        elif not self.skip_depth and tag in {"td", "th"}:
            self.parts.append("\t")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)

    def get_text(self) -> str:
        return "".join(self.parts)


def extract_html_content(raw: str) -> tuple[str, str]:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        parser = HTMLTextExtractor()
        parser.feed(raw)
        return parser.get_text(), "html.parser"
    soup = BeautifulSoup(raw, "html.parser")
    for element in soup(["script", "style", "head"]):
        element.decompose()
    return soup.get_text(separator="\n"), "beautifulsoup"


def extract_html_file(path: str | Path) -> tuple[str, str]:
    return extract_html_content(read_text_file(path))
