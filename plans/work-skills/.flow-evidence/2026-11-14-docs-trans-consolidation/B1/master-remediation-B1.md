# B1 主控修复与处置记录（双重验证后）

日期：2026-11-14。Auditor 判通过（P0/P1=0，P2=1）+ 第二意见判修后可用（3 高 5 中 4 低）。分歧实质：契约字面验收（含路径 exists 断言）无法捕获"文档命令 vs 脚本 CLI 逐字对账"层缺陷——第二意见的参数级核验（读 argparse 对照文档命令）补上了这个盲区。

**方法论沉淀（记档）**：exists 断言只验"文件存在"，不验"参数存在"。后续 mode/契约类改写批次的委派单应加一条：文档中的 CLI 命令示例须与脚本 argparse 逐参数对账（--help 输出比对）。

## 本批修复（主控直接实施，10 处）

| # | 修复 | 点位 | 对应发现 |
|---|---|---|---|
| 1 | merge.py CLI argparse 化：--delete-temp 开关默认 False（合并后默认保留输入 PDF——输入可能是用户存量文件）；convert.py 用内嵌 merge_pdfs 不受影响（已 grep 确认唯一调用方是 mode 文档示例） | scripts/htmlpdf/merge.py main() | 第二意见高 1（最急） |
| 2 | md-to-pdf.md 67 行 --output-dir → -o ./pdfs/output.pdf | modes/md-to-pdf.md | 第二意见高 2 |
| 3 | md-to-pdf.md 76 行 --output-dir → -o ./pdfs（--batch 真实保留） | 同上 | 第二意见高 2 |
| 4 | md-to-pdf.md 86-87 行页眉页脚假示例块 → 替换为 --config 真实用法示例 | 同上 | 第二意见高 2 + 中 6 |
| 5 | SKILL.md 路由表 md-to-pdf 行删"页眉页脚"宣称 | SKILL.md:16 | 第二意见高 3 |
| 6 | SKILL.md 新增「未覆盖方向」节：md→docx 等未列方向默认不支持（公文例外归 gongwen-trans） | SKILL.md | 第二意见中 4 |
| 7 | md-to-pdf.md 故障排除补「Mermaid 预渲染需网络」（jsdelivr CDN）+ --no-pre-render 同样需网络的说明 | 同上 | 第二意见中 5 |
| 8 | md-to-pdf.md 补 mermaid-syntax.md 引用一行（消解半孤儿） | 同上 | 第二意见低 12 |
| 9 | anydoc-to-md.md B 节头部加历史环境工作流警示行（inbox/素材处理/llm-wiki 未部署可跳过）+ OCR 路由优先级声明一行（自上而下第一条） | modes/anydoc-to-md.md | 第二意见中 7 部分 + 低 9 |
| 10 | html-to-pdf.md:102 output/exports 旧语境 → "遵循所在项目约定，未约定时输出到当前工作目录" | modes/html-to-pdf.md | 第二意见中 7 部分 |

**顺手修（Auditor P2-1 提前消化）**：references/mermaid-syntax.md:297 旧命令 `scripts/md_to_pdf.py` → `scripts/mdpdf/md_to_pdf.py`（本属 B3 改动清单，一行级提前修复；B3 兜底 grep 词表仍补下划线形态）。

修复后验证：merge.py ast 语法 OK + --help 正常 + 真跑合并（pypdf 造样 → merge.py 默认模式 → merged.pdf 产出且 in1/in2 保留 = 默认不删语义实证；3.11-arm64 + PyPDF2 新装）。md-to-pdf.md 假参数 grep 清零。

## executor-log / master-spot-check 勘误（Auditor P3-1/2）

- P3-1：executor-log "退出码 0" 系断言跑在 bun install 后、清理前的时点记录；终态应为 exit 1（1 条件 FAIL）。以本记录勘误，原文不改。
- P3-2：master-spot-check "39/40" 为我的断言脚本计数（含 node_modules 条件路径 1 项），Executor 原始计数 42/41/1。两计数口径不同（我合并了条件路径判定），结论一致，以 Auditor 复跑 42/41/1 为准。

## 记档不修（移交后续）

- P3-3 裸名/全路径风格不一致（描述性提及，非解析指针）。
- P3-4 mdpdf package.json npm scripts 失效 + executor-log 交叉引用悬空（记录瑕疵）。
- P3-5 install.py:45 断裂（树内零改动边界，留痕）。
- 第二意见低 10/11：触发词方向不匹配与模糊请求询问规则（SKILL.md 路由完备性打磨，后续小批）。
- 第二意见中 8：相邻技能反向链接——B3 计划内待办。

## 结论

3 高 + 4 中/低修复完成并验证，Auditor P2-1 提前消化。B1 达可收口状态：补提交剩余部分（4 mode 改写 + SKILL.md + 本批修复 + 证据）后进入 B3。
