---
name: deepagents
description: LangChain Agent Harness 指南，支持创建新 Agent 和编辑现有 Agent 两个场景，当用户提到“deepagents”时触发。覆盖四大组件（执行环境/上下文管理/委托/转向）、MCP、RAG、Harness Profiles、代码解释器、多模态、前端集成与生产部署。
---

# DeepAgents - Agent Harness 使用指南

本技能提供 LangChain DeepAgents 的完整使用指南，根据用户需求自动识别场景并提供相应的解决方案。

## 场景识别

本技能会自动检测用户需求并进入对应场景：

### 场景 A：创建新 Agent

**触发条件：**
- 用户提到"创建 Agent"、"新建 Agent"、"创建新的 AI 助手"
- 表达需要构建具有特定能力的 Agent
- 首次使用 DeepAgents 功能

**工作流程：**
1. **收集用户需求** → 首先参考 [[references/harness.md]] 了解核心能力范围
2. **讨论具体需求** → 根据涉及的功能调用相应文档：
   - 子代理配置：[[references/subagents.md]], [[references/async-subagents.md]]
   - Skills 技能：[[references/skills.md]]
   - Memory 持久化：[[references/memory.md]]
   - 后端系统：[[references/backends.md]], [[references/sandboxes.md]]
   - 人工干预：[[references/human-in-the-loop.md]]
   - 模型配置：[[references/models.md]]
   - 流式输出：[[references/streaming.md]]
3. **生成配置代码** → 首先参考 [[references/customization.md]] 的 API 结构
4. **生成功能代码** → 结合具体功能文档与示例文档
5. 请求用户确认

### 场景 B：编辑现有 Agent

**触发条件：**
- 用户提到"编辑 Agent"、"修改配置"、"添加功能"
- 提及现有代码或配置文件
- 询问如何修改某个设置

**工作流程：**
1. **识别编辑类型** → 参考 [[references/customization.md]] 了解可配置参数
2. **获取功能详情** → 调用具体的功能文档（见场景 A 中的文档列表）
3. **生成修改代码** → 首先参考 [[references/customization.md]] 的 API 结构
4. **生成功能代码** → 结合具体功能文档与示例文档
5. 请求用户确认

---

## 文档参考流程

### 阶段一：收集基本信息

**主要参考：[[references/harness.md]]**

在此阶段，通过了解 Harness 的核心能力范围，收集用户的以下信息（官方组织为四大组件分类）：

| 组件 | 能力 | 可配置项 |
|------|------|----------|
| **执行环境** | 自定义工具 | `tools` 参数 |
| | 虚拟文件系统 | `backend` 参数 |
| | 文件系统权限 | `permissions` 参数 |
| | 代码执行（沙箱 / JS 解释器） | Sandbox Backend / `eval` 工具 |
| **上下文管理** | Skills 按需加载 | `skills` 参数 |
| | Memory 持久记忆 | `memory` 参数 |
| | 摘要与上下文卸载 | 内置中间件 |
| | Prompt Caching | Anthropic 模型默认启用 |
| **委托** | 任务规划 | `write_todos` 工具 |
| | 子代理委派 | `subagents` 参数 |
| **转向** | 人工干预 | `interrupt_on` 参数 |
| **Harness Profiles** | 按 provider/model 打包配置 | profile 注册 |

### 阶段二：讨论具体需求

根据用户关心的功能领域，调用相应的功能文档：

| 功能领域 | 参考文档 |
|---------|---------|
| 子代理配置 | [[references/subagents.md]], [[references/async-subagents.md]], [[references/dynamic-subagents.md]] |
| 技能系统 | [[references/skills.md]] |
| 持久化记忆 | [[references/memory.md]] |
| 后端系统 | [[references/backends.md]], [[references/sandboxes.md]] |
| 人工干预 | [[references/human-in-the-loop.md]] |
| 模型选择 | [[references/models.md]] |
| 流式输出 | [[references/streaming.md]], [[references/event-streaming.md]] |
| 权限管理 | [[references/permissions.md]] |
| 工具与 MCP | [[references/tools.md]], [[references/mcp.md]] |
| Harness Profiles | [[references/profiles.md]] |
| 代码解释器（QuickJS eval） | [[references/interpreters.md]] |
| RAG 与检索 | [[references/rag.md]], [[references/retrieval.md]] |
| 多模态 | [[references/multimodal.md]] |
| 生产部署 | [[references/going-to-production.md]], [[references/fault-tolerance.md]] |

### 阶段三：生成配置代码

**主要参考：[[references/customization.md]]**

`create_deep_agent` 的核心配置结构：

```python
create_deep_agent(
    model: str | BaseChatModel | None = None,
    tools: Sequence[BaseTool | Callable | dict[str, Any]] | None = None,
    *,
    system_prompt: str | SystemMessage | None = None,
    middleware: Sequence[AgentMiddleware] = (),
    subagents: Sequence[SubAgent | CompiledSubAgent | AsyncSubAgent] | None = None,
    skills: list[str] | None = None,
    memory: list[str] | None = None,
    response_format: ResponseFormat[ResponseT] | type[ResponseT] | dict[str, Any] | None = None,
    backend: BackendProtocol | BackendFactory | None = None,
    interrupt_on: dict[str, bool | InterruptOnConfig] | None = None,
    permissions: list[FilesystemPermission] | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    ...
) -> CompiledStateGraph
```

### 阶段四：生成功能代码

根据具体功能需求，参考相应的功能文档和示例：

| 代码类型 | 主要参考 | 辅助参考 |
|---------|---------|---------|
| 子代理定义 | [[references/subagents.md]] | [[references/subagents_examples.md]] |
| 技能创建 | [[references/skills.md]] | 官方示例 skills |
| Human-in-the-loop | [[references/human-in-the-loop.md]] | [[references/hitl_examples.md]] |
| 后端配置 | [[references/backends.md]], [[references/sandboxes.md]] | [[references/customization.md]] 示例代码 |
| 工具定义 | [[references/customization.md]] Tools 章节 | 通用 LangChain 工具文档 |

---

## 核心概念

### DeepAgents 是什么？

DeepAgents 是 LangChain 提供的 Agent Harness，按官方最新组织方式提供四大组件能力：

| 组件 | 说明 | 内置工具/参数 |
|------|------|----------|
| **执行环境** | 工具、虚拟文件系统、权限、代码执行 | `tools`, `backend`, `permissions`, `execute`/`eval` |
| **上下文管理** | Skills、Memory、摘要卸载、Prompt Caching | `skills`, `memory` |
| **委托** | 任务规划与子代理 | `write_todos`, `task` |
| **转向** | 人工干预 | `interrupt_on` |

另有 Harness Profiles 按 provider/model 打包可复用配置（见 [[references/profiles.md]]）。

---

## 完整参考文档索引

### 核心文档（按使用顺序）

1. [[references/harness.md]] - **优先参考**：收集需求时了解核心能力
2. [[references/customization.md]] - **优先参考**：生成配置代码时的 API 结构

### 功能文档（按功能领域）

| 功能领域 | 主文档 | 示例/辅助文档 |
|---------|-------|--------------|
| 子代理 | [[references/subagents.md]], [[references/async-subagents.md]] | [[references/subagents_examples.md]], [[references/dynamic-subagents.md]] |
| 技能系统 | [[references/skills.md]] | - |
| 持久化记忆 | [[references/memory.md]] | - |
| 后端系统 | [[references/backends.md]] | [[references/sandboxes.md]] |
| 人工干预 | [[references/human-in-the-loop.md]] | [[references/hitl_examples.md]] |
| 权限管理 | [[references/permissions.md]] | - |
| 模型配置 | [[references/models.md]] | [[references/profiles.md]]（Harness Profiles） |
| 流式输出 | [[references/streaming.md]] | [[references/event-streaming.md]] |
| 上下文工程 | [[references/context-engineering.md]] | - |
| 工具与 MCP | [[references/tools.md]] | [[references/mcp.md]] |
| 代码解释器 | [[references/interpreters.md]] | - |

### 应用场景文档

| 场景 | 参考文档 |
|------|---------|
| RAG | [[references/rag.md]] |
| 检索 | [[references/retrieval.md]] |
| 数据分析 | [[references/data-analysis.md]] |
| 深度研究 | [[references/deep-research.md]] |
| 评测（Rubric） | [[references/rubric.md]] |
| 多模态 | [[references/multimodal.md]] |

### 前端集成文档

| 文档 | 说明 |
|------|------|
| [[references/frontend/overview.md]] | 前端组件总览与架构 |
| [[references/frontend/sandbox.md]] | 沙箱 UI 组件 |
| [[references/frontend/subagent-streaming.md]] | 子代理流式渲染 |
| [[references/frontend/todo-list.md]] | 任务列表 UI 组件 |

### 入门与生态文档

| 文档 | 说明 |
|------|------|
| [[references/overview.md]] | Deep Agents 总览 |
| [[references/quickstart.md]] | 快速上手 |
| [[references/comparison.md]] | 与其他框架对比 |
| [[references/a2a.md]] | A2A 协议集成 |
| [[references/acp.md]] | ACP 协议集成 |
| [[references/code-link.md]] | Code Link |
| [[references/content-builder.md]] | Content Builder |
| [[references/openwiki.md]] | OpenWiki 集成 |
| [[references/going-to-production.md]] | 生产化指南 |
| [[references/fault-tolerance.md]] | 容错机制 |
| [[references/changelog-py.md]] | Python 版变更日志 |
| [[references/changelog-js.md]] | JS 版变更日志 |

### 官方资源

- [Deep Agents 官方文档](https://docs.langchain.com/oss/python/deepagents/)
