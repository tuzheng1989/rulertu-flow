# 证据与测试 — Bundle、verify、viewer 与离线替身

## Evidence Bundle 结构

每次 Invocation 恒落盘一个 Bundle：

```
<work_dir>/<flow_id>/<flow_version>/<invocation_id>/
  events.jsonl     # 逐事件账本（每次调用一行）
  result.json      # project_result（RunResult.raw 的实物）
  frozen.json      # 冻结执行契约（执行身份）
  plan.json        # 编译后执行计划（与 invocation_started 事件互为逐字节实物）
  manifest.json    # 最后原子写出封口：files 字节 hash + Bundle State
  artifacts/<sha>  # 溢出大产物（hex = ref 的 $artifact 去掉 sha256: 前缀）
```

## `verify()` 三态（机械判据，无人工裁量）

| 返回 | 判据 |
|------|------|
| `"finalized"` | manifest 完整封口、全部 hash 核对通过 |
| `"incomplete"` | 半行 JSON / 无 bundle_finalized / manifest 未写（崩溃中断） |
| `"corrupt"` | hash 不符 |

崩溃后禁止补写冒充 finalized。API：`result.evidence.verify()` /
`verify_bundle(dir)`；事件读回：`result.evidence.events` / `load_events(dir)`。

## 大产物溢出（>64KiB）

tool 步输出超 64KiB 时全量字节溢出到 `artifacts/<hex>`，账本里只留
`$artifact` 引用。恢复 = 读回字节后 `json.loads`；核验 = 重算内容摘要与
ref 的摘要/size 比对。字节序列化口径：
`serialize_candidate(value) == json.dumps(value, sort_keys=True).encode()`。
样例：`examples/large_artifact.py`。

## Viewer（人工核查）

```python
from rhetra import serve
serve(work_dir="evidence", port=8765)   # 阻塞，Ctrl-C 退出，仅绑 127.0.0.1
```

CLI 等价：`rhetra viewer evidence --port 8765`。只读审查 Bundle 树。
dist 三段解析：显式 `dist=` → 包内 `viewer_dist` → 开发回退 `<repo>/viewer/dist`
（都没有则报错指引 build 或传 dist）。

## 离线测试替身（offline_kit）

`mode="offline"` 的确定性通道——**单进程、零外呼、可计数**，消费方写自动化
测试的正规路径。三个注册表（`rhetra.adapters.offline_kit`），键都是快照条目的
`implementation`：

| 注册表 | kind | 替身签名 |
|--------|------|---------|
| `MODEL_SCRIPTS` | model | `fn(inputs: dict) -> {"content": <llm 输出>}` |
| `TOOL_FNS` | tool | `fn(inputs: dict) -> <tool 输出 dict>` |
| `TRANSFORM_FNS` | operation | `fn(inputs: dict) -> <输出 dict>` |

内置 civil-rescue 全套替身；自定义 flow 自注册替身（examples 的标准模式）：

```python
from rhetra import run_flow
from rhetra.adapters.offline_kit import MODEL_SCRIPTS

def _my_model(inputs: dict) -> dict:
    return {"content": {...}}   # 须过该步 output_schema

MODEL_SCRIPTS["my-model-impl"] = _my_model   # 键 = 快照 implementation
try:
    result = run_flow(flow, input=..., resources=..., work_dir=tmp, mode="offline")
finally:
    MODEL_SCRIPTS.pop("my-model-impl", None)  # 用完恢复，别污染注册表
```

自适应脚本模式（见 `examples/civil_rescue_planner.py`）：同一 `implementation`
可能被 planner 调用（`inputs == {}` → 返回 FlowDefinition 草案）和被 step
执行调用（inputs 含业务字段 → 返回业务输出）——脚本内按 inputs 形状分流。

## 三层断言纪律（测试怎么写）

examples 一贯的断言口径——**终态 / 结构 / hash 一致，不做业务值断言**：

```python
# 1. 终态
assert result.status == "completed", f"status={result.status} failure={result.failure}"
assert result.evidence.verify() == "finalized"
# 2. 结构（schema 允许的键集、线程链标记、分支走向）
assert set(result.output) == {"pending_confirmations", "plan", "report"}
# 3. hash 一致（如 planner 采纳定义与显式定义互核）
from rhetra.contracts.flow import flow_definition_hash
assert draft["adopted"]["definition_hash"] == flow_definition_hash(explicit)
```

fake 替身是确定性的：断言行为契约（status/结构），不断言 LLM 业务值。

## 验收门禁参考

消费方 CI 可参考 `D:/runspace/rhetra-harness/scripts/acceptance.py`（六判据
机器可读门禁）与 `pytest -m smoke`（单进程离线、CI ≤10min 的 smoke 圈口径）。
