"""External Codex backend. Usage: codex_review.py <plan> <output> [session-id]."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Sequence

_PLUGIN_SCRIPTS = str(Path(__file__).resolve().parents[3] / "scripts")
if _PLUGIN_SCRIPTS not in sys.path:
    sys.path.insert(0, _PLUGIN_SCRIPTS)

from codex_exec import CodexExecError, extract_thread_id, repository_for, resolve_cli, run_codex
from normalize import ReviewError, normalize_file
from review_common import (
    EXIT_INPUT,
    EXIT_PROCESS,
    EXIT_PROTOCOL,
    append_protocol_error,
    load_session,
    parse_inputs,
    prior_review,
    prompt_for,
    validate_schema,
    write_state,
)


def run(argv: Sequence[str], *, timeout: float | None = None) -> int:
    try:
        plan, output, round_number, explicit = parse_inputs(list(argv))
        validate_schema()
        session = load_session(output, "external-codex", explicit, allow_legacy=True)
        repo = repository_for(plan)
        prefix = resolve_cli("codex")
    except (OSError, subprocess.SubprocessError, ReviewError, CodexExecError) as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return EXIT_INPUT
    prompt = prompt_for(plan, session, prior_review(output, round_number) if not session else None)
    result = run_codex(prefix, repo, output, session, prompt, timeout=timeout)
    if result.returncode != 0:
        return EXIT_PROCESS
    thread_id = extract_thread_id(result.events_text) or session
    if not thread_id:
        return EXIT_PROTOCOL
    try:
        normalize_file(output)
    except ReviewError as exc:
        append_protocol_error(result.log_path, exc)
        return EXIT_PROTOCOL
    write_state(output, plan, round_number, "external-codex", "codex-cli", thread_id)
    print(f"SESSION_ID={thread_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv))
