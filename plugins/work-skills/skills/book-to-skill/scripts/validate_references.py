#!/usr/bin/env python3
"""Validate generated reference structure and chapter links."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from reference_builder import MARKER


LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def validate(references: Path) -> tuple[int, int]:
    if not references.is_dir():
        raise RuntimeError(f"References directory not found: {references}")
    if not (references / MARKER).is_file():
        raise RuntimeError(f"Generated marker missing: {references / MARKER}")
    if not (references / "index.md").is_file():
        raise RuntimeError("Chapter index is missing")
    markdown = sorted(references.rglob("*.md"))
    if not markdown:
        raise RuntimeError("No Markdown references were generated")
    links = 0
    missing: list[str] = []
    for path in markdown:
        text = path.read_text(encoding="utf-8")
        for target in LINK_RE.findall(text):
            if target.startswith("#") or re.match(r"^[a-zA-Z]+://", target):
                continue
            links += 1
            if Path(target).is_absolute():
                missing.append(f"absolute link in {path}: {target}")
            elif not (path.parent / target).resolve().exists():
                missing.append(f"missing link from {path}: {target}")
    if missing:
        raise RuntimeError("\n".join(missing))
    return len(markdown), links


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("references", type=Path)
    args = parser.parse_args()
    try:
        files, links = validate(args.references.resolve())
    except (OSError, RuntimeError, UnicodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    print(f"Validation passed: {files} Markdown files, {links} internal links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
