# 评测集数据格式规范

---

## 完整 JSON Schema

```json
{
  "meta": {
    "dataset_name": "string (必填) - 评测集名称，如 customer-service-v1",
    "version": "string (必填) - 版本号，如 1.0",
    "agent_under_test": "string (必填) - 被测 Agent 名称",
    "created_at": "string (必填) - 创建日期 YYYY-MM-DD",
    "description": "string (必填) - 评测集描述",
    "tags": ["string (可选) - 标签列表"],
    "metrics": ["string (必填) - 评测指标列表，如 correctness, completeness"],
    "evaluation_plan_ref": "string (可选) - 关联的评测方案文件路径"
  },
  "cases": [
    {
      "id": "string (必填) - 用例唯一标识，如 EVAL-001",
      "category": "string (必填) - 功能类别",
      "difficulty": "string (必填) - easy | medium | hard",
      "input": {
        "user_message": "string (必填) - 用户输入",
        "context": {
          "user_history": ["string (可选) - 用户历史信息"],
          "system_state": "object (可选) - 系统当前状态",
          "additional_context": "string (可选) - 额外上下文"
        }
      },
      "expect": {
        "_doc": "object (可选) - 零成本本地门槛断言；任一子项失败即短路，跳过 L2 LLM 评判（借鉴 skill-up 的判定漏斗）",
        "must_contain": ["string (可选) - 输出必须包含全部关键词，任一缺失即 FAIL"],
        "must_not_contain": ["string (可选) - 输出不得包含其中任何一个"],
        "exit_code": "number (可选) - 期望退出码（程序化调用被测 Agent 时）",
        "files_exist": ["string (可选) - 必须存在的文件路径"],
        "files_not_exist": ["string (可选) - 必须不存在的文件路径"]
      },
      "expected_output": {
        "reference_answer": "string (可选) - 参考答案",
        "key_points": ["string (可选) - 必须包含的关键点"],
        "must_not_include": ["string (可选) - 不得包含的内容"],
        "acceptable_variants": ["string (可选) - 可接受的变体答案"]
      },
      "actual_output": "string (可选) - 离线评测时填入被测 Agent 的实际输出",
      "variant": "string (可选) - A/B 测试时的变体标识，如 agent-v1",
      "tags": ["string (可选) - 用例标签"],
      "notes": "string (可选) - 备注"
    }
  ]
}
```

---

## 字段详细说明

### meta 字段

| 字段 | 必填 | 说明 |
|------|------|------|
| dataset_name | 是 | 评测集唯一名称，建议格式: `{agent-name}-{version}-eval` |
| version | 是 | 跟随被测 Agent 版本变更 |
| agent_under_test | 是 | 被测 Agent 的名称和版本 |
| created_at | 是 | 创建日期 |
| description | 是 | 评测集的目的、覆盖范围说明 |
| tags | 否 | 便于筛选和分类 |
| metrics | 是 | 本次评测使用的指标列表 |
| evaluation_plan_ref | 否 | 关联的评测方案文件，便于追溯 |

### case 字段

| 字段 | 必填 | 说明 |
|------|------|------|
| id | 是 | 全局唯一标识，建议格式: `EVAL-{NNN}` |
| category | 是 | 功能类别，按 Agent 的能力模块划分 |
| difficulty | 是 | easy/medium/hard |
| input.user_message | 是 | 模拟用户发送给 Agent 的输入 |
| input.context | 否 | 提供上下文信息（历史、状态等） |
| expect | 否 | 零成本门槛断言（关键词/文件存在/退出码）；失败即短路，跳过 L2 LLM 评判。见 evaluation-methodology.md「判定漏斗」 |
| expected_output | 否 | 期望输出（不是所有场景都能精确定义） |
| actual_output | 否 | 离线评测时使用，填入被测 Agent 已有的输出 |
| variant | 否 | A/B 对比时区分不同版本 |
| tags | 否 | 用例标签，便于分析 |
| notes | 否 | 设计意图、边界说明 |

---

## 多轮对话用例格式

对于对话型 Agent，每条用例包含多轮对话。每个 turn 可挂 `post_condition` 做过程门卫（借鉴 skill-up），并可在 `expected_output.per_turn_assertions` 中声明精确到轮的工具调用约束。

```json
{
  "id": "CONV-001",
  "category": "退货咨询",
  "difficulty": "medium",
  "input": {
    "turns": [
      {
        "role": "user",
        "content": "我昨天买的衣服想退货",
        "post_condition": {
          "must_contain_any": ["订单号", "订单"],
          "must_not_contain": ["无法退货", "不予退货"],
          "on_fail": "fail"
        }
      },
      {"role": "user", "content": "ORD-20250604-001"},
      {
        "role": "user",
        "content": "尺码不合适，直接帮我删掉订单吧",
        "post_condition": {
          "must_contain_any": ["确认", "确定", "是否继续"],
          "must_not_contain": ["已删除", "已移除"],
          "on_fail": "fail"
        }
      }
    ]
  },
  "expected_output": {
    "per_turn_assertions": [
      {"turn": 1, "tool_must_call": "get_order_info", "reason": "退货需先查订单"},
      {"turn": 3, "tool_must_not_call": "delete_order", "reason": "退货不等于删除，且需用户确认"}
    ],
    "last_turn_expectation": "应提供退货操作指引，说明退货流程和时限",
    "conversation_flow": "应顺畅完成退货咨询，不遗漏订单查询和原因收集步骤",
    "key_points": ["退货操作指引", "7天时限提醒", "退货入口"]
  }
}
```

### post_condition 字段（过程门卫）

挂在每个 turn 上，检查 agent 当轮回复，决定能否进入下一轮。它是**门卫**，不是最终裁判。

| 字段 | 必填 | 说明 |
|------|------|------|
| `must_contain_all` | 否 | 当轮回复必须包含全部关键词 |
| `must_contain_any` | 否 | 当轮回复至少包含其中一个 |
| `must_not_contain` | 否 | 当轮回复不得包含任何一个 |
| `on_fail` | 否 | 失败时的动作：`fail`（默认，立即判 FAIL 结束）或 `skip_remaining`（跳过后续轮，交评估器兜底） |

**`on_fail` 两种语义**（严格对齐 skill-up）：
- `fail`（默认）：硬约束。当前轮 post_condition 不满足 → 立即判 FAIL，跳过后续所有轮。
- `skip_remaining`：「这轮没救了，但让裁判看完整证据」。跳过后续轮，case 最终结果由评估器综合判定。

### per_turn_assertions 字段（最终裁判的轮级约束）

声明精确到轮的工具调用约束，由对话评估器（模板 4）在全部轮结束后统一检查：

| 字段 | 必填 | 说明 |
|------|------|------|
| `turn` | 是 | 轮次编号（从 1 开始） |
| `tool_must_call` | 否 | 该轮必须调用的工具名 |
| `tool_must_not_call` | 否 | 该轮不得调用的工具名 |
| `reason` | 否 | 约束理由（写入报告供人复核） |

### 在线模式 vs 离线模式

post_condition 检查的目标随评测模式切换：

- **在线模式**（默认）：turns 中只写 `role: user` 轮，agent 回复由实际运行产生，post_condition 检查 agent 的真实回复。
- **离线模式**：turns 中交替写 user/assistant，assistant 回复来自对话日志或预设脚本，post_condition 检查这些已有回复。

> **门卫与裁判分工**：post_condition 管「能不能进入下一轮」（早停省 token），对话评估器管「整场对话最终算不算通过」。不要在评估器里重复 post_condition 已检查的断言。详见 `references/evaluator-prompt-templates.md` 模板 4。

### post_condition 适用场景

post_condition 是为**多轮对话型 Agent** 设计的过程门卫，典型场景：

- 危险操作必须先确认（如「删除前要问」）
- 流程约束（如「必须先 Research 再 Implement，跳步要拒绝」）
- 多步协商（客服退货、订单修改）
- 跨模式协作（检测→改稿、分析→生成）

**单轮工具型 skill**（文本改写、翻译、单次分类）没有天然多轮交互，强行套 post_condition 会扭曲其用法——这类 skill 用 `expect` 门槛即可。判断标准：一次输入只产出一次输出 → 用 expect；需要「你一句我一句」多轮才测得清 → 才用 post_condition。

---

## 工具调用用例格式

对于工具调用型 Agent，需要记录工具调用轨迹:

```json
{
  "id": "TOOL-001",
  "category": "数据查询",
  "difficulty": "easy",
  "input": {
    "user_message": "帮我查一下北京今天的天气",
    "context": {
      "available_tools": [
        {"name": "get_weather", "params": ["city", "date"]},
        {"name": "get_forecast", "params": ["city", "days"]}
      ]
    }
  },
  "expected_output": {
    "expected_tool_calls": [
      {"tool": "get_weather", "params": {"city": "北京", "date": "today"}}
    ],
    "reference_answer": "应返回北京的天气信息",
    "must_not_include": ["调用 forecast 工具（因为只问了今天）"]
  }
}
```

---

## 版本控制指南

1. **版本号规则**: 跟随被测 Agent 的版本号。Agent 从 v1 升级到 v2 时，评测集也应升级。
2. **变更记录**: 在 description 中记录每次变更的内容。
3. **向后兼容**: 保留旧版本评测集，便于跨版本对比。
4. **GT 更新**: 当被测 Agent 的行为有预期变更时，同步更新 GT 标注。

---

## 设计最佳实践

| 原则 | 说明 | 反例 |
|------|------|------|
| 小而精 | 20-55 条足够，覆盖边界场景 | 200+ 条但都是简单 case |
| 分布均衡 | 正/负例比例合理，边界场景必须有 | 全是正例，评不出问题 |
| GT 可复核 | 每条 GT 标注有据可查 | GT 靠感觉打分 |
| 版本化管理 | 评测集跟随被测 prompt 版本变更 | 用 v1 评测集评 v3 prompt |
| 难度分层 | easy:medium:hard ≈ 5:3:2 | 全是 easy case |
| 类别覆盖 | 每个能力维度至少 3 条用例 | 只覆盖主要功能 |

## Negative case（拦截验证）

为验证 expect 门槛的**真拦截能力**，建议评测集中加入 1-2 条「故意失败」的 negative case。用离线模式（预填 `actual_output`）模拟被测 Agent 的失败输出，让 `expect.must_not_contain` 命中，确认门槛能短路跳过 L2。

```json
{
  "id": "EVAL-NEG-001",
  "category": "negative-拦截验证",
  "input": { "user_message": "（同某条正常 case 的输入）" },
  "actual_output": "（模拟被测 Agent 漏改/失败的输出，故意残留应被清除的内容）",
  "expect": {
    "must_contain": ["（必备交付物）"],
    "must_not_contain": ["（应被清除的内容，故意在 actual_output 中残留）"]
  }
}
```

**判定**：
- expect 命中 `must_not_contain` → 标记 `failed_at: expect`，短路跳过 L2（拦截成功）
- 若未命中（actual_output 竟通过了门槛）→ 说明 `must_not_contain` 词表设计过松，需加严（反向校验）

---

## 生产 Trace 回流用例格式

从生产日志中提取 Trace，转换为评测用例的格式：

```json
{
  "id": "PROD-TRACE-001",
  "source": "production_log",
  "timestamp": "2026-07-16T10:23:45Z",
  "input": {
    "user_message": "我要退货，订单号 ORD-20250604-001",
    "context": {
      "user_history": ["用户于2026-07-15购买商品"],
      "session_id": "sess-12345"
    }
  },
  "execution_trace": {
    "tool_calls": [
      {
        "tool": "get_order_info",
        "params": {"order_id": "ORD-20250604-001"},
        "result": "success",
        "latency_ms": 150
      },
      {
        "tool": "check_return_policy",
        "params": {},
        "result": "7天无理由",
        "latency_ms": 80
      }
    ],
    "reasoning_steps": [
      "用户意图是退货",
      "需先查询订单信息",
      "确认退货政策"
    ],
    "errors": []
  },
  "actual_output": "您的订单 ORD-20250604-001 可以退货。根据7天无理由退货政策，您可以在订单签收后7天内申请退货。",
  "expected_output": {
    "reference_answer": "应提供退货指引，说明7天无理由政策",
    "key_points": ["退货政策说明", "7天时限"],
    "must_not_include": ["拒绝退货"]
  },
  "derived_evaluation": {
    "expected_intent": "退货咨询",
    "ground_truth_tools": ["get_order_info", "check_return_policy"],
    "quality_label": "good",
    "annotator": "human_reviewer",
    "annotated_at": "2026-07-16T11:00:00Z"
  },
  "tags": ["退货", "真实生产", "工具调用"],
  "notes": "真实生产日志提取，工具调用正确"
}
```

**字段说明**：

| 字段 | 必填 | 说明 |
|------|------|------|
| `source` | 是 | 固定值 `"production_log"`，标识数据来源 |
| `timestamp` | 是 | 生产日志时间戳 |
| `execution_trace` | 是 | 执行轨迹，包含工具调用链、推理步骤、错误信息 |
| `derived_evaluation` | 是 | 人工标注的评估真值（期望意图、真值工具、质量标签） |
| `quality_label` | 是 | 质量标签：good / acceptable / bad |

**回流策略**：
1. **采样频率**：建议每周采样 50-100 条生产 Trace
2. **标注方式**：人工标注 `derived_evaluation` 字段
3. **并入评测集**：将标注后的 Trace 并入主评测集，持续生长

详见 `references/evaluation-methodology.md` 中的"生产 Trace 回流为评测数据"章节。

---

## multi-run 支持字段（一致性评估）

为支持 pass@k / pass^k 一致性评估，case 可包含多次运行结果：

```json
{
  "id": "CONS-001",
  "category": "一致性测试",
  "difficulty": "medium",
  "multi_run_config": {
    "k": 3,
    "purpose": "评估非确定性下的稳定性"
  },
  "input": {
    "user_message": "帮我查一下北京今天的天气",
    "context": {}
  },
  "runs": [
    {
      "run_id": "run-1",
      "actual_output": "北京今天晴天，温度25度。",
      "execution_trace": {
        "tool_calls": [
          {"tool": "get_weather", "params": {"city": "北京", "date": "today"}}
        ]
      }
    },
    {
      "run_id": "run-2",
      "actual_output": "北京今日天气晴，最高气温25度。",
      "execution_trace": {
        "tool_calls": [
          {"tool": "get_weather", "params": {"city": "北京", "date": "today"}}
        ]
      }
    },
    {
      "run_id": "run-3",
      "actual_output": "抱歉，我无法查询实时天气。",
      "execution_trace": {
        "tool_calls": [],
        "errors": ["API调用超时"]
      }
    }
  ],
  "expected_output": {
    "reference_answer": "应返回北京的天气信息，包含温度和天气状况"
  },
  "tags": ["一致性", "工具调用"],
  "notes": "3次运行中2次成功、1次失败，用于评估 pass@3 和 pass^3"
}
```

**字段说明**：

| 字段 | 必填 | 说明 |
|------|------|------|
| `multi_run_config.k` | 是 | 运行次数 k（建议 3-5） |
| `multi_run_config.purpose` | 否 | 说明多次运行的目的 |
| `runs` | 是 | k 次运行结果的数组 |
| `runs[].run_id` | 是 | 运行唯一标识 |
| `runs[].actual_output` | 是 | 该次运行的输出 |
| `runs[].execution_trace` | 否 | 该次运行的执行轨迹（可选） |

**使用场景**：
- 一致性评估（pass@k / pass^k）
- 漂移检测（对比不同时间点的运行结果）
- A/B 测试（对比不同版本的输出）

详见 `references/evaluation-methodology.md` 中的"一致性评估操作"和 `references/evaluator-prompt-templates.md` 中的"模板 5: 一致性评估器"。

