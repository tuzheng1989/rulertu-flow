#!/usr/bin/env python3
"""Compare performance metric JSON files using explicit budgets."""

from __future__ import annotations

import json
import sys
from pathlib import Path


LOWER_IS_BETTER = {"lcp_ms", "inp_ms", "cls", "tbt_ms", "js_kb", "css_kb", "heap_mb"}


def main() -> int:
    if len(sys.argv) != 3:
        print("用法: compare_metrics.py baseline.json candidate.json", file=sys.stderr)
        return 2
    try:
        before = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        after = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 2

    context_keys = ("page", "device", "network", "cache", "percentile")
    mismatches = [key for key in context_keys if before.get(key) != after.get(key)]
    if mismatches:
        print(json.dumps({"comparable": False, "context_mismatches": mismatches}, ensure_ascii=False, indent=2))
        return 2

    budgets = after.get("budgets", before.get("budgets", {}))
    changes = []
    for name in sorted(LOWER_IS_BETTER & before.keys() & after.keys()):
        old, new = before[name], after[name]
        if not isinstance(old, (int, float)) or not isinstance(new, (int, float)):
            continue
        delta_pct = None if old == 0 else round((new - old) / old * 100, 2)
        budget = budgets.get(name)
        changes.append({
            "metric": name, "before": old, "after": new, "delta_pct": delta_pct,
            "budget": budget, "within_budget": budget is None or new <= budget,
        })
    failed = [item["metric"] for item in changes if not item["within_budget"]]
    print(json.dumps({"comparable": True, "changes": changes, "failed_budgets": failed}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
