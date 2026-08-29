from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS))

from scaffold_output import scaffold  # noqa: E402
from reference_builder import build_references  # noqa: E402
from validate_output import validate_output  # noqa: E402


def write_skill(path: Path, name: str, body: str = "# Skill\n") -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Use this skill for representative test tasks.\n---\n\n{body}",
        encoding="utf-8",
    )


def write_knowledge(path: Path) -> None:
    write_skill(path, path.name)
    references = path / "references"
    chapters = references / "chapters"
    chapters.mkdir(parents=True)
    for name in ("index.md", "overview.md", "glossary.md", "patterns.md", "cheatsheet.md"):
        (references / name).write_text(f"# {name}\n内容\n", encoding="utf-8")
    (chapters / "ch01.md").write_text("# 第一章\n\n来源：第 1 章\n\n知识内容\n", encoding="utf-8")


def write_method(path: Path, sibling: str) -> None:
    body = """# Method

## R：来源依据
证据
## I：方法机制
机制
## A1：来源中的应用
案例
## A2：触发场景
触发
## E：执行步骤
步骤
## B：边界
边界
"""
    write_skill(path, path.name, body)
    evidence = path / "references" / "evidence.md"
    evidence.parent.mkdir()
    evidence.write_text("# Evidence\n\n来源：第 1 章\n", encoding="utf-8")
    cases = [
        {"id": f"yes-{i}", "type": "should_trigger", "prompt": f"正例 {i}"}
        for i in range(3)
    ]
    cases.extend(
        [
            {"id": "no-1", "type": "should_not_trigger", "prompt": "无关问题"},
            {
                "id": "no-2",
                "type": "should_not_trigger",
                "prompt": "兄弟场景",
                "expected_behavior": f"应调用 {sibling}",
            },
            {"id": "edge-1", "type": "edge_case", "prompt": "边界问题"},
        ]
    )
    (path / "test-prompts.json").write_text(
        json.dumps({"skill": path.name, "test_cases": cases}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_methods_pack(path: Path, prefix: str = "sample") -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "INDEX.md").write_text("# Methods\n", encoding="utf-8")
    (path / "GLOSSARY.md").write_text("# Glossary\n", encoding="utf-8")
    (path / "distillation-report.json").write_text("{}\n", encoding="utf-8")
    first = f"{prefix}-method-one"
    second = f"{prefix}-method-two"
    write_method(path / "skills" / first, second)
    write_method(path / "skills" / second, first)


class ScaffoldTests(unittest.TestCase):
    def test_hybrid_scaffold_is_selective(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "pack"
            scaffold(output, "hybrid", "sample", ["faithful", "methods"])
            self.assertTrue((output / "skills" / "sample-source").is_dir())
            self.assertTrue((output / "skills" / "methods" / "skills").is_dir())
            self.assertFalse((output / "skills" / "sample-knowledge").exists())
            plan = json.loads((output / "build-plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["components"], ["faithful", "methods"])
            self.assertFalse(plan["user_confirmed"])

    def test_hybrid_requires_multiple_components(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "two or three"):
                scaffold(Path(tmp) / "pack", "hybrid", "sample", ["faithful"])


class OutputValidationTests(unittest.TestCase):
    def test_faithful_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sample-source"
            write_skill(target, target.name)
            build_references("第 1 章 规则\n正文\n1.1 条件\n条件正文\n", target)
            stats = validate_output(target, "faithful")
            self.assertEqual(stats["skills"], 1)

    def test_knowledge_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sample-knowledge"
            write_knowledge(target)
            stats = validate_output(target, "knowledge")
            self.assertEqual(stats["knowledge_chapters"], 1)

    def test_method_contract_and_sibling_tests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "methods"
            write_methods_pack(target)
            stats = validate_output(target, "methods")
            self.assertEqual(stats["skills"], 2)
            self.assertEqual(stats["test_cases"], 12)

    def test_selective_hybrid_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sample-skill-pack"
            (target / "skills").mkdir(parents=True)
            (target / "PACK_INDEX.md").write_text("# Pack\n", encoding="utf-8")
            plan = {
                "schema_version": 1,
                "book_slug": "sample",
                "selected_mode": "hybrid",
                "confidence": "high",
                "scores": {"faithful": 1, "knowledge": 5, "methods": 4},
                "components": ["knowledge", "methods"],
                "excluded_components": {"faithful": "No exact-source requirement"},
                "scopes": {
                    "knowledge": {"chapters": "all", "purpose": "understanding"},
                    "methods": {"chapters": ["2"], "purpose": "execution"},
                },
                "user_confirmed": True,
            }
            (target / "build-plan.json").write_text(
                json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            write_knowledge(target / "skills" / "sample-knowledge")
            write_methods_pack(target / "skills" / "methods")
            stats = validate_output(target, "hybrid")
            self.assertEqual(stats["components"], 2)
            self.assertEqual(stats["skills"], 3)

    def test_rejects_extra_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sample-knowledge"
            write_knowledge(target)
            skill = target / "SKILL.md"
            skill.write_text(
                skill.read_text(encoding="utf-8").replace(
                    "description:", "source_book: example\ndescription:"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "only name and description"):
                validate_output(target, "knowledge")

    def test_allows_external_markdown_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sample-knowledge"
            write_knowledge(target)
            with (target / "references" / "overview.md").open("a", encoding="utf-8") as stream:
                stream.write("\n[external](https://example.com/source)\n")
            validate_output(target, "knowledge")


if __name__ == "__main__":
    unittest.main()
