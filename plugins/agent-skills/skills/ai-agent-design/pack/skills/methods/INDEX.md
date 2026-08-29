# methods 索引 · Agent 设计可执行方法

7 个独立可执行方法 skill，从《深入理解 AI Agent》蒸馏而来。每个 skill 可独立安装使用。

## 方法清单（按支柱）

| Skill | 解决问题 | 主证据章 |
|---|---|---|
| [ai-agent-design-react-loop](skills/ai-agent-design-react-loop/) | 如何构建 Agent 推进循环 | ch1/2/4 |
| [ai-agent-design-proposer-reviewer](skills/ai-agent-design-proposer-reviewer/) | 如何判定任务真正完成 | 引言/ch4/5/10 |
| [ai-agent-design-context-engineering](skills/ai-agent-design-context-engineering/) | 如何工程化管理上下文 | ch2/3 |
| [ai-agent-design-eval-driven-iteration](skills/ai-agent-design-eval-driven-iteration/) | 如何科学评估与迭代 | 引言/ch6/7 |
| [ai-agent-design-tool-design](skills/ai-agent-design-tool-design/) | 如何设计工具与异步架构 | ch4/5 |
| [ai-agent-design-sft-vs-rl-selection](skills/ai-agent-design-sft-vs-rl-selection/) | 如何选型后训练与奖励设计 | ch7 |
| [ai-agent-design-coding-as-meta-tool](skills/ai-agent-design-coding-as-meta-tool/) | 如何用代码作为元能力 | ch5/8 |

## 方法关系

- **react-loop** `composes-with` **proposer-reviewer**：推进循环 + 完成判定，构成 Agent 主干。
- **react-loop** `composes-with` **context-engineering**：循环决定推进，上下文决定每步看到什么。
- **proposer-reviewer** `contrasts-with` **eval-driven-iteration**：单任务完成判定 vs 系统级批量度量。
- **tool-design** `composes-with` **proposer-reviewer**：执行工具的安全审查由 proposer-reviewer 承担。
- **sft-vs-rl-selection** `depends-on` **eval-driven-iteration**：评估是后训练的前提。
- **coding-as-meta-tool** `composes-with` **tool-design**：代码用于创造 / 设计新工具。

## 选用决策
- 刚起步建主干 → react-loop + proposer-reviewer + context-engineering
- 要质量与可靠性 → eval-driven-iteration + proposer-reviewer
- 要模型层面提升 → sft-vs-rl-selection（先做 eval-driven-iteration）
- 要扩展能力边界 → coding-as-meta-tool + tool-design

## 蒸馏说明
见 [distillation-report.json](distillation-report.json)。候选 8 个，交付 7 个；agentic-rag 因仅 ch3 单一证据降级为 knowledge 条目。每个交付方法均过 5 项验证（多语境证据 / 迁移 / 增量 / 执行 / 区分）。
