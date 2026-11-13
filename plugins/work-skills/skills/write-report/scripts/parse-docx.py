#!/usr/bin/env python3
"""
DOCX 文档解析器
将 Word 文档 (DOCX) 转换为 Markdown 格式

依赖:
    pip install python-docx pymdown-extensions

使用方法:
    python parse-docx.py input.docx --output output.md
    python parse-docx.py input.docx --output output.md --preserve-format
"""

import re
import argparse
from pathlib import Path
from datetime import datetime

try:
    from docx import Document
    from docx.shared import Pt
except ImportError:
    print("错误: 需要安装 python-docx")
    print("请运行: pip install python-docx")
    exit(1)


class DocxParser:
    """DOCX 文档解析器"""

    def __init__(self, docx_path):
        self.docx_path = Path(docx_path)
        self.doc = Document(str(docx_path))
        self.output = []
        self.in_code_block = False
        self.code_language = ''
        self.code_buffer = []

    def parse(self, preserve_format=False):
        """
        解析 DOCX 文档

        Args:
            preserve_format: 是否保留原始格式（加粗、斜体等）
        """
        for paragraph in self.doc.paragraphs:
            self._parse_paragraph(paragraph, preserve_format)

        for table in self.doc.tables:
            self._parse_table(table)

        # 处理未完成的代码块
        if self.in_code_block:
            self._flush_code_block()

        return self._to_markdown()

    def _parse_paragraph(self, paragraph, preserve_format):
        """解析段落"""
        style_name = paragraph.style.name
        text = paragraph.text.strip()

        if not text:
            self.output.append({'type': 'empty'})
            return

        # 检测标题
        if 'Heading' in style_name:
            level = self._get_heading_level(style_name)
            self.output.append({
                'type': 'heading',
                'level': level,
                'text': '#' * level + ' ' + text
            })
        # 检测列表
        elif paragraph.style.name.startswith('List'):
            list_char = self._get_list_char(paragraph)
            self.output.append({
                'type': 'list',
                'text': f"{list_char} {text}"
            })
        # 检测代码块
        elif self._is_code_paragraph(paragraph):
            self._handle_code_block(paragraph)
        # 普通段落
        else:
            formatted_text = self._format_text(paragraph, preserve_format)
            self.output.append({
                'type': 'paragraph',
                'text': formatted_text
            })

    def _parse_table(self, table):
        """解析表格为易读的文字格式"""
        rows = []

        # 分析表格，寻找真正的表头
        first_row = table.rows[0] if table.rows else None
        if not first_row:
            return

        # 获取所有单元格内容
        all_headers = [self._format_cell(cell).strip() for cell in first_row.cells]

        # 去重表头，保留首次出现的
        seen_headers = set()
        unique_headers = []
        header_indices = []

        for i, header in enumerate(all_headers):
            if header and header not in seen_headers:
                seen_headers.add(header)
                unique_headers.append(header)
                header_indices.append(i)

        if not header_indices:
            return

        # 添加章节标题
        if unique_headers:
            # 取第一个有效表头作为章节标题
            section_title = unique_headers[0].split('、')[0].strip()
            rows.append(f'\n## {section_title}')

        # 处理数据行
        for row_idx, row in enumerate(table.rows[1:], start=1):
            cells_text = []
            for i in header_indices:
                if i < len(row.cells):
                    cell_text = self._format_cell(row.cells[i]).strip()
                    cells_text.append(cell_text)
                else:
                    cells_text.append('')

            # 过滤空行和全是空白的行
            if any(cell.strip() for cell in cells_text):
                # 第一列作为标签，其余作为值
                if cells_text[0]:
                    label = cells_text[0]
                    values = [v for v in cells_text[1:] if v.strip()]

                    if values:
                        # 去重值
                        unique_values = []
                        seen_values = set()
                        for v in values:
                            if v not in seen_values:
                                seen_values.add(v)
                                unique_values.append(v)

                        value_text = '、'.join(unique_values) if len(unique_values) > 1 else unique_values[0]
                        rows.append(f'**{label}**: {value_text}')
                    else:
                        # 只有标签，没有值
                        if label and not any(c.isdigit() for c in label if len(label) < 5):
                            rows.append(f'**{label}**')

        table_md = '\n'.join(rows)
        self.output.append({
            'type': 'table',
            'text': table_md
        })

    def _format_cell(self, cell):
        """格式化表格单元格"""
        return ' '.join(p.text.strip() for p in cell.paragraphs)

    def _format_text(self, paragraph, preserve_format):
        """格式化文本（处理加粗、斜体等）"""
        if not preserve_format:
            return paragraph.text.strip()

        runs = paragraph.runs
        formatted_parts = []

        for run in runs:
            text = run.text
            if not text:
                continue

            # 处理加粗
            if run.bold:
                text = f"**{text}**"
            # 处理斜体
            elif run.italic:
                text = f"*{text}*"
            # 处理删除线
            elif run.strike:
                text = f"~~{text}~~"

            # 处理链接
            if run.hyperlink:
                url = run.hyperlink.address
                text = f"[{text}]({url})"

            formatted_parts.append(text)

        return ''.join(formatted_parts)

    def _get_heading_level(self, style_name):
        """从样式名称提取标题级别"""
        match = re.search(r'Heading\s*(\d)', style_name)
        if match:
            return int(match.group(1))
        return 2  # 默认 H2

    def _get_list_char(self, paragraph):
        """获取列表符号"""
        # 根据段落样式判断
        if 'Bullet' in paragraph.style.name:
            return '-'
        else:
            # 获取列表编号
            return paragraph.style._element.pPr.numPr.ilvl.val if paragraph._element.pPr.numPr else '1.'

    def _is_code_paragraph(self, paragraph):
        """检测是否为代码段落"""
        text = paragraph.text

        # 代码特征检测
        code_indicators = [
            text.startswith('```'),
            text.startswith('    '),
            any(char in text for char in '{}()[];:,.<>'),
            sum(1 for c in text if c in '{}();:') / max(len(text), 1) > 0.15
        ]

        return any(code_indicators)

    def _handle_code_block(self, paragraph):
        """处理代码块"""
        text = paragraph.text.strip()

        # 检测代码块开始/结束
        if text.startswith('```'):
            if self.in_code_block:
                # 结束代码块
                self._flush_code_block()
                self.in_code_block = False
            else:
                # 开始代码块
                self.in_code_block = True
                self.code_language = text[3:].strip()
        elif self.in_code_block:
            # 收集代码内容
            self.code_buffer.append(text)
        else:
            # 单行代码
            language = self._detect_code_language(text)
            self.output.append({
                'type': 'code',
                'text': text,
                'language': language
            })

    def _flush_code_block(self):
        """刷新代码块缓冲区"""
        if self.code_buffer:
            code = '\n'.join(self.code_buffer)
            self.output.append({
                'type': 'code_block',
                'text': code,
                'language': self.code_language
            })
        self.code_buffer = []

    def _detect_code_language(self, text):
        """检测代码语言"""
        patterns = {
            'python': [r'\bdef\b', r'\bclass\b', r'\bimport\b', r'print\('],
            'javascript': [r'\bfunction\b', r'\bconst\b', r'let ', r'=>'],
            'typescript': [r'\binterface\b', r'\btype\b', r': string'],
            'java': [r'\bpublic class\b', r'\bpublic void\b', r'\bstatic\b'],
            'go': [r'\bfunc\b', r'\bpackage\b', r'var\s+\w+'],
            'bash': [r'#!/', r'\bif\b', r'\bthen\b', r'fi\b'],
            'sql': [r'\bSELECT\b', r'\bFROM\b', r'\bWHERE\b'],
            'json': [r'^\s*\{', r'^\s*\['],
            'xml': [r'<\?xml', r'</\w+>'],
        }

        scores = {}
        for lang, lang_patterns in patterns.items():
            score = sum(1 for p in lang_patterns if re.search(p, text, re.IGNORECASE))
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
            elif item['type'] in ['code', 'code_block']:
                lang = item.get('language', '')
                md_lines.append(f'```{lang}')
                md_lines.append(item['text'])
                md_lines.append('```')
                md_lines.append('')
            elif item['type'] == 'paragraph':
                if item['text']:
                    md_lines.append(item['text'])
                    md_lines.append('')
            elif item['type'] == 'table':
                md_lines.append(item['text'])
                md_lines.append('')
            elif item['type'] == 'empty':
                md_lines.append('')

        return '\n'.join(md_lines)


def main():
    parser = argparse.ArgumentParser(
        description='将 DOCX 文档转换为 Markdown',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('input', help='DOCX 文件路径')
    parser.add_argument('--output', '-o', required=True, help='输出 Markdown 文件路径')
    parser.add_argument('--preserve-format', action='store_true', help='保留原始格式（加粗、斜体等）')

    args = parser.parse_args()

    # 检查输入文件
    docx_path = Path(args.input)
    if not docx_path.exists():
        print(f"错误: 找不到文件 {docx_path}")
        return 1

    # 解析 DOCX
    print(f"📄 解析 DOCX: {docx_path}")
    parser_obj = DocxParser(docx_path)
    markdown = parser_obj.parse(preserve_format=args.preserve_format)

    # 输出
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown)

    print(f"✓ 输出: {output_path}")
    print(f"  字符数: {len(markdown)}")
    print(f"  段落数: {len(parser_obj.doc.paragraphs)}")
    print(f"  表格数: {len(parser_obj.doc.tables)}")

    return 0


if __name__ == '__main__':
    exit(main())
