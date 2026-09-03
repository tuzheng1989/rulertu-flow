"""similarity_check.py 行为基线（B3）。

CLI 接口（similarity_check.py:122-132）：
    --repo --references(可重复, 必填) --output --window(默认6) --threshold(默认0.2) --min-run(默认10)
命中条件（:105）：containment >= threshold 或 预估最长相同连续行数 >= min_run。

用例以默认参数运行（window=6）：6 行连续相同文本构成一个相同指纹窗口。
"""

from __future__ import annotations

import json

# 12 行共享文本：两份文件中都逐行相同（normalize 后一致：去首尾空白、压缩空白、小写）
SHARED_LINES = [
    "alpha = compute_alpha(1)",
    "beta = compute_beta(alpha)",
    "gamma = beta + 3",
    "delta = gamma * 2",
    "result = summarize(alpha, delta)",
    "if result > 10:",
    "    report(result)",
    "    log_event(\"threshold\")",
    "else:",
    "    log_event(\"skip\")",
    "cleanup(alpha)",
    "return result",
]

UNIQUE_HEAD = ["head_one = 1", "head_two = 2", "head_three = 3"]
UNIQUE_TAIL = ["tail_one = 1", "tail_two = 2"]
UNRELATED_LINES = [
    f"unrelated_{i} = hash((str({i}), 'x'))" for i in range(1, 11)
]


def run_check(run_cli, scripts, repo, refs, output):
    return run_cli(
        scripts.similarity_check,
        "--repo", repo, "--references", refs, "--output", output,
    )


def test_files_sharing_long_run_are_flagged(write_tree, run_cli, scripts, tmp_path):
    """共享 >= 6 连续相同行的文件命中，报告指向参考文件（锚点 :105-119, :198-203）。"""
    repo = write_tree({"app.py": "\n".join(UNIQUE_HEAD + SHARED_LINES + UNIQUE_TAIL) + "\n"})
    refs = write_tree(
        {"other.py": "\n".join(["ref_head = 0"] + SHARED_LINES + ["ref_tail = 9"]) + "\n"},
        base=tmp_path / "refs",
    )
    output = tmp_path / "similarity.json"

    result = run_check(run_cli, scripts, repo, refs, output)
    assert result.returncode == 0, result.stderr

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["summary"]["scanned_file_count"] == 1  # 只有 repo/app.py
    assert payload["summary"]["flagged_file_count"] == 1
    flagged = payload["flagged_files"][0]
    assert flagged["path"] == "app.py"
    # 独立真值：12 行共享文本。window=6 时完全落在共享段内的窗口是第 3..9 个，共 7 个
    assert flagged["reference_hits"] == [{"path": "refs/other.py", "matched_windows": 7}]
    # 预估相同连续行数 = 共享段 12 行
    assert flagged["est_max_similar_run_lines"] == 12
    assert flagged["containment"] > 0.5
    # 示例给出仓库内与参考文件的行号区间
    example = flagged["examples"][0]
    assert example["reference"] == "refs/other.py"
    assert example["repo_lines"][0] >= 4  # 共享段从 app.py 第 4 行开始
    assert payload["summary"]["matched_reference_files"] == ["refs/other.py"]


def test_unrelated_file_is_not_flagged(write_tree, run_cli, scripts, tmp_path):
    """与参考语料无共享窗口的文件不命中（锚点 :76-77, :105, :166）。"""
    repo = write_tree({"clean.py": "\n".join(UNRELATED_LINES) + "\n"})
    refs = write_tree({"other.py": "\n".join(SHARED_LINES) + "\n"}, base=tmp_path / "refs")
    output = tmp_path / "similarity.json"

    result = run_check(run_cli, scripts, repo, refs, output)
    assert result.returncode == 0, result.stderr

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["summary"]["scanned_file_count"] == 1
    assert payload["summary"]["flagged_file_count"] == 0
    assert payload["flagged_files"] == []
    assert payload["summary"]["matched_reference_files"] == []


def test_missing_reference_root_fails(write_tree, run_cli, scripts, tmp_path):
    """参考目录不存在：非零退出并提示（锚点 :137-140）。"""
    repo = write_tree({"app.py": "value = 1\n"})
    output = tmp_path / "similarity.json"

    result = run_check(run_cli, scripts, repo, tmp_path / "no-such-refs", output)
    assert result.returncode != 0
    assert "reference root not found" in result.stderr
    assert not output.exists()
