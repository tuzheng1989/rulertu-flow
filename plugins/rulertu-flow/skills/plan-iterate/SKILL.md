---
name: plan-iterate
description: 独立评审并迭代方案文档。当用户要求方案迭代、评审方案、方案打分或继续打磨方案时使用；代码差异评审不触发。
---

# 方案评审迭代

对方案最多评审五轮。每轮使用共享 [review schema](scripts/review-schema.json)；`score >= 8.5` 且没有 P0/P1 才达标。中间产物位于 `<plan目录>/.plan-iterate/<plan名>/`：`review-RN.json`、`review-RN.log`、`state.json`；Codex 外调通道另有 `review-RN.events.jsonl` 与 `review-RN.stderr.log`。

## 评审通道

按宿主能力选择，优先级从上到下：

- 子代理通道（默认，宿主有子代理工具且 `rulertu-flow:auditor` 可用）：派 auditor 只读评审，随任务注入方案路径、[review schema](scripts/review-schema.json) 与「仅输出一个符合 schema 的 JSON 对象」要求；把返回的 JSON 原样存为 `review-RN.json` 后，运行 `python scripts/review_common.py normalize <review-RN.json>` 做归一化与严格校验（退出码 `2` 为协议错误），再运行 `python scripts/review_common.py state <plan> <轮次> <review-RN.json>` 写 `state.json`。子代理每轮独立派发、不跨轮复用会话，复审时注入上一轮 JSON。
- Codex 外调通道（宿主无子代理，或用户要求跨模型第二意见时）：运行 `scripts/codex_review.py <plan> <output> [session-id]`，外调 Codex CLI 的只读沙箱做跨模型评审。Windows 直接使用 Python；POSIX 可使用 `codex-review.sh` 转发。

Codex 外调通道只在用户明确授权且目标 CLI 可用时运行；可用性以首轮评审调用本身作为冒烟，失败按进程失败处理，不回退为同宿主自评。原会话无法恢复时，新建目标评审会话并注入上一轮 JSON。

两种通道都核验锚点和代码事实。规范性基线只用于检查变更是否显式、穿透是否完整，不因方案面向未来而否决。每轮将 `backend`、`round`、`plan_path`、`plan_sha256` 和 reviewer/session 标识原子写入 `state.json`。

## 循环

1. 定位用户指定的方案；无法可靠确定时询问路径。
   会话有 `mcp__flow-deck__flow_task` 时，定位后调用 `kind: "iterate"`、`plan: "<plan名>"` 声明当前迭代任务；无该工具时静默跳过。
2. 发起独立评审，读取归一化 JSON，报告评分与 P0/P1/P2 数量。
3. 未达标时派 Executor 只修改该方案文档，逐条实质响应 P0/P1，P2 可说明不采纳理由。
4. 使用同一 reviewer/session 复审当前磁盘内容。最多五轮，无论是否达标都输出逐轮评分、遗留问题和产物路径。

结束迭代（达标、五轮用尽、失败停止、暂停或取消）时，有 `mcp__flow-deck__flow_task` 则调用 `kind: "idle"` 撤下当前任务；恢复迭代时重新声明 `iterate`。

外部脚本退出码：`0` 成功、`2` 输入或 schema 错误、`3` 外部进程失败、`4` 协议输出或 session ID 缺失。进程失败可重试一次；再次失败停止并保留产物。Codex 后端兼容读取旧 `session.txt`，任一通道成功后迁移为 `state.json`。损坏 JSON、布尔型分数或字段不完整均拒绝。
