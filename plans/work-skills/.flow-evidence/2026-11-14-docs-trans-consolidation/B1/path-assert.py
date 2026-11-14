# B1 路径断言：四份 mode 文档中的脚本引用，从 modes/ 目录出发解析
import os, re, sys

MODES = r"C:\Users\tuzhe\runspace\rulertu-flow\plugins\work-skills\skills\docs-trans\modes"

# 从每份文档 grep 提取 ../scripts/... 引用（截到反引号/空白/引号前）
refs = {}  # doc -> list of (line_no, path)
for doc in ["anydoc-to-md.md", "url-to-md.md", "md-to-pdf.md", "html-to-pdf.md"]:
    refs[doc] = []
    with open(os.path.join(MODES, doc), encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            for m in re.finditer(r"\.\./scripts/[A-Za-z0-9_\-./]+", line):
                p = m.group(0).rstrip(".")
                refs[doc].append((i, p))

total, failed = 0, []
for doc, items in refs.items():
    for ln, p in items:
        total += 1
        full = os.path.normpath(os.path.join(MODES, p))
        ok = os.path.exists(full)
        print(f"{'PASS' if ok else 'FAIL'}  {doc}:{ln}  {p}")
        if not ok:
            failed.append((doc, ln, p))

# 去重后的唯一目标文件数
uniq = sorted({p for items in refs.values() for _, p in items})
print(f"\n断言总数: {total}  唯一路径: {len(uniq)}  失败: {len(failed)}")
print("唯一路径清单:")
for p in uniq:
    print("  ", p)
sys.exit(1 if failed else 0)
