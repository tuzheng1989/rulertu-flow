# Evaluation Plan — data-analysis 技能评测

- 日期：2026-11-13
- 评测工作区：plans/work-skills/2026-11-13-data-analysis-eval/
- 规模档位：标准评测（10 条：路由推演 8 + 执行冒烟 2）
- 被测方式：subagent 只读技能文档模拟冷启动（与 2026-11-13-skill-eval 同法）
- 指标体系：沿用 skill-eval 的通用 4 项（Correctness .15 / Completeness .10 / Coherence .10 / Safety 一票否决）+ 专属 3 项（RoutingCorrectness .25 / ContractCompleteness .20 / ExecutionQuality .20），N/A 剔除重分配

## 重点验证目标（源自 B1 双重验证的修复项）

1. **字体块 Windows 修复实效**（第二意见定"高"）：DA-E10 真跑 matplotlib 中文图——乱码即 FAIL（L1 机械可判）。
2. **CSV 输入指引实效**（B1 修复新补）：DA-E09 真跑 GBK 编码 csv 分析——指引是否足以让冷启动会话正确读入。
3. **决策 7 路径修复实效**（Auditor P1）：DA-E02 路由推演中 document mode 对扫描页处理的引用可达性（../../modes/image.md）。

## 评测集

10 条：路由推演 8（4 正例 + 3 边界 + 1 混合输入）+ 执行冒烟 2（CSV 真跑 / 中文图表+视觉提取真跑）。难度 easy 2 / medium 5 / hard 3。

## 判定漏斗

1. L1 机械断言：DA-E10 图表中文渲染检查（无乱码方框）、执行产物落盘存在性
2. 被测 subagent（路由决策 / 真跑执行）
3. 评估 subagent 按 evaluator-prompt.md 逐条评分（JSON 落 raw/）
4. 主控聚合 → scores.csv + report.md

## 评测约束

- 被测调用方式：general-purpose subagent，只读 data-analysis 文档，无会话历史
- 执行类产物落 outputs/；样本在 samples/
- 单次评估（不跑 pass@k）；综合分即基线 v1.0
