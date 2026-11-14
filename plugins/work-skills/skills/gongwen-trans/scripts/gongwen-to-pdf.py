#!/usr/bin/env python3
"""
gongwen-to-pdf.py — 将公文（Markdown 或 DOCX）转换为 PDF

PDF 输出走 docx2pdf（依赖本机 Microsoft Word 的 COM 接口），
GB/T 9704-2012 版式在 docx 侧完整实现，PDF 仅是渲染，零版式重写。

用法：
    python gongwen-to-pdf.py <input.md|input.docx> [--output out.pdf] [--keep-docx]

输入为 .md 时：先链式调用同目录 gongwen-to-docx.py 产出中间 docx，
转换成功后默认删除该中间 docx（--keep-docx 保留）。
输入为 .docx 时：直接转换，外部传入的 docx 永不删除。
"""

import argparse
import subprocess
import sys
from pathlib import Path


# ============================================================
# Word 可用性前置检测
# ============================================================

def check_word_available() -> str:
    """探测本机 Word COM：返回 "ok" / "no_pywin32" / "no_word"。"""
    try:
        import win32com.client
    except ImportError:
        return "no_pywin32"
    word = None
    try:
        word = win32com.client.Dispatch("Word.Application")
        return "ok"
    except Exception:
        return "no_word"
    finally:
        if word is not None:
            word.Quit()


# ============================================================
# 链式产出中间 docx
# ============================================================

def produce_intermediate_docx(md_path: Path, docx_path: Path) -> None:
    """调用同目录 gongwen-to-docx.py 将 Markdown 转为中间 docx。"""
    docx_script = Path(__file__).resolve().parent / "gongwen-to-docx.py"
    result = subprocess.run(
        [sys.executable, str(docx_script), str(md_path), "-o", str(docx_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not docx_path.exists():
        sys.stderr.write(result.stderr or result.stdout or "")
        print(f"错误: 中间 docx 生成失败（gongwen-to-docx.py 退出码 {result.returncode}）", file=sys.stderr)
        sys.exit(1)


# ============================================================
# docx → pdf 转换
# ============================================================

def convert_docx_to_pdf(docx_path: Path, pdf_path: Path) -> None:
    """调用 docx2pdf 转换并确认 pdf 落盘。"""
    from docx2pdf import convert

    try:
        convert(str(docx_path), str(pdf_path))
    except Exception as exc:
        print(f"错误: PDF 转换失败: {exc}", file=sys.stderr)
        print("常见原因: docx 文件被其他程序占用（请关闭后重试）。", file=sys.stderr)
        sys.exit(1)

    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        print(f"错误: 转换后未检测到有效 PDF: {pdf_path}", file=sys.stderr)
        sys.exit(1)


# ============================================================
# 主流程
# ============================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="将公文（Markdown 或 DOCX）转换为 PDF（依赖本机 Microsoft Word）"
    )
    parser.add_argument("input", help="输入 .md 或 .docx 文件路径")
    parser.add_argument("--output", help="输出 PDF 文件路径（默认: 输入文件同目录、同名 .pdf）")
    parser.add_argument(
        "--keep-docx",
        action="store_true",
        help="保留中间 docx（仅输入为 .md 时有意义；输入为 .docx 时该文件本就不会被删除）",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误: 文件不存在: {input_path}", file=sys.stderr)
        sys.exit(1)

    suffix = input_path.suffix.lower()
    if suffix not in (".md", ".docx"):
        print(f"错误: 不支持的输入类型 {suffix}（仅支持 .md / .docx）", file=sys.stderr)
        sys.exit(1)

    # Word 可用性前置检测：不可用时明确提示退出，而非转换中途栈崩溃
    word_status = check_word_available()
    if word_status == "no_pywin32":
        print("错误: 缺少 pywin32 依赖（pip install pywin32）", file=sys.stderr)
        sys.exit(1)
    if word_status == "no_word":
        print("公文 PDF 转换需要 Microsoft Word（docx2pdf 依赖 Word COM）。", file=sys.stderr)
        print("请先安装 Microsoft Word 后重试。", file=sys.stderr)
        sys.exit(1)

    # 确定输出路径（未指定时：与输入文件同目录、同名 .pdf）
    if args.output:
        pdf_path = Path(args.output)
    else:
        pdf_path = input_path.with_suffix(".pdf")

    chained_docx = suffix == ".md"
    if chained_docx:
        # 临时名防覆盖：同目录若已有同名 .docx（用户外部文件），链式产出不得覆盖后删除
        docx_path = input_path.with_name(input_path.stem + ".gongwen-tmp.docx")
        print(f"[INFO] 输入为 Markdown，先生成中间 docx: {docx_path}")
        produce_intermediate_docx(input_path, docx_path)
    else:
        docx_path = input_path

    convert_docx_to_pdf(docx_path, pdf_path)

    # 中间 docx 生命周期：仅链式产出才默认删除，外部传入的 docx 不删
    if chained_docx and not args.keep_docx:
        try:
            docx_path.unlink()
            print(f"[INFO] 已删除中间 docx: {docx_path}")
        except OSError as exc:
            print(f"警告: 中间 docx 删除失败（保留）: {exc}", file=sys.stderr)

    size_kb = pdf_path.stat().st_size / 1024
    print(f"[OK] PDF 转换完成: {pdf_path}")
    print(f"     文件大小: {size_kb:.1f} KB")

    return 0


if __name__ == "__main__":
    sys.exit(main())
