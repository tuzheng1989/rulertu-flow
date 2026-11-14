#!/usr/bin/env python3
"""
Markdown to PDF Converter with Mermaid Support

This script converts Markdown files to PDF with full support for:
- Mermaid diagrams (flowcharts, sequence diagrams, etc.)
- Code syntax highlighting
- Chinese/English mixed content
- Custom CSS styling
- Table of contents
- Headers, footers, page numbers

Requirements:
    pip install playwright markdown2 pygments
    playwright install chromium
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright
import markdown2
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

# Diagram pre-renderer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from diagram_renderer import pre_render as pre_render_diagrams


# Default HTML template with Mermaid support
DEFAULT_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        /* Base styles */
        @page {{
            size: {page_size} {orientation};
            margin: {margin_top} {margin_right} {margin_bottom} {margin_left};
        }}

        body {{
            font-family: "Microsoft YaHei", "SimSun", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: {content_width};
            margin: 0 auto;
            padding: 20px;
        }}

        /* Headings */
        h1 {{
            font-size: 2em;
            border-bottom: 2px solid #007acc;
            padding-bottom: 0.3em;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            page-break-after: avoid;
        }}

        h2 {{
            font-size: 1.5em;
            border-bottom: 1px solid #ddd;
            padding-bottom: 0.2em;
            margin-top: 1.2em;
            margin-bottom: 0.4em;
            page-break-after: avoid;
        }}

        h3 {{
            font-size: 1.25em;
            margin-top: 1em;
            margin-bottom: 0.3em;
            page-break-after: avoid;
        }}

        h4, h5, h6 {{
            margin-top: 0.8em;
            margin-bottom: 0.2em;
            page-break-after: avoid;
        }}

        /* Paragraphs and lists */
        p {{
            margin: 0.5em 0;
            text-align: justify;
        }}

        ul, ol {{
            padding-left: 2em;
            margin: 0.5em 0;
        }}

        li {{
            margin: 0.2em 0;
        }}

        /* Links */
        a {{
            color: #007acc;
            text-decoration: none;
        }}

        a:hover {{
            text-decoration: underline;
        }}

        /* Blockquotes */
        blockquote {{
            border-left: 4px solid #ddd;
            padding-left: 1em;
            margin: 1em 0;
            color: #666;
            background-color: #f9f9f9;
            padding: 0.5em 1em;
        }}

        /* Tables */
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
            page-break-inside: avoid;
        }}

        th, td {{
            border: 1px solid #ddd;
            padding: 8px 12px;
            text-align: left;
        }}

        th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}

        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}

        /* Code blocks */
        pre {{
            background-color: #f6f8fa;
            border-radius: 6px;
            padding: 16px;
            overflow: auto;
            margin: 1em 0;
            page-break-inside: avoid;
        }}

        code {{
            font-family: "Consolas", "Monaco", "Courier New", monospace;
            font-size: 0.9em;
        }}

        pre code {{
            background-color: transparent;
            padding: 0;
            border-radius: 0;
        }}

        p > code, li > code {{
            background-color: #f1f1f1;
            padding: 2px 6px;
            border-radius: 3px;
        }}

        /* Pygments syntax highlighting */
        .highlight {{
            background-color: #f6f8fa;
            border-radius: 6px;
            padding: 16px;
            overflow-x: auto;
        }}

        .highlight .hll {{ background-color: #ffffcc }}
        .highlight .c {{ color: #999988; font-style: italic }}
        .highlight .err {{ color: #a61717; background-color: #e3d2d2 }}
        .highlight .k {{ color: #000080; font-weight: bold }}
        .highlight .o {{ color: #666666 }}
        .highlight .n {{ color: #333333 }}
        .highlight .mi {{ color: #009999 }}
        .highlight .s {{ color: #d14 }}
        .highlight .nf {{ color: #990000; font-weight: bold }}
        .highlight .kc {{ color: #006699; font-weight: bold }}
        .highlight .kd {{ color: #006699; font-weight: bold }}
        .highlight .kn {{ color: #006699; font-weight: bold }}

        /* Mermaid diagrams */
        .mermaid {{
            text-align: center;
            margin: 20px 0;
            background-color: #fff;
            padding: 10px;
            page-break-inside: avoid;
        }}

        /* Table of contents */
        .toc {{
            background-color: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 15px 20px;
            margin-bottom: 20px;
        }}

        .toc-title {{
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
        }}

        .toc ul {{
            list-style-type: none;
            padding-left: 0;
        }}

        .toc li {{
            margin: 5px 0;
        }}

        .toc a {{
            color: #007acc;
            text-decoration: none;
        }}

        .toc a:hover {{
            text-decoration: underline;
        }}

        .toc-level-2 {{ padding-left: 20px; }}
        .toc-level-3 {{ padding-left: 40px; }}
        .toc-level-4 {{ padding-left: 60px; }}

        /* Horizontal rules */
        hr {{
            border: none;
            border-top: 1px solid #ddd;
            margin: 2em 0;
        }}

        /* Images */
        img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 1em auto;
        }}

        /* Page break control */
        .page-break {{ page-break-after: always; }}
        .no-break {{ page-break-inside: avoid; }}

        /* Print-specific styles */
        @media print {{
            body {{
                max-width: none;
            }}
        }}

        /* Custom CSS (来自 --style，后定义覆盖前面默认样式，实现定制) */
        {custom_css}
    </style>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose',
            fontFamily: 'Microsoft YaHei, SimSun, sans-serif'
        }});
    </script>
</head>
<body>
    {toc}
    {content}
</body>
</html>
"""


def extract_mermaid_blocks(content: str) -> list[tuple[str, str]]:
    """
    Extract Mermaid code blocks from Markdown content.

    Returns a list of (original_block, unique_id) tuples.
    """
    pattern = r'```mermaid\n(.*?)\n```'
    matches = []
    for i, match in enumerate(re.finditer(pattern, content, re.DOTALL)):
        original = match.group(0)
        mermaid_code = match.group(1)
        unique_id = f'mermaid-{i}'
        matches.append((original, unique_id, mermaid_code))
    return matches


def convert_mermaid_to_html(content: str) -> str:
    """
    Convert Mermaid code blocks to HTML div elements.
    """
    mermaid_blocks = extract_mermaid_blocks(content)
    for original, unique_id, mermaid_code in mermaid_blocks:
        html_block = f'<div class="mermaid">{mermaid_code}</div>'
        content = content.replace(original, html_block, 1)
    return content


def highlight_code_blocks(content: str) -> str:
    """
    Apply Pygments syntax highlighting to code blocks.
    """
    def replace_code_block(match):
        lang = match.group(1) or 'text'
        code = match.group(2)

        try:
            if lang == 'text' or lang == '':
                lexer = get_lexer_by_name('text')
            else:
                lexer = get_lexer_by_name(lang)
        except ClassNotFound:
            try:
                lexer = guess_lexer(code)
            except ClassNotFound:
                lexer = get_lexer_by_name('text')

        formatter = HtmlFormatter(
            style='github',
            linenos=False,
            cssclass='highlight'
        )
        highlighted = highlight(code, lexer, formatter)
        return highlighted

    # Match fenced code blocks: ```lang ... ```
    pattern = r'```(\w*)\n(.*?)\n```'
    return re.sub(pattern, replace_code_block, content, flags=re.DOTALL)


def generate_toc(content: str, depth: int = 3) -> str:
    """
    Generate table of contents from HTML content.
    """
    headings = re.findall(r'<h([1-6])[^>]*>(.*?)</h\1>', content)
    if not headings:
        return ''

    toc_items = []
    for level, title in headings:
        level_int = int(level)
        if level_int > depth:
            continue
        # Remove HTML tags from title
        title_text = re.sub(r'<[^>]+>', '', title)
        # Create anchor
        anchor = re.sub(r'[^\w\u4e00-\u9fff-]', '-', title_text).strip('-')
        toc_items.append((level_int, title_text, anchor))

    if not toc_items:
        return ''

    toc_html = '<div class="toc">\n<div class="toc-title">目录</div>\n<ul>\n'
    for level, title, anchor in toc_items:
        indent = level - 1
        toc_html += f'<li class="toc-level-{level}"><a href="#{anchor}">{title}</a></li>\n'
    toc_html += '</ul>\n</div>\n'

    # Add anchors to headings in content
    for i, (level, title, anchor) in enumerate(toc_items):
        # Find and replace the heading
        pattern = f'(<h{level}[^>]*>)({re.escape(title)})(</h{level}>)'
        replacement = f'<h{level} id="{anchor}">\\2\\3'
        content = re.sub(pattern, replacement, content, count=1)

    return toc_html, content


def markdown_to_html(
    markdown_content: str,
    title: str = "Document",
    highlight: bool = True,
    toc: bool = False,
    toc_depth: int = 3,
    custom_css: str = None,
    **template_vars
) -> str:
    """
    Convert Markdown content to HTML with Mermaid support.
    """
    # First, extract mermaid blocks to prevent markdown2 from converting them
    mermaid_blocks = extract_mermaid_blocks(markdown_content)
    for original, unique_id, mermaid_code in mermaid_blocks:
        markdown_content = markdown_content.replace(original, f'<<<MERMAID_{unique_id}>>>')

    # Convert Markdown to HTML
    extras = ['fenced-code-blocks', 'tables', 'toc', 'header-ids']
    html_content = markdown2.markdown(markdown_content, extras=extras)

    # Restore mermaid blocks as HTML
    for original, unique_id, mermaid_code in mermaid_blocks:
        placeholder = f'<<<MERMAID_{unique_id}>>>'
        html_block = f'<div class="mermaid">{mermaid_code}</div>'
        html_content = html_content.replace(placeholder, html_block)

    # Apply syntax highlighting (skip mermaid blocks)
    if highlight:
        html_content = highlight_code_blocks(html_content)

    # Generate TOC if requested
    toc_html = ''
    if toc:
        toc_html, html_content = generate_toc(html_content, toc_depth)

    # Load custom CSS if provided
    custom_css_content = ''
    if custom_css and os.path.exists(custom_css):
        with open(custom_css, 'r', encoding='utf-8') as f:
            custom_css_content = f.read()

    # Build template variables
    defaults = {
        'title': title,
        'content': html_content,
        'toc': toc_html,
        'page_size': template_vars.get('page_size', 'A4'),
        'orientation': template_vars.get('orientation', 'portrait'),
        'margin_top': template_vars.get('margin_top', '20mm'),
        'margin_right': template_vars.get('margin_right', '20mm'),
        'margin_bottom': template_vars.get('margin_bottom', '20mm'),
        'margin_left': template_vars.get('margin_left', '20mm'),
        'content_width': template_vars.get('content_width', '800px'),
        'custom_css': custom_css_content,
    }

    # Use custom template if provided
    if custom_css and os.path.exists(custom_css.replace('.css', '.html')):
        template_path = custom_css.replace('.css', '.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
    else:
        template = DEFAULT_HTML_TEMPLATE

    return template.format(**defaults)


def html_to_pdf(
    html_content: str,
    output_path: str,
    timeout: int = 60000,
    base_dir: Optional[str] = None,
    **kwargs
) -> None:
    """
    Convert HTML content to PDF using Playwright.

    Uses a temp HTML file + page.goto() so relative paths (images, CSS)
    resolve correctly against base_dir.
    """
    # Determine directory for temp HTML (resolve relative paths against this)
    tmp_dir = base_dir or str(Path(output_path).parent)
    tmp_html = os.path.join(tmp_dir, f'__md2pdf_{Path(output_path).stem}.html')

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        try:
            # Write HTML to temp file so file:// URL resolves relative paths
            with open(tmp_html, 'w', encoding='utf-8') as f:
                f.write(html_content)

            file_url = Path(tmp_html).as_uri()
            page.goto(file_url, wait_until='networkidle', timeout=timeout)

            # Wait for Mermaid diagrams to render
            try:
                page.wait_for_selector('.mermaid svg', timeout=timeout)
            except Exception:
                page.wait_for_timeout(1000)

            # PDF generation options
            pdf_options = {
                'path': output_path,
                'format': kwargs.get('page_size', 'A4'),
                'landscape': kwargs.get('orientation', 'portrait') == 'landscape',
                'margin': {
                    'top': kwargs.get('margin_top', '20mm'),
                    'right': kwargs.get('margin_right', '20mm'),
                    'bottom': kwargs.get('margin_bottom', '20mm'),
                    'left': kwargs.get('margin_left', '20mm'),
                },
                'print_background': True,
            }

            page.pdf(**pdf_options)
        finally:
            # Clean up temp file
            if os.path.exists(tmp_html):
                os.unlink(tmp_html)
            browser.close()


def convert_markdown_to_pdf(
    input_path: str,
    output_path: Optional[str] = None,
    style: Optional[str] = None,
    toc: bool = False,
    toc_depth: int = 3,
    page_size: str = 'A4',
    orientation: str = 'portrait',
    margin_top: str = '20mm',
    margin_right: str = '20mm',
    margin_bottom: str = '20mm',
    margin_left: str = '20mm',
    content_width: str = '800px',
    timeout: int = 60000,
    pre_render: bool = True,
    **kwargs
) -> str:
    """
    Convert a Markdown file to PDF.

    Args:
        input_path: Path to the input Markdown file
        output_path: Path to the output PDF file (optional)
        style: Path to custom CSS file
        toc: Generate table of contents
        toc_depth: Maximum heading depth for TOC
        page_size: Page size (A4, Letter, etc.)
        orientation: Page orientation (portrait/landscape)
        margin_top: Top margin
        margin_right: Right margin
        margin_bottom: Bottom margin
        margin_left: Left margin
        content_width: Content width for HTML
        timeout: Render timeout in milliseconds
        pre_render: Pre-render diagrams (Mermaid/PlantUML/SVG/HTML) to PNG

    Returns:
        Path to the generated PDF file
    """
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Read Markdown content
    with open(input_file, 'r', encoding='utf-8') as f:
        markdown_content = f.read()

    # Determine output path
    if output_path is None:
        output_path = input_file.with_suffix('.pdf')
    else:
        output_path = Path(output_path)
        if output_path.is_dir():
            output_path = output_path / input_file.with_suffix('.pdf').name

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Pre-render diagrams to PNG if enabled
    if pre_render:
        diagram_dir = str(output_path.parent / 'diagrams')
        markdown_content, diagram_blocks = pre_render_diagrams(
            markdown_content, diagram_dir, timeout=min(timeout, 30000)
        )
        if diagram_blocks:
            rendered = sum(1 for b in diagram_blocks if b.rendered)
            print(f"Pre-rendered {rendered}/{len(diagram_blocks)} diagrams")

    # Get document title
    title = input_file.stem.replace('-', ' ').replace('_', ' ').title()

    # Convert to HTML
    html_content = markdown_to_html(
        markdown_content,
        title=title,
        highlight=True,
        toc=toc,
        toc_depth=toc_depth,
        custom_css=style,
        page_size=page_size,
        orientation=orientation,
        margin_top=margin_top,
        margin_right=margin_right,
        margin_bottom=margin_bottom,
        margin_left=margin_left,
        content_width=content_width,
    )

    # Convert to PDF (base_dir = input file dir for relative path resolution)
    html_to_pdf(
        html_content,
        str(output_path),
        timeout=timeout,
        base_dir=str(input_file.parent.resolve()),
        page_size=page_size,
        orientation=orientation,
        margin_top=margin_top,
        margin_right=margin_right,
        margin_bottom=margin_bottom,
        margin_left=margin_left,
    )

    return str(output_path)


def batch_convert(
    input_dir: str,
    output_dir: str,
    recursive: bool = False,
    **kwargs
) -> list[str]:
    """
    Batch convert Markdown files to PDF.

    Returns a list of generated PDF paths.
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Find all Markdown files
    pattern = '**/*.md' if recursive else '*.md'
    markdown_files = list(input_path.glob(pattern))

    if not markdown_files:
        print(f"No Markdown files found in {input_dir}")
        return []

    # Convert each file
    results = []
    for md_file in markdown_files:
        try:
            # Preserve directory structure
            relative_path = md_file.relative_to(input_path)
            pdf_file = output_path / relative_path.with_suffix('.pdf')
            pdf_file.parent.mkdir(parents=True, exist_ok=True)

            print(f"Converting: {md_file}")
            result = convert_markdown_to_pdf(
                str(md_file),
                str(pdf_file),
                **kwargs
            )
            results.append(result)
            print(f"  -> {result}")

        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)

    return results


def load_config(config_path: str) -> dict:
    """
    Load configuration from JSON file.
    """
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def main():
    parser = argparse.ArgumentParser(
        description='Convert Markdown to PDF with Mermaid support',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s README.md
  %(prog)s README.md -o output.pdf --style custom.css --toc
  %(prog)s ./docs --batch --output-dir ./pdfs
  %(prog)s README.md --config md-to-pdf.config.json
        """
    )

    parser.add_argument('input', help='Input Markdown file or directory')
    parser.add_argument('-o', '--output', help='Output PDF file or directory')
    parser.add_argument('--style', help='Custom CSS file path')
    parser.add_argument('--toc', action='store_true', help='Generate table of contents')
    parser.add_argument('--toc-depth', type=int, default=3, help='TOC max depth (default: 3)')
    parser.add_argument('--batch', action='store_true', help='Batch convert directory')
    parser.add_argument('--recursive', action='store_true', help='Recursive batch conversion')

    # Page settings
    parser.add_argument('--page-size', default='A4', choices=['A4', 'A3', 'A5', 'Letter', 'Legal'],
                       help='Page size (default: A4)')
    parser.add_argument('--orientation', default='portrait', choices=['portrait', 'landscape'],
                       help='Page orientation (default: portrait)')

    # Margins
    parser.add_argument('--margin-top', default='20mm', help='Top margin (default: 20mm)')
    parser.add_argument('--margin-right', default='20mm', help='Right margin (default: 20mm)')
    parser.add_argument('--margin-bottom', default='20mm', help='Bottom margin (default: 20mm)')
    parser.add_argument('--margin-left', default='20mm', help='Left margin (default: 20mm)')

    # Other
    parser.add_argument('--content-width', default='800px', help='Content width (default: 800px)')
    parser.add_argument('--timeout', type=int, default=60000, help='Render timeout in ms (default: 60000)')
    parser.add_argument('--pre-render', action='store_true', default=True,
                       help='Pre-render diagrams to PNG (default: True)')
    parser.add_argument('--no-pre-render', dest='pre_render', action='store_false',
                       help='Disable diagram pre-rendering, use CDN fallback')
    parser.add_argument('--config', help='Load configuration from JSON file')

    args = parser.parse_args()

    # Load config if specified
    config = load_config(args.config) if args.config else {}

    # Merge args with config (args take precedence)
    kwargs = {
        'style': args.style or config.get('style'),
        'toc': args.toc or config.get('toc', False),
        'toc_depth': args.toc_depth or config.get('tocDepth', 3),
        'page_size': args.page_size or config.get('pageSize', 'A4'),
        'orientation': args.orientation or config.get('orientation', 'portrait'),
        'margin_top': args.margin_top or config.get('margin', {}).get('top', '20mm'),
        'margin_right': args.margin_right or config.get('margin', {}).get('right', '20mm'),
        'margin_bottom': args.margin_bottom or config.get('margin', {}).get('bottom', '20mm'),
        'margin_left': args.margin_left or config.get('margin', {}).get('left', '20mm'),
        'content_width': args.content_width or config.get('contentWidth', '800px'),
        'timeout': args.timeout or config.get('timeout', 60000),
        'pre_render': args.pre_render if args.pre_render is not None else config.get('preRender', True),
    }

    # Check if input is a directory or file
    input_path = Path(args.input)
    if input_path.is_dir():
        # Batch conversion
        output_dir = args.output or config.get('outputDir', './pdfs')
        results = batch_convert(
            str(input_path),
            output_dir,
            recursive=args.recursive or config.get('recursive', False),
            **kwargs
        )
        print(f"\nConverted {len(results)} file(s) to PDF")

    elif input_path.is_file():
        # Single file conversion
        result = convert_markdown_to_pdf(
            str(input_path),
            args.output,
            **kwargs
        )
        print(f"PDF generated: {result}")

    else:
        print(f"Error: Input path not found: {args.input}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
