# B1 委派单：data-analysis 组建（sn-da 四合一）

- 方案：plans/work-skills/2026-11-13-data-analysis-consolidation.md（详案第 2 节 B1，含设计决策 1-7 与改动清单 1-6——**先通读方案全文再动工**，方案是唯一契约）
- 证据目录：plans/work-skills/.flow-evidence/2026-11-13-data-analysis-consolidation/B1/
- 仓库：C:\Users\tuzhe\runspace\rulertu-flow（Windows Git Bash），技能源在 plugins/work-skills/skills/
- 纪律：**不 git commit**；git mv 保 rename 追踪；只动边界内文件；先建 data-analysis/ 父目录再 mv

## 执行要点（方案之外的补充）

1. **改动顺序建议**：先建目录 + git mv 两棵子技能树与四份 SKILL.md（纯 rename）→ 改写四份文档 → 处置决策 7 的 4 个文件 → git rm caption.py → 新写 SKILL.md → 源目录清零核验。
2. **决策 7 的 4 个文件处置精度**：
   - `capability/excel-table-styling/table-theme-styling/SKILL.md` 12/14 行：注释里"若已加载 sn-da-large-file-analysis 技能"语境 → 改为"若为大文件场景，先按 `../../references/large-file-engine.md` 转换 Parquet"（相对路径按该文件实际层级计算，逐字核对）。
   - doc 三件的 `CAPTION = ".../sn-da-image-caption/scripts/caption.py"` 代码段：删除死常量及其调用行，原位改为注释指引（`# 图片理解：由会话视觉直读完成，流程见 ../modes/image.md`——相对路径按实际层级）。
3. **image.md 改写核心**：数据源改为"用 Read 工具直接读图片（会话原生视觉）"；SKILL.md 原 107-229 行管道（Parsing/Visualization/Export/Multi-Image）中的解析逻辑保留但把"caption 文本"输入改为"视觉读图输出"；95-105 行 Prompt Strategy 的五类图片（chart/table/UI/diagram/general）转写为一个"视觉提取指引"小节（每类 2-3 句提取要点）；231-238 行 Common Pitfalls 四条 caption 专属指引删除，"Timeout"条可改写为"大图（>5MB）先压缩再读"提示。
4. **excel.md 大文件门四处**：45/49/99/143 行全部改为指向 `references/large-file-engine.md`；49 行的 `read_file(path="<skills_base>/sn-da-large-file-analysis/SKILL.md")` 伪代码同步改路径。
5. **SKILL.md 新写**：路由表按扩展名——`.xlsx/.xls/.csv` → modes/excel.md（≥10k 行时 excel.md 内部转 large-file 档）；`.docx/.doc/.pdf/.pptx/.ppt` → modes/document.md；`.png/.jpg/.jpeg/.gif/.webp/.bmp` + 数据提取 → modes/image.md；触发词四组合并 + 互斥边界（图片编辑/生成不归、格式转换归 anydoc-to-md、报告成稿改写归 write-report）；capability（44）与 doc-capability（3）索引。

## 冒烟执行（方案"如何验证"L2/L3）

- **excel 冒烟**：用 python openpyxl 在证据目录生成小 xlsx（2 Sheet：Sheet1 销售数据 20 行、Sheet2 汇总表），然后以被测者身份只读 data-analysis 文档执行分析（真跑 pandas），产物落证据目录 smoke-excel-result.md。
- **image 冒烟**：用 matplotlib 生成一张含表格的 png（3×4 数据表+标题，中文字体注意），只读文档执行提取，产物落 smoke-image-result.md；**断言全程零外部 API 调用**（无 SN_API_KEY/network 到 sensenova）。
- **路由推演 7 条**：subagent 只读 data-analysis/SKILL.md，对 7 条用户消息输出路由决策（4 正例：xlsx 分析 / pdf 发票提取 / 截图表格转 Excel / 百万行大文件；3 边界：图片编辑请求应拒、"把这个 PDF 转成 Markdown"应指 anydoc-to-md、"帮我改写这份报告"应指 write-report）。决策文本落 raw-routing.md。

## 定向验证映射

| 锚点 | 验证 |
|---|---|
| 目录搬迁 | git porcelain rename 追踪；除决策 7 的 4 个文件外 staged diff 零行变化 |
| 旧名清零 | `grep -rn "sn-da-" skills/data-analysis/` 零命中 |
| 外部依赖清零 | `grep -rin "sensenova\|SN_API_KEY\|SN_VISION\|SN_CHAT" skills/data-analysis/` 零命中 |
| 入口约束 | `wc -l data-analysis/SKILL.md` ≤ 200；四组触发词 + 互斥边界在 description |
| 计数守恒 | capability 44 + doc-capability 3 = 47 个 SKILL.md |
| 顶层清零 | `ls \| grep sn-da` 零输出 |
| 冒烟与推演 | 3 项产物落证据目录 |

## 回报要求

- 完整日志写 `evidence/B1/executor-log.md`：改动清单（rename 记录）、决策 7 处置明细、每条验收命令与退出码、3 项冒烟产物与断言结果。
- 发现现状与方案锚点不符时停下上报，不自行扩改。
