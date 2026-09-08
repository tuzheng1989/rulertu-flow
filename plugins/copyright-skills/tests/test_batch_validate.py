"""batch_validate.py 行为基线（多软著批量校验）。

锚点（batch_validate.py）：
- entries 为空报错；name/version/module_roots/output_dir 必填
- 跨条目共享文件未列入 allowlist 即阻断；列入则记 review_items
- 每份代码行低于内部下限（--min-code-lines，默认 500）报错
- 条目两两查重（复用 similarity_check 指纹），任一方向超限即阻断
- --first 指向条目文件集外的路径报错
"""

from __future__ import annotations

import json

import pytest


@pytest.fixture()
def batch_module(load_module, scripts):
    """按依赖序加载 scan_source → similarity_check → batch_validate。

    batch_validate 顶层 import inventory_repo / strip_source（同目录）与
    similarity_check（跨目录，其顶层又 import scan_source），
    load_module 注册进 sys.modules 后 import 即可解析。
    """
    load_module("scan_source", scripts.scan_source.parent)
    load_module("similarity_check", scripts.similarity_check.parent)
    load_module("inventory_repo", scripts.inventory_repo.parent)
    load_module("strip_source", scripts.strip_source.parent)
    return load_module("batch_validate", scripts.batch_validate.parent)


def entry(name, roots, out, **extra):
    data = {
        "name": name,
        "version": "V1.0",
        "module_roots": roots,
        "output_dir": out,
    }
    data.update(extra)
    return data


def run_validate(batch_module, repo, config, **overrides):
    defaults = {"min_code_lines": 10, "window": 6, "threshold": 0.2, "min_run": 10}
    defaults.update(overrides)
    return batch_module.validate_batch(repo, config, **defaults)


def module_tree(prefix: str, count: int) -> str:
    return "".join(f"def {prefix}_{i:03d}(): return {i}\n" for i in range(1, count + 1))


def write_module(repo, root, prefix, count):
    target = repo / root
    target.mkdir(parents=True, exist_ok=True)
    (target / "core.py").write_text(module_tree(prefix, count), encoding="utf-8")


# ---------------------------------------------------------------------------
# 通过路径：独立模块的合法批量配置
# ---------------------------------------------------------------------------

def test_valid_batch_passes(batch_module, tmp_path):
    repo = tmp_path / "repo"
    write_module(repo, "src/sched", "sched", 20)
    write_module(repo, "src/report", "report", 20)
    write_module(repo, "src/web", "webjs", 20)

    report = run_validate(batch_module, repo, {
        "entries": [
            entry("调度软件", ["src/sched"], "out/sched", first="src/sched/core.py"),
            entry("报表软件", ["src/report"], "out/report"),
            entry("网页软件", ["src/web"], "out/web"),
        ],
    })
    assert report["passed"] is True
    assert report["failures"] == []
    assert [item["code_lines"] for item in report["entries"]] == [20, 20, 20]
    assert [item["file_count"] for item in report["entries"]] == [1, 1, 1]
    pair_flags = [item["flagged_count"] for item in report["pairs"]]
    assert pair_flags == [0, 0, 0]
    assert report["shared_files"] == []
    # --first 在条目文件集内，无阻断
    assert report["entries"][0]["first"] == "src/sched/core.py"


# ---------------------------------------------------------------------------
# 唯一归属：共享文件未列入 allowlist 阻断，列入则记 review_items
# ---------------------------------------------------------------------------

def test_shared_file_blocked_then_allowed_by_allowlist(batch_module, tmp_path):
    repo = tmp_path / "repo"
    write_module(repo, "src/sched", "sched", 20)
    write_module(repo, "src/report", "report", 20)
    shared = repo / "src/common.py"
    shared.parent.mkdir(parents=True, exist_ok=True)
    shared.write_text(module_tree("common", 10), encoding="utf-8")

    config = {
        "entries": [
            entry("调度软件", ["src/sched", "src/common.py"], "out/sched"),
            entry("报表软件", ["src/report", "src/common.py"], "out/report"),
        ],
    }

    # 注意：module_roots 是目录级过滤器，单文件 root 需要 exact 匹配路径
    report = run_validate(batch_module, repo, config)
    assert report["passed"] is False
    shared_failures = [item for item in report["failures"] if "shared file" in item]
    assert len(shared_failures) == 1
    assert "src/common.py" in shared_failures[0]

    config["shared_allowlist"] = ["src/common.py"]
    report = run_validate(batch_module, repo, config)
    assert report["passed"] is True
    assert len(report["shared_files"]) == 1
    assert report["shared_files"][0]["allowed"] is True
    assert any("src/common.py" in item for item in report["review_items"])


def test_allowlist_unknown_entry_recorded(batch_module, tmp_path):
    """allowlist 里写了不存在的文件：记录 review_items，不阻断也不静默。"""
    repo = tmp_path / "repo"
    write_module(repo, "src/sched", "sched", 20)
    write_module(repo, "src/report", "report", 20)

    report = run_validate(batch_module, repo, {
        "entries": [
            entry("调度软件", ["src/sched"], "out/sched"),
            entry("报表软件", ["src/report"], "out/report"),
        ],
        "shared_allowlist": ["src/ghost.py"],
    })
    assert report["passed"] is True
    review_items = report["review_items"]
    assert any("src/ghost.py" in item for item in review_items)


# ---------------------------------------------------------------------------
# 代码行下限与配置校验
# ---------------------------------------------------------------------------

def test_code_lines_below_minimum_blocked(batch_module, tmp_path):
    repo = tmp_path / "repo"
    write_module(repo, "src/sched", "sched", 20)
    write_module(repo, "src/thin", "thin", 3)

    report = run_validate(batch_module, repo, {
        "entries": [
            entry("调度软件", ["src/sched"], "out/sched"),
            entry("薄模块", ["src/thin"], "out/thin"),
        ],
    }, min_code_lines=10)
    assert report["passed"] is False
    assert any("below minimum" in item for item in report["failures"])


def test_missing_required_fields_blocked(batch_module, tmp_path):
    repo = tmp_path / "repo"
    write_module(repo, "src/sched", "sched", 20)

    report = run_validate(batch_module, repo, {
        "entries": [
            {"name": "调度软件", "version": "V1.0", "module_roots": ["src/sched"], "output_dir": "out/sched"},
            entry("缺目录", ["src/sched"], "out/x", output_dir=None),
            entry("调度软件", ["src/sched"], "out/sched"),
        ],
    }, min_code_lines=10)
    assert report["passed"] is False
    assert any("output_dir is required" in item for item in report["failures"])
    assert any("duplicate name+version" in item for item in report["failures"])
    assert any("output_dir duplicates" in item for item in report["failures"])


# ---------------------------------------------------------------------------
# 两两查重：同内容模块互相阻断，改写后通过
# ---------------------------------------------------------------------------

def test_pairwise_similarity_blocked(batch_module, tmp_path):
    repo = tmp_path / "repo"
    write_module(repo, "src/alpha", "same_body", 30)
    write_module(repo, "src/beta", "same_body", 30)

    report = run_validate(batch_module, repo, {
        "entries": [
            entry("甲软件", ["src/alpha"], "out/alpha"),
            entry("乙软件", ["src/beta"], "out/beta"),
        ],
    })
    assert report["passed"] is False
    pair = report["pairs"][0]
    assert pair["flagged_count"] > 0
    assert any("exceed similarity limits" in item for item in report["failures"])
    assert pair["max_containment"] > 0.2


def test_pairwise_similarity_passes_after_rewrite(batch_module, tmp_path):
    repo = tmp_path / "repo"
    write_module(repo, "src/alpha", "alpha_body", 30)
    write_module(repo, "src/beta", "beta_body", 30)

    report = run_validate(batch_module, repo, {
        "entries": [entry("甲软件", ["src/alpha"], "out/alpha"),
                    entry("乙软件", ["src/beta"], "out/beta")],
    })
    assert report["passed"] is True


def test_first_outside_entry_blocked(batch_module, tmp_path):
    repo = tmp_path / "repo"
    write_module(repo, "src/sched", "sched", 20)
    write_module(repo, "src/report", "report", 20)

    report = run_validate(batch_module, repo, {
        "entries": [
            entry("调度软件", ["src/sched"], "out/sched", first="src/report/core.py"),
        ],
    })
    assert report["passed"] is False
    assert any("--first path not in entry files" in item for item in report["failures"])


# ---------------------------------------------------------------------------
# CLI：端到端
# ---------------------------------------------------------------------------

def test_cli_end_to_end(write_tree, run_cli, scripts, tmp_path):
    repo = write_tree({
        "src/sched/core.py": module_tree("sched", 120),
        "src/report/core.py": module_tree("report", 120),
    })
    batch = tmp_path / "batch.json"
    batch.write_text(json.dumps({
        "entries": [
            entry("调度软件", ["src/sched"], "out/sched"),
            entry("报表软件", ["src/report"], "out/report"),
        ],
    }), encoding="utf-8")
    output = tmp_path / "batch-report.json"

    result = run_cli(scripts.batch_validate, "--repo", repo, "--batch", batch, "--output", output, "--min-code-lines", "10")
    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert payload["entries"][0]["code_lines"] == 120

    # 失败路径：共享文件未 allowlist → exit 1
    (repo / "src/shared.py").write_text(module_tree("shared", 15), encoding="utf-8")
    batch.write_text(json.dumps({
        "entries": [
            entry("调度软件", ["src/sched", "src/shared.py"], "out/sched"),
            entry("报表软件", ["src/report", "src/shared.py"], "out/report"),
        ],
    }), encoding="utf-8")
    result = run_cli(scripts.batch_validate, "--repo", repo, "--batch", batch, "--output", output)
    assert result.returncode == 1
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["passed"] is False
    assert any("shared file" in item for item in payload["failures"])