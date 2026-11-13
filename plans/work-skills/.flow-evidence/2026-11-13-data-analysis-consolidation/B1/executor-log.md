# B1 执行日志：data-analysis 组建（sn-da 四合一）

- 执行者：Executor（B1 委派单）
- 日期：2026-11-13
- 仓库：C:\Users\tuzhe\runspace\rulertu-flow
- 纪律遵守：未 git commit；git mv 保 rename；边界外零触碰（.gitignore 与其他 untracked 为既有状态，未动）

## 一、改动清单

### 1. rename 搬迁（git mv，53 个文件）

| 源 | 目标 | 文件数 |
|---|---|---|
| sn-da-excel-workflow/capability/ | data-analysis/capability/ | 46（44 子 SKILL.md + 2 类别索引 md） |
| sn-da-non-spreadsheet-analysis/capability/ | data-analysis/doc-capability/ | 3（word/pdf/ppt-analysis） |
| sn-da-excel-workflow/SKILL.md | data-analysis/modes/excel.md | 1 |
| sn-da-non-spreadsheet-analysis/SKILL.md | data-analysis/modes/document.md | 1 |
| sn-da-image-caption/SKILL.md | data-analysis/modes/image.md | 1 |
| sn-da-large-file-analysis/SKILL.md | data-analysis/references/large-file-engine.md | 1 |

### 2. 删除与新增

- `git rm sn-da-image-caption/scripts/caption.py`（415 行，SenseNova 依赖，不随迁）
- 新写 `data-analysis/SKILL.md`（86 行）：frontmatter 四组触发词 + 互斥边界 + 输入类型路由表 + mode 定位 + capability/doc-capability 索引

### 3. 四份 mode/reference 文档改写（rename 后内容修改）

| 文件 | diff 规模 | 改动内容 |
|---|---|---|
| modes/excel.md | 19 行 | 删 frontmatter 加前缀行；四处大文件门（原 45/49/99/143 行）改指 `../references/large-file-engine.md`；49 行 read_file 伪代码同步改路径；capability base path（原 194 行）改 `data-analysis/capability/`；description 引 image-caption 随 frontmatter 删除消除 |
| modes/document.md | 65 行 | 删 frontmatter 加前缀行；doc 三件路由表与 read_file 伪代码、Available sub-skills 列表改 `doc-capability/` 路径；Caption Script 节改写为"Image Content via Visual Reading"指引节；MUST DO / NEVER DO 四条 caption 指引改视觉直读 |
| modes/image.md | 140 行 | 删 frontmatter 加前缀行；删 caption.py 用法节与 Calling from Python 节（原 16-94 行）；Prompt Strategy（原 95-105 行）转写为"视觉提取指引"（五类图片提取要点表 + 大图压缩/两段提取）；管道节保留（parse_markdown_table / Visualization / Export to Excel 原样），数据源改"Read 工具视觉直读"；Multi-Image 改为逐张直读后合并；Common Pitfalls 六条 → 五条（Always caption first → Always read the image first；Use --prompt 删除；two passes 改两段直读；Timeout → 大图 >5MB 先压缩；保留 Verify/Chinese font） |
| references/large-file-engine.md | 9 行 | 删 frontmatter 加前缀行（注明由 excel.md Step 2 大文件门进入）；标题 Skill → Engine；"in this skill" → "in this document" |

### 4. 决策 7 处置明细（4 个树内文件，其余 45 个树内文件零行变化）

| 文件 | 处置 |
|---|---|
| capability/excel-table-styling/table-theme-styling/SKILL.md | 12/14 行注释旧技能名引用 → "若为大文件场景，先按 ../../references/large-file-engine.md 转换 Parquet"（相对路径按实际层级核对：上两级至 data-analysis/ 再入 references/） |
| doc-capability/pdf-analysis/SKILL.md | description "嵌入图表 caption"→"视觉理解"；Core Method 3 标题/导语/函数改视觉直读（删 CAPTION 常量与 subprocess 调用段，原位注释指引"图片理解：由会话视觉直读完成，流程见 ../modes/image.md"，函数改 render_scanned_pdf_pages 返回 PNG 路径列表）；Core Method 4 混合 PDF 同法改写（图片页渲染收集、返回 image_pages）；56 行 / 220-222 行注释 / 299 行 Pitfalls 同步改直读表述 |
| doc-capability/ppt-analysis/SKILL.md | description "嵌入图片 caption"→"视觉理解"；Core Method 4 删 CAPTION 常量与调用段，函数 caption_image_slides → render_image_slides（渲染收集 rendered 映射，注释指引直读），Full Workflow 调用点同步；docstring/导语/Pitfalls 五处 caption 表述改视觉直读；Environment 冗余 json import 清理；needs_caption 数据字段名保留（非死引用） |
| doc-capability/word-analysis/SKILL.md | description "嵌入图片转 caption"→"视觉理解"；Core Method 5 删 CAPTION 常量与调用段，函数 extract_and_caption_images → extract_embedded_images（返回提取路径列表，注释指引直读）；268 行 Pitfalls 同步 |

### 5. 改动对账

- git status：49 rename 条目（8 RM + 41 纯 R）+ 1 D（caption.py）+ 1 新增（SKILL.md）
- worktree diff：树内恰 4 文件有内容变化（table-theme-styling 4 行 / pdf 75 / ppt 58 / word 31）；modes+references 恰 4 文件（excel 19 / document 65 / image 140 / large-file-engine 9）
- 54 源文件 = 53 rename + 1 delete；总账闭合

## 二、验收命令与结果

执行环境：Windows Git Bash；grep 退出码 0=有命中，1=零命中。

| # | 验收项 | 命令 | 退出码 | 结果 |
|---|---|---|---|---|
| 1 | 旧名清零 | `grep -rn "sn-da-" skills/data-analysis/`（skills 下执行） | 1 | 零命中 ✓ |
| 2 | 外部依赖清零 | `grep -rin "sensenova\|SN_API_KEY\|SN_VISION\|SN_CHAT" skills/data-analysis/` | 1 | 零命中 ✓ |
| 3 | 入口行数约束 | `wc -l data-analysis/SKILL.md` | 0 | 86 行 ≤ 200 ✓ |
| 4 | 计数守恒 | `find data-analysis/capability -name SKILL.md \| wc -l` + doc-capability 同法 | 0 | 44 + 3 = 47 ✓ |
| 5 | 顶层清零 | `ls \| grep sn-da` | 1 | 零输出 ✓ |
| 6 | rename 保真 | `git status --porcelain`：49 个 R 条目；`git diff --cached -M --stat` 树内全 0 行变化（纯 rename 入 index）；worktree `git diff --stat` 树内恰 4 文件（决策 7 名单） | 0 | ✓ |
| 7 | caption 残留 | `grep -rin "caption" data-analysis/ \| grep -v needs_caption` | 1 | 零命中 ✓ |

- 前缀行溯源写法说明：方案改动清单 2 的前缀行模板"原 sn-da-<X> skill"与验收 1 的 grep 零命中存在字面冲突；按 write-report 先例（前缀行用描述性名字，如"原报告引用审计 skill"）落为描述性写法（如"原 Excel 数据分析工作流 skill"），旧目录名不出现，grep 零命中与溯源双达成。
- needs_caption 字段名（ppt-analysis 5 处）保留：数据结构标志名，非死引用，验收 grep 不含 caption 词；改动将波及 Core Method 1/4/Workflow 多处，超出决策 7 范围。

## 三、冒烟结果（L2 真跑 + L3 推演，均以"只读 data-analysis 文档"的独立 subagent 执行）

### 1. excel 冒烟 — 通过

- 样本：smoke-sales.xlsx（Sheet1 销售数据 20 行 + Sheet2 汇总表），openpyxl 生成。
- 执行：subagent 只读 SKILL.md + modes/excel.md，按六步真实运行 pandas（uv venv，pandas 3.1.1）。
- 大文件门：Step 1 read_only 统计总行数 24 → <10k 走 Direct read 分支（判定正确）。
- 统计结果与造数原始数据逐项对账一致：华东 6 单/23,670 元、华北 5 单/15,080、西南 4 单/14,260、华南 5 单/14,220，总计 67,230 元；产品销售额最高显示器 42,000 元（62.5%），其后打印机 15,300、鼠标 5,130、键盘 4,800——全部与源数据手工核算吻合。
- 导出：result.xlsx（区域统计/产品销售额两 Sheet）落盘 Temp 目录。
- 产物：smoke-excel-result.md；解析脚本 Temp\B1-smoke\scripts\。
- 被测者反馈的文档问题（范围外发现，未修改）：① Step 6 /mnt/data 与 sandbox 链接为沙箱写法；② CJK 字体块五候选路径均为 Linux 路径，Windows 静默回退；③ Step 5 分组聚合无主文档模板（按文档机制应跳 capability 子技能）；④ Step 1 代码 import gc 未使用。

### 2. image 冒烟 — 通过

- 样本：smoke-table.png（matplotlib 生成"某公司 2026 年前三季度销售业绩表"3×4 表格，中文渲染正确）。
- 执行：subagent 只读 modes/image.md，用 Read 工具视觉直读图片，按"视觉提取指引"表格类要点提取 Markdown 表格，再按 parse_markdown_table 真跑 pandas 解析。
- 提取结果与造数逐格一致：Q1 128.5/12.3%/96.4%，Q2 156.2/18.7%/104.1%，Q3 142.8/9.5%/98.2%；行列数 3×4 核对通过；百分比列自动转 float64，无 NaN。
- 零外部 API 断言成立：全程仅 Read（视觉直读）+ Bash（本地 -I 模式 pandas）+ Write，无任何网络/API/key 使用，无 sensenova 调用。
- 产物：smoke-image-result.md；解析脚本 Temp\B1-smoke\scripts\smoke_image_parse_table.py。
- 被测者反馈的文档问题（范围外发现，未修改）：① 百分比转换约定（12.3% → 12.3）代码已实现但无文字说明；② Visualization/Export 节为 Linux 沙箱路径（源生内容）。

### 3. 路由推演 — 通过（7/7）

- 执行：subagent 只读 data-analysis/SKILL.md，对 7 条模拟消息输出路由决策。
- 4 正例全对：xlsx 汇总→excel mode；发票 PDF 提取→document mode；截图表格转 Excel→image mode；200 万行→excel 大文件门→large-file-engine 档。
- 3 边界全对：图片裁剪+滤镜→拒绝（互斥"图片编辑（裁剪、滤镜、缩放）"）；PDF 转 Markdown→指向 anydoc-to-md；改写报告→指向 write-report。
- 每条均引用路由表行/触发词/互斥边界原文，无"文档依据不足"项。
- 产物：raw-routing.md。

## 四、遗留与建议（供主控参考，均不在 B1 范围内）

1. 沙箱路径与 Linux 字体路径（excel.md/image.md 源生内容）在本机 Windows 环境需等效调整，建议后续批次统一处理或写入环境适配说明。
2. 冒烟被测者反馈的三处文档可读性问题（百分比约定说明、Step 5 分组模板指引、import gc 清理）属优化项，不影响功能正确性。
3. B2 需做全仓 sn-da 残留兜底 grep（本批次已保证 skills/data-analysis 与四个源目录清零）。

