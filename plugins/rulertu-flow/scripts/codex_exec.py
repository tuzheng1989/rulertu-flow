"""Plugin-level Codex CLI exec layer, shared by codex-consult and plan-iterate.

Usage: codex_exec.py <output> <prompt> [session-id]
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

EXIT_INPUT, EXIT_PROCESS, EXIT_PROTOCOL = 2, 3, 4


class CodexExecError(Exception):
    """Input or environment problem that maps to exit code 2."""


def resolve_cli(name: str, *, platform_name: str | None = None) -> list[str]:
    """Return a shell-free executable prefix, including npm's Windows wrapper case."""
    platform_name = platform_name or os.name
    if platform_name != "nt":
        executable = shutil.which(name)
        if executable:
            return [executable]
        raise CodexExecError(f"CLI is not installed: {name}")
    for extension in (".exe", ".com"):
        executable = shutil.which(f"{name}{extension}")
        if executable:
            return [executable]
    wrapper = shutil.which(f"{name}.cmd")
    if wrapper and name == "codex":
        node = shutil.which("node.exe") or shutil.which("node")
        entrypoint = Path(wrapper).parent / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
        if node and entrypoint.is_file():
            return [node, str(entrypoint)]
    raise CodexExecError(f"no shell-free Windows executable found for: {name}")


def repository_for(anchor: Path | None = None) -> Path:
    """Resolve repo root from the anchor file's directory, or the process cwd when None."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=str(anchor.parent) if anchor else None,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return Path(result.stdout.strip()).resolve()


def active_profile() -> str:
    # CODEX_PROFILE 优先（如注入 -p glm 规避宿主账号配额）；未设置时回退旧名
    # CODEX_REVIEW_PROFILE，保持存量环境兼容；两者都未设置时无 profile。
    for name in ("CODEX_PROFILE", "CODEX_REVIEW_PROFILE"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def build_command(prefix: list[str], repo: Path, output: Path, session_id: str | None, prompt: str) -> list[str]:
    profile = active_profile()
    prof = ["-p", profile] if profile else []
    if session_id:
        return prefix + ["exec", *prof, "resume", session_id, "--json", "-o", str(output), prompt]
    return prefix + ["exec", *prof, "-s", "read-only", "-C", str(repo), "--json", "-o", str(output), prompt]


def extract_thread_id(events: str) -> str | None:
    for line in events.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "thread.started" and isinstance(event.get("thread_id"), str):
            return event["thread_id"]
    return None


def artifact_paths(output: Path) -> tuple[Path, Path, Path]:
    stem = output.with_suffix("")
    return Path(f"{stem}.events.jsonl"), Path(f"{stem}.stderr.log"), Path(f"{stem}.log")


def write_log(log: Path, returncode: int, events: Path, stderr: Path) -> tuple[str, str]:
    events_text = events.read_text(encoding="utf-8")
    stderr_text = stderr.read_text(encoding="utf-8")
    log.write_text(
        f"exit_code={returncode}\nevents={events.name}\nstderr={stderr.name}\n"
        f"\n[events]\n{events_text}\n[stderr]\n{stderr_text}",
        encoding="utf-8",
    )
    return events_text, stderr_text


class ExecResult:
    def __init__(self, returncode: int, events_text: str, log_path: Path) -> None:
        self.returncode = returncode
        self.events_text = events_text
        self.log_path = log_path


def run_codex(
    prefix: list[str],
    repo: Path,
    output: Path,
    session_id: str | None,
    prompt: str,
    *,
    timeout: float | None = None,
) -> ExecResult:
    """Run codex once; events/stderr/log land next to output. Process failures map to returncode -1."""
    output.parent.mkdir(parents=True, exist_ok=True)
    events_path, stderr_path, log_path = artifact_paths(output)
    try:
        with events_path.open("w", encoding="utf-8", newline="\n") as events, stderr_path.open(
            "w", encoding="utf-8", newline="\n"
        ) as errors:
            completed = subprocess.run(
                build_command(prefix, repo, output, session_id, prompt),
                cwd=repo,
                stdin=subprocess.DEVNULL,
                stdout=events,
                stderr=errors,
                timeout=timeout,
                check=False,
            )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log_path.write_text(f"process failure: {exc}\n", encoding="utf-8")
        return ExecResult(-1, "", log_path)
    events_text, _ = write_log(log_path, completed.returncode, events_path, stderr_path)
    return ExecResult(completed.returncode, events_text, log_path)


def parse_inputs(argv: list[str]) -> tuple[Path, str, str | None]:
    if len(argv) not in {3, 4}:
        raise CodexExecError("usage: codex_exec.py <output> <prompt> [session-id]")
    output = Path(argv[1]).expanduser().resolve()
    if not argv[2].strip():
        raise CodexExecError("prompt must not be empty")
    return output, argv[2], argv[3] if len(argv) == 4 else None


def main(argv: Sequence[str], *, timeout: float | None = None) -> int:
    try:
        output, prompt, session = parse_inputs(list(argv))
        repo = repository_for()
        prefix = resolve_cli("codex")
    except (OSError, subprocess.SubprocessError, CodexExecError) as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return EXIT_INPUT
    result = run_codex(prefix, repo, output, session, prompt, timeout=timeout)
    if result.returncode != 0:
        return EXIT_PROCESS
    thread_id = extract_thread_id(result.events_text) or session
    if not thread_id:
        return EXIT_PROTOCOL
    print(f"SESSION_ID={thread_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
