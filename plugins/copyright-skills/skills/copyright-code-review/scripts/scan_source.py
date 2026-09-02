#!/usr/bin/env python3
"""Collect static compliance facts from source files before copyright submission."""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


SOURCE_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cs", ".css", ".go", ".h", ".hpp", ".html",
    ".java", ".js", ".jsx", ".kt", ".kts", ".php", ".py", ".rb", ".rs",
    ".scala", ".sh", ".sql", ".swift", ".ts", ".tsx", ".vue",
}
DEFAULT_EXCLUDES = [
    ".git/**", ".agents/**", ".codex/**", ".venv*/**", "venv/**", "node_modules/**",
    "dist/**", "build/**", "coverage/**", "__pycache__/**", ".pytest_cache/**",
    "docs/**", "data/**", "results/**", "reports/**", "logs/**",
    "tests/**", "**/tests/**", "conftest.py", "**/test_*.py", "**/*_test.py",
    "**/*.min.js", "**/*.min.css",
    "**/vendor/**", "**/generated/**", "**/.env", "**/.env.*",
]
PLACEHOLDER_PATTERN = re.compile(
    r"\bTODO\b|\bFIXME\b|\bXXX\b|\bHACK\b|待实现|待补充|待完善|待接入|占位", re.IGNORECASE
)
LICENSE_PATTERN = re.compile(
    r"Copyright\s*[©(]|Apache License|GNU General Public|MIT License|BSD [23]-Clause"
    r"|Licensed under|@author",
    re.IGNORECASE,
)
STUB_PATTERN = re.compile(r"^\s*(pass|\.\.\.)\s*(#.*)?$")
ENTRY_CODE_PATTERN = re.compile(
    r"if __name__\s*==\s*['\"]__main__['\"]|def main\s*\(|func main\s*\("
    r"|public static void main|int main\s*\(",
)
ENTRY_FILE_NAMES = {
    "main.py", "app.py", "manage.py", "index.js", "index.ts", "main.go",
    "main.c", "main.cpp", "app.java", "main.java",
}
MOJIBAKE_SNIPPETS = ("�", "锟斤拷", "ï¿½")
MAX_LISTED_HITS = 50


def git_output(repo: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args], cwd=repo, text=True, encoding="utf-8", errors="replace",
            capture_output=True, check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def discover(repo: Path) -> list[Path]:
    tracked = git_output(repo, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    if tracked is not None:
        return [repo / value for value in tracked.split("\0") if value]
    return [path for path in repo.rglob("*") if path.is_file()]


def matches(path: str, patterns: list[str]) -> str | None:
    normalized = path.replace("\\", "/")
    for pattern in patterns:
        if fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch("/" + normalized, "*/" + pattern):
            return pattern
    return None


def blank_line_runs(lines: list[str]) -> list[int]:
    runs: list[int] = []
    run = 0
    for line in lines:
        if line.strip():
            if run > 2:
                runs.append(run)
            run = 0
        else:
            run += 1
    if run > 2:
        runs.append(run)
    return runs


def scan_file(path: Path, relative: str) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    hits: dict[str, list[int]] = {
        "placeholder": [],
        "license_marker": [],
        "stub_line": [],
        "mojibake": [],
    }
    for number, line in enumerate(lines, start=1):
        if PLACEHOLDER_PATTERN.search(line):
            hits["placeholder"].append(number)
        if LICENSE_PATTERN.search(line):
            hits["license_marker"].append(number)
        if STUB_PATTERN.match(line):
            hits["stub_line"].append(number)
        if any(snippet in line for snippet in MOJIBAKE_SNIPPETS):
            hits["mojibake"].append(number)
    listed = {key: value[:MAX_LISTED_HITS] for key, value in hits.items() if value}
    return {
        "path": relative,
        "physical_lines": len(lines),
        "blank_lines": sum(1 for line in lines if not line.strip()),
        "blank_line_runs_over2": blank_line_runs(lines),
        "entry_candidate": path.name.lower() in ENTRY_FILE_NAMES or bool(ENTRY_CODE_PATTERN.search(text)),
        "findings": listed,
        "finding_counts": {key: len(value) for key, value in hits.items() if value},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include-root", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    args = parser.parse_args()

    repo = args.repo.resolve()
    output = args.output.resolve()
    include_roots = [value.strip("/\\") for value in args.include_root]
    exclusions = DEFAULT_EXCLUDES + args.exclude
    scanned: list[dict] = []
    excluded: list[dict] = []

    for path in discover(repo):
        try:
            relative = path.resolve().relative_to(repo).as_posix()
        except (OSError, ValueError):
            continue
        reason = None
        if include_roots and not any(relative == root or relative.startswith(root + "/") for root in include_roots):
            reason = "outside include roots"
        elif path.suffix.lower() not in SOURCE_EXTENSIONS:
            reason = "not an application source extension"
        else:
            pattern = matches(relative, exclusions)
            if pattern:
                reason = f"excluded by {pattern}"
        if reason:
            excluded.append({"path": relative, "reason": reason})
            continue
        scanned.append(scan_file(path, relative))

    scanned.sort(key=lambda item: (item["path"].casefold(), item["path"]))
    excluded.sort(key=lambda item: (item["path"].casefold(), item["path"]))
    status = git_output(repo, "status", "--porcelain=v1")
    finding_totals: dict[str, int] = {}
    for item in scanned:
        for key, count in item["finding_counts"].items():
            finding_totals[key] = finding_totals.get(key, 0) + count
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": str(repo),
        "git": {
            "commit": git_output(repo, "rev-parse", "HEAD"),
            "branch": git_output(repo, "branch", "--show-current"),
            "dirty": bool(status) if status is not None else None,
        },
        "selection": {
            "include_roots": include_roots,
            "exclude_patterns": exclusions,
            "extensions": sorted(SOURCE_EXTENSIONS),
        },
        "scanned_files": scanned,
        "excluded_files": excluded,
        "summary": {
            "scanned_file_count": len(scanned),
            "total_physical_lines": sum(item["physical_lines"] for item in scanned),
            "total_blank_lines": sum(item["blank_lines"] for item in scanned),
            "entry_candidates": [item["path"] for item in scanned if item["entry_candidate"]],
            "finding_totals": finding_totals,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"scanned_files={len(scanned)} findings={finding_totals} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
