"""External Claude Code backend. Usage: claude_review.py <plan> <output> [session-id]."""
from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Sequence

from normalize import ReviewError, atomic_write_json, normalize_review
from review_common import (
    EXIT_INPUT,
    EXIT_PROCESS,
    EXIT_PROTOCOL,
    SCHEMA_PATH,
    append_protocol_error,
    artifact_paths,
    load_session,
    parse_inputs,
    prior_review,
    prompt_for,
    repository_for,
    resolve_cli,
    validate_schema,
    write_log,
    write_state,
)


def build_command(
    prefix: list[str], schema: dict[str, Any], session_id: str | None, new_session_id: str, prompt: str
) -> list[str]:
    command = prefix + [
        "-p",
        "--model",
        "opus",
        "--effort",
        "high",
        "--permission-mode",
        "plan",
        "--tools",
        "Read,Glob,Grep",
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(schema, ensure_ascii=False, separators=(",", ":")),
    ]
    command.extend(["--resume", session_id] if session_id else ["--session-id", new_session_id])
    command.append(prompt)
    return command


def extract_result(payload_text: str) -> tuple[str, dict[str, Any]]:
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise ReviewError(f"invalid Claude JSON output: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("is_error") is True:
        raise ReviewError("Claude result is missing or marked as an error")
    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        raise ReviewError("Claude result has no session_id")
    candidate = payload.get("structured_output")
    if candidate is None:
        candidate = payload.get("result")
    if isinstance(candidate, str):
        try:
            candidate = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise ReviewError(f"Claude result is not structured JSON: {exc}") from exc
    return session_id, normalize_review(candidate)


def run(argv: Sequence[str], *, timeout: float | None = None) -> int:
    try:
        plan, output, round_number, explicit = parse_inputs(list(argv))
        schema = validate_schema()
        session = load_session(output, "external-claude", explicit, allow_legacy=False)
        repo = repository_for(plan)
        prefix = resolve_cli("claude")
    except (OSError, subprocess.SubprocessError, ReviewError) as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return EXIT_INPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    events_path, stderr_path, log_path = artifact_paths(output)
    new_session_id = str(uuid.uuid4())
    prompt = prompt_for(plan, session, prior_review(output, round_number) if not session else None)
    try:
        with events_path.open("w", encoding="utf-8", newline="\n") as events, stderr_path.open(
            "w", encoding="utf-8", newline="\n"
        ) as errors:
            completed = subprocess.run(
                build_command(prefix, schema, session, new_session_id, prompt),
                cwd=repo,
                stdin=subprocess.DEVNULL,
                stdout=events,
                stderr=errors,
                timeout=timeout,
                check=False,
            )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log_path.write_text(f"process failure: {exc}\n", encoding="utf-8")
        return EXIT_PROCESS
    events_text, _ = write_log(log_path, completed.returncode, events_path, stderr_path)
    if completed.returncode != 0:
        return EXIT_PROCESS
    try:
        session_id, review = extract_result(events_text)
        atomic_write_json(output, review)
    except ReviewError as exc:
        append_protocol_error(log_path, exc)
        return EXIT_PROTOCOL
    write_state(output, plan, round_number, "external-claude", "claude-code", session_id)
    print(f"SESSION_ID={session_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv))
