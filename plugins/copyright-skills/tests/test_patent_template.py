"""patent-drafting 内置默认交底书模板的结构基线。

锚点（templates/技术交底书-默认模板.docx，由桌面案A docx 手术生成，2026-11-15）：
- 骨架：封面 7 段 + 8 个章节标题（样式 35）+ 各标题后空段 + 第 4 章标题下样式 38 图占位空段
- 无案A内容残留：word/media/、word/embeddings/ 条目不存在的；正文对案A关键词零命中
- 版式：sectPr 为 titlePg + header type=first + footer type=first/default 的首页/默认
  结构（settings.xml 无 evenAndOddHeaders——源 docx 实测为 titlePg 而非奇偶页，勿改断言）
- rels 闭合：document.xml 正文引用的 r:id/r:embed 全部存在于 rels（源包 rId9-13 随
  OLE 与图片一并删除，rId5/6/7 为 sectPr 页眉页脚引用必须保留）
- 样式断言一律用 styleId，不用样式名——源 styles.xml 中样式 35 的名称即为乱码字节
"""

from __future__ import annotations

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (
    PLUGIN_ROOT / "skills" / "patent-drafting" / "templates" / "技术交底书-默认模板.docx"
)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WT = f"{{{W}}}"

# 期望骨架：按文档顺序的段文本（strip 后比对；'' 表示空段）
EXPECTED_PARAS = [
    "技术交底书",
    "专利交底书名称：",
    "技术交底书撰写人：",
    "技术交底书撰写人的电话：",
    "技术交底书撰写人的邮箱：",
    "类型：√发明专利   实用新型专利   外观设计专利",
    "内部编号：",
    "",
    "1、术语解释",
    "",
    "本发明要解决的技术问题是什么？",
    "",
    "2、详细介绍技术背景,并描述已有的与本发明最相近似的实现方案",
    "",
    "3、以因果关系推理的方式推导出现有技术的缺点是什么？针对这些缺点，说明本发明的目的。",
    "",
    "4、本发明技术方案的详细阐述，应该结合流程图、原理框图、电路图、时序图进行说明",
    "",
    "",
    "5、本发明的关键点和欲保护点是什么？",
    "",
    "6、用推理方式推导出本发明的优点",
    "",
    "7、针对4中的技术方案，是否还有别的替代方案同样能完成发明目的？",
    "",
]

# 案A正文特征关键词（源 docx 案例内容，模板中必须零残留）
CASE_A_KEYWORDS = [
    "时空本体", "散件", "编织", "Fragment", "张力", "本体蓝图",
    "倒排", "物化", "WKT", "Neo4j", "RCC-8", "Allen",
]


def _para_text(p: ET.Element) -> str:
    return "".join(t.text or "" for t in p.iter(f"{WT}t"))


def _load_template_parts():
    with zipfile.ZipFile(TEMPLATE) as z:
        names = z.namelist()
        doc_root = ET.fromstring(z.read("word/document.xml"))
        rels_root = ET.fromstring(z.read("word/_rels/document.xml.rels"))
        ct_bytes = z.read("[Content_Types].xml")
    return names, doc_root, rels_root, ct_bytes


def test_template_exists_and_wellformed():
    assert TEMPLATE.is_file(), f"默认模板缺失: {TEMPLATE}"
    with zipfile.ZipFile(TEMPLATE) as z:
        # zipfile 可开且无坏条目
        assert z.testzip() is None
        # document.xml 良构可解析
        ET.fromstring(z.read("word/document.xml"))


def test_body_skeleton_whitelist():
    """结构白名单：段序列与期望逐段一致（含空段节奏）。"""
    _, doc_root, _, _ = _load_template_parts()
    body = doc_root.find(f"{WT}body")
    paras = [el for el in body if el.tag == f"{WT}p"]
    actual = [_para_text(p).strip() for p in paras]
    assert actual == EXPECTED_PARAS, (
        "骨架段序列不符:\n"
        + "\n".join(
            f"  [{i}] 期望={e!r} 实际={a!r}"
            for i, (e, a) in enumerate(zip(EXPECTED_PARAS, actual))
            if e != a
        )
    )
    # body 内除段落与末尾 sectPr 外无其他元素（无表格等）
    non_p = [el for el in body if el.tag != f"{WT}p"]
    assert len(non_p) == 1 and non_p[0].tag == f"{WT}sectPr"


def test_no_case_a_residue():
    """无案A残留：条目与关键词两个层面。"""
    names, doc_root, _, _ = _load_template_parts()
    assert not any(n.startswith("word/media/") for n in names)
    assert not any(n.startswith("word/embeddings/") for n in names)
    doc_text = ET.tostring(doc_root, encoding="unicode")
    for kw in CASE_A_KEYWORDS:
        assert kw not in doc_text, f"document.xml 残留案A关键词: {kw}"
    # 页眉页脚也不得残留
    with zipfile.ZipFile(TEMPLATE) as z:
        for part in ("word/header1.xml", "word/footer1.xml", "word/footer2.xml"):
            text = z.read(part).decode("utf-8")
            for kw in CASE_A_KEYWORDS:
                assert kw not in text, f"{part} 残留案A关键词: {kw}"


def test_cover_name_value_stripped():
    """封面名称行的值 run 已剥离——只余标签，无任何 run 携带案A名称。"""
    _, doc_root, _, _ = _load_template_parts()
    body = doc_root.find(f"{WT}body")
    paras = [el for el in body if el.tag == f"{WT}p"]
    name_para = paras[1]
    assert _para_text(name_para).strip() == "专利交底书名称："
    for r_el in name_para.iter(f"{WT}r"):
        assert "时空本体" not in _para_text(r_el)


def test_layout_styles_and_sectpr():
    """版式：样式引用用 styleId 断言（样式名在源文件即乱码）；sectPr 为首页/默认结构。"""
    _, doc_root, _, _ = _load_template_parts()
    body = doc_root.find(f"{WT}body")
    paras = [el for el in body if el.tag == f"{WT}p"]
    style_ids = set()
    for p in paras:
        pPr = p.find(f"{WT}pPr")
        if pPr is not None:
            s = pPr.find(f"{WT}pStyle")
            if s is not None:
                style_ids.add(s.get(f"{WT}val"))
    assert {"9", "35"} <= style_ids, f"样式 9(Title)/35(章节标题) 应被引用，实际: {style_ids}"
    # 第 4 章标题下保留样式 38 图占位空段
    assert "38" in style_ids, "样式 38(图占位) 应被引用"
    # 第 2 个标题的自动编号（代理所模板原始设计）仍在位
    q_para = paras[10]
    assert _para_text(q_para).strip() == "本发明要解决的技术问题是什么？"
    numPr = q_para.find(f"{WT}pPr").find(f"{WT}numPr")
    assert numPr is not None, "标题 2 的 numPr 自动编号应原样保留"

    sectpr = body.find(f"{WT}sectPr")
    assert sectpr is not None
    pgSz = sectpr.find(f"{WT}pgSz")
    assert pgSz.get(f"{WT}w") == "11900" and pgSz.get(f"{WT}h") == "16832"
    pgMar = sectpr.find(f"{WT}pgMar")
    assert pgMar.get(f"{WT}top") == "1440"
    assert pgMar.get(f"{WT}bottom") == "1157"
    assert pgMar.get(f"{WT}left") == "1440"
    assert pgMar.get(f"{WT}right") == "1355"
    assert sectpr.find(f"{WT}titlePg") is not None, "首页/默认结构依赖 titlePg"
    header_types = {
        h.get(f"{WT}type") for h in sectpr.findall(f"{WT}headerReference")
    }
    footer_types = {
        f.get(f"{WT}type") for f in sectpr.findall(f"{WT}footerReference")
    }
    assert header_types == {"first"}
    assert footer_types == {"default", "first"}


def test_rels_closure_and_content_types():
    """rels 闭合与 Content_Types 清理：无悬空引用、无 bin/emf/png 声明。"""
    _, doc_root, rels_root, ct_bytes = _load_template_parts()
    rel_ids = {rel.get("Id") for rel in rels_root}
    assert not {"rId9", "rId10", "rId11", "rId12", "rId13"} & rel_ids
    # document.xml 中全部 r:id / r:embed 引用闭合于 rels
    ns = {"r": R}
    refs = set()
    for el in doc_root.iter():
        for attr_name, attr_val in el.attrib.items():
            if attr_name.startswith(f"{{{R}}}") and attr_val.startswith("rId"):
                refs.add(attr_val)
    for el in doc_root.findall(f".//{WT}headerReference", ns):
        refs.add(el.get(f"{{{R}}}id"))
    for el in doc_root.findall(f".//{WT}footerReference", ns):
        refs.add(el.get(f"{{{R}}}id"))
    assert refs <= rel_ids, f"悬空引用: {refs - rel_ids}"
    # sectPr 的页眉页脚引用在位
    assert refs >= {"rId5", "rId6", "rId7"}
    # Content_Types：bin/emf/png 的 Default 已随部件删除
    ct_text = ct_bytes.decode("utf-8")
    for ext in ('Extension="bin"', 'Extension="emf"', 'Extension="png"'):
        assert ext not in ct_text, f"Content_Types 仍声明已删扩展名: {ext}"
