#!/usr/bin/env python3
"""
gongwen-to-docx.py — 将 Markdown + YAML frontmatter 转换为符合 GB/T 9704-2012 标准的公文 DOCX

用法：
    python gongwen-to-docx.py <input.md> [-o output.docx] [--verbose]
"""

import argparse
import os
import re
import sys
from pathlib import Path

import yaml
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, Mm, Cm, Emu


# ============================================================
# 常量配置
# ============================================================

# 页面尺寸（GB/T 9704-2012）
PAGE_WIDTH = Mm(210)
PAGE_HEIGHT = Mm(297)
MARGIN_TOP = Mm(37)
MARGIN_BOTTOM = Mm(35)
MARGIN_LEFT = Mm(28)
MARGIN_RIGHT = Mm(26)

# 行距
BODY_LINE_SPACING = Pt(28)

# 首行缩进（2 个三号字 = 2 × 16pt × 0.35mm/pt ≈ 2 × 5.6mm）
FIRST_LINE_INDENT = Pt(32)

# 字体配置：role → (eastAsia_font, ascii_font, size_pt, bold)
FONT_CONFIG = {
    "title":       {"ea": "FZXiaoBiaoSong", "ascii": "Times New Roman", "size": 22, "bold": False},
    "doc_number":  {"ea": "KaiTi",          "ascii": "Times New Roman", "size": 16, "bold": False},
    "body":        {"ea": "FangSong",       "ascii": "Times New Roman", "size": 16, "bold": False},
    "heading1":    {"ea": "SimHei",         "ascii": "Times New Roman", "size": 16, "bold": False},
    "heading2":    {"ea": "KaiTi",          "ascii": "Times New Roman", "size": 16, "bold": False},
    "heading3":    {"ea": "FangSong",       "ascii": "Times New Roman", "size": 16, "bold": True},
    "recipient":   {"ea": "FangSong",       "ascii": "Times New Roman", "size": 16, "bold": False},
    "attachment":  {"ea": "FangSong",       "ascii": "Times New Roman", "size": 16, "bold": False},
    "signature":   {"ea": "FangSong",       "ascii": "Times New Roman", "size": 16, "bold": False},
    "cc":          {"ea": "FangSong",       "ascii": "Times New Roman", "size": 14, "bold": False},
    "page_number": {"ea": "SimSun",         "ascii": "Times New Roman", "size": 14, "bold": False},
}

# 标题字体回退（方正小标宋简体通常未安装）
TITLE_FONT_FALLBACK_EA = "SimSun"
TITLE_FONT_FALLBACK_BOLD = True

# 公文字类型配置
DOC_TYPE_CONFIG = {
    "通知": {"has_recipient": True,  "has_quotation": False, "default_closing": None},
    "报告": {"has_recipient": True,  "has_quotation": False, "default_closing": "特此报告。"},
    "请示": {"has_recipient": True,  "has_quotation": False, "default_closing": "妥否，请批示。"},
    "批复": {"has_recipient": True,  "has_quotation": True,  "default_closing": "此复。"},
    "函":   {"has_recipient": False, "has_quotation": False, "default_closing": None},
}

# 中文标题编号正则（裸数字编号不在此判定，由 parse_body 启发式区分列表/三级标题）
HEADING_PATTERNS = [
    (re.compile(r"^[一二三四五六七八九十百]+、"), "h1"),
    (re.compile(r"^[（(][一二三四五六七八九十百]+[）)]"), "h2"),
]

# 列表标记正则
UL_PATTERN = re.compile(r"^[-*+]\s+(.+)$")
OL_PATTERN = re.compile(r"^(\d+)[\.、]\s+(.+)$")

# 行内格式正则
BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")
ITALIC_PATTERN = re.compile(r"\*(.+?)\*")


# ============================================================
# 字体检测
# ============================================================

_title_font_available = None

def check_title_font():
    """检测方正小标宋简体是否可用"""
    global _title_font_available
    if _title_font_available is not None:
        return _title_font_available

    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
        )
        i = 0
        while True:
            try:
                name, _, _ = winreg.EnumValue(key, i)
                if "xiaobiao" in name.lower() or "小标宋" in name:
                    winreg.CloseKey(key)
                    _title_font_available = True
                    return True
                i += 1
            except OSError:
                break
        winreg.CloseKey(key)
    except OSError:
        pass

    _title_font_available = False
    return False


def get_title_font():
    """获取标题字体配置，含回退逻辑"""
    if check_title_font():
        return FONT_CONFIG["title"]
    else:
        cfg = dict(FONT_CONFIG["title"])
        cfg["ea"] = TITLE_FONT_FALLBACK_EA
        cfg["bold"] = TITLE_FONT_FALLBACK_BOLD
        return cfg


# ============================================================
# 解析层
# ============================================================

def parse_frontmatter(text, input_path=None):
    """
    拆分 YAML frontmatter 和正文，返回 (metadata, body_text)
    如果没有 frontmatter，使用输入文件名（去除扩展名）作为 title
    """
    text = text.strip()

    # 尝试解析 frontmatter
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            yaml_text = text[3:end].strip()
            body = text[end + 4:].strip()
            try:
                metadata = yaml.safe_load(yaml_text)
                if isinstance(metadata, dict):
                    # 将日期对象转换为字符串
                    for key, value in metadata.items():
                        if isinstance(value, (int, float, str, bool, type(None), list)):
                            continue
                        elif hasattr(value, 'isoformat'):  # datetime/date 对象
                            metadata[key] = value.isoformat()
                        elif not isinstance(value, dict):
                            metadata[key] = str(value)
                    return metadata, body
            except yaml.YAMLError:
                pass  # YAML 解析失败，继续使用无 frontmatter 模式

    # 没有 frontmatter 或解析失败，使用默认 metadata
    if input_path:
        # 从文件名推导标题
        default_title = Path(input_path).stem
    else:
        default_title = "未命名文档"

    metadata = {
        "title": default_title,
        "_no_frontmatter": True,  # 标记这是自动生成的 frontmatter
    }
    return metadata, text


def classify_line_raw(line):
    """
    判断单行的公文类型（保留缩进信息，识别列表）。
    裸有序编号先标为 ordered_candidate，由 parse_body 二次判定是列表还是三级标题。
    """
    # 行首缩进空格数 → 列表层级
    left_stripped = line.lstrip(" ")
    indent_spaces = len(line) - len(left_stripped)
    text = left_stripped.rstrip()
    if not text:
        return {"type": "blank", "text": ""}

    # 1) Markdown # 标题
    md_match = re.match(r"^(#{1,6})\s+(.+)$", text)
    if md_match:
        hashes = md_match.group(1)
        inner = md_match.group(2).strip()
        # 带 # 前缀的数字编号 → 三级标题（明确语义，不走启发式）
        if OL_PATTERN.match(inner):
            return {"type": "h3", "text": inner}
        for pattern, level in HEADING_PATTERNS:
            if pattern.match(inner):
                return {"type": level, "text": inner}
        # 普通 ## 节标题
        return {"type": "section_heading", "text": inner, "md_level": len(hashes)}

    # 2) 无 # 前缀
    ul_match = UL_PATTERN.match(text)
    if ul_match:
        return {"type": "list_item", "ordered": False,
                "level": indent_spaces // 2, "marker": "-",
                "text": ul_match.group(1)}

    ol_match = OL_PATTERN.match(text)
    if ol_match:
        return {"type": "ordered_candidate",
                "level": indent_spaces // 2,
                "marker": ol_match.group(1) + ".",
                "text": ol_match.group(2)}

    # 裸中文编号
    for pattern, level in HEADING_PATTERNS:
        if pattern.match(text):
            return {"type": level, "text": text}

    return {"type": "paragraph", "text": text}


def _nearest_non_blank(elements, idx, direction):
    """从 idx 向 direction 方向查找最近的非 blank 元素"""
    j = idx + direction
    while 0 <= j < len(elements):
        if elements[j]["type"] != "blank":
            return elements[j]
        j += direction
    return None


def _is_list_item(elem):
    """元素是否为列表项（含有序候选，使连续编号互相确认）"""
    if elem is None:
        return False
    return elem["type"] in ("list_item", "ordered_candidate")


def parse_body(body_text):
    """
    解析正文 Markdown 为结构化元素列表（两遍）。
    第二遍用相邻行启发式：有序编号若紧邻其他列表项则为有序列表，否则为三级标题。
    """
    elements = [classify_line_raw(line) for line in body_text.split("\n")]

    for i, elem in enumerate(elements):
        if elem["type"] != "ordered_candidate":
            continue
        prev_nb = _nearest_non_blank(elements, i, -1)
        next_nb = _nearest_non_blank(elements, i, +1)
        if _is_list_item(prev_nb) or _is_list_item(next_nb):
            elem["type"] = "list_item"
            elem["ordered"] = True
        else:
            elem["type"] = "h3"
    return elements


def parse_inline_formatting(text):
    """
    拆分行内格式为片段列表。
    支持的 Markdown 格式：**粗体**，*斜体*，`代码`（保留原样）
    返回 [(text, bold, italic), ...]
    """
    segments = []

    # 优先处理粗体 **text**，然后处理斜体 *text*
    # 使用 finditer 从左到右处理所有匹配
    pos = 0
    combined = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*)")

    for match in combined.finditer(text):
        # 匹配前的普通文本
        if match.start() > pos:
            segments.append((text[pos:match.start()], False, False))

        matched = match.group(1)
        if matched.startswith("**") and matched.endswith("**"):  # **bold**
            segments.append((matched[2:-2], True, False))
        elif matched.startswith("*") and matched.endswith("*"):  # *italic*
            segments.append((matched[1:-1], False, True))

        pos = match.end()

    # 剩余普通文本
    if pos < len(text):
        segments.append((text[pos:], False, False))

    if not segments:
        segments = [(text, False, False)]

    return segments


# ============================================================
# 文档构建层
# ============================================================

def setup_page(doc):
    """设置页面尺寸和边距"""
    section = doc.sections[0]
    section.page_width = PAGE_WIDTH
    section.page_height = PAGE_HEIGHT
    section.orientation = WD_ORIENT.PORTRAIT
    section.top_margin = MARGIN_TOP
    section.bottom_margin = MARGIN_BOTTOM
    section.left_margin = MARGIN_LEFT
    section.right_margin = MARGIN_RIGHT


def set_font(run, font_config, bold_override=None):
    """设置 run 的字体（包括 East Asian 字体）"""
    run.font.size = Pt(font_config["size"])
    is_bold = bold_override if bold_override is not None else font_config.get("bold", False)
    run.font.bold = is_bold
    run.font.name = font_config["ascii"]

    # 设置 East Asian 字体 — 这是中文排版的关键
    r_elem = run._element
    rPr = r_elem.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:eastAsia"), font_config["ea"])
    rFonts.set(qn("w:ascii"), font_config["ascii"])
    rFonts.set(qn("w:hAnsi"), font_config["ascii"])


def set_paragraph_spacing(paragraph, before_pt=0, after_pt=0, line_spacing=None, line_rule=None):
    """设置段落间距"""
    pf = paragraph.paragraph_format
    pf.space_before = Pt(before_pt)
    pf.space_after = Pt(after_pt)
    if line_spacing is not None:
        pf.line_spacing = line_spacing
        pf.line_spacing_rule = line_rule


def add_empty_paragraph(doc, font_config=None, height_pt=16):
    """添加空行段落"""
    p = doc.add_paragraph()
    if font_config:
        run = p.add_run()
        run.font.size = Pt(height_pt)
        set_font(run, font_config)
    set_paragraph_spacing(p, before_pt=0, after_pt=0, line_spacing=Pt(height_pt),
                          line_rule=4)  # WD_LINE_SPACING.EXACTLY = 4
    return p


def add_title(doc, title_text):
    """添加公文标题（居中，二号）"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_spacing(p, before_pt=0, after_pt=0)

    title_cfg = get_title_font()
    run = p.add_run(title_text)
    set_font(run, title_cfg)
    return p


def add_doc_number(doc, number):
    """添加发文字号（居中，楷体三号）"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_spacing(p, before_pt=0, after_pt=0, line_spacing=BODY_LINE_SPACING,
                          line_rule=4)

    run = p.add_run(number)
    set_font(run, FONT_CONFIG["doc_number"])
    return p


def add_red_line(doc):
    """
    添加红线 — 使用段落底部边框模拟。
    红线位于发文字号之下、主送机关之上。
    """
    p = doc.add_paragraph()
    set_paragraph_spacing(p, before_pt=0, after_pt=0, line_spacing=Pt(4), line_rule=4)

    # 添加底部边框
    pPr = p._element.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")

    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "24")  # 约 3pt 粗
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "FF0000")
    pBdr.append(bottom)

    pPr.append(pBdr)
    return p


def add_recipient(doc, recipient_text):
    """添加主送机关（左对齐，顶格，仿宋三号）"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    set_paragraph_spacing(p, before_pt=0, after_pt=0, line_spacing=BODY_LINE_SPACING,
                          line_rule=4)

    run = p.add_run(recipient_text)
    set_font(run, FONT_CONFIG["recipient"])
    return p


def add_quotation(doc, reference_doc):
    """添加批复引用语"""
    text = f"{reference_doc}。经研究，现批复如下："
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.first_line_indent = FIRST_LINE_INDENT
    set_paragraph_spacing(p, before_pt=0, after_pt=0, line_spacing=BODY_LINE_SPACING,
                          line_rule=4)

    run = p.add_run(text)
    set_font(run, FONT_CONFIG["body"])
    return p


def add_body_paragraph(doc, text):
    """添加正文段落（仿宋三号，首行缩进，28pt 固定行距）"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.first_line_indent = FIRST_LINE_INDENT
    set_paragraph_spacing(p, before_pt=0, after_pt=0, line_spacing=BODY_LINE_SPACING,
                          line_rule=4)

    # 处理行内格式
    segments = parse_inline_formatting(text)
    for seg_text, bold, italic in segments:
        run = p.add_run(seg_text)
        set_font(run, FONT_CONFIG["body"], bold_override=bold)
        if italic:
            run.font.italic = True
    return p


def add_heading(doc, level, text):
    """添加公文层级标题"""
    level_map = {
        "h1": FONT_CONFIG["heading1"],
        "h2": FONT_CONFIG["heading2"],
        "h3": FONT_CONFIG["heading3"],
    }
    font_cfg = level_map.get(level, FONT_CONFIG["body"])

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.first_line_indent = FIRST_LINE_INDENT
    set_paragraph_spacing(p, before_pt=0, after_pt=0, line_spacing=BODY_LINE_SPACING,
                          line_rule=4)

    # 处理行内格式
    segments = parse_inline_formatting(text)
    for seg_text, bold, italic in segments:
        run = p.add_run(seg_text)
        set_font(run, font_cfg, bold_override=bold)
        if italic:
            run.font.italic = True
    return p


def add_section_heading(doc, text, md_level=2):
    """添加 Markdown ## 节标题（黑体三号，首行缩进2字符）"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf = p.paragraph_format
    pf.first_line_indent = FIRST_LINE_INDENT
    set_paragraph_spacing(p, before_pt=0, after_pt=0, line_spacing=BODY_LINE_SPACING,
                          line_rule=4)

    segments = parse_inline_formatting(text)
    for seg_text, bold, italic in segments:
        run = p.add_run(seg_text)
        set_font(run, FONT_CONFIG["heading1"], bold_override=bold)
        if italic:
            run.font.italic = True
    return p


def add_list_item(doc, text, level, ordered, marker):
    """添加列表项（仿宋三号，按层级缩进 + 悬挂缩进）"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf = p.paragraph_format
    pf.left_indent = Pt(32) * (level + 1)
    pf.first_line_indent = Pt(-16)
    set_paragraph_spacing(p, before_pt=0, after_pt=0, line_spacing=BODY_LINE_SPACING,
                          line_rule=4)

    prefix = f"{marker} " if ordered else "• "
    run = p.add_run(prefix)
    set_font(run, FONT_CONFIG["body"])

    segments = parse_inline_formatting(text)
    for seg_text, bold, italic in segments:
        run = p.add_run(seg_text)
        set_font(run, FONT_CONFIG["body"], bold_override=bold)
        if italic:
            run.font.italic = True
    return p


def add_closing(doc, closing_text):
    """添加结语段落（如"特此报告。"）"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.first_line_indent = FIRST_LINE_INDENT
    set_paragraph_spacing(p, before_pt=0, after_pt=0, line_spacing=BODY_LINE_SPACING,
                          line_rule=4)

    run = p.add_run(closing_text)
    set_font(run, FONT_CONFIG["body"])
    return p


def add_attachment_notice(doc, attachments):
    """添加附件说明"""
    if not attachments:
        return

    # "附件："标签
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf = p.paragraph_format
    pf.first_line_indent = FIRST_LINE_INDENT
    set_paragraph_spacing(p, before_pt=0, after_pt=0, line_spacing=BODY_LINE_SPACING,
                          line_rule=4)

    run = p.add_run("附件：")
    set_font(run, FONT_CONFIG["attachment"])

    # 附件列表
    if isinstance(attachments, list):
        for i, att in enumerate(attachments):
            suffix = "\n" if i < len(attachments) - 1 else ""
            att_text = str(att)
            if not att_text.startswith("附件"):
                att_text = f"附件{i + 1}：{att_text}"
            run = p.add_run(att_text + suffix)
            set_font(run, FONT_CONFIG["attachment"])
    else:
        # 单个附件（字符串）
        run = p.add_run(str(attachments))
        set_font(run, FONT_CONFIG["attachment"])


def add_signature(doc, issuer, date_str):
    """添加落款（发文机关 + 日期，右对齐）"""
    # 发文机关
    p1 = doc.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    set_paragraph_spacing(p1, before_pt=0, after_pt=0, line_spacing=BODY_LINE_SPACING,
                          line_rule=4)
    if issuer:
        run = p1.add_run(issuer)
        set_font(run, FONT_CONFIG["signature"])

    # 成文日期
    if date_str:
        p2 = doc.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        set_paragraph_spacing(p2, before_pt=0, after_pt=0, line_spacing=BODY_LINE_SPACING,
                              line_rule=4)
        run = p2.add_run(date_str)
        set_font(run, FONT_CONFIG["signature"])


def add_cc(doc, cc_text):
    """添加抄送段落"""
    if not cc_text:
        return

    # 分隔线
    p_line = doc.add_paragraph()
    set_paragraph_spacing(p_line, before_pt=0, after_pt=0)
    pPr = p_line._element.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    top = OxmlElement("w:top")
    top.set(qn("w:val"), "single")
    top.set(qn("w:sz"), "6")
    top.set(qn("w:space"), "1")
    top.set(qn("w:color"), "000000")
    pBdr.append(top)
    pPr.append(pBdr)

    # 抄送内容
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    set_paragraph_spacing(p, before_pt=0, after_pt=0)

    run = p.add_run(f"抄送：{cc_text}")
    set_font(run, FONT_CONFIG["cc"])


def add_page_numbers(doc):
    """添加页脚页码"""
    section = doc.sections[0]
    footer = section.footer
    footer.is_linked_to_previous = False

    # 清空已有内容
    for p in footer.paragraphs:
        p.clear()

    p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 插入 PAGE 域代码
    run = p.add_run()
    set_font(run, FONT_CONFIG["page_number"])

    fld_char_begin = OxmlElement("w:fldChar")
    fld_char_begin.set(qn("w:fldCharType"), "begin")
    run._element.append(fld_char_begin)

    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    run._element.append(instr)

    fld_char_end = OxmlElement("w:fldChar")
    fld_char_end.set(qn("w:fldCharType"), "end")
    run._element.append(fld_char_end)


# ============================================================
# 文档组装
# ============================================================

def build_document(metadata, body_elements):
    """按公文格式组装完整文档"""
    doc = Document()
    setup_page(doc)

    # 检查是否为普通文档模式（无 frontmatter）
    is_plain_doc = metadata.get("_no_frontmatter", False)

    doc_type = metadata.get("doc_type", "")
    type_config = DOC_TYPE_CONFIG.get(doc_type, {
        "has_recipient": True, "has_quotation": False, "default_closing": None
    })

    # 1. 标题
    title = metadata.get("title", "")
    if title:
        add_title(doc, title)

    if not is_plain_doc:
        # === 公文特有元素 ===

        # 2. 空行
        add_empty_paragraph(doc, FONT_CONFIG["body"])

        # 3. 发文字号
        doc_number = metadata.get("doc_number", "")
        if doc_number:
            add_doc_number(doc, doc_number)

        # 4. 红线
        add_red_line(doc)

        # 5. 主送机关
        recipient = metadata.get("recipient", "")
        if recipient and type_config.get("has_recipient", True):
            add_recipient(doc, recipient)

        # 6. 引用语（仅批复）
        if type_config.get("has_quotation") and metadata.get("reference_doc"):
            add_quotation(doc, metadata["reference_doc"])
    else:
        # === 普通文档模式：只添加一个空行 ===
        add_empty_paragraph(doc, FONT_CONFIG["body"])

    # 7. 正文
    closing_in_body = None
    for elem in body_elements:
        if elem["type"] == "blank":
            continue
        elif elem["type"] in ("h1", "h2", "h3"):
            add_heading(doc, elem["type"], elem["text"])
        elif elem["type"] == "section_heading":
            add_section_heading(doc, elem["text"], elem.get("md_level", 2))
        elif elem["type"] == "list_item":
            add_list_item(doc, elem["text"], elem["level"],
                          elem.get("ordered", False), elem.get("marker", ""))
        elif elem["type"] == "paragraph":
            text = elem["text"]
            # 检测是否为结语行（如"此复。""特此报告。"）
            stripped = text.rstrip()
            if stripped in ("此复。", "特此报告。", "妥否，请批示。",
                           "特此通知。", "特此函达。", "特此函复。"):
                closing_in_body = stripped
                continue
            add_body_paragraph(doc, text)

    if not is_plain_doc:
        # === 公文特有元素 ===

        # 8. 结语（如果正文中未出现，且类型配置有默认结语）
        default_closing = type_config.get("default_closing")
        if closing_in_body:
            add_closing(doc, closing_in_body)
        elif default_closing:
            add_closing(doc, default_closing)

        # 9. 附件说明
        attachments = metadata.get("attachments")
        if attachments:
            add_attachment_notice(doc, attachments)

        # 10. 落款
        issuer = metadata.get("issuer", "")
        date_str = metadata.get("date", "")
        if issuer or date_str:
            add_signature(doc, issuer, date_str)

        # 11. 抄送
        cc = metadata.get("cc", "")
        if cc:
            add_cc(doc, cc)

    # 12. 页码（公文和普通文档都有）
    add_page_numbers(doc)

    return doc


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="将 Markdown 文件转换为符合 GB/T 9704-2012 标准的公文 DOCX"
    )
    parser.add_argument("input", help="输入 Markdown 文件路径")
    parser.add_argument("-o", "--output", help="输出 DOCX 文件路径（默认: 输入文件同目录、同名 .docx）")
    parser.add_argument("--verbose", action="store_true", help="显示详细处理信息")
    args = parser.parse_args()

    # 读取输入文件
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误: 文件不存在: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    # 解析 frontmatter
    metadata, body = parse_frontmatter(text, input_path)

    # 如果没有 frontmatter，使用普通文档模式（仅应用字体样式）
    is_plain_doc = metadata.get("_no_frontmatter", False)

    if args.verbose:
        print(f"[INFO] 标题: {metadata.get('title', '')}")
        print(f"[INFO] 类型: {metadata.get('doc_type', '未指定')}")
        if is_plain_doc:
            print(f"[INFO] 模式: 普通文档（仅应用公文字体样式）")

    # 字体检测
    if not check_title_font():
        print("警告: 方正小标宋简体未安装，标题使用宋体+加粗替代。", file=sys.stderr)
        print("      如需标准字体，请安装方正小标宋简体。", file=sys.stderr)

    # 解析正文
    body_elements = parse_body(body)

    if args.verbose:
        para_count = sum(1 for e in body_elements if e["type"] == "paragraph")
        head_count = sum(1 for e in body_elements if e["type"] in ("h1", "h2", "h3"))
        print(f"[INFO] 正文段落数: {para_count}, 标题数: {head_count}")

    # 构建文档
    doc = build_document(metadata, body_elements)

    # 确定输出路径（未指定时：与输入文件同目录、同名 .docx）
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix(".docx")

    # 创建输出目录
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 保存
    doc.save(str(output_path))

    # 统计
    total_chars = sum(len(e.get("text", "")) for e in body_elements)
    total_paras = sum(1 for e in body_elements if e["type"] in
                      ("paragraph", "h1", "h2", "h3", "section_heading", "list_item"))

    print(f"[OK] 转换完成: {output_path}")
    print(f"     字符数: {total_chars}")
    print(f"     段落数: {total_paras}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
