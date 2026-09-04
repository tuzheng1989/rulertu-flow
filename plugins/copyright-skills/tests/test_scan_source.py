"""scan_source.py 行为基线（B3）。

锚点（scan_source.py）：
- :28-30  PLACEHOLDER_PATTERN（TODO/待实现/待补充等）
- :31-35  LICENSE_PATTERN
- :36     STUB_PATTERN（pass / ... 行）
- :45-46  MOJIBAKE_SNIPPETS
- :47-58  AI 特征注释四规则：MD_BOLD / SECTION_REF / PATH_REF / HALFWIDTH_PAREN_NOTE
- :37-44  入口候选：文件名在 ENTRY_FILE_NAMES 或正文命中 ENTRY_CODE_PATTERN
- :102-129 scan_file 各 findings 行号与 finding_counts
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


def test_ai_style_comment_rules_hit_with_line_number(load_module, scripts, tmp_path):
    """AI 特征注释四规则各自命中并记录行号（锚点 :47-58, :113-120）。

    - md_markup：注释里的 **加粗**
    - section_ref：§ 精确文档引用（plan §2-W1.2）
    - path_ref：带斜杠的相对路径引用（data/prototype_kg/kg.json）
    - halfwidth_paren_note：中文内容的半角括号元组式注
    """
    module = load_module("scan_source", scripts.scan_source.parent)
    sample = "\n".join([
        "# 按**实际付费调用**累计",                      # 1 md 加粗
        "# 配置见 `data/prototype_kg/kg.json`",          # 2 行内代码反引号
        '"""W3.4 告警等级合成(plan §2-W3.4)。"""',        # 3 § 引用
        "# 配置见 data/prototype_kg/kg.json",            # 4 路径引用
        "# provenance 单向投影(只写不读,P5-Q1)",          # 5 半角括号元组式注
    ])
    path = tmp_path / "sample.py"
    path.write_text(sample, encoding="utf-8")

    result = module.scan_file(path, "sample.py")
    assert result["findings"]["md_markup"] == [1]
    assert result["findings"]["inline_code"] == [2]
    assert result["findings"]["section_ref"] == [3]
    assert result["findings"]["path_ref"] == [2, 4]  # 行 2 反引号里也是路径，双规则命中
    assert result["findings"]["halfwidth_paren_note"] == [5]
    assert result["finding_counts"]["md_markup"] == 1
    assert result["finding_counts"]["inline_code"] == 1
    assert result["finding_counts"]["halfwidth_paren_note"] == 1


def test_ai_style_comment_rules_do_not_hit_normal_writing(load_module, scripts, tmp_path):
    """人类常规写法不命中：全角括号注、纯文件名、幂运算、含引号的代码元组、URL。"""
    module = load_module("scan_source", scripts.scan_source.parent)
    sample = "\n".join([
        "# 单点可配置阈值（百分数口径，演示用）",            # 1 全角括号 + 全角逗号
        "# 配置见 kg.json",                              # 2 纯文件名，无斜杠路径
        "area = width ** 2",                             # 3 幂运算
        'label = ("人类门", "机器门")',                    # 4 含引号的代码元组
        "# 文档见 https://example.com/guide.md",          # 5 URL 不按路径引用计
        "# 时间线分析工具（仅展示与复盘）",                  # 6 全角括号注
    ])
    path = tmp_path / "sample.py"
    path.write_text(sample, encoding="utf-8")

    result = module.scan_file(path, "sample.py")
    for key in ("md_markup", "inline_code", "section_ref", "path_ref", "halfwidth_paren_note"):
        assert key not in result["findings"], (key, result["findings"])


def test_inline_code_rule_only_flags_comment_lines(load_module, scripts, tmp_path):
    """行内代码规则只查 # 注释行；shell 代码行的反引号是命令替换语法，不命中。"""
    module = load_module("scan_source", scripts.scan_source.parent)

    sh = tmp_path / "run.sh"
    sh.write_text("#!/bin/bash\nVALUE=`cat config.txt`\necho $VALUE\n", encoding="utf-8")
    result = module.scan_file(sh, "run.sh")
    assert "inline_code" not in result["findings"]

    py = tmp_path / "note.py"
    py.write_text("# 用法见 `python main.py --help`\n", encoding="utf-8")
    assert module.scan_file(py, "note.py")["findings"]["inline_code"] == [1]


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


def test_audit_round2_rules_hit_with_line_number(load_module, scripts, tmp_path):
    """审核反馈五规则：横幅、列表、强调词、需求编号、工具名各自命中（独立真值）。"""
    module = load_module("scan_source", scripts.scan_source.parent)
    sample = "\n".join([
        "# ============================",          # 1 横幅
        "# - 列表项（注释行列表）",                  # 2 注释行 md 列表
        '"""',                                     # 3 docstring 开
        "- 如实返回，不可绕过",                      # 4 docstring 列表 + 强调词
        "符合唯一出口约束（W4.1）",                   # 5 强调词 + 需求编号
        '"""',                                     # 6 docstring 闭
        'note = "严禁超时（R23）"',                  # 7 强调词 + 编号（运行时字符串，审核口径同样须清）
        "# Codex 生成的模块",                        # 8 工具名
    ])
    path = tmp_path / "sample.py"
    path.write_text(sample, encoding="utf-8")
    result = module.scan_file(path, "sample.py")
    assert result["findings"]["banner_divider"] == [1]
    assert result["findings"]["md_list"] == [2, 4]
    # 强调词只查注释/docstring；运行时文案中的"严禁超时"是人类正常表达，不报
    assert result["findings"]["emph_phrase"] == [4, 5]
    assert result["findings"]["req_id"] == [5, 7]
    assert result["findings"]["ai_tool_marker"] == [8]


def test_audit_round2_rules_negative_cases(load_module, scripts, tmp_path):
    """人类常规写法与易混代码不命中：T-2h、V1.0、乘法、普通中文句。"""
    module = load_module("scan_source", scripts.scan_source.parent)
    sample = "\n".join([
        "start = t0 + T-2h_offset",                # 1 T-2h 不算需求编号
        "version = \"V1.0\"",                       # 2 版本号不算编号
        "area = width ** 2",                        # 3 幂运算
        "# 按时间点读取快照并计算均值",                # 4 普通注释
        "# 五幕时间线与告警等级联动的说明文字",        # 5 普通注释
    ])
    path = tmp_path / "sample.py"
    path.write_text(sample, encoding="utf-8")
    result = module.scan_file(path, "sample.py")
    for key in ("banner_divider", "md_list", "emph_phrase", "req_id", "ai_tool_marker"):
        assert key not in result["findings"], (key, result["findings"])
