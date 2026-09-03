"""check_submission.py 行为基线（B6）。

锚点（check_submission.py，新增脚本）：
- 输出已存在拒绝覆盖（全局红线 1）
- 缺失文档 → files 缺失条目 + 非零退出
- pending 权属项 → blocked_items + 非零退出（内部暂停提交）
- scenario / status 越界 → 清单无效，报错退出，不写输出
- 全 provided + 文件齐全 → 机检通过、manual_items 非空、报告无"可提交"结论措辞
- docx 可解析、render_hint 提示先经 render_check.py

权属清单 schema 唯一出处：references/ownership.md（B2）。conftest.py 不在本批
允许改动清单内，脚本路径在本文件内自持；run_cli fixture 复用 conftest。
"""

from __future__ import annotations

import json
from pathlib import Path

import fitz

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills" / "software-copyright-cn" / "scripts" / "check_submission.py"
)

SCENARIO = "independent"  # 独立开发：必需文件仅主体资格证明（ownership.md 决策表）


def ownership_payload(statuses):
    """statuses 与条目一一对应：(type, status) 序列 → 权属清单 dict。"""
    return {
        "scenario": SCENARIO,
        "items": [
            {"file": f"证明-{i}.pdf", "type": kind, "status": status, "note": ""}
            for i, (kind, status) in enumerate(statuses)
        ],
    }


def write_ownership(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def make_pdf(path: Path) -> Path:
    """fitz 造单页 PDF，页数独立真值为 1。"""
    doc = fitz.open()
    doc.new_page()
    doc.save(path)
    doc.close()
    return path


def run_check(run_cli, docs, ownership: Path, output: Path):
    args = []
    for doc in docs:
        args += ["--docs", str(doc)]
    return run_cli(
        SCRIPT, *args,
        "--ownership", str(ownership),
        "--output", str(output),
    )


def test_missing_doc_listed_and_nonzero_exit(tmp_path, run_cli):
    """缺失文档：files 必现缺失条目 + 非零退出（验收标准 1）。"""
    pdf = make_pdf(tmp_path / "签章页.pdf")
    ownership = write_ownership(tmp_path / "ownership.json", ownership_payload([("identity", "provided")]))
    output = tmp_path / "submission-check.json"
    missing = tmp_path / "说明书.docx"  # 故意不创建

    result = run_check(run_cli, [pdf, missing], ownership, output)

    assert result.returncode != 0
    report = json.loads(output.read_text(encoding="utf-8"))
    by_name = {Path(entry["path"]).name: entry for entry in report["files"]}
    assert by_name["说明书.docx"]["exists"] is False
    assert by_name["说明书.docx"]["parsed"] is False
    assert by_name["说明书.docx"]["error"]  # 缺失原因可读


def test_all_provided_pdf_passes_machine_checks(tmp_path, run_cli):
    """全 provided + 单页 PDF：机检通过、manual_items 非空、无"可提交"结论措辞（验收标准 3）。"""
    pdf = make_pdf(tmp_path / "签章页.pdf")
    ownership = write_ownership(tmp_path / "ownership.json", ownership_payload([("identity", "provided")]))
    output = tmp_path / "submission-check.json"

    result = run_check(run_cli, [pdf], ownership, output)

    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["files"][0]["parsed"] is True
    assert report["files"][0]["pages"] == 1  # 独立真值：fitz 造的就是单页
    assert report["ownership"]["scenario"] == "independent"
    assert report["ownership"]["provided"] == 1
    assert report["ownership"]["pending"] == 0
    assert report["ownership"]["na"] == 0
    assert report["ownership"]["blocked_items"] == []
    assert report["manual_items"]  # 机器不可判定项固定列出
    text = output.read_text(encoding="utf-8")
    assert "可提交" not in text
    assert "官方" not in text  # 报告只陈述机检事实，不得暗示官方结果（红线 2）
    assert "conclusion" not in report  # 无结论类字段
    assert "render_check" in report["render_hint"]


def test_pending_ownership_blocks(tmp_path, run_cli):
    """pending 权属项：必现 blocked_items + 非零退出（验收标准 2）。"""
    pdf = make_pdf(tmp_path / "签章页.pdf")
    statuses = [("identity", "provided"), ("contract", "pending")]
    ownership = write_ownership(tmp_path / "ownership.json", ownership_payload(statuses))
    output = tmp_path / "submission-check.json"

    result = run_check(run_cli, [pdf], ownership, output)

    assert result.returncode != 0
    report = json.loads(output.read_text(encoding="utf-8"))
    blocked_files = [item["file"] for item in report["ownership"]["blocked_items"]]
    assert blocked_files == ["证明-1.pdf"]  # 独立真值：只有第 1 项是 pending
    assert report["ownership"]["pending"] == 1


def test_malformed_ownership_json_rejected(tmp_path, run_cli):
    """--ownership 指向非法 JSON：SystemExit 报错含清单路径与原因，不抛 traceback。"""
    pdf = make_pdf(tmp_path / "签章页.pdf")
    ownership = tmp_path / "ownership.json"
    ownership.write_text("{not-json", encoding="utf-8")
    output = tmp_path / "submission-check.json"

    result = run_check(run_cli, [pdf], ownership, output)

    assert result.returncode != 0
    assert "ownership.json" in result.stderr
    assert "not valid JSON" in result.stderr
    assert "Traceback" not in result.stderr
    assert not output.exists()


def test_invalid_scenario_rejected(tmp_path, run_cli):
    """scenario 越界：清单无效，报错退出，不写输出（ownership.md 消费规则）。"""
    pdf = make_pdf(tmp_path / "签章页.pdf")
    payload = ownership_payload([("identity", "provided")])
    payload["scenario"] = "freelance"  # 六标识之外
    ownership = write_ownership(tmp_path / "ownership.json", payload)
    output = tmp_path / "submission-check.json"

    result = run_check(run_cli, [pdf], ownership, output)

    assert result.returncode != 0
    assert "scenario" in result.stderr
    assert not output.exists()


def test_invalid_status_rejected(tmp_path, run_cli):
    """status 越界（三态之外）：清单无效，报错退出，不写输出。"""
    pdf = make_pdf(tmp_path / "签章页.pdf")
    payload = ownership_payload([("identity", "unknown")])
    ownership = write_ownership(tmp_path / "ownership.json", payload)
    output = tmp_path / "submission-check.json"

    result = run_check(run_cli, [pdf], ownership, output)

    assert result.returncode != 0
    assert "status" in result.stderr
    assert not output.exists()


def test_existing_output_rejected(tmp_path, run_cli):
    """输出已存在：拒绝覆盖（全局红线 1）。"""
    pdf = make_pdf(tmp_path / "签章页.pdf")
    ownership = write_ownership(tmp_path / "ownership.json", ownership_payload([("identity", "provided")]))
    output = tmp_path / "submission-check.json"
    output.write_bytes(b"existing")

    result = run_check(run_cli, [pdf], ownership, output)

    assert result.returncode != 0
    assert "refusing to overwrite" in result.stderr
    assert output.read_bytes() == b"existing"


def test_docx_parsed_with_render_hint(tmp_path, run_cli):
    """docx：python-docx 可解析（无页数概念，pages 为 null），render_hint 指向 render_check.py。"""
    from docx import Document

    docx_path = tmp_path / "说明书.docx"
    document = Document()
    document.add_paragraph("功能说明正文")
    document.save(docx_path)
    ownership = write_ownership(tmp_path / "ownership.json", ownership_payload([("identity", "provided")]))
    output = tmp_path / "submission-check.json"

    result = run_check(run_cli, [docx_path], ownership, output)

    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["files"][0]["parsed"] is True
    assert report["files"][0]["pages"] is None  # docx 无页数，页数校验属 render_check.py
    assert "render_check" in report["render_hint"]
