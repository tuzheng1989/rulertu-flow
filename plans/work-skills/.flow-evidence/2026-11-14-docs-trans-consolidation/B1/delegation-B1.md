# B1 委派单：docs-trans 组建（四转换技能四合一）

- 方案：plans/work-skills/2026-11-14-docs-trans-consolidation.md（详案第 2 节 B1，含设计决策 1-6 与改动清单 1-5——**先通读方案全文再动工**，方案是唯一契约）
- 证据目录：plans/work-skills/.flow-evidence/2026-11-14-docs-trans-consolidation/B1/
- 仓库：C:\Users\tuzhe\runspace\rulertu-flow（Windows Git Bash），技能源在 plugins/work-skills/skills/
- 纪律：**不 git commit**；git mv 保 rename 追踪；只动边界内文件；先建 docs-trans/ 父目录再 mv

## 执行要点（方案之外的补充）

1. **改动顺序**：建父目录 → git mv 四棵 scripts 树 + mermaid-syntax.md + evals.json + 四份 SKILL.md（纯 rename）→ git rm 两 README → 删未追踪 __pycache__ → 改写四份 mode 文档 → 新写 SKILL.md → 源目录清零核验。
2. **mode 文档脚本路径改写是本批最高风险点**（上批决策 7 的 13 处死指针前车之鉴）：四份 mode 文档内所有脚本引用（`{baseDir}/scripts/...`、`../sn-search` 类相对路径、裸 scripts/ 路径）逐一改为 `scripts/<引擎子目录>/...` 新路径，**每处改完后用 python os.path 从该文件目录出发做 exists 断言**，全部通过才算完。已知待改：anydoc-to-md.md 的 4 个脚本引用、url-to-md.md 的 scripts/ 引用（bun 命令的 cwd 语境同步改 scripts/url/）、md-to-pdf.md 的 scripts/3py 与 assets/config 引用、html-to-pdf.md 的 convert.py/merge.py 引用。
3. **frontmatter 处理**：删 YAML frontmatter，正文最前加前缀行（`> 本文件为 docs-trans 的 <原名> mode（2026-11-14 组建）。入口与路由见 SKILL.md。`——描述性名，不写旧目录名字面）。
4. **SKILL.md 新写**：路由表按"输入 → 输出"——已有文档文件（Word/PPT/Excel/EPUB/RTF/扫描 PDF）→ anydoc-to-md mode；URL/网页 → url-to-md mode；.md 文件 → md-to-pdf mode；.html/. 幻灯片 → html-to-pdf mode；触发词四组 + 互斥边界（文档分析归 data-analysis、公文生成归 gongwen-trans、报告成稿归 write-report）；scripts 四子目录索引（anydoc/url/mdpdf/htmlpdf）。
5. **EvoCenter 旧语境**：anydoc mode 的"EvoCenter 专用"描述删改为本仓通用语境。

## 冒烟执行（方案"如何验证"L2）

- anydoc：openpyxl 造小 xlsx → 按 mode 文档转换出 md（产物落证据目录 smoke-anydoc/）
- md-to-pdf：造小 md 含一段 mermaid 代码块 → 转出 PDF（smoke-mdpdf/）；若 Mermaid 渲染依赖未装，按文档故障排除节如实记录（区分环境因素与路径断裂）
- html-to-pdf：造小 html → 转 PDF（smoke-htmlpdf/）
- url-to-md：真转 https://example.com 出 md（smoke-url/）；bun/依赖问题如实记录归因

判定原则同 B1 冒烟：验证"搬迁后可发现、可加载、正确启动"，环境性失败（依赖缺失）不算 B1 失败但必须归因记录。

## 路由推演（方案"如何验证"L3）

subagent 只读 docs-trans/SKILL.md，对 8 条消息输出路由决策（产物 raw-routing.md）：
1. 「把这个 Word 文档转成 Markdown」→ anydoc-to-md
2. 「抓取这个网页的内容存成 md」→ url-to-md
3. 「把我这份 markdown 笔记转成 PDF」→ md-to-pdf
4. 「这批 HTML 幻灯片合成一个 PDF」→ html-to-pdf
5. 「分析这份 PDF 的数据」→ data-analysis（互斥边界）
6. 「生成一份公文 docx」→ gongwen-trans（互斥边界）
7. 「帮我改写这份报告」→ write-report（互斥边界）
8. 「扫描版 PDF 转成可搜索文字」→ anydoc-to-md 的 OCR 路由

## 定向验证映射

| 锚点 | 验证 |
|---|---|
| 目录搬迁 | git porcelain rename 追踪；除 4 份 mode 文档外 staged diff 零行变化 |
| 旧路径引用清零 | 方案 L1 第一条 grep 零命中 |
| frontmatter 清零 | 方案 L1 第二条 grep 零命中 |
| 入口约束 | SKILL.md ≤ 200 行；四组触发词 + 互斥边界在 description |
| 脚本树守恒 | git ls-files 四技能原文件全集 vs docs-trans 新树逐一对账（含 vendor 内部 2 文件） |
| 顶层清零 | 方案 L1 第三条 ls 零输出 |
| 冒烟与推演 | 4 冒烟产物 + raw-routing.md 落证据目录 |

## 回报要求

- 完整日志写 `evidence/B1/executor-log.md`：改动清单（rename 记录）、脚本路径改写明细（每处附 exists 断言结果）、每条验收命令与退出码、4 冒烟归因结论。
- 发现现状与方案锚点不符时停下上报，不自行扩改。
