#!/usr/bin/env python3
"""Validate Book2Skill output contracts for all generation modes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from validate_references import validate as validate_references


MODES = ("faithful", "knowledge", "methods", "hybrid")
COMPONENTS = {"faithful", "knowledge", "methods"}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ABSOLUTE_WINDOWS_RE = re.compile(r"[A-Za-z]:[\\/]")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
URI_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")


def _require_file(path: Path, label: str) -> None:
    if not path.is_file() or not path.read_text(encoding="utf-8").strip():
        raise RuntimeError(f"Missing or empty {label}: {path}")


def _frontmatter(path: Path) -> dict[str, str]:
    _require_file(path, "SKILL.md")
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise RuntimeError(f"Missing YAML frontmatter: {path}")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise RuntimeError(f"Unclosed YAML frontmatter: {path}") from error
    fields: dict[str, str] = {}
    current: str | None = None
    for raw in lines[1:end]:
        if raw.startswith((" ", "\t")):
            if current and raw.strip():
                fields[current] = (fields[current] + " " + raw.strip()).strip()
            continue
        if ":" not in raw:
            raise RuntimeError(f"Invalid frontmatter line in {path}: {raw}")
        key, value = raw.split(":", 1)
        current = key.strip()
        fields[current] = value.strip().strip("'\"")
    if set(fields) != {"name", "description"}:
        raise RuntimeError(f"Frontmatter must contain only name and description: {path}")
    if not fields["description"] or fields["description"] in {"|", ">"}:
        raise RuntimeError(f"Description is empty: {path}")
    return fields


def _skill(path: Path) -> None:
    fields = _frontmatter(path / "SKILL.md")
    name = fields["name"]
    if name != path.name:
        raise RuntimeError(f"Skill name {name!r} does not match directory {path.name!r}")
    if len(name) >= 64 or not SLUG_RE.fullmatch(name):
        raise RuntimeError(f"Invalid skill name: {name}")
    for markdown in path.rglob("*.md"):
        text = markdown.read_text(encoding="utf-8")
        for target in LINK_RE.findall(text):
            if target.startswith("#") or URI_RE.match(target):
                continue
            if ABSOLUTE_WINDOWS_RE.search(target) or target.startswith(("/", "\\")):
                raise RuntimeError(f"Absolute local link in {markdown}: {target}")


def _faithful(path: Path) -> dict[str, int]:
    _skill(path)
    files, links = validate_references(path / "references")
    return {"skills": 1, "markdown_files": files, "links": links}


def _knowledge(path: Path) -> dict[str, int]:
    _skill(path)
    references = path / "references"
    for name in ("index.md", "overview.md", "glossary.md", "patterns.md", "cheatsheet.md"):
        _require_file(references / name, name)
    chapters = sorted((references / "chapters").glob("*.md"))
    if not chapters:
        raise RuntimeError(f"No knowledge chapter files: {references / 'chapters'}")
    for chapter in chapters:
        _require_file(chapter, "knowledge chapter")
        if not re.search(r"来源|source", chapter.read_text(encoding="utf-8"), re.IGNORECASE):
            raise RuntimeError(f"Knowledge chapter does not identify its source: {chapter}")
    return {"skills": 1, "knowledge_chapters": len(chapters)}


def _method_sections(skill_file: Path) -> None:
    text = skill_file.read_text(encoding="utf-8")
    for section in ("R", "I", "A1", "A2", "E", "B"):
        if not re.search(rf"^##+\s+{re.escape(section)}(?:\s|[：:])", text, re.MULTILINE):
            raise RuntimeError(f"Method Skill missing {section} section: {skill_file}")


def _test_cases(path: Path, sibling_names: set[str]) -> int:
    _require_file(path, "test-prompts.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Invalid test JSON: {path}: {error}") from error
    cases = data.get("test_cases")
    if not isinstance(cases, list):
        raise RuntimeError(f"test_cases must be an array: {path}")
    counts = {
        kind: sum(case.get("type") == kind for case in cases if isinstance(case, dict))
        for kind in ("should_trigger", "should_not_trigger", "edge_case")
    }
    if counts["should_trigger"] < 3 or counts["should_not_trigger"] < 2 or counts["edge_case"] < 1:
        raise RuntimeError(f"Insufficient method tests in {path}: {counts}")
    if sibling_names:
        serialized = json.dumps(
            [case for case in cases if case.get("type") == "should_not_trigger"],
            ensure_ascii=False,
        )
        if not any(name in serialized for name in sibling_names):
            raise RuntimeError(f"No sibling-skill confusion test in {path}")
    return len(cases)


def _methods(path: Path) -> dict[str, int]:
    _require_file(path / "INDEX.md", "method INDEX.md")
    _require_file(path / "GLOSSARY.md", "method GLOSSARY.md")
    _require_file(path / "distillation-report.json", "distillation report")
    try:
        report = json.loads((path / "distillation-report.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Invalid distillation report: {error}") from error
    if not isinstance(report, dict):
        raise RuntimeError("distillation-report.json must contain an object")
    skills_root = path / "skills"
    skill_dirs = sorted(item for item in skills_root.iterdir() if item.is_dir()) if skills_root.is_dir() else []
    if not skill_dirs:
        raise RuntimeError(f"No method Skills found: {skills_root}")
    names = {item.name for item in skill_dirs}
    tests = 0
    for skill_dir in skill_dirs:
        _skill(skill_dir)
        _method_sections(skill_dir / "SKILL.md")
        _require_file(skill_dir / "references" / "evidence.md", "method evidence")
        tests += _test_cases(skill_dir / "test-prompts.json", names - {skill_dir.name})
    return {"skills": len(skill_dirs), "test_cases": tests}


def _hybrid(path: Path) -> dict[str, int]:
    _require_file(path / "PACK_INDEX.md", "PACK_INDEX.md")
    _require_file(path / "build-plan.json", "build-plan.json")
    try:
        plan = json.loads((path / "build-plan.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Invalid build plan: {error}") from error
    if plan.get("selected_mode") != "hybrid":
        raise RuntimeError("Hybrid build plan must use selected_mode=hybrid")
    components = plan.get("components")
    if not isinstance(components, list) or not 2 <= len(components) <= 3:
        raise RuntimeError("Hybrid components must contain two or three values")
    if len(set(components)) != len(components) or not set(components) <= COMPONENTS:
        raise RuntimeError("Hybrid components must be unique faithful, knowledge, or methods values")
    if plan.get("user_confirmed") is not True:
        raise RuntimeError("Hybrid build plan has not been user-confirmed")
    book_slug = plan.get("book_slug", "")
    if len(book_slug) >= 64 or not SLUG_RE.fullmatch(book_slug):
        raise RuntimeError(f"Invalid book_slug in build plan: {book_slug!r}")
    scopes = plan.get("scopes")
    if not isinstance(scopes, dict) or set(scopes) != set(components):
        raise RuntimeError("Hybrid scopes must match components exactly")

    expected = set()
    stats = {"skills": 0, "components": len(components)}
    if "faithful" in components:
        name = f"{book_slug}-source"
        expected.add(name)
        result = _faithful(path / "skills" / name)
        stats["skills"] += result["skills"]
    if "knowledge" in components:
        name = f"{book_slug}-knowledge"
        expected.add(name)
        result = _knowledge(path / "skills" / name)
        stats["skills"] += result["skills"]
    if "methods" in components:
        expected.add("methods")
        result = _methods(path / "skills" / "methods")
        stats["skills"] += result["skills"]
    skills_root = path / "skills"
    actual = {item.name for item in skills_root.iterdir() if item.is_dir()} if skills_root.is_dir() else set()
    if actual != expected:
        raise RuntimeError(f"Hybrid component directories differ from plan: expected {expected}, got {actual}")
    return stats


def validate_output(path: Path, mode: str) -> dict[str, int]:
    path = path.resolve()
    if not path.is_dir():
        raise RuntimeError(f"Output directory not found: {path}")
    if mode == "faithful":
        return _faithful(path)
    if mode == "knowledge":
        return _knowledge(path)
    if mode == "methods":
        return _methods(path)
    if mode == "hybrid":
        return _hybrid(path)
    raise ValueError(f"Unsupported mode: {mode}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--mode", required=True, choices=MODES)
    args = parser.parse_args(argv)
    try:
        stats = validate_output(args.output, args.mode)
    except (OSError, RuntimeError, UnicodeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    details = ", ".join(f"{key}={value}" for key, value in sorted(stats.items()))
    print(f"{args.mode} validation passed: {details}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
