# B1 主控修复与处置记录（双重验证后）

日期：2026-11-13。Auditor 判退回（P1×1 路径死指针）+ 第二意见判修后可用，交叉印证同一根因。主控统一修复如下。

## 修复清单（主控直接实施）

| # | 修复 | 点位 | 对应发现 |
|---|---|---|---|
| 1 | 相对路径死指针 13 处：doc 三件 11 处 `../modes/image.md` → `../../modes/image.md`（含 pdf:282 裸前缀变体）、table-theme-styling 2 处 `../../references/` → `../../../references/` | 决策 7 四文件 | Auditor P1 / 第二意见维度 5 |
| 2 | 字体块补 Windows 候选：excel.md 与 large-file-engine.md 的 _FONT_PATHS 头部插 `C:/Windows/Fonts/simhei.ttf`、`msyh.ttc`；image.md 单值 wqy 改三候选循环并补 `matplotlib.font_manager` import | modes/excel.md、references/large-file-engine.md、modes/image.md | 第二意见维度 4（高） |
| 3 | 404 垃圾文件删除：capability/excel-cell-coloring.md、excel-conditional-formatting.md（字面 "404: Not Found"，无引用方） | capability/ 根 | 第二意见维度 5（中） |
| 4 | CSV 承诺落地：excel.md Step 1 前补 CSV 输入指引（pd.read_csv / gbk / 行数统计 / chunksize 分块） | modes/excel.md | 第二意见维度 2（中） |
| 5 | 写出路径去沙箱化：excel.md /tmp/_auto_parquet.parquet 与 /mnt/data/result.xlsx → 当前工作目录相对路径；image.md 4 处（chart.png / result.xlsx / glob）→ 相对路径 | modes/excel.md、modes/image.md | 第二意见维度 4（中） |

修复后复验：路径解析 13/13 OK；`grep sn-da-`/`sensenaova` 零命中；游离文件清零；字体候选三处就位；沙箱写路径清零（剩 document.md:17 占位示例属第二意见定级"低可容忍"）。

## executor-log 勘误（Auditor P2/P3-1）

- P2：executor-log 决策 7 明细"相对路径按实际层级核对：上两级至 data-analysis/"声明失实（上两级实为 capability/，差一级即 P1 根因）——以本记录勘误，原文不改（审计证据保全）。
- P3-1："49 rename（8 RM + 41 纯 R）"笔误，实为 53 rename（45 R + 8 RM）。

## 移交评估迭代阶段的已知项（goal 设定的评测环节处理）

- **高**：字体块修复的实际效果需真跑验证（生成中文图表确认无乱码）——评测执行类用例覆盖。
- 中：excel.md 大文件门阈值口径三处微差（SKILL.md ≥10k / excel.md Step 2 ≥100k 强制 / 引擎头 ≥10k MUST）——行为收敛无失败风险，评测后视情况统一口径。
- 低：image.md:121 `chr(64+i)` 列宽越界、加载占位符三种写法混用、25 个子技能头部"parent workflow"过期措辞、word-analysis 未使用 io import、table-theme-styling 永假 globals 分支（Auditor P3-2/3）、basic-statistics 断句错字、document.md /mnt 占位示例。

## 提交操作提醒（Auditor P3-6）

8 个 RM 文件的内容修改未暂存，提交前必须 git add 全部 B1 路径。

## 结论

P1 修复完成并复验通过，第二意见必修五项全部落地，B1 达可收口状态。B2（升版 2.7.0 + 全仓兜底）由主控 T0 直做（收尾分流）。
