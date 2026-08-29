# Shared State (共享状态) 模式详解

> ⚠️ **书外工程实践**，非《深入理解 AI Agent》（李博杰）本书内容。
> 属 ai-agent-design pack 的 **practices 实践层**（第五组件），收纳工程社区的 agent 协调模式。
> **书内对应**：ch10「共享上下文 + 数据平面：共享文件系统虚拟目录树」（Agent 之于运行时如进程之于内核）。

## 概述

代理自主运行，通过所有都可以直接读写的持久存储进行协调。没有中央协调器，代理检查存储、行动、写回发现，基于其他代理的工作调整行为。

## 架构图

```
          ┌─────────────────────┐
          │  共享存储            │
          │  (数据库/文件系统)     │
          └─────────────────────┘
        ↙     ↓     ↘
    Agent A  Agent B  Agent C
    (自主)  (自主)  (自主)
      ↓        ↓        ↓
    读取    读取      读取
    存储状态  存储状态    存储状态
      ↓        ↓        ↓
    行动    行动        行动
      ↓        ↓        ↓
    写入    写入        写入
    发现    发现        发现
      ↑        ↑        ↑
    └────────┴────────┘
       基于他人的发现
       调整自身行为
```

## 工作流程

1. **初始化**: 在共享存储中写入初始问题或数据集
2. **读取**: 代理读取存储中的相关信息
3. **行动**: 基于读取的信息执行工作
4. **写入**: 将发现或更新写回存储
5. **循环**: 代理重复读取→行动→写入循环
6. **终止**: 满足终止条件（时间限制、收敛阈值、代理决定）

## 适用场景

### 典型用例

| 场景 | 共享内容 | 为什么适合 |
|------|----------|----------|
| **研究综合** | 发现、假设、证据 | 代理基于他人发现调整调查 |
| **知识图谱构建** | 实体、关系、属性 | 代理相互验证和扩展图谱 |
| **分布式优化** | 解、状态、更新 | 代理基于他人解调整策略 |
| **集体决策** | 投票、论据、结论 | 无需协调器即可汇聚意见 |

### 最佳使用条件

✅ 协作研究，代理共享发现
✅ 需要消除单点故障
✅ 代理需要相互发现进行协作
✅ 知识需要持续积累和更新

### 不适合的情况

❌ 需要严格的顺序控制
❌ 可能产生冲突性工作
❌ 终止条件难以确定
❌ 工作需要严格的审计追踪

## 使用 DeepAgents 创建示例

```
创建 shared state infrastructure:
  - 数据库或文件系统
  - 读/写 API
  - 事件通知机制（可选）

创建 agents (自主运行):
  - literature_agent:
      读取: 研究状态、未探索线索
      写入: 发现、论文引用
  - industry_agent:
      读取: 行业报告、公司信息
      写入: 市场数据、产品信息
  - patent_agent:
      读取: 技术趋势、竞争对手专利
      写入: 专利分析、技术预测

终止条件:
  - 时间限制: 30分钟
  - 收敛阈值: 5分钟无新发现
  - 质量代理: 决定是否足够完整
```

## 关键设计考虑

### 并发控制

```python
class SharedStore:
    def __init__(self):
        self.lock = asyncio.Lock()

    async def write(self, agent_id, data):
        """带锁的写入"""
        async with self.lock:
            # 检测冲突
            current = self.read()
            if not self.is_compatible(current, data):
                # 使用版本控制
                data = self.merge(current, data, agent_id)

            # 写入
            self.data.update(data)
            self.data[agent_id] = {
                "timestamp": now(),
                "content": data
            }
```

### 终止条件

```python
class TerminationMonitor:
    def __init__(self):
        self.last_activity = now()
        self.convergence_window = 5 * 60  # 5分钟

    def should_terminate(self):
        # 条件1: 时间限制
        if elapsed(start_time) > time_limit:
            return True, "时间限制"

        # 条件2: 收敛
        if elapsed(self.last_activity) > self.convergence_window:
            return True, "已收敛"

        # 条件3: 质量代理决定
        if quality_agent.is_satisfied():
            return True, "质量达标"

        return False, "继续"
```

### 防止重复工作

```python
def check_duplicates(agent_id, task):
    """检查是否有其他代理正在做相同工作"""
    active_tasks = store.read("active_tasks")

    for other_id, other_task in active_tasks.items():
        if agent_id == other_id:
            continue

        if similarity(task, other_task) > threshold:
            return True, f"{other_id} 正在进行相似工作"

    # 注册此任务
    active_tasks[agent_id] = task
    store.write("active_tasks", active_tasks)
    return False, "可以开始"
```

## 常见陷阱

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 无限循环 | A 写→B 读→写→A 读... | 实现严格的终止条件和 TTD 设计 |
| 冲突写入 | 多个代理同时修改 | 使用锁定、版本控制、合并策略 |
| 重复工作 | 代理不知道其他人在做什么 | 工作注册表、主动状态共享 |
| 难以调试 | 行为自组织 | 详细日志、状态快照、可视化 |
| 早熟停止 | 条件过早满足 | 多重终止条件、人工审查 |
