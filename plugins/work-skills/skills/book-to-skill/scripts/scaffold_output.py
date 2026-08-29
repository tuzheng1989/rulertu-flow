#!/usr/bin/env python3
"""Create an empty, mode-specific Book2Skill output layout."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


MODES = ("faithful", "knowledge", "methods", "hybrid")
COMPONENTS = ("faithful", "knowledge", "methods")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _require_slug(value: str) -> str:
    if len(value) >= 64 or not SLUG_RE.fullmatch(value):
        raise ValueError("book slug must be lowercase hyphen-case and shorter than 64 characters")
    return value


def _empty_output(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise RuntimeError(f"Output is not empty: {path}")
    path.mkdir(parents=True, exist_ok=True)


def _knowledge_layout(path: Path) -> None:
    (path / "references" / "chapters").mkdir(parents=True, exist_ok=True)


def _methods_layout(path: Path) -> None:
    (path / "skills").mkdir(parents=True, exist_ok=True)


def scaffold(output: Path, mode: str, book_slug: str, components: list[str]) -> Path:
    output = output.resolve()
    book_slug = _require_slug(book_slug)
    if mode not in MODES:
        raise ValueError(f"Unsupported mode: {mode}")
    if len(set(components)) != len(components) or any(item not in COMPONENTS for item in components):
        raise ValueError("components must be unique faithful, knowledge, or methods values")
    if mode == "hybrid" and not 2 <= len(components) <= 3:
        raise ValueError("hybrid mode requires two or three components")
    if mode != "hybrid" and components:
        raise ValueError("components are only valid for hybrid mode")

    _empty_output(output)
    if mode == "faithful":
        return output
    if mode == "knowledge":
        _knowledge_layout(output)
        return output
    if mode == "methods":
        _methods_layout(output)
        return output

    skills = output / "skills"
    skills.mkdir()
    if "faithful" in components:
        (skills / f"{book_slug}-source").mkdir()
    if "knowledge" in components:
        _knowledge_layout(skills / f"{book_slug}-knowledge")
    if "methods" in components:
        (skills / "methods" / "skills").mkdir(parents=True)

    plan = {
        "schema_version": 1,
        "book_slug": book_slug,
        "selected_mode": "hybrid",
        "confidence": "medium",
        "scores": {"faithful": 0, "knowledge": 0, "methods": 0},
        "evidence": {"faithful": [], "knowledge": [], "methods": []},
        "components": components,
        "excluded_components": {
            item: "TODO: explain why this component is excluded"
            for item in COMPONENTS if item not in components
        },
        "scopes": {
            item: {"chapters": [], "purpose": "TODO"}
            for item in components
        },
        "planned_skills": [],
        "user_confirmed": False,
    }
    (output / "build-plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--mode", required=True, choices=MODES)
    parser.add_argument("--book-slug", required=True)
    parser.add_argument("--components", nargs="*", default=[])
    args = parser.parse_args(argv)
    try:
        output = scaffold(args.output, args.mode, args.book_slug, args.components)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    print(f"Created {args.mode} output layout: {output}")
    if args.mode == "hybrid":
        print("Next step: complete build-plan.json and obtain user confirmation before generation.")
    else:
        print("Next step: generate the selected mode using the matching reference guide.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

