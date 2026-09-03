"""render_check.py 行为测试（B4，先写函数级，再写 CLI 级）。

锚点（render_check.py）：
- count_pdf_lines：fitz 逐页提取文本、按换行拆分后非空行计数，
  报告含 render_checked / total_pages / pages / under_pages / min_lines / line_definition；
- convert_to_pdf：接缝函数，可被替换（第三切片验证注入）；
- CLI：soffice 缺失 → 非零退出 + 人工核对提示，绝不产出 render_checked: true；
- CLI：输出已存在 → 拒绝覆盖（全局红线 1）。

本机无 LibreOffice/soffice，缺失分支即真实环境分支。
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import fitz
import pytest

from conftest import CN_SCRIPTS

RENDER_CHECK = CN_SCRIPTS / "render_check.py"


# --- 第二切片：count_pdf_lines 行数统计 ------------------------------------


def make_pdf(path, lines_per_page):
    """用 fitz 构造已知行数的 PDF：每页写入 lines_per_page[i] 行互异文本。"""
    document = fitz.open()
    for count in lines_per_page:
        page = document.new_page()
        for i in range(count):
            page.insert_text((50, 60 + i * 14), f"row {i:03d} of page content")
    document.save(path)
    document.close()


@pytest.fixture()
def load_render_check(load_module):
    return load_module("render_check", CN_SCRIPTS)


def test_count_pdf_lines_reports_per_page_and_under_list(tmp_path, load_render_check):
    """3 页 PDF（35/10/0 行）按 min_lines=30：第 2、3 页列入不足清单（锚点 count_pdf_lines）。"""
    pdf = tmp_path / "manual.pdf"
    make_pdf(pdf, [35, 10, 0])

    report = load_render_check.count_pdf_lines(pdf, min_lines=30)
    assert report["render_checked"] is True
    assert report["total_pages"] == 3
    assert report["pages"] == {"1": 35, "2": 10, "3": 0}
    assert report["under_pages"] == ["2", "3"]
    assert report["min_lines"] == 30
    # 行的口径必须写进报告，便于人工复核时对齐
    assert "line_definition" in report and report["line_definition"]


def test_count_pdf_lines_all_pages_sufficient(tmp_path, load_render_check):
    """所有页达标：under_pages 为空列表，render_checked 仍为 True。"""
    pdf = tmp_path / "manual.pdf"
    make_pdf(pdf, [31, 30])

    report = load_render_check.count_pdf_lines(pdf, min_lines=30)
    assert report["render_checked"] is True
    assert report["under_pages"] == []
    assert report["pages"] == {"1": 31, "2": 30}


def test_count_pdf_lines_ignores_blank_rows(tmp_path, load_render_check):
    """口径验证：页内空白行不计入。样本写入 4 行非空文本，其间插入一行仅含
    空格的文本（get_text 会原样返回该空白行），计数必须为 4 而非 5。
    """
    pdf = tmp_path / "manual.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((50, 60), "only 0")
    page.insert_text((50, 74), "   ")  # 仅空格：构成真空白行
    page.insert_text((50, 88), "only 1")
    page.insert_text((50, 102), "only 2")
    page.insert_text((50, 116), "only 3")
    document.save(pdf)
    document.close()

    # 样本自检：确认 get_text 确实返回了那行空白，否则用例失去构造前提
    with fitz.open(pdf) as probe:
        assert any(not line.strip() for line in probe[0].get_text().splitlines())

    report = load_render_check.count_pdf_lines(pdf, min_lines=1)
    assert report["pages"] == {"1": 4}


# --- 第三切片：CLI 行为（soffice 缺失分支 / 拒绝覆盖 / 转换器注入） ----------


def _make_docx(path) -> None:
    from docx import Document

    document = Document()
    document.add_paragraph("演示段落，供存在性校验。")
    document.save(path)


@pytest.mark.skipif(
    shutil.which("soffice") is not None,
    reason="前提：PATH 中无 soffice。装了 LibreOffice 的机器上会真启动 soffice 转换，"
    "用例失去触发条件；失败分支另由 test_cli_soffice_path_invalid_fails_loudly "
    "以显式 --soffice 坏路径覆盖。",
)
def test_cli_soffice_forced_but_missing_fails_loudly(tmp_path, run_cli):
    """--converter soffice 且 PATH 无 soffice：非零退出 + 人工核对提示，
    且绝不产出报告（必不现 render_checked: true 假成功）。
    """
    docx = tmp_path / "manual.docx"
    _make_docx(docx)
    report = tmp_path / "render-report.json"

    result = run_cli(
        RENDER_CHECK, "--docx", docx, "--min-lines", "30",
        "--output", report, "--converter", "soffice",
    )
    assert result.returncode != 0
    assert "无法渲染校验" in result.stderr
    assert "人工" in result.stderr
    assert not report.exists()


def test_cli_soffice_path_invalid_fails_loudly(tmp_path, run_cli):
    """--soffice 指向不存在的可执行文件：同样走人工核对降级分支。"""
    docx = tmp_path / "manual.docx"
    _make_docx(docx)
    report = tmp_path / "render-report.json"

    result = run_cli(
        RENDER_CHECK, "--docx", docx, "--min-lines", "30",
        "--output", report, "--soffice", tmp_path / "no-such-soffice.exe",
    )
    assert result.returncode != 0
    assert "无法渲染校验" in result.stderr
    assert not report.exists()


def test_cli_refuses_existing_output(tmp_path, run_cli):
    """输出报告已存在：拒绝覆盖（全局红线 1，与既有脚本约定一致）。"""
    docx = tmp_path / "manual.docx"
    _make_docx(docx)
    report = tmp_path / "render-report.json"
    report.write_text("{}", encoding="utf-8")

    result = run_cli(RENDER_CHECK, "--docx", docx, "--min-lines", "30", "--output", report)
    assert result.returncode != 0
    assert "refusing to overwrite output" in result.stderr
    assert report.read_text(encoding="utf-8") == "{}"


def test_cli_missing_docx_rejected(tmp_path, run_cli):
    docx = tmp_path / "missing.docx"
    result = run_cli(
        RENDER_CHECK, "--docx", docx, "--min-lines", "30", "--output", tmp_path / "r.json"
    )
    assert result.returncode != 0
    assert "docx not found" in result.stderr


def test_cli_injected_converter_full_report(tmp_path, load_render_check, monkeypatch):
    """转换函数是接缝：注入产出 fitz 构造 PDF 的假转换器，全流程报告可断言；
    临时转换目录用后必须清理。注入时显式 --converter soffice + 占位 --soffice 路径
    通过后端选择，fake 断言收到的 converter 参数。
    """
    docx = tmp_path / "manual.docx"
    _make_docx(docx)
    soffice_stub = tmp_path / "soffice-stub.exe"
    soffice_stub.write_bytes(b"")
    pdf = tmp_path / "manual.pdf"
    make_pdf(pdf, [5, 2])

    captured: dict = {}

    def fake_convert(docx_path, converter, out_dir, soffice=None):
        captured["converter"] = converter
        captured["out_dir"] = Path(out_dir)
        target = Path(out_dir) / Path(docx_path).with_suffix(".pdf").name
        target.write_bytes(pdf.read_bytes())
        return target

    monkeypatch.setattr(load_render_check, "convert_to_pdf", fake_convert)
    report_path = tmp_path / "render-report.json"

    code = load_render_check.main(
        ["--docx", str(docx), "--min-lines", "3", "--output", str(report_path),
         "--converter", "soffice", "--soffice", str(soffice_stub)]
    )
    assert code == 0
    assert captured["converter"] == "soffice"
    assert captured["out_dir"].exists() is False, "临时转换目录必须清理"

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["render_checked"] is True
    assert report["total_pages"] == 2
    assert report["pages"] == {"1": 5, "2": 2}
    assert report["under_pages"] == ["2"]
    assert report["min_lines"] == 3
