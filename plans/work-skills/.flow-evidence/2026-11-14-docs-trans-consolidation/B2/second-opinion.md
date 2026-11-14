# B2 独立第二意见评审（冷启动可用性）

说明：第二意见代理只读契约未落盘，本报告由主控原样落盘（全文无增删）。总体判断：**可直接使用**。两个「中」项已由主控当日修复（见 master-remediation-B2.md）。

# gongwen-trans 升级独立第二意见评审（T3 第二意见，只读）

范围：plugins/work-skills/skills/gongwen-trans/（SKILL.md 156 行、references/gbt9704-reference.md、scripts/gongwen-to-docx.py、scripts/gongwen-to-pdf.py），对照 plans/work-skills/2026-11-14-docs-trans-consolidation.md B2 节。全部结论基于逐行读取原文，未运行脚本（文档/接口层面核验）。

## 维度 1：双格式路由清晰度 — 通过，一处措辞歧义

- 三种表述均可无歧义决策：无格式"生成公文"→默认 DOCX（SKILL.md:32"否则默认 DOCX"，与 description:11"未指定时…同名 .docx"同步）；明确 docx→:23；明确 pdf→:26 + description 触发词"生成公文 pdf/公文转 pdf/红头文件 pdf"。「输出格式」节（38-44）与 frontmatter description 一致。
- 【中】SKILL.md:32"用户明确要求 PDF（或 `--pdf`）时"——反引号 `--pdf` 形态强烈暗示 CLI 标记，但两脚本均无该参数（docx 脚本仅 input/-o/--verbose，pdf 脚本仅 input/--output/--keep-docx）。此为计划 B2 决策 3 原文措辞直译。冷启动 agent 可能先试 `--pdf` 得 argparse 报错再回退用法节自纠，不阻断但应改为"（或消息中出现 pdf 字样）"之类。

## 维度 2：脚本接口一致性 — 通过（除上述 `--pdf`）

- SKILL.md:23 用法与 gongwen-to-docx.py:751-753 argparse 逐项吻合；:26 用法与 gongwen-to-pdf.py:90-96 逐项吻合。
- --keep-docx 语义：SKILL.md:42（.md 链式默认删中间 docx、--keep-docx 保留、.docx 输入原文件永不删）与脚本 121-138 行及 argparse help 三方一致。
- 【中】--keep-docx 保留的文件名是 `<stem>.gongwen-tmp.docx`（gongwen-to-pdf.py:124），SKILL.md:42 未披露该命名。用户要"保留 docx"却拿到带 .gongwen-tmp 中缀的文件，agent 无从预告。
- 【低】转换失败路径（convert_docx_to_pdf sys.exit(1)）不清理中间 docx，失败后残留 .gongwen-tmp.docx。

## 维度 3：错误路径 — 基本可用，两处小瑕

- Word 不可用：前置检测提示"需要 Microsoft Word…请先安装"，SKILL.md:43 与常见问题表:151 同步，可自救。
- 文件占用：提示"docx 文件被其他程序占用"；【低】但被锁的也可能是输出 pdf（阅读器占用），归因单一可能误导。
- 【低】pywin32 缺失时先打"pip install pywin32"（:31）随后仍打"请先安装 Microsoft Word"（:111-112），两条矛盾提示并列，第二条误导。
- 【低】gongwen-to-docx.py:762 硬编码 utf-8 读入，非 utf-8 输入抛裸 UnicodeDecodeError，常见问题表未列编码项。
- 中间 docx 生成失败：透传子进程 stderr + 退出码，可诊断。

## 维度 4：与 docs-trans 边界 — 通过

双侧互指：本技能 SKILL.md:44 明写"普通（非公文）文档转 PDF 归 docs-trans 的 md-to-pdf mode"；docs-trans/SKILL.md:31 及其 description 反向指回 gongwen-trans。plugins/ 下 grep "gongwen-docx" 零残留命中，git 状态确认旧目录整体 rename，不构成冷启动歧义。

## 维度 5：链式调用接口兼容 — 通过

gongwen-to-pdf.py:52 `[sys.executable, script, md, "-o", docx]` 与 gongwen-to-docx.py:751-752（positional input + `-o/--output`）完全匹配；gongwen-to-docx.py 随迁零改动（git 纯 R）。中间 docx 临时名防覆盖（:123-124）已实现，与主控修复声明相符。

佐证：依赖节与两脚本 import 一致；gbt9704-reference.md 随迁零改动，其规格数字与 SKILL.md 格式规范要点逐项一致（37/35/28/26mm、22pt 标题、16pt 仿宋、28pt 行距）。【低】B2 决策 4 写"requirements 新增 docx2pdf"，实际新旧目录均无 requirements.txt（依赖内联在 SKILL.md，冷启动不缺信息，仅计划留痕偏差）。

## 总体判断：可直接使用

五维度核心核验（路由、接口、边界、链式兼容、错误提示）全部通过，无阻断缺陷。两个「中」项（`--pdf` 措辞歧义、--keep-docx 产物命名未披露）属文档措辞/边角体验。
