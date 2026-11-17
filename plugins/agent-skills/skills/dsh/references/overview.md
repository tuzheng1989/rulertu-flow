# DeepSeek Harness 总览

> 精编自官方 `README.md`、`docs/architecture.md`、`docs/cordis-primer.md`、`SAFETY.md`（v0.2.2-rc.3）。

## dsh 是什么

DeepSeek Harness（`dsh`）是 DeepSeek AI 开源的 Agent Harness，口号 **everything-is-a-plugin**：模型适配器、工具注册表、会话日志、Agent 循环本身全部是插件，均可从配置替换。底层由 [Cordis](https://github.com/cordiverse/cordis) 框架驱动。

- MIT 协议；developer preview 阶段，**会有破坏性变更**
- 仓库：<https://github.com/deepseek-ai/deepseek-harness>；文档站：<https://deepseek-harness.github.io/deepseek-harness/>
- 设计论文：*A Programming Paradigm for Spatiotemporal Composability*（arXiv:2608.25512）

## Cordis 五思想

1. **插件是实现 Service 的对象**：可以是带 `inject` / `apply(ctx)` 字段的函数、普通对象、或 `Service` 子类。
2. **Context 是服务的仓库**：服务以稳定键挂载，如 `ctx.tools`、`ctx.llm`、`ctx.sessions`；其他插件按键查找而非导入具体实现。
3. **`inject` 声明依赖**：插件等到所需服务就绪才加载，加载顺序由服务需求表达，无需手工编排启动顺序。
4. **类型化事件通信**：服务经 TypeScript declaration merging 声明事件名，按 `emit` / `waterfall` / `parallel` / `serial` / `bail` 五种模式派发。
5. **注册即副作用**：prompt 段、工具 schema、适配器、provider、监听器都经 `ctx.effect()` / `ctx.on()` 安装，重载与卸载时按注册逆序回退。

## Profile 与 Bundle

一个运行中的 `dsh` 是启动时按有序层组合出的插件树：

- **Profile**：命名组合，存于 Harness home（默认 `~/.dsh`）的 `profiles/<name>`。列出所叠 bundle、持有 out-of-tree 插件依赖与用户自己的 `cordis.patch.yml`。内置五模板：`web` / `headless` / `sdk` / `sdk-minimal` / `acp`。
- **Bundle**：Cordis 配置行及其挂载代码的分发格式。`package.json` 的 `dsh` 字段自声明：`dsh.profile` 列出 profile 的 bundles；`dsh.bundle` 指向 bundle 的 patch 文件。
- **Patch**：按 id 定位配置行并**整行替换其 config**（不深合并），或插入新行。四层叠加（后层胜出）：profile 的有序 bundles → profile 的 `cordis.patch.yml` → home 级 `$DSH_HOME/cordis.patch.yml` → `--patch` 覆盖层（argv 顺序）。
- **`dsh-base`**：`web`/`headless`/`sdk`/`acp` 四 profile 共享的第一层（模型适配器、工具、持久化、沙箱与审批策略、设置、凭据、遥测）。`dsh-sdk-minimal` 是刻意例外：单一 bundle 自持完整显式 SDK 树，不叠 `dsh-base`。

查看本机实际启动的插件树：

```sh
dsh --profile web --dump-config
```

打印的每一行都可以被你自己的 patch 替换。

## 核心包与服务

| 包 | 职责 | ctx 键 |
|---|---|---|
| `core/session` | 追加式 `SessionEvent` 日志与内存存储 | `ctx.sessions` |
| `core/system-prompt` | Prompt 段与工具 schema 组装 | `ctx.systemPrompt` |
| `core/tools` | 作用域工具注册表与守卫执行管线 | `ctx.tools` |
| `core/agent` | `Agent` 接口、live 注册表、`agent/*` 事件 | `ctx.agents` |
| `core/agent-loop` | 默认驱动器（实现上述接口） | `ctx.agentLoop` |
| `core/scope` | 每-Agent 作用域注册原语 | 库，无键 |
| `llm/llm` | 消息与流词汇表 + 适配器接缝 | `ctx.llm` |

会话日志是模型所见上下文的唯一来源（**model-visible means logged**：模型可见即入日志）。`turn/*`、`step/*`、`system/message`、`user/message`、`assistant/message`、`tool/*` 是持久会话事件；fork、resume、回放、遥测均从持久结算派生。

## 事件三域

- **Session 事件**：追加进日志的事实，经 `session/event` 广播——需要跨重载存活的事实用它。
- **Agent 事件**（`agent/*`）：携带 live Agent（inbox、step、status、request、validation、continuation）——观察或拦截进行中的工作用它。
- **能力事件**：把策略与适配器挂到接缝（`fs/*`、`tools/*`、`telemetry/*`）——不导入循环本体。

注意：`turn/*`、`step/*`、`tool/call`、`tool/result` 是**持久会话事件类型**，不是同名 Cordis 事件；要观察它们，监听 `session/event` 并检查 `event.type`。`agent/pre-step`、`agent/request`、`llm/stream`、`tools/*` 三事件是 waterfall，监听器**必须调用 `next()`** 委托下游。

## 扩展点速查（新行为挂哪里）

| 目标 | 机制 |
|---|---|
| 新增模型 provider | 在 `ctx.llm` 注册适配器（见 [[llm-adapters.md]]） |
| 新增模型可见能力 | 在 `ctx.tools` 注册工具；schema 自动进 prompt 组装（见 [[tools.md]]） |
| 给单个会话不同能力集 | 组合 agent preset；其中的服务行需要 `isolate` realm |
| Shell 执行 | 注册 `ctx.shell` 后端；本地实现经 `ctx.subprocess` 派生 |
| 持久终端 | 注册 `ctx.terminals` 后端 + `dsh-tool-terminal` |
| 人工命令 | 在 `ctx.commands` 注册；派发不经过模型回合 |
| 后台任务管理 | 在 `ctx.jobs` 注册；`job_*` 工具读取或停止任务 |
| 外部 webhook 启动会话 | 在 `ctx.webhookRuntime` 注册受信规则并挂 provider 适配器 |
| 文件系统访问或策略 | 注册 `ctx.fs` provider 或监听 `fs/*` 事件 |
| 限制派生进程 | 用 `ctx.sandbox` 后端；消费方在派生前包裹 argv |
| 拦截请求/工具/回合 | 用对应 `agent/*` 或 `tools/*` 事件；`agent/turn-stopping` 停回合 |
| 新增模型可见上下文 | 调 `agent.inject()`；落入下一个被接受的请求 |
| UI / 编辑器集成 | 驱动 `ctx.agents` 并从 `session/event` 渲染 |
| 持久会话状态 | 扩展 `SessionEventMap`；从日志渲染与回放 |
| 会话标题生成 | 注册唯一的 `ctx.sessionTitle` provider |
| 回合边界 fork | `ctx.agents.create({ sessionId, seed, inheritedEventCount, meta: { isSeeded: true } })` |
| 会话存新后端 | 实现 `SessionPersistence`（`create`/`open`/`stat`/`list`/`export`） |
| 把注册限定到单个 Agent | 用该 Agent 的 `agent.ctx` |

对应的手把手指南（仓库 cookbook）：`docs/cookbook/adding-a-tool.md`、`adding-an-llm-adapter.md`、`adding-a-package.md`、`adding-a-settings-card.md`、`extension-cookbook.md`。

## Turn / Step 语义

- **Step** = 一次模型请求 + 它调用的工具；**Turn** = 零或多个 step，首个输入被认领前开启，无欠账时关闭。
- 简化流：`turn/start` → 组装 prompt 段与 step 准入工具 schema → `step/start` → `agent/request` → 流式产出（`assistant/message`）→ `tool/call*` → `tools/pre-execute → tools/execute → tools/post-execute` → `tool/result*` → `step/end` →（工具欠新请求或有下一 step 输入则继续）→ `turn/end`。
- 失败 step 会记录缺失的工具结果；重试不重复组装与 `agent/pre-step`。

## 安全须知（SAFETY）

dsh 是实验性 developer-preview 软件，**未经安全审计，不得视为安全或生产就绪**。它能执行模型生成的代码与命令、加载三方插件、访问网络/进程/凭据/文件。

- 沙箱、审批、权限控制**只降低风险，不保证隔离**；不得作为不可信工作负载的唯一安全控制。
- 责任使用：最小权限；优先一次性虚拟机/容器/专用环境；对可访问文件做备份；不暴露敏感凭据；运行前审查插件、配置与待批命令。
- 典型事实：`sdk-minimal` profile 锁定 `danger-full-access`（持久 shell 可改运行时可见的任意路径），务必用一次性目录/容器；`web_fetch` 免逐次审批且可达环回与内网地址。

## 与同类框架的关系

dsh 与 LangChain DeepAgents 同属 "Agent Harness" 范畴，但路线不同：DeepAgents 以 `create_deep_agent()` 单函数组装（Python），dsh 以 Cordis 插件树 + profile/patch 组合（TypeScript），扩展面下沉到配置层。需要对比选型时可参考本插件 deepagents 技能。
