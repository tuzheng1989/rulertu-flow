#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML to PDF 转换器（统一版）

单文件 / 批量 / 智能检测演示文稿 一站式解决。

核心设计（基于实战经验）：
  1. 自动推断设计尺寸 —— 从 HTML 的 body{width;height} 读出像素值，
     换算为英寸（÷96 DPI）注入 @page，从而在「渲染时」就使用正确纸张，
     而非事后缩放（事后缩放会破坏布局，治标不治本）。
  2. 注入打印 CSS —— @page size（必须用 in/cm 等长度单位，px 无效）+
     margin:0 + print-color-adjust:exact（保背景色/渐变）+ body 尺寸锁定。
  3. 全程绝对路径 —— Chrome headless 无法解析相对输出路径（错误 0x3）。
  4. --virtual-time-budget —— 虚拟时钟快速推进，避免 Google Fonts 等
     外部资源加载导致超时。
  5. 编码安全 —— stdout 强制 UTF-8，日志用纯 ASCII 标记。

CLI:
  python convert.py <input> <output.pdf> [options]

  input  : 单个 HTML 文件 / 目录（自动识别 slides/ 结构）/ 通配符
"""
import sys
import os
import re
import glob
import subprocess

# ---- 编码安全：避免 Windows GBK 控制台崩溃（✓/✗ 等字符）----
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 纯 ASCII 状态标记，双重保险
OK_MARK = "[OK]"
FAIL_MARK = "[FAIL]"


# ---------------------------------------------------------------------------
# Chrome 定位
# ---------------------------------------------------------------------------
def find_chrome() -> str:
    """查找 Chrome / Chromium 可执行文件路径，找不到返回空字符串。"""
    candidates = [
        os.environ.get("CHROME_PATH", ""),  # 环境变量优先
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return ""


# ---------------------------------------------------------------------------
# 尺寸推断：从 HTML body 检测固定设计尺寸（像素）
# ---------------------------------------------------------------------------
def detect_design_size(html_text: str):
    """
    解析 body { ... width: Npx; ... height: Mpx; ... }，返回 (width, height)。
    找不到固定像素尺寸（文档流型 HTML）时返回 None，由调用方回退到预设纸张。

    兼容 <style> 块与内联 style 属性；body 选择器可能跨多行。
    """
    # body { ... } 块（非贪婪到第一个 }，支持换行）
    body_blocks = re.findall(r"body\s*\{([^}]*)\}", html_text, re.IGNORECASE | re.DOTALL)
    body_css = "\n".join(body_blocks)

    width = height = None
    m = re.search(r"(?:^|[\s;{])width\s*:\s*(\d+(?:\.\d+)?)\s*px", body_css, re.IGNORECASE)
    if m:
        width = float(m.group(1))
    m = re.search(r"(?:^|[\s;{])height\s*:\s*(\d+(?:\.\d+)?)\s*px", body_css, re.IGNORECASE)
    if m:
        height = float(m.group(1))

    if width and height and width > 0 and height > 0:
        return (width, height)
    return None


def px_to_inches(px: float) -> float:
    """像素转英寸（Web 标准 96 DPI）。"""
    return px / 96.0


def fmt_inches(v: float) -> str:
    """格式化英寸值，去除无意义尾零（20.0 -> '20', 11.25 -> '11.25'）。"""
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s if s else "0"


# ---------------------------------------------------------------------------
# 打印 CSS 注入
# ---------------------------------------------------------------------------
def build_print_css(design_size, page_size: str = "", margin: str = "0"):
    """
    构造 @media print CSS。

    design_size 优先：按其换算 @page size（in）并锁定 body 像素尺寸。
    否则用 page_size（如 'A4'、'Letter'、'8.5in 11in'），不锁定 body。
    """
    if design_size:
        w_in, h_in = px_to_inches(design_size[0]), px_to_inches(design_size[1])
        page_size_value = f"{fmt_inches(w_in)}in {fmt_inches(h_in)}in"
        body_lock = (
            f"  html, body {{\n"
            f"    width: {int(design_size[0])}px !important;\n"
            f"    height: {int(design_size[1])}px !important;\n"
            f"    max-width: {int(design_size[0])}px !important;\n"
            f"    overflow: hidden !important;\n"
            f"  }}\n"
        )
    else:
        page_size_value = page_size or "A4"
        body_lock = ""

    return (
        "<style>\n"
        "@media print {\n"
        f"  @page {{ size: {page_size_value}; margin: {margin}; }}\n"
        f"{body_lock}"
        "  * {\n"
        "    -webkit-print-color-adjust: exact !important;\n"
        "    print-color-adjust: exact !important;\n"
        "  }\n"
        "}\n"
        "</style>\n"
    )


def inject_css(html_text: str, css: str) -> str:
    """把 CSS 注入 HTML（优先 </head> 前，其次 <body> 前，最后追加到开头）。"""
    if "</head>" in html_text:
        return html_text.replace("</head>", css + "</head>", 1)
    if "<body" in html_text:
        return re.sub(r"(<body)", css + r"\1", html_text, count=1)
    return css + html_text


# ---------------------------------------------------------------------------
# 文件发现
# ---------------------------------------------------------------------------
def find_html_files(input_path: str):
    """
    收集待转换的 HTML 文件列表（已排序）。

    支持单文件 / 目录 / 通配符；目录下若有 slides/ 子目录则优先取之。
    始终排除以 temp_ 开头的临时文件。
    """
    if os.path.isfile(input_path):
        return [input_path] if input_path.lower().endswith(".html") else []

    if os.path.isdir(input_path):
        slides_dir = os.path.join(input_path, "slides")
        base = slides_dir if os.path.isdir(slides_dir) else input_path
        files = sorted(glob.glob(os.path.join(base, "*.html")))
    else:
        # 通配符
        files = sorted(glob.glob(input_path))
        files = [f for f in files if f.lower().endswith(".html")]

    return [f for f in files if not os.path.basename(f).startswith("temp_")]


# ---------------------------------------------------------------------------
# 单文件转换
# ---------------------------------------------------------------------------
def convert_one(
    html_file: str,
    output_pdf: str,
    chrome_path: str,
    auto_size: bool = True,
    page_size: str = "",
    margin: str = "0",
    timeout: int = 180,
) -> bool:
    """转换单个 HTML 为 PDF。注入打印 CSS 后调用 Chrome headless。"""
    abs_output = os.path.abspath(output_pdf)
    os.makedirs(os.path.dirname(abs_output) or ".", exist_ok=True)

    with open(html_file, "r", encoding="utf-8", errors="ignore") as f:
        html_text = f.read()

    # 尺寸推断（可被 auto_size=False 关闭，或 page_size 覆盖）
    design_size = detect_design_size(html_text) if auto_size else None
    if design_size:
        w_in, h_in = px_to_inches(design_size[0]), px_to_inches(design_size[1])
        print(
            f"    design: {int(design_size[0])}x{int(design_size[1])}px "
            f"-> {fmt_inches(w_in)}in x {fmt_inches(h_in)}in"
        )

    css = build_print_css(design_size, page_size=page_size, margin=margin)
    html_text = inject_css(html_text, css)

    # 写临时 HTML（与目标 PDF 同目录），用绝对路径交给 Chrome
    temp_html = abs_output[:-4] + "_print.html"
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_text)

    file_url = "file:///" + temp_html.replace(os.sep, "/")
    cmd = [
        chrome_path,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        f"--print-to-pdf={abs_output}",  # 绝对路径！相对路径会报错 0x3
        "--virtual-time-budget=10000",   # 虚拟时钟，避免外部资源加载超时
        "--run-all-compositor-stages-before-draw",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if design_size:
        cmd.append(f"--window-size={int(design_size[0])},{int(design_size[1])}")
    cmd.append(file_url)

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"    {FAIL_MARK} 超时（{timeout}s）")
        _safe_remove(temp_html)
        return False
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode("utf-8", errors="ignore") if e.stderr else ""
        # 提取关键错误行
        key = _extract_key_error(err)
        print(f"    {FAIL_MARK} Chrome 退出码 {e.returncode}: {key}")
        _safe_remove(temp_html)
        return False
    finally:
        _safe_remove(temp_html)

    return os.path.exists(abs_output)


def _extract_key_error(stderr: str) -> str:
    """从 Chrome stderr 中提取一行人类可读的关键错误。"""
    for line in stderr.splitlines():
        if "ERROR" in line and ("write file" in line.lower() or "path" in line.lower()
                                or "failed" in line.lower()):
            return line.strip()[:160]
    return stderr.strip().splitlines()[-1][:160] if stderr.strip() else ""


def _safe_remove(path: str):
    try:
        if path and os.path.exists(path):
            os.unlink(path)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# 合并 + 验证
# ---------------------------------------------------------------------------
def merge_pdfs(pdf_files, output_pdf: str, keep_temp: bool = False) -> bool:
    """用 PyPDF2 合并多个 PDF。"""
    try:
        import PyPDF2
    except ImportError:
        print("[ERROR] PyPDF2 未安装，请运行: pip install PyPDF2")
        print("临时 PDF 已保留，可手动合并:")
        for p in pdf_files:
            print(f"  - {p}")
        return False

    os.makedirs(os.path.dirname(os.path.abspath(output_pdf)) or ".", exist_ok=True)
    merger = PyPDF2.PdfMerger()
    try:
        for pdf in pdf_files:
            merger.append(pdf)
        merger.write(output_pdf)
        merger.close()
    except Exception as e:
        print(f"[ERROR] 合并失败: {e}")
        return False

    if not os.path.exists(output_pdf):
        print("[ERROR] 合并产物未生成")
        return False

    print(f"[OK] 已合并 {len(pdf_files)} 个文件 -> {output_pdf}")
    print(f"     大小: {os.path.getsize(output_pdf):,} 字节")

    if not keep_temp:
        for pdf in pdf_files:
            _safe_remove(pdf)
    return True


def verify_pdf(pdf: str):
    """读取首页尺寸并打印，便于排查比例问题。fitz 缺失时静默跳过。"""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return
    try:
        doc = fitz.open(pdf)
        if len(doc) > 0:
            r = doc[0].rect
            ratio = r.width / r.height if r.height else 0
            print(f"     首页尺寸: {r.width:.1f} x {r.height:.1f} pt "
                  f"({r.width/72:.2f} x {r.height/72:.2f} in), 比例 {ratio:.4f}")
        doc.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 批量入口
# ---------------------------------------------------------------------------
def batch_convert(
    input_path: str,
    output_pdf: str,
    auto_size: bool = True,
    page_size: str = "",
    margin: str = "0",
    keep_temp: bool = False,
) -> bool:
    """批量转换：单文件直接输出；多文件逐个转换后合并。"""
    chrome_path = find_chrome()
    if not chrome_path:
        print("[ERROR] 未找到 Chrome。请安装，或设置 CHROME_PATH 环境变量。")
        return False
    print(f"Chrome: {chrome_path}")

    html_files = find_html_files(input_path)
    if not html_files:
        print(f"[ERROR] 未找到 HTML 文件: {input_path}")
        return False
    print(f"发现 {len(html_files)} 个 HTML 文件")

    abs_output = os.path.abspath(output_pdf)
    temp_dir = os.path.join(os.path.dirname(abs_output) or ".", ".html2pdf_tmp")
    os.makedirs(temp_dir, exist_ok=True)

    is_single = len(html_files) == 1
    produced = []

    for i, html in enumerate(html_files, 1):
        name = os.path.splitext(os.path.basename(html))[0]
        if is_single:
            out = abs_output  # 单文件直接输出到目标
        else:
            out = os.path.join(temp_dir, f"{i:02d}_{name}.pdf")
        print(f"[{i}/{len(html_files)}] {os.path.basename(html)} ...", end="")
        ok = convert_one(
            html, out, chrome_path,
            auto_size=auto_size, page_size=page_size, margin=margin,
        )
        print(f" {OK_MARK if ok else FAIL_MARK}")
        if ok:
            produced.append(out)

    print(f"\n成功 {len(produced)}/{len(html_files)}")
    if not produced:
        return False

    if is_single:
        print(f"[OK] 输出: {abs_output}")
        verify_pdf(abs_output)
        return True

    # 多文件合并
    ok = merge_pdfs(produced, abs_output, keep_temp=keep_temp)
    if ok:
        verify_pdf(abs_output)
        # 清理临时目录
        if not keep_temp:
            try:
                os.rmdir(temp_dir)
            except OSError:
                pass
    return ok


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) < 2:
        print(__doc__)
        print("\n用法: python convert.py <input> <output.pdf> [options]")
        print("  --page-size SIZE   强制纸张（如 A4 / Letter / 8.5in 11in），关闭自动推断")
        print("  --no-auto-size     关闭尺寸自动推断，用 Chrome 默认纸张")
        print("  --margin M         页边距（默认 0），如 '10mm'")
        print("  --keep-temp        保留中间 PDF")
        return 1

    input_path = argv[0]
    output_pdf = argv[1]
    auto_size = True
    page_size = ""
    margin = "0"
    keep_temp = False

    i = 2
    while i < len(argv):
        a = argv[i]
        if a == "--page-size" and i + 1 < len(argv):
            page_size = argv[i + 1]; auto_size = False; i += 2
        elif a == "--no-auto-size":
            auto_size = False; i += 1
        elif a == "--margin" and i + 1 < len(argv):
            margin = argv[i + 1]; i += 2
        elif a == "--keep-temp":
            keep_temp = True; i += 1
        else:
            print(f"[WARN] 未知参数: {a}"); i += 1

    return 0 if batch_convert(
        input_path, output_pdf,
        auto_size=auto_size, page_size=page_size,
        margin=margin, keep_temp=keep_temp,
    ) else 1


if __name__ == "__main__":
    sys.exit(main())
