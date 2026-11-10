# B1 方案文档勘误留痕（补记，回应审计 P2-1）

- 执行者：主控（非 Executor，主控职责行为）
- 时机：B1 修订轮收口阶段（Executor 停止写入后）
- 改动文件：`plans/work-skills/2026-11-10-producthunt-research-channel.md`（当时未在 B1 边界内，主控更新批次边界后执行）
- 改动内容：
  1. 第 0 节子命令参数表按 `mcp-tools-schema.json` 实测修订（`--slug`→`--name`、leaderboard 去掉 `--period` 且 `--date` 必填、limit 上限 8 clamp 注记）
  2. 第 0 节末尾追加「实施期勘误」引注块，指向本证据目录的 schema 落盘文件
- 依据链：Executor 修订轮报告 §裁决 1（tools/list 探测授权）→ schema 落盘 → 主控裁决参数定稿 → 方案文档同步勘误
- 审计引用：B2 审计报告 P2-1（判定为 B1 sanctioned 勘误、非 B2 越界；建议补留痕，即本文件）
