---
name: rhetra
description: Rhetra-Harness Python 包使用指南（调用级 Agent Harness：版本化 Flow、冻结执行契约、逐调用证据）。当用户提到 "rhetra"、"flow harness"、"接入 rhetra"、"写 flow.yaml"、"rhetra 证据/evidence bundle"、"plan_flow"、"run_flow" 时触发。覆盖五个场景：消费方接入、Flow 定义编写、planner 语法糖路径、证据审查、离线测试替身。
---

# Rhetra — 调用级 Agent Harness 使用指南

本技能提供 `rhetra` Python 包（pip 可安装）的完整使用指南。Rhetra 以可审查执行图
编排 LLM 与 Tool 调用：版本化 Flow 固定流程，每次执行映射回图中的步骤，并提供
冻结执行契约与逐调用证据。

**版本锚点**：本文档基于 rhetra 0.1.0（2026-09，M3「可导入包最小闭环」）。
源码与可运行样例在 `D:/runspace/rhetra-harness/`；API 以其 `rhetra/__init__.py`
的 `__all__`（24 符号）为 0.x 兼容承诺。若包行为与本文档冲突，以源码为准并
更新本技能。

## 场景识别

### 场景 A：接入消费方（在宿主仓库使用 rhetra）

**触发条件：**
- 用户要在另一个项目里安装/导入 rhetra（如 EvoMAV 的 `flow` harness 节点）
- 问"怎么跑一条 flow"、"run_flow 怎么用"

**工作流程：**
1. 安装与最小闭环 → [[references/quickstart.md]]
2. 选择调用形态：显式 flow（`run_flow(flow=...)`）还是任务规划（`run_flow(task=...)`，见 [[references/planner.md]]）
3. API 细节 → [[references/python-api.md]]

### 场景 B：编写 / 修改 Flow 定义

**触发条件：**
- 用户要写或改 `flow.yaml`、定义 Step / transition / 输入输出 schema
- `validate` 或 `freeze` 报 SpecErrorList / PreflightError

**工作流程：**
1. Flow 结构、三类 Step、五类 transition、版本约束 → [[references/flow-definition.md]]
2. 资源快照（snapshot）结构同在该文档——Step 选择器靠它解析
3. 静态校验闭环：`rhetra validate` → `rhetra freeze`（见 quickstart）

### 场景 C：planner 语法糖路径（无预定义 flow）

**触发条件：**
- 用户只有一段任务描述，想让 planner 临时生成 flow
- 提到 `plan_flow`、`PlannerError`、Draft、`save_flow`

**工作流程：**
1. `run_flow(task=...)` 语法糖与零特权路径语义 → [[references/planner.md]]
2. `plan_flow` 直调（planner_model 显式指定 / hints）
3. 采纳草案落盘为版本化 flow：`save_flow` 三态版本语义

### 场景 D：证据审查与测试

**触发条件：**
- 用户要核对一次执行的证据（events / verify / viewer）
- 要为接入方写自动化测试（离线替身、断言纪律）

**工作流程：**
1. Bundle 结构、verify 三态、大产物溢出、viewer → [[references/evidence.md]]
2. 离线测试：`mode="offline"` + `offline_kit` 注册表注入替身 → [[references/evidence.md]]
3. 三层断言纪律（终态 / 结构 / hash 一致）→ [[references/evidence.md]]

---

## 核心概念

### Rhetra 是什么？

固定流程执行库（flow harness），三项能力承诺：**图可审查、执行可观测、Flow 固定流程**。

| 概念 | 说明 | 载体 |
|------|------|------|
| **版本化 Flow** | flow.yaml 声明执行图：三类 Step + 五类 transition + 输入输出 schema | `flow.yaml`（受限 YAML 子集） |
| **资源快照** | Step 选择器（operation/tool/model）的版本与实现清单 | `snapshot.json`（entries 列表） |
| **冻结执行契约** | 执行前 preflight：归一化 → 选择器解析 → 契约冻结（含 hash 身份） | `build_frozen_execution` / `frozen.json` |
| **证据账本** | 每次调用逐事件落盘、manifest 封口、可机械核验 | Evidence Bundle（`events.jsonl` 等） |
| **零特权路径** | planner 生成的 flow 与显式 flow 走同一准入/冻结/证据通道 | `run_flow(task=...)` |
| **执行模式** | `mode="auto"`（真实模型栈，fail closed）/ `mode="offline"`（确定性替身） | `run_flow(mode=...)` |

三类 Step：`transform`（确定性操作）、`tool`（外部工具调用）、`llm`（模型调用 + prompt）。
五类 transition：`next`、`fork`/`join`（配对）、`switch`/`merge`（配对）。

### 顶层心智模型

```
flow.yaml + input + snapshot.json
   → build_frozen_execution（preflight 冻结，失败异常外显）
   → InvocationRunner.run（LangGraph 1.2.7 编译驱动）
   → RunResult + Evidence Bundle（<work_dir>/<flow_id>/<flow_version>/<invocation_id>/）
   → result.evidence.verify() == "finalized" 即证据完整封口
```

准入失败（SpecErrorList / PreflightError / UsageError / PlannerError / 装配
ValueError / SecretResolutionError / 证据持久化 OSError）从 `run_flow` 以异常
外显，不包装为 RunResult——准入失败没有 Invocation，无证据可持。

---

## 参考文档索引

| 文档 | 内容 | 何时读 |
|------|------|--------|
| [[references/quickstart.md]] | 安装、CLI 五命令、最小 Python 闭环、退出码、异常面 | 优先：任何场景先读 |
| [[references/flow-definition.md]] | flow.yaml 全结构、Step/transition/引用语法、快照结构 | 场景 B |
| [[references/python-api.md]] | 24 个公开符号逐个说明、RunResult/EvidenceHandle | 场景 A |
| [[references/planner.md]] | task 语法糖、plan_flow、Draft、save_flow | 场景 C |
| [[references/evidence.md]] | Bundle 结构、verify、溢出产物、viewer、离线替身与测试纪律 | 场景 D |

### 官方资源（本机）

- 源码仓库：`D:/runspace/rhetra-harness/`
- 可运行样例：`D:/runspace/rhetra-harness/examples/`（五个脚本，头部 docstring 载明前置）
- 领域术语：`D:/runspace/rhetra-harness/CONTEXT.md`
- 验收门禁：`D:/runspace/rhetra-harness/scripts/acceptance.py`
