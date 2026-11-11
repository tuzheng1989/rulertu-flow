# B1 批审计报告（T2 · 证据包模式）

审计人：auditor（独立验证者，只读）。日期：2026-11-11。
被审对象：flow-deck 轨道图跨会话状态持久化 + 拓扑下推（B1 批，目标 0.21.0）。
证据包：本目录 delegation.md / test-final.log / validate-final.log / diff.patch / probe-u1-u2.md。
契约权威：`plans/flow-deck/2026-11-11-deck-deps-progress-persistence.md` B1 详案 + 设计裁决 D1-D10。
主控已抽查复跑测试（154 pass / 0 fail）并标注可采信——本审计未重跑全量，按角色契约对高风险项做静态逐行核验 + 证据交叉对账。

## 总结论

**可收口。** 五项核验全部 PASS，无 P0、无 P1，P2 记档 2 条。G8（真机跨会话往返）按委派单留主控收口时执行，不在本单范围。

## 一、差异范围核验 — PASS

- **证据真实性**：工作区 `git diff` 与证据包 diff.patch 逐字节一致（raw 与 CRLF 归一后双重比对均 IDENTICAL）；stat 为 9 文件 230 insertions / 17 deletions，与 Executor 回报一致。
- **边界吻合**：diff 涉及 9 个文件——register.tsx、parse.ts、parse.test.ts、register.test.ts、types/index.d.ts、README.md、双 manifest、根 CHANGELOG.md——全部落在委派单锚点表边界内，无边界外文件、无顺手改。（注：主控转述口径「边界 10 文件」，委派单锚点表实际归并为 9 个不同文件，diff 恰为 9；口径差异在转述，不在证据。）
- **既有断言改动核验（Executor 自述项）**：diff.patch:84-96 中 parse.test.ts 既有用例「depStatuses 按 progress 标注三态」的 `toEqual` 期望数组从 3 字段扩为 4 字段——`status` 三值（pending/done/active）与 `dependsOn` 逐项未动，仅追加 `phase` 字段，且追加值恰为实现第一遍查表语义（无记录→'待执行'、收口→'收口'、执行→'执行'）。属 DepNode 契约扩字段带来的夹具同步，非行为改写。register.test.ts 侧为纯新增三用例（`@@ -409,6 +409,92 @@` 仅 + 行），既有断言零触碰。
- register.tsx 各 hunk 与锚点表逐项对得上：imports（parseProgressMap / DepGraph）、常量 :69-71、四个顶层函数 :222-258、文本行 :687/:822、session.start :1136-1141、persistProgress 调用 :1471、persistDeps 调用 :1524。parse.ts：parseProgressMap :413-422、DepNode.phase :426-430、depStatuses 两遍改造 :432-461。

## 二、契约核验 — PASS（五个子项）

1. **恢复降级语义（G2/G3 前提）**：`readPersistedProgress`（register.tsx:222-229）= try `store.get` + `parseProgressMap(...) ?? {}`，catch → `{}`；`readPersistedDeps`（:231-238）= `parseDepGraph` 透传，catch → null。`parseProgressMap`（parse.ts:415-422）整体非对象/数组/null → null、逐键剔非 string、空对象合法（D9 逐项吻合）；`parseDepGraph`（parse.ts:395-411）对 undefined/坏 plan → null。store.get 默认 undefined 时恢复值恒为 `{}` / null——与旧清空 `() => ({})` / `() => null` 状态值等价，G3「逐字节同改前」成立（既有 149 测全绿为回归实证）。
2. **持久化 best-effort（G4）**：`persistProgress`/`persistDeps`（register.tsx:242-258）与 lastExecution 既有范式（:1491-1495，即委派单所指 :1444-1448 一带）同构：`try { await $.store.set } catch { $.ui.log(..., { to: 'debug' }) }`。U2 探针给出直接证据：测试引擎 store.set 抛 HooksError 被 catch 吃掉、三条持久化失败 debug log 在场而工具返回文案正确。细节：`persistProgress` 的 `read($, progress)` 在 try 外——符合详案评审节点「取 atom 而非重复拼装」，atom 读与处理器内其他 read 同可靠性，非缺陷。
3. **拓扑下推（G9/D10）**：parse.ts:436-461 两遍结构——第一遍查表（现状语义原样），第二遍栈迭代：种子为第一遍 done 节点；`settled` 集合保证终止（每条 dependsOn 边仅在所属节点 settle 时考察一次，环与自环安全）；悬空批次名 `byBatch.get(dep) === undefined → continue` 跳过不崩；上游强制 `status='done'` + `phase='收口'`（对 active 上游亦强制覆盖，与 D10「强制 done」口径一致）。**持久化数据不被改写**：`nodes` 为 `{...node}` 浅拷贝新对象，下推只改拷贝的 status/phase，`progress` 参数与 `graph.batches` 原件零写入；两处调用点（register.tsx:563、:629）均纯渲染消费，无状态回写。
4. **文本行同源**：register.tsx:687（cardNodes 分支）与 :822（主分支）文本行均改用 `node.phase`，状态符号（MARK.done/run/idle）与计数（done filter）同源于 depStatuses 输出；grep 证实 register.tsx 已无裸 `progressMap[...]` 查表残留，无 ✓/「待执行」矛盾路径。L2 用例 3 的 `/待执行/` 全树负断言佐证。
5. **update 回调同步纯函数**：session.start 恢复为「先取后写」（register.tsx:1138-1141）：`const stored = await read...` 在回调外完成，回调 `() => stored` 同步纯函数，与详案伪代码逐行对应。

## 三、测试证据核验 — PASS

- **数量对账**：test-final.log 154 pass / 0 fail（4 文件）。HEAD 基线静态计数 149（parse 55 + register 80 + agents 4 + poll 10）+ 新 5 = 154；工作区计数 parse 57 / register 83 与之吻合。新增 5 测与委派单清单一一对应且全部在 diff.patch 中在场：
  - L1 两测：`parseProgressMap 校验跨会话进度恢复`（diff.patch:66-76，四例合一测）、`depStatuses 拓扑下推`（diff.patch:100-127，四例合一测）；
  - L2 三测：恢复-渲染往返（diff.patch:201-231）、坏形状降级（diff.patch:233-257）、拓扑下推渲染（diff.patch:259-285）。
- **负断言在场**：坏形状无 DAG（diff.patch:253 `执行 DAG` toBeUndefined）；拓扑下推「待执行」全树负断言（diff.patch:282）；末批漏报维持查表（diff.patch:126 `['done','pending','pending']`）。
- **断言与规格一致**：L2 用例 1 断言 DAG 标题 + `✓ B1` color success + `○ B2` dimColor + `1/2 收口`；用例 3 断言 done 色 + `收口 · 起点` 文本行 + `2/2 收口`——与委派单 L2 规格逐条对应。store.get 替身按 key 分流（U1 探针实证载荷 `{"key":...}` 形态）。
- **G6 收尾四件在场**：types/index.d.ts:177/:179 注释（diff.patch:421-425）、README.md 第 21 行段落补持久化口径（diff.patch:46）、双 manifest 0.20.0→0.21.0（diff.patch:21-22、34-35）、根 CHANGELOG Unreleased 条目（diff.patch:9）。
- **G7**：validate-final.log 末行 `Validation passed with warnings`；警告（author/LICENSE/icon）均为仓库级既有状况，与本批 diff 无关；静态扫描行确认 `$.store.get (via readLastExecution, readPersistedDeps, readPersistedProgress), $.store.set` ——新顶层函数被引擎正确识别。
- **零改动验证项**：diff 中无 spinnerWord / phaseText 触碰，对应既有用例在 log 中通过。

## 四、副作用扫描 — PASS

- **session.start**：仅替换 :1090-1091（旧行号）两行清空，其余清空序列（currentTask/execution/batchScope/plans/notified/guardWarned/baselined/agents/ghIssues/stall/doc*/tree*/touched/gitStatus/closureCard）、`firstReportAt.clear()`（:1155）、beat 清零（:1164）、代次门（:1126）逐行未动；lastExecution 恢复 + toast（:1250-1252）原样，D5「恢复不加 toast」遵守。
- **flow_report**：仅 +1 行 `await persistProgress($)`（:1471，progress update 之后、lastRun 写入之前）；closureCard/execution/lastRun/guardWarned/currentTask/batchScope 副作用链与 lastExecution store.set（:1457-1495）零改动；`firstReportAt` 仅 :1420 读、:1507（flow_batch）写，恢复逻辑不触碰。
- **flow_deps**：仅 +1 行 `await persistDeps($, graph)`（:1524），返回值文案未动。

## 五、红线核验 — PASS

diff.patch 全文零 `beat` 命中；register.tsx beat 写入路径未触碰；红线回归用例「红线1：连发 3 次 beat tick，除 beat 外全部 PluginState 键快照不变」在 test-final.log 通过（该断言天然覆盖新恢复键：beat tick 不得写 progress/deps）。

## 问题清单

| 级别 | 条目 | 证据 | 说明 |
|------|------|------|------|
| P2 | register.test.ts:1008、:1053 注释「测试引擎无（store.set）该设施（仅 store.get 钩子可应答）」已被 U2 探针证伪 | probe-u1-u2.md:34-41（引擎提示 `on('store.set', ...)` 可应答） | Executor 已如实上报并与方案调研结论的出入标注「上报主控」，按委派单边界未顺手改注释——处置正确。建议 B2/G8 补写入侧机器断言时一并修正两处注释。 |
| P2 | 写入侧（store.set 落值正确性）本批无机器断言，G4 证据是「catch 分支真实走过 + 工具返回不变」而非「落值正确」 | 委派单「测试替身边界」节 + probe U2 | 方案原判断「测试引擎无该设施」不成立（见上条），真值断言留 G8 真机与 B2。记档不阻断。 |

## 完成度 / 证据真实性 / 契约对齐一览

- 完成度：G1-G7、G9 全部有实现 + 测试 + 产物证据；G8 按单留主控。
- 证据真实性：diff.patch 与工作区逐字节一致；测试日志数量与 HEAD/工作区静态计数对账吻合；U1/U2 探针带原始输出摘录。
- 契约对齐：D2 键名、D3 降级语义、D4 写时机与范式、D5 无 toast、D8 清空语义不动、D9 逐键容错、D10 视图修正不改数据——逐条核过，无弱化。
- 建议下一步：主控执行 G8 真机跨会话往返后收口；B2 开工时消化两条 P2。
