# Message Bus (消息总线) 模式详解

> ⚠️ **书外工程实践**，非《深入理解 AI Agent》（李博杰）本书内容。
> 属 ai-agent-design pack 的 **practices 实践层**（第五组件），收纳工程社区的 agent 协调模式。
> **书内对应**：ch10「控制平面：消息传递 / 消息总线 / 跨组织边界用 A2A 协议」。

## 概述

代理通过发布和订阅两个原语进行交互。代理订阅他们关心的主题，路由器传递匹配的消息。消除了点对点连接的复杂性，支持事件驱动的灵活工作流程。

## 架构图

```
事件源 → 消息总线 ← 代理订阅
  ↓         ↓
 告警/事件  ┌────────────────┐
            │   Router    │
            │ (路由器)     │
            └────────────────┘
         ↙  ↓  ↘
    Agent A   Agent B   Agent C
   (订阅X)  (订阅Y)  (订阅Z)
     ↓          ↓          ↓
   处理     处理       处理
     ↓          ↓          ↓
  发布事件 → 消息总线 → 订阅者
```

## 工作流程

1. **代理订阅**: 代理订阅他们感兴趣的事件主题
2. **事件发布**: 事件源或代理向总线发布事件
3. **路由**: 路由器根据主题将事件传递给订阅的代理
4. **处理**: 订阅的代理处理事件
5. **链式反应**: 处理的代理可能发布新事件，触发下一个处理阶段

## 适用场景

### 典型用例

| 场景 | 事件流 | 代理类型 |
|------|--------|----------|
| **安全运营** | 告警→分诊→调查→响应 | 分诊、调查、响应、收集 |
| **订单处理** | 订单→库存→支付→发货 | 库存、支付、物流、通知 |
| **CI/CD** | 代码→测试→构建→部署 | 测试、构建、部署、监控 |
| **数据分析** | 数据→清洗→分析→报告 | 清洗、分析、可视化 |

### 最佳使用条件

✅ 事件驱动流程，工作流由事件而非预定序列涌现
✅ 代理生态可能增长，新代理可以独立添加
✅ 需要灵活的事件路由和分发
✅ 工作流可能因发现而变化

### 不适合的情况

❌ 需要严格的顺序执行
❌ 事件处理必须实时协调
❌ 需要复杂的调试和追溯
❌ 路由逻辑高度不确定

## 使用 DeepAgents 创建示例

```
创建 message bus infrastructure:
  - 定义事件主题: alert.network, alert.credential, event.enrichment
  - 实现发布/订阅机制
  - 实现智能路由器

创建 agents:
  - triage_agent:
      订阅: alert.*
      发布: alert.routed.{type}
  - network_investigation_agent:
      订阅: alert.routed.network
      发布: event.enrichment, event.response
  - identity_analysis_agent:
      订阅: alert.routed.credential
      发布: event.enrichment
  - context_gathering_agent:
      订阅: event.enrichment
      发布: event.response_ready
  - response_coordinator:
      订阅: event.response_ready
      决定最终响应
```

## 关键设计考虑

### 主题命名约定

```
# 结构化主题名称
{domain}.{category}.{action}.{detail}

示例:
- alert.network.intrusion.high
- order.payment.success.credit_card
- data.cleaning.csv.complexity.high
```

### 路由策略

```python
class MessageRouter:
    def route(self, event):
        """智能路由决策"""
        # 1. 精确匹配
        if event.topic in self.subscribers:
            return self.subscribers[event.topic]

        # 2. 通配符匹配
        wildcard = self.find_wildcard_match(event.topic)
        if wildcard:
            return self.subscribers[wildcard]

        # 3. 基于内容的路由
        return self.content_based_route(event)
```

### 错误处理

```python
def publish_with_retry(event, max_retries=3):
    """带重试和死信队列的发布"""
    for attempt in range(max_retries):
        try:
            bus.publish(event)
            return True
        except RouteError:
            delay(attempt * 100)
        except SubscriberError:
            # 订阅者不可用
            dead_letter_queue.add(event)
            return False
    return False
```

## 常见陷阱

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 事件丢失 | 订阅者故障 | 实现持久化队列和确认机制 |
| 路由错误 | 分类不准确 | 使用 LLM 进行语义路由 + 后备规则 |
| 调试困难 | 事件链复杂 | 实现事件追踪和可视化 |
| 循环事件 | A→B→C→A | 设置事件层级或 TTL |
| 顺序问题 | 无保证 | 需要顺序时使用序列号 |
