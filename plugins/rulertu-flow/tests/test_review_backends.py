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


def load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


codex_review = load_module("codex_review")
claude_review = load_module("claude_review")
review_common = load_module("review_common")
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
        value = {
            "review": "ok",
            "score": 8.5,
            "issues": [{"severity": "P2", "title": "t", "detail": "d", "fix": "f"}],
        }
        self.assertEqual(normalize_review(value)["issues"][0]["suggestion"], "f")
        with self.assertRaises(ReviewError):
            normalize_review({**VALID, "score": True})

    def test_rejects_unknown_or_incomplete_fields(self):
        with self.assertRaises(ReviewError):
            normalize_review({**VALID, "extra": 1})
        with self.assertRaises(ReviewError):
            normalize_review({"score": 9, "issues": [], "suggestions": []})


class SharedProtocolTests(unittest.TestCase):
    def setUp(self):
        Cleanup().cleanup()

    def tearDown(self):
        Cleanup().cleanup()

    def test_schema_is_located_next_to_backends(self):
        self.assertEqual(review_common.SCHEMA_PATH, SCRIPTS / "review-schema.json")
        review_common.validate_schema()

    def test_session_is_backend_scoped_and_legacy_is_codex_only(self):
        output = RUNTIME / "review-R2.json"
        (RUNTIME / "state.json").write_text(
            json.dumps({"backend": "external-codex", "session_id": "codex-id"}), encoding="utf-8"
        )
        self.assertEqual(review_common.load_session(output, "external-codex", None, allow_legacy=True), "codex-id")
        self.assertIsNone(review_common.load_session(output, "external-claude", None, allow_legacy=False))
        (RUNTIME / "state.json").unlink()
        (RUNTIME / "session.txt").write_text("legacy-id\n", encoding="utf-8")
        self.assertEqual(review_common.load_session(output, "external-codex", None, allow_legacy=True), "legacy-id")
        self.assertIsNone(review_common.load_session(output, "external-claude", None, allow_legacy=False))

    def test_new_backend_prompt_includes_previous_review(self):
        output = RUNTIME / "review-R2.json"
        (RUNTIME / "review-R1.json").write_text(json.dumps(VALID), encoding="utf-8")
        prompt = review_common.prompt_for(RUNTIME / "plan.md", None, review_common.prior_review(output, 2))
        self.assertIn("上一轮 JSON", prompt)
        self.assertIn('"score": 9', prompt)

    def test_shell_free_cli_resolution(self):
        with mock.patch.object(review_common.shutil, "which", return_value="/usr/bin/claude"):
            self.assertEqual(review_common.resolve_cli("claude", platform_name="posix"), ["/usr/bin/claude"])
        paths = {
            "codex.exe": None,
            "codex.com": None,
            "codex.cmd": "C:/npm/codex.cmd",
            "node.exe": "C:/node/node.exe",
        }
        with mock.patch.object(review_common.shutil, "which", side_effect=lambda name: paths.get(name)), mock.patch.object(
            review_common.Path, "is_file", return_value=True
        ):
            self.assertEqual(
                review_common.resolve_cli("codex", platform_name="nt"),
                ["C:/node/node.exe", "C:\\npm\\node_modules\\@openai\\codex\\bin\\codex.js"],
            )


class CodexBackendTests(unittest.TestCase):
    def invoke(self, mode: str, round_number: int = 1, session: str | None = None, preserve: bool = False):
        cleanup = Cleanup()
        if not preserve:
            cleanup.cleanup()
        plan = RUNTIME / "plan.md"
        plan.write_text("# Plan\n", encoding="utf-8")
        output = RUNTIME / f"review-R{round_number}.json"

        def fake_run(command, **kwargs):
            target = Path(command[command.index("-o") + 1])
            if mode == "timeout":
                raise codex_review.subprocess.TimeoutExpired(command, 1)
            if mode == "failure":
                return SimpleNamespace(returncode=7)
            target.write_text("{broken" if mode == "corrupt" else json.dumps(VALID), encoding="utf-8")
            if mode != "missing-session":
                kwargs["stdout"].write('{"type":"thread.started","thread_id":"codex-new"}\n')
                kwargs["stdout"].flush()
            return SimpleNamespace(returncode=0)

        args = ["codex_review.py", str(plan), str(output)] + ([session] if session else [])
        with mock.patch.object(codex_review, "repository_for", return_value=RUNTIME), mock.patch.object(
            codex_review, "resolve_cli", return_value=["codex"]
        ), mock.patch.object(codex_review.subprocess, "run", side_effect=fake_run):
            result = codex_review.run(args, timeout=0.01)
        return cleanup, output, result

    def test_commands_first_resume_and_thread_event(self):
        repo, output = Path("C:/repo"), Path("C:/out/review-R1.json")
        first = codex_review.build_command(["codex"], repo, output, None, "prompt")
        self.assertEqual(first[:7], ["codex", "exec", "-s", "read-only", "-C", str(repo), "--json"])
        resumed = codex_review.build_command(["codex"], repo, output, "id", "prompt")
        self.assertEqual(resumed[:4], ["codex", "exec", "resume", "id"])
        self.assertEqual(
            codex_review.extract_thread_id('{"type":"thread.started","thread_id":"tid"}\n'), "tid"
        )

    def test_success_errors_and_legacy_migration(self):
        cleanup, output, result = self.invoke("success")
        self.addCleanup(cleanup.cleanup)
        self.assertEqual(result, 0)
        state = json.loads((RUNTIME / "state.json").read_text(encoding="utf-8"))
        self.assertEqual((state["backend"], state["session_id"]), ("external-codex", "codex-new"))
        self.assertIn("thread.started", Path(str(output.with_suffix("")) + ".log").read_text(encoding="utf-8"))
        for mode, expected in (("failure", 3), ("timeout", 3), ("corrupt", 4), ("missing-session", 4)):
            with self.subTest(mode=mode):
                temporary, _, actual = self.invoke(mode)
                temporary.cleanup()
                self.assertEqual(actual, expected)
        Cleanup().cleanup()
        (RUNTIME / "session.txt").write_text("legacy-id\n", encoding="utf-8")
        temporary, _, actual = self.invoke("success", round_number=2, preserve=True)
        self.addCleanup(temporary.cleanup)
        self.assertEqual(actual, 0)
        self.assertFalse((RUNTIME / "session.txt").exists())

    def test_input_exit_code(self):
        self.assertEqual(codex_review.run(["codex_review.py"]), 2)


class ClaudeBackendTests(unittest.TestCase):
    def invoke(self, mode: str, round_number: int = 1, session: str | None = None, preserve: bool = False):
        cleanup = Cleanup()
        if not preserve:
            cleanup.cleanup()
        plan = RUNTIME / "plan.md"
        plan.write_text("# Plan\n", encoding="utf-8")
        output = RUNTIME / f"review-R{round_number}.json"
        captured: list[list[str]] = []

        def fake_run(command, **kwargs):
            captured.append(command)
            if mode == "timeout":
                raise claude_review.subprocess.TimeoutExpired(command, 1)
            if mode == "failure":
                return SimpleNamespace(returncode=9)
            if mode == "corrupt":
                text = "not-json"
            else:
                payload = {
                    "type": "result",
                    "is_error": False,
                    "structured_output": {**VALID, **({"score": True} if mode == "invalid-review" else {})},
                }
                if mode != "missing-session":
                    payload["session_id"] = "claude-new"
                text = json.dumps(payload)
            kwargs["stdout"].write(text + "\n")
            kwargs["stdout"].flush()
            return SimpleNamespace(returncode=0)

        args = ["claude_review.py", str(plan), str(output)] + ([session] if session else [])
        with mock.patch.object(claude_review, "repository_for", return_value=RUNTIME), mock.patch.object(
            claude_review, "resolve_cli", return_value=["claude"]
        ), mock.patch.object(claude_review.subprocess, "run", side_effect=fake_run):
            result = claude_review.run(args, timeout=0.01)
        return cleanup, output, result, captured

    def test_command_is_read_only_structured_and_resumable(self):
        schema = review_common.validate_schema()
        first = claude_review.build_command(["claude"], schema, None, "new-id", "prompt")
        self.assertEqual(first[:6], ["claude", "-p", "--model", "opus", "--effort", "high"])
        self.assertIn("plan", first)
        self.assertIn("Read,Glob,Grep", first)
        self.assertIn("--json-schema", first)
        self.assertEqual(first[-3:-1], ["--session-id", "new-id"])
        resumed = claude_review.build_command(["claude"], schema, "old-id", "unused", "prompt")
        self.assertEqual(resumed[-3:-1], ["--resume", "old-id"])

    def test_result_string_is_normalized(self):
        payload = json.dumps({"session_id": "sid", "result": json.dumps(VALID)})
        self.assertEqual(claude_review.extract_result(payload), ("sid", VALID))

    def test_success_state_artifacts_and_resume(self):
        cleanup, output, result, _ = self.invoke("success")
        self.addCleanup(cleanup.cleanup)
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), VALID)
        state = json.loads((RUNTIME / "state.json").read_text(encoding="utf-8"))
        self.assertEqual((state["backend"], state["reviewer"], state["session_id"]),
                         ("external-claude", "claude-code", "claude-new"))
        self.assertTrue(Path(str(output.with_suffix("")) + ".events.jsonl").is_file())
        temporary, _, actual, captured = self.invoke("success", round_number=2, session="claude-old")
        temporary.cleanup()
        self.assertEqual(actual, 0)
        self.assertIn("--resume", captured[0])
        self.assertIn("claude-old", captured[0])

    def test_failure_timeout_and_protocol_errors(self):
        for mode, expected in (
            ("failure", 3),
            ("timeout", 3),
            ("corrupt", 4),
            ("invalid-review", 4),
            ("missing-session", 4),
        ):
            with self.subTest(mode=mode):
                temporary, _, actual, _ = self.invoke(mode)
                temporary.cleanup()
                self.assertEqual(actual, expected)

    def test_backend_switch_starts_new_session_with_previous_json(self):
        Cleanup().cleanup()
        (RUNTIME / "review-R1.json").write_text(json.dumps(VALID), encoding="utf-8")
        (RUNTIME / "state.json").write_text(
            json.dumps({"backend": "external-codex", "session_id": "codex-id"}), encoding="utf-8"
        )
        cleanup, _, result, captured = self.invoke("success", round_number=2, preserve=True)
        self.addCleanup(cleanup.cleanup)
        self.assertEqual(result, 0)
        self.assertNotIn("--resume", captured[0])
        self.assertIn("上一轮 JSON", captured[0][-1])

    def test_input_exit_code(self):
        self.assertEqual(claude_review.run(["claude_review.py"]), 2)


if __name__ == "__main__":
    unittest.main()
