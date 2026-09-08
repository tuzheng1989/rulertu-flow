#!/usr/bin/env python3
"""Collect static compliance facts from source files before copyright submission."""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


SOURCE_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cs", ".css", ".go", ".h", ".hpp", ".html",
    ".java", ".js", ".jsx", ".kt", ".kts", ".php", ".py", ".rb", ".rs",
    ".scala", ".sh", ".sql", ".swift", ".ts", ".tsx", ".vue",
}
DEFAULT_EXCLUDES = [
    ".git/**", ".agents/**", ".codex/**", ".venv*/**", "venv/**", "node_modules/**",
    "dist/**", "build/**", "coverage/**", "__pycache__/**", ".pytest_cache/**",
    "docs/**", "data/**", "results/**", "reports/**", "logs/**",
    "tests/**", "**/tests/**", "conftest.py", "**/test_*.py", "**/*_test.py",
    "**/*.min.js", "**/*.min.css",
    "**/vendor/**", "**/generated/**", "**/.env", "**/.env.*",
]
PLACEHOLDER_PATTERN = re.compile(
    r"\bTODO\b|\bFIXME\b|\bXXX\b|\bHACK\b|待实现|待补充|待完善|待接入|占位", re.IGNORECASE
)
LICENSE_PATTERN = re.compile(
    r"Copyright\s*[©(]|Apache License|GNU General Public|MIT License|BSD [23]-Clause"
    r"|Licensed under|@author",
    re.IGNORECASE,
)
STUB_PATTERN = re.compile(r"^\s*(pass|\.\.\.)\s*(#.*)?$")
ENTRY_CODE_PATTERN = re.compile(
    r"if __name__\s*==\s*['\"]__main__['\"]|def main\s*\(|func main\s*\("
    r"|public static void main|int main\s*\(",
)
ENTRY_FILE_NAMES = {
    "main.py", "app.py", "manage.py", "index.js", "index.ts", "main.go",
    "main.c", "main.cpp", "app.java", "main.java",
}
MOJIBAKE_SNIPPETS = ("�", "锟斤拷", "ï¿½")
# AI 特征注释：Markdown 加粗、行内代码反引号、§ 文档精确引用、带斜杠的相对路径
# 引用、中文内容的半角括号元组式注（(只写不读,P5-Q1)）。全行检索，与占位符同样
# 容忍字符串内误报，命中项走用户逐条审批，不自动改写。
MD_BOLD_PATTERN = re.compile(r"\*\*[^*\s][^*]*[^*\s]\*\*|\*\*[^*\s]\*\*")
INLINE_CODE_PATTERN = re.compile(r"`[^`]+`")
SECTION_REF_PATTERN = re.compile(r"§")
PATH_REF_PATTERN = re.compile(
    r"[A-Za-z0-9_][A-Za-z0-9_.-]*/[A-Za-z0-9_./-]*\."
    r"(?:py|js|jsx|ts|tsx|vue|json|md|yaml|yml|csv|txt|sh|sql|html|css)\b"
)
HALFWIDTH_PAREN_NOTE_PATTERN = re.compile(
    r"\([^()\"'`=%]*[一-鿿][^()\"'`=%]*,[^()\"'`=%]*\)"
)
MAX_LISTED_HITS = 50
# 反引号在 shell 里是命令替换语法，行内代码检测只针对 # 注释行，避免误报
INLINE_CODE_COMMENT_PREFIXES = ("#",)
# 2026-09-04 审核反馈新增：注释块分隔线横幅、Markdown 列表、强调性表达、
# 需求编号（W/R/T/G/P 系）、生成工具名。同走"命中即列项、人工审批"口径。
BANNER_DIVIDER_PATTERN = re.compile(r"^\s*(?:#|//).*[=\-_]{4,}")
MD_LIST_PATTERN = re.compile(r"^\s*[-*]\s+\S|^\s*\d+[.)]\s+\S")
EMPH_PHRASES = ("不可绕过", "唯一出口", "绝不", "严禁", "红线", "如实")
REQ_ID_PATTERN = re.compile(r"\b[WRTGP][0-9]{1,3}(?:[-.·][A-Za-z0-9]{1,6})?\b")
AI_TOOL_PATTERN = re.compile(
    r"Claude|ChatGPT|Copilot|Codex|Gemini|GPT-[45o]|作为 ?AI|AI 生成|AI生成|人工智能生成|大模型生成",
    re.IGNORECASE,
)
# 2026-09-08 经验清单补充：提交材料不得含他人网址与第三方软件名（经验第 3 条
# "无他人软件名/公司名/网址"）。URL 全行检索，API endpoint 等合法引用命中后由
# 用户审批豁免；第三方软件名只查注释/docstring——import 与配置赋值里引用开源
# 库名是合法使用，注释里的宣传性提及才是驳回风险。词表大小写敏感、词边界匹配，
# 先小清单硬编码，误报/漏报积累后再外置。
SENSITIVE_URL_PATTERN = re.compile(r"https?://|www\.", re.IGNORECASE)
THIRD_PARTY_NAME_PATTERN = re.compile(
    r"\b(?:Vue|React|Angular|Django|Flask|FastAPI|Laravel|Rails"
    r"|TensorFlow|PyTorch|Kubernetes|Docker|Elasticsearch|Redis"
    r"|MySQL|PostgreSQL|MongoDB|Kafka|Nginx|Apache|WordPress"
    r"|GitLab|GitHub|Electron)\b"
)


def git_output(repo: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args], cwd=repo, text=True, encoding="utf-8", errors="replace",
            capture_output=True, check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def discover(repo: Path) -> list[Path]:
    tracked = git_output(repo, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    if tracked is not None:
        return [repo / value for value in tracked.split("\0") if value]
    return [path for path in repo.rglob("*") if path.is_file()]


def matches(path: str, patterns: list[str]) -> str | None:
    normalized = path.replace("\\", "/")
    for pattern in patterns:
        if fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch("/" + normalized, "*/" + pattern):
            return pattern
    return None


def blank_line_runs(lines: list[str]) -> list[int]:
    runs: list[int] = []
    run = 0
    for line in lines:
        if line.strip():
            if run > 2:
                runs.append(run)
            run = 0
        else:
            run += 1
    if run > 2:
        runs.append(run)
    return runs


def scan_file(path: Path, relative: str) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    hits: dict[str, list[int]] = {
        "placeholder": [],
        "license_marker": [],
        "stub_line": [],
        "mojibake": [],
        "md_markup": [],
        "inline_code": [],
        "section_ref": [],
        "path_ref": [],
        "halfwidth_paren_note": [],
        "banner_divider": [],
        "md_list": [],
        "emph_phrase": [],
        "req_id": [],
        "ai_tool_marker": [],
        "sensitive_url": [],
        "third_party_name": [],
    }
    in_docstring = False
    for number, line in enumerate(lines, start=1):
        if PLACEHOLDER_PATTERN.search(line):
            hits["placeholder"].append(number)
        if LICENSE_PATTERN.search(line) and not in_docstring:
            hits["license_marker"].append(number)
        if STUB_PATTERN.match(line) and not in_docstring:
            hits["stub_line"].append(number)
        if any(snippet in line for snippet in MOJIBAKE_SNIPPETS):
            hits["mojibake"].append(number)
        if MD_BOLD_PATTERN.search(line):
            hits["md_markup"].append(number)
        stripped = line.strip()
        if stripped.startswith(INLINE_CODE_COMMENT_PREFIXES) and INLINE_CODE_PATTERN.search(line):
            hits["inline_code"].append(number)
        if SECTION_REF_PATTERN.search(line):
            hits["section_ref"].append(number)
        if PATH_REF_PATTERN.search(line) and "http://" not in line and "https://" not in line:
            hits["path_ref"].append(number)
        if HALFWIDTH_PAREN_NOTE_PATTERN.search(line):
            hits["halfwidth_paren_note"].append(number)
        if BANNER_DIVIDER_PATTERN.search(line):
            hits["banner_divider"].append(number)
        in_commentish = in_docstring or stripped.startswith("#")
        comment_text = stripped[1:] if stripped.startswith("#") else stripped
        if in_commentish and MD_LIST_PATTERN.match(comment_text):
            hits["md_list"].append(number)
        if (in_docstring or stripped.startswith("#")) and any(w in line for w in EMPH_PHRASES):
            hits["emph_phrase"].append(number)
        if REQ_ID_PATTERN.search(line):
            hits["req_id"].append(number)
        if AI_TOOL_PATTERN.search(line):
            hits["ai_tool_marker"].append(number)
        if SENSITIVE_URL_PATTERN.search(line):
            hits["sensitive_url"].append(number)
        if in_commentish and THIRD_PARTY_NAME_PATTERN.search(line):
            hits["third_party_name"].append(number)
        if relative.endswith(".py"):
            triple = line.count(chr(34)*3)
            if in_docstring and triple % 2 == 1:
                in_docstring = False
            elif not in_docstring and triple == 1:
                in_docstring = True
    listed = {key: value[:MAX_LISTED_HITS] for key, value in hits.items() if value}
    return {
        "path": relative,
        "physical_lines": len(lines),
        "blank_lines": sum(1 for line in lines if not line.strip()),
        "blank_line_runs_over2": blank_line_runs(lines),
        "entry_candidate": path.name.lower() in ENTRY_FILE_NAMES or bool(ENTRY_CODE_PATTERN.search(text)),
        "findings": listed,
        "finding_counts": {key: len(value) for key, value in hits.items() if value},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include-root", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    args = parser.parse_args()

    repo = args.repo.resolve()
    output = args.output.resolve()
    include_roots = [value.strip("/\\") for value in args.include_root]
    exclusions = DEFAULT_EXCLUDES + args.exclude
    scanned: list[dict] = []
    excluded: list[dict] = []

    for path in discover(repo):
        try:
            relative = path.resolve().relative_to(repo).as_posix()
        except (OSError, ValueError):
            continue
        reason = None
        if include_roots and not any(relative == root or relative.startswith(root + "/") for root in include_roots):
            reason = "outside include roots"
        elif path.suffix.lower() not in SOURCE_EXTENSIONS:
            reason = "not an application source extension"
        else:
            pattern = matches(relative, exclusions)
            if pattern:
                reason = f"excluded by {pattern}"
        if reason:
            excluded.append({"path": relative, "reason": reason})
            continue
        scanned.append(scan_file(path, relative))

    scanned.sort(key=lambda item: (item["path"].casefold(), item["path"]))
    excluded.sort(key=lambda item: (item["path"].casefold(), item["path"]))
    status = git_output(repo, "status", "--porcelain=v1")
    finding_totals: dict[str, int] = {}
    for item in scanned:
        for key, count in item["finding_counts"].items():
            finding_totals[key] = finding_totals.get(key, 0) + count
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": str(repo),
        "git": {
            "commit": git_output(repo, "rev-parse", "HEAD"),
            "branch": git_output(repo, "branch", "--show-current"),
            "dirty": bool(status) if status is not None else None,
        },
        "selection": {
            "include_roots": include_roots,
            "exclude_patterns": exclusions,
            "extensions": sorted(SOURCE_EXTENSIONS),
        },
        "scanned_files": scanned,
        "excluded_files": excluded,
        "summary": {
            "scanned_file_count": len(scanned),
            "total_physical_lines": sum(item["physical_lines"] for item in scanned),
            "total_blank_lines": sum(item["blank_lines"] for item in scanned),
            "entry_candidates": [item["path"] for item in scanned if item["entry_candidate"]],
            "finding_totals": finding_totals,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"scanned_files={len(scanned)} findings={finding_totals} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
