"""Cross-platform external Codex backend for plan-iterate.

Usage: python codex_review.py <plan> <output> [session-id]
Exit codes: 0 success, 2 input/schema error, 3 process failure, 4 protocol error.
"""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence
from normalize import ReviewError, atomic_write_json, normalize_file

EXIT_INPUT, EXIT_PROCESS, EXIT_PROTOCOL = 2, 3, 4
ROUND_PATTERN = re.compile(r"review-R(\d+)\.json$")
SCHEMA_PATH = Path(__file__).with_name("review-schema.json")

def validate_schema() -> None:
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewError(f"invalid review schema: {exc}") from exc
    required = {"overall_quality", "score", "issues", "suggestions"}
    if set(schema.get("required", [])) != required or not required.issubset(schema.get("properties", {})):
        raise ReviewError("review schema required fields differ from protocol")

def repository_for(plan: Path) -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=plan.parent,
        stdin=subprocess.DEVNULL, capture_output=True, text=True,
        encoding="utf-8", check=True,
    )
    return Path(result.stdout.strip()).resolve()

def build_command(repo: Path, output: Path, session_id: str | None, prompt: str) -> list[str]:
    if session_id:
        return ["codex", "exec", "resume", session_id, "--json", "-o", str(output), prompt]
    return ["codex", "exec", "-s", "read-only", "-C", str(repo), "--json", "-o", str(output), prompt]

def extract_thread_id(events: str) -> str | None:
    for line in events.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "thread.started" and isinstance(event.get("thread_id"), str):
            return event["thread_id"]
    return None

def load_session(output: Path, explicit: str | None) -> str | None:
    if explicit:
        return explicit
    match = ROUND_PATTERN.search(output.name)
    if not match or int(match.group(1)) <= 1:
        return None
    state_path = output.parent / "state.json"
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ReviewError(f"invalid state.json: {exc}") from exc
        session = state.get("session_id")
        if isinstance(session, str) and session:
            return session
    legacy = output.parent / "session.txt"
    if legacy.exists():
        session = legacy.read_text(encoding="utf-8").strip()
        if session:
            return session
    return None

def prompt_for(plan: Path, resumed: bool) -> str:
    prefix = "重新完整阅读当前磁盘上的方案并逐条核对上一轮问题。" if resumed else "完整阅读并独立评审方案。"
    return (f"{prefix}\n方案: {plan}\n核验文件锚点与代码事实；按 P0/P1/P2 报告问题。"
            "输出严格 JSON：overall_quality、0-10 的 score、issues、suggestions。"
            "达到 8.5 分且无 P0/P1 才算通过。")

def write_state(output: Path, plan: Path, round_number: int, session_id: str) -> None:
    atomic_write_json(output.parent / "state.json", {
        "backend": "external-codex", "round": round_number,
        "plan_path": str(plan), "plan_sha256": hashlib.sha256(plan.read_bytes()).hexdigest(),
        "reviewer": "codex-cli", "session_id": session_id,
    })
    legacy = output.parent / "session.txt"
    if legacy.exists():
        legacy.unlink()

def run(argv: Sequence[str], *, timeout: float | None = None) -> int:
    if len(argv) not in {3, 4}:
        print("usage: codex_review.py <plan> <output> [session-id]", file=sys.stderr)
        return EXIT_INPUT
    plan, output = Path(argv[1]).expanduser().resolve(), Path(argv[2]).expanduser().resolve()
    match = ROUND_PATTERN.search(output.name)
    if not plan.is_file() or not match:
        print("plan must exist and output must be named review-RN.json", file=sys.stderr)
        return EXIT_INPUT
    try:
        validate_schema()
        session = load_session(output, argv[3] if len(argv) == 4 else None)
        repo = repository_for(plan)
    except (OSError, subprocess.SubprocessError, ReviewError) as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return EXIT_INPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    stem = output.with_suffix("")
    events_path, stderr_path, log_path = Path(f"{stem}.events.jsonl"), Path(f"{stem}.stderr.log"), Path(f"{stem}.log")
    command = build_command(repo, output, session, prompt_for(plan, bool(session)))
    try:
        with events_path.open("w", encoding="utf-8", newline="\n") as events, stderr_path.open("w", encoding="utf-8", newline="\n") as errors:
            completed = subprocess.run(command, cwd=repo, stdin=subprocess.DEVNULL, stdout=events,
                                       stderr=errors, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        log_path.write_text(f"process failure: {exc}\n", encoding="utf-8")
        return EXIT_PROCESS
    events_text = events_path.read_text(encoding="utf-8")
    stderr_text = stderr_path.read_text(encoding="utf-8")
    log_path.write_text(
        f"exit_code={completed.returncode}\n"
        f"events={events_path.name}\nstderr={stderr_path.name}\n"
        f"\n[events]\n{events_text}\n[stderr]\n{stderr_text}",
        encoding="utf-8",
    )
    if completed.returncode != 0:
        return EXIT_PROCESS
    thread_id = extract_thread_id(events_text) or session
    if not thread_id:
        return EXIT_PROTOCOL
    try:
        normalize_file(output)
    except ReviewError as exc:
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(f"protocol error: {exc}\n")
        return EXIT_PROTOCOL
    write_state(output, plan, int(match.group(1)), thread_id)
    print(f"SESSION_ID={thread_id}")
    return 0

if __name__ == "__main__":
    raise SystemExit(run(sys.argv))
