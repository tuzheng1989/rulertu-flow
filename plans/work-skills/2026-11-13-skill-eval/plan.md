# Evaluation Plan — work-skills 双技能评测（deep-research 0.8.0 / write-report）

- 日期：2026-11-13
- 评测工作区：plans/work-skills/2026-11-13-skill-eval/
- 规模档位：标准评测（14 条用例，含轻量真跑）
- 被测方式：subagent 只读技能文档模拟冷启动会话

## 基本信息

- **被测对象**：
  1. `plugins/work-skills/skills/deep-research/`（v0.8.0，五阶段迭代式网络研究技能，7 搜索通道）
  2. `plugins/work-skills/skills/write-report/`（报告成稿后处理 + 长文档引擎，3 mode + 3 引擎模式）
- **Agent 类型**：指令遵循 + 工具调用混合
- **评测目的**：验证整合后的两个技能在冷启动条件下的路由正确性、契约自包含性与真实可执行性
- **评测范围**：触发路由 / 通道与 mode 分派 / 边界遵守 / 执行产出质量；不含性能与成本评测

## 指标体系

### L1 机械可验证（主控代码断言）

| 指标 | 方式 | 说明 |
|---|---|---|
| FormatCompliance | 脚本断言 | 文档快照：技能内引用路径存在、版本一致（复用 B1-B3 验收口径作回归基线） |
| BoundaryBinary | 0/1 断言 | WR-E07：审计前后样稿 hash 一致；DR/WR 执行产物落盘位置符合契约 |

### L2 半客观（评估 subagent，LLM-as-a-Judge）

通用四项（模板 1 标准）：

| 指标 | 权重 | 评分 |
|---|---|---|
| Correctness | 0.15 | 1-5 Likert |
| Completeness | 0.10 | 1-5 Likert |
| Coherence | 0.10 | 1-5 Likert |
| Safety | 一票否决 | 0/1 |

专属三项（不适用标 N/A，加权时剔除）：

| 指标 | 权重 | 评分 | 定义 |
|---|---|---|---|
| RoutingCorrectness | 0.25 | 1-5 | 路由/分派决策是否正确（skill、mode、引擎模式、搜索通道、降级路径） |
| ContractCompleteness | 0.20 | 1-5 | 决策/产出是否遵循文档契约（输入输出约定、边界声明、自包含可执行） |
| ExecutionQuality | 0.20 | 1-5 | 真实执行产出的质量（仅执行类 case 适用） |

### L3 主观

争议 case（judge 间分差 ≥2 或 Safety FAIL）由用户仲裁。

## 评测集

14 条：deep-research 7（DR-E01~E07）+ write-report 7（WR-E01~E07）。难度分布 easy 3 / medium 6 / hard 5。执行类 3 条（DR-E06 / WR-E06 / WR-E07），路由推演类 11 条。详见 dataset.json。

## 被测执行协议

- **路由推演类（11 条）**：被测 subagent 收到「完整技能文档 + 用户消息」，输出路由决策与下一步动作（不真执行）。决策文本交评估 subagent 评分。
- **执行类（3 条）**：被测 subagent 真实执行并落盘产物：
  - DR-E06：轻量研究（max_loops=1，1-2 条 query，不深读），题目「Serper.dev API 的定价与免费额度」
  - WR-E06：compose 改写 `samples/sample-draft.md`（~500 字粗糙草稿 → 压缩改写）
  - WR-E07：audit 审计 `samples/smoke-sample.md`（复用 B2 冒烟样稿，含已知幻觉引用 R1）
- 同一被测 subagent 顺序处理同批多个 case，prompt 明确各 case 相互独立。

## 判定漏斗

1. L1 快照断言（FormatCompliance / BoundaryBinary）→ 失败短路标 FAIL
2. 被测 subagent 执行（路由决策或真跑）
3. 评估 subagent 按 evaluator-prompt.md 逐条评分，JSON 落 `raw/`
4. 主控聚合 → scores.csv + report.md；争议 case 提请用户仲裁

## 评测约束

- 被测调用方式：subagent（general-purpose），只读技能文档，无会话历史
- 单条路由推演超时 ~3 分钟；执行类 ~15 分钟（DR-E06 上限）
- 深度：单次评估（不做 pass@k；如需建立长期基线另跑深度档）
- 评估模型：与主控同源（sonnet subagent）
