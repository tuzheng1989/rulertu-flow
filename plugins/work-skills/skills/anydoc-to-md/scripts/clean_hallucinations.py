#!/usr/bin/env python3
"""幻觉复读清洗器（DeepSeek-OCR 后处理）

沉淀自《赤脚医生手册》766 页八轮清理实战。DeepSeek-OCR 在插图页/密集表格页
会把图内标注或表头「无限复读」或「编造模板」，已确认八种形态：

  1. 字级刷屏        蛔虫蛔虫蛔虫…（纯中文单元 x5+）
  2. 词+标点噪声刷屏  尿胆原、尿胆原、、…（双标点破坏周期）
  3. 数字/单字空格刷屏 "2 2 2 2…"（ASCII 序列）
  4. 长单元复读       「结缔组织之间由结缔组织相连，」x50（8-60字混合单元）
  5. 递增编号复读     椎体（77节）…（192节）/ 图 21-100 名例86…（编号变化）
  6. 行级/交替重复    同行 x5+，或 A|B|A|B 交替 x4+
  7. 幻觉标签        【摘要】【解析】【查看译文】【中文标题】等
  8. 时代错位编造     论文/专利正文、现代日期、高考题、产品表、假书名（只检测报告，删除需人工确认边界）

用法:
  python clean_hallucinations.py <文件.md 或 底稿目录>          # 清洗
  python clean_hallucinations.py <路径> --check                 # 只检测报告，不改写
"""
import argparse
import os
import re
import sys
from collections import Counter

# 7. 幻觉标签（直接清除）
HALLU_TAGS = ['【查看译文】', '查看译文', '【中文标题】', '【英文标题】', '【关键词】', '【DOI】']

# 8. 时代错位哨兵（出现即报告可疑，不自动删）
SENTINELS = ['深度学习', '神经网络', '权利要求', '计算机视觉', '技术领域', '背景技术',
             '制作方法', '本文介绍', '本发明', '本实用新型', '产品名称', '含答案',
             '高考', '正方体', 'csdnimg', 'http://', 'https://']


def clean_text(t: str) -> tuple[str, dict]:
    stat = {}
    n0 = len(t)

    # 7 幻觉标签
    for tag in HALLU_TAGS:
        if tag in t:
            stat['标签'] = stat.get('标签', 0) + t.count(tag)
            t = t.replace(tag, '')

    # 1 字级刷屏
    t, c = re.subn(r'([一-鿿]{2,8})\1{4,}', r'\1', t)
    if c: stat['字级刷屏'] = c

    # 2 词+标点噪声刷屏
    t, c = re.subn(r'([一-鿿]{2,8})(?:[、，。,\s；;]*\1){3,}', r'\1', t)
    if c: stat['词噪声刷屏'] = c

    # 3 数字/单字+空格刷屏（排除表格管道符）
    t, c = re.subn(r'(?<![\w|])(\d{1,4}|[一-鿿]{1,3})(?:\s+\1){4,}(?![\w|])', r'\1', t)
    if c: stat['空格刷屏'] = c

    # 5a 递增编号复读：词（N节）连续5+ → 只留首个
    def fold_inc(m):
        seq = m.group(0)
        first = re.match(r'[一-鿿]{1,6}（\d+节）', seq)
        return first.group(0)
    t, c = re.subn(r'(?:[一-鿿]{1,6}（\d+节）[\s,，、]*){5,}', fold_inc, t)
    if c: stat['编号复读'] = c

    # 5b 图号+例号递增：图 N-M 名 例 K 连续3+ → 留首个
    def fold_fig(m):
        return re.match(r'图\s?\d+-\d+[^\n]{0,30}例\s?\d+', m.group(0)).group(0)
    t, c = re.subn(r'(?:图\s?\d+-\d+[^\n]{0,30}例\s?\d+[\s,，、]*){3,}', fold_fig, t)
    if c: stat['图例复读'] = c

    # 4 长单元复读（8-60字，迭代至稳定）
    pat_long = re.compile(r'([一-鿿0-9a-zA-Z，。、\s]{8,60}?)\1{2,}')
    total = 0
    while True:
        t2, c = pat_long.subn(lambda m: m.group(1), t)
        total += c
        if t2 == t:
            break
        t = t2
    if total: stat['长单元'] = total

    # 6 行级重复（同行≥5次只留1）
    lines = t.split('\n')
    seen, out = {}, []
    dup = 0
    for l in lines:
        key = l.strip()
        if len(key) >= 4:
            seen[key] = seen.get(key, 0) + 1
            if seen[key] >= 5:
                dup += 1
                continue
        out.append(l)
    if dup:
        stat['行重复'] = dup
        t = '\n'.join(out)

    t = re.sub(r'\n{3,}', '\n\n', t)
    stat['_削减字符'] = n0 - len(t)
    return t, stat


def check_text(t: str, whole_book: bool = False) -> list[str]:
    """whole_book=True 时行重复阈值放宽（医书固定体例/表头跨页累计属正常）"""
    issues = []
    for kw in SENTINELS:
        if kw in t:
            issues.append(kw)
    for m in re.finditer(r'20[0-3]\d年', t):
        issues.append(f'现代年份{m.group(0)}')
        break
    if re.search(r'(?:图\s?\d+-\d+[^\n]{0,30}例\s?\d+[\s,，、]*){3,}', t):
        issues.append('图例递增复读')
    if re.search(r'(?:[一-鿿]{1,6}（\d+节）[\s,，、]*){5,}', t):
        issues.append('编号递增复读')
    # 表格分隔行/固定体例行不算
    SKIP = ('|', '【诊断要点】', '【治疗】', '【预防】', '新针疗法', '草药单方', '中医辨证施治', '【生长环境】')
    threshold = 50 if whole_book else 5
    lines = [l.strip() for l in t.split('\n') if len(l.strip()) >= 8]
    for l, c in Counter(lines).items():
        if c >= threshold and not l.startswith(SKIP):
            issues.append(f'行重复x{c}:{l[:20]}')
            break
    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('target', help='md 文件或底稿目录（pages-md/）')
    ap.add_argument('--check', action='store_true', help='只检测报告，不改写')
    args = ap.parse_args()

    files = []
    if os.path.isdir(args.target):
        files = [os.path.join(args.target, f) for f in sorted(os.listdir(args.target)) if f.endswith('.md')]
    else:
        files = [args.target]

    cleaned = 0
    for p in files:
        t = open(p, encoding='utf-8').read()
        if args.check:
            issues = check_text(t, whole_book=(len(files) == 1 and os.path.getsize(p) > 300_000))
            if issues:
                print(f'{os.path.basename(p)}: {issues}')
            continue
        t2, stat = clean_text(t)
        if stat.get('_削减字符', 0) > 10:
            open(p, 'w', encoding='utf-8').write(t2)
            cleaned += 1
            print(f'{os.path.basename(p)}: {stat}')
    if args.check:
        print('（--check 模式：以上为可疑页，需人工确认边界后处理）')
    else:
        print(f'完成：{len(files)} 文件中 {cleaned} 个有实质清洗')


if __name__ == '__main__':
    sys.exit(main())
