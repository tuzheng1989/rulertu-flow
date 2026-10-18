#!/usr/bin/env python3
"""Build a risk-directed acceptance matrix from explicit JSON dimensions."""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("用法: build_matrix.py acceptance.json", file=sys.stderr)
        return 2
    try:
        spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 2

    journeys = spec.get("journeys", [])
    defaults = spec.get("defaults", {})
    if not isinstance(journeys, list) or not journeys:
        print(json.dumps({"error": "journeys 必须是非空数组"}, ensure_ascii=False))
        return 2

    def dimension(journey: dict, key: str, fallback: str) -> list[str]:
        value = journey.get(key, defaults.get(key, [fallback]))
        if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
            raise ValueError(f"{key} 必须是非空字符串数组")
        return value

    cases = []
    seen = set()
    try:
        for journey in journeys:
            if not isinstance(journey, dict) or not journey.get("name") or not journey.get("expected"):
                raise ValueError("每个 journey 必须包含 name 和 expected")
            dimensions = [
                dimension(journey, "roles", "default"),
                dimension(journey, "viewports", "desktop"),
                dimension(journey, "browsers", "chromium"),
                dimension(journey, "networks", "normal"),
                dimension(journey, "locales", "default"),
            ]
            for role, viewport, browser, network, locale in itertools.product(*dimensions):
                key = (journey["name"], role, viewport, browser, network, locale)
                if key in seen:
                    continue
                seen.add(key)
                cases.append({
                    "journey": journey["name"], "risk": journey.get("risk", "未标注"),
                    "role": role, "viewport": viewport, "browser": browser, "network": network,
                    "locale": locale, "expected": journey["expected"],
                })
    except ValueError as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps({"count": len(cases), "cases": cases}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
