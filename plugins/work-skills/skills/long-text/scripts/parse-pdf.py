#!/usr/bin/env python3
"""
PDF 文档解析器
将 PDF 文档转换为 Markdown 格式

依赖:
    pip install PyMuPDF pymdown-extensions

使用方法:
    python parse-pdf.py input.pdf --output output.md
    python parse-pdf.py input.pdf --output output.md --pages 1-5
"""

import re
import argparse
from pathlib import Path
from datetime import datetime

try:
    import fitz  # PyMuPDF
except ImportError:
    print("错误: 需要安装 PyMuPDF")
    print("请运行: pip install PyMuPDF")
    exit(1)


class PDFParser:
    """PDF 文档解析器"""

    def __init__(self, pdf_path):
        self.pdf_path = Path(pdf_path)
        self.doc = fitz.open(str(pdf_path))
        self.output = []

    def parse(self, pages=None, extract_images=False):
        """
        解析 PDF 文档

        Args:
            pages: 页面范围，如 "1-5" 或 [1, 2, 3]
            extract_images: 是否提取图片
        """
        page_range = self._parse_page_range(pages) if pages else None

        for page_num in range(len(self.doc)):
            if page_range and page_num not in page_range:
                continue

            page = self.doc[page_num]
            text = page.get_text("text")
            blocks = page.get_text("blocks")

            # 解析页面内容
            self._parse_page(page_num + 1, blocks)

        self.doc.close()

        # 转换为 Markdown
        markdown = self._to_markdown()

        return markdown

    def _parse_page_range(self, pages):
        """解析页面范围参数"""
        if isinstance(pages, str):
            # 处理 "1-5" 格式
            if '-' in pages:
                start, end = map(int, pages.split('-'))
                return list(range(start - 1, end))
            else:
                return [int(pages) - 1]
        return pages

    def _parse_page(self, page_num, blocks):
        """解析单个页面"""
        for block in blocks:
            if block['type'] == 0:  # 文本块
                self._parse_text_block(block, page_num)
            elif block['type'] == 1:  # 图片块
                self._parse_image_block(block, page_num)

    def _parse_text_block(self, block, page_num):
        """解析文本块"""
        text = block[4].strip()

        # 检测标题
        if self._is_heading(block):
            level = self._get_heading_level(block)
            heading = '#' * level + ' ' + text
            self.output.append({
                'type': 'heading',
                'level': level,
                'text': heading,
                'page': page_num
            })
        # 检测列表
        elif self._is_list_item(text):
            self.output.append({
                'type': 'list',
                'text': text,
                'page': page_num
            })
        # 检测代码块（基于字体或格式）
        elif self._is_code_block(block):
            self.output.append({
                'type': 'code',
                'text': text,
                'language': self._detect_code_language(text),
                'page': page_num
            })
        # 普通段落
        else:
            self.output.append({
                'type': 'paragraph',
                'text': text,
                'page': page_num
            })

    def _parse_image_block(self, block, page_num):
        """解析图片块"""
        if block[7] > 50 and block[6] > 50:  # 过滤小图片
            self.output.append({
                'type': 'image',
                'page': page_num,
                'bbox': block[:4]
            })

    def _is_heading(self, block):
        """检测是否为标题"""
        # 基于字体大小判断
        if len(block) < 5:
            return False
        font_size = block.get('size', 12)
        return font_size >= 14

    def _get_heading_level(self, block):
        """判断标题级别"""
        font_size = block.get('size', 12)
        if font_size >= 24:
            return 1
        elif font_size >= 20:
            return 2
        elif font_size >= 16:
            return 3
        else:
            return 4

    def _is_list_item(self, text):
        """检测是否为列表项"""
        return bool(re.match(r'^[\s]*[\-\*\•]\s+', text) or re.match(r'^[\s]*\d+\.\s+', text))

    def _is_code_block(self, block):
        """检测是否为代码块"""
        text = block[4]
        # 基于字体（通常是等宽字体）和内容特征判断
        # 简化判断：包含大量特殊字符
        special_chars = sum(1 for c in text if c in '{}()[];:,.><|&')
        return special_chars > len(text) * 0.1

    def _detect_code_language(self, text):
        """检测代码语言"""
        patterns = {
            'python': [r'\bdef\b', r'\bclass\b', r'\bimport\b', r'print\('],
            'javascript': [r'\bfunction\b', r'\bconst\b', r'let ', r'=>'],
            'java': [r'\bpublic class\b', r'\bpublic void\b', r'\bstatic\b'],
            'go': [r'\bfunc\b', r'\bpackage\b', r'var\s+\w+'],
            'bash': [r'#!/', r'\bif\b', r'\bthen\b', r'fi\b'],
            'css': [r'\{', r'\}', r':\s*'],
            'html': [r'<html', r'<div', r'<body'],
        }

        scores = {}
        for lang, lang_patterns in patterns.items():
            score = sum(1 for p in lang_patterns if re.search(p, text))
            if score > 0:
                scores[lang] = score

        return max(scores.items(), key=lambda x: x[1])[0] if scores else ''

    def _to_markdown(self):
        """将解析结果转换为 Markdown"""
        md_lines = []

        for item in self.output:
            if item['type'] == 'heading':
                md_lines.append(item['text'])
                md_lines.append('')
            elif item['type'] == 'list':
                md_lines.append(item['text'])
            elif item['type'] == 'code':
                lang = item['language']
                md_lines.append(f'```{lang}')
                md_lines.append(item['text'])
                md_lines.append('```')
                md_lines.append('')
            elif item['type'] == 'paragraph':
                if item['text']:
                    md_lines.append(item['text'])
                    md_lines.append('')
            elif item['type'] == 'image':
                md_lines.append(f'![图片]({self.pdf_path.name}_page_{item["page"]}.png)')
                md_lines.append('')

        return '\n'.join(md_lines)


def main():
    parser = argparse.ArgumentParser(
        description='将 PDF 文档转换为 Markdown',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('input', help='PDF 文件路径')
    parser.add_argument('--output', '-o', required=True, help='输出 Markdown 文件路径')
    parser.add_argument('--pages', help='页面范围，如 "1-5" 或 "1,3,5"')
    parser.add_argument('--extract-images', action='store_true', help='提取图片')

    args = parser.parse_args()

    # 检查输入文件
    pdf_path = Path(args.input)
    if not pdf_path.exists():
        print(f"错误: 找不到文件 {pdf_path}")
        return 1

    # 解析 PDF
    print(f"📄 解析 PDF: {pdf_path}")
    parser_obj = PDFParser(pdf_path)
    markdown = parser_obj.parse(pages=args.pages)

    # 输出
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown)

    print(f"✓ 输出: {output_path}")
    print(f"  字符数: {len(markdown)}")

    return 0


if __name__ == '__main__':
    exit(main())
