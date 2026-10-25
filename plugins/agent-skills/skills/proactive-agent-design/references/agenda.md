# Agenda：议程

【原文】预测的需求要经过明确采纳，才成为持续跟进的承诺。论文 §4.3、图 9 包括目标生成、跨时段子目标与长期议程、优先级和冲突消解；新的用户请求与已有承诺需要协调。

【导读】议程可理解为带元数据的依赖图。用「任务自产、优先级自排、现场自恢复」检查其主动形态；最有力的检查是重启后还知道每项为何存在、做到哪里、在等什么。该概括是工程判据，具体字段并非论文规定的 schema。

需要做出的决策：

- 从预测到承诺的筛选条件：与职责的关系、收益、冲突、重复项及消失的需求如何处理。
- 每项至少保存依据（追溯预测与职责）、进度、依赖；持久化位置和写入时机由实现决定。
- 新工作到来时如何抢占、保存现场、切换和恢复；恢复前核对依赖与依据是否过期。
- 谁能取消、暂停和更改优先级；已完成项如何避免重复执行；等待何种信号才能重启。

【实现约定】按需采用下列持久记录：

```yaml
id: agenda-item-id
mandate_ref: human-goal-version
basis: {evidence_refs: [], prediction_ref: null}
progress: {state: proposed, completed_segments: [], checkpoint_ref: null}
dependencies: []
priority_basis: null
waiting_for: null
resume_trigger: null
revalidate_at: null
stop_condition: null
```

这些空值表示尚待设计的字段；完成的架构需说明实际存储与恢复方式。可用状态包括 `proposed / committed / running / suspended / completed / cancelled`，避免用一个 done 标记掩盖部分完成。

【导读】会话内 Todo、外部消息队列可能提供一部分能力；根据实际持久化和任务来源判断，不能凭工具名宣布已有／缺失某环。明确人补位的位置及持续投入。

**诊断与验证**：待办腐烂查失效与清理；中断失忆查 checkpoint；重复执行查进度和外部状态核对。中断后重启、插入一个高优先级请求、使原需求消失，分别检查恢复、抢占和取消。

**环间接口**：反向定义 Awareness 的职责相关性；接收 Anticipation 的候选需求；给 Arbitration 的是候选工作而非执行许可；Action 逐段回写，Adaptation 修正筛选标准。
