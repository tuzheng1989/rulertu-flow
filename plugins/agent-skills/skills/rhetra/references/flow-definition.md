# Flow 定义 — flow.yaml 结构与资源快照

> 完整真实样例：`D:/runspace/rhetra-harness/cases/civil-rescue/flow.yaml`。
> 本文档按该案例归纳，写 flow 时以它为模板。

## 顶层骨架

```yaml
schema_version: 1            # 恒为 1
flow_id: civil-rescue-plan   # 全局标识
flow_version: 1.0.0          # SemVer
description: ...
input_schema: {...}          # JSON Schema（flow 输入的准入校验）
entry: extract_tasks         # 起始 step id
steps: [...]
transitions: [...]
output_schema: {...}         # flow_output 的准入校验
outputs: {...}               # 输出装配：引用哪些 step 输出的哪些路径
```

**受限 YAML**：flow 源经 `parse_restricted_yaml` 解析——YAML 的受限子集，
不支持任意标签等危险构造。JSON 是合法输入（`load_flow` 对 JSON/YAML 同源处理；
`FlowDefinitionV1` 经 `model_dump` 序列化为 JSON 文本即是合法 flow 源）。

## 三类 Step

每个 step 公共字段：`id` / `type` / `description` / `required` / `inputs` /
`output_schema`；按 type 追加**选择器**：

| type | 选择器字段 | 绑定资源 kind | 说明 |
|------|-----------|--------------|------|
| `transform` | `operation: {id, version}` | `operation` | 确定性变换（纯函数） |
| `tool` | `tool: {id, version}` | `tool` | 外部工具调用（HTTP 等） |
| `llm` | `model: {id, version}` + `prompt` | `model` | 模型调用，输出须符 output_schema |

- `version` 支持 SemVer 区间：`1.0.0`（精确）、`'>=1.0.0'`、`'>=1.0.0,<2.0.0'`。
  预发布版（如 `1.0.0a1`）在 resolve 层 fail closed，flow 侧点名不可用。
- `required: true|false`：非必需步（如 switch 的分支兜底）在图结构校验中
  的准入语义不同，复制样例时注意 civil-rescue 的 `full_plan`/`partial_plan` 用法。
- `llm` 的 `prompt` 是消息列表（`role: system|user` + `content`），content 中
  `{{字段名}}` 占位符在执行时以该步 `inputs` 的实际值填充。

## inputs 引用语法

```yaml
inputs:
  incident: {ref: flow_input, path: /incident}                    # flow 输入的 JSON Pointer
  weather:  {ref: step_output, step: check_weather, path: /facts} # 前驱 step 输出
  plan:
    one_of:                                                         # 多源择一（switch 分支汇聚）
      - {ref: step_output, step: full_plan, path: /plan}
      - {ref: step_output, step: partial_plan, path: /plan}
```

- `path` 是 JSON Pointer（`/` 起始，数组下标可用，如 `/incident/regions/0/adcode`）。
- 只能引用前驱可达的 step 输出（图结构校验强制）。

## 五类 transition

```yaml
transitions:
  - {id: gather_facts, type: fork, from: extract_tasks, to: [check_weather, check_devices]}
  - {id: facts_ready,  type: join,  fork: gather_facts, from: [check_weather, check_devices], to: propose_plan}
  - {id: validate_next, type: next, from: propose_plan, to: validate_plan}
  - id: choose_plan
    type: switch
    from: validate_plan
    cases:
      - id: valid
        when: {op: eq, left: {ref: source_output, path: /hard_constraints_passed}, right: {value: true}}
        to: full_plan
    default: partial_plan
  - {id: plan_ready, type: merge, switch: choose_plan, from: [full_plan, partial_plan], to: assemble_result}
```

- `fork`/`join` **按 id 配对**（join 引用 `fork: <id>`）：并行分支全完成才放行。
- `switch`/`merge` **按 id 配对**（merge 引用 `switch: <id>`）：条件分支汇聚。
- `when` 的 `left` 用 `ref: source_output`（switch 源 step 的输出），`right` 用字面量。

## outputs 装配

```yaml
outputs:
  report: {ref: step_output, step: assemble_result, path: /report}
  plan:
    one_of:
      - {ref: step_output, step: full_plan, path: /plan}
      - {ref: step_output, step: partial_plan, path: /plan}
```

执行产物 `flow_output` 须过顶层 `output_schema`，否则按失败语义收口。

## 资源快照（snapshot.json）

Step 选择器在 preflight 时对快照解析，**执行期不再变更**（冻结语义的根基）：

```json
{
  "entries": [
    {
      "kind": "operation",            // operation | tool | model
      "id": "rescue-extract-op",      // 与 flow 中选择器 id 对应
      "version": "1.0.0",
      "implementation": "rescue-extract-impl",  // adapter 装配键（offline 替身注册键）
      "contract": {
        "input_schema": {...},        // 与 flow step 的 inputs/output_schema 核对
        "output_schema": {...}
      }
    }
  ]
}
```

- 快照即资源菜单：planner 的规划上下文、`run_flow` 的 adapter 装配、preflight
  的契约核对都从这里取。
- `kind=model` 条目的 `implementation` 在 `mode="auto"` 下解析真实模型
  （API key 走环境变量），`mode="offline"` 下查 `offline_kit.MODEL_SCRIPTS`。
- 真实模型快照可用 CLI 生成：`rhetra import-models <models.json目录> -o snapshot.json`
  （已存在则合并导入，支持 `--provider` / `--model` 过滤）。

## 校验闭环（写 flow 的标准动作）

```bash
rhetra validate <flow.yaml>                                   # 静态：结构/schema
rhetra freeze <flow.yaml> --input <input> --resources <snap>  # preflight：选择器解析+契约冻结
```

validate 只查 flow 本身；freeze 才会暴露选择器解析失败（快照缺条目、版本区间
无解、契约不匹配）。两关都过后再 `run`。对应 Python API：`validate_flow` /
`load_flow` / `build_frozen_execution`。
