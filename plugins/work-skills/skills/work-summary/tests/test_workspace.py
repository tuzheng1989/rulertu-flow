import json
import os
from pathlib import Path
import subprocess
import sys
import shutil
import uuid
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "workspace.py"


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parent / ("scratch_" + uuid.uuid4().hex)
        self.root.mkdir()
        self.env = dict(os.environ, XDG_CONFIG_HOME=str(self.root / "config"), PYTHONIOENCODING="utf-8")
        self.a = self.root / "a"
        self.b = self.root / "b"
        self.a.mkdir()
        self.b.mkdir()

    def tearDown(self):
        shutil.rmtree(self.root)

    def run_cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                                env=self.env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0 if ok else 1, result.stderr)
        return json.loads(result.stdout) if ok else result.stderr

    def test_configuration_reuse_switch_and_missing_directory(self):
        self.run_cli("get", ok=False)
        self.assertEqual(self.run_cli("set", self.a / "."), str(self.a.resolve()))
        self.assertEqual(self.run_cli("get"), str(self.a.resolve()))
        self.run_cli("reserve", self.b, "2026-04-01", "personal")
        self.assertEqual(self.run_cli("get"), str(self.a.resolve()))
        self.run_cli("set", self.root / "missing", ok=False)
        self.assertEqual(self.run_cli("get"), str(self.a.resolve()))
        self.run_cli("set", self.b)
        self.assertEqual(self.run_cli("get"), str(self.b.resolve()))
        shutil.rmtree(self.b)
        self.run_cli("get", ok=False)

    def test_reserve_never_overwrites_and_separates_modes(self):
        first = Path(self.run_cli("reserve", self.a, "2026-04-01", "personal"))
        first.write_text("original", encoding="utf-8")
        second = Path(self.run_cli("reserve", self.a, "2026-04-01", "personal"))
        team = Path(self.run_cli("reserve", self.a, "2026-04-01", "team"))
        self.assertEqual(len({first, second, team}), 3)
        self.assertEqual(first.read_text(encoding="utf-8"), "original")
        self.run_cli("reserve", self.a, "bad", "team", ok=False)

    def test_discovery_includes_legacy_and_reports_unreadable(self):
        legacy = self.a / "旧月报.txt"
        legacy.write_text("一月工作总结", encoding="utf-8")
        invalid = self.a / "bad.md"
        invalid.write_bytes(b"\xff")
        (self.a / "ignored.pdf").write_bytes(b"ignored")
        result = self.run_cli("discover", self.a)
        self.assertEqual(result["files"], [str(legacy)])
        self.assertEqual(result["errors"][0]["path"], str(invalid))


if __name__ == "__main__":
    unittest.main()
