# Orchestrator-Subagent (协调器-子代理) 模式详解

> ⚠️ **书外工程实践**，非《深入理解 AI Agent》（李博杰）本书内容。
> 属 ai-agent-design pack 的 **practices 实践层**（第五组件），收纳工程社区的 agent 协调模式。
> **书内对应**：ch10「管理者模式」（规划者是系统瓶颈，应配最强模型与最精提示词）。

## 概述

层级化模式，一个主代理（协调器）作为团队负责人，负责规划工作、委派任务、综合结果。子代理处理特定职责并返回结果。

## 架构图

```
用户任务
  ↓
┌─────────────────────────────────┐
│      Orchestrator (协调器)      │
│  1. 接收并理解任务            │
│  2. 分解为子任务               │
│  3. 委派给子代理               │
│  4. 收集结果                  │
│  5. 综合最终输出               │
└─────────────────────────────────┘
  ↓         ↓         ↓          ↓
子任务1    子任务2    子任务3    ... (并行或串行)
  ↓         ↓         ↓          ↓
┌───────┐ ┌───────┐ ┌───────┐
│Agent 1│ │Agent 2│ │Agent 3│ ...
└───────┘ └───────┘ └───────┘
  ↓         ↓         ↓
  结果1      结果2      结果3
  ↑         ↑         ↑
  └─────────┴─────────┘
       回到 Orchestrator
            ↓
      综合输出 → 用户
```

## 工作流程

1. **任务接收**: Orchestrator 接收用户请求
2. **任务分解**: 将复杂任务分解为可管理的子任务
3. **任务委派**: 根据子代理的专业领域分配任务
4. **并行执行**: 子代理独立处理各自任务（可选并行）
5. **结果收集**: Orchestrator 收集所有子代理的输出
6. **结果综合**: 将分散的结果整合为连贯的输出
7. **返回用户**: 呈现最终综合结果

## 适用场景

### 典型用例

| 场景 | Orchestrator | Subagents | 子任务特征 |
|------|-------------|-----------|-------------|
| **代码审查** | 主审查系统 | 安全、测试、风格、架构 | 各自独立，输出明确 |
| **市场分析** | 分析协调器 | 竞品、趋势、用户调研 | 需要不同数据源 |
| **文档生成** | 文档主编 | API、教程、示例、FAQ | 内容类型不同 |
| **问题诊断** | 诊断协调器 | 日志、配置、网络、数据库 | 多角度分析 |

### 最佳使用条件

✅ 任务可以清晰分解为独立子任务
✅ 子任务有明确边界和预期输出
✅ 子代理可以专注于特定职责
✅ 需要中央协调器维护整体连贯性

### 不适合的情况

❌ 子任务之间高度相互依赖
❌ 需要子代理间频繁的信息共享
❌ 无法预先规划分解策略
❌ 子代理需要长时间积累上下文

## 关键设计考虑

### 1. 任务分解策略

**按上下文分解** (推荐):
```
主任务: "分析一个电商网站的用户体验"
分解:
- Agent A: 分析移动端体验
- Agent B: 分析桌面端体验
- Agent C: 分析结账流程
- Agent D: 分析客服交互
```

**按工作类型分解** (避免):
```
主任务: "分析用户体验"
分解:
- Agent A: 研究
- Agent B: 分析
- Agent C: 报告
```
*(这种方式容易产生上下文重叠和重复工作)*

### 2. 子代理专业化

为每个子代理定义明确的专业领域:

```python
SUBAGENT_SPECIALIZATIONS = {
    "security_agent": {
        "scope": "安全漏洞、认证、授权",
        "tools": ["security_scanner", "compliance_checker"],
        "output_format": "漏洞报告"
    },
    "test_agent": {
        "scope": "测试覆盖率、测试用例",
        "tools": ["test_runner", "coverage_analyzer"],
        "output_format": "测试报告"
    },
    "style_agent": {
        "scope": "代码风格、命名约定",
        "tools": ["linter", "style_guide"],
        "output_format": "风格审查"
    }
}
```

### 3. 并行 vs 串行执行

| 执行方式 | 优点 | 缺点 | 适用场景 |
|---------|------|------|---------|
| **并行** | 速度快，利用子代理并发 | 可能产生冲突，资源争用 | 独立子任务 |
| **串行** | 有序，避免冲突 | 速度慢 | 有依赖的子任务 |
| **混合** | 平衡速度和有序 | 复杂度高 | 部分独立的子任务 |

```python
# 定义任务依赖关系
DEPENDENCY_GRAPH = {
    "setup": [],           # 无依赖，可并行
    "code_review": ["setup"],  # 依赖 setup
    "security": ["setup"],
    "final_report": ["code_review", "security"]  # 等待所有前置任务
}
```

### 4. 结果综合策略

#### 简单拼接
```markdown
## 安全审查
{security_output}

## 测试覆盖
{test_output}

## 代码风格
{style_output}
```

#### 智能融合
```python
def synthesize_results(results):
    """
    检测结果间的冲突并解决
    """
    conflicts = detect_conflicts(results)
    if conflicts:
        results = resolve_conflicts(conflicts)
    return format_unified_report(results)
```

#### 级联更新
```
当 Agent A 发现的问题影响 Agent B 的范围时:
1. Orchestrator 通知 Agent B
2. Agent B 重新评估其结果
3. 返回更新后的结果
```

## 使用 DeepAgents 创建示例

使用 deepagents skill 创建:

```
创建 orchestrator agent:
  prompt: "你是一个协调器。接收任务: {task}。
          1. 分解任务为子任务
          2. 委派给合适的子代理
          3. 收集结果
          4. 综合成最终报告"

  subagents:
    - security_agent: "专注于安全检查"
    - test_agent: "专注于测试覆盖"
    - style_agent: "专注于代码风格"

创建 subagents (独立):
  - security_agent: "检查安全漏洞"
  - test_agent: "验证测试覆盖"
  - style_agent: "评估代码风格"
```

## 常见陷阱

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 协调器成为信息瓶颈 | 所有信息必须通过协调器 | 允许子代理间有限的信息共享 |
| 串行执行导致速度慢 | 未利用并行能力 | 分析依赖关系，并行执行独立任务 |
| 子代理范围重叠 | 分解策略不当 | 明确定义每个子代理的专业领域 |
| 结果冲突难以解决 | 缺少冲突检测机制 | 在综合阶段检测和解决冲突 |
| 上下文在传递中丢失 | 多次汇总导致信息损失 | 在结果中保留原始细节，最后才摘要 |

## 扩展变体

### 多层协调器

```
主协调器
  ↓
  一级子协调器 A    一级子协调器 B
  ↓                    ↓
  Agent A1, A2...      Agent B1, B2...
```

### 动态任务分配

```python
def dynamic_allocation(task):
    """
    根据任务特征动态选择最合适的子代理
    """
    if task.type == "security":
        return security_agent
    elif task.type == "testing":
        return test_agent
    else:
        # 创建临时专业化子代理
        return create_specialized_agent(task)
```

### 自适应工作流

```python
class AdaptiveOrchestrator:
    def __init__(self):
        self.patterns = learned_decomposition_patterns

    def decompose(self, task):
        # 根据历史学习调整分解策略
        pattern = self.patterns.match(task.type)
        return pattern.apply(task)
```

## 指标监控

- 任务分解效率: 分解是否充分且无重叠？
- 子代理利用率: 是否所有子代理都在工作？
- 并行效率: 并行执行比串行快多少？
- 结果综合质量: 最终输出的连贯性如何？
- 上下文丢失: 在多次传递中丢失了多少信息？
