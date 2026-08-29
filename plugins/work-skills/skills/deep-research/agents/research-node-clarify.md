# Research Node: Clarify With User

## 任务描述

在进入研究循环前，判断用户的研究主题是否足够明确。若主题过于宽泛或关键要素（范围/受众/深度/输出格式）缺失，生成至多 1 轮澄清提问；否则直接放行。

本节点是**防跑偏的第一道闸门**，借鉴 `open_deep_research` 的 `clarify_with_user`，但强制单轮以避免在 Skill 会话中无限澄清。

## 输入参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `research_topic` | string | 用户提出的研究主题 |
| `user_request` | string | 用户原始完整请求（含可选参数如"循环N次""中文搜索"） |

## 输出格式

输出 JSON 对象，包含判定结果与（可能的）提问列表。

```json
{
  "need_clarification": true,
  "reason": "主题过于宽泛，无法判断研究边界与受众",
  "questions": [
    {
      "q": "研究范围聚焦在哪个层面？",
      "type": "choice",
      "options": ["技术原理", "产业应用", "政策合规"],
      "use_ask_user_question": true
    },
    {
      "q": "报告主要受众是谁？",
      "type": "choice",
      "options": ["技术人员", "管理层", "通用读者"],
      "use_ask_user_question": true
    }
  ]
}
```

若无需澄清：

```json
{
  "need_clarification": false,
  "reason": "主题已含明确限定，范围与受众可合理推断",
  "questions": []
}
```

## 执行逻辑

### 第 1 步：判定 need_clarification

**触发澄清的准则（满足任一即触发）：**
- 主题含泛词且无限定（如「研究一下 AI」「了解下区块链」「调研大模型」）
- 研究范围不明确（技术应用 / 产业 / 政策 / 学术 等层面未界定）
- 目标受众无法合理推断（技术 / 管理 / 通用）
- 研究深度或输出格式存在显著歧义

**不触发的准则（同时满足即放行）：**
- 主题已含明确限定（如「量子计算在密码学中的应用」「Rust 语言的所有权机制」）
- 范围、受众可从主题合理推断

### 第 2 步：生成提问（仅当 need_clarification=true）

- 至多问 **2 个**最关键的问题，优先级：范围 > 受众 > 深度 > 输出格式
- 每个问题标注 `type`：
  - `choice`（选项可枚举，≤4 个）→ `use_ask_user_question: true`，主控流程用 **AskUserQuestion** 工具提问
  - `open`（开放性问题，如"具体关注哪个子方向"）→ `use_ask_user_question: false`，主控流程用**文本**直接提问

### 第 3 步：约束

- **最多 1 轮**。本节点不基于"历史已问过"做循环判断（Skill 会话中由主控流程保证只调用一次）。
- 不要为了澄清而澄清：若任一准则可合理推断，则 `need_clarification=false`。

## 提示词模板

```
你是一个研究意图澄清专家。判断用户的研究主题是否足够明确，必要时生成至多 1 轮澄清提问。

## 输入信息
- 研究主题: {research_topic}
- 用户原始请求: {user_request}

## 判定准则

触发澄清（满足任一）：
- 主题含泛词且无限定（如"研究一下 AI"）
- 研究范围 / 受众 / 深度 存在显著歧义

不触发（同时满足）：
- 主题已含明确限定（如"量子计算在密码学中的应用"）
- 范围、受众可合理推断

## 提问要求（仅当 need_clarification=true）
- 至多 2 个问题，优先级：范围 > 受众 > 深度 > 输出格式
- 选项可枚举(≤4) → type="choice", use_ask_user_question=true
- 开放性问题 → type="open", use_ask_user_question=false

## 输出格式
输出 JSON：
{
  "need_clarification": <bool>,
  "reason": "<判定理由>",
  "questions": [
    {"q": "...", "type": "choice|open", "options": ["..."], "use_ask_user_question": <bool>}
  ]
}

## 判定结果:
```

## 示例

### 示例 1：触发澄清

**输入：**
```json
{ "research_topic": "研究一下 AI", "user_request": "研究一下 AI" }
```

**输出：**
```json
{
  "need_clarification": true,
  "reason": "「AI」是泛词，未限定技术方向、应用领域与受众",
  "questions": [
    {"q": "研究范围聚焦在哪个层面？", "type": "choice", "options": ["核心技术原理", "产业应用与落地", "政策与合规", "学术前沿"], "use_ask_user_question": true},
    {"q": "报告受众是谁？", "type": "choice", "options": ["技术人员", "管理层/决策者", "通用读者"], "use_ask_user_question": true}
  ]
}
```

### 示例 2：直接放行

**输入：**
```json
{ "research_topic": "Rust 语言的所有权机制", "user_request": "深入研究 Rust 语言的所有权机制，循环 4 次" }
```

**输出：**
```json
{
  "need_clarification": false,
  "reason": "主题明确限定在 Rust 所有权机制，受众可合理推断为技术人员",
  "questions": []
}
```

## 注意事项

1. **能推断则不问**：宁可基于合理推断放行，也不要打扰用户
2. **选项要互斥**：choice 类问题的 options 必须互斥、可枚举
3. **开放问题用文本**：open 类问题不要硬塞选项，交给用户自由回答
4. **单轮约束**：主控流程保证本节点只执行一次，节点内不做历史循环判断

## 相关文件

- 上一节点: 主控流程第 1 步（解析请求）
- 下一节点: `research-node-brief.md`（无论是否澄清，均进入 brief 生成）
- 主控流程: `../SKILL.md` 第 1.5 步
