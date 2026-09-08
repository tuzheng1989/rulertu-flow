"""build_source_docx.py 行为基线。

锚点（build_source_docx.py）：
- --lines-per-page 必须 >= 1；输出已存在拒绝覆盖；sha256 漂移拒构建
- <=3,000 代码行全选；>3,000 代码行取覆盖前 1,500 代码行的物理行段 +
  覆盖后 1,500 代码行的物理行段，段内注释与空行随物理行保留
- manifest 双轨（total_physical_lines / total_code_lines）与边界条目、
  selected_sha256
"""

from __future__ import annotations

import hashlib
import json

REPO_LAYOUT = {
    "main.py": "if __name__ == \"__main__\":\n    start()\n",
    "app.py": "value = 1\nvalue = 2\n",
}


def build_inventory(run_cli, scripts, repo, output):
    result = run_cli(scripts.inventory_repo, "--repo", repo, "--output", output)
    assert result.returncode == 0, result.stderr
    return output


def read_manifest(docx_path):
    manifest_path = docx_path.with_suffix(docx_path.suffix + ".manifest.json")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def test_at_most_3000_lines_selects_all(write_tree, run_cli, scripts, tmp_path, make_lines):
    """>=1 且 <=3000 行：全选，selected_line_count 等于手写总行数（锚点 :85, :144）。"""
    repo = write_tree({"app.py": make_lines(10), "main.py": make_lines(3, prefix="entry")})
    inventory = build_inventory(run_cli, scripts, repo, tmp_path / "inventory.json")
    output = tmp_path / "src.docx"

    result = run_cli(
        scripts.build_source_docx,
        "--inventory", inventory, "--output", output,
        "--title", "演示系统", "--version", "V1.0",
        "--lines-per-page", "500",
    )
    assert result.returncode == 0, result.stderr
    assert output.is_file()

    manifest = read_manifest(output)
    # 独立真值：写入的 10 + 3 = 13 行（无注释空行，物理行=代码行）
    assert manifest["total_physical_lines"] == 13
    assert manifest["total_code_lines"] == 13
    assert manifest["selected_physical_line_count"] == 13
    assert manifest["selected_code_line_count"] == 13
    assert manifest["selection"] == "all"
    assert manifest["tail_start"] is None
    # 清单序（casefold）在前：app.py 排在 main.py 之前
    assert manifest["first"]["path"] == "app.py"
    assert manifest["first"]["line"] == 1
    assert manifest["last"]["path"] == "main.py"


def test_over_3000_lines_takes_head_and_tail(write_tree, run_cli, scripts, tmp_path, make_lines):
    """3001 行单文件：前 1500 + 后 1500，第 1501 行被跳过，两段不重叠（锚点 :85, :145-148）。"""
    repo = write_tree({"big.py": make_lines(3001)})
    inventory = build_inventory(run_cli, scripts, repo, tmp_path / "inventory.json")
    output = tmp_path / "src.docx"

    result = run_cli(
        scripts.build_source_docx,
        "--inventory", inventory, "--output", output,
        "--title", "演示系统", "--version", "V1.0",
        "--lines-per-page", "3000",
    )
    assert result.returncode == 0, result.stderr

    manifest = read_manifest(output)
    # 独立真值：3001 行全为代码行，head 段物理 1..1500，tail 段物理 1502..3001
    assert manifest["total_physical_lines"] == 3001
    assert manifest["total_code_lines"] == 3001
    assert manifest["selected_physical_line_count"] == 3000
    assert manifest["selected_code_line_count"] == 3000
    assert manifest["selection"] == "first-1500-code-lines-and-last-1500"
    assert manifest["first"] == {"path": "big.py", "line": 1, "text": "line_0001"}
    assert manifest["head_end"]["line"] == 1500
    assert manifest["tail_start"]["line"] == 1502
    assert manifest["last"] == {"path": "big.py", "line": 3001, "text": "line_3001"}
    # 不重叠
    assert manifest["head_end"]["line"] < manifest["tail_start"]["line"]


def test_source_changed_after_inventory_rejected(
    write_tree, run_cli, scripts, tmp_path, make_lines
):
    """入选文件 sha256 与清单不符：拒构建并提示（锚点 :74-75）。"""
    repo = write_tree({"app.py": make_lines(5)})
    inventory = build_inventory(run_cli, scripts, repo, tmp_path / "inventory.json")
    # 清单生成后篡改源码
    (repo / "app.py").write_text(make_lines(6), encoding="utf-8")

    result = run_cli(
        scripts.build_source_docx,
        "--inventory", inventory, "--output", tmp_path / "src.docx",
        "--title", "演示系统", "--version", "V1.0",
    )
    assert result.returncode != 0
    assert "source changed after inventory" in result.stderr
    assert "app.py" in result.stderr


def test_lines_per_page_zero_rejected(write_tree, run_cli, scripts, tmp_path, make_lines):
    """--lines-per-page 0：拒绝（锚点 :61-62）。"""
    repo = write_tree({"app.py": make_lines(5)})
    inventory = build_inventory(run_cli, scripts, repo, tmp_path / "inventory.json")

    result = run_cli(
        scripts.build_source_docx,
        "--inventory", inventory, "--output", tmp_path / "src.docx",
        "--title", "演示系统", "--version", "V1.0",
        "--lines-per-page", "0",
    )
    assert result.returncode != 0
    assert "--lines-per-page must be positive" in result.stderr


def test_existing_output_refused(write_tree, run_cli, scripts, tmp_path, make_lines):
    """输出文件已存在：拒绝覆盖（锚点 :63-65，全局红线 1）。"""
    repo = write_tree({"app.py": make_lines(5)})
    inventory = build_inventory(run_cli, scripts, repo, tmp_path / "inventory.json")
    output = tmp_path / "src.docx"
    output.write_bytes(b"existing")

    result = run_cli(
        scripts.build_source_docx,
        "--inventory", inventory, "--output", output,
        "--title", "演示系统", "--version", "V1.0",
    )
    assert result.returncode != 0
    assert "refusing to overwrite output" in result.stderr
    # 原文件未被触碰
    assert output.read_bytes() == b"existing"


def test_selected_sha256_stable_across_runs(write_tree, run_cli, scripts, tmp_path, make_lines):
    """同一输入两次构建：manifest 的 selected_sha256 一致（锚点 :149-151）。"""
    repo = write_tree({"app.py": make_lines(20), "main.py": make_lines(4, prefix="entry")})
    inventory = build_inventory(run_cli, scripts, repo, tmp_path / "inventory.json")

    common = ["--inventory", inventory, "--title", "演示系统", "--version", "V1.0"]
    first = run_cli(scripts.build_source_docx, *common, "--output", tmp_path / "a.docx")
    second = run_cli(scripts.build_source_docx, *common, "--output", tmp_path / "b.docx")
    assert first.returncode == 0 and second.returncode == 0, first.stderr + second.stderr

    sha_a = read_manifest(tmp_path / "a.docx")["selected_sha256"]
    sha_b = read_manifest(tmp_path / "b.docx")["selected_sha256"]
    assert sha_a == sha_b
    assert len(sha_a) == 64


# ---------------------------------------------------------------------------
# B5：--first 入口前置（切片 1 / 切片 2）
# ---------------------------------------------------------------------------

# 独立真值：手写三文件布局与其逐行记录。清单序（casefold）为 app.py, main.py, zed.py，
# 总 5 行；app.py 在字母序最前，main.py 是"入口不在前"的样本。
FIRST_LAYOUT = {
    "main.py": "a\nb\n",
    "app.py": "x\ny\n",
    "zed.py": "z\n",
}

FIRST_FILE_RECORDS = {
    "app.py": [
        {"path": "app.py", "line": 1, "text": "x"},
        {"path": "app.py", "line": 2, "text": "y"},
    ],
    "main.py": [
        {"path": "main.py", "line": 1, "text": "a"},
        {"path": "main.py", "line": 2, "text": "b"},
    ],
    "zed.py": [{"path": "zed.py", "line": 1, "text": "z"}],
}


def expected_sha256(paths: list[str]) -> str:
    """按给定文件顺序串接记录，重算 manifest 的 selected_sha256（B3 既有口径）。"""
    records = [record for path in paths for record in FIRST_FILE_RECORDS[path]]
    return hashlib.sha256(
        json.dumps(records, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_first_layout(run_cli, scripts, write_tree, tmp_path):
    repo = write_tree(FIRST_LAYOUT)
    inventory = build_inventory(run_cli, scripts, repo, tmp_path / "inventory.json")
    return repo, inventory


def test_first_flag_moves_entry_to_front(write_tree, run_cli, scripts, tmp_path, make_lines):
    """--first 单文件：入口移到串接序列最前，其余文件保持清单相对顺序（锚点 :54-60 附近新增）。"""
    _, inventory = build_first_layout(run_cli, scripts, write_tree, tmp_path)
    output = tmp_path / "src.docx"

    result = run_cli(
        scripts.build_source_docx,
        "--inventory", inventory, "--output", output,
        "--title", "演示系统", "--version", "V1.0",
        "--lines-per-page", "500",
        "--first", "main.py",
    )
    assert result.returncode == 0, result.stderr

    manifest = read_manifest(output)
    assert manifest["first"]["path"] == "main.py"
    assert manifest["first"]["line"] == 1
    # 其余文件保持清单相对顺序：app.py 在 zed.py 前，串接顺序 main → app → zed
    assert manifest["last"]["path"] == "zed.py"
    assert manifest["selected_physical_line_count"] == 5
    assert manifest["selected_code_line_count"] == 5
    assert manifest["selected_sha256"] == expected_sha256(["main.py", "app.py", "zed.py"])


def test_first_flag_multiple_paths_keep_given_order(
    write_tree, run_cli, scripts, tmp_path, make_lines
):
    """--first 多次传入：按传入顺序排列（非字母序）（代码评审节点：传入顺序语义）。"""
    _, inventory = build_first_layout(run_cli, scripts, write_tree, tmp_path)
    output = tmp_path / "src.docx"

    result = run_cli(
        scripts.build_source_docx,
        "--inventory", inventory, "--output", output,
        "--title", "演示系统", "--version", "V1.0",
        "--lines-per-page", "500",
        "--first", "zed.py", "--first", "app.py",
    )
    assert result.returncode == 0, result.stderr

    manifest = read_manifest(output)
    # 传入顺序 zed → app，其余 main 殿后；不是字母序（字母序会是 app → main → zed）
    assert manifest["first"]["path"] == "zed.py"
    assert manifest["last"]["path"] == "main.py"
    assert manifest["selected_sha256"] == expected_sha256(["zed.py", "app.py", "main.py"])


def test_first_flag_unknown_path_rejected(write_tree, run_cli, scripts, tmp_path, make_lines):
    """--first 未知路径：SystemExit，错误信息列出清单内可选路径（验收标准第 2 条）。"""
    _, inventory = build_first_layout(run_cli, scripts, write_tree, tmp_path)

    result = run_cli(
        scripts.build_source_docx,
        "--inventory", inventory, "--output", tmp_path / "src.docx",
        "--title", "演示系统", "--version", "V1.0",
        "--first", "not-in-list.py",
    )
    assert result.returncode != 0
    assert "not-in-list.py" in result.stderr
    assert "app.py" in result.stderr


def test_first_flag_keeps_line_count_changes_sha256(
    write_tree, run_cli, scripts, tmp_path, make_lines
):
    """--first 前置：selected_line_count 不变；selected_sha256 因顺序改变而改变。

    sha256 按选中记录的 JSON 串接计算，顺序即内容（既定设计取舍）：
    新值与按新顺序的独立重算一致，不与旧值比较。
    """
    _, inventory = build_first_layout(run_cli, scripts, write_tree, tmp_path)

    common = ["--inventory", inventory, "--title", "演示系统", "--version", "V1.0"]
    plain = run_cli(scripts.build_source_docx, *common, "--output", tmp_path / "plain.docx")
    fronted = run_cli(
        scripts.build_source_docx, *common,
        "--output", tmp_path / "fronted.docx", "--first", "main.py",
    )
    assert plain.returncode == 0 and fronted.returncode == 0, plain.stderr + fronted.stderr

    plain_manifest = read_manifest(tmp_path / "plain.docx")
    fronted_manifest = read_manifest(tmp_path / "fronted.docx")
    assert plain_manifest["selected_physical_line_count"] == 5
    assert plain_manifest["selected_code_line_count"] == 5
    assert fronted_manifest["selected_physical_line_count"] == plain_manifest["selected_physical_line_count"]
    assert fronted_manifest["selected_code_line_count"] == plain_manifest["selected_code_line_count"]
    assert fronted_manifest["selected_sha256"] != plain_manifest["selected_sha256"]
    assert fronted_manifest["selected_sha256"] == expected_sha256(["main.py", "app.py", "zed.py"])
    # 无 --first 的构建顺序不受影响：仍是清单序 app → main → zed
    assert plain_manifest["first"]["path"] == "app.py"
    assert plain_manifest["selected_sha256"] == expected_sha256(["app.py", "main.py", "zed.py"])


def test_reordered_first_records_front_order(write_tree, run_cli, scripts, tmp_path, make_lines):
    """manifest 的 reordered_first 按传入顺序记录本次前置的文件（锚点 :138-154 附近新增）。"""
    _, inventory = build_first_layout(run_cli, scripts, write_tree, tmp_path)
    output = tmp_path / "src.docx"

    result = run_cli(
        scripts.build_source_docx,
        "--inventory", inventory, "--output", output,
        "--title", "演示系统", "--version", "V1.0",
        "--first", "zed.py", "--first", "app.py",
    )
    assert result.returncode == 0, result.stderr

    manifest = read_manifest(output)
    assert manifest["reordered_first"] == ["zed.py", "app.py"]
    assert manifest["first"]["path"] == "zed.py"


def test_no_first_flag_leaves_reordered_first_empty(
    write_tree, run_cli, scripts, tmp_path, make_lines
):
    """无 --first：reordered_first 为空列表，锁定缺省语义（必不现：非空）。"""
    _, inventory = build_first_layout(run_cli, scripts, write_tree, tmp_path)
    output = tmp_path / "src.docx"

    result = run_cli(
        scripts.build_source_docx,
        "--inventory", inventory, "--output", output,
        "--title", "演示系统", "--version", "V1.0",
    )
    assert result.returncode == 0, result.stderr

    manifest = read_manifest(output)
    assert manifest["reordered_first"] == []
    assert manifest["first"]["path"] == "app.py"


def test_first_flag_applied_after_selection_over_3000(
    write_tree, run_cli, scripts, tmp_path, make_lines
):
    """>3000 行 + --first 入口：selection 在 reorder 之后执行——前置的入口段
    占据 head 段，其余按清单序补足；selected_line_count 仍为 3000（委派单 B3）。

    独立真值：main.py 3001 行（entry_0001..entry_3001）+ app.py 2000 行，
    清单序 app 在前；--first main.py 后串接为 main → app，共 5001 行，
    selected = 前 1500（main.py:1-1500）+ 后 1500（app.py:501-2000）。
    """
    repo = write_tree({
        "main.py": make_lines(3001, prefix="entry"),
        "app.py": make_lines(2000),
    })
    inventory = build_inventory(run_cli, scripts, repo, tmp_path / "inventory.json")
    output = tmp_path / "src.docx"

    result = run_cli(
        scripts.build_source_docx,
        "--inventory", inventory, "--output", output,
        "--title", "演示系统", "--version", "V1.0",
        "--lines-per-page", "3000",
        "--first", "main.py",
    )
    assert result.returncode == 0, result.stderr

    manifest = read_manifest(output)
    assert manifest["total_physical_lines"] == 5001
    assert manifest["total_code_lines"] == 5001
    assert manifest["selection"] == "first-1500-code-lines-and-last-1500"
    assert manifest["reordered_first"] == ["main.py"]
    assert manifest["selected_physical_line_count"] == 3000
    assert manifest["selected_code_line_count"] == 3000
    assert manifest["first"] == {"path": "main.py", "line": 1, "text": "entry_0001"}
    assert manifest["head_end"] == {"path": "main.py", "line": 1500, "text": "entry_1500"}
    assert manifest["tail_start"] == {"path": "app.py", "line": 501, "text": "line_0501"}
    assert manifest["last"] == {"path": "app.py", "line": 2000, "text": "line_2000"}


# ---------------------------------------------------------------------------
# 代码行口径：物理行全渲染（注释空行保留），行数达标按代码行统计
# ---------------------------------------------------------------------------

# 独立真值：main.py 原 7 行（shebang + 模块 docstring 2 行 + 空行 + def +
# 函数 docstring + 行尾注），代码行 [5, 7] 共 2 行。app.py 原 4 行（注释 +
# 代码 + 空行 + 代码），代码行 [2, 4] 共 2 行。清单序 app 在前。
STRIP_LAYOUT = {
    "main.py": (
        "#!/usr/bin/env python3\n"
        '"""模块说明\n'
        '跨行"""\n'
        "\n"
        "def run():\n"
        '    """函数说明"""\n'
        "    return 1  # 尾注\n"
    ),
    "app.py": "# 注释\nvalue = 1\n\nrun(value)\n",
}


def build_strip_layout(run_cli, scripts, write_tree, tmp_path):
    repo = write_tree(STRIP_LAYOUT)
    inventory = build_inventory(run_cli, scripts, repo, tmp_path / "inventory.json")
    return repo, inventory


def test_physical_lines_rendered_and_code_lines_accounted(
    write_tree, run_cli, scripts, tmp_path
):
    """物理行全渲染（含注释空行），manifest 双轨行数与逐文件统计。"""
    _, inventory = build_strip_layout(run_cli, scripts, write_tree, tmp_path)
    output = tmp_path / "src.docx"

    result = run_cli(
        scripts.build_source_docx,
        "--inventory", inventory, "--output", output,
        "--title", "演示系统", "--version", "V1.0",
        "--lines-per-page", "500",
    )
    assert result.returncode == 0, result.stderr

    manifest = read_manifest(output)
    assert manifest["total_physical_lines"] == 11
    assert manifest["total_code_lines"] == 4
    assert manifest["selected_physical_line_count"] == 11
    assert manifest["selected_code_line_count"] == 4
    assert manifest["selection"] == "all"
    assert manifest["strip_stats"]["app.py"] == {
        "original_lines": 4,
        "retained_lines": 2,
        "removed_comment_lines": 1,
        "removed_blank_lines": 1,
        "trimmed_trailing_comments": 0,
    }
    assert manifest["strip_stats"]["main.py"] == {
        "original_lines": 7,
        "retained_lines": 2,
        "removed_comment_lines": 4,
        "removed_blank_lines": 1,
        "trimmed_trailing_comments": 1,
    }
    # 首末记录为物理首末行：注释与行尾注随行保留
    assert manifest["first"] == {"path": "app.py", "line": 1, "text": "# 注释"}
    assert manifest["last"] == {"path": "main.py", "line": 7, "text": "    return 1  # 尾注"}


def test_docx_renders_all_physical_lines_with_relative_path(
    write_tree, run_cli, scripts, tmp_path
):
    """docx 左列显示 相对路径:原物理行号；注释行与空行原样成行。"""
    repo = write_tree({"sub/app.py": "# 顶注\nvalue = 1  # 注\n\nrun()\n"})
    inventory = build_inventory(run_cli, scripts, repo, tmp_path / "inventory.json")
    output = tmp_path / "src.docx"

    result = run_cli(
        scripts.build_source_docx,
        "--inventory", inventory, "--output", output,
        "--title", "演示系统", "--version", "V1.0",
        "--lines-per-page", "500",
    )
    assert result.returncode == 0, result.stderr

    from docx import Document

    table = Document(str(output)).tables[0]
    cells = [
        (row.cells[0].text, row.cells[1].text)
        for row in table.rows
    ]
    assert cells == [
        ("sub/app.py:1", "# 顶注"),
        ("sub/app.py:2", "value = 1  # 注"),
        ("sub/app.py:3", ""),
        ("sub/app.py:4", "run()"),
    ]


def test_selection_all_when_code_lines_under_3000(
    write_tree, run_cli, scripts, tmp_path
):
    """3,000 行阈值按代码行判定：原始 3200 物理行、代码行 1600 → 全选。"""
    body = "".join(f"line_{i:04d}\n\n" for i in range(1, 1601))
    repo = write_tree({"big.py": body})
    inventory = build_inventory(run_cli, scripts, repo, tmp_path / "inventory.json")
    output = tmp_path / "src.docx"

    result = run_cli(
        scripts.build_source_docx,
        "--inventory", inventory, "--output", output,
        "--title", "演示系统", "--version", "V1.0",
        "--lines-per-page", "1600",
    )
    assert result.returncode == 0, result.stderr

    manifest = read_manifest(output)
    assert manifest["total_physical_lines"] == 3200
    assert manifest["total_code_lines"] == 1600
    assert manifest["selection"] == "all"
    assert manifest["selected_physical_line_count"] == 3200
    assert manifest["selected_code_line_count"] == 1600
    assert manifest["tail_start"] is None


def test_head_tail_segments_bound_at_code_lines_and_keep_comments(
    write_tree, run_cli, scripts, tmp_path
):
    """前后段按代码行定界：边界停在第 1500 / 第 total−1499 个代码行所在
    物理行，段内注释与空行随物理行保留。

    独立真值：big.py = line_0001..line_1500（物理 1..1500，代码 1..1500）+
    "# 头段边界注释"（物理 1501）+ line_1501..line_3001（物理 1502..3002，
    代码 1501..3001）。总代码行 3001 > 3000。
    head 段 = 物理 1..1500；tail 段 = 第 1502 个代码行（line_1502，物理 1503）
    至末行物理 3002；物理 1501 的注释与物理 1502 的 line_1501 落在中段不提交。
    """
    body = (
        "".join(f"line_{i:04d}\n" for i in range(1, 1501))
        + "# 头段边界注释\n"
        + "".join(f"line_{i:04d}\n" for i in range(1501, 3002))
    )
    repo = write_tree({"big.py": body})
    inventory = build_inventory(run_cli, scripts, repo, tmp_path / "inventory.json")
    output = tmp_path / "src.docx"

    result = run_cli(
        scripts.build_source_docx,
        "--inventory", inventory, "--output", output,
        "--title", "演示系统", "--version", "V1.0",
        "--lines-per-page", "3000",
    )
    assert result.returncode == 0, result.stderr

    manifest = read_manifest(output)
    assert manifest["total_physical_lines"] == 3002
    assert manifest["total_code_lines"] == 3001
    assert manifest["selection"] == "first-1500-code-lines-and-last-1500"
    assert manifest["selected_physical_line_count"] == 3000
    assert manifest["selected_code_line_count"] == 3000
    assert manifest["first"] == {"path": "big.py", "line": 1, "text": "line_0001"}
    assert manifest["head_end"] == {"path": "big.py", "line": 1500, "text": "line_1500"}
    assert manifest["tail_start"] == {"path": "big.py", "line": 1503, "text": "line_1502"}
    assert manifest["last"] == {"path": "big.py", "line": 3002, "text": "line_3001"}


def test_python_syntax_error_refuses_build(
    write_tree, run_cli, scripts, tmp_path
):
    """Python 语法不可解析：拒构建转人工，不伪造通过。"""
    repo = write_tree({"broken.py": "def broken(:\n"})
    inventory = build_inventory(run_cli, scripts, repo, tmp_path / "inventory.json")

    result = run_cli(
        scripts.build_source_docx,
        "--inventory", inventory, "--output", tmp_path / "src.docx",
        "--title", "演示系统", "--version", "V1.0",
    )
    assert result.returncode != 0
    assert "strip failed" in result.stderr
    assert "broken.py" in result.stderr
