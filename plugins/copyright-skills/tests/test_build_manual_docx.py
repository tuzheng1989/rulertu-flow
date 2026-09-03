"""build_manual_docx.py 行为基线（B3）。

锚点（build_manual_docx.py）：
- :60-61  输出已存在拒绝覆盖
- :64-69  显式页数不足 --min-pages 拒绝
- :70-72  无图片拒绝
- :142-151 audit JSON 的 evidence_references 计数与 page_evidence 逐页映射
  （B4 已翻转：正文不再出现 evidence 段，evidence 只进旁路 audit JSON，全局红线 3）
"""

from __future__ import annotations

import json

from docx import Document


def spec_with_images(pages, png_name="img.png"):
    return {"title": "演示系统 操作手册", "version": "V1.0", "date": "2026年9月", "pages": pages}


def run_build(run_cli, scripts, spec_path, output, min_pages):
    return run_cli(
        scripts.build_manual_docx,
        "--spec", spec_path, "--output", output, "--min-pages", str(min_pages),
    )


def test_min_pages_not_met_rejected(tmp_path, write_tree, run_cli, scripts, tiny_png):
    """显式页数 < --min-pages：拒绝（锚点 :64-69）。"""
    write_tree({"img.png": tiny_png})
    spec_path = tmp_path / "spec.json"
    pages = [
        {"title": f"{i} 章", "paragraphs": ["内容"], "image": "img.png"} for i in range(1, 3)
    ]
    spec_path.write_text(json.dumps(spec_with_images(pages), ensure_ascii=False), encoding="utf-8")
    output = tmp_path / "manual.docx"

    # 2 个内容页 + 封面 + 目录 = 4 页 < 6
    result = run_build(run_cli, scripts, spec_path, output, min_pages=6)
    assert result.returncode != 0
    assert "manual has only 4 explicit pages" in result.stderr
    assert "at least 6 required" in result.stderr
    assert not output.exists()


def test_no_images_rejected(tmp_path, run_cli, scripts):
    """内容页均无图片：拒绝并提示真实截图要求（锚点 :70-72）。"""
    spec_path = tmp_path / "spec.json"
    pages = [{"title": f"{i} 章", "paragraphs": ["内容"]} for i in range(1, 9)]
    spec_path.write_text(json.dumps(spec_with_images(pages), ensure_ascii=False), encoding="utf-8")

    # 8 个内容页 + 封面 + 目录 = 10 页，页数达标，卡在无图分支
    result = run_build(run_cli, scripts, spec_path, tmp_path / "manual.docx", min_pages=10)
    assert result.returncode != 0
    assert "real screenshots" in result.stderr


def test_existing_output_refused(tmp_path, write_tree, run_cli, scripts, tiny_png):
    """输出文件已存在：拒绝覆盖（锚点 :60-61，全局红线 1）。"""
    write_tree({"img.png": tiny_png})
    spec_path = tmp_path / "spec.json"
    pages = [{"title": "1 章", "paragraphs": ["内容"], "image": "img.png"}]
    spec_path.write_text(json.dumps(spec_with_images(pages), ensure_ascii=False), encoding="utf-8")
    output = tmp_path / "manual.docx"
    output.write_bytes(b"existing")

    result = run_build(run_cli, scripts, spec_path, output, min_pages=3)
    assert result.returncode != 0
    assert "refusing to overwrite output" in result.stderr
    assert output.read_bytes() == b"existing"


def test_evidence_kept_out_of_body_and_written_to_audit(tmp_path, write_tree, run_cli, scripts, tiny_png):
    """【B4 翻转】evidence 不进正文（全局红线 3），逐页写入 audit JSON 的
    page_evidence：键为内容页序号（1 起，字符串），无 evidence 的页省略。
    evidence_references 仍为各页 evidence 条数之和。
    """
    # 图片与 spec 同目录（构建器按 spec 所在目录解析相对图片路径）
    write_tree({"img.png": tiny_png}, base=tmp_path)
    spec_path = tmp_path / "spec.json"
    pages = [
        {
            "title": "1 系统入口",
            "paragraphs": ["打开首页。"],
            "image": "img.png",
            "evidence": ["poc/server/app.py", "docs/spec.md"],
        },
        {
            "title": "2 数据导出",
            "paragraphs": ["点击导出。"],
            "image": "img.png",
            "evidence": ["lib/export.js"],
        },
        {
            "title": "3 无证据页",
            "paragraphs": ["普通内容。"],
            "image": "img.png",
        },
    ]
    spec_path.write_text(json.dumps(spec_with_images(pages), ensure_ascii=False), encoding="utf-8")
    output = tmp_path / "manual.docx"

    result = run_build(run_cli, scripts, spec_path, output, min_pages=5)
    assert result.returncode == 0, result.stderr
    assert output.is_file()

    # 正文任何段落不含 evidence 段字样，也不含任何 evidence 路径
    texts = [p.text for p in Document(str(output)).paragraphs]
    assert not any("材料复核依据" in t for t in texts)
    assert not any("poc/server/app.py" in t for t in texts)
    assert not any("lib/export.js" in t for t in texts)

    audit_path = output.with_suffix(output.suffix + ".audit.json")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    # 独立真值：2 + 1 + 0 = 3 条 evidence；第 3 页无 evidence，故省略
    assert audit["evidence_references"] == 3
    assert audit["page_evidence"] == {"1": ["poc/server/app.py", "docs/spec.md"], "2": ["lib/export.js"]}
    assert audit["explicit_pages"] == 5
    assert audit["illustrated_content_pages"] == 3
