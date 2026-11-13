#!/usr/bin/env python3
"""
Long-Text Chapter Merger
整合多个章节文件为单一文档

使用方法:
    python merge.py --workspace workspace/{project-name}
    python merge.py --workspace workspace/{project-name} --output my-document.md
"""

import re
import os
import argparse
from pathlib import Path
from datetime import datetime


def parse_structure(structure_path):
    """解析 00-structure.md 文件，提取元信息和章节列表"""
    with open(structure_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取元信息
    meta = {}
    meta_pattern = r'- \*\*(.+?)\*\*:\s*(.+)'
    for match in re.finditer(meta_pattern, content):
        key, value = match.groups()
        meta[key.strip()] = value.strip()

    # 提取章节列表
    chapters = []
    table_pattern = r'\|\s*(\d+)\s*\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|\s*(\d+)\s*\|\s*(\w+)\s*\|'
    for match in re.finditer(table_pattern, content):
        num, title, summary, words, status = match.groups()
        chapters.append({
            'number': int(num),
            'title': title.strip(),
            'summary': summary.strip(),
            'words': int(words),
            'status': status.strip()
        })

    return meta, chapters


def read_chapter(workspace, chapter_num):
    """读取单个章节文件"""
    chapter_path = workspace / f'chapter-{chapter_num:02d}.md'
    if not chapter_path.exists():
        return None

    with open(chapter_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 移除章节开头的 # 标题（将在整合时统一添加）
    content = re.sub(r'^# .+\n+', '', content, count=1)

    return content


def generate_toc(chapters):
    """生成目录"""
    toc = "## 目录\n\n"
    for ch in chapters:
        if ch['status'] in ['completed', 'reviewed']:
            # 生成锚点链接
            anchor = ch['title'].lower().replace(' ', '-').replace('/', '-')
            # 移除特殊字符
            anchor = re.sub(r'[^\w\u4e00-\u9fff-]', '', anchor)
            toc += f"{ch['number']}. [{ch['title']}](#{ch['number']}-{anchor})\n"
    return toc + "\n---\n\n"


def merge_document(meta, chapters, workspace):
    """整合完整文档"""
    output = []

    # 文档标题页
    output.append(f"# {meta.get('文档标题', '未命名文档')}\n")
    output.append("---\n\n")

    # 元信息
    if meta.get('创建时间'):
        output.append(f"**创建时间**: {meta.get('创建时间')}\n")
    if meta.get('目标读者'):
        output.append(f"**目标读者**: {meta.get('目标读者')}\n")
    if meta.get('预期字数'):
        output.append(f"**预期字数**: {meta.get('预期字数')}\n")
    if meta.get('文档类型'):
        output.append(f"**文档类型**: {meta.get('文档类型')}\n")
    output.append("\n")

    # 目录
    output.append(generate_toc(chapters))

    # 章节内容
    for ch in chapters:
        if ch['status'] in ['completed', 'reviewed']:
            content = read_chapter(workspace, ch['number'])
            if content:
                output.append(f"\n## {ch['number']}. {ch['title']}\n\n")
                output.append(content)
                output.append("\n---\n")

    return ''.join(output)


def main():
    parser = argparse.ArgumentParser(description='整合长文档章节', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--workspace', required=True, help='工作区路径（包含 00-structure.md 和 chapter-*.md 文件）')
    parser.add_argument('--output', default='final-output.md', help='输出文件名（默认: final-output.md）')
    parser.add_argument('--dry-run', action='store_true', help='预览整合结果但不写入文件')

    args = parser.parse_args()

    workspace = Path(args.workspace)
    structure_path = workspace / '00-structure.md'

    if not structure_path.exists():
        print(f"错误: 找不到结构文件 {structure_path}")
        print(f"请确保工作区包含 00-structure.md 文件")
        return 1

    # 解析结构
    meta, chapters = parse_structure(structure_path)

    if not chapters:
        print(f"警告: {structure_path} 中未找到章节定义")

    # 统计信息
    completed_count = sum(1 for c in chapters if c['status'] in ['completed', 'reviewed'])
    total_words = sum(c.get('words', 0) for c in chapters if c['status'] in ['completed', 'reviewed'])

    print(f"📄 文档整合任务")
    print(f"  工作区: {workspace}")
    print(f"  文档标题: {meta.get('文档标题', '未命名')}")
    print(f"  总章节数: {len(chapters)}")
    print(f"  已完成: {completed_count}")
    print(f"  预估字数: {total_words}")
    print()

    # 整合文档
    content = merge_document(meta, chapters, workspace)

    if args.dry_run:
        print("--- 预览前 500 字符 ---")
        print(content[:500])
        print("...")
        return 0

    # 输出
    output_path = workspace / args.output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✓ 文档已整合: {output_path}")
    print(f"  文件大小: {len(content)} 字符")
    return 0


if __name__ == '__main__':
    exit(main())
