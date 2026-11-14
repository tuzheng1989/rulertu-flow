#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF合并模块 - 使用PyPDF2合并多个PDF文件

"""
import os
import sys
from pathlib import Path
from typing import List

# 编码安全：避免 Windows GBK 控制台输出特殊符号（✓/✗）崩溃
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def merge_pdfs(
    pdf_files: List[str],
    output_pdf: str,
    delete_temp: bool = True
) -> bool:
    """
    合并多个PDF文件

    Args:
        pdf_files: PDF文件路径列表
        output_pdf: 输出PDF文件路径
        delete_temp: 是否删除临时文件

    Returns:
        bool: 合并是否成功
    """
    try:
        import PyPDF2
    except ImportError:
        print("错误：PyPDF2未安装")
        print("请运行: pip install PyPDF2")
        return False

    if not pdf_files:
        print("错误：没有PDF文件需要合并")
        return False

    # 验证所有PDF文件存在
    missing_files = [f for f in pdf_files if not os.path.exists(f)]
    if missing_files:
        print(f"错误：以下PDF文件不存在:")
        for f in missing_files:
            print(f"  - {f}")
        return False

    # 创建输出目录
    output_dir = os.path.dirname(output_pdf)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    print(f"合并 {len(pdf_files)} 个PDF文件...")

    try:
        merger = PyPDF2.PdfMerger()

        for pdf in pdf_files:
            print(f"  添加: {os.path.basename(pdf)}")
            merger.append(pdf)

        print(f"正在合并到: {os.path.basename(output_pdf)}")
        merger.write(output_pdf)
        merger.close()

        if os.path.exists(output_pdf):
            file_size = os.path.getsize(output_pdf)
            print(f"✓ 成功创建合并PDF ({file_size:,} 字节)")
            print(f"  位置: {output_pdf}")

            # 删除临时文件
            if delete_temp:
                print("\n正在清理临时文件...")
                for pdf in pdf_files:
                    try:
                        os.unlink(pdf)
                        print(f"  删除: {os.path.basename(pdf)}")
                    except Exception as e:
                        print(f"  警告: 无法删除 {os.path.basename(pdf)}: {e}")
                print("✓ 临时文件已清理")

            return True
        else:
            print("✗ PDF文件未生成")
            return False

    except Exception as e:
        print(f"✗ 合并失败: {e}")
        return False


def main():
    """命令行入口"""
    if len(sys.argv) < 3:
        print("用法: python merge.py <output.pdf> <pdf1> <pdf2> ...")
        print("示例: python merge.py output.pdf temp1.pdf temp2.pdf temp3.pdf")
        sys.exit(1)

    output_pdf = sys.argv[1]
    pdf_files = sys.argv[2:]

    success = merge_pdfs(pdf_files, output_pdf, delete_temp=True)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
