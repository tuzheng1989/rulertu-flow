# B2 委派单：历史批次补报通道（backfill）

方案详案：`plans/flow-deck/2026-11-11-deck-deps-progress-persistence.md`（B2 节 + 设计裁决 D11）——本单为执行摘要，锚点与详案冲突时以详案为准。

## 目标

修「跨会话漏报留存」：implement-plan 现行契约明文"不补报、不重试"（SKILL.md:18），个别 agent 忘了调用 flow_report 后错误静默固化。本批实现：

1. **flow-deck 侧**：`flow_report` 加可选 `backfill: boolean`——纯写 progress + 持久化的旁路，**跳过全部"当前执行"副作用**（closureCard/execution/lastRun/currentTask/batchScope/guardWarned 写入与 firstReportAt 记点）。旁路隔离的必要性：常规通道的收口上报会撤任务清边界（D11），补报历史批次走同链路会破坏当前批次。
2. **implement-plan 技能侧**：开工核对从"只核对不回写"扩展为"核对后补报"（:12），"不补报"旧口径改写（:18）。

## 验收标准（原文）

| # | 断言 |
|---|------|
| G10 | backfill 补报只写 progress + 持久化：currentTask/batchScope/closureCard/firstReportAt 均不变 |
| G11 | 非 backfill 常规上报行为与改前一致（backfill 缺省 falsy） |
| G12 | implement-plan 开工核对含补报口径、"不补报"旧口径已更新、单一出处；双 manifest 0.22.0 + CHANGELOG 条目落盘 |
| G13 | 真机：B1 收口漏报 → B2 会话开工核对补报 → 面板 B1 done 且 B2 任务与边界不受扰（**归最终波次收口，不在本单**） |

## 改动锚点与边界（B1 后行号，±2 偏差以内容定位）

| 文件 | 锚点 | 改动 |
|------|------|------|
| `plugins/flow-deck/hooks/register.tsx` | :1184 起 flow_report 注册块 | inputSchema 加 `backfill: { type: 'boolean', description: '补报历史批次状态：只更新轨道图批次进度，不触碰当前任务、批次边界与通关卡；仅用于开工核对时补齐前序批次' }` |
| 同上 | :1410 处理器 | parse 校验（report === null 报错）之后、**一切副作用之前**分流：`e.backfill === true` → progress update（键 `plan#batch` → phase）+ `persistProgress($)` → 返回 `{ result: '历史批次状态已补报：<plan>#<batch> → <phase>' }`。不触碰下方任何副作用 |
| `plugins/rulertu-flow/skills/implement-plan/SKILL.md` | :12 | 开工检查点"核对前置批次证据"句后接补报口径（详案原文） |
| 同上 | :18 | "不补报、不重试"旧口径改写（详案原文） |
| `plugins/flow-deck/hooks/register.test.ts` | 新用例 + :922 一带 | 见测试规格；顺手修正过时注释（P2-1，只改注释不动逻辑） |
| `plugins/flow-deck/.claude-plugin/plugin.json` + `.codex-plugin/plugin.json` | version | 0.21.0 → 0.22.0（两处同步） |
| `CHANGELOG.md`（仓库根） | Unreleased | 加 flow-deck 0.22.0 条目 |

## 测试规格（hooks/register.test.ts）

1. **backfill 旁路**：flow_task + flow_batch 声明 B2 后，`flow_report(plan, batch:'B1', phase:'收口', backfill:true)` → 断言 progress 收 B1 键、currentTask 仍 B2、batchScope 未清、closureCard 无写入、firstReportAt 无新记点（state.set 序列）、返回文案含「已补报」；
2. **回归**：backfill 后接常规上报，行为与无 backfill 路径一致；全部既有用例不改动通过；
3. **写入侧断言**（B1 探针已证 `on('store.set')` 可应答）：常规 flow_report 后断言 store.set 收到 `progressMap` 键与含新键的完整 map；flow_deps 后断言 `depsGraph`；backfill 后断言 store.set 收到补报后 map；
4. **注释修正**：:922 一带「测试引擎无该设施（仅 store.get 钩子可应答）」更新为 store.set 可应答口径。

## 回报要求

- G10-G12 逐条 PASS/FAIL + 证据；测试命令、退出码、通过/失败数（日志落盘本目录）；
- backfill 分流点对照副作用清单（closureCard 组装/execution 写入/progress 写入/lastRun/currentTask/batchScope/guardWarned/firstReportAt/store.set lastExecution）逐一列「触碰/未触碰」。
