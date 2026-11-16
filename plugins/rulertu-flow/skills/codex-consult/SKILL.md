---
name: codex-consult
description: 外调 Codex CLI 只读沙箱获取跨模型第二意见或独立执行读任务。当用户点名 Codex、要求跨模型评审或第二意见，或宿主无子代理能力需要外部评审时使用；含授权前提、会话续用与退出码协议。
---

# Codex 外调

把一个自包含任务交给 Codex CLI 独立执行：只读沙箱、JSON 事件流、最终消息落盘。执行层是插件级脚本 [codex_exec.py](../../scripts/codex_exec.py)（相对本技能 `../../scripts/codex_exec.py`）。方案评审专用封装（schema 归一化、轮次状态机）在 plan-iterate 的 `codex_review.py`，复用同一执行层，本技能不重复。

## 授权前提

只在用户明确授权且 codex CLI 已登录可用时运行。可用性以首次调用本身作为冒烟，失败按进程失败处理（退出码 `3`），不回退为同宿主自答。可用环境变量 `CODEX_PROFILE` 注入 `-p <profile>`（如 `glm`，规避宿主账号配额）；未设置时回退旧名 `CODEX_REVIEW_PROFILE`，两者都未设置则无 profile。

## 调用

```
python ../../scripts/codex_exec.py <output> <prompt> [session-id]
```

（Windows 用 `python`，POSIX 用 `python3`；路径按插件根解析。）

- `<output>`：Codex 最终消息落盘路径，父目录自动创建；同名派生 `<主名>.events.jsonl`、`<主名>.stderr.log`、`<主名>.log` 三份产物。
- `<prompt>`：自包含任务描述。固定只读沙箱（`-s read-only -C <仓库根>`），仓库根按调用时所在目录解析，prompt 中引用文件一律用绝对路径。不提供写通道。
- `[session-id]`：续用上一轮会话（传上一轮 stdout 打印的 SESSION_ID）；不传则新会话。

## 退出码

`0` 成功，stdout 打印 `SESSION_ID=` 供续用；`2` 输入错误；`3` 外部进程失败；`4` 协议输出或 session ID 缺失。进程失败可重试一次；再次失败停止并保留产物。返回的意见由调用方核验后采纳，不盲信。
