"""归一化 codex 评审 JSON 并校验必需字段。

部分代理（如 cc-switch）会丢弃 codex --output-schema 的 json_schema 约束，
导致字段名漂移（实测：review→overall_quality、fix→suggestion）。
本脚本把已知漂移映射回标准字段，再校验必需字段齐全。

用法: python normalize.py <review.json>
退出码: 0=合法（已原地归一化写回） 1=缺少必需字段
"""
import json
import sys

path = sys.argv[1]
d = json.load(open(path, encoding="utf-8"))

if "overall_quality" not in d and "review" in d:
    d["overall_quality"] = d.pop("review")
for issue in d.get("issues", []):
    if "suggestion" not in issue and "fix" in issue:
        issue["suggestion"] = issue.pop("fix")
d.setdefault("suggestions", [])

ok = (
    isinstance(d.get("score"), (int, float))
    and isinstance(d.get("issues"), list)
    and "overall_quality" in d
)
for issue in d["issues"]:
    ok = ok and issue.get("severity") in ("P0", "P1", "P2") and issue.get("title") and issue.get("detail")

if not ok:
    sys.exit(1)
json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
