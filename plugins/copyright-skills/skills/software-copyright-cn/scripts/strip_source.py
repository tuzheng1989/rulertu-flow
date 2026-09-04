#!/usr/bin/env python3
"""Strip comments and blank lines from source text for copyright submission.

新口径：申报源代码不得包含注释、不得有空行。剥离发生在构建层，仓库源码不动。
Python 走 tokenize + ast 精确路径；其余语言走引号感知状态机（启发式，局限见
references/source-code.md）。字符串字面量内的注释符绝不误删。
"""

from __future__ import annotations

import ast
import io
import tokenize

# 各语言剥离配置：行注释起点、块注释 (起, 止)、需跟踪的字符串引号
STRIP_RULES: dict[str, dict] = {
    "c-family": {"line": ["//"], "block": [("/*", "*/")], "quotes": "\"'`"},
    "hash": {"line": ["#"], "block": [], "quotes": "\"'"},
    "sql": {"line": ["--"], "block": [("/*", "*/")], "quotes": "'"},
    "html": {"line": [], "block": [("<!--", "-->")], "quotes": ""},
    "css": {"line": [], "block": [("/*", "*/")], "quotes": "\"'"},
}
SUFFIX_RULES = {
    ".js": "c-family", ".jsx": "c-family", ".ts": "c-family", ".tsx": "c-family",
    ".vue": "c-family", ".java": "c-family", ".c": "c-family", ".cc": "c-family",
    ".cpp": "c-family", ".cs": "c-family", ".go": "c-family", ".rs": "c-family",
    ".h": "c-family", ".hpp": "c-family",
    ".kt": "c-family", ".kts": "c-family", ".php": "c-family", ".scala": "c-family",
    ".swift": "c-family",
    ".sh": "hash", ".rb": "hash",
    ".sql": "sql",
    ".html": "html", ".css": "css",
}


class StripError(Exception):
    """源码不可解析或扩展名不受支持，剥离失败（转人工，不伪造通过）。"""


StripStats = dict[str, int]


def strip_lines(text: str, suffix: str) -> tuple[list[str], StripStats]:
    """按扩展名剥离注释与空行，返回 (保留行, 统计)。行内代码原文逐字保留。"""
    stats = {
        "original_lines": len(text.splitlines()),
        "retained_lines": 0,
        "removed_comment_lines": 0,
        "removed_blank_lines": 0,
        "trimmed_trailing_comments": 0,
    }
    if suffix.lower() == ".py":
        kept = _strip_python(text, stats)
    else:
        rule_name = SUFFIX_RULES.get(suffix.lower())
        if rule_name is None:
            raise StripError(f"unsupported source extension: {suffix!r}")
        kept = _strip_generic(text, STRIP_RULES[rule_name], stats)
    stats["retained_lines"] = len(kept)
    return kept, stats


# ---------------------------------------------------------------------------
# Python 精确路径：tokenize 定位注释，ast 区分 docstring 与多行字符串
# ---------------------------------------------------------------------------

def _strip_python(text: str, stats: StripStats) -> list[str]:
    full_line_rows, trailing_cols = _py_comment_facts(text)
    doc_rows, string_rows = _py_string_rows(text)
    kept: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if number in doc_rows or number in full_line_rows:
            stats["removed_comment_lines"] += 1
        elif number in trailing_cols:
            kept.append(line[:trailing_cols[number]])
            stats["trimmed_trailing_comments"] += 1
        elif number in string_rows:
            kept.append(line)  # 多行字符串内部（非 docstring）逐字保留
        elif not line.strip():
            stats["removed_blank_lines"] += 1
        else:
            kept.append(line)
    return kept


def _py_comment_facts(text: str) -> tuple[set[int], dict[int, int]]:
    """tokenize 定位 COMMENT：整行注释行号集合、行尾注释 (行号, 截断列)。"""
    full_line: set[int] = set()
    trailing: dict[int, int] = {}
    try:
        tokens = tokenize.generate_tokens(io.StringIO(text).readline)
        for tok in tokens:
            if tok.type != tokenize.COMMENT:
                continue
            row, col = tok.start
            if tok.line[:col].strip():
                trailing[row] = col
            else:
                full_line.add(row)
    except (tokenize.TokenError, IndentationError, SyntaxError) as exc:
        raise StripError(f"python source not tokenizable: {exc}") from exc
    return full_line, trailing


def _py_string_rows(text: str) -> tuple[set[int], set[int]]:
    """ast 区分语句级独立字符串（docstring 类，删除）与多行字符串（内部保留）。"""
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        raise StripError(f"python source not parseable: {exc}") from exc
    doc_rows: set[int] = set()
    string_rows: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            end = node.end_lineno or node.lineno  # end_lineno 3.8+ 恒有值
            string_rows |= set(range(node.lineno, end + 1))
        # 表达式语句位置的字符串 = docstring 类，整段删除
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            end = node.value.end_lineno or node.value.lineno
            doc_rows |= set(range(node.value.lineno, end + 1))
    return doc_rows, string_rows


# ---------------------------------------------------------------------------
# 非 Python 启发式路径：引号感知状态机（正则字面量、模板插值等属已知局限）
# ---------------------------------------------------------------------------

def _strip_generic(text: str, rule: dict, stats: StripStats) -> list[str]:
    line_markers: list[str] = rule["line"]
    block_markers: list[tuple[str, str]] = rule["block"]
    quotes = rule["quotes"]
    kept: list[str] = []
    state = {"buffer": "", "quote": "", "block_end": "", "escape": False,
             "is_comment": False, "trimmed": False}

    def flush() -> None:
        if state["buffer"].strip():
            if state["trimmed"]:
                stats["trimmed_trailing_comments"] += 1
            kept.append(state["buffer"].rstrip("\n"))
        elif state["is_comment"]:
            stats["removed_comment_lines"] += 1
        else:
            stats["removed_blank_lines"] += 1
        state["buffer"] = ""
        state["is_comment"] = False
        state["trimmed"] = False

    i = 0
    length = len(text)
    while i < length:
        char = text[i]
        pair = text[i:i + 2]
        if state["quote"]:
            state["buffer"] += char
            if state["escape"]:
                state["escape"] = False
            elif char == "\\":
                state["escape"] = True
            elif char == state["quote"]:
                state["quote"] = ""
            elif char == "\n":
                flush()  # 多行字符串内的换行：该行原样保留
        elif state["block_end"]:
            end = state["block_end"]
            if text[i:i + len(end)] == end:
                state["block_end"] = ""
                i += len(end)
                if not state["buffer"].strip():
                    state["trimmed"] = True  # 注释在前、代码在后的行按截断计
                j = i
                while j < length and text[j] != "\n" and not text[j].strip():
                    j += 1
                if j < length and text[j] == "\n":
                    state["is_comment"] = True  # 结束后当行仅剩空白，按注释行计
                    i = j
                continue
            if char == "\n":
                flush()  # 块注释行；结束当行若有代码则按代码行保留
            # 块注释内部字符不输出
        else:
            block = _match_block(block_markers, text, i)
            marker = _match_marker(line_markers, pair, char)
            if block:
                if state["buffer"].strip():
                    state["trimmed"] = True  # 行内开始块注释：该行按截断计
                else:
                    state["is_comment"] = True
                state["block_end"] = block[1]
                i += len(block[0])
                continue
            if marker:
                if state["buffer"].strip():
                    state["trimmed"] = True
                else:
                    state["is_comment"] = True
                while i < length and text[i] != "\n":  # 跳过注释文本
                    i += 1
                continue
            if char == "\n":
                flush()
            else:
                if char in quotes:
                    state["quote"] = char
                state["buffer"] += char
        i += 1

    if state["buffer"] or state["is_comment"] or state["trimmed"]:
        flush()  # 末行无换行符
    return kept


def _match_marker(markers: list[str], pair: str, char: str) -> str | None:
    for marker in markers:
        if pair == marker or (len(marker) == 1 and char == marker):
            return marker
    return None


def _match_block(
    blocks: list[tuple[str, str]], text: str, i: int
) -> tuple[str, str] | None:
    for start, end in blocks:
        if text[i:i + len(start)] == start:
            return start, end
    return None
