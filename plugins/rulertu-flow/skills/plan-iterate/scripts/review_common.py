"""Shared protocol handling for the plan-review subagent channel."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from normalize import ReviewError, atomic_write_json, normalize_file

_PLUGIN_SCRIPTS = str(Path(__file__).resolve().parents[3] / "scripts")
if _PLUGIN_SCRIPTS not in sys.path:
    sys.path.insert(0, _PLUGIN_SCRIPTS)
from codex_exec import EXIT_INPUT, EXIT_PROCESS, EXIT_PROTOCOL

ROUND_PATTERN = re.compile(r"review-R(\d+)\.json$")
SCHEMA_PATH = Path(__file__).with_name("review-schema.json")
REQUIRED_FIELDS = {"overall_quality", "score", "issues", "suggestions"}


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
        "issues 每项必须且只能含 severity、title、detail、suggestion 四个字段，"
        "severity 取值只能是 P0、P1 或 P2。"
        "达到 8.5 分且无 P0/P1 才算通过。"
    )


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


def main(argv: list[str]) -> int:
    """子代理评审通道的落盘入口：归一化校验与 state 写入。

    用法：
      review_common.py normalize <review.json>
      review_common.py state <plan> <round> <review.json>
    """
    args = argv[1:]
    if len(args) == 2 and args[0] == "normalize":
        try:
            normalize_file(Path(args[1]))
        except ReviewError as exc:
            print(f"protocol error: {exc}", file=sys.stderr)
            return EXIT_PROTOCOL
        return 0
    if len(args) == 4 and args[0] == "state":
        plan, round_number, output = Path(args[1]), int(args[2]), Path(args[3])
        write_state(output, plan, round_number, "subagent-auditor", "auditor", "subagent")
        return 0
    print(
        "usage: review_common.py normalize <review.json> | state <plan> <round> <review.json>",
        file=sys.stderr,
    )
    return EXIT_INPUT


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
