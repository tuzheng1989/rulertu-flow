# B3 委派单：阶段缩减 5→2（验证全绿即收口）

方案详案：`plans/flow-deck/2026-11-11-deck-deps-progress-persistence.md`（B3 节）——本单为执行摘要，锚点与详案冲突时以详案为准。

## 目标

每批上报从五阶段（开工/派单/执行/验证/收口）缩为两阶段（执行/验证）——错误主形态是漏报，调用次数 5→2 直接降漏报面。**核心设计：上报契约两值，内部状态五值兼容**——收口不消失，变为验证全绿的谓词（`testsPassed === testsTotal ≥ 1`），progress 存量值、通关卡、撤任务、清边界、轨道图 done 判定等下游全部零改动，唯一收敛点在处理器。

## 验收标准（原文）

| # | 断言 |
|---|------|
| G14 | 验证全绿自动收口：撤任务、清边界、通关卡、progress 终态、轨道图 done，与显式收口逐项等价 |
| G15 | 验证部分通过不升格（8/10 仍验证态） |
| G16 | 显式收口兼容；`开工`/`派单` 存量值渲染退化不崩 |
| G17 | 每批上报调用次数 5 → 2；SKILL.md/README/types 三处口径一致且单一出处 |

（G13/G8 真机项归最终波次收口，不在本单。）

## 改动锚点与边界（B2 后行号有漂移，以内容定位为准）

| 文件 | 锚点 | 改动 |
|------|------|------|
| `plugins/flow-deck/hooks/register.tsx` | flow_report 注册块（:1184 起） | inputSchema `phase` 描述改：`'当前阶段：执行 \| 验证；验证上报全绿（testsPassed === testsTotal 且 ≥1）自动收口，无需再报收口'` |
| 同上 | flow_report 处理器 closurePhase 判定（内容定位 `const closurePhase`） | `report.phase === '收口'` 放宽为 `(report.phase === '收口' \|\| report.phase === '验证')`，其余条件（testsTotal >= 1 && testsPassed === testsTotal）不动 |
| 同上 | stamped 构造（内容定位 `const stamped: ExecutionReport`） | closurePhase 成立时 `phase: '收口'`——**唯一升格点**，此后全部下游走既有分支零改动 |
| `plugins/flow-deck/hooks/parse.ts` | :195-199 phaseProgress | 阶段表 `['开工','派单','执行','验证','收口']` → `['执行','验证']`；存量值 indexOf -1 → total 0 退化纯文字（现状未知阶段同行为） |
| `plugins/rulertu-flow/skills/implement-plan/SKILL.md` | :18（B2 刚改写过，本批再改同一句） | 上报纪律改两阶段口径（详案原文第 5 条，含 backfill 句保留） |
| `plugins/flow-deck/types/index.d.ts` | :71 ExecutionReport.phase 注释 | 改：上报契约两值；收口为内部终态（验证全绿升格或显式上报，存量值可能为旧五枚举） |
| `plugins/flow-deck/README.md` | :13 与 :19 | Spinner 行与 flow_report 描述同步两阶段口径 |
| `plugins/flow-deck/hooks/parse.test.ts` | :264 一带 | 既有五阶段断言改两阶段；新增退化用例 |
| `plugins/flow-deck/hooks/register.test.ts` | 新用例 + 旧措辞清扫 | 见测试规格；P2 清扫：内容定位「store 出口留待端到端」旧措辞更新（只改注释） |
| 双 manifest + CHANGELOG.md | version / Unreleased | 0.22.0 → 0.23.0 + 条目 |

## 测试规格

1. **L1**：`phaseProgress('执行') → {index:1,total:2}`、`('验证') → {index:2,total:2}`、`('开工') → total 0`；
2. **L2 升格等价**：`flow_report(plan, B1, phase:'验证', testsPassed:10, testsTotal:10)` → currentTask 撤下、closureCard 组装、progress 记 `收口`、lastRun 写入——与显式收口路径逐项等价（可对照既有收口用例断言集）；
3. **L2 不升格**：`phase:'验证', testsPassed:8, testsTotal:10` → 不收口，显示验证 2/2 与测试进度条 warn 色；
4. **L2 兼容回归**：显式 `phase:'收口'` 既有用例全过；
5. 注意 backfill 交互：backfill 补报 `phase:'收口'` 直写 progress 不经 closurePhase 判定（D11 旁路），既有 B2 用例回归即证。

## 零改动验证项（回报确认）

`spinnerWord`（hooks/parse.ts，直接消费 phase 字符串）与 `phaseText`（hooks/register.tsx，只映射执行/验证两皮肤词）未被触碰。

## 回报要求

G14-G17 逐条 PASS/FAIL + 证据；测试命令、退出码、通过/失败数（日志落盘本目录）；升格收敛点唯一性确认（diff 中仅 stamped 一处写 `收口` 升格）。
