# 源代码 Word

## 统计口径

“系统全部代码”指申请版本中由申请人编写并参与软件运行的源文件。默认纳入产品源码和必要启动脚本；默认排除测试、第三方依赖、vendor/minified 文件、构建产物、缓存、数据、模型、锁文件、文档、实验结果、生成代码、`.env` 和秘密文件。边界不明确时，把候选文件列入清单供用户确认，不静默删除。

先运行：

```powershell
python scripts/inventory_repo.py --repo . --output "code-inventory.json"
```

需要调整口径时使用重复的 `--include-root` 或 `--exclude`。清单中的物理行数是唯一统计来源。不要先删空行或注释再计数，也不要把文件分隔标题算作源码行。

## 抽取规则

- 总物理行数大于 3,000：按清单固定的文件路径顺序串接，取前 1,500 行和后 1,500 行，二者不重叠。
- 主程序入口必须出现在文档前部：默认按清单文件路径顺序串接；入口未居前时，用 `--first <入口相对路径>` 把它前置到串接序列最前，manifest 的 `reordered_first` 字段即记录本次前置的文件与顺序，不再要求手工改清单。入口候选由 `inventory_repo.py` 结果与用户确认共同确定。
- 总物理行数不超过 3,000：提交全部代码。
- 每一行保留原文，并在 Word 左侧显示相对路径和原文件行号。文件名、页眉或分隔文字不占源码行数。
- 同一次清单生成 Word 和登记表中的“源程序量”。抽取后记录首行、前段末行、后段首行、末行以及 SHA-256。

## 构建前检查

入选文件先过静态扫描（主 SKILL.md 第 3 步）：占位符、乱码、连续空行、第三方版权头、空桩行命中项经用户审批修复后才构建。扫描后置会让缺陷直接进入提交件，补正成本远高于构建前处理。

构建命令：

```powershell
python scripts/build_source_docx.py --inventory "code-inventory.json" --output "源代码.docx" --title "软件全称" --version "V1.0" --first "src/main.py"
python scripts/render_check.py --docx "源代码.docx" --min-lines 50 --output render-report.json
```

构建器按每页 50 个源码记录分页；3,000 行通常得到 60 个代码页。每页 50 行对齐官方“每页不少于 50 行”口径（核对记录：中国版权保护中心官网"所需文件"页，https://www.ccopyright.com.cn/index.php?optionid=1080，2026-09-03）。长行在 Word 中折行显示，仍只对应一个源文件物理行，manifest 的记录数不变；但折行会使该页实际渲染行数少于每页记录数，`render_check.py` 的报告会列出实际行数不足 `--min-lines` 的页，整改（调小 `--lines-per-page` 或字号）由人工决策，构建器不自动改版式。本机无 soffice 时脚本非零退出并提示转人工，不伪造通过。

## 完成标准

- Word 中源码记录数等于 `selected_line_count`；大仓库恰为 3,000，小仓库等于全部代码行数。
- 主程序入口出现在文档前部；用 `--first` 前置时，manifest 的 `reordered_first` 与文档首记录 `first.path` 一致可核。入选文件无占位符、乱码、第三方版权头和异常连续空行（构建前扫描已确认）。
- 前后段边界与清单一致，无重复、漏段或排序漂移；manifest 的 `reordered_first` 如实记录任何前置调整。
- 文档不含密钥、个人数据、第三方压缩库或与申请软件无关的实验资产。
- 软件名称和版本与登记表、说明书一致；页眉页脚和页码连续。
- 渲染实测：`render_check.py` 报告无不足页；本机无法渲染时把“逐页核对每页行数”列入 `review-needed.md` 人工核对项。

审计口径移交：说明书 audit JSON 的 `page_evidence` 键为“内容页序号（1 起）”，与 docx 物理页号相差封面+目录 2 页，消费时注意换算。

