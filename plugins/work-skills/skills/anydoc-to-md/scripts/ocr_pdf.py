#!/usr/bin/env python3
# 扫描版 PDF → Markdown OCR 管线（DeepSeek-OCR + llama.cpp）
#
# 沉淀自《妇人大全良方》631 页全流程实战，关键经验：
#   1. 串行 OCR（并行双请求会挤爆 KV 池返回 500）
#   2. 温度 0 + top-k 1（OCR 要确定性，不要采样）
#   3. 裁掉页眉/边栏可根治「页眉艺术字诱导的循环输出」（最高频故障）
#   4. 裁剪后顶部加 60px 白边，防首行贴边被漏识
#   5. 奇偶页装订方向不同 → 边栏位置镜像 → 需差异化裁剪
#   6. 循环检测（同句≥5/字符集≤4）拦截退化输出，失败页不写盘保留重试机会
#   7. 断点续传：按页落盘，中断后重跑自动跳过已完成页
#
# 用法:
#   python ocr_pdf.py <输入.pdf> -o <输出.md> [选项]
# 选项:
#   --pages A-B          只处理页范围（1 起算），如 1-50
#   --header-pattern RE  页眉清理正则（如 "中医临床必读丛书"），默认无
#   --crop-top N         裁掉顶部 N px（页眉高度，诱导循环时设置）
#   --crop-side RE       边栏裁剪 "左,右"（如 "215,1480"）；奇偶镜像自动换算
#   --workdir DIR        工作目录（默认 <输出>.ocr/），含渲染图与逐页 md
#   --port N             llama-server 端口（默认 8991）
#   --keep-server        结束后不关闭本次拉起的 server
# 环境要求（OCR_HOME 默认 ~/.cache/evo-ocr）:
#   $OCR_HOME/llama-cpp/llama-server.exe
#   $OCR_HOME/models/DeepSeek-OCR-Q8_0.gguf + mmproj-DeepSeek-OCR-Q8_0.gguf
# 首次安装见 SKILL.md「环境准备」。

import argparse
import base64
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from collections import Counter

OCR_HOME = os.environ.get('OCR_HOME', os.path.expanduser('~/.cache/evo-ocr'))
SERVER = os.path.join(OCR_HOME, 'llama-cpp', 'llama-server.exe')
MODEL = os.path.join(OCR_HOME, 'models', 'DeepSeek-OCR-Q8_0.gguf')
MMPROJ = os.path.join(OCR_HOME, 'models', 'mmproj-DeepSeek-OCR-Q8_0.gguf')
PAD_TOP = 60          # 顶部白边：防首行贴边漏识
RETRIES = 3
SENT_END = tuple('。！？…”』')


# ---------- 第 1 步：文本层检测 ----------

def has_text_layer(pdf_path: str, sample: int = 20) -> bool:
    """抽样判断是否存在文本层（有则应直接用 anydoc，无需 OCR）"""
    import pypdf
    reader = pypdf.PdfReader(pdf_path)
    pages = reader.pages[:min(sample, len(reader.pages))]
    return any((p.extract_text() or '').strip() for p in pages)


# ---------- 第 2 步：渲染 ----------

def render_pages(pdf_path: str, pages_dir: str, page_list: list[int]) -> list[int]:
    """提取指定页的内嵌扫描图为灰度 PNG，返回无内嵌图的页码"""
    import pypdf
    from PIL import Image
    os.makedirs(pages_dir, exist_ok=True)
    reader = pypdf.PdfReader(pdf_path)
    no_img = []
    for k, n in enumerate(page_list, 1):
        out = os.path.join(pages_dir, f'page{n:04d}.png')
        if os.path.exists(out):
            continue
        try:
            images = reader.pages[n - 1].images
            if not images:
                no_img.append(n)
                continue
            Image.open(io.BytesIO(images[0].data)).convert('L').save(out)
        except Exception:
            no_img.append(n)
        if k % 100 == 0:
            print(f'  渲染 {k}/{len(page_list)}', flush=True)
    return no_img


# ---------- 第 3 步：server 管理 ----------

def http_get(url: str, timeout: int = 5):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read().decode()


def wait_ready(port: int, secs: float = 120) -> bool:
    t0 = time.time()
    while time.time() - t0 < secs:
        try:
            if 'ok' in http_get(f'http://127.0.0.1:{port}/health'):
                return True
        except Exception:
            pass
        time.sleep(3)
    return False


def ensure_server(port: int) -> subprocess.Popen | None:
    """返回本脚本拉起的进程（复用已运行的则返回 None），失败抛异常"""
    try:
        if 'ok' in http_get(f'http://127.0.0.1:{port}/health'):
            print('复用已运行的 llama-server', flush=True)
            return None
    except Exception:
        pass
    for p in (SERVER, MODEL, MMPROJ):
        if not os.path.exists(p):
            raise SystemExit(f'缺 {p}，请按 SKILL.md「环境准备」安装')
    # 教训：KV 池 16384（8192 在长输出页会溢出 500）
    proc = subprocess.Popen(
        [SERVER, '-m', MODEL, '--mmproj', MMPROJ, '-c', '16384',
         '--temp', '0', '--top-k', '1', '--port', str(port), '--threads', '8'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not wait_ready(port):
        proc.terminate()
        raise SystemExit('llama-server 启动超时')
    print('llama-server 已就绪', flush=True)
    return proc


# ---------- 第 4 步：OCR ----------

def ocr_image(img, port: int) -> str:
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode()
    payload = json.dumps({'messages': [{'role': 'user', 'content': [
        {'type': 'text', 'text': 'OCR markdown'},
        {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{b64}'}}]}],
        'temperature': 0, 'top_k': 1, 'max_tokens': 4096}).encode()
    req = urllib.request.Request(
        f'http://127.0.0.1:{port}/v1/chat/completions', data=payload,
        headers={'Content-Type': 'application/json'})
    resp = json.load(urllib.request.urlopen(req, timeout=900))
    return resp['choices'][0]['message']['content']


def is_degenerate(text: str) -> bool:
    """循环退化检测：同句≥5次 / 字符集≤4 / 大量重复行"""
    if len(set(text)) <= 4:
        return True
    lines = [l.strip() for l in text.split('\n') if len(l.strip()) >= 8]
    if lines:
        top, cnt = Counter(lines).most_common(1)[0]
        if cnt >= 5:
            return True
    sents = [s.strip() for s in re.split(r'[。！？\n]', text) if len(s.strip()) >= 10]
    if sents:
        top, cnt = Counter(sents).most_common(1)[0]
        if cnt >= 5:
            return True
    return False


def build_cropped(png_path: str, odd: bool, top: int, side: tuple[int, int]):
    """按奇偶页差异化裁剪 + 顶部白边。side=(正文左界, 正文右界)"""
    from PIL import Image
    im = Image.open(png_path)
    w, h = im.size
    left, right = side if odd else (w - side[1], w - side[0])
    box = (left, top, right, h)
    c = im.crop(box)
    padded = Image.new('L', (c.size[0], c.size[1] + PAD_TOP), 255)
    padded.paste(c, (0, PAD_TOP))
    return padded


def batch_ocr(pages_dir: str, md_dir: str, port: int, page_list: list[int],
              top: int, side: tuple[int, int] | None) -> list[int]:
    """逐页 OCR（串行），返回失败页码清单"""
    os.makedirs(md_dir, exist_ok=True)
    failed, done = [], 0
    t0 = time.time()
    for n in page_list:
        out = os.path.join(md_dir, f'page{n:04d}.md')
        if os.path.exists(out) and os.path.getsize(out) > 0:
            continue  # 断点续传
        png = os.path.join(pages_dir, f'page{n:04d}.png')
        if not os.path.exists(png):
            failed.append(n)
            continue
        img = (build_cropped(png, n % 2 == 1, top, side) if side
               else _plain(png))
        ok = False
        for attempt in range(1, RETRIES + 1):
            try:
                text = ocr_image(img, port)
                if is_degenerate(text):
                    raise ValueError('循环退化')
                with open(out, 'w', encoding='utf-8') as f:
                    f.write(text)
                ok = True
                break
            except Exception as exc:
                print(f'  page{n} 第{attempt}次失败: {str(exc)[:60]}', flush=True)
                time.sleep(5 * attempt)
        if not ok:
            failed.append(n)
        done += 1
        if done % 10 == 0:
            rate = done / (time.time() - t0) * 60
            print(f'  OCR {done} 页  {rate:.1f}页/分  失败{len(failed)}', flush=True)
    return failed


def _plain(png_path: str):
    from PIL import Image
    im = Image.open(png_path)
    padded = Image.new('L', (im.size[0], im.size[1] + PAD_TOP), 255)
    padded.paste(im, (0, PAD_TOP))
    return padded


# ---------- 第 5 步：合并清理 ----------

HALF_FULL = str.maketrans({',': '，', ';': '；', ':': '：', '?': '？',
                           '!': '！', '(': '（', ')': '）'})


def clean_page(text: str, header_re: str | None) -> str:
    lines_kept = []
    lines = [l.rstrip() for l in text.split('\n')]
    for i, l in enumerate(lines):
        s = l.strip()
        if not s:
            continue
        if header_re and re.search(header_re, s) and len(s) < 60:
            continue
        if re.fullmatch(r'\d{1,4}', s) and (i < 3 or i >= len(lines) - 3):
            continue  # 页首尾独立页码行
        lines_kept.append(s)
    body = '\n'.join(lines_kept)
    # 中文邻接的半角标点转全角
    out = []
    for i, ch in enumerate(body):
        prev = body[i - 1] if i else ''
        nxt = body[i + 1] if i + 1 < len(body) else ''
        if ch in HALF_FULL and (re.match(r'[一-鿿]', prev or 'x')
                                or re.match(r'[一-鿿]', nxt or 'x')):
            out.append(ch.translate(HALF_FULL))
        else:
            out.append(ch)
    return ''.join(out)


def _norm_title(s: str) -> str:
    return re.sub(r'[#*\s（）()：:，,。、·「」《》]', '', s)


def _protected(s: str) -> bool:
    """不参与段落合并的独立行：标题/列表/目录条目/论名/注记"""
    if s.startswith(('#', '- ', '* ', '|', '〔')) or s == '---':
        return True
    if re.search(r'[·…]{2,}\s*\d{1,3}$', s):
        return True
    if re.search(r'\s\d{1,3}$', s) and len(s) < 40:
        return True
    if re.match(r'^[一二三四五六七八九十]+曰', s):
        return True
    if re.match(r'^《[^》]{1,8}》[^，。]{0,12}$', s):
        return True
    return False


def layout_pass(text: str) -> str:
    """段落重建 + 去重：非句末行并入下文；近距/栏目级重复标题唯一化"""
    out: list[str] = []
    last_norm, last_at, seen_short = '', -10, set()
    idx = 0
    for raw in text.split('\n'):
        idx += 1
        s = raw.strip()
        if not s:
            continue
        if s.startswith('#'):
            n = _norm_title(s)
            if n and n == last_norm and idx - last_at <= 4:
                continue                       # 近距重复标题
            if n and len(n) <= 6:
                if n in seen_short:
                    continue                   # 栏目级标题全书唯一
                seen_short.add(n)
            last_norm, last_at = n, idx
            if out and out[-1]:
                out.append('')
            out.extend([s, ''])
            continue
        if _protected(s):
            if out and out[-1]:
                out.append('')
            out.extend([s, ''])
            continue
        if out and out[-1] and not _protected(out[-1]) \
                and not out[-1].endswith(SENT_END) and not out[-1].endswith('：'):
            out[-1] += s                       # 段内硬换行合并
        else:
            if out and out[-1]:
                out.append('')
            out.append(s)
        if s.endswith(SENT_END):
            out.append('')
    while out and not out[-1]:
        out.pop()
    return '\n'.join(out)


def merge(md_dir: str, page_list: list[int], out_path: str,
          header_re: str | None) -> dict:
    parts, missing = [], []
    for n in page_list:
        p = os.path.join(md_dir, f'page{n:04d}.md')
        if not os.path.exists(p):
            missing.append(n)
            continue
        parts.append(clean_page(open(p, encoding='utf-8').read(), header_re))
        parts.append('')
    text = layout_pass('\n'.join(parts))
    text = re.sub(r'\n{3,}', '\n\n', text)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(text)
    return {'chars': len(text), 'missing_pages': missing}


# ---------- 主流程 ----------

def parse_side(v: str | None) -> tuple[int, int] | None:
    if not v:
        return None
    a, b = v.split(',')
    return int(a), int(b)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf')
    ap.add_argument('-o', '--output', required=True)
    ap.add_argument('--pages')
    ap.add_argument('--header-pattern')
    ap.add_argument('--crop-top', type=int, default=0)
    ap.add_argument('--crop-side')
    ap.add_argument('--workdir')
    ap.add_argument('--port', type=int, default=8991)
    ap.add_argument('--keep-server', action='store_true')
    args = ap.parse_args()

    import pypdf  # 延迟导入：仅 OCR 场景需要
    total = len(pypdf.PdfReader(args.pdf).pages)
    lo, hi = (1, total)
    if args.pages:
        lo, hi = (int(x) for x in args.pages.split('-'))
    page_list = list(range(lo, min(hi, total) + 1))
    workdir = args.workdir or args.output + '.ocr'
    pages_dir = os.path.join(workdir, 'pages')
    md_dir = os.path.join(workdir, 'pages-md')
    print(f'共 {total} 页，处理 {lo}-{min(hi, total)}，工作目录 {workdir}', flush=True)

    if has_text_layer(args.pdf):
        print('⚠️ 检测到文本层：此 PDF 可直接用 anydoc 转换，无需 OCR。'
              '如确需 OCR 请人工确认后重读代码移除此检查。', flush=True)
        return 2

    print('== 渲染 ==', flush=True)
    no_img = render_pages(args.pdf, pages_dir, page_list)
    if no_img:
        print(f'  无内嵌图页（跳过）: {no_img[:10]}{"..." if len(no_img) > 10 else ""}',
              flush=True)

    print('== OCR ==', flush=True)
    proc = ensure_server(args.port)
    try:
        failed = batch_ocr(pages_dir, md_dir, args.port, page_list,
                           args.crop_top, parse_side(args.crop_side))
    finally:
        if proc and not args.keep_server:
            proc.terminate()
            print('llama-server 已关闭（--keep-server 可保留复用）', flush=True)

    print('== 合并 ==', flush=True)
    stat = merge(md_dir, page_list, args.output, args.header_pattern)
    print(f"输出 {args.output}（{stat['chars']} 字）", flush=True)

    # 质量报告：失败页需人工兜底（读原图转录）
    todo = sorted(set(failed) | set(stat['missing_pages']))
    if todo:
        print(f'\n⚠️ {len(todo)} 页未成功，需人工兜底（读图转录后写 '
              f'{md_dir}/pageNNNN.md 再重跑本脚本合并）:\n  {todo}', flush=True)
    print('提示：合并为通用清理。书籍级结构整理（卷次/目录/页眉变体）'
          '请参照 SKILL.md「进阶清理」人工复核。', flush=True)
    return 1 if todo else 0


if __name__ == '__main__':
    sys.exit(main())
