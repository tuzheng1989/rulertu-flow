"""External Codex backend. Usage: codex_review.py <plan> <output> [session-id]."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from normalize import ReviewError, normalize_file
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


def build_command(prefix: list[str], repo: Path, output: Path, session_id: str | None, prompt: str) -> list[str]:
    # CODEX_REVIEW_PROFILE：可选注入 -p <profile>（如 glm），规避宿主账号配额；
    # 未设置时行为与历史版本逐字节一致（默认无 profile）。
    profile = os.environ.get("CODEX_REVIEW_PROFILE", "").strip()
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


def run(argv: Sequence[str], *, timeout: float | None = None) -> int:
    try:
        plan, output, round_number, explicit = parse_inputs(list(argv))
        validate_schema()
        session = load_session(output, "external-codex", explicit, allow_legacy=True)
        repo = repository_for(plan)
        prefix = resolve_cli("codex")
    except (OSError, subprocess.SubprocessError, ReviewError) as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return EXIT_INPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    events_path, stderr_path, log_path = artifact_paths(output)
    prompt = prompt_for(plan, session, prior_review(output, round_number) if not session else None)
    try:
        with events_path.open("w", encoding="utf-8", newline="\n") as events, stderr_path.open(
            "w", encoding="utf-8", newline="\n"
        ) as errors:
            completed = subprocess.run(
                build_command(prefix, repo, output, session, prompt),
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
    thread_id = extract_thread_id(events_text) or session
    if not thread_id:
        return EXIT_PROTOCOL
    try:
        normalize_file(output)
    except ReviewError as exc:
        append_protocol_error(log_path, exc)
        return EXIT_PROTOCOL
    write_state(output, plan, round_number, "external-codex", "codex-cli", thread_id)
    print(f"SESSION_ID={thread_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv))
