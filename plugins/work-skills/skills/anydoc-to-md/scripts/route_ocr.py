# 路由决策器：扫描版 PDF 采样试跑 Windows OCR，评分后推荐最佳引擎
# 决策矩阵:
#   有文本层           → anydoc（直接提示，不代跑）
#   扫描·页数<=8       → 建议 Claude 视觉逐页（会话内行为，打印建议）
#   扫描·评分>=70      → Windows OCR 批量（winocr.ps1，~2s/页，现代横排印刷）
#   扫描·评分<70       → DeepSeek-OCR 管线（ocr_pdf.py，古籍/竖排/繁体/复杂版面）
# 用法:
#   python route_ocr.py <PDF> [--sample N] [--json]
#   python route_ocr.py <PDF> --run -o <输出.md>   # 评分>=70 时自动跑 winocr 全书；<70 时打印 deepseek 命令
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ocr_pdf import has_text_layer, render_pages  # noqa: E402

REP_RE = re.compile(r'(.)\1{5,}')          # 同字连击>=6：乱码/循环信号
WINOCR_THRESHOLD = 70
CLAUDE_VISION_MAX_PAGES = 8


def sample_pages(total: int, k: int = 3) -> list[int]:
    """中段均匀采样 k 页（1 起算），跳过前 10% 封面/版权区"""
    lo = max(2, int(total * 0.1) + 1)
    span = max(total - lo + 1, 1)
    pages = sorted({min(lo + span * i // k, total) for i in range(k)})
    return [p for p in pages if 1 <= p <= total]


def score_text(text: str) -> dict:
    """Windows OCR 单页输出 → 质量信号与扣分。满分 100。"""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    n_chars = len(re.sub(r'\s', '', text))
    latin = len(re.findall(r'[A-Za-z]', text))
    cjk = len(re.findall(r'[一-鿿]', text))
    penalty, signals = 0.0, []

    if n_chars < 120:
        penalty += 60
        signals.append(f'字符量过低({n_chars})')
    if lines:
        short_ratio = sum(1 for ln in lines if len(ln) <= 4) / len(lines)
        avg_len = sum(len(ln) for ln in lines) / len(lines)
        if short_ratio > 0.5 and avg_len < 6:
            penalty += 40
            signals.append(f'竖排/碎行信号(短行占比{short_ratio:.0%},均长{avg_len:.1f})')
    reps = len(REP_RE.findall(text))
    if reps:
        penalty += 15 * reps
        signals.append(f'同字连击x{reps}')
    if cjk + latin > 0 and latin / (cjk + latin) > 0.5 and n_chars >= 120:
        # 中文引擎下 Latin 占主导：中文基本没识别出来（或本就是英文档——见报告人工判断）
        penalty += 30
        signals.append(f'Latin占比{latin / (cjk + latin):.0%}')
    return {'score': max(0, int(100 - penalty)), 'chars': n_chars, 'signals': signals}


def run_winocr(pages_dir: str, out_dir: str) -> str:
    ps1 = os.path.join(HERE, 'winocr.ps1')
    r = subprocess.run(
        ['powershell', '-ExecutionPolicy', 'Bypass', '-File', ps1,
         '-PagesDir', pages_dir, '-OutDir', out_dir],
        capture_output=True, text=True, timeout=3600)
    tail = (r.stdout or '').strip().splitlines()[-1:]
    if r.returncode != 0 or not any('WINOCR-DONE' in t for t in tail):
        raise RuntimeError(f'winocr.ps1 失败: {r.stderr or tail}')
    return tail[0]


def probe(pdf_path: str, k: int) -> dict:
    import pypdf
    total = len(pypdf.PdfReader(pdf_path).pages)
    if has_text_layer(pdf_path):
        return {'engine': 'anydoc', 'pages': total, 'score': None,
                'reason': '存在文本层，直接 anydoc 转换，无需 OCR'}

    pages = sample_pages(total, k)
    with tempfile.TemporaryDirectory() as td:
        pdir, odir = os.path.join(td, 'pages'), os.path.join(td, 'md')
        no_img = render_pages(pdf_path, pdir, pages)
        got = [p for p in pages if p not in no_img]
        if not got:
            return {'engine': 'deepseek', 'pages': total, 'score': None,
                    'reason': '采样页均无内嵌扫描图（渲染方式异常），交 DeepSeek 管线处理'}
        run_winocr(pdir, odir)
        results = []
        for p in got:
            md = os.path.join(odir, f'page{p:04d}.md')
            text = open(md, encoding='utf-8-sig').read() if os.path.exists(md) else ''
            results.append({'page': p, **score_text(text)})
        score = int(sum(r['score'] for r in results) / len(results)) if results else 0

    if total <= CLAUDE_VISION_MAX_PAGES:
        return {'engine': 'claude-vision', 'pages': total, 'score': score,
                'samples': results,
                'reason': f'仅 {total} 页，Claude 视觉逐页转写最快最准'}
    engine = 'winocr' if score >= WINOCR_THRESHOLD else 'deepseek'
    reason = ('Windows OCR 采样质量良好（现代横排印刷），'
              f'~2s/页' if engine == 'winocr' else
              'Windows OCR 采样质量不足（疑似古籍/竖排/繁体/复杂版面），'
              'DeepSeek-OCR 质量更稳，~30s/页')
    return {'engine': engine, 'pages': total, 'score': score,
            'samples': results, 'reason': reason}


def merge_winocr(md_dir: str, out_path: str) -> int:
    """按页序合并 winocr 逐页结果为单文件"""
    n = 0
    with open(out_path, 'w', encoding='utf-8') as out:
        for name in sorted(os.listdir(md_dir)):
            if not re.fullmatch(r'page\d{4}\.md', name):
                continue
            out.write(open(os.path.join(md_dir, name), encoding='utf-8-sig').read().strip())
            out.write('\n\n')
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description='anydoc-to-md OCR 路由决策器')
    ap.add_argument('pdf')
    ap.add_argument('--sample', type=int, default=3, help='采样页数(默认3)')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--run', action='store_true', help='按决策执行（仅 winocr 全自动）')
    ap.add_argument('-o', '--output')
    args = ap.parse_args()

    r = probe(args.pdf, args.sample)

    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"页数: {r['pages']}  采样评分: {r['score']}")
        for s in r.get('samples', []):
            print(f"  第{s['page']}页 得分{s['score']} 字符{s['chars']} {(';'.join(s['signals'])) or 'OK'}")
        print(f"→ 引擎: {r['engine']}  ({r['reason']})")

    if args.run:
        if r['engine'] == 'anydoc':
            print(f'\n执行: anydoc "{args.pdf}" -o "{args.output or "<输出.md>"}"')
        elif r['engine'] == 'claude-vision':
            print('\n由 Claude 会话直接逐页读图转写（无需脚本）。')
        elif r['engine'] == 'deepseek':
            print(f'\n执行: python "{os.path.join(HERE, "ocr_pdf.py")}" "{args.pdf}" -o "{args.output or "<输出.md>"}"')
            print('（古籍建议先 --pages 小范围试跑并调 --crop-top/--crop-side，见 SKILL.md C 节）')
        elif r['engine'] == 'winocr':
            if not args.output:
                print('需要 -o 指定输出文件'); return 2
            workdir = args.output + '.ocr'
            pdir, odir = os.path.join(workdir, 'pages'), os.path.join(workdir, 'pages-md')
            import pypdf
            total = len(pypdf.PdfReader(args.pdf).pages)
            print(f'渲染 {total} 页...', flush=True)
            render_pages(args.pdf, pdir, list(range(1, total + 1)))
            print('Windows OCR 识别中...', flush=True)
            print(run_winocr(pdir, odir))
            n = merge_winocr(odir, args.output)
            print(f'完成: {n} 页 → {args.output}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
