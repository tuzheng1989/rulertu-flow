# Python API — 公开符号手册

> `rhetra/__init__.py` 的 `__all__`（24 符号）即 0.x 兼容承诺。按用途分组。

## 1. 执行入口

### `run_flow(flow=None, *, task=None, input=None, resources=None, work_dir="evidence", mode="auto") -> RunResult`

顶层便捷入口，固定走全流程、不跳审查：归一化 → `build_frozen_execution` →
`InvocationRunner.run`。

- `flow` 与 `task` **恰好传一个**（都传/都不传 → `UsageError`）。
  - `flow`：路径 | YAML/JSON 源文本 | `FlowDefinitionV1`；
  - `task`：语法糖路径，先经 `plan_flow` 规划（见 [[planner.md]]）。
- `input`：必传，路径 | dict（路径走受限 YAML 解析，根必须是对象）。
- `resources`：必传，路径（JSON）| dict | `ResourceSnapshot` 实例。
- `work_dir`：证据落盘根，**恒落盘不接受 None**。
- `mode`：`"auto"`（真实 adapter，缺凭据/依赖 fail closed）| `"offline"`（确定性
  替身）。mode 在任何资源装配前校验。

异常面见 [[quickstart.md]]：准入失败异常外显，不进 RunResult。

### `RunResult`（project_result dict 的只读薄包）

| 属性 | 类型 | 说明 |
|------|------|------|
| `.status` | `str` | completed / failed / cancelled |
| `.output` | `Any` | `flow_output`（过 output_schema 的最终产物） |
| `.usage` | `dict` | usage_summary（token 等用量汇总） |
| `.invocation_id` | `str \| None` | 本次调用 id（Bundle 目录名） |
| `.frozen_execution_hash` | `str \| None` | 冻结契约 hash（执行身份） |
| `.failure` | `dict \| None` | 失败时的结构化原因 |
| `.step_outcomes` | `dict[str, str]` | 各 step 终态 |
| `.conformance` | `dict` | 合规核对结果 |
| `.evidence` | `EvidenceHandle` | 本次 Bundle 句柄 |
| `.raw` | `dict` | 原始 project_result（逃生口） |

### `EvidenceHandle`（Bundle 只读薄包）

- `.bundle_dir -> Path`：`<work_dir>/<flow_id>/<flow_version>/<invocation_id>/`
- `.events -> list`：`load_events` 的转发（逐事件账本）
- `.verify() -> str`：`verify_bundle` 的转发，期望 `"finalized"`

## 2. Flow 读写与校验

| 符号 | 签名要点 | 说明 |
|------|---------|------|
| `validate_flow` | `(flow) -> None` | 静态校验；不合法抛 `SpecErrorList` |
| `load_flow` | `(text) -> FlowDefinitionV1` | 从 YAML/JSON 源文本加载+校验 |
| `load_flow_value` | `(value: dict) -> FlowDefinitionV1` | 从已解析 dict 加载+校验 |
| `save_flow` | `(flow, dir, version=None) -> FlowDefinitionV1` | 三态版本语义，见 [[planner.md]] |

## 3. Preflight 冻结族（细粒度控制）

`run_flow` 内部即这条链，需要单独落盘冻结契约或复用 runner 时直用：

| 符号 | 说明 |
|------|------|
| `build_frozen_execution(flow_source, input_value, snapshot, *, input_source_bytes=None) -> (plan, FrozenExecutionDefinition)` | preflight 冻结：选择器解析、契约核对、冻结身份 |
| `FrozenExecutionDefinition` | 冻结产物类型（含 `definition` 与执行身份） |
| `ConstraintsV1` / `EvidencePolicyV1` | 冻结契约中的约束与证据策略 |
| `component_profiles` | 组件 profile 冻结身份（adapter 强身份） |
| `persist_frozen_definition` | 冻结契约落盘（freeze 命令的实现内核） |
| `PreflightError` | preflight 失败异常 |

## 4. 执行内核

| 符号 | 说明 |
|------|------|
| `InvocationRunner(frozen, *, model_adapters, tool_adapters, transform_registry, evidence_root)` | 单次调用执行器；`.run() -> dict`（project_result） |
| `compile_execution_plan` | flow → LangGraph 执行计划（编译层，自定义宿主接入用） |

`run_flow` 的 `mode` 只影响 adapter 装配：
- `"offline"` → `build_offline_adapters(snapshot)`（替身注册表，见 [[evidence.md]]）；
- `"auto"` → `build_runtime_adapters(snapshot)`（真实栈，惰性导入；缺重依赖时报
  `ImportError` 指引安装 `rhetra[live]`）。

## 5. 证据

| 符号 | 说明 |
|------|------|
| `verify_bundle(directory) -> str` | 机械核验 Bundle：finalized / incomplete / corrupt |
| `load_events(directory) -> list[EvidenceEvent]` | 读回逐事件账本 |

细节（Bundle 布局、溢出产物、viewer）见 [[evidence.md]]。

## 6. 资源

| 符号 | 说明 |
|------|------|
| `ResourceSnapshot` | 快照模型：`model_validate(dict)` 构造；`.entries` / `.resolve(kind, id, constraint)` 公开解析 |

## 7. Viewer

| 符号 | 说明 |
|------|------|
| `serve(work_dir="evidence", *, port=8765, dist=None, open=False)` | 本地只读 viewer（阻塞；dist 三段解析：显式 → 包内 viewer_dist → 开发回退） |
| `build_server(...)` | 同内核的非阻塞变体（返回 server 对象，宿主自管生命周期） |

## 8. Planner（PEP 562 惰性）

| 符号 | 说明 |
|------|------|
| `plan_flow(task, *, resources, planner_model=None, hints=None, work_dir="planner_drafts") -> FlowDefinitionV1` | 见 [[planner.md]] |
| `PlannerError(stage, code, message)` | 规划失败（选模/装配/重试耗尽） |

## 9. 异常

| 符号 | 说明 |
|------|------|
| `UsageError(ValueError)` | 调用方用法错误；CLI 退出码 64 |
| `SpecErrorList` | flow 定义不合法（`rhetra.contracts.errors`，随公开面可捕） |

## 接入模式速查

```python
# 常规：一次调用
result = run_flow(flow, input=..., resources=..., work_dir=..., mode=...)
if result.status != "completed":
    ...result.failure...
assert result.evidence.verify() == "finalized"

# 宿主自定义装配：冻结 → 自备 adapter → runner（EvoMAV 同进程适配器走这条）
from rhetra import build_frozen_execution, InvocationRunner
_, frozen = build_frozen_execution(flow_source, input_value, snapshot)
runner = InvocationRunner(frozen, model_adapters=..., tool_adapters=...,
                          transform_registry=..., evidence_root=...)
raw = runner.run()
```
