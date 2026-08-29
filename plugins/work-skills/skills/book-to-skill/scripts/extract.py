#!/usr/bin/env python3
"""Extract a supported book into a normalized text corpus."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from book2skill_extractor import ExtractionError, extract_book
from book2skill_extractor.capabilities import capability_report


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path.cwd() / "book2skill-work")
    parser.add_argument("--pdf-mode", choices=("auto", "technical", "text"), default="auto")
    parser.add_argument("--check", action="store_true", help="Print available extraction capabilities")
    parser.add_argument("--json", action="store_true", help="Print the result as JSON")
    return parser.parse_args()


def main() -> int:
    args = _args()
    if args.check:
        print(json.dumps(capability_report(), ensure_ascii=False, indent=2))
        return 0
    if args.input is None:
        print("Error: input is required unless --check is used", file=sys.stderr)
        return 2
    try:
        result = extract_book(args.input, pdf_mode=args.pdf_mode)
        output = args.output_dir.resolve()
        output.mkdir(parents=True, exist_ok=True)
        text_path = output / "full_text.txt"
        report_path = output / "extraction_report.json"
        text_path.write_text(result.text, encoding="utf-8")
        report = {
            "schema_version": 1,
            "format": result.input_format,
            "extractor": result.extractor,
            "character_count": len(result.text),
            "warnings": list(result.warnings),
            "full_text": text_path.name,
        }
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (ExtractionError, OSError, UnicodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        print(f"Text: {text_path}")
        print(f"Report: {report_path}")
        print(f"Extractor: {result.extractor}; characters: {len(result.text)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
