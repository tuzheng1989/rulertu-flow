# Agent 评测报告 — data-analysis 技能

## 基本信息

| 字段 | 内容 |
|------|------|
| 被测技能 | data-analysis（sn-da 四合一组建，插件 2.7.0） |
| 评测集 | data-analysis-skill-eval v1.0（10 条：路由推演 8 + 执行冒烟 2） |
| 评测时间 | 2026-11-13 |
| 被测方式 | general-purpose subagent 只读技能文档，冷启动模拟 |
| 评估方式 | L1 机械断言 + L2 LLM-as-a-Judge（独立评估 subagent，含 iconv/awk 复算与独立读图复核） |

## 总体评分

| 指标 | 均值 | 说明 |
|------|------|------|
| Correctness | 4.9 | E10 扣 1（目验描述层误判，图表本身正确） |
| Completeness | 4.9 | E02 扣 1（引用走 document.md 通用节而非 pdf-analysis 内部精确路径） |
| Coherence | 4.9 | E10 扣 1（同 E10 目验误判） |
| Safety | 10/10 PASS | 零编造、零越界 |
| RoutingCorrectness | 5.0 | 路由 8/8 全对 |
| ContractCompleteness | 5.0 | 全满 |
| ExecutionQuality | 4.5 | E10 扣 1（目验误判） |
| **综合加权分** | **4.93** | 8 条满分段 + E02 4.875 + E10 4.4 |

## 三处 B1 修复实效实证（本评测重点目标）

1. **字体块 Windows 修复**（DA-E10）：`C:/Windows/Fonts/simhei.ttf` 首位命中，`font.family=['SimHei']` 运行时确认；评估器独立读图复核中文零乱码、四数值标签与数据一致。第二意见定"高"的缺口闭环 ✓
2. **CSV 输入指引**（DA-E09）：utf-8 失败（UnicodeDecodeError 0xb6）后按指引切 gbk 成功；评估端 iconv+awk 独立复算样本零偏差（华东 18470 / 华北 13100 / 华南 11520 / 西南 3000 / 总 46090）；hexdump 证实被测对首字节的解读属实 ✓
3. **决策 7 路径修复**（DA-E02）：扫描件链路（空文本判定 → 渲染 PNG → 视觉直读 → image.md 指引）完整走通，引用条款经原文核验真实可达 ✓（completeness 扣 1 分为引用精度：走 document.md 通用节而非 pdf-analysis 内部 `../../modes/image.md` 精确路径——属可接受的等价路径，非不可达）

## 关键发现

### 优势
1. **路由 8/8 全对且依据到行号级**：4 正例（含混合输入双路路由、200 万行经大文件门入引擎档并给出内存估算与分块方案）+ 3 边界转出（图片编辑拒→agnes-image、PDF 转 MD→anydoc-to-md、报告润色→write-report，逐条引用互斥边界原话）+ 1 混合。
2. **执行 2/2 真跑成功**：CSV 编码策略按指引完整覆盖；图表数值逐项一致。
3. **安全性全 PASS**：E10 目验误读被评估器识别为"描述层错误而非编造"（图表本身正确），定性准确。

### 劣势
1. **DA-E10 目验误判**（唯一实质缺陷）：被测读图陈述"华南略高于西南"与数据相反（14220 < 14260，两柱高差约 0.3% 近等高所致）——**被测行为问题，非技能文档缺陷**；图表本身正确。改进方向属模型能力层（近似等高柱的目验精度），建议后续评测在目验类 case 增加"相对大小关系断言"检查项。
2. **DA-E02 引用精度**（completeness 4）：对 image.md 的引用走 document.md 通用节，未落到 pdf-analysis 内部精确相对路径——等价可达，不影响执行。
3. 环境偏差如实记录：本机 Python 无 pandas/matplotlib，被测用 uv 临时环境与本机另一 Python 解决，未污染任何目录（如实记录为环境偏差而非隐瞒）。

## 典型案例

- **最佳**：DA-E04——200 万行 + 8G 内存的约束下，完整给出流式探查 → 50k 块 Parquet → 列选择性加载 → dtype 下采样 → 向量化聚合 → 大文件写出的全链方案，含单 Sheet 行数上限拆分与内存估算（1.9GB）。
- **最差**：DA-E10——执行全部正确，仅目验陈述一处相对高度误判。

## 改进建议

### 高优先级
无（技能文档无实质缺陷；三处修复全部实证有效）。

### 低优先级（记档，不阻断）
1. 目验类评测 case 增加"相对大小关系断言"检查项（评测方法层改进）。
2. excel.md 大文件门阈值口径（SKILL.md ≥10k / Step 2 ≥100k 强制 / 引擎头 ≥10k MUST）可在后续维护中统一措辞。
3. 决策 7 之外的引用精度不强制；如追求行号级引用可在 document.md 的 Visual Reading 节加一行"详细指引见 doc-capability 各件与 modes/image.md"。

## 基线声明

本评测为 data-analysis 技能的**质量基线 v1.0**（综合 4.93）。后续模型升级或技能文档改动时，以同评测集复跑对比即漂移检测。

## 产物清单

- plan.md / dataset.json / evaluator-prompt.md
- raw/candidate-{A,B,C}-*.md（被测输出 3 份）、raw/scores-data-analysis.json（10 条评分）
- scores.csv（80 行）、outputs/DA-E09/result.md、outputs/DA-E10/chart.png
- samples/sales-gbk.csv（GBK 样本）
