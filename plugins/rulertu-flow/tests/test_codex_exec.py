from __future__ import annotations

import contextlib
import io
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

PLUGIN_SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(PLUGIN_SCRIPTS))

import codex_exec  # noqa: E402

RUNTIME = Path(__file__).parent / "runtime"


class Cleanup:
    def cleanup(self):
        for path in RUNTIME.iterdir():
            if path.name != ".gitkeep" and path.is_file():
                path.unlink()


class CommandTests(unittest.TestCase):
    def test_first_resume_and_thread_event(self):
        repo, output = Path("C:/repo"), Path("C:/out/consult-R1.md")
        first = codex_exec.build_command(["codex"], repo, output, None, "prompt")
        self.assertEqual(first[:7], ["codex", "exec", "-s", "read-only", "-C", str(repo), "--json"])
        resumed = codex_exec.build_command(["codex"], repo, output, "id", "prompt")
        self.assertEqual(resumed[:4], ["codex", "exec", "resume", "id"])
        self.assertEqual(
            codex_exec.extract_thread_id('{"type":"thread.started","thread_id":"tid"}\n'), "tid"
        )

    def test_profile_prefers_new_name_and_falls_back(self):
        with mock.patch.dict(codex_exec.os.environ, {"CODEX_PROFILE": "glm", "CODEX_REVIEW_PROFILE": "old"}):
            command = codex_exec.build_command(["codex"], Path("r"), Path("o.md"), None, "p")
        self.assertEqual(command[command.index("-p") + 1], "glm")
        with mock.patch.dict(codex_exec.os.environ, {"CODEX_PROFILE": "", "CODEX_REVIEW_PROFILE": "old"}):
            command = codex_exec.build_command(["codex"], Path("r"), Path("o.md"), None, "p")
        self.assertEqual(command[command.index("-p") + 1], "old")
        with mock.patch.dict(codex_exec.os.environ, {"CODEX_PROFILE": "", "CODEX_REVIEW_PROFILE": ""}):
            command = codex_exec.build_command(["codex"], Path("r"), Path("o.md"), None, "p")
        self.assertNotIn("-p", command)

    def test_shell_free_cli_resolution(self):
        with mock.patch.object(codex_exec.shutil, "which", return_value="/usr/bin/codex"):
            self.assertEqual(codex_exec.resolve_cli("codex", platform_name="posix"), ["/usr/bin/codex"])
        paths = {
            "codex.exe": None,
            "codex.com": None,
            "codex.cmd": "C:/npm/codex.cmd",
            "node.exe": "C:/node/node.exe",
        }
        with mock.patch.object(codex_exec.shutil, "which", side_effect=lambda name: paths.get(name)), mock.patch.object(
            codex_exec.Path, "is_file", return_value=True
        ):
            self.assertEqual(
                codex_exec.resolve_cli("codex", platform_name="nt"),
                ["C:/node/node.exe", "C:\\npm\\node_modules\\@openai\\codex\\bin\\codex.js"],
            )

    def test_repository_for_resolves_from_cwd_or_anchor(self):
        root = codex_exec.repository_for()
        self.assertEqual(root, Path(__file__).resolve().parents[3])
        self.assertEqual(codex_exec.repository_for(Path(__file__)), root)


class CliTests(unittest.TestCase):
    def setUp(self):
        Cleanup().cleanup()

    def tearDown(self):
        Cleanup().cleanup()

    def invoke(self, mode: str, session: str | None = None):
        output = RUNTIME / "consult-R1.md"

        def fake_run(command, **kwargs):
            target = Path(command[command.index("-o") + 1])
            if mode == "timeout":
                raise codex_exec.subprocess.TimeoutExpired(command, 1)
            if mode == "failure":
                return SimpleNamespace(returncode=7)
            target.write_text("final answer", encoding="utf-8")
            if mode != "missing-session":
                kwargs["stdout"].write('{"type":"thread.started","thread_id":"generic-id"}\n')
                kwargs["stdout"].flush()
            return SimpleNamespace(returncode=0)

        args = ["codex_exec.py", str(output), "summarize the repository"] + ([session] if session else [])
        with mock.patch.object(codex_exec, "repository_for", return_value=RUNTIME), mock.patch.object(
            codex_exec, "resolve_cli", return_value=["codex"]
        ), mock.patch.object(codex_exec.subprocess, "run", side_effect=fake_run) as runner, contextlib.redirect_stdout(
            io.StringIO()
        ) as stdout:
            result = codex_exec.main(args, timeout=0.01)
        return output, result, runner, stdout.getvalue()

    def test_success_prints_session_and_writes_artifacts(self):
        output, result, _, stdout = self.invoke("success")
        self.assertEqual(result, 0)
        self.assertIn("SESSION_ID=generic-id", stdout)
        self.assertEqual(output.read_text(encoding="utf-8"), "final answer")
        stem = output.with_suffix("")
        self.assertIn("[events]", Path(f"{stem}.log").read_text(encoding="utf-8"))
        self.assertTrue(Path(f"{stem}.events.jsonl").is_file())
        self.assertTrue(Path(f"{stem}.stderr.log").is_file())

    def test_resume_passes_session_id(self):
        _, result, runner, _ = self.invoke("success", session="prior-id")
        self.assertEqual(result, 0)
        command = runner.call_args[0][0]
        self.assertEqual(command[command.index("resume") + 1], "prior-id")

    def test_failure_timeout_and_protocol_exit_codes(self):
        for mode, expected in (("failure", 3), ("timeout", 3), ("missing-session", 4)):
            with self.subTest(mode=mode):
                _, result, _, _ = self.invoke(mode)
                self.assertEqual(result, expected)

    def test_input_exit_code(self):
        self.assertEqual(codex_exec.main(["codex_exec.py"]), 2)
        self.assertEqual(codex_exec.main(["codex_exec.py", str(RUNTIME / "o.md"), "   "]), 2)


if __name__ == "__main__":
    unittest.main()
