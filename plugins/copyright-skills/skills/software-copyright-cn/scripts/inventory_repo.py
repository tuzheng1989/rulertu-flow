#!/usr/bin/env python3
"""Build a deterministic, auditable inventory of application source files."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
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
    "docs/**", "data/**", "results/**", "reports/**", "logs/**", "openwiki/**",
    "tests/**", "**/tests/**", "conftest.py", "**/test_*.py", "**/*_test.py",
    "bench/**", "**/bench/**", "benchmark/**", "**/benchmark/**",
    "**/*.min.js", "**/*.min.css",
    "**/vendor/**", "**/generated/**", "**/.env", "**/.env.*",
]


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


def physical_lines(data: bytes) -> int:
    if not data:
        return 0
    return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)


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
    included: list[dict] = []
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
        data = path.read_bytes()
        included.append({
            "path": relative,
            "bytes": len(data),
            "physical_lines": physical_lines(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })

    included.sort(key=lambda item: (item["path"].casefold(), item["path"]))
    excluded.sort(key=lambda item: (item["path"].casefold(), item["path"]))
    total_lines = sum(item["physical_lines"] for item in included)
    status = git_output(repo, "status", "--porcelain=v1")
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
        "included_files": included,
        "excluded_files": excluded,
        "included_file_count": len(included),
        "total_physical_lines": total_lines,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"included_files={len(included)} total_physical_lines={total_lines} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
