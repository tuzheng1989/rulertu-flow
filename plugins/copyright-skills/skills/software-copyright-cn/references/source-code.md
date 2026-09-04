# 源代码 Word

## 剥离口径（注释与空行）

申报源代码文档**不得包含注释、不得有空行**。剥离发生在构建层（`build_source_docx.py` 内置调用 `strip_source.strip_lines`），仓库源码不动——不存在交付副本与仓库的静默分叉问题，manifest 的 `strip_stats` 逐文件记录剥离明细，审计链完整。剥离范围：

- 整行注释整行删除：`#`（py/sh/rb）、`//` 与 `/* */`（c 系/js/ts/java/go 等）、`--` 与 `/* */`（sql）、`<!-- -->`（html）。含 shebang（`#!/usr/bin/env python3`，属功能性注释，用户口径一并删除）。
- 行尾注释截去注释部分，代码部分逐字保留（含原有空白，不重排）。
- Python 语句级独立字符串（模块/类/函数 docstring）整段删除。
- 空行与纯空白行全删。
- 字符串字面量内的 `#`、`//`、`--` 绝不误删（改变代码实质是红线）：Python 走 `tokenize` + `ast` 精确路径；其余语言走引号感知状态机，正则字面量、模板字符串插值等极少数形态属已知局限——非 Python 项目构建后应人工抽查 docx，语法不可解析的 Python 文件构建器拒构并转人工。

原"注释精修/去 AI 味整改"口径（含十条 AI 特征注释检测）废止：注释不进文档，整改对象不复存在。`scan_source.py` 的注释类检测仍会命中仓库源码，其结论仅用于定位，不要求整改、不阻断构建；占位符、乱码、第三方版权头、空桩行等代码实质问题仍须构建前处理（版权头随注释剥离后，第三方代码的权属问题不因此消失，预审照做）。

## 统计口径

“系统全部代码”指申请版本中由申请人编写并参与软件运行的源文件。默认纳入产品源码和必要启动脚本；默认排除测试、第三方依赖、vendor/minified 文件、构建产物、缓存、数据、模型、锁文件、文档、实验结果、生成代码、`.env` 和秘密文件。边界不明确时，把候选文件列入清单供用户确认，不静默删除。

先运行：

```powershell
python scripts/inventory_repo.py --repo . --output "code-inventory.json"
```

需要调整口径时使用重复的 `--include-root` 或 `--exclude`。清单中的物理行数是仓库事实记录；**申报与截断一律以剥离后行数（retained）为准**：3,000 行阈值判断、前/后 1,500 段截取、登记表“源程序量”、文档页数全部基于 retained 口径，与提交文档逐页自洽。仓库源码不因剥离改动，无需重跑清单。

## 抽取规则

- 剥离后总行数（retained）大于 3,000：按清单固定的文件路径顺序串接，取前 1,500 行和后 1,500 行，二者不重叠。
- 主程序入口必须出现在文档前部：默认按清单文件路径顺序串接；入口未居前时，用 `--first <入口相对路径>` 把它前置到串接序列最前，manifest 的 `reordered_first` 字段即记录本次前置的文件与顺序，不再要求手工改清单。入口候选由 `inventory_repo.py` 结果与用户确认共同确定。
- 剥离后总行数不超过 3,000：提交全部代码。
- 代码行逐字保留；注释与空行构建时剥离。Word 左列显示 `文件名:行号`（重编行号，文件内连续，不显示相对路径）；完整相对路径保留在 manifest 记录中供回溯。文件名、页眉或分隔文字不占源码行数。
- manifest 双轨记录：`total_physical_lines`（原始物理行数）、`total_retained_lines`（剥离后行数）、`strip_stats`（每文件 original/retained 与注释、空行、行尾注分类计数）、首行/前段末行/后段首行/末行及 SHA-256（均按 retained 口径）。

## 构建前检查

入选文件先过静态扫描（主 SKILL.md 第 3 步）：占位符、乱码、第三方版权头、空桩行命中项经用户审批修复后才构建（连续空行与注释由构建层剥离，不再要求整改）。扫描后置会让缺陷直接进入提交件，补正成本远高于构建前处理。

构建命令：

```powershell
python scripts/build_source_docx.py --inventory "code-inventory.json" --output "源代码.docx" --title "软件全称" --version "V1.0" --first "src/main.py"
python scripts/render_check.py --docx "源代码.docx" --min-lines 50 --output render-report.json
```

构建器按每页 50 个源码记录分页；剥离后行数通常少于物理行数，页数随之减少。每页 50 行对齐官方“每页不少于 50 行”口径（核对记录：中国版权保护中心官网"所需文件"页，https://www.ccopyright.com.cn/index.php?optionid=1080，2026-09-03）。长行在 Word 中折行显示，仍只对应一个源文件物理行，manifest 的记录数不变；但折行会使该页实际渲染行数少于每页记录数，`render_check.py` 的报告会列出实际行数不足 `--min-lines` 的页，整改（调小 `--lines-per-page` 或字号）由人工决策，构建器不自动改版式。本机无 soffice 时脚本非零退出并提示转人工，不伪造通过。

## 完成标准

- Word 中源码记录数等于 `selected_line_count`（retained 口径）；大仓库恰为 3,000，小仓库等于剥离后全部代码行数。
- **文档内无注释行、无空行**（剥离口径）；Python 入选文件全部通过精确剥离，非 Python 文件经人工抽查确认无误删。
- 主程序入口出现在文档前部；用 `--first` 前置时，manifest 的 `reordered_first` 与文档首记录 `first.path` 一致可核。入选文件无占位符、乱码、第三方版权头和空桩行（构建前扫描已确认）。
- 前后段边界与 retained 串接序一致，无重复、漏段或排序漂移；manifest 的 `reordered_first` 如实记录任何前置调整。
- manifest 双轨行数可核：`total_retained_lines` ≤ `total_physical_lines`，`strip_stats` 各文件 retained 之和等于 `total_retained_lines`。
- 文档不含密钥、个人数据、第三方压缩库或与申请软件无关的实验资产。
- 软件名称和版本与登记表、说明书一致；页眉页脚和页码连续。
- 渲染实测：`render_check.py` 报告无不足页；本机无法渲染时把“逐页核对每页行数”列入 `review-needed.md` 人工核对项。

审计口径移交：说明书 audit JSON 的 `page_evidence` 键为“内容页序号（1 起）”，与 docx 物理页号相差封面+目录 2 页，消费时注意换算。
