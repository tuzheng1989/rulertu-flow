# Agent Teams (代理团队) 模式详解

> ⚠️ **书外工程实践**，非《深入理解 AI Agent》（李博杰）本书内容。
> 属 ai-agent-design pack 的 **practices 实践层**（第五组件），收纳工程社区的 agent 协调模式。
> **书内对应**：ch10「管理者模式 + 持久化上下文 / 轨迹即状态」（团队成员跨任务累积上下文，区别于单次子代理）。

## 概述

协调器生成多个独立运行的代理工作进程。团队成员从共享队列认领任务，自主完成多步骤工作并发出完成信号。与协调器-子代理的关键区别是团队成员是持久化的，在多个任务中累积上下文。

## 架构图

```
┌─────────────────────────────────────┐
│         Coordinator (协调器)         │
│  - 管理任务队列                   │
│  - 分配任务给团队成员               │
│  - 收集完成结果                   │
└─────────────────────────────────────┘
      ↓ 任务队列
  ┌────┴────┬────┴────┬────┴────┐
  ↓         ↓         ↓         ↓
Teammate 1  Teammate 2  Teammate 3  ... (持久化进程)
  ↓         ↓         ↓         ↓
持久化    持久化     持久化
上下文    上下文      上下文
  ↓         ↓         ↓
多步骤    多步骤      多步骤
任务      任务        任务
  ↓         ↓         ↓
认领新     认领新     认领新
任务        任务        任务
  └─────────┴─────────┴─────────┘
       ↓ 完成信号
  ┌─────────────────────────────────────┐
│         Coordinator (协调器)         │
│  - 运行集成测试                   │
│  - 综合最终结果                   │
└─────────────────────────────────────┘
```

## 与协调器-子代理的核心区别

| 特征 | 协调器-子代理 | 代理团队 |
|------|---------------|----------|
| 工作成员生命周期 | 单次任务后终止 | 持久化运行 |
| 上下文积累 | 每次重新开始 | 跨任务累积 |
| 任务持续时间 | 短暂、有界 | 长期、多步骤 |
| 任务数量 | 固定子任务数 | 动态队列 |

## 适用场景

### 典型用例

| 场景 | 为什么适合团队模式 |
|------|-----------------|
| **代码库迁移** | 每个服务独立迁移，团队成员建立对服务的熟悉 |
| **批量数据处理** | 每个团队成员处理不同数据集，累积处理模式 |
| **多项目监控** | 团队成员长期跟踪不同项目，积累历史上下文 |
| **分布式爬取** | 每个成员负责特定域，累积域名知识 |

### 最佳使用条件

✅ 子任务独立，可长时间运行
✅ 从持续的多步骤工作中受益
✅ 需要代理在多次调用中保留状态
✅ 每个团队成员可以建立领域专业化

### 不适合的情况

❌ 子任务之间需要频繁信息共享
❌ 工作需要在单一协调器下严格管理
❌ 任务短暂且多样化
❌ 需要严格的任务完成顺序

## 使用 DeepAgents 创建示例

```
创建 coordinator agent:
  prompt: "你是任务协调器。管理任务队列，
          分配给合适的团队成员，
          收集完成后运行集成测试"

创建 teammates (持久化):
  - teammate_1: "专注于 {domain_a} 的任务"
  - teammate_2: "专注于 {domain_b} 的任务"
  - teammate_3: "专注于 {domain_c} 的任务"

  所有 teammates 持久化运行:
    - 从队列认领任务
    - 自主完成多步骤工作
    - 积累领域上下文
    - 信号任务完成
```

## 关键设计考虑

### 任务队列管理

```python
class TaskQueue:
    def __init__(self):
        self.tasks = []
        self.completed = []

    def add_task(self, task):
        self.tasks.append(task)

    def claim_task(self, teammate_id):
        """认领任务，考虑团队成员专长"""
        suitable_tasks = [t for t in self.tasks
                       if t.specialization == teammate_id]
        if suitable_tasks:
            task = suitable_tasks.pop(0)
            task.assignee = teammate_id
            return task
        return None
```

### 持久化上下文

```python
class PersistentTeammate:
    def __init__(self, specialization):
        self.specialization = specialization
        self.memory = []  # 跨任务累积
        self.learned_patterns = {}

    def work_on_task(self, task):
        # 使用累积的上下文
        context = self.get_relevant_context(task)
        result = self.execute(task, context)

        # 从这次任务中学习
        self.learn_from(task, result)
        return result
```

### 完成检测与协调

```python
def check_completion(team, threshold=0.8):
    """检查是否有足够的团队成员完成任务"""
    completed = sum(1 for t in team if t.is_idle())
    ratio = completed / len(team)

    if ratio >= threshold:
        return True, f"{completed}/{len(team)} ready"
    return False, f"等待更多完成..."
```

## 常见陷阱

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 团队成员重复工作 | 独立性导致无法协调 | 任务分配时检查正在处理的工作 |
| 任务完成时间差异大 | 复杂度不同 | 设置合理的等待策略 |
| 共享资源冲突 | 多个成员访问相同资源 | 实现锁定或资源分区 |
| 团队成员负载不均 | 分配策略不当 | 动态重新平衡工作负载 |
