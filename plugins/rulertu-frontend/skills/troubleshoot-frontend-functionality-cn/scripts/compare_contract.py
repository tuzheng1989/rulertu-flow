#!/usr/bin/env python3
"""Compare a JSON response with required dotted paths. Read-only and dependency-free."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def resolve(value, path: str):
    current = value
    for part in path.split("."):
        if isinstance(current, list) and part == "[]":
            current = current[0] if current else None
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return False, None
    return True, current


def type_name(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def main() -> int:
    if len(sys.argv) != 3:
        print("用法: compare_contract.py response.json expected-fields.json", file=sys.stderr)
        return 2
    try:
        response = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        expected = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 2
    if not isinstance(expected, dict):
        print(json.dumps({"error": "expected-fields.json 必须是 {路径: 类型} 对象"}, ensure_ascii=False))
        return 2

    findings = []
    for path, wanted in expected.items():
        found, value = resolve(response, path)
        actual = type_name(value) if found else "missing"
        if not found or (wanted != "any" and actual != wanted):
            findings.append({"path": path, "expected": wanted, "actual": actual})
    print(json.dumps({"checked": len(expected), "findings": findings}, ensure_ascii=False, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
