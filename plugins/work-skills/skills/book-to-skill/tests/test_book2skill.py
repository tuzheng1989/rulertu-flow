from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS))

from book2skill_extractor import extract_book  # noqa: E402
from reference_builder import MARKER, build_references  # noqa: E402
from validate_references import validate  # noqa: E402


BOOK_TEXT = """本书说明

第 1 章 起步
本章介绍。
1.1 准备。先检查输入。
准备正文。
1.1.1 条件
条件正文。
1.2 执行
执行正文。
第 2 章 收尾
第二章正文。
2.1 验证
验证正文。
"""


class ExtractionTests(unittest.TestCase):
    def test_text_and_html_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text_path = root / "书.md"
            text_path.write_text("第 1 章 测试\n正文", encoding="utf-8")
            text_result = extract_book(text_path)
            self.assertEqual(text_result.input_format, "md")
            self.assertIn("正文", text_result.text)

            html_path = root / "book.html"
            html_path.write_text("<h1>第 1 章 HTML</h1><p>正文</p><script>ignore</script>", encoding="utf-8")
            html_result = extract_book(html_path)
            self.assertIn("第 1 章 HTML", html_result.text)
            self.assertNotIn("ignore", html_result.text)

    def test_stdlib_epub_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "book.epub"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(
                    "META-INF/container.xml",
                    '<rootfile full-path="OEBPS/content.opf"/>',
                )
                archive.writestr(
                    "OEBPS/content.opf",
                    '<manifest><item id="c1" href="c1.xhtml"/></manifest>'
                    '<spine><itemref idref="c1"/></spine>',
                )
                archive.writestr("OEBPS/c1.xhtml", "<h1>第 1 章 EPUB</h1><p>内容</p>")
            result = extract_book(path)
            self.assertIn("第 1 章 EPUB", result.text)

    def test_stdlib_docx_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "book.docx"
            xml = (
                '<?xml version="1.0"?><w:document '
                'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:body><w:p><w:r><w:t>第 1 章 DOCX</w:t></w:r></w:p>'
                '<w:p><w:r><w:t>正文</w:t></w:r></w:p></w:body></w:document>'
            )
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", xml)
            result = extract_book(path)
            self.assertIn("第 1 章 DOCX", result.text)


class ReferenceTests(unittest.TestCase):
    def test_builds_chapter_links_without_provenance_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "target"
            result = build_references(BOOK_TEXT, skill)
            files, links = validate(result.references)
            self.assertEqual(result.chapters, 2)
            self.assertGreaterEqual(files, 7)
            self.assertGreaterEqual(links, 6)
            all_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in result.references.rglob("*.md")
            )
            self.assertIn("1.1 准备。", all_text)
            self.assertIn("先检查输入。", all_text)
            self.assertNotIn("source_file", all_text)
            self.assertNotIn("sha256", all_text)
            self.assertNotIn("page:", all_text)
            marker = json.loads((result.references / MARKER).read_text(encoding="utf-8"))
            self.assertEqual(set(marker), {"schema_version", "generator"})

    def test_force_only_replaces_generated_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "target"
            references = skill / "references"
            references.mkdir(parents=True)
            (references / "manual.md").write_text("人工内容", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Refusing"):
                build_references(BOOK_TEXT, skill, force=True)
            self.assertTrue((references / "manual.md").is_file())

            (references / MARKER).write_text("{}", encoding="utf-8")
            result = build_references(BOOK_TEXT, skill, force=True)
            self.assertFalse((result.references / "manual.md").exists())
            validate(result.references)

    def test_pipeline_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            book = root / "book.txt"
            target = root / "target-skill"
            book.write_text(BOOK_TEXT, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "pipeline.py"), str(book), "--skill-dir", str(target)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((target / "references" / "index.md").is_file())
            self.assertIn("Chapters processed: 2", result.stdout)


if __name__ == "__main__":
    unittest.main()
