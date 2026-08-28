#!/usr/bin/env sh
# POSIX compatibility layer; Windows callers invoke claude_review.py directly.
exec python3 "$(dirname "$0")/claude_review.py" "$@"
