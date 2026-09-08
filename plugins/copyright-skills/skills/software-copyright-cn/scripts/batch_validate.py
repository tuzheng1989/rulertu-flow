#!/usr/bin/env python3
"""Validate a multi-filing batch configuration before any material is generated.

一份项目拆多个软著申报前的批量校验：条目间文件唯一归属（共享文件必须列入
allowlist）、每份代码行达标（内部风控下限，非官方要求）、条目两两源码查重
（复用同插件 similarity_check 的 6 行窗口指纹）。任一阻断项存在则非零退出；
通过只代表拆分本身过了本地自检，不等于机关审查通过。

流程文档见 references/multi-filing.md（权威出处）。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "copyright-code-review" / "scripts"))

from inventory_repo import DEFAULT_EXCLUDES, SOURCE_EXTENSIONS, discover, git_output, matches
from strip_source import StripError, code_line_rows
from similarity_check import check_file, normalize_lines, shingles

MIN_CODE_LINES_DEFAULT = 500


def decode(data: bytes) -> str:
    """与 build_source_docx.decode 同口径（utf-8-sig/utf-8/gb18030/replace）。"""
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace")


def build_entry_index(
    files: list[tuple[str, Path]], window: int
) -> tuple[dict, list[dict]]:
    """按条目文件集构造指纹索引，结构与 similarity_check.build_reference_index 一致。"""
    index: dict[str, list[tuple[int, int]]] = {}
    ref_files: list[dict] = []
    for relative, path in sorted(files):
        content = normalize_lines(path)
        shs = shingles(content, window)
        file_idx = len(ref_files)
        ref_files.append({
            "path": relative,
            "content_lines": len(content),
            "shingle_count": len(shs),
            "linenos": [number for number, _ in content],
            "shingles": shs,
        })
        for sh_idx, sh in enumerate(shs):
            index.setdefault(sh["hash"], []).append((file_idx, sh_idx))
    return index, ref_files


def resolve_entry_files(
    repo: Path, entry: dict, exclusions: list[str]
) -> list[str]:
    """按 module_roots + 排除规则解析条目文件集，返回排序后的相对路径。"""
    include_roots = [value.strip("/\\") for value in entry["module_roots"]]
    files: list[str] = []
    for path in discover(repo):
        try:
            relative = path.resolve().relative_to(repo).as_posix()
        except (OSError, ValueError):
            continue
        if path.suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        if not any(relative == root or relative.startswith(root + "/") for root in include_roots):
            continue
        if matches(relative, exclusions):
            continue
        files.append(relative)
    return sorted(files, key=lambda value: (value.casefold(), value))


def count_code_lines(repo: Path, files: list[str]) -> tuple[int, int]:
    """逐文件统计代码行与物理行（strip_source 口径），返回 (code, physical)。"""
    code_total = 0
    physical_total = 0
    for relative in files:
        data = (repo / relative).read_bytes()
        physical_total += data.count(b"\n") + (0 if data.endswith(b"\n") or not data else 1)
        try:
            rows, _ = code_line_rows(decode(data), Path(relative).suffix)
        except StripError as exc:
            raise SystemExit(f"code line accounting failed: {relative}: {exc}") from exc
        code_total += len(rows)
    return code_total, physical_total


def validate_batch(
    repo: Path, batch: dict, min_code_lines: int,
    window: int, threshold: float, min_run: int,
) -> dict:
    """全量校验，返回可直接序列化的报告（failures 非空即阻断）。"""
    failures: list[str] = []
    review_items: list[str] = []
    entries: list[dict] = batch.get("entries") or []
    if not entries:
        failures.append("batch.entries is empty")
    allowlist = set(batch.get("shared_allowlist") or [])
    params = batch.get("similarity") or {}

    seen_names: dict[str, str] = {}
    seen_outputs: dict[str, str] = {}
    file_sets: dict[str, list[str]] = {}
    entry_reports: list[dict] = []

    for entry in entries:
        name = entry.get("name")
        version = entry.get("version")
        output_dir = entry.get("output_dir")
        module_roots = entry.get("module_roots") or []
        label = f"{name or '<unnamed>'} {version or ''}".strip()
        if not name or not version:
            failures.append(f"{label}: name and version are required")
        if not module_roots:
            failures.append(f"{label}: module_roots is required")
        if not output_dir:
            failures.append(f"{label}: output_dir is required")
        if output_dir:
            if output_dir in seen_outputs:
                failures.append(
                    f"{label}: output_dir duplicates {seen_outputs[output_dir]}: {output_dir}"
                )
            else:
                seen_outputs[output_dir] = label
        if name and version:
            key = f"{name}|{version}"
            if key in seen_names:
                failures.append(f"{label}: duplicate name+version with {seen_names[key]}")
            else:
                seen_names[key] = label

        exclusions = DEFAULT_EXCLUDES + list(entry.get("exclude") or [])
        files = resolve_entry_files(repo, entry, exclusions) if module_roots else []
        file_sets[label] = files
        if not files:
            failures.append(f"{label}: module_roots resolve to no source files")

        code_lines = physical_lines = 0
        if files:
            code_lines, physical_lines = count_code_lines(repo, files)
            if code_lines < min_code_lines:
                failures.append(
                    f"{label}: code lines {code_lines} below minimum {min_code_lines}"
                )
        first = entry.get("first")
        if first and files and first not in files:
            failures.append(f"{label}: --first path not in entry files: {first}")

        entry_reports.append({
            "name": name,
            "version": version,
            "module_roots": module_roots,
            "exclude": list(entry.get("exclude") or []),
            "output_dir": output_dir,
            "first": first,
            "file_count": len(files),
            "code_lines": code_lines,
            "physical_lines": physical_lines,
            "files": files,
        })

    # 唯一归属：跨条目共享文件必须列入 allowlist，否则阻断
    owners: dict[str, list[str]] = {}
    for label, files in file_sets.items():
        for relative in files:
            owners.setdefault(relative, []).append(label)
    shared_files: list[dict] = []
    for relative, labels in sorted(owners.items()):
        if len(labels) < 2:
            continue
        allowed = relative in allowlist
        shared_files.append({"path": relative, "entries": sorted(labels), "allowed": allowed})
        if allowed:
            review_items.append(
                f"shared file {relative} allowed by allowlist; entries: {', '.join(sorted(labels))}"
            )
        else:
            failures.append(
                f"shared file not in allowlist: {relative} (entries: {', '.join(sorted(labels))})"
            )
    unknown_allow = sorted(allowlist - set(owners))
    for relative in unknown_allow:
        review_items.append(f"allowlist entry matches no file: {relative}")

    # 两两查重：i 的文件查 j 的索引，双向都跑，任一方向标记即该对阻断。
    # allowlist 共享文件有意出现在多份材料中，其雷同已知可接受，排除在比对外
    pair_sets = {
        label: [rel for rel in files if rel not in allowlist]
        for label, files in file_sets.items()
    }
    pairs: list[dict] = []
    labels = [entry["name"] + " " + (entry["version"] or "") for entry in entries]
    valid = [label for label in labels if pair_sets.get(label)]
    for i in range(len(valid)):
        for j in range(i + 1, len(valid)):
            a, b = valid[i], valid[j]
            flagged: list[dict] = []
            for source, target in ((a, b), (b, a)):
                index, ref_files = build_entry_index(
                    [(rel, repo / rel) for rel in pair_sets[target]], window
                )
                for relative in pair_sets[source]:
                    result = check_file(
                        repo / relative, relative, index, ref_files,
                        window, threshold, min_run,
                    )
                    if result:
                        result["direction"] = f"{source} -> {target}"
                        flagged.append(result)
            if flagged:
                failures.append(
                    f"pair {a} <-> {b}: {len(flagged)} file(s) exceed similarity limits"
                )
            pairs.append({
                "entries": [a, b],
                "flagged_count": len(flagged),
                "max_containment": max(
                    (item["containment"] for item in flagged), default=0.0
                ),
                "flagged": flagged,
            })

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": str(repo),
        "parameters": {
            "min_code_lines": min_code_lines,
            "similarity": {
                "window": window,
                "containment_threshold": threshold,
                "min_run_lines": min_run,
            },
        },
        "entries": entry_reports,
        "shared_files": shared_files,
        "pairs": pairs,
        "failures": failures,
        "review_items": review_items,
        "passed": not failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-code-lines", type=int, default=MIN_CODE_LINES_DEFAULT)
    parser.add_argument("--window", type=int, default=6)
    parser.add_argument("--containment-threshold", type=float, default=0.2)
    parser.add_argument("--min-run", type=int, default=10)
    args = parser.parse_args()

    repo = args.repo.resolve()
    batch = json.loads(args.batch.read_text(encoding="utf-8"))
    report = validate_batch(
        repo, batch,
        min_code_lines=args.min_code_lines,
        window=args.window,
        threshold=args.containment_threshold,
        min_run=args.min_run,
    )
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    status = git_output(repo, "status", "--porcelain=v1")
    report["git"] = {
        "commit": git_output(repo, "rev-parse", "HEAD"),
        "branch": git_output(repo, "branch", "--show-current"),
        "dirty": bool(status) if status is not None else None,
    }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"entries={len(report['entries'])} passed={report['passed']} "
        f"failures={len(report['failures'])} output={output}"
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())