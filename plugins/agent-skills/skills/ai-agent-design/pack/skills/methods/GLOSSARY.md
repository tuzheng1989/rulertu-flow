# methods 共用术语

> 方法层共用术语速查（与 knowledge 层 glossary 互补，此处只列方法执行高频词）。

- **Harness** — 模型之外的约束 / 验证 / 纠正机制；react-loop、proposer-reviewer、context-engineering 都是其组成。
- **验证器（verifier）** — 基于真实观测判定结果的对象；proposer-reviewer 与 eval-driven-iteration 的核心。
- **轨迹（trajectory）** — Agent 消息历史；react-loop 不断追加它推进任务。
- **判停条件** — 方法执行中何时停止（如最大迭代、验证器判定失败）。
- **参数传递保真性** — 模型感知世界 = 工具操作世界；tool-design 的底线。
- **天然 Harness** — 测试 / 类型 / VCS 等软件工程基础设施；coding-as-meta-tool 的依据。
- **5 项验证** — 多语境证据 / 迁移能力 / 增量价值 / 可执行性 / 可区分性；方法交付门槛。
