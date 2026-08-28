---
name: plan-iterate
description: 独立评审并迭代方案文档。当用户要求方案迭代、评审方案、方案打分或继续打磨方案时使用；代码差异评审不触发。
---

# 方案评审迭代

对方案最多评审三轮。每轮使用共享 [review schema](scripts/review-schema.json)；`score >= 8.5` 且没有 P0/P1 才达标。中间产物位于 `<plan目录>/.plan-iterate/<plan名>/`：`review-RN.json`、`review-RN.log`、`state.json`；外部后端另有 `review-RN.events.jsonl` 与 `review-RN.stderr.log`。

## 后端选择

- Codex 宿主：运行 `scripts/claude_review.py <plan> <output> [session-id]`，外调 Claude Code `opus/high` 做只读跨模型评审。Windows 直接使用 Python；POSIX 可使用 `claude-review.sh` 转发。
- Claude Code 宿主：运行 `scripts/codex_review.py <plan> <output> [session-id]`，外调 Codex CLI 的只读沙箱。Windows 直接使用 Python；POSIX 可使用 `codex-review.sh` 转发。

两个外部后端都只在用户明确授权且目标 CLI 已安装、已登录时运行；缺少任一前提时停止并报告，不回退为同宿主自评。后端切换或原会话无法恢复时，新建目标评审会话并注入上一轮 JSON。

两种后端都核验锚点和代码事实。规范性基线只用于检查变更是否显式、穿透是否完整，不因方案面向未来而否决。每轮将 `backend`、`round`、`plan_path`、`plan_sha256` 和 reviewer/session 标识原子写入 `state.json`。

## 循环

1. 定位用户指定的方案；无法可靠确定时询问路径。
2. 发起独立评审，读取归一化 JSON，报告评分与 P0/P1/P2 数量。
3. 未达标时派 Executor 只修改该方案文档，逐条实质响应 P0/P1，P2 可说明不采纳理由。
4. 使用同一 reviewer/session 复审当前磁盘内容。最多三轮，无论是否达标都输出逐轮评分、遗留问题和产物路径。

外部脚本退出码：`0` 成功、`2` 输入或 schema 错误、`3` 外部进程失败、`4` 协议输出或 session ID 缺失。进程失败可重试一次；再次失败停止并保留产物。Codex 后端兼容读取旧 `session.txt`，任一后端成功后迁移为 `state.json`。损坏 JSON、布尔型分数或字段不完整均拒绝。
