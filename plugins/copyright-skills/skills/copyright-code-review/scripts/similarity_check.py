#!/usr/bin/env python3
"""Compare submission source files with local reference corpora via n-gram fingerprints."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scan_source import DEFAULT_EXCLUDES, SOURCE_EXTENSIONS, git_output, matches

MAX_LISTED_MATCHES = 20
COMMENT_PREFIXES = ("#", "//", "/*", "*", "--")


def normalize_lines(path: Path) -> list[tuple[int, str]]:
    """Return (original line number, normalized text); skip blank and pure-comment lines."""
    text = path.read_text(encoding="utf-8", errors="replace")
    content = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = " ".join(raw.strip().split()).lower()
        if not line or line.startswith(COMMENT_PREFIXES):
            continue
        content.append((number, line))
    return content


def shingles(content: list[tuple[int, str]], window: int) -> list[dict]:
    """Hash each consecutive line window; files shorter than the window use one window."""
    size = min(window, len(content))
    if size == 0:
        return []
    shs = []
    for i in range(len(content) - size + 1):
        chunk = "\n".join(text for _, text in content[i:i + size])
        digest = hashlib.blake2b(chunk.encode("utf-8"), digest_size=16).hexdigest()
        shs.append({"hash": digest, "start": i, "end": i + size - 1})
    return shs


def build_reference_index(ref_roots: list[Path], window: int) -> tuple[dict, list[dict]]:
    """Map fingerprint -> [(file index, shingle index)] over all reference roots."""
    index: dict[str, list[tuple[int, int]]] = {}
    ref_files: list[dict] = []
    for root in ref_roots:
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            if path.suffix.lower() not in SOURCE_EXTENSIONS:
                continue
            relative = path.relative_to(root).as_posix()
            if matches(relative, DEFAULT_EXCLUDES):
                continue
            content = normalize_lines(path)
            shs = shingles(content, window)
            file_idx = len(ref_files)
            ref_files.append({
                "path": f"{root.name}/{relative}",
                "content_lines": len(content),
                "shingle_count": len(shs),
                "linenos": [number for number, _ in content],
                "shingles": shs,
            })
            for sh_idx, sh in enumerate(shs):
                index.setdefault(sh["hash"], []).append((file_idx, sh_idx))
    return index, ref_files


def check_file(
    path: Path, relative: str, index: dict, ref_files: list[dict],
    window: int, threshold: float, min_run: int,
) -> dict | None:
    content = normalize_lines(path)
    shs = shingles(content, window)
    if not shs:
        return None
    size = min(window, len(content))
    matched = [False] * len(shs)
    reference_hits: dict[str, int] = {}
    examples: list[dict] = []
    for i, sh in enumerate(shs):
        hits = index.get(sh["hash"])
        if not hits:
            continue
        matched[i] = True
        file_idx, sh_idx = hits[0]
        ref = ref_files[file_idx]
        reference_hits[ref["path"]] = reference_hits.get(ref["path"], 0) + 1
        if len(examples) < MAX_LISTED_MATCHES:
            ref_start = ref["shingles"][sh_idx]["start"]
            ref_end = ref["shingles"][sh_idx]["end"]
            examples.append({
                "repo_lines": [content[sh["start"]][0], content[sh["end"]][0]],
                "reference": ref["path"],
                "reference_lines": [ref["linenos"][ref_start], ref["linenos"][ref_end]],
            })
    matched_count = sum(matched)
    containment = matched_count / len(shs)
    best_streak = streak = 0
    for flag in matched:
        streak = streak + 1 if flag else 0
        best_streak = max(best_streak, streak)
    est_run = min(best_streak + size - 1, len(content)) if best_streak else 0
    if containment < threshold and est_run < min_run:
        return None
    return {
        "path": relative,
        "content_lines": len(content),
        "shingle_count": len(shs),
        "matched_shingles": matched_count,
        "containment": round(containment, 4),
        "est_max_similar_run_lines": est_run,
        "reference_hits": [
            {"path": name, "matched_windows": count}
            for name, count in sorted(reference_hits.items(), key=lambda kv: -kv[1])
        ],
        "examples": examples,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--references", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include-root", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--window", type=int, default=6)
    parser.add_argument("--threshold", type=float, default=0.2)
    parser.add_argument("--min-run", type=int, default=10)
    args = parser.parse_args()

    repo = args.repo.resolve()
    output = args.output.resolve()
    ref_roots = [root.resolve() for root in args.references]
    for root in ref_roots:
        if not root.is_dir():
            print(f"reference root not found: {root}", file=sys.stderr)
            return 1

    index, ref_files = build_reference_index(ref_roots, args.window)

    include_roots = [value.strip("/\\") for value in args.include_root]
    exclusions = DEFAULT_EXCLUDES + args.exclude
    scanned_count = 0
    flagged: list[dict] = []
    for path in sorted(repo.rglob("*")):
        if not path.is_file():
            continue
        try:
            relative = path.resolve().relative_to(repo).as_posix()
        except (OSError, ValueError):
            continue
        if path.suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        if matches(relative, exclusions):
            continue
        if include_roots and not any(
            relative == root or relative.startswith(root + "/") for root in include_roots
        ):
            continue
        scanned_count += 1
        result = check_file(path, relative, index, ref_files, args.window, args.threshold, args.min_run)
        if result:
            flagged.append(result)

    # 序列化前剥离中间数据（指纹列表与行号映射），只留统计值
    for ref in ref_files:
        ref.pop("shingles", None)
        ref.pop("linenos", None)

    flagged.sort(key=lambda item: (-item["containment"], -item["est_max_similar_run_lines"]))
    per_reference: dict[str, int] = {}
    for item in flagged:
        for hit in item["reference_hits"]:
            per_reference[hit["path"]] = per_reference.get(hit["path"], 0) + hit["matched_windows"]
    status = git_output(repo, "status", "--porcelain=v1")
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": str(repo),
        "git": {
            "commit": git_output(repo, "rev-parse", "HEAD"),
            "branch": git_output(repo, "branch", "--show-current"),
            "dirty": bool(status) if status is not None else None,
        },
        "parameters": {
            "window": args.window,
            "containment_threshold": args.threshold,
            "min_run_lines": args.min_run,
            "references": [str(root) for root in ref_roots],
        },
        "reference_corpus": {
            "file_count": len(ref_files),
            "shingle_count": sum(ref["shingle_count"] for ref in ref_files),
        },
        "flagged_files": flagged,
        "summary": {
            "scanned_file_count": scanned_count,
            "flagged_file_count": len(flagged),
            "matched_reference_files": sorted(per_reference),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"scanned_files={scanned_count} reference_files={len(ref_files)} "
        f"flagged={len(flagged)} output={output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
