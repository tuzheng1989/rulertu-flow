#!/usr/bin/env python3
"""
Diagram Pre-renderer for MD-to-PDF

Pre-renders Mermaid, PlantUML, SVG, and HTML diagram blocks to PNG
before PDF generation, ensuring reliable rendering in the final output.

Usage:
    from diagram_renderer import pre_render
    modified_content, blocks = pre_render(markdown_text, output_dir)
"""

import base64
import os
import re
import zlib
import urllib.request
from dataclasses import dataclass
from typing import Optional

from playwright.sync_api import sync_playwright, Browser


@dataclass
class DiagramBlock:
    """Detected diagram block in markdown."""
    block_type: str          # mermaid, plantuml, html, svg
    code: str                # diagram source code
    index: int               # sequential index
    original_text: str       # original matched text in markdown
    source_file: Optional[str] = None
    png_file: Optional[str] = None
    rendered: bool = False


# HTML template for Mermaid rendering
MERMAID_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>body{{margin:0;padding:20px;background:#fff}}</style>
<script type="module">
import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
mermaid.initialize({{
    startOnLoad:true, theme:'default', securityLevel:'loose',
    fontFamily:'Microsoft YaHei,SimSun,sans-serif'
}});
</script>
</head>
<body><div class="mermaid">{code}</div></body>
</html>"""


def detect_blocks(content: str) -> list[DiagramBlock]:
    """Detect all renderable diagram blocks in markdown content."""
    blocks: list[DiagramBlock] = []
    idx = 0

    # Mermaid blocks: ```mermaid ... ```
    for m in re.finditer(r'```mermaid\n(.*?)\n```', content, re.DOTALL):
        blocks.append(DiagramBlock('mermaid', m.group(1), idx, m.group(0)))
        idx += 1

    # PlantUML blocks: ```plantuml or ```puml
    for m in re.finditer(r'```(?:plantuml|puml)\n(.*?)\n```', content, re.DOTALL):
        blocks.append(DiagramBlock('plantuml', m.group(1), idx, m.group(0)))
        idx += 1

    # HTML code blocks containing diagram elements
    for m in re.finditer(r'```html\n(.*?)\n```', content, re.DOTALL):
        code = m.group(1)
        lower = code.lower()
        if any(tag in lower for tag in ('<svg', '<canvas', 'echarts', 'd3.', 'chart.js')):
            blocks.append(DiagramBlock('html', code, idx, m.group(0)))
            idx += 1

    # Inline SVG blocks (not inside code fences)
    for m in re.finditer(r'(<svg\b[^>]*>.*?</svg>)', content, re.DOTALL):
        if not _inside_code_fence(content, m.start()):
            blocks.append(DiagramBlock('svg', m.group(1), idx, m.group(0)))
            idx += 1

    # Inline HTML blocks with layout styling (architecture diagrams, etc.)
    # Detects <div style="display:flex/grid/..."> ... </div> blocks
    for html_text, start, end in _detect_inline_html_blocks(content):
        blocks.append(DiagramBlock('inline-html', html_text, idx, html_text))
        idx += 1

    return blocks


# Layout CSS properties that indicate a complex diagram
_LAYOUT_INDICATORS = (
    'display\\s*:\\s*(?:flex|grid|inline-flex|inline-grid)',
    'position\\s*:\\s*(?:absolute|relative|sticky)',
    'flex-direction',
    'justify-content',
    'align-items',
    'grid-template',
)


def _detect_inline_html_blocks(content: str) -> list[tuple[str, int, int]]:
    """
    Detect complex inline HTML blocks (architecture diagrams, etc.)
    that are NOT inside code fences.

    Returns list of (html_text, start_pos, end_pos).
    """
    results: list[tuple[str, int, int]] = []

    # Build pattern to match root <div> with layout-style attributes
    layout_pat = '|'.join(_LAYOUT_INDICATORS)
    root_pattern = re.compile(
        rf'<div\b[^>]*style\s*=\s*["\'][^"\']*(?:{layout_pat})[^"\']*["\']',
        re.IGNORECASE,
    )

    for m in root_pattern.finditer(content):
        start = m.start()
        if _inside_code_fence(content, start):
            continue

        # Avoid overlapping with already-detected blocks
        # (e.g., if this div is inside a previously matched block)
        end_pos = _find_matching_close_div(content, start)
        if end_pos < 0:
            continue

        html_block = content[start:end_pos]
        # Only pre-render substantial blocks (multi-line, meaningful size)
        if html_block.count('\n') >= 2 and len(html_block) > 80:
            results.append((html_block, start, end_pos))

    return results


def _find_matching_close_div(content: str, start: int) -> int:
    """
    Find the position after the closing </div> that matches the <div at `start`.
    Handles nested <div> elements by tracking depth.
    Returns -1 if no match found.
    """
    depth = 0
    pos = start

    while pos < len(content):
        open_m = re.search(r'<div\b', content[pos:], re.IGNORECASE)
        close_m = re.search(r'</div\s*>', content[pos:], re.IGNORECASE)

        if close_m is None:
            return -1

        # If there's an opening <div before the next </div>, increase depth
        if open_m is not None and open_m.start() < close_m.start():
            depth += 1
            pos += open_m.end()
        else:
            depth -= 1
            if depth == 0:
                return pos + close_m.end()
            pos += close_m.end()

    return -1


def _inside_code_fence(content: str, pos: int) -> bool:
    """Check if a position falls inside a fenced code block."""
    return content[:pos].count('```') % 2 == 1


def save_sources(blocks: list[DiagramBlock], source_dir: str) -> None:
    """Save diagram source code to individual files."""
    ext_map = {'mermaid': '.mmd', 'plantuml': '.puml', 'html': '.html', 'svg': '.svg', 'inline-html': '.html'}
    os.makedirs(source_dir, exist_ok=True)
    for b in blocks:
        ext = ext_map.get(b.block_type, '.txt')
        path = os.path.join(source_dir, f'diagram_{b.index:03d}{ext}')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(b.code)
        b.source_file = path


def render_all(blocks: list[DiagramBlock], output_dir: str, timeout: int = 30000) -> None:
    """Render all diagram blocks to PNG files."""
    os.makedirs(output_dir, exist_ok=True)

    plantuml_blocks = [b for b in blocks if b.block_type == 'plantuml']
    pw_blocks = [b for b in blocks if b.block_type != 'plantuml']

    # PlantUML via online API (no Java needed)
    for b in plantuml_blocks:
        png_path = os.path.join(output_dir, f'diagram_{b.index:03d}.png')
        try:
            _render_plantuml(b.code, png_path)
            b.png_file = png_path
            b.rendered = True
        except Exception as e:
            print(f"[WARN] PlantUML #{b.index} render failed: {e}")

    # Others via Playwright
    if pw_blocks:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for b in pw_blocks:
                png_path = os.path.join(output_dir, f'diagram_{b.index:03d}.png')
                try:
                    _render_playwright(browser, b, png_path, timeout)
                    b.png_file = png_path
                    b.rendered = True
                except Exception as e:
                    print(f"[WARN] {b.block_type} #{b.index} render failed: {e}")
            browser.close()


def _render_playwright(browser: Browser, block: DiagramBlock, png_path: str, timeout: int) -> None:
    """Render a diagram block using Playwright screenshot."""
    page = browser.new_page()
    try:
        if block.block_type == 'mermaid':
            html = MERMAID_HTML.format(code=block.code)
        elif block.block_type == 'svg':
            html = (
                '<html><head><meta charset="UTF-8">'
                '<style>body{margin:0;padding:10px;background:#fff}</style>'
                f'</head><body>{block.code}</body></html>'
            )
        else:  # html, inline-html
            if '<html' in block.code.lower():
                html = block.code
            else:
                html = (
                    '<html><head><meta charset="UTF-8">'
                    f'<style>body{{margin:0;padding:10px;background:#fff}}</style>'
                    f'</head><body>{block.code}</body></html>'
                )

        page.set_content(html, wait_until='networkidle')

        if block.block_type == 'mermaid':
            try:
                page.wait_for_selector('.mermaid svg', timeout=timeout)
            except Exception:
                page.wait_for_timeout(3000)

        page.screenshot(path=png_path, full_page=True)
    finally:
        page.close()


def _render_plantuml(code: str, png_path: str) -> None:
    """Render PlantUML diagram via the online render API."""
    encoded = _encode_plantuml(code)
    url = f'https://www.plantuml.com/plantuml/png/{encoded}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
        if len(data) < 100:
            raise RuntimeError("PlantUML server returned empty response")
        with open(png_path, 'wb') as f:
            f.write(data)


# --- PlantUML encoding utilities ---

def _encode_plantuml(text: str) -> str:
    """Encode PlantUML text for the online render API (raw deflate + custom base64)."""
    comp = zlib.compressobj(9, zlib.DEFLATED, -15)
    compressed = comp.compress(text.encode('utf-8')) + comp.flush()
    return _plantuml_b64(compressed)


def _plantuml_b64(data: bytes) -> str:
    """PlantUML custom base64 encoding."""
    def _enc6(b: int) -> str:
        if b < 10:
            return chr(48 + b)
        b -= 10
        if b < 26:
            return chr(65 + b)
        b -= 26
        if b < 26:
            return chr(97 + b)
        b -= 26
        return '-' if b == 0 else ('_' if b == 1 else '?')

    result: list[str] = []
    for i in range(0, len(data), 3):
        b1 = data[i]
        b2 = data[i + 1] if i + 1 < len(data) else 0
        b3 = data[i + 2] if i + 2 < len(data) else 0
        result.append(_enc6(b1 >> 2))
        result.append(_enc6(((b1 & 0x3) << 4) | (b2 >> 4)))
        result.append(_enc6(((b2 & 0xF) << 2) | (b3 >> 6)))
        result.append(_enc6(b3 & 0x3F))
    return ''.join(result)


# --- Content replacement ---

def png_to_data_uri(png_path: str) -> str:
    """Convert PNG file to a data URI for embedding in HTML."""
    with open(png_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('ascii')
    return f'data:image/png;base64,{b64}'


def replace_with_images(content: str, blocks: list[DiagramBlock]) -> str:
    """Replace diagram blocks in markdown content with embedded PNG images."""
    for b in blocks:
        if not b.rendered or not b.png_file:
            continue
        data_uri = png_to_data_uri(b.png_file)
        img_tag = (
            f'<img src="{data_uri}" '
            f'alt="{b.block_type} diagram" '
            f'style="max-width:100%;display:block;margin:1em auto">'
        )
        content = content.replace(b.original_text, img_tag, 1)
    return content


def pre_render(content: str, output_dir: str, timeout: int = 30000) -> tuple[str, list[DiagramBlock]]:
    """
    Main entry point: detect diagrams, render to PNG, replace in content.

    Args:
        content: Raw markdown content
        output_dir: Directory to store source files and PNGs
        timeout: Playwright render timeout in ms

    Returns:
        Tuple of (modified_content, diagram_blocks)
    """
    blocks = detect_blocks(content)
    if not blocks:
        return content, []

    source_dir = os.path.join(output_dir, 'source')
    save_sources(blocks, source_dir)
    render_all(blocks, output_dir, timeout)
    return replace_with_images(content, blocks), blocks
