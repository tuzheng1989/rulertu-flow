"""scan_source.py 行为基线（B3）。

锚点（scan_source.py）：
- :28-30  PLACEHOLDER_PATTERN（TODO/待实现/待补充等）
- :31-35  LICENSE_PATTERN
- :36     STUB_PATTERN（pass / ... 行）
- :45-46  MOJIBAKE_SNIPPETS
- :37-44  入口候选：文件名在 ENTRY_FILE_NAMES 或正文命中 ENTRY_CODE_PATTERN
- :90-117 scan_file 各 findings 行号与 finding_counts
"""

from __future__ import annotations

import json


SAMPLE = "\n".join([
    "# TODO implement retry",          # 1 占位符
    "value = \"text 待补充 inside\"",   # 2 占位符（中文占位词）
    "",                                 # 3 空行
    "    pass",                         # 4 桩行
    "# Copyright (C) 2026 Example",     # 5 license 标记
    "data = \"锟斤拷\"",                 # 6 乱码
])


def test_scan_file_reports_each_finding_with_line_number(load_module, scripts, tmp_path):
    """占位符 / license 头 / 桩行 / 乱码各自命中，行号为独立真值（锚点 :99-107）。"""
    module = load_module("scan_source", scripts.scan_source.parent)
    path = tmp_path / "sample.py"
    path.write_text(SAMPLE, encoding="utf-8")

    result = module.scan_file(path, "sample.py")
    assert result["findings"] == {
        "placeholder": [1, 2],
        "license_marker": [5],
        "stub_line": [4],
        "mojibake": [6],
    }
    assert result["finding_counts"] == {
        "placeholder": 2,
        "license_marker": 1,
        "stub_line": 1,
        "mojibake": 1,
    }
    assert result["physical_lines"] == 6
    # sample.py 不是入口文件名，正文也没有入口守卫
    assert result["entry_candidate"] is False


def test_todo_inside_string_is_hit_as_is(load_module, scripts, tmp_path):
    """字符串内的 TODO 也会命中（PLACEHOLDER_PATTERN 全行检索，锚点 :100）。

    现状会误报——按现状锁定；是否区分字符串/注释属行为变更，B 批后续再议。
    """
    module = load_module("scan_source", scripts.scan_source.parent)
    path = tmp_path / "msg.py"
    path.write_text("message = \"TODO: polish wording\"\n", encoding="utf-8")

    result = module.scan_file(path, "msg.py")
    assert result["findings"]["placeholder"] == [1]


def test_entry_candidate_by_filename_and_by_guard(load_module, scripts, tmp_path):
    """入口候选：main.py 文件名即命中；其他文件需正文含入口守卫（锚点 :37-44, :114）。"""
    module = load_module("scan_source", scripts.scan_source.parent)

    main_py = tmp_path / "main.py"
    main_py.write_text("start()\n", encoding="utf-8")
    assert module.scan_file(main_py, "main.py")["entry_candidate"] is True

    guard_py = tmp_path / "worker.py"
    guard_py.write_text("if __name__ == \"__main__\":\n    run()\n", encoding="utf-8")
    assert module.scan_file(guard_py, "worker.py")["entry_candidate"] is True

    plain_py = tmp_path / "util.py"
    plain_py.write_text("value = 1\n", encoding="utf-8")
    assert module.scan_file(plain_py, "util.py")["entry_candidate"] is False


def test_gb18030_file_flagged_as_mojibake(load_module, scripts, tmp_path):
    """GB18030 源码按 utf-8 errors=replace 读取，产生 U+FFFD → 乱码命中（锚点 :45, :91）。"""
    module = load_module("scan_source", scripts.scan_source.parent)
    path = tmp_path / "legacy.py"
    path.write_bytes("# 中文注释\nvalue = 1\n".encode("gb18030"))

    result = module.scan_file(path, "legacy.py")
    assert result["findings"]["mojibake"] == [1]


def test_cli_summary_and_excluded_files(write_tree, run_cli, scripts, tmp_path):
    """CLI：入口候选汇总、excluded 记录与 finding_totals（锚点 :175-183）。"""
    repo = write_tree({
        "main.py": "if __name__ == \"__main__\":\n    start()\n",
        "app.py": "# TODO wire up\nvalue = 1\n",
        "node_modules/x.js": "var a = 1;\n",
        "docs/x.md": "# 文档\n",
    })
    output = tmp_path / "scan.json"
    result = run_cli(scripts.scan_source, "--repo", repo, "--output", output)
    assert result.returncode == 0, result.stderr

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["summary"]["scanned_file_count"] == 2
    # main.py 与 app.py 都在 ENTRY_FILE_NAMES（:41-44），按 casefold 序输出
    assert payload["summary"]["entry_candidates"] == ["app.py", "main.py"]
    # app.py 一处 TODO → 占位符总数 1（独立真值）
    assert payload["summary"]["finding_totals"] == {"placeholder": 1}
    excluded = {item["path"]: item["reason"] for item in payload["excluded_files"]}
    assert excluded["node_modules/x.js"] == "excluded by node_modules/**"
    assert excluded["docs/x.md"] == "not an application source extension"
