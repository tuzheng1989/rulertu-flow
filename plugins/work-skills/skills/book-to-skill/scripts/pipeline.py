#!/usr/bin/env python3
"""Extract one book and build its chapter-linked references tree."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from book2skill_extractor import ExtractionError, extract_book
from reference_builder import build_references, skill_slug
from validate_references import validate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--skill-dir", type=Path)
    parser.add_argument("--pdf-mode", choices=("auto", "technical", "text"), default="auto")
    parser.add_argument(
        "--force", action="store_true",
        help="Replace references only when they carry the Book2Skill generated marker",
    )
    args = parser.parse_args(argv)
    source = args.input.resolve()
    skill_dir = (args.skill_dir or Path.cwd() / skill_slug(source.stem)).resolve()
    try:
        result = extract_book(source, pdf_mode=args.pdf_mode)
        built = build_references(result.text, skill_dir, force=args.force)
        files, links = validate(built.references)
    except (ExtractionError, OSError, RuntimeError, UnicodeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    print(f"Skill directory: {skill_dir}")
    print(f"Extractor: {result.extractor}")
    print(f"Chapters processed: {built.chapters}")
    print(f"Markdown files written: {files}")
    print(f"Internal links validated: {links}")
    for warning in result.warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    print("Next step: write and validate SKILL.md against the generated chapter structure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
