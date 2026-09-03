"""inventory_repo.py 行为基线（B3）。

锚点（inventory_repo.py）：
- :57-60  physical_lines 计行边界
- :20-28  DEFAULT_EXCLUDES 与 :93 excluded 记录的 reason 字段
- :103-104 casefold 排序
- :31-39, :111-115 非 git 目录下 git 元数据为 None
"""

from __future__ import annotations

import json


# ---- physical_lines：独立真值 = 手数行数 ----

def test_physical_lines_empty(load_module, scripts):
    module = load_module("inventory_repo", scripts.inventory_repo.parent)
    # 空文件 0 行
    assert module.physical_lines(b"") == 0


def test_physical_lines_no_trailing_newline(load_module, scripts):
    module = load_module("inventory_repo", scripts.inventory_repo.parent)
    # b"a\nb" 手数是 2 行（最后一个换行缺失也要算一行）
    assert module.physical_lines(b"a\nb") == 2
    assert module.physical_lines(b"only") == 1


def test_physical_lines_crlf(load_module, scripts):
    module = load_module("inventory_repo", scripts.inventory_repo.parent)
    # CRLF 文件按行计，\r 不产生额外行：3 行
    assert module.physical_lines(b"a\r\nb\r\nc\r\n") == 3


# ---- CLI ----

def test_cli_default_excludes_record_reason(write_tree, run_cli, scripts, tmp_path):
    """DEFAULT_EXCLUDES 命中的文件进 excluded，且记录带命中模式理由（锚点 :20-28, :91-93）。"""
    repo = write_tree({
        "main.py": "if __name__ == \"__main__\":\n    pass\n",
        "app.py": "value = 1\n",
        "node_modules/x.js": "var a = 1;\n",   # 命中 node_modules/**
        "docs/extra.py": "value = 2\n",        # 命中 docs/**
        ".env": "SECRET=1\n",                  # 无后缀，先命中"非源码后缀"分支
    })
    output = tmp_path / "out" / "inventory.json"
    result = run_cli(scripts.inventory_repo, "--repo", repo, "--output", output)
    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))

    excluded = {item["path"]: item["reason"] for item in payload["excluded_files"]}
    assert excluded["node_modules/x.js"] == "excluded by node_modules/**"
    assert excluded["docs/extra.py"] == "excluded by docs/**"
    # Path(".env").suffix 为空，按现状落在"非源码后缀"分支，而不是排除模式分支
    assert excluded[".env"] == "not an application source extension"
    # 每条 excluded 记录都有 reason 字段
    assert all(item["reason"] for item in payload["excluded_files"])
    # 入选文件不含被排除项
    included = {item["path"] for item in payload["included_files"]}
    assert included == {"main.py", "app.py"}


def test_cli_sort_uses_casefold(write_tree, run_cli, scripts, tmp_path):
    """排序键为 casefold（锚点 :103）。

    说明：同 casefold 键的相对次序取决于稳定排序前的 rglob 枚举顺序（文件系统相关，
    不保证与写入顺序一致），因此只断言 casefold 序本身；纯 ASCII 排序会把
    "Zebra.py" 排在 "apple.py" 之前，与此不同。
    """
    repo = write_tree({
        "Zebra.py": "z = 1\n",
        "apple.py": "a = 1\n",
        "Banana.py": "b = 1\n",
        "cherry.py": "c = 1\n",
    })
    output = tmp_path / "inventory.json"
    result = run_cli(scripts.inventory_repo, "--repo", repo, "--output", output)
    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))

    order = [item["path"] for item in payload["included_files"]]
    # casefold 序：apple < banana < cherry < zebra；纯 ASCII 序 Zebra.py 会排最前
    assert order == ["apple.py", "Banana.py", "cherry.py", "Zebra.py"]


def test_cli_non_git_repo_metadata_none(write_tree, run_cli, scripts, tmp_path):
    """非 git 目录：git 元数据为 None 不崩溃，且回退到文件系统遍历（锚点 :31-39, :46）。"""
    repo = write_tree({"app.py": "value = 1\n"})
    output = tmp_path / "inventory.json"
    result = run_cli(scripts.inventory_repo, "--repo", repo, "--output", output)
    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["git"] == {"commit": None, "branch": None, "dirty": None}
    # 非 git 时 discover 回退 rglob，文件仍被清点
    assert [item["path"] for item in payload["included_files"]] == ["app.py"]


def test_cli_gb18030_file_counted_as_bytes(write_tree, run_cli, scripts, tmp_path):
    """GB18030 编码文件照常入选，bytes 为原始字节数、行数按物理行计。"""
    content = "# 中文注释\nvalue = 1\n".encode("gb18030")
    repo = write_tree({"cn.py": content})
    output = tmp_path / "inventory.json"
    result = run_cli(scripts.inventory_repo, "--repo", repo, "--output", output)
    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))

    entry = payload["included_files"][0]
    assert entry["path"] == "cn.py"
    assert entry["bytes"] == len(content)  # 独立真值：写入时的字节数
    assert entry["physical_lines"] == 2
