from __future__ import annotations
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SCRIPTS = Path(__file__).parents[1] / "skills" / "plan-iterate" / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("codex_review", SCRIPTS / "codex_review.py")
codex_review = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(codex_review)
from normalize import ReviewError, normalize_review

VALID = {"overall_quality": "ok", "score": 9, "issues": [], "suggestions": []}
RUNTIME = Path(__file__).parent / "runtime"

class Cleanup:
    def cleanup(self):
        for path in RUNTIME.iterdir():
            if path.name != ".gitkeep" and path.is_file():
                path.unlink()

class NormalizeTests(unittest.TestCase):
    def test_maps_legacy_fields_and_rejects_boolean_score(self):
        value = {"review": "ok", "score": 8.5, "issues": [{
            "severity": "P2", "title": "t", "detail": "d", "fix": "f"}]}
        self.assertEqual(normalize_review(value)["issues"][0]["suggestion"], "f")
        with self.assertRaises(ReviewError):
            normalize_review({**VALID, "score": True})

    def test_rejects_unknown_or_incomplete_fields(self):
        with self.assertRaises(ReviewError):
            normalize_review({**VALID, "extra": 1})
        with self.assertRaises(ReviewError):
            normalize_review({"score": 9, "issues": [], "suggestions": []})

class ProtocolTests(unittest.TestCase):
    def test_command_construction(self):
        repo, out = Path("C:/repo"), Path("C:/out/review-R1.json")
        first = codex_review.build_command(repo, out, None, "prompt")
        self.assertEqual(first[:7], ["codex", "exec", "-s", "read-only", "-C", str(repo), "--json"])
        resumed = codex_review.build_command(repo, out, "abc", "prompt")
        self.assertEqual(resumed[:4], ["codex", "exec", "resume", "abc"])
        self.assertNotIn("-C", resumed)

    def test_jsonl_thread_event(self):
        events = '{"type":"noise"}\nnot-json\n{"type":"thread.started","thread_id":"tid"}\n'
        self.assertEqual(codex_review.extract_thread_id(events), "tid")
        self.assertIsNone(codex_review.extract_thread_id("{}"))

    def test_legacy_session_migration_input(self):
        Cleanup().cleanup()

    def test_schema_is_located_next_to_script(self):
        self.assertEqual(codex_review.SCHEMA_PATH, SCRIPTS / "review-schema.json")
        codex_review.validate_schema()
        (RUNTIME / "session.txt").write_text("legacy-id\n", encoding="utf-8")
        self.assertEqual(codex_review.load_session(RUNTIME / "review-R2.json", None), "legacy-id")
        Cleanup().cleanup()

class FakeCodexTests(unittest.TestCase):
    def invoke(self, mode: str, round_number: int = 1, session: str | None = None, preserve: bool = False):
        temporary = Cleanup()
        if not preserve:
            temporary.cleanup()
        root = RUNTIME
        plan = root / "plan.md"
        plan.write_text("# Plan\n", encoding="utf-8")
        out = root / f"review-R{round_number}.json"

        def fake_run(command, **kwargs):
            output = Path(command[command.index("-o") + 1])
            if mode == "timeout":
                raise codex_review.subprocess.TimeoutExpired(command, 1)
            if mode == "failure":
                return SimpleNamespace(returncode=7)
            if mode == "corrupt":
                output.write_text("{broken", encoding="utf-8")
            else:
                output.write_text(json.dumps(VALID), encoding="utf-8")
            if mode != "missing-session":
                kwargs["stdout"].write('{"type":"thread.started","thread_id":"new-id"}\n')
                kwargs["stdout"].flush()
            return SimpleNamespace(returncode=0)

        args = ["codex_review.py", str(plan), str(out)] + ([session] if session else [])
        with mock.patch.object(codex_review, "repository_for", return_value=root), mock.patch.object(
            codex_review.subprocess, "run", side_effect=fake_run
        ):
            result = codex_review.run(args, timeout=0.01)
        return temporary, root, out, result

    def test_first_round_and_state(self):
        temporary, root, out, result = self.invoke("success")
        self.addCleanup(temporary.cleanup)
        self.assertEqual(result, 0)
        state = json.loads((root / "state.json").read_text(encoding="utf-8"))
        self.assertEqual((state["round"], state["session_id"]), (1, "new-id"))
        self.assertTrue(Path(str(out.with_suffix("")) + ".events.jsonl").exists())
        self.assertIn("thread.started", Path(str(out.with_suffix("")) + ".log").read_text(encoding="utf-8"))

    def test_resume_failure_timeout_and_protocol_errors(self):
        for mode, expected in (("failure", 3), ("timeout", 3), ("corrupt", 4), ("missing-session", 4)):
            with self.subTest(mode=mode):
                temporary, _, _, result = self.invoke(mode)
                temporary.cleanup()
                self.assertEqual(result, expected)
        temporary, _, _, result = self.invoke("success", round_number=2, session="old-id")
        temporary.cleanup()
        self.assertEqual(result, 0)

    def test_legacy_session_is_migrated_to_state(self):
        Cleanup().cleanup()
        (RUNTIME / "session.txt").write_text("legacy-id\n", encoding="utf-8")
        temporary, root, _, result = self.invoke("success", round_number=2, preserve=True)
        self.addCleanup(temporary.cleanup)
        self.assertEqual(result, 0)
        self.assertFalse((root / "session.txt").exists())
        self.assertEqual(json.loads((root / "state.json").read_text(encoding="utf-8"))["session_id"], "new-id")

    def test_input_exit_code(self):
        self.assertEqual(codex_review.run(["codex_review.py"]), 2)

if __name__ == "__main__":
    unittest.main()
