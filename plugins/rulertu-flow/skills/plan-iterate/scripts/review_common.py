"""Shared protocol and artifact handling for plan-review backends."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from normalize import ReviewError, atomic_write_json

EXIT_INPUT, EXIT_PROCESS, EXIT_PROTOCOL = 2, 3, 4
ROUND_PATTERN = re.compile(r"review-R(\d+)\.json$")
SCHEMA_PATH = Path(__file__).with_name("review-schema.json")
REQUIRED_FIELDS = {"overall_quality", "score", "issues", "suggestions"}


def resolve_cli(name: str, *, platform_name: str | None = None) -> list[str]:
    """Return a shell-free executable prefix, including npm's Windows wrapper case."""
    platform_name = platform_name or os.name
    if platform_name != "nt":
        executable = shutil.which(name)
        if executable:
            return [executable]
        raise ReviewError(f"CLI is not installed: {name}")
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
    raise ReviewError(f"no shell-free Windows executable found for: {name}")


def validate_schema() -> dict[str, Any]:
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewError(f"invalid review schema: {exc}") from exc
    if set(schema.get("required", [])) != REQUIRED_FIELDS or not REQUIRED_FIELDS.issubset(
        schema.get("properties", {})
    ):
        raise ReviewError("review schema required fields differ from protocol")
    return schema


def repository_for(plan: Path) -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=plan.parent,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return Path(result.stdout.strip()).resolve()


def parse_inputs(argv: list[str]) -> tuple[Path, Path, int, str | None]:
    if len(argv) not in {3, 4}:
        raise ReviewError("usage: <backend> <plan> <review-RN.json> [session-id]")
    plan = Path(argv[1]).expanduser().resolve()
    output = Path(argv[2]).expanduser().resolve()
    match = ROUND_PATTERN.search(output.name)
    if not plan.is_file() or not match:
        raise ReviewError("plan must exist and output must be named review-RN.json")
    return plan, output, int(match.group(1)), argv[3] if len(argv) == 4 else None


def load_session(output: Path, backend: str, explicit: str | None, *, allow_legacy: bool) -> str | None:
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
        if state.get("backend") == backend and isinstance(session, str) and session:
            return session
    legacy = output.parent / "session.txt"
    if allow_legacy and legacy.exists():
        session = legacy.read_text(encoding="utf-8").strip()
        if session:
            return session
    return None


def prior_review(output: Path, round_number: int) -> str | None:
    if round_number <= 1:
        return None
    previous = output.with_name(f"review-R{round_number - 1}.json")
    return previous.read_text(encoding="utf-8") if previous.is_file() else None


def prompt_for(plan: Path, session: str | None, previous: str | None) -> str:
    if session:
        opening = "重新完整阅读当前磁盘上的方案，并逐条核对同一会话上一轮的问题。"
    elif previous:
        opening = f"这是新评审会话。重新完整阅读方案，并核对上一轮 JSON：\n{previous}\n"
    else:
        opening = "完整阅读并独立评审方案。"
    return (
        f"{opening}\n方案: {plan}\n"
        "核验文件锚点与代码事实；按 P0/P1/P2 报告问题。"
        "规范性基线只用于检查变更是否显式且穿透完整，不因方案面向未来而否决。"
        "输出严格 JSON：overall_quality、0-10 的 score、issues、suggestions。"
        "达到 8.5 分且无 P0/P1 才算通过。"
    )


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


def append_protocol_error(log: Path, error: Exception) -> None:
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"\nprotocol error: {error}\n")


def write_state(
    output: Path,
    plan: Path,
    round_number: int,
    backend: str,
    reviewer: str,
    session_id: str,
) -> None:
    atomic_write_json(
        output.parent / "state.json",
        {
            "backend": backend,
            "round": round_number,
            "plan_path": str(plan),
            "plan_sha256": hashlib.sha256(plan.read_bytes()).hexdigest(),
            "reviewer": reviewer,
            "session_id": session_id,
        },
    )
    legacy = output.parent / "session.txt"
    if legacy.exists():
        legacy.unlink()
