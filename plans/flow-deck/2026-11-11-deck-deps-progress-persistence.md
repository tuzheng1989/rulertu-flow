# 方案：deck 轨道图跨会话状态持久化

- 方案名：`deck-deps-progress-persistence`
- 日期：2026-11-11
- 状态：待评审
- 涉及插件：flow-deck（B1、B2、B3 工具侧）、rulertu-flow/implement-plan（B2、B3 技能侧）
- 需求来源：用户反馈（2026-11-11 会话）——轨道图更新"经常漏"，多批次跨会话实施时轨道图消失、历史批次状态回落"待执行"
- 修订：v4（2026-11-11）——三轮 argue：拓扑下推（D10）、历史批次补报通道（B2/D11，"全量传递"主张的工程化吸收）、阶段缩减 5→2（B3，用户裁决并入本方案一起做）；auditor 自审修正：路径带 hooks/ 前缀、store.set 时机限定词纠偏（每次上报而非收口时）

## 需求

轨道图（mission-control 皮肤下依赖图/DAG 的称呼）由两路内存数据合成：`deps`（`flow_deps` 声明的静态结构）+ `progress`（`flow_report` 逐批累积的阶段 map）。两者在 `session.start` 被显式清空（hooks/register.tsx:1094-1095），而 implement-plan 的常态是一批一个会话——每个新会话开始，轨道图结构消失、历史批次状态全部丢失，agent 重新 `flow_deps` 只能恢复结构恢复不了状态。

需求：**`progress` 与 `deps` 经 `$.store` 跨会话持久化，`session.start` 恢复而非清空**；新会话声明同方案实施任务后，轨道图自动接续显示，历史批次保持收口/进行中状态。

评审补充（2026-11-11 argue 轮）：`depStatuses` 逐节点独立查表，节点间零校验——单点错误（漏报收口等）静默留存，持久化后跨会话固化；依赖语义下单点错破坏整图可信度（B1 误显「待执行」时，B2 的「进行中」读作越依赖执行）。据此并入渲染层拓扑下推（D10）。

评审补充（2026-11-11 第三轮 argue，用户裁决并入）：错误次数 ∝ 上报调用次数——`flow_report` 每批五阶段（开工/派单/执行/验证/收口）各报一次，漏报面五倍于必要。仅「执行」「验证」是持续耗时阶段（executor / auditor），开工与派单是瞬态且功能已被 `flow_task` / `flow_batch` 声明覆盖。据此缩减上报契约为两阶段（B3）。

### 替代方案的演化（两轮 argue 存档）

用户最初提议"每次更新轨道图传全量状态"。第一轮否决其 `flow_deps` 携带全量状态重传的形态：结构声明与状态上报混一体、"定稿调一次"契约破坏、与 `flow_report` 职责重叠——这些理由与事实前提无关，维持。第一轮论证中"agent 记忆不可靠、重传会把正确节点覆盖坏"一条，经第二轮 argue 修正事实前提后**撤回**：

- 错误主形态是**漏报不是误报**——agent 有方案文档与 git log 可查证，"记错状态"低概率；真实错误是个别 agent 忘了调用（implement-plan SKILL.md:18 现行契约甚至明文"不补报、不重试"）。
- 跨会话场景下**查证式补报比拓扑下推更早修复漏报**——B2 开工时的补报即时生效，拓扑下推要等 B2 收口才能反推 B1。

据此吸收用户主张为 **B2 补报通道**：`flow_report` 加 `backfill` 旁路 + implement-plan 开工核对从"只核对不回写"扩展为"核对后补报"。查证式状态重构落在有上下文的 agent 侧（用户主张），结构推导留在插件渲染层（D10），持久化作底座（B1）——三层互补而非互斥。

## 关键调研结论（方案钉点）

- `EXECUTION_STORE_KEY = 'lastExecution'`（hooks/register.tsx:67）是唯一 store 持久化先例：`flow_report` **每次上报后** `$.store.set` + try/catch 降级（:1444-1448，写入与 phase 无关；"收口时"限定实际属于 lastRun atom 写入 :1426-1428）；`readLastExecution`（:209-216）= `store.get` + `parseExecution` 防御 + null 降级；`session.start` 尾部恢复进 `lastRun` atom 并 toast（:1204-1206）。
- `progress` / `deps` atom 定义于 hooks/register.tsx:78-79，纯内存；`session.start` 清空锚点 :1094-1095（前后均为 await update 清空序列，无顺序依赖）。
- `flow_report` 处理器写 progress 锚点 :1420-1424（update 回调同步拼新 map）；`flow_deps` 处理器锚点 :1471-1478（graph 为局部变量，值在手）。
- `parseDepGraph`（hooks/parse.ts:395-411）已存在，恢复校验直接复用；`parseProgressMap` 需新写（`unknown → Record<string,string> | null`）。
- 渲染合成：`selectTaskView`（hooks/parse.ts:36：`implementing && data.graph?.plan === task.plan`）零改动——恢复的数据经既有过滤链路自然生效；`depStatuses`（hooks/parse.ts:420-426）现状逐节点独立查表、节点间无推导（D10 的改造对象）。DAG 的 done 计数（"n/m 收口"）与流水线连线 `pipelineLinks` 均消费 depStatuses 输出——推导后自动一致；**例外是节点文本行**：hooks/register.tsx:645 与 :780 裸查 `progressMap`，需同步改用推导后 phase，否则 ✓ 符号与「待执行」文本自相矛盾。
- 测试设施：`on('store.get')` 钩子可应答（hooks/register.test.ts:402 先例，返回值可按需构造）；**`store.set` 在测试引擎无设施**（hooks/register.test.ts:922 注释先例），写入侧机器断言不可行，留待真机端到端。
- 类型契约：types/index.d.ts:177-180 progress/deps 注释需补跨会话语义（纯注释，无结构变化）。
- 版本：双 manifest 均 0.20.0；根 CHANGELOG Unreleased 现有 work-skills 2.5.0 等条目，flow-deck 从 0.20.0 顺接 0.21.0，无断档。

## 设计裁决与取舍

| # | 裁决 | 取舍说明 |
|---|------|---------|
| D1 | 持久化 `progress` 与 `deps` 两个独立 store 键，而非合并单键 | 两路数据写入时机不同（report 逐次 / deps 一次）；独立键互不牵连，坏形状互不拖垮 |
| D2 | store 键名 `progressMap` / `depsGraph`（camelCase，沿 `lastExecution` 先例） | 同插件命名空间内一致 |
| D3 | 恢复在 `session.start` 原位替换清空（:1094-1095），先 `store.get` + parse 再 update | 坏形状/不可用降级为空 map / null——与现状行为逐字节一致，降级安全 |
| D4 | 写时机：`flow_report` 的 progress update 后、`flow_deps` 的 deps update 后各自 `store.set`，best-effort try/catch + debug log（沿 :1444-1448 范式） | 持久化失败不阻塞工具返回值，静默降级 |
| D5 | 恢复不加 toast | `lastExecution` toast 是"提醒用户上次执行"；状态恢复是静默背景数据，加 toast 与既有 toast 叠加噪音 |
| D6 | 不做 progress 键清理/淘汰 | 渲染只查当前 graph 的批次，多余键零渲染成本；store 无大小压力；极简优先 |
| D7 | 不做 cwd / 方案名校验 | `lastExecution` 同口径；progress 键自带 `plan#` 前缀天然按方案隔离，deps 渲染要求 `task.plan === graph.plan`（selectTaskView 过滤），同名方案状态延续本就是合理语义 |
| D8 | `currentTask` / `execution` / `batchScope` 清空语义不动 | "新会话从无任务状态开始"（README 契约）保持；恢复的图在 `flow_task`/`flow_batch` 声明同方案实施后才显示，"依赖图只在实施对应方案时显示"契约保持 |
| D9 | `parseProgressMap` 逐键过滤非 string 值，整体非对象才返回 null | 混入个别坏键不丢弃整份进度；与 `parseDepGraph` 逐项容错口径一致 |
| D10 | 渲染层拓扑下推：任一节点 done ⇒ 其 dependsOn 闭包（含传递）强制 done，phase 同步置「收口」 | dependsOn 的定义即"下游收口前上游必已收口"，恒成立、不依赖执行纪律；视图修正不改写持久化数据。覆盖面如实：修**非末批**漏报收口；末批漏报（无下游）与误报收口不覆盖，兜底为同键重新上报覆盖（既有语义）与真机目检 |
| D11 | `flow_report` 加可选 `backfill`：纯写 progress + 持久化的旁路，跳过 closureCard/execution/lastRun/currentTask/batchScope/guardWarned/firstReportAt 全部副作用 | 常规通道的收口上报会撤任务清边界（hooks/register.tsx:1436-1441 副作用链），补报历史批次若走同链路会破坏当前批次状态——旁路隔离是补报可幂等重放的前提（B2） |

## 路线图

| 批次 | 内容 | 级 | 依赖 |
|------|------|----|----|
| B1 | flow-deck：progress/deps store 持久化 + session.start 恢复 + 拓扑下推 + 测试 + 文档收尾（0.21.0） | T2 | — |
| B2 | 历史批次补报通道：flow_report `backfill` 旁路（flow-deck 工具契约）+ implement-plan 开工核对补报纪律（rulertu-flow 技能） | T2 | B1（补报写入复用 persistProgress 通道；无持久化则补报的状态下会话即丢） |
| B3 | 阶段缩减 5→2：上报契约只余「执行 / 验证」，验证全绿自动升格收口（flow-deck 收口判定 + implement-plan 上报纪律，0.23.0） | T2 | B2（implement-plan SKILL.md:18 同句两改须串行；B2 的 backfill 补报写法先定型） |

**粒度裁决**：三批。B1 内部写入侧（两个处理器）与恢复侧（session.start）是同一机制的两个半程——只写不恢复无行为变化，只恢复不写恢复恒空，拆开任何一半都不可独立验收（连续信号）；拓扑下推并入 B1：同文件集（hooks/parse.ts 渲染纯函数 + hooks/register.tsx 两处文本行）、同一验收命令，且其价值前提正是"持久化固化的错误需要视图层自愈"。不立纯验证批与基线批（现有 hooks/register.test.ts 的 session.start 用例群即基线，`store.get` 默认 undefined 的新路径天然降级为现状）。B2 不并入 B1：跨插件文件集（implement-plan 技能文档）、backfill 分流有独立可断言行为、消费 B1 的持久化通道（隔离信号：后序批次消费前序机制的端到端结果）。B3 不并入 B2：收口判定升格与 backfill 旁路是两个独立可验收的契约变化（各自的正反用例互不依赖）；唯一顺序约束是 implement-plan SKILL.md:18 的同句串行。版本号三处回写与 CHANGELOG 属跨插件版本对齐收尾，并入对应改动批次。

---

## B1 详案：flow-deck 轨道图跨会话状态持久化 + 拓扑下推

### 五要素 · 如何改

**契约注释（先锚，纯注释无结构变化）**

- `plugins/flow-deck/types/index.d.ts:177`：progress 注释补"；经 `$.store` 键 `progressMap` 跨会话恢复"。
- `plugins/flow-deck/types/index.d.ts:179`：deps 注释补"；经 `$.store` 键 `depsGraph` 跨会话恢复"。

**hooks/parse.ts（1 个新函数 + 1 个改造）**

- `hooks/parse.ts:411`（parseDepGraph 之后）新增顶层纯函数 `parseProgressMap(value: unknown): Record<string, string> | null`：整体非对象/数组 → null；逐键收 string 值（D9），其余键剔除；空对象合法。
- `hooks/parse.ts:413-426` `DepNode` 加 `phase: string` 字段（推导后阶段，供文本行取用）；`depStatuses` 改两遍：第一遍现状逐节点查表；第二遍拓扑下推（D10）——done 节点沿 dependsOn 闭包传播，上游强制 done 且 phase 置「收口」。栈迭代 + 已处理集合；dependsOn 引用图中不存在的批次名跳过不崩；图有环时已处理集合保证终止。

**hooks/register.tsx（按锚点顺序）**

1. `:67` EXECUTION_STORE_KEY 之后加常量 `PROGRESS_STORE_KEY = 'progressMap'`、`DEPS_STORE_KEY = 'depsGraph'`（D2）。
2. `:216` readLastExecution 之后新增两个模块顶层函数（引擎静态扫描约束：收 `$` 的辅助必须顶层 function）：
   - `readPersistedProgress($): Promise<Record<string, string>>` —— try `store.get(PROGRESS_STORE_KEY)`，`parseProgressMap` 为 null 时返回 `{}`；catch 返回 `{}`（D3 降级）。
   - `readPersistedDeps($): Promise<DepGraph | null>` —— try `store.get(DEPS_STORE_KEY)`，`parseDepGraph` 结果透传；catch 返回 null。
3. `:1094-1095` 两行清空替换为恢复（D3/D8，其余清空行零改动）：
   ```ts
   await update($, progress, () => await …)  // 不可行：update 回调同步
   ```
   实际形态（先取后写，回调保持同步纯函数）：
   ```ts
   const storedProgress = await readPersistedProgress($)
   await update($, progress, () => storedProgress)
   const storedDeps = await readPersistedDeps($)
   await update($, deps, () => storedDeps)
   ```
4. `:1424` progress update 之后加 `await persistProgress($)`：新顶层函数，`read($, progress)` 后 `store.set(PROGRESS_STORE_KEY, 最新 map)`，try/catch + `$.ui.log(..., { to: 'debug' })`（D4）。
5. `:1476` deps update 之后加 `await persistDeps($, graph)`：同 try/catch 范式，值直接传入（D4）。
6. `:645` 与 `:780` 节点文本行：`progressMap[...] ?? '待执行'` 改用推导后 `node.phase`（:645 用 cardNodes 的 node）——与状态符号同源，消除 ✓ 与「待执行」文本自相矛盾（D10）。

**测试**

- L1（hooks/parse.test.ts）`parseProgressMap` 四例：合法对象全收 / 整体非对象（字符串、数组、null）返回 null / 混合值剔除非 string 键保留其余 / 空对象合法返回 `{}`。
- L1（hooks/parse.test.ts）`depStatuses` 拓扑下推四例：B2 收口 + B1 无记录 → B1 推导 done 且 phase「收口」；B3 收口沿 B2→B1 链式传递；dependsOn 引用不存在批次名 → 跳过不崩；末批漏报（无下游）→ 维持查表结果（覆盖面负断言）。
- L2（hooks/register.test.ts，沿 :402 store.get 先例与 :1468 DAG 用例形态）：
  1. **恢复-渲染往返**：`on('store.get')` 按调用顺序或 key 分流返回 `{ 'demo#B1': '收口' }` 与 `{ plan: 'demo', batches: [{ batch: 'B1' }, { batch: 'B2', dependsOn: ['B1'] }] }` → `session.start` → `flow_task` implement demo → mount → 断言 DAG 区块标题在、`✓ B1`（done 色）、`○ B2`（pending dim）、`1/2 收口`。
  2. **坏形状降级**：store.get 返回 `'garbage'` / `{ plan: 123 }` → `session.start` → `flow_task` implement demo → mount → 无 DAG 区块、无异常（行为同现状）。
  3. **拓扑下推渲染**：store.get 返回 progress `{ 'demo#B2': '收口' }`（B1 无记录）+ deps B1→B2 链 → mount → `✓ B1` 且 B1 文本行「收口」（非「待执行」）、`2/2 收口`。
- 写入侧（persistProgress/persistDeps 的 store.set）：测试引擎无该设施（922 注释先例），既有 flow_report/flow_deps 用例回归即覆盖"写入路径执行不抛错、工具返回值不变"；真实持久化断言留 G8 真机。

**文档与版本收尾（并入本批）**

- README 第 21 行段落"依赖图只在实施对应方案时显示"句后补：轨道图结构与各批次阶段经 `$.store` 跨会话恢复，新会话声明同方案实施任务后自动接续。
- 双 manifest `.claude-plugin/plugin.json` 与 `.codex-plugin/plugin.json`：0.20.0 → **0.21.0**。
- 根 CHANGELOG.md Unreleased 加 0.21.0 条目（持久化 + 拓扑下推合并一条，沿 0.19.0 多功能先例）。

### 五要素 · 如何验证

- **L1**：`parseProgressMap` 四例；既有 L1 全量回归。
- **L2**：上述 2 个新 mount 用例；既有全部用例回归（`store.get` 默认 undefined → 恢复路径降级为现状，理论上零影响，回归实证）。
- **L3 真机端到端**（主控收口时做，G8）：真会话 A `flow_deps` 声明 + `flow_report` 上报 B1 至收口 → 结束会话开新会话 B → `flow_task` implement 同方案 → `/deck` 打开 → 轨道图出现且 B1 为收口色。
- **红线回归**：`claude plugin test plugins/flow-deck` 全量 + `claude plugin validate plugins/flow-deck`。

### 五要素 · 验收标准（逐条 PASS/FAIL + 证据）

| # | 断言 | 证据 |
|---|------|------|
| G1 | store.get 返回合法 progress+deps → session.start 后同方案实施任务的面板出现 DAG 区块，B1 done、B2 pending、`1/2 收口` | 用例 1 输出 |
| G2 | store.get 坏形状 → 恢复降级为空，无 DAG、无异常，行为同现状 | 用例 2 输出 |
| G3 | store.get 默认 undefined（全部既有用例）→ 行为逐字节同改前 | 全量回归输出 |
| G4 | flow_report / flow_deps 工具返回值不因持久化失败变错误（best-effort） | 既有用例回归（store.set 无设施即常态失败路径） |
| G5 | `parseProgressMap` 四例通过 | L1 输出 |
| G6 | types 注释、README 句、双 manifest 0.21.0、CHANGELOG 条目落盘 | 文件 diff |
| G7 | `claude plugin test` 全绿 + `validate` 通过 | 命令输出 |
| G8 | 真机跨会话往返：会话 A 收口 B1 → 新会话同方案 → 轨道图接续且 B1 done | 真机截图/记录 |
| G9 | 拓扑下推：B2 收口 B1 无记录 → B1 显示 done 且文本「收口」、n/m 计数含推导节点；末批漏报维持现状；dependsOn 引用不存在批次不崩 | L1 传播用例 + L2 用例 3 |

### 五要素 · 代码评审节点

- 恢复取写在 update 回调外完成（回调必须保持同步纯函数），两步之间无并发写窗口风险（session.start 串行段）；
- `persistProgress` 用 `read($, progress)` 取最新 map 而非在处理器重复拼装——拼装逻辑单一出处（update 回调）；
- store.set 失败的 try/catch 范式与 :1444-1448 逐字一致（debug log 文案带上下文）；
- 旧会话在途 `flow_report` 与新会话恢复交错：键带 `plan#` 前缀，写入即该方案真实状态，无污染路径——评审确认无新增代次门需求（与 git 快照的 cwd 语义不同）；
- D6 无清理：确认渲染层对多余键零消费（`depStatuses` 只查 graph.batches）。
- 拓扑下推的终止性与键安全（环 / 不存在批次名）；推导后 done 计数、连线、状态符号与文本行四处同源一致。

### 五要素 · 分级与验证流程

**T2**。依据：多文件（hooks/register.tsx、hooks/parse.ts、types/index.d.ts、两个测试文件、README、双 manifest、CHANGELOG）；邻近 `session.start` 生命周期契约与 PluginState 注释——但均为注释级补充与行为加法（恢复），不改清空契约本体（currentTask 等保持）；新增持久化写入有 `lastExecution` 成熟先例且 best-effort 降级；有既有测试覆盖（session.start 用例群 + DAG 渲染用例）。执行代理实施 → 审计代理（证据包模式），流程按 implement-plan 查表。

---

## B2 详案：历史批次补报通道

### 五要素 · 如何改

**动机链**：argue 轮事实修正——错误主形态是漏报（agent 忘了调用；implement-plan SKILL.md:18 现行契约"不补报、不重试"明文放任漏报留存）；跨会话场景下 B2 开工时的查证补报比拓扑下推更早修复 B1 漏报（下推要等 B2 收口，补报在 B2 开工即生效）。

**flow-deck 侧（工具契约加法）**

- hooks/register.tsx:1137-1155 `flow_report` 注册的 inputSchema 加可选 `backfill: { type: 'boolean', description: '补报历史批次状态：只更新轨道图批次进度，不触碰当前任务、批次边界与通关卡；仅用于开工核对时补齐前序批次' }`。
- hooks/register.tsx:1364 处理器在 parse 校验之后、一切副作用之前分流：`e.backfill === true` 时只做 progress update + `persistProgress($)`（复用 B1 通道），返回 `{ result: '历史批次状态已补报：<plan>#<batch> → <phase>' }`；**不触碰** closureCard/execution/lastRun/currentTask/batchScope/guardWarned 写入与 firstReportAt 记点（D11——常规通道的收口上报会撤任务清边界，补报走同链路会破坏当前批次）。

**rulertu-flow 侧（implement-plan 技能，plugins/rulertu-flow/skills/implement-plan/SKILL.md）**

- `:12` 开工检查点"核对前置批次证据"句后接：核对到的收口事实与面板状态可能不符（跨会话漏报），会话有 `mcp__flow-deck__flow_report` 时，对本方案已收口（证据目录或 git log 佐证）且非本会话已上报的前序批次，逐条带 `backfill: true` 补报（幂等，可重复）。
- `:18` "工具不存在时静默跳过，不补报、不重试"改为："工具不存在时静默跳过。常规上报漏报不补报不重试；开工核对发现的历史批次收口缺失，按开工检查点口径经 `backfill` 补报。"

**收尾**：双 manifest `.claude-plugin/plugin.json` 与 `.codex-plugin/plugin.json` 0.21.0 → **0.22.0**；根 CHANGELOG.md Unreleased 加 0.22.0 条目（backfill 补报通道 + implement-plan 开工核对纪律）。

**测试（hooks/register.test.ts 新增）**

- backfill 补报 B1 收口（此前 flow_task/flow_batch 已声明 B2）：断言 progress 收 B1 键（state.set 拦截或渲染）、currentTask 仍为 B2、batchScope 不被清、closureCard 无写入、返回文案含"已补报"。
- backfill 后接常规上报：行为与无 backfill 路径一致（回归）。
- 写入侧断言（B1 审计 P2-2 消化）：`on('store.set')` 钩子实际可应答（B1 探针证伪"测试引擎无该设施"的旧调研结论）——常规 flow_report 后断言 store.set 收到 `progressMap` 键与含新键的完整 map；flow_deps 后断言 `depsGraph` 键；backfill 后断言 store.set 收到补报后的 map。
- 顺手修正（B1 审计 P2-1）：hooks/register.test.ts :922 一带「测试引擎无该设施（仅 store.get 钩子可应答）」过时注释更新为可应答口径（只改注释不动测试逻辑，沿 0.19.0 方案先例）。

### 五要素 · 如何验证

- L2 上述两用例；既有 flow_report 用例全量回归（inputSchema 加法对既有调用零影响——backfill 缺省 falsy）。
- 红线回归：`claude plugin test plugins/flow-deck` + `claude plugin validate plugins/flow-deck`。
- 技能文档机械核对：grep "不补报"确认旧口径已更新且开工检查点含补报口径、全库无第二处陈述。

### 五要素 · 验收标准（逐条 PASS/FAIL + 证据）

| # | 断言 | 证据 |
|---|------|------|
| G10 | backfill 补报只写 progress + 持久化：currentTask/batchScope/closureCard/firstReportAt 均不变 | L2 state.set 序列 + store.set 写入侧断言 |
| G11 | 非 backfill 常规上报行为与改前一致（backfill 缺省 falsy） | 既有用例回归 |
| G12 | implement-plan 开工核对含补报口径、"不补报"旧口径已更新、单一出处；双 manifest 0.22.0 + CHANGELOG 条目落盘 | grep 输出 + 文件 diff |
| G13 | 真机：B1 收口漏报 → B2 会话开工核对补报 → 面板 B1 done 且 B2 任务与边界不受扰 | 真机记录 |

### 五要素 · 代码评审节点

- backfill 分流位置在 parse 校验之后、一切副作用之前；对照 hooks/register.tsx:1411-1448 副作用清单逐一核对无遗漏（漏跳任一项即破坏幂等重放）；
- inputSchema 描述措辞防止 agent 把 backfill 当常规上报通道（限定"仅开工核对补齐前序批次"）；
- 技能纪律的事实源边界：证据目录或 git log 可佐证才补报，无法佐证不臆测补报（U4）。

### 五要素 · 分级与验证流程

**T2**。依据：flow-deck 工具契约加法 + 处理器副作用分流（漏跳即破坏当前批次状态，需逐一核对）；跨插件技能文档契约修改（"不补报、不重试"是 implement-plan 现行明文契约，本批改写它）；有既有测试覆盖（flow_report 用例群）。执行代理实施 → 审计代理（证据包模式），流程按 implement-plan 查表。

---

## B3 详案：阶段缩减 5→2（验证全绿即收口）

### 五要素 · 如何改

**核心设计**：上报契约缩为两值（`执行` | `验证`），**内部状态保持五值兼容**——`progress` 存量值、通关卡、撤任务、清边界、轨道图 done 判定等下游全部消费 `收口` 终态语义，零改动；唯一收敛点在处理器，验证全绿时 `stamped.phase` 置 `收口`。

**hooks/register.tsx**

1. `:1147` flow_report 注册的 inputSchema `phase` 描述改为：`'当前阶段：执行 | 验证；验证上报全绿（testsPassed === testsTotal 且 ≥1）自动收口，无需再报收口'`。
2. `:1371-1373` closurePhase 判定的 `report.phase === '收口'` 放宽为 `(report.phase === '收口' || report.phase === '验证')`，其余条件（`testsTotal >= 1 && testsPassed === testsTotal`）不动——显式 `收口` 上报保留兼容（老调用与存量数据）。
3. `:1404` stamped 构造处加收敛：closurePhase 成立时 `phase: '收口'`（唯一升格点，防逻辑散布）——此后 progress 写入、closureCard、lastRun、currentTask 撤下、batchScope 清理全走既有分支零改动。

**hooks/parse.ts**

4. `:196` `phaseProgress` 阶段表 `['开工','派单','执行','验证','收口']` → `['执行','验证']`。存量持久化值 `开工`/`派单` 落入 indexOf -1 → total 0 渲染退化为纯文字（现状未知阶段同行为）；`收口` 经 `selectTaskView`（:34）过滤不进渲染，不进表无碍。

**零改动验证项**（实施时在回报中确认）：`spinnerWord`（hooks/parse.ts:95-100 直接消费 phase 字符串，`执行`/`验证` 正常显示）、`phaseText`（hooks/register.tsx:519-520 只映射执行/验证两皮肤词）。

**rulertu-flow 侧（implement-plan SKILL.md:18，B2 之后改写同一句）**

5. 上报纪律改为："每批执行开始上报 `phase: '执行'`；验证（定向测试跑完）上报 `phase: '验证'` 并带最终 `testsPassed`/`testsTotal`——全绿自动收口，无需再报收口。工具不存在时静默跳过。常规漏报不补报不重试；开工核对发现的历史批次收口缺失，按开工检查点口径经 `backfill` 补报（`phase: '收口'`）。"

**契约注释与文档**

6. types/index.d.ts:71 `ExecutionReport.phase` 注释改："上报契约两值（执行 | 验证）；收口为内部终态——验证全绿升格或显式上报，存量值可能为旧五枚举"。
7. README :13（Spinner 行"批次 · 阶段"描述）与 :19（flow_report 激活描述）同步两阶段口径。
8. 收尾：双 manifest 0.20.0 → **0.23.0**（B2 收 0.22.0 后顺接）、CHANGELOG 条目。

### 五要素 · 如何验证

- **L1**（hooks/parse.test.ts）：`phaseProgress('执行') → {index:1,total:2}`、`('验证') → {index:2,total:2}`、`('开工') → total 0`（存量值退化）；既有 `:264` 五阶段断言同步改写。
- **L2**（hooks/register.test.ts）：
  1. 验证全绿上报（`phase:'验证', testsPassed:10, testsTotal:10`）→ currentTask 撤下、closureCard 组装、progress 记 `收口`、lastRun 写入——与显式收口路径逐项等价；
  2. 验证部分通过（8/10）→ 不收口，面板显示验证 2/2 与测试进度条 warn 色；
  3. 显式 `phase:'收口'` 既有用例全量回归（兼容通道）。
- **红线回归**：`claude plugin test plugins/flow-deck` + `claude plugin validate plugins/flow-deck`。
- 技能文档机械核对：SKILL.md:18 单一出处、README/types 口径一致。

### 五要素 · 验收标准（逐条 PASS/FAIL + 证据）

| # | 断言 | 证据 |
|---|------|------|
| G14 | 验证全绿自动收口：撤任务、清边界、通关卡、progress 终态、轨道图 done，与显式收口逐项等价 | L2 用例 1 |
| G15 | 验证部分通过不升格（8/10 仍验证态） | L2 用例 2 |
| G16 | 显式收口兼容；`开工`/`派单` 存量值渲染退化不崩 | 既有用例回归 + L1 |
| G17 | 每批上报调用次数 5 → 2；SKILL.md/README/types 三处口径一致且单一出处 | 文档 diff + grep |

### 五要素 · 代码评审节点

- 收敛点唯一（`:1404` 一处置 `收口`），升格逻辑不得散布到渲染层或 persist 层；
- tests 缺省或 `testsTotal === 0` 不升格（现状 `>= 1` 条件保持——无测试证据不算全绿）；
- spinner/phaseText 零改动的实证（回报列出两函数现状引用）；
- B2 交互：backfill 补报 `phase:'收口'` 直写 progress 不经 closurePhase 判定（D11 旁路），两通道互不干扰。

### 五要素 · 分级与验证流程

**T2**。依据：closurePhase 是行为语义修改（非纯加法）、多文件、跨插件纪律改写（implement-plan 上报契约）；有既有测试覆盖（flow_report/phaseProgress 用例群）。执行代理实施 → 审计代理（证据包模式），流程按 implement-plan 查表。

---

## 不确定点（实施时消解）

| # | 不确定点 | 消解方式 | 兜底 |
|---|---------|---------|------|
| U1 | `on('store.get')` 钩子入参是否携带 key（分流返回需要） | 实施时以测试宿主类型/一次试探为准 | 无 key 则用闭包变量按调用序切换返回值（session.start 内两次 get 顺序固定：先 progress 后 deps，lastExecution 在尾部） |
| U2 | `store.set` 在测试引擎的具体形态（抛错被吃 vs 静默 no-op） | 实施时观察 debug log | D4 try/catch 两形态均降级，不阻塞工具返回 |
| U3 | 真机 `$.store` 的持久化作用域（全局 vs 按仓库） | G8 真机端到端顺带确认 | 无论哪种，D7 的键隔离论证均成立；按仓库作用域更优 |
| U4 | agent 判断"已收口"的事实源边界（git log 提交与批次映射不保证一一对应） | 技能纪律限定"证据目录或 git log 佐证，无法佐证不补报" | 宁缺勿错——拓扑下推与该批次下次真实上报仍在 |
| U5 | 验证全绿时点早于最终提交（收尾动作在测试后）——通关卡战报 numstat/minutes 不含收口上报之后的改动 | 纪律写明"验证上报在最终提交之后发出"（implement-plan 收口动作顺序：提交 → 上报验证） | 接受误差：战报行已有"统计截至"时效披露（README :15 同口径） |
