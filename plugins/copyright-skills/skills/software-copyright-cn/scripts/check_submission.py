#!/usr/bin/env python3
"""Machine-check upload candidates before the online registration submission.

Consumes an ownership evidence checklist whose JSON schema is defined in
references/ownership.md (the single source of truth for that format), checks
each upload candidate (signature-page PDF, manual / source-code docx or pdf)
for existence, non-zero size and parseability (page count for PDFs), and
writes a machine-check report.

The report states machine-check facts and open to-dos only. It never issues
a submission verdict: signature clarity, print scaling and online-form vs.
worksheet consistency stay in `manual_items`, and docx line counts belong to
render_check.py (this script does not render).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import fitz
except ImportError as exc:
    raise SystemExit("PyMuPDF is required: python -m pip install pymupdf") from exc

try:
    from docx import Document as load_docx
except ImportError as exc:
    raise SystemExit("python-docx is required: python -m pip install python-docx") from exc

# 与 references/ownership.md 决策表/三态一致（schema 唯一出处，勿在此另立）
SCENARIOS = ("independent", "cooperative", "commissioned", "employment", "derivative", "transferred")
STATUSES = ("provided", "pending", "na")

MANUAL_ITEMS = [
    "签章清晰度：在线打印的申请确认签章页签章是否清晰，需人工核验。",
    "打印比例：签章页格式和打印比例未被擅自改动（核对记录见 references/registration-form.md），需人工核验。",
    "在线表单与底稿一致性：在线系统填报内容与工作底稿逐字段一致，需人工核对。",
]

RENDER_HINT = "docx 类交付件须先经 render_check.py 实测每页行数；本脚本不做渲染，渲染结论以 render-report.json 为准。"


def check_doc(path: Path) -> dict:
    entry = {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": None,
        "parsed": False,
        "pages": None,
        "error": None,
    }
    if not entry["exists"]:
        entry["error"] = "file not found"
        return entry
    entry["size_bytes"] = path.stat().st_size
    if entry["size_bytes"] == 0:
        entry["error"] = "file is empty"
        return entry
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            with fitz.open(path) as pdf:
                pages = pdf.page_count
            if pages <= 0:
                entry["error"] = f"pdf has no pages: {pages}"
                return entry
            entry["pages"] = pages
        elif suffix == ".docx":
            load_docx(str(path))  # 打开成功即视为可解析；页数属渲染结果，此处不测
        else:
            entry["error"] = f"unsupported file type: {suffix or '<none>'} (expected .pdf or .docx)"
            return entry
    except Exception as exc:  # 解析失败是可预期分支，原样记录原因
        entry["error"] = f"failed to parse: {exc}"
        return entry
    entry["parsed"] = True
    return entry


def load_ownership(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"ownership checklist not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ownership checklist is not valid JSON: {path} ({exc})") from exc
    scenario = payload.get("scenario")
    if scenario not in SCENARIOS:
        raise SystemExit(
            f"invalid ownership checklist: unknown scenario {scenario!r} "
            f"(expected one of: {', '.join(SCENARIOS)})"
        )
    items = payload.get("items", [])
    for item in items:
        if item.get("status") not in STATUSES:
            raise SystemExit(
                f"invalid ownership checklist: item {item.get('file')!r} has status "
                f"{item.get('status')!r} (expected one of: {', '.join(STATUSES)})"
            )
    counts = {status: 0 for status in STATUSES}
    for item in items:
        counts[item["status"]] += 1
    blocked_items = [
        {"file": item.get("file", ""), "type": item.get("type", ""), "note": item.get("note", "")}
        for item in items
        if item["status"] == "pending"
    ]
    return {
        "scenario": scenario,
        "provided": counts["provided"],
        "pending": counts["pending"],
        "na": counts["na"],
        "blocked_items": blocked_items,
    }


def main() -> int:
    # 错误消息含中文文件名（如权属清单条目），Windows 管道默认 cp936 会让
    # 按 utf-8 读取 stderr 的调用方解码失败；统一按 utf-8 输出诊断信息。
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs", type=Path, action="append", required=True,
                        help="待上传文件（签章页 PDF、说明书/源代码 docx 或 pdf），可重复")
    parser.add_argument("--ownership", type=Path, required=True,
                        help="权属文件清单 JSON（schema 见 references/ownership.md）")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite output: {output}")

    ownership = load_ownership(args.ownership.resolve())
    files = [check_doc(path) for path in args.docs]
    report = {
        "files": files,
        "ownership": ownership,
        "manual_items": MANUAL_ITEMS,
        "render_hint": RENDER_HINT,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    machine_failed = any(not item["parsed"] for item in files)
    return 1 if machine_failed or ownership["blocked_items"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
