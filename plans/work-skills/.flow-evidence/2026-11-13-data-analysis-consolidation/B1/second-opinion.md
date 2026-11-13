# B1 独立第二意见评审（冷启动可用性）

说明：第二意见代理只读契约未落盘，本报告由主控原样落盘（全文无增删）。总体判断：**修后可用**。必修项已由主控处置（见 master-remediation.md）。

# data-analysis 技能第二意见评审（T3 双重验证 · 只读）

对象：plugins/work-skills/skills/data-analysis/。已实读 SKILL.md、三个 mode、引擎文档、方案第 2 节，抽查 5 capability + 3 doc-capability 子技能，路径解析用 python normpath 实证。

## 维度 1 · 入口路由 — 通过，两处低危口径差

混合输入（Excel+截图）：规则 1"各自路由后汇总"明确无歧义。纯触发词：规则 2 按组匹配可决策；无文件时进 mode 后自然向用户要文件。互斥边界指向的 anydoc-to-md、write-report 均实际存在（已 ls 验证）。扫描 PDF：document.md Universal Rules → "Image Content via Visual Reading" 节 → image.md 指引，链路完整且 pdf-analysis 内有可执行的 fitz 渲染方法（render_scanned_pdf_pages，104-117 行）。

- 低：SKILL.md:37 路由表图片行限定"+数据提取"，而触发词③含"图片描述/识别图片"（无提取意图）。"看看这张图"按表不入行、按规则 2 入 image mode，两读法最终收敛，仅轻微犹豫，不误路由。
- 低：大文件门口径三处微差——SKILL.md:35/38 称"≥10k 转入引擎档"，excel.md Step 2 仅 ≥100k 强制读引擎，引擎文档头（large-file-engine.md:8）称"≥10k MUST use this document"。行为收敛（10k-100k 内联代码与引擎 Method 3 同型），无失败风险。

## 维度 2 · mode 契约自包含 — 基本通过

excel.md 六步齐全，每步 `→ capability:` 指针全部实存；44 子技能索引与目录逐类计数一致（47=44+3 守恒，find 实证）。image.md 无 caption 残留（全树 grep "caption" 在 modes/ 零命中），`read_image_and_extract` 为带注释伪代码，可理解。document.md 三步 + MUST/NEVER 清单自洽。

- 中：CSV 承诺无内容支撑。SKILL.md:35 路由表与触发词⑤均含 .csv，但 excel.md 六步全 openpyxl/pandas.read_excel 语境，Step 1 代码读 .csv 直接抛异常；引擎档也无 read_csv(chunksize=) 等价物。会话可自救，冷启动首次必失败。
- 低：image.md:121 `chr(64 + i)` 超过 26 列时列宽字母越界（潜在 bug，随迁遗留）。
- 低：加载占位符三种写法混用（SKILL.md:55 skills_root / excel.md:46 skills_base / excel.md:180 base_path）。

## 维度 3 · 大文件引擎衔接 — 通过

excel.md Step 2 的 `../references/large-file-engine.md` 相对路径解析正确（modes/ 与 references/ 同级），≥100k 行 STOP+read_file 指令可执行；引擎文档第 3 行头部入口指引在位。核心方法路径无关，本机可用。仅阈值口径差见维度 1。

## 维度 4 · 本机适配缺口 — Executor 自报属实，独立定级如下

- **高**：字体块两条——excel.md:153-172 与 large-file-engine.md:34-53。5 个候选路径全为 Linux/云沙箱（/mnt/afs_agents、/usr/share/fonts 等），Windows 零命中 → for 循环静默不设字体，**所有含中文的 matplotlib 图表输出乱码**；且文档明令"copy as-is / Do NOT search for fonts"，主动阻断会话自救。image.md:85 单 wqy 路径同理（if exists 静默跳过）。必须改：补 `C:/Windows/Fonts/simhei.ttf`、`msyh.ttc` 等候选。
- 中：写出路径——excel.md:128 `/mnt/data/result.xlsx`、image.md:100/102/110/133（chart.png、result.xlsx、glob 输入）、excel.md:54 `/tmp/_auto_parquet.parquet`。原生 Windows Python 首次写出必 FileNotFoundError；会话可自愈（换工作目录），但"copy as-is"语境使失败成为常态。建议改相对路径。
- 低（可容忍）：document.md:17 为带 `# from user` 注释的占位示例；5 个 capability 子技能及 ppt/word 内的 /mnt/ 示例路径——会话天然以用户实际路径替换，不构成阻断。

## 维度 5 · 子技能树健康度 — 两处中危

- 中：**decision 7 改写的 4 个文件相对路径全部差一级**（python normpath 实证目标不存在）：doc-capability 三件多处 `../modes/image.md`（pdf:111/133/146/159/205/282，word:181/186/204，ppt:178/224）解析到不存在的 `doc-capability/modes/image.md`，应为 `../../modes/image.md`；table-theme-styling/SKILL.md:12/14 `../../references/large-file-engine.md` 解析到 `capability/references/`，应为 `../../../`。会话可 glob 自救，但按字面 read_file 必失败——恰是本次改写新引入的断点。
- 中：`capability/excel-cell-coloring.md` 与 `capability/excel-conditional-formatting.md` 两个游离文件内容为字面 "404: Not Found"（旧库垃圾随迁，无任何引用方）。按仓库目录约定属污染，应删除。
- 低：25 个子技能头部 "see the parent workflow SKILL.md" 过期；ppt-analysis `needs_caption` 仅为自洽内部变量名；percentage-calculation/range-reading 等 frontmatter 旧 name 措辞为惰性残留；basic-statistics description 有"基础统计与，"断句错字。

## 总体判断：修后可用

建议下一步小修（不动结构）：① 两处字体块补 Windows 候选路径（高）；② 修 4 个文件的 ../ 层级断点（中）；③ 示例写出路径去 /mnt、/tmp 化（中）；④ 删 2 个 404 垃圾文件（中）；⑤ excel.md 补一行 CSV 读取提示（中低，可选）。无需返工。
