# Planner — task 语法糖路径与 Flow 保存

> 无预定义 flow 时：任务描述 → planner 临时生成 FlowDefinition → 与显式 flow
> **完全同流**执行（零特权路径）。真实样例：`D:/runspace/rhetra-harness/examples/civil_rescue_planner.py`。

## `run_flow(task=...)` 语法糖

```python
result = run_flow(
    task="为灾区生成无人机搜救任务分配建议",
    input="cases/civil-rescue/input-full.json",   # 必传（usage 级校验前置：规划前拦截）
    resources="cases/civil-rescue/snapshot-offline.json",  # 必传（planner 要资源菜单+选模）
    work_dir="evidence",
    mode="offline",
)
```

语义链：`task` → `plan_flow` 规划出 `FlowDefinitionV1`（Draft 落
`<work_dir>/planner/`）→ 作为显式 flow 走同一 `build_frozen_execution` →
`InvocationRunner.run`。生成的 flow 没有任何准入豁免。

**已知语义（README 异常面记档）**：`run_flow(task=...)` 的选模与 adapter 装配
发生在 `plan_flow` 之前——这两阶段的 `PlannerError` **不保证 Draft 存在**；
`plan_flow` 内部任何终止路径均保证原子落盘一个完整 Draft。

## 隐式选模规则（裁定 2）

`task` 形态不传 `planner_model` 时：

- 快照 `kind=model` 条目**恰好一个**且为稳定版 → 用之；
- 零个或多个 → `PlannerError`（报错含 `plan_flow(planner_model=...)` 指引）；
- 唯一条目为预发布版 → 同样 fail closed，指引显式指定。

要精确控制就绕开语法糖直调 `plan_flow`。

## `plan_flow` 直调

```python
from rhetra import plan_flow, PlannerError, run_flow

definition = plan_flow(
    "为灾区生成无人机搜救任务分配建议",
    resources="cases/civil-rescue/snapshot-offline.json",  # ResourceSnapshot | dict（必传）
    planner_model="rescue-planner",   # 显式指定：走快照公开 resolve（"== 点名能力"）
    hints={"偏好": "优先小机型"},       # 可选 dict：进 prompt 文本，须可 JSON 序列化
    work_dir="planner_drafts",        # Draft 落 <work_dir>/planner/
)
# definition 是普通 FlowDefinitionV1：可直接 run_flow(definition, ...)
result = run_flow(definition, input=..., resources=..., work_dir=..., mode=...)
```

- Draft 文件：`<work_dir>/planner/<UTC时间戳>Z-<uuid8>.json`，先建 `plan_id`
  骨架、try/finally 保证任何终止路径原子落盘。
- 规划内部有草案环：产出须过 `load_flow_value` 校验 + 选择器预检，不合法会
  带着重试（`retry_limit` 记录在 Draft 的 `attempts`）。
- `PlannerError(stage, code, message)`：stage 如 `model_resolution`，code 如
  `model_not_unique` / `model_resolve_failed`。

## Draft（advisory 产物）

```python
draft = json.loads(sorted((Path(work_dir) / "planner").glob("*.json"))[0].read_text("utf-8"))
draft["terminal_stage"]            # completed / 失败阶段
draft["model"]                     # {"id": ..., "source": "snapshot"|"explicit"}
draft["adopted"]["definition_hash"]  # 采纳定义的 hash（与显式定义可互核）
draft["attempts"]                  # 重试轨迹
```

**定位**：Draft 不是 Evidence Bundle，**不参与 `verify()`**，仅审计规划过程。

## `save_flow` — 采纳草案为版本化 flow

```python
from rhetra import save_flow
returned = save_flow(definition, "flows/")            # 三态版本语义
returned = save_flow(definition, "flows/", version="1.1.0")  # 显式版本副本
```

三态语义（A5）：

| 调用 | 行为 | 返回 |
|------|------|------|
| 显式 `version` | 副本改写为该版本落盘（须合法 SemVer） | 更新后定义 |
| `version=None` 且 dir 无同 flow_id 既有版本 | 按定义自身版本落盘 | 原定义 |
| `version=None` 且有既有版本 | 按最高既有 semver **bump patch** 落盘 | 更新后定义 |

契约（幂等/冲突）：

- 目标已存在且**同内容**（definition hash 相等）→ 幂等成功，不重写；
- 目标已存在且**异内容** → `ValueError` 拒绝覆盖；
- 目标存在但不可读回 → 同样拒绝（防御坏文件上误判幂等）；
- 并发自动 bump 为 best-effort：异内容并发可能 last-writer-wins。

复用路径（`examples/save_and_reload.py`）：`plan_flow` → `save_flow` 落盘 →
后续 `run_flow(路径)` 直跑，planner 只付一次成本。
