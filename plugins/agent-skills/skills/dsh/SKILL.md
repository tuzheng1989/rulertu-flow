---
name: dsh
description: DeepSeek Harness（dsh）Agent 底座使用指南，覆盖四个场景——运行部署、SDK 应用集成、插件开发、Profile 配置调优，当用户提到 "dsh"、"deepseek harness"、"deepseek-harness" 或需要在 dsh 上搭建 Agent 应用时触发。内容基于官方仓库 deepseek-ai/deepseek-harness 文档精编：Cordis 插件框架、五种内置 Profile（web/headless/sdk/sdk-minimal/acp）、模型接入（DeepSeek 与 OpenAI 兼容网关）、工具/服务/事件/LLM 适配器扩展、TypeScript 与 Python SDK、Bundle 打包发布与插件市场。
---

# DeepSeek Harness（dsh）使用指南

本技能为「以 dsh 为底座快速搭建 Agent 应用」提供指引，根据用户需求自动识别场景并路由到对应参考文档。

> **版本锚点**：本技能基于官方仓库 `deepseek-ai/deepseek-harness` v0.2.2-rc.3（2026-11）文档精编。dsh 处于 developer preview，**会有破坏性变更**；若包行为与本文冲突，以[源仓库](https://github.com/deepseek-ai/deepseek-harness)与[文档站](https://deepseek-harness.github.io/deepseek-harness/)为准并更新本技能。

## 场景识别

本技能自动检测用户需求并进入对应场景：

### 场景 A：运行与部署 dsh

**触发条件：**
- 用户提到「安装 dsh」「跑起来」「启动 Web UI」「部署」
- 询问 `npx @deepseek-ai/dsh web`、headless 一次性任务、ACP/SDK 服务化启动
- 询问如何配置模型（DeepSeek API key、第三方 provider、自建网关）

**工作流程：**
1. 安装与启动 → [[references/quickstart.md]]
2. 模型接入（key、网关、协议、推理档位）→ [[references/models.md]]
3. 涉及 profile 组合与覆盖 → [[references/profiles-and-patches.md]]
4. 部署前安全评估 → [[references/overview.md]] 安全须知一节

### 场景 B：用 SDK 构建 Agent 应用

**触发条件：**
- 用户提到「SDK」「嵌入到我的应用」「Python/TypeScript 调用」「programmatic」
- 需要在自有进程里驱动 dsh 完成任务（JSON-RPC 子进程模式）

**工作流程：**
1. 选型与快速上手 → [[references/sdk.md]]（TypeScript `@deepseek-ai/dsh-sdk-client` / Python `deepseek-harness-sdk`）
2. 选择 profile 与传入 patch → [[references/sdk.md]] + [[references/profiles-and-patches.md]]
3. 需要审批、用户提问、会话恢复等交互控制 → [[references/sdk.md]] 对应小节
4. 内置能力不够、需要装插件 → 转场景 C/D

### 场景 C：开发插件扩展 dsh

**触发条件：**
- 用户提到「写插件」「加工具」「自定义 tool」「新增模型 provider」「扩展」
- 询问 `defineTool`、Service、事件监听、LLM adapter 的写法

**工作流程：**
1. 第一个插件（三种形式、生命周期、依赖注入）→ [[references/plugin-basics.md]]
2. 按扩展点选文档：
   - 模型可见工具：[[references/tools.md]]
   - 服务与事件、可替换能力（三角色设计）：[[references/services-and-events.md]]
   - 接入新模型 provider：[[references/llm-adapters.md]]
3. 打包发布（bundle、安装、版本兼容）→ [[references/publishing.md]]
4. 判断新行为该挂哪个扩展点 → [[references/overview.md]] 扩展点速查表

### 场景 D：配置与调优现有 Profile

**触发条件：**
- 用户提到「改配置」「cordis.patch.yml」「换默认模型」「加/减工具」「team mode」
- 询问 patch 覆盖、组合顺序、`--dump-config`、HMR

**工作流程：**
1. 组合模型（bundle/patch 四层顺序）→ [[references/profiles-and-patches.md]]
2. 常见定制配方（str_replace_editor、Team mode、shell 栈切换等）→ [[references/profiles-and-patches.md]]
3. 涉及插件层本身 → 转场景 C

---

## 核心概念（五分钟心智模型）

| 概念 | 一句话 | 关键事实 |
|------|--------|----------|
| **dsh** | DeepSeek 开源的 Agent Harness，口号 everything-is-a-plugin | 模型适配器、工具注册表、会话日志、Agent 循环全部是可替换插件 |
| **Cordis** | 底层插件框架：插件向共享 ctx 贡献服务、类型化事件与可回退副作用 | 插件 = 导出 `apply(ctx)` 的模块；`inject` 声明依赖；注册即 effect，卸载自动清理 |
| **Profile** | 一个可启动的组合，位于 `$DSH_HOME/profiles/<name>` | 内置五模板：`web`（浏览器 UI）/ `headless`（一次性任务）/ `sdk`（JSON-RPC）/ `sdk-minimal`（独立最小树）/ `acp`（自动化 stdio） |
| **Bundle** | 插件配置层的 npm 分发格式 | package.json 里 `dsh.bundle` 声明 patch 文件；`dsh plugin add` 安装进 profile |
| **Patch** | 覆盖配置的 YAML 层（`cordis.patch.yml`） | 按 id 替换整行 config（不深合并）或插入新行；四层叠加，后层胜出 |
| **SDK** | 从外部进程驱动完整 dsh runtime | TypeScript 与 Python 双实现，同一 JSON-RPC 协议，子进程惰性启动 |
| **ctx 服务** | 插件挂在 ctx 上的具名能力 | `ctx.tools` / `ctx.llm` / `ctx.agents` / `ctx.sessions` / `ctx.systemPrompt` 等 |

**四层组合顺序**（后层按行覆盖前层）：
`bundles 依序` → `profile 的 cordis.patch.yml` → `$DSH_HOME/cordis.patch.yml`（机器级）→ `--patch` 覆盖层（argv 顺序）

**默认路径**：`DSH_HOME` 默认 `~/.dsh`；Web 默认 `http://127.0.0.1:3080`；npm 包名 `@deepseek-ai/dsh`。

---

## 完整参考文档索引

### 本地参考（references/，按使用顺序）

| 文档 | 内容 | 何时读 |
|------|------|--------|
| [[references/overview.md]] | 定位、架构、核心服务、事件三域、扩展点速查、安全须知 | 任何场景前建立全局认识 |
| [[references/quickstart.md]] | 安装三路径、五种 Profile、CLI 速查、Web UI 引导 | 场景 A |
| [[references/models.md]] | DeepSeek/三方/自定义网关、四协议、compat 开关、推理档位 | 场景 A/B 的模型接入 |
| [[references/profiles-and-patches.md]] | 组合机制、dump 三命令、HMR、常用定制配方 | 场景 A/D |
| [[references/plugin-basics.md]] | 第一个插件、三种形式、生命周期、Schemastery 配置 | 场景 C 入门 |
| [[references/tools.md]] | defineTool DSL、内置工具目录 | 场景 C 加工具 |
| [[references/services-and-events.md]] | 服务、五种事件模式、三角色能力设计 | 场景 C 进阶 |
| [[references/llm-adapters.md]] | LlmAdapter、StreamChunk 协议、注册与接线 | 场景 C 接新模型 |
| [[references/sdk.md]] | TypeScript/Python SDK 全用法 | 场景 B |
| [[references/publishing.md]] | bundle 打包、安装、版本兼容、插件市场 | 场景 C 分发 |

### 官方文档映射（溯源用）

| 主题 | 仓库路径（docs/ 下） | 文档站 |
|------|---------------------|--------|
| 架构总览 | `architecture.md` | [架构](https://deepseek-harness.github.io/deepseek-harness/) |
| 用户指南 | `user/guide/` | 同上 |
| 插件开发教程 | `user/develop/basic|framework|practice/` | 同上 |
| Cordis 入门 | `cordis-primer.md`、`cordis-tutorial/` | 同上 |
| 子系统参考 | `subsystems/*.md` | 同上 |
| 配置目录（生成） | `config-catalog.md` | 同上 |
| 工具目录（生成） | `tool-catalog.md` | 同上 |
| CLI 行为参考 | `../apps/cli/reference/README.md` | 仓库内 |

### 官方资源

- 源仓库：https://github.com/deepseek-ai/deepseek-harness
- 文档站：https://deepseek-harness.github.io/deepseek-harness/
- 插件生态：GitHub topic [`dsh-plugin`](https://github.com/topics/dsh-plugin)
