---
name: plan-iterate
description: 独立评审并迭代方案文档。当用户要求方案迭代、评审方案、方案打分或继续打磨方案时使用；代码差异评审不触发。
---

# 方案评审迭代

对方案最多评审三轮。每轮使用共享 [review schema](scripts/review-schema.json)；`score >= 8.5` 且没有 P0/P1 才达标。中间产物位于 `<plan目录>/.plan-iterate/<plan名>/`：`review-RN.json`、`review-RN.log`、`state.json`；外部后端另有 `review-RN.events.jsonl` 与 `review-RN.stderr.log`。

## 后端选择

- Codex 宿主：创建一个 plan-iterate 专用的新上下文只读评审代理，注入方案路径、schema 和评审口径；同一线程的后续轮次对同一代理 follow-up。新线程无法恢复时创建新代理并注入上一轮 JSON。
- Claude Code：运行跨平台 `scripts/codex_review.py <plan> <output> [session-id]`。Windows 直接使用 Python；POSIX 可使用 `codex-review.sh` 转发。真实外部调用只在用户已明确授权且 CLI 已登录时执行。

两种后端都核验锚点和代码事实。规范性基线只用于检查变更是否显式、穿透是否完整，不因方案面向未来而否决。每轮将 `backend`、`round`、`plan_path`、`plan_sha256` 和 reviewer/session 标识原子写入 `state.json`。

## 循环

1. 定位用户指定的方案；无法可靠确定时询问路径。
2. 发起独立评审，读取归一化 JSON，报告评分与 P0/P1/P2 数量。
3. 未达标时派 Executor 只修改该方案文档，逐条实质响应 P0/P1，P2 可说明不采纳理由。
4. 使用同一 reviewer/session 复审当前磁盘内容。最多三轮，无论是否达标都输出逐轮评分、遗留问题和产物路径。

外部脚本退出码：`0` 成功、`2` 输入或 schema 错误、`3` Codex 进程失败、`4` 协议事件或 session ID 缺失。进程失败可重试一次；再次失败停止并保留产物。脚本兼容读取旧 `session.txt`，成功后迁移为 `state.json`。损坏 JSON、布尔型分数或字段不完整均拒绝。
