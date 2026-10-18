#!/usr/bin/env python3
"""Read-only frontend project profiler. Emits JSON and never installs dependencies."""

from __future__ import annotations

import json
import sys
from pathlib import Path


MARKERS = {
    "frameworks": {
        "next": ["next"], "react": ["react"], "vue": ["vue"],
        "nuxt": ["nuxt"], "svelte": ["svelte"],
    },
    "routing": {
        "react-router": ["react-router", "react-router-dom"],
        "vue-router": ["vue-router"],
    },
    "state_or_data": {
        "tanstack-query": ["@tanstack/react-query", "@tanstack/vue-query"],
        "swr": ["swr"], "pinia": ["pinia"], "redux": ["@reduxjs/toolkit", "redux"],
        "zustand": ["zustand"],
    },
    "testing": {
        "vitest": ["vitest"], "jest": ["jest"], "playwright": ["@playwright/test"],
        "cypress": ["cypress"], "testing-library": ["@testing-library/react", "@testing-library/vue"],
    },
    "styling": {
        "tailwind": ["tailwindcss"], "antd": ["antd"], "element-plus": ["element-plus"],
        "mui": ["@mui/material"], "chakra": ["@chakra-ui/react"],
    },
}


def detect(groups: dict[str, dict[str, list[str]]], deps: set[str]) -> dict[str, list[str]]:
    return {
        group: [name for name, packages in values.items() if deps.intersection(packages)]
        for group, values in groups.items()
    }


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    package_file = root / "package.json"
    if not package_file.is_file():
        print(json.dumps({"error": "未找到 package.json", "root": str(root)}, ensure_ascii=False))
        return 2
    try:
        package = json.loads(package_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(json.dumps({"error": f"无法读取 package.json: {error}"}, ensure_ascii=False))
        return 2

    deps = set(package.get("dependencies", {})) | set(package.get("devDependencies", {}))
    managers = []
    search_roots = []
    for candidate in (root, *root.parents):
        search_roots.append(candidate)
        if (candidate / ".git").exists():
            break
    for name, marker in (
        ("pnpm", "pnpm-lock.yaml"), ("npm", "package-lock.json"),
        ("yarn", "yarn.lock"), ("bun", "bun.lockb"),
    ):
        owner = next((parent for parent in search_roots if (parent / marker).exists()), None)
        if owner:
            managers.append({"name": name, "lockfile_root": str(owner), "distance": search_roots.index(owner)})
    if managers:
        nearest = min(item["distance"] for item in managers)
        managers = [{key: value for key, value in item.items() if key != "distance"}
                    for item in managers if item["distance"] == nearest]
    candidates = [
        path for path in ("src", "app", "pages", "components", "routes", "tests", "e2e")
        if (root / path).exists()
    ]
    scripts = package.get("scripts", {})
    useful = {key: value for key, value in scripts.items() if any(
        token in key.lower() for token in ("dev", "test", "lint", "type", "build", "e2e")
    )}
    result = {
        "root": str(root),
        "package_manager": managers or [{"name": "未识别", "lockfile_root": None}],
        **detect(MARKERS, deps),
        "directories": candidates,
        "commands": useful,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
