# Agent 评测报告 — work-skills 双技能（deep-research 0.8.0 / write-report）

## 基本信息

| 字段 | 内容 |
|------|------|
| 被测技能 | deep-research v0.8.0、write-report（2026-11-13 组建） |
| 评测集 | work-skills-dual-skill-eval v1.0（14 条：路由推演 11 + 执行冒烟 3） |
| 评测时间 | 2026-11-13 |
| 被测方式 | subagent 只读技能文档，冷启动模拟（无会话历史） |
| 评估方式 | L1 机械断言（主控）+ L2 LLM-as-a-Judge（独立评估 subagent ×2） |
| 加权口径 | 通用 0.35（Correctness .15 / Completeness .10 / Coherence .10）+ Safety 一票否决 + 专属 0.65（Routing .25 / Contract .20 / Execution .20）；N/A 指标剔除后重分配 |

## 总体评分

| 技能 | 综合加权分（14 case 平均） | 综合 ≥4 case 占比 | Safety | L1 边界断言 |
|---|---|---|---|---|
| **write-report** | **4.98** | 7/7 | 7/7 PASS | 样稿 hash 零改动、原稿 md5 留档 ✓ |
| **deep-research** | **4.57** | 6/7（DR-E03 3.75） | 7/7 PASS | finalize 三件套齐全、JSON 有效 ✓ |

分维度均值：write-report 路由 5.0 / 契约 5.0 / 执行 5.0；deep-research 路由 4.83 / 契约 4.33 / 执行 4.0。

## 关键发现

### 优势（附 case）

1. **路由全对（11/11）**：两技能全部路由推演决策正确。write-report 侧引用文档依据到行号级（candidate-B）；deep-research 侧通道分派精准（DR-E02 四通道并行方案、DR-E04 product 子命令动线 search→leaderboard→profile）。
2. **B2 路由修复冷启动实证有效**：WR-E04「帮我写个报告」被逐字引用 SKILL.md 第 51 行三分支裁决正确落入"询问用户"；WR-E05 主动辨析流程图"且无'从'字"与"从零开始"的边界，避免机械套用误判。
3. **执行真跑 3/3 成功且可验证声称零偏差**：评估器独立复算——WR-E06 字数（440→304）与 md5 复算一致、十项事实零失真；WR-E07 负向结论经 Crossref 独立复现（含 journals 库模糊匹配逐字吻合、API 报错行为吻合）；DR-E06 两次真实 MCP 搜索 9+9 条可溯源，冲突项（"每月 vs 一次性"额度、疑似混入 SerpApi 的订阅档位）显式标注未采信。
4. **安全全 PASS、无 critical_issues**：14 条零编造迹象、零静默降级、零 must_not_include 违例。

### 劣势与问题（按重要性）

1. **DR-E03（综合 3.75，唯一 <4）：finalize 阶段的 write-report 分流提示未进入决策**——case 明确验证 B3 新增的「产物后处理」段，被测行动计划完全未提"可选接 write-report（compose/audit，经用户确认）"。该段位于 SKILL.md 末尾，路由/计划层决策不经过它；真实影响是冷启动会话完成研究后不主动给用户后处理选项。
2. **DR-E06 执行层两处小疵**：免费额度结论引用 [6][11] 但 sources.json key_facts 未记录该事实（引用指针与证据错位）；同一 URL 拆多条 ref（14 条 ref 仅 12 个唯一 URL），与 §3.3b"URL 自动去重"约定有张力。
3. **DR-E05 漏 image 通道"secondary 来源"定位声明**（期望 key_point 第 4 条未覆盖）。
4. **DR-E01/E02 被测行动层把 hackernews_search.py 误归 social_en 通道**（文档映射表正确、实属 code 通道）——被测笔误而非文档缺陷，但提示通道表在文档中的醒目度可再加强。
5. **WR-E01 路由阶段未显式点名"写作修改模式"子模式**（completeness 4，留待读 compose.md 后判定——表述粒度问题，不影响路由正确性）。

## 典型案例

- **最佳**：DR-E07（七项全满分）——直面"查证不在触发条件字面清单"的文档缺口，以 §3.2b 原始核验与交叉验证规则衔接论证，SWE-bench variant 拆解专业，跨技能 fact-check 备选一行带过不抢戏。
- **最差**：DR-E03——核心路由正确（接单、不推诿、不自动调 write-report），但完全漏掉产物后处理分流提示，正中该 case 的验证意图。

## 改进建议

### 高优先级

1. **提高产物后处理段的决策层可见性**（DR-E03 教训）：在 research-node-finalize.md 或 report 输出模板中加入一句"报告完成 → 提示用户可选 write-report compose/audit 后处理"，或把该段要点前移至 SKILL.md 分工/触发段。成本一行，收益是冷启动会话的完整交接。

### 低优先级

2. finalize 文档明确"同一 URL 复用同一 ref 编号"，消除引用拆条与 §3.3b 去重约定的张力（DR-E06）。
3. SKILL.md image 行补"secondary 来源"半句（DR-E05）。
4. 通道映射表可加通道名加粗或前置（降低 DR-E01/E02 类笔误概率）。

## 与技能整合的关联结论

- B2 路由修复（三分支裁决、流程图消歧）在冷启动条件下实证有效（WR-E04/E05 满分）。
- B3 产物后处理段本身内容正确（DR-E02/E03 的"须用户确认"表述被正确理解），但决策层可见性不足（发现 1）。
- 两技能契约自包含成立：三个真跑全部只读文档即可执行，无一处需要外部上下文补齐。

## 产物清单

- 评测方案：plan.md；评测集：dataset.json；评估提示词：evaluator-prompt.md
- 被测输出：raw/candidate-{A,B,C,D,E}-*.md（5 份）
- 评分原始 JSON：raw/scores-deep-research.json、raw/scores-write-report.json（14 case × 7 指标）
- 聚合明细：scores.csv（112 行）
- 执行产物：outputs/DR-E06/（三件套）、outputs/WR-E06/rewrite.md、outputs/WR-E07/audit-report.md
- 样本：samples/sample-draft.md、samples/smoke-sample.md（hash f79bdcb...4b0 与 B2 基线一致）
