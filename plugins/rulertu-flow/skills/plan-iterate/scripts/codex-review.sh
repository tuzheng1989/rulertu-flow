#!/usr/bin/env sh
# POSIX compatibility layer; Windows callers invoke codex_review.py directly.
exec python3 "$(dirname "$0")/codex_review.py" "$@"
