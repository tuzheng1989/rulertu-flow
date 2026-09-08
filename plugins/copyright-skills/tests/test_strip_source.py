"""strip_source.py 行为基线（申报源代码剥离：注释与空行构建时全删）。

锚点（strip_source.py）：
- strip_lines(text, suffix) -> (保留行, 统计)  唯一入口
- Python 走 tokenize + ast 精确路径；其余语言走引号感知状态机
- 统计键：original_lines / retained_lines / removed_comment_lines /
  removed_blank_lines / trimmed_trailing_comments
- Python 语法不可解析时抛 StripError，不伪造通过
"""

from __future__ import annotations

import pytest


@pytest.fixture()
def strip_lines(load_module, scripts):
    """加载 strip_source 模块并返回其 strip_lines 函数。"""
    module = load_module("strip_source", scripts.strip_source.parent)
    return module.strip_lines


def stats_of(strip_lines, text: str, suffix: str) -> dict:
    _, stats = strip_lines(text, suffix)
    return stats


# ---------------------------------------------------------------------------
# Python 精确路径（tokenize + ast）
# ---------------------------------------------------------------------------

def test_py_full_line_comment_and_shebang_removed(strip_lines):
    """整行 # 注释与 shebang 整行删除（shebang 属 # 注释，用户口径全删）。"""
    text = "\n".join([
        "#!/usr/bin/env python3",          # shebang → 删
        "# 模块说明",                       # 整行注释 → 删
        "value = 1",                       # 保留
    ]) + "\n"
    kept, stats = strip_lines(text, ".py")
    assert kept == ["value = 1"]
    assert stats["original_lines"] == 3
    assert stats["retained_lines"] == 1
    assert stats["removed_comment_lines"] == 2
    assert stats["removed_blank_lines"] == 0
    assert stats["trimmed_trailing_comments"] == 0


def test_py_trailing_comment_trimmed_code_kept_verbatim(strip_lines):
    """行尾注释截去，代码部分逐字保留（含原有空白，不重排）。"""
    text = "value = 1  # 说明文字\nrun(value)   #type: ignore  # 再注\n"
    kept, stats = strip_lines(text, ".py")
    assert kept == ["value = 1  ", "run(value)   "]
    assert stats["trimmed_trailing_comments"] == 2
    assert stats["removed_comment_lines"] == 0


def test_py_blank_and_whitespace_lines_removed(strip_lines):
    """空行与纯 whitespace 行全删。"""
    text = "a = 1\n\n   \n\t\nb = 2\n"
    kept, stats = strip_lines(text, ".py")
    assert kept == ["a = 1", "b = 2"]
    assert stats["removed_blank_lines"] == 3


def test_py_docstring_statements_removed(strip_lines):
    """语句级独立字符串（模块/类/函数 docstring）整段删除。"""
    text = "\n".join([
        '"""模块说明。',
        "跨两行。\"\"\"",
        "",
        "def run():",
        '    """函数说明"""',
        "    return 1",
    ]) + "\n"
    kept, stats = strip_lines(text, ".py")
    assert kept == ["def run():", "    return 1"]
    assert stats["removed_comment_lines"] == 3  # docstring 两行 + 函数 docstring 一行
    assert stats["removed_blank_lines"] == 1


def test_py_multiline_string_assignment_kept(strip_lines):
    """非语句级多行字符串（赋值右侧）逐字保留，字符串内的 # 与空行不动。"""
    text = "\n".join([
        "text = \"\"\"第一行",
        "# 看似注释",
        "",
        "尾行\"\"\"",
        "value = 1",
    ]) + "\n"
    kept, stats = strip_lines(text, ".py")
    assert kept == [
        "text = \"\"\"第一行",
        "# 看似注释",
        "",
        "尾行\"\"\"",
        "value = 1",
    ]
    assert stats["retained_lines"] == 5
    assert stats["removed_comment_lines"] == 0
    assert stats["removed_blank_lines"] == 0


def test_py_hash_inside_string_literal_kept(strip_lines):
    """字符串字面量内的 # 与 URL 双斜杠绝不误删。"""
    text = 'url = "https://example.com/a#anchor"\nlabel = "标号#1"\n'
    kept, stats = strip_lines(text, ".py")
    assert kept == [text[:-1].split("\n")[0], 'label = "标号#1"']
    assert stats["trimmed_trailing_comments"] == 0


def test_py_syntax_error_raises_strip_error(strip_lines, load_module, scripts):
    """语法不可解析：抛 StripError 转人工，不静默通过。"""
    module = load_module("strip_source", scripts.strip_source.parent)
    with pytest.raises(module.StripError):
        strip_lines("def broken(:\n", ".py")


def test_py_stats_independent_truth(strip_lines):
    """统计各键为独立真值：4 行文件 1 注释 1 空行 1 行尾注 1 代码。"""
    text = "# 头注\n\ncode = 1  # 尾注\nrun()\n"
    kept, stats = strip_lines(text, ".py")
    assert kept == ["code = 1  ", "run()"]
    assert stats == {
        "original_lines": 4,
        "retained_lines": 2,
        "removed_comment_lines": 1,
        "removed_blank_lines": 1,
        "trimmed_trailing_comments": 1,
    }


# ---------------------------------------------------------------------------
# 非 Python 启发式路径（引号感知状态机）
# ---------------------------------------------------------------------------

def test_js_line_block_and_string_comments(strip_lines):
    """js：// 整行删、/* */ 块删、行尾 // 截、字符串内 // 保留。"""
    text = "\n".join([
        "// 头注",
        "const url = \"https://example.com\";  // 行尾注",
        "/* 块注释",
        "   跨行 */",
        "run(1);",
    ]) + "\n"
    kept, stats = strip_lines(text, ".js")
    assert kept == ["const url = \"https://example.com\";  ", "run(1);"]
    assert stats["removed_comment_lines"] == 3  # 头注 + 块两行
    assert stats["trimmed_trailing_comments"] == 1
    assert stats["retained_lines"] == 2


def test_js_hash_in_double_quoted_string_kept(strip_lines):
    """js：双引号字符串内的 # 不当作注释。"""
    text = 'const label = "a#b";\nrun(1);\n'
    kept, _ = strip_lines(text, ".js")
    assert kept == ['const label = "a#b";', "run(1);"]


def test_sh_hash_comments_with_single_quotes(strip_lines):
    """sh：# 整行删、行尾 # 截、单引号字符串内 # 保留。"""
    text = "\n".join([
        "#!/bin/bash",
        'NAME="编号#1"',
        "echo $NAME  # 说明",
    ]) + "\n"
    kept, stats = strip_lines(text, ".sh")
    assert kept == ['NAME="编号#1"', "echo $NAME  "]
    assert stats["removed_comment_lines"] == 1
    assert stats["trimmed_trailing_comments"] == 1


def test_html_comment_removed(strip_lines):
    """html：<!-- --> 整块删，普通标签保留。"""
    text = "\n".join([
        "<html>",
        "<!-- 说明",
        "跨行 -->",
        "<body>ok</body>",
        "</html>",
    ]) + "\n"
    kept, stats = strip_lines(text, ".html")
    assert kept == ["<html>", "<body>ok</body>", "</html>"]
    assert stats["removed_comment_lines"] == 2


def test_css_block_comment_removed(strip_lines):
    """css：/* */ 删，规则保留。"""
    text = "/* 说明 */\nbody {\n  color: red;\n}\n"
    kept, stats = strip_lines(text, ".css")
    assert kept == ["body {", "  color: red;", "}"]
    assert stats["removed_comment_lines"] == 1


def test_sql_dash_and_block_comments(strip_lines):
    """sql：-- 整行删、行尾 -- 截、字符串内 -- 保留。"""
    text = "\n".join([
        "-- 头注",
        "SELECT 'a--b' AS x  -- 说明",
        "FROM t;",
    ]) + "\n"
    kept, stats = strip_lines(text, ".sql")
    assert kept == ["SELECT 'a--b' AS x  ", "FROM t;"]
    assert stats["removed_comment_lines"] == 1
    assert stats["trimmed_trailing_comments"] == 1


def test_no_comment_no_blank_passthrough(strip_lines):
    """无注释无空行的代码原样透传，统计归零。"""
    text = "a = 1\nb = 2\n"
    kept, stats = strip_lines(text, ".py")
    assert kept == ["a = 1", "b = 2"]
    assert stats == {
        "original_lines": 2,
        "retained_lines": 2,
        "removed_comment_lines": 0,
        "removed_blank_lines": 0,
        "trimmed_trailing_comments": 0,
    }


# ---------------------------------------------------------------------------
# 代码行定位（code_line_rows）：物理行号映射
# ---------------------------------------------------------------------------

@pytest.fixture()
def code_line_rows(load_module, scripts):
    """加载 strip_source 模块并返回其 code_line_rows 函数。"""
    module = load_module("strip_source", scripts.strip_source.parent)
    return module.code_line_rows


def test_py_code_line_rows_map_to_physical_lines(code_line_rows):
    """Python：代码行返回 1 起物理行号，注释/空行/docstring 不占代码行。"""
    text = "#!/usr/bin/env python3\n# 说明\nvalue = 1\n\nrun(value)  # 尾注\n"
    rows, stats = code_line_rows(text, ".py")
    assert rows == [3, 5]
    assert stats["retained_lines"] == 2


def test_js_code_line_rows_map_to_physical_lines(code_line_rows):
    """js：整行注/块注行不占代码行，行尾注所在行算代码行。"""
    text = "// 头\nconst a = 1;  // 注\n\n/* 块\n注 */\nrun();\n"
    py_rows, stats = code_line_rows(text, ".js")
    assert py_rows == [2, 6]
    assert stats["retained_lines"] == 2
