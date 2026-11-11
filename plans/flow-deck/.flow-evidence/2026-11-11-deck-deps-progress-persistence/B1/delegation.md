# B1 委派单：flow-deck 轨道图跨会话状态持久化 + 拓扑下推

方案详案：`plans/flow-deck/2026-11-11-deck-deps-progress-persistence.md`（B1 节，五要素全文）——本单为执行摘要，锚点与详案冲突时以详案为准。

## 目标

flow-deck 插件的轨道图（依赖图 DAG）跨会话丢状态：`progress` 与 `deps` 两个内存 atom 在 session.start 被清空，一批一个会话的实施常态下轨道图消失、历史批次回落「待执行」。本批实现三件事：

1. **持久化**：`flow_report` / `flow_deps` 处理器更新 atom 后经 `$.store` 持久化（两个新键）；
2. **恢复**：session.start 把清空替换为「store.get + parse 防御 + 恢复」，坏形状降级为现状空值；
3. **拓扑下推**：`depStatuses` 渲染纯函数加依赖闭包传播——任一节点 done ⇒ 其 dependsOn 闭包（含传递）强制 done，phase 置「收口」。

## 验收标准（原文，逐条 PASS/FAIL + 证据）

| # | 断言 |
|---|------|
| G1 | store.get 返回合法 progress+deps → session.start 后同方案实施任务的面板出现 DAG 区块，B1 done、B2 pending、`1/2 收口` |
| G2 | store.get 坏形状 → 恢复降级为空，无 DAG、无异常，行为同现状 |
| G3 | store.get 默认 undefined（全部既有用例）→ 行为逐字节同改前 |
| G4 | flow_report / flow_deps 工具返回值不因持久化失败变错误（best-effort，try/catch + debug log） |
| G5 | `parseProgressMap` 四例通过（合法全收 / 整体非对象 null / 混合值剔非 string / 空对象合法） |
| G6 | types 注释、README 句、双 manifest 0.21.0、CHANGELOG 条目落盘 |
| G7 | `claude plugin test plugins/flow-deck` 全绿 + `claude plugin validate plugins/flow-deck` 通过 |
| G9 | 拓扑下推：B2 收口 B1 无记录 → B1 显示 done 且文本「收口」、n/m 计数含推导节点；末批漏报维持现状；dependsOn 引用不存在批次不崩 |

（G8 真机跨会话往返由主控收口时执行，不在本单范围。）

## 改动锚点与边界（全部改动限于以下文件）

| 文件 | 锚点 | 改动 |
|------|------|------|
| `plugins/flow-deck/hooks/register.tsx` | :67 | EXECUTION_STORE_KEY 后加 `PROGRESS_STORE_KEY = 'progressMap'`、`DEPS_STORE_KEY = 'depsGraph'` |
| 同上 | :216 后 | 新增模块顶层函数 `readPersistedProgress($)`（try store.get + parseProgressMap，null/异常 → `{}`）、`readPersistedDeps($)`（try store.get + parseDepGraph，异常 → null） |
| 同上 | :1094-1095 | 两行清空替换为「先取后写」恢复（update 回调保持同步纯函数：`const stored = await read...; await update($, atom, () => stored)`） |
| 同上 | :1424 后 | progress update 后加 `await persistProgress($)`（read 最新 map → store.set，try/catch + `$.ui.log(..., { to: 'debug' })`，范式同 :1444-1448） |
| 同上 | :1476 后 | deps update 后加 `await persistDeps($, graph)`（值直接传入，同 try/catch 范式） |
| 同上 | :645 与 :780 | 节点文本行 `progressMap[...] ?? '待执行'` 改用推导后 `node.phase`（:645 用 cardNodes 的 node） |
| `plugins/flow-deck/hooks/parse.ts` | :411 后 | 新增顶层纯函数 `parseProgressMap(value: unknown): Record<string, string> \| null`：整体非对象/数组 → null；逐键收 string 值；空对象合法 |
| 同上 | :413-426 | `DepNode` 加 `phase: string` 字段；`depStatuses` 改两遍：第一遍现状逐节点查表；第二遍拓扑下推（栈迭代 + 已处理集合；dependsOn 引用不存在批次名跳过；有环时已处理集合保证终止） |
| `plugins/flow-deck/types/index.d.ts` | :177 / :179 | progress / deps 注释补「经 `$.store` 键 `progressMap` / `depsGraph` 跨会话恢复」 |
| `plugins/flow-deck/README.md` | :21 | 「依赖图只在实施对应方案时显示」句后补持久化恢复口径 |
| `plugins/flow-deck/.claude-plugin/plugin.json` + `.codex-plugin/plugin.json` | version | 0.20.0 → 0.21.0（两处同步） |
| `CHANGELOG.md`（仓库根） | Unreleased | 加 flow-deck 0.21.0 条目（持久化 + 拓扑下推合并一条） |
| `plugins/flow-deck/hooks/parse.test.ts` | 新用例 | `parseProgressMap` 四例 + `depStatuses` 下推四例（见下） |
| `plugins/flow-deck/hooks/register.test.ts` | 新用例 | 恢复-渲染往返 / 坏形状降级 / 拓扑下推渲染三个 mount 用例（见下） |

## 实现接缝（TDD 红绿循环）

- **L1 纯函数接缝**：`parseProgressMap`、`depStatuses`——先写测试（红）再实现（绿），每轮一个接缝一个测试；
- **L2 mount 接缝**：session.start 恢复链路（store.get mock 分流）与 DAG 渲染断言；
- **测试替身边界**：mock 用既有 `on('store.get', ...)` 钩子（register.test.ts:402 先例）；`store.set` 测试引擎无设施（register.test.ts:922 注释先例，走 catch 分支即常态失败路径，G4 由既有用例回归覆盖）。

## 锚点 → 定向测试命令映射

| 改动锚点 | 定向测试 |
|---------|---------|
| parse.ts 两个纯函数 | `claude plugin test plugins/flow-deck`（L1 用例含其中；无单测过滤设施时全量即定向，规模可接受） |
| register.tsx 恢复/持久化/文本行 | 同上（L2 mount 用例） |
| 收尾（types/README/manifest/CHANGELOG） | `claude plugin validate plugins/flow-deck` + git diff 人工核对 |

## L2 用例规格

1. **恢复-渲染往返**：`on('store.get')` 分流返回 `{ 'demo#B1': '收口' }` 与 `{ plan: 'demo', batches: [{batch:'B1'},{batch:'B2',dependsOn:['B1']}] }` → `session.start` → `flow_task` implement demo → mount → 断言 DAG 区块标题、`✓ B1`（done 色）、`○ B2`（pending dim）、`1/2 收口`；
2. **坏形状降级**：store.get 返回 `'garbage'` / `{ plan: 123 }` → session.start → flow_task implement demo → mount → 无 DAG 区块、无异常；
3. **拓扑下推渲染**：store.get 返回 progress `{ 'demo#B2': '收口' }`（B1 无记录）+ deps B1→B2 链 → mount → `✓ B1` 且 B1 文本行「收口」（非「待执行」）、`2/2 收口`。

注意：store.get 钩子入参是否携带 key（U1）——有 key 按 key 分流；无 key 用闭包变量按调用序切换（session.start 内 get 顺序固定：progress → deps → lastExecution）。

## 回报要求

- 每条验收 G1-G7/G9 的 PASS/FAIL 与证据（测试输出摘录、diff 摘录）；
- 测试命令、退出码、通过/失败数（完整日志落盘本目录）；
- U1/U2 的实际观察结论（store.get 入参形态、store.set 在测试引擎的失败形态）；
- 零改动验证项的确认：spinnerWord 与 phaseText 未被触碰。
