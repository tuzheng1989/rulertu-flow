# flow-deck 炫酷化（0.18.0）：收口仪式 · 任务控制台 · 呼吸面板 · 驻场小生物

日期：2026-11-02 ｜ 状态：待评审
需求来源：brainstorm 创意轮产出四设计 → 深钻轮内存评估（稳态增量 <1MB）→ grilling 收束共识（本文档的决策依据，不再重述）。

## 路线图

| 批次 | 内容 | 定级 | 依赖 |
|---|---|---|---|
| B1 | 收口仪式 + 任务控制台（事件驱动/静态映射，零边际） | T1 | — |
| B2 | 呼吸面板 + 驻场小生物（共享节拍器，帧动画） | T2 | B1（小生物敬礼态消费 B1 的通关卡状态） |
| 收尾 | 版本 0.18.0 + README 更新 | T0 | B2 |

依赖链：B1 → B2 → 收尾。发布为一版 0.18.0，两批实施完合并发布。
取舍裁决记录：B1 两项共享面板渲染层上下文（同一组渲染函数与文案出口），合并摊薄装载开销；B2 两项共享节拍器与帧状态设计，合并；B1/B2 之间隔离——B2 引入新工程模式（帧 atom、可见性门控），独立收口可单独回滚。收尾为轻量收尾，主控 T0 直做。

## 红线与契约（单一出处，全文引用此处）

1. **帧三红线**（源自深钻轮，B2 全程有效）：
   - 帧状态只写入专用帧 atom（本方案新增 `beat`），禁止写入其余任何 PluginState 键——否则击穿 `poll.ts:100` gitSnapshotKey 时间戳防抖，每帧叠加全树刷新；
   - 帧回调只做帧号切换与 `$.ui.panes()` 可见性判定，禁止数据面 IO（git / `$.agent.list()` / `$.fs.*` / `$.store.*`）；
   - 面板不可见即停帧：门控照抄 `register.tsx:894-900` refreshAgentPane 的 `$.ui.panes()` 含 `deck` 判定模式。
2. **语义色契约**（既有，出处 ui.ts 头注 / 2026-11-01-native-ui-redesign §设计契约）：全部颜色经 `TONE` 表取值，渲染层禁 ANSI 字面量色名；任务控制台皮肤的色彩同样只能通过扩展/复用 TONE 实现。
3. **越界守卫与 git 轮询逻辑零改动**：本方案不触碰 `guardDecision`、`createGitPoller` 的判定与节流路径；poll.ts 改动限定为 numstat 数据装配的加法式扩展（新增 `byPath` 字段，不改既有字段语义、查询命令与快照防抖逻辑）。

## 新增状态生命周期（单一出处，正文引用此处）

| 状态 | 初始化 | 更新时机 | 清理时机 | 跨会话行为 |
|---|---|---|---|---|
| `closureCard` atom（新，模式同 register.tsx:70 lastRun） | 初始 `null`；session.start 重置 `null`（并入 758-777 重置清单） | 全绿收口**且前置校验通过**时写入（scope 非空且 plan/batch 匹配，B1 条目 3；校验不过不写） | 清卡规则单一出处 B1 条目 4：flow_task 非 idle / idle、flow_report 非收口、flow_batch 声明四出口直接清空；任何收口报告到达时——能组装新卡（全绿且 scope 匹配）则写新卡，否则清卡，唯一例外为报告与现存卡同 plan#batch 且全绿（重复上报收口）→ 三出口幂等保留：closureCard 保留原卡，lastRun 与 store 亦保留原含 closure 记录（重放口径，处置单一出处 B1 条目 4）；另 session.start 重置 | 不持久化；跨会话战报经 lastRun atom 与 `$.store`（EXECUTION_STORE_KEY）出口 |
| `beat` 帧原子（新，`0 \| 1`） | 初始 `0`；session.start 重置 `0` | beatTimer 回调翻转（仅 `$.ui.panes()` 含 deck；查询失败跳过本次） | 无销毁态：session.start 先 cancel 旧 beatTimer 再重置为 `0`，不残留定时器 | 不持久化；新会话从 0 起 |
| 首报时间 map（模块级，键 `<plan>#<batch>`） | 模块加载空 map | flow_batch 声明三态（唯一写入点）：首次声明该键记 `Date.now()`；同键重新声明（边界调整）**不重置**起点——起点恒为该键在本会话的首次 flow_batch 声明；异批声明记新键起点、旧键保留。flow_report 收口组装读 map 判定 minutes 时先于本处理器一切状态写入（语句顺序契约，B1 条目 3） | session.start 清空（模式同 778-779 模块级变量重置） | 不跨会话残留 |
| `closure` 字段（ExecutionReport 可选；类型与可空语义单一出处见 B1 条目 1：files 必填 number（缺失/非法整个丢弃），added/removed/minutes 为 number \| null 且缺省与 null 等价，statsAt 为统计快照 fetchedAt、可缺省） | 缺省不出现 | 全绿收口且前置校验通过时组装写入 stamped（B1 条目 3；校验不过整个不写；同 plan#batch 全绿重复收口为幂等例外——以现存卡 closure 重建 stamped.closure 后照写，B1 条目 4）；序列化经 995 行 `$.store.set` 原样保留 null | 不主动清理：非收口上报的新 stamped 自然不含，store 值被新上报覆盖（唯一例外：同 plan#batch 全绿重复收口经重放保留原 closure，B1 条目 4） | 随 EXECUTION_STORE_KEY 持久化，867 行 readLastExecution 经 parseExecution 透传恢复（null 原样透传，缺省规范化为 null——缺省与 null 等价，B1 条目 4a） |
| `byPath` 与 `numstatSides`（GitStatus 可选字段） | buildGitStatus 每次构建填充 | 每次成功 numstat 轮询随 gitStatus atom 整体替换；`numstatSides` 记 worktree/cached 两侧各自状态（ok / skipped 未查询（该侧无 tracked 改动）/ failed 本应查询但返回 null），B1 条目 2 | 无独立清理：非 git 仓库或最近一次轮询失败退避（poll.ts:130-131）时 gitStatus 整体为 null；session.start 清空 gitStatus（置 null，待新一轮查询）——B1 条目 3 战报统计判定的取数前提 | 不持久化；计入 gitSnapshotKey（fetchedAt 除外，poll.ts:101-106），逐文件行数与侧状态变化触发发布，与既有 added/removed 同口径；跨会话由代次门隔离——session.start 在任何 await 之前同步递增模块级 generation 并捕获新值，再清空 gitStatus、重建 timer 与首轮查询（顺序契约，B1 条目 2a）；poller publish 回调（register.tsx:877-879）把代次比对收进 update 回调内部（比对与写入同一回调完成，B1 条目 2a 原子性契约），仅当捕获代次与回调执行时的当前 generation 相等才写入，旧会话在途 publish 的回调在递增之后执行（无论清空前还是清空后）均被拒绝、递增之前完成写入的由清空兜底，不得残留旧 cwd 快照 |
| `artDirection` / `companionMode`（模块级配置） | register 时按 userConfig 覆盖（默认 `mission-control` / `on`，模式同 755 行 guardMode） | 无运行时更新（仅 register 读配置） | 不清理 | 每次会话 register 重读 userConfig |

## 术语

锚点 = 文件:行号；通关卡 = 收口仪式的全卡组件；节拍器 = `$.clock.every` 定时器；帧 atom = `beat`。

---

## B1：收口仪式 + 任务控制台（T1）

### 如何改

**通关卡（收口仪式）**

1. `types/index.d.ts:55-72`：`ExecutionReport` 追加可选字段 `closure?: { files: number; added: number | null; removed: number | null; minutes: number | null; statsAt?: number }`（加法式，旧值兼容）。契约（本方案单一出处，正文与生命周期表均引用此处）：`files` 必填 number——组装侧前置校验不过时整个 closure 不写入（条目 3）、解析侧缺失/非法时整个 closure 丢弃不产出卡（条目 4a），故存续的 closure 不存在"files 不可用"形态；`added`/`removed`/`minutes` 为 `number | null` 且持久化与恢复同一契约——组装侧三字段始终写全（null 原样），解析侧字段缺失规范化为 null（缺省与 null 等价，不出现 undefined 形态，条目 4a）；`added`/`removed` 为 `null` = 统计不可用（收口时 gitStatus atom 为 null，或任一必需 numstat 侧查询失败，条目 2/3），与"有数据但零行"的真实 0 必须可区分；`minutes` 为 `null` = 无首报起点；`statsAt` 为该次统计快照的 fetchedAt（ms），仅统计可用（数值非 null）时随行写入、可缺省。序列化规则：995 行 `$.store.set` 对 stamped 原样保留 null（不折算、不删键）；`parseExecution`（条目 4a）按同一契约透传。
2. **numstat 逐文件数据贯通**（parse 聚合 + poll 装配两段缺一不可）：`hooks/parse.ts:484` `parseNumstat` 增加按文件聚合出口——新增纯函数 `numstatByPath(stdout): Map<path, {a, r}>`（原总计逻辑改为对聚合结果求和，`added`/`removed` 行为不变；二进制 `-` 行沿用既有跳过口径）。numstat 行解析规格（真实 git 输出格式）：每行 `added\tremoved\tpath` 三列 tab 分隔（与 parseNumstat 484 行既有 split('\t') 口径一致）；rename 行 path 列两种记法都要解析出**目标路径**——全量记法 `old => new` 取 `=>` 右侧整段，花括号压缩记法 `src/{old => new}/file.ts` 取花括号内 `=>` 右侧并保留花括号前后段拼接还原为 `src/new/file.ts`；路径列引号处理——numstat 命令（poll.ts:125-126）现状不带 status 命令（117 行）的 `-c core.quotePath=false`，quotePath 默认开启时非 ASCII 路径以双引号 + `\nnn` 八进制转义形态输出，含空格/制表符等特殊字符路径也可能带双引号包裹：路径列以 `"` 包裹时剥去首尾引号并解码八进制转义（字节序列按 UTF-8 还原，含 `\"`、`\\`），不以 `"` 包裹时原样保留（剥引号先例：parse.ts:423 unquotePath，porcelain 侧 quotePath=false 下仅控制字符等罕见路径仍带）；解析不假定 core.quotePath 配置取值，两种形态均兼容。还原出的目标路径经 normalizePath + 小写归一化后作为 byPath 键（条目 3 匹配同口径）。`GitStatus`（types:111-134）追加可选 `byPath?: Record<string, [number, number]>`；`buildGitStatus`（parse.ts:499-533）签名扩展为同时接收两次 numstat 的逐文件聚合与两次原始输出（`string | null`），同路径暂存+未暂存求和后填充 `byPath`，并填充新可选字段 `numstatSides?: { worktree: 'ok' | 'skipped' | 'failed'; cached: 'ok' | 'skipped' | 'failed' }`（GitStatus 追加，与 byPath 同为加法式扩展）。数据装配改造在 `hooks/poll.ts:123-128`：worktree 与 cached 两次原始输出（124-127 行）不再只交 `parseNumstat` 取总数，逐文件结果保留并合并后随 `buildGitStatus` 传入——查询命令与节流/防抖行为（116 行节流门、129-131 档位、133-137 快照防抖）零改动（红线 3）。**侧状态贯通**（战报统计失败语义的单一出处，条目 3 与生命周期表引用此处）：124-127 行两次 numstat 是 `Promise.all` 下的独立查询，单侧可能失败（`run` 返回 null），且 null 同时承载"该侧无 tracked 改动未发起查询"（125/126 行三元条件不满足）与"发起查询但失败"两种情形——区分口径与查询条件同源：worktree 侧本应查询 ⇔ unstaged+conflicts 非空、cached 侧本应查询 ⇔ staged 非空（porcelain 分类，buildGitStatus 内部可得），由此装配 `numstatSides`：发起且成功 → `ok`，未发起 → `skipped`，本应查询但返回 null → `failed`。**任一必需侧 `failed` → 战报统计整体不可用**（条目 3 组装时 added/removed 整体置 null、statsAt 缺省，与 gitStatus 为 null 同一不可用口径，禁止把单侧部分数据——byPath 或合计——当真实战报值）；`skipped` 未查询不算失败。既有 `GitStatus.added`/`removed` 合计字段维持现状语义与既有消费方（输入区横条 1180 行等）不变（红线 3：既有字段语义零改动）。
2a. **跨会话 git 快照隔离**（`hooks/register.tsx` session.start 回调）：重置清单（758-777）追加 `await update($, gitStatus, () => null)`——gitStatus 为模块级 atom（68 行）不随会话重建，同一插件实例连续启动不同 cwd 的会话时，新会话首轮 tickGit（902 行）完成前的收口会读到上一 cwd 的旧快照，必须清空待新一轮查询；**代次门**（R5 P2 落实比对-写入原子性）：session.start 递增模块级 `generation`（声明模式同 778-779 模块级变量；generation 仅在该同步段变更），poller 的 publish 回调（877-879，session.start 内创建并捕获当次 generation）**不在回调外比对后写入，而是把代次校验收进 update 回调内部**：`update($, gitStatus, prev => capturedGeneration === currentGeneration ? status : prev)`——比对与写入在同一回调内完成、天然串行，不依赖引擎 update 的"外部比对与写入间无插入"原子性假设；回调执行时代次已变则原样返回 `prev`（丢弃旧快照）——旧会话在途查询的 publish 迟到完成时仅靠清空挡不住写入，需门禁拦截。**执行顺序契约（R4 P1 落实，语句顺序固定，生命周期表与测试引用此处）**：① **同步递增 generation 并捕获新值（纯同步、无 await，先于本回调内一切异步操作）** → ② 清空 gitStatus（`await update`，即上述重置清单追加项） → ③ 重建 timer 与首轮查询（908-911 / 902 行，publish 回调捕获 ① 的新代次）。旧会话在途 publish 的交错全枚举（比对以 update 回调执行时刻为准）：在 ① 之前 update 回调已执行完毕（写入落地）→ 该次写入时 generation 尚未递增、比对通过合法，随后 ② 清空兜底清除，不残留；update 回调在 ① 之后任一时刻执行（无论 ②③ 前后）→ 回调内读到的当前 generation 已递增、与捕获值必不等，原样返回 prev 不写入——比对与写入同帧，不存在"比对已过而写入未落"的窗口；先递增后清空保证不存在"清空已完成而代次未变"的写入窗口（顺序倒置即复现该窗口）。门禁只加在 register 侧 publish 接线，`createGitPoller` 内部（poll.ts）零改动（红线 3）。生命周期见"新增状态生命周期"表 byPath 行。
3. `hooks/register.tsx:974-1000`（flow_report 处理器）：`phase === '收口'` 且 `testsTotal >= 1 && testsPassed === testsTotal` 时进入收口组装分支，组装 `closure` 并入 stamped（979 行 stamped 构造处；既有 988-991 的 scope 清空逻辑不动，清空不追溯影响已并入 stamped 的 closure）——持久化随 995 行 `$.store.set` 自动生效（null 原样保留，序列化规则见条目 1）；同时写入新 atom `closureCard`（`register.tsx` atoms 区，模式同 70 行 lastRun），并把 `closureCard` 登记进 `types/index.d.ts` PluginState（模式同 types:169 lastRun）。失败/中断收口（tests 不全绿）不写 closureCard，且清空既有卡（见条目 4）。closure 组装口径，**语句顺序固定**：① 读首报 map 判定 minutes → ② 读 batchScope 前置校验 → ③ 读 gitStatus（含 numstatSides 侧状态）组装行数与 statsAt → ④ 并入 stamped，四步全部先于 980-984 的 execution/progress 更新——该顺序为契约：minutes 判定不得依赖本报告触发的任何状态写入（防线说明：起点唯一由 flow_batch 声明记录、progress 更新不写首报 map（见生命周期表），但若实现偏离该口径把起点记录挂回 progress 首报路径，且判定落在 progress 更新之后，直接收口会自造起点、把 null 折算成 0 分钟）：
   - **前置校验（②，先于一切 closure 字段组装）**：`scope !== null && scope.plan === report.plan && scope.batch === report.batch` 方可组装（report 为 975 行 parseExecution 产物，② 早于 ④ 故不引用 stamped）——flow_report 处理器 988-991 在收口或批次不匹配时会清 batchScope（990 行置 null），收口报告自身的 scope 也可能已被更早的异批报告清掉；校验不过（scope 为 null，或为他批残留 plan/batch 不匹配）→ **整个 closure 不写入**（files 一并不可用，不降级为"仅缺行数"的部分战报），closureCard 不写新卡，旧卡去留与 lastRun/store 两出口处置按条目 4 统一规则判定：报告与现存卡同 plan#batch 且全绿（重复上报收口）→ 三出口幂等保留（重放口径，见条目 4）；异键或无卡 → 清卡，通关卡退化为普通摘要行、战报不出现在面板（store 写入的是不含 closure 的 stamped，与失败收口同路径）；
   - 文件数 = `batchScope.files.length`（**声明边界数**，非 git 实测变动数），通关卡文案注明"声明边界"——前置校验通过后 files 恒有值（条目 1 可空语义）；
   - 路径匹配前对 git 路径与 scope 路径做**同一归一化**：均经 `normalizePath(path, cwd)`（parse.ts:307-314：反斜杠转正斜杠、绝对路径剥 cwd 前缀）+ 小写键后比较，调用模式同 register.tsx:664 scopeSet；byPath 键在条目 2 解析时按同口径归一化，杜绝绝对路径声明 / 分隔符差异导致的漏配；
   - ±行数三态（不可用 / 真实 0 / 数值）：组装时读 gitStatus atom——为 `null`（最近一次轮询失败退避中、非 git 仓库（poll.ts:130-131），或 session.start 已清空待首轮查询（条目 2a）），**或 `numstatSides` 任一必需侧为 `failed`**（该侧本应查询（非 `skipped`）但返回 null，条目 2）→ `added`/`removed` 整体置 `null`（统计不可用，战报显示 `—`）且 `statsAt` 缺省不写，禁止把单侧部分数据当真实值；两侧均可用（`ok` 或 `skipped`）→ 数值可用 = byPath 中 scope 内文件合计，同时把该快照 `fetchedAt` 写入 `closure.statsAt`，通关卡战报展示"统计截至 HH:MM"——**不做任何滞后区间承诺**（轮询失败与快照防抖下滞后无可靠上限，时间戳是唯一如实披露）；byPath 无该文件数据时不计入（未跟踪文件不进 numstat、二进制 diff 为 `-` 行被跳过，parse.ts:483 既有口径）——gitStatus 非 null 且侧可用而 scope 内全部文件无数据时合计为**真实 0**（有数据但零行）；`null`（不可用）与 `0`（零行）必须可区分（条目 1 类型）；
   - `minutes = (Date.now() - 首报时间[plan#batch]) / 60000` 取整，map 无该键（无首报起点）时为 `null`，战报省略分钟段显示 `—`；首报时间为新增模块级 map，起点唯一由 flow_batch 声明记录（首次声明该键记起点 / 同键重新声明**不重置**起点——起点恒为该键在本会话的首次 flow_batch 声明 / 异批声明记新键起点、旧键保留），完整生命周期见"新增状态生命周期"表。取舍（R3 P2 落实）：flow_batch 声明无法区分边界调整与真正重开（implement-plan 允许实施中重新声明更新边界），取首声明可避免正常的边界调整把耗时误清零，重开场景的间隔计入是已接受的近似；战报与通关卡文案的分钟段口径注明"自首次边界声明"。
4a. `hooks/parse.ts:276-293` `parseExecution`：白名单追加可选字段 `closure` 透传——校验规则（与条目 1 类型同一契约，R3 P2 落实）：`closure` 为对象且 `files` 为 number（必填，缺失或非法（如字符串）→ 丢弃整个 closure 字段，视同缺省、不产出卡）时透传；`added`/`removed`/`minutes` 各自接受 number 或 `null`，**字段缺失规范化为 null**（缺省与 null 等价，不透传 undefined、不折算为 0——否则恢复出的对象违反条目 1 的必填 `number | null` 契约）；`statsAt` 为 number 时透传、可缺省。若不如此，跨会话恢复（867 行 readLastExecution）拿到的 report 缺字段或 null 语义被折算，战报格式必不现/必错。
4b. `register.tsx` flow_report 处理器收口分支（985 行旁）：同步 `update($, lastRun, () => stamped)`——408 行空态摘要读的是 lastRun **atom** 而非 store，不补此通路则本会话 idle 后摘要必不现战报。重复上报收口命中条目 4 幂等例外时，stamped 已先按例外规则以现存卡 closure 重建（重放），故 lastRun 写入与 995 行 store 写入同源一致，两出口保留的均为含 closure 的记录。
4. 通关卡出口（清卡规则单一出处，生命周期表引用此处；R3 P1 落实）：
   - 四出口直接清空 `closureCard`（各加一行）：flow_task 非 idle 上报（955 处理器）、flow_task idle 上报（966 行旁）、flow_report 非收口阶段（985 行前）、flow_batch 声明处理器（1002-1014，新批次启动即清旧卡）；
   - **任何收口报告到达时统一判定**（取代原独立"非全绿收口"出口）：能组装新卡（全绿且前置校验通过，条目 3）→ 写新卡；否则清卡；**唯一例外**：报告与现存卡同 plan#batch 且全绿（重复上报收口——首次收口已清 batchScope（988-991），第二次校验必不过）→ **三出口幂等保留，处置单一出处在本条（R4 P1 落实，条目 3/4b 与生命周期表引用此处）**：closureCard 保留原卡（既有规则）；lastRun atom 与 `$.store`（995 行）同样保留原含 closure 的记录，不被本次无 closure 的 stamped 覆盖。实现口径取**重放**：命中例外时，在 4b 的 lastRun 写入与 995 行 store 写入之前，先以现存卡的 closure 重建 stamped.closure（等价重放首次收口的原战报记录）再写，两出口写入照常执行——"每次收口刷新 lastRun"的既有行为不变，且不存在"本次 stamped 不含 closure 却写入 lastRun/store"的通路（不取"直接跳过两出口写入"口径：会中断该既有行为）。由此：tests 不全绿的收口 → 清卡；全绿但 scope 缺失/他批残留且与现存卡异键 → 清卡（防"旧卡存在 → 他批错配收口"下旧卡冒充本次全绿）；同 plan#batch 全绿重复 → 三出口均保留原战报；
   - guardWarned 清理仅在**任务或批次实际变化**时执行（R4 P2 落实、R5 P1 修正清理条件，B2 条目 3 捂脸门引用此处；理由：guardWarned 的去重语义属于"批次边界 + 文件"——README 既有契约"同批同文件只提醒一次"，同批阶段上报不改变边界、不应重置去重，清理的目标只是跨任务/跨批残留）：flow_task 声明（955-972）——新声明的 plan（+batch 若有）与当前 currentTask 的 plan#batch 不同、或当前无任务 → 清空，相同（幂等重申同一任务）→ 不清；flow_report 非收口分支（985-987 直接设置新 currentTask 处）——报告的 plan#batch 与当前 currentTask 的 plan#batch 不同 → 清空，相同（同批阶段推进：执行→验证等）→ 不清（该分支不经 flow_task 也能激活新任务——直接上报异批执行阶段即切换任务，异批不清则旧任务的历史告警压住新任务态位）；flow_batch 声明（1009 行）为**既有行为、本方案不改**——每次声明（含同键重新声明）都清，这是既有契约"边界变化重置去重"（register.tsx:1008 注释为出处，README"批次重新声明后重置"同口径），边界调整即边界变化、清空使新边界下的越界可再次提醒。警告属于活动任务，guardWarned 无批次归属信息，靠任务激活点的变化判定清理最简（R3 P2 落实）；警告态判定维持 `currentTask 非空 && guardWarned.length > 0`，变化清理闭合后该判定不再有"currentTask 已换新而告警是旧任务残留"的假阳性通路（收口分支不清，由 currentTask 置 null 关门）；
   - idle 清卡即"并入摘要"：摘要数据经 4b 通路已在 lastRun atom 与 store，不新增独立折叠元素。
5. `hooks/register.tsx:157` `describeExecution`：`report.closure` 存在时摘要文案升级为战报格式（如 `B2 · 3 文件 · +842 −96 · 41 分钟 · 全绿`）——空态摘要（408 行）与 toast（869 行）自动继承。
6. Pane 工作流页签渲染（renderFlowBody，register.tsx:352-535；Pane 分发在 1064）：`closureCard !== null` 且无活动任务时，在当前执行卡位置渲染通关卡。通关卡走**独立装配分支，不经 selectTaskView**（register.tsx:174 装配出口所调的 parse.ts:25-35 只在活动实施任务匹配时返回 graph，而收口时 985 行已把 currentTask 置 null，经它必得 null）：渲染处直接 `read($, deps)` 与 `read($, progress)`（既有 atom，renderFlowBody 356 行同款读取），`deps.plan === closureCard.plan` 匹配时渲染轨道图——**按各批实际状态着色**：progress map `<plan>#<batch>` 键的最新阶段经既有 `depStatuses`（parse.ts:363-368）+ `pipelineLinks` 计算，已收口批次节点/连线 done 色，本批（`closureCard.batch`）节点高亮，未执行批次维持现状色；仅当依赖图内**全部**批次节点均已收口（done === nodes.length，方案收官）时才全图 done 色——这是"全线点亮"庆祝态的唯一触发条件，任何单批收口不得整图点亮（颜色仍限 TONE 表，契约 2）+ 战报行 + `TONE.ok` 标题；未声明 deps 或 plan 不匹配（deps 残留他方案的图）时按无图处理，只渲染战报行。

**任务控制台（皮肤）**

7. `hooks/register.tsx:90-109` 配置模式区：新增 `let artDirection: 'default' | 'mission-control' = 'mission-control'`，register 时按 `options.artDirection` 覆盖（模式同 755 行 guardMode）。
8. `.claude-plugin/plugin.json`：userConfig 增加 `artDirection`（options `["default", "mission-control"]`，default `mission-control`）。
9. `hooks/parse.ts` 新增 `skin = { label: (key) => string }` 术语表（全中文，7 条映射，一词一义）：批次→飞行阶段、执行→阶段进行、验证→数据校验、评分→燃料余量、依赖图→轨道图、停滞→遥测丢失、无任务→待命。渲染层取文案处（标题行、进度条标签、DAG 区标题、空态行、停滞提示）按 `artDirection` 切换 default/mission-control 词表；**只换文案，不改图形结构与信息量**。颜色经 TONE（契约 2）。

### 如何验证

- L1：`numstatByPath` 单测（多文件/空输出/rename 目标路径还原——全量记法 `a/old.ts => b/new.ts` 与花括号压缩记法 `src/{old => new}/file.ts → src/new/file.ts`；带引号路径剥引号 + 八进制转义解码；同文件暂存+未暂存求和）；`buildGitStatus` 侧状态装配单测（`numstatSides` 填充：两侧均成功 → ok/ok；一侧无 tracked 改动未查询 → 该侧 skipped、对侧不受影响；本应查询的一侧返回 null → 该侧 failed——skipped 与 failed 必须可区分）；`describeExecution` 战报格式单测（有/无 closure；`minutes`/`added`/`removed` 为 null → `—`、为真实 0 → 显示数值，null 与 0 两态各自断言可区分；`statsAt` 存在 → 战报含"统计截至 HH:MM"）；`parseExecution` closure 透传单测（null 字段原样透传；部分缺失——added 有 removed 无 → removed 规范化为 null，不出现 undefined 形态；非法值——files 为字符串 → 整个 closure 丢弃——跨会话恢复前置）；skin 术语表双词表快照。
- L2（register.test.ts 既有替身编排模式扩展）：
  - 正常批次事件顺序：flow_batch 声明 3 文件（含绝对路径与反斜杠分隔符各一，验证归一化贯通）→ 系列 flow_report（执行→验证 1/3→验证 3/3→收口 全绿）→ 断言 closureCard 写入且 closure 数值正确（文件数 = 声明边界数；gitStatus 替身注入 byPath，键含同一文件的两种路径写法 → 行数正确合并；`statsAt` = 替身快照 fetchedAt；`minutes` = 收口时刻 − 首次声明时刻，可控时钟断言精确值）；
  - numstat 贯通（poll.test.ts 既有 createGitPoller 替身模式扩展，71 行起）：替身注入**真实格式** numstat 原始输出——目录重命名（花括号压缩记法，如 `1\t2\tsrc/{old => new}/file.ts`）、普通重命名（全量记法，如 `3\t0\ta/old.ts => b/new.ts`）、中文路径（八进制转义 + 双引号形态与原样形态各一）、含空格路径（双引号包裹形态）、同文件暂存+未暂存两段 → 断言 publish 收到的 `GitStatus.byPath` 逐文件正确（目标路径经还原 + 归一化后与 scope 匹配）、合计与既有 `added`/`removed` 口径一致；
  - numstat 侧状态贯通（poll.test.ts 同替身模式，R3 P1 落实）：status 成功 + 单侧 diff 失败（该侧有 tracked 改动、run 替身对 numstat 命令返回 null）→ 快照 `numstatSides` 该侧 failed，收口组装 added/removed 整体为 null（不可用）且 statsAt 缺省——不得把对侧部分数据当真实值；对侧无 tracked 改动（skipped）+ 本侧成功 → 统计正常（skipped 未查询不算失败）；两侧均成功 → 正常（数值与既有口径一致）；
  - 收口但 testsPassed < testsTotal → 断言 closureCard 必不写入且既有卡被清空；
  - 收口边界缺失/错配两场景（无旧卡前提）：flow_report 收口时 batchScope 已为 null（此前被 flow_task 或异批报告清空）→ 断言 closure 不写入、closureCard 保持空、store 值不含 closure；batchScope 为他批残留（plan/batch 与收口报告不匹配）→ 同前断言；有旧卡时的去留由下方清卡统一规则序列覆盖；
  - 统计三态：收口时 gitStatus atom 为 null（轮询失败替身）→ closure.added/removed 为 null、statsAt 缺省，战报行显示 `—`；gitStatus 非 null 但 byPath 不含 scope 文件 → added/removed 为真实 0（与 null 可区分）且 statsAt 有值；
  - 序列：成功收口 → flow_batch 新批次声明 → 失败收口 → 断言 closureCard 为空（旧成功卡不残留）；
  - 清卡统一规则两序列（B1 条目 4，R3 P1 落实）：成功收口（卡写入）→ 重复上报同 plan#batch 全绿收口（batchScope 已被首次收口清空、校验必不过）→ 断言 closureCard 保留现状（幂等不清）且 **lastRun atom 与 store 值仍含 closure（三出口一致，重放生效——不存在无 closure 的 stamped 覆盖两出口的通路，R4 P1 落实）**；成功收口（旧卡存在）→ 他批错配收口（scope 为 null 或异批残留）→ 断言旧卡必清、不冒充本次收口；
  - guardWarned 条件清理两组序列并存（B1 条目 4，R5 P1 落实）：①同批去重保留——同批越界（warn 提醒一次）→ 同批阶段上报（flow_report 非收口、与 currentTask 同 plan#batch）→ 同文件再次越界 → 断言不重复提醒（guardWarned 未被同批上报清空，README 去重契约"同批同文件只提醒一次"保持）；②异批清理——同批越界后直接 flow_report 上报异批执行阶段 → 断言 guardWarned 已清、旧任务告警不跨任务残留（R4 已加序列，与 B2 L1 同场景互补——B2 L1 断言小生物态位、此处断言集合清理）；
  - 重复收口三出口完整序列（B1 条目 4 幂等例外，R4 P1 落实）：成功收口 → 重复上报同 plan#batch 全绿收口 → flow_task idle → 新会话恢复（再次 session.start，867 行 readLastExecution）→ 逐步断言：重复收口后三出口（closureCard、lastRun atom、store 值）均含 closure 且逐字段一致；idle 后 closureCard 清空而 lastRun atom 与 store 值仍含 closure；新会话恢复后 lastRun atom 含 closure（null 字段原样透传）、toast（869 行）为战报格式——重复收口不得使任何出口退回无 closure 形态；
  - 全绿后 flow_task idle → 断言 closureCard 清空、store 值含 closure（null 字段原样保留）、lastRun atom 更新为含 closure 的 stamped；readLastExecution（parseExecution 透传后）返回值含 closure 且 null 字段未折算为 0（跨会话恢复断言：null 原样保留（含缺省字段规范化为 null，两形态恢复后等价）/ 真实 0 不被折算，两态可区分）；
  - 全绿后新 flow_report（下一批执行）→ 断言清空；
  - 通关卡装配三场景：closureCard.plan 匹配 deps → 渲染轨道图（着色按各批实际状态，断言见下条）；未声明 deps → 仅战报行；deps 为他方案残留（plan 不匹配）→ 按无图处理；
  - 通关卡轨道图按实际状态着色（多批次依赖图）：B1 收口全绿而 B2/B3 待执行（progress 仅 B1 为收口）→ 断言轨道图呈混合状态（B1 节点/连线 done 色、本批高亮，B2/B3 维持现状色），而非全 done；依赖图内全部批次收口 → 全图 done 色（"全线点亮"唯一触发）；
  - 首报时间（可控时钟，flow_batch 声明三态分别断言）：首次声明该 plan#batch → 收口 minutes = 收口时刻 − 首次声明时刻（声明后不经任何 flow_report 直接收口同样成立，且不为 0 分钟）；同键重新声明（边界调整，files 集合变化）→ **起点不变**（minutes 仍从首次声明时刻起算，断言不被清零，R3 P2 落实）；异批声明 → 新键起点记录（新批 minutes 从其声明时刻起算；旧键保留不可经行为观测，由代码评审节点核对）；session.start 重触发后直接收口（无 scope）→ closure 整体不写入（条目 3 前置校验），战报不出现；
  - 跨会话 git 快照隔离（B1 条目 2a，R3 P2 落实）：连续两次 session.start（替身注入不同 cwd）、第二次首轮 tickGit 查询未完成（run 替身挂起）时收口 → 断言 closure.added/removed 为 null（统计不可用）而非上一 cwd 旧快照值；旧会话在途查询在第二次 session.start 之后才 resolve → 断言 gitStatus 未被旧快照污染（代次门丢弃迟到 publish）；
  - 代次门交错时序（B1 条目 2a 顺序契约，R4 P1 落实；R5 P2 增第四场景）：四种交错各一序列——旧会话 publish 分别在 ①代次递增之前、②递增后清空前、③清空后（重建前）到达 → 第一种断言写入被随后的清空兜底清除，②③断言门禁直接拒绝，三种交错后 gitStatus 均不得含旧 cwd 快照（不存在"清空已完成而代次未变"的写入窗口）；④比对-写入原子性（R5 P2 落实）——旧会话 publish 已调用 update、其回调尚未执行（替身延迟回调执行）时 session.start 递增代次 → 断言回调执行时不写入旧快照、原样保留 prev：比对以回调执行时刻为准、与写入同帧，不存在"检查已过而写入未落"的窗口；
  - 渲染树对比拆三组（R4 P2 拆组、R5 P2 补条件）：①基线回归——限定未触发新功能场景（无通关卡、无任务）且**显式固定 companion=off**（小生物默认 on——B2 条目 4，无任务时进睡觉态仍渲染占位，不固定则基线必含 B2 新增节点、必不齐），`artDirection=default` 渲染树与改动前基线快照一致；②双皮肤同态对比——相同新功能状态下（如通关卡展示时）default 与 mission-control 渲染树的结构与非文案信息（节点数、MARK 符号、TONE 色）一致，仅文案不同；③companion=on 默认态双皮肤对比——两皮肤在相同状态（含小生物行；取无任务睡觉态，与 ① 同场景仅 companion 开关差异，互补覆盖）下结构与非文案信息一致，仅文案不同（skin 只换文案不改结构，B1 条目 9）。

### 验收标准

1. 全绿收口且前置校验通过 → 面板渲染树含通关卡（文件数注明"声明边界"口径；统计不可用——gitStatus 为 null（含 session.start 后待首轮查询）或任一必需 numstat 侧失败——时 ±行数为 `—` 且 statsAt 缺省；统计可用时为数值并附"统计截至 HH:MM"；byPath 无 scope 文件时为真实 0，与 `—` 两态可区分；分钟数为收口时刻 − 首次声明起点（口径注明"自首次边界声明"），缺失时为 `—`；全绿标记）；tests 不全绿的收口 → 必不现通关卡且既有卡被清；scope 缺失或他批残留的收口 → closure 整体不写入、战报不出现，旧卡按条目 4 统一规则处置（异键必清，同 plan#batch 全绿重复上报三出口均保留——卡不清、lastRun 与 store 经重放保留含 closure 记录）。逐条 PASS/FAIL 附测试输出。
2. idle 上报后通关卡从面板消失；"上次执行"摘要行（408）为战报格式；新会话恢复 toast（869）同样为战报格式。
3. 基线回归限定未触发新功能的场景（无通关卡、无任务，且显式固定 companion=off——小生物默认 on，无任务无卡场景它仍渲染（睡觉态），不固定则基线必不齐；`artDirection=default` 渲染树与改动前基线一致——快照回归）；双皮肤对比验收两组：相同新功能状态下（如通关卡展示时）default 与 mission-control 渲染树的结构与非文案信息（节点数、MARK 符号、TONE 色）一致，仅文案不同；companion=on 默认态下两皮肤在相同状态（含小生物行）的结构与非文案信息同样一致，仅文案不同。
4. 既有全部测试（`claude plugin test plugins/flow-deck`）无回归。

### 代码评审节点

- numstat 工作树口径的如实披露（与 B1 条目 3 同口径）：统计不可用——gitStatus 为 null（最近一次轮询失败退避 poll.ts:130-131、非 git 仓库或 session.start 后待首轮查询）或 `numstatSides` 任一必需侧 failed（条目 2；skipped 未查询不算失败）→ added/removed 为 null、statsAt 缺省，战报显示 `—`；统计可用 → 数值，statsAt 记录该快照 fetchedAt，通关卡战报展示"统计截至 HH:MM"——**不做任何滞后区间承诺**（轮询失败与快照防抖 poll.ts:133-137 下滞后无可靠上限，时间戳是唯一如实披露）；byPath 无该文件 → 真实 0。未跟踪文件与二进制 diff（`-` 行）不计入行数；收口后提交的部分不计入——口径以 statsAt 时间戳为准，防止误读为精确统计。
- 首报时间 map 生命周期对照"新增状态生命周期"表核对（flow_batch 声明三态：首次记起点 / 同键重新声明（边界调整）不重置起点 / 异批记新键旧键保留；session.start 清空；无起点 minutes 为 null 显示 `—`）；收口组装语句顺序逐行核对（minutes 判定 → scope 前置校验 → gitStatus 取数（含 numstatSides 侧判定）→ 并入 stamped，均先于 progress 更新，重排需回指条目 3 顺序契约）。
- 清卡统一规则逐分支核对（条目 4：四直接出口 + 收口报告三分支——写新卡 / 清卡 / 同 plan#batch 全绿重复三出口保留（卡 + lastRun/store 重放），逐出口核对不存在"无 closure 的 stamped 写入 lastRun/store"残留通路）；跨会话 git 快照隔离核对（条目 2a：session.start 先同步递增 generation（无 await）再清空 gitStatus、后重建 timer（顺序契约——先清空后递增会留"清空已完成而代次未变"的写入窗口）+ 代次门拦截旧会话在途 publish——比对与写入须在同一 update 回调内完成（回调外比对后写入存在"比对已过而写入未落"窗口，R5 P2 口径），只清空无门禁时旧查询迟到写入仍会污染，两件缺一不可）；guardWarned 条件清理逐点核对（条目 4：flow_task 声明与 flow_report 非收口分支仅在任务/批次实际变化时清、同批阶段上报路径上不得存在任何清 guardWarned 的残留代码，flow_batch 声明（既有 1009 行）维持既有契约不动，捂脸门判定无假阳性通路）。
- skin 术语表是否越界改了信息量（评审对照：7 条映射外的文案一律不动）。

### 分级与验证流程

T1 低。依据：纯加法式改动（可选字段、新增 atom/函数/配置），不触碰守卫判定与轮询判定/节流路径（红线 3：poll.ts 仅 numstat 数据装配的加法式扩展），有既有测试覆盖模式可仿写。按 T1 流程：执行代理实施 → 主控亲自机械验证收口。

---

## B2：呼吸面板 + 驻场小生物（T2）

### 如何改

1. **节拍器与帧 atom**（`hooks/register.tsx`）：`beatTimer = $.clock.every(BEAT_MS=800, ...)` 在 **session.start 回调内创建**——register（754 行）只有 on/options、无引擎对象 `$`，`$.clock.every` 仅在该回调内可用（创建语句模式同 908-911 planTimer/gitTimer）；创建前先 `beatTimer?.cancel()` 取消旧实例并 `update($, beat, () => 0)` 重置帧号（生命周期模式同 780-781 取消旧 planTimer/gitTimer），防重复 session.start 累积定时器。回调体仅两件事：`$.ui.panes()` 含 `deck` 时 `update($, beat, b => b ^ 1)`，否则空操作（红线 1-3 的全部体现）；panes 查询失败时跳过本次翻转（fail-closed：try/catch 吞错、定时器保持存活下一 tick 重试，模式同 894-900 refreshAgentPane 的异常处理）。`beat: 0 | 1` 加入 PluginState（types index.d.ts PluginState 区追加）。呼吸频率不做配置项（硬编码，观察期后再议）。
2. **呼吸渲染**：工作流页签中"运行中"元素——阶段进度条当前段与执行阶段行——的着色在 `TONE.accent` 与 dimColor（现有暗档，register.tsx:408 先例）之间按 `beat` 切换；验证计数反馈为全绿定格：`testsPassed === testsTotal && testsTotal > 0` 时计数行渲染 `MARK.done`（✓）前缀——纯函数派生自 report 字段、无独立生命周期（此处把 grilling 共识的"落定跳变一帧"微调为"全绿定格"：跳变帧需要额外状态记录与自动清除规则，给不出确定断言；定格同样标识验证落定且纯派生可测）。`stall !== null` 时上述呼吸元素固定灰档（dimColor）不再随 beat 切换——停跳即"死了"（小生物抖腿态不受此灰档约束，见条目 3）。ctrl+o 展开态不影响（面板本身不在展开视图内，透传逻辑无涉）；AbovePrompt 输入区横条（1175 起）不加呼吸（面板专属，克制）。
3. **小生物状态机**（`hooks/parse.ts` 新增纯函数 `creatureState(sources): CreatureState`，输入全为现有 atoms 的只读快照）：优先级 敬礼（closureCard 非空）> 捂脸（`currentTask 非空 && guardWarned.length > 0`——警告属于活动任务：guardWarned 的清理点为 session.start（766 行）与任务/批次实际变化的激活点（flow_task 声明异任务、flow_batch 声明（1009 行既有，边界变化重置）、flow_report 非收口分支（985-987）仅异批时清——清理条件单一出处 B1 条目 4（R5 P1 口径）：同批阶段上报不清、去重保留；flow_report 非收口分支不经 flow_task 直接激活新任务，异批不清则旧任务告警在新任务开启后残留重现），flow_report 收口分支仍不清 guardWarned，故判定必须以活动任务为门（收口后 currentTask 置 null、捂脸退位），否则批次结束后的历史告警长期压住停滞/分身/干活/睡觉态；guardWarned 为 `string[]`、初始 `[]`（register.tsx:65 / types:158-159），必须按长度判定，非 null 判断会在初始空数组即命中捂脸态）> 抖腿（stall 非空）> 分身（agents.agents 有 running）> 干活（currentTask 非空）> 睡觉（其余）。`creatureFrames: Record<CreatureState, [string, string]>` 盲文两帧静态常量（每态两帧，共 12 个字符串常量），帧选择 `frames[beat]`。
4. **小生物渲染**：工作流页签标题行右端固定占位（单行，两帧盲文字符 ≤4 列宽；"角落 ≤3 行"按单行落地，超宽面板不扩展）。`companion` userConfig（plugin.json，default `on`；register.tsx 配置模式区新增 `companionMode`，off 时渲染层跳过，节拍器与呼吸不受影响——呼吸独立于小生物存在）。
5. 呼吸与小生物共用 beatTimer（单一 clock），不建第二个定时器。

### 如何验证

- L1：`creatureState` 优先级单测（六态互斥、组合输入取最高优先级；初始空数组 `guardWarned = []` 不命中捂脸态、落到次优先级态）；警告态作用域状态转换单测：告警（currentTask 非空 + guardWarned 非空 → 捂脸）→ 收口（currentTask 置 null）→ 捂脸退位落次优先级态；告警 → idle（currentTask 置 null）→ 同前断言；告警 → flow_task 切新方案/迭代（任务实际变化，guardWarned 经 B1 条目 4 条件清理清空、currentTask 换新非空）→ 捂脸退位落干活态（历史告警不跨任务残留，R3 P2 落实）；告警 → 收口 → 直接 flow_report 上报异批执行阶段（不经 flow_task，批次实际变化，guardWarned 经 B1 条目 4 非收口分支异批清理清空、currentTask 换新非空）→ 不捂脸、落干活态（flow_report 激活路径不残留旧告警，R4 P2 落实）；creatureFrames 常量宽度断言（每帧 ≤4 显示列）。
- L2（替身编排）：
  - 红线 1 回归：连发 3 次 beat tick，断言除 `beat` 外全部 PluginState 键快照不变；
  - 红线 3：`$.ui.panes()` 替身返回不含 deck → 断言 beat 不变；panes 替身抛错 → 断言 beat 不变且定时器存活（下一 tick 正常翻转）；
  - 节拍器生命周期：连续两次 session.start（register.test.ts:53 触发模式）后驱动一个 BEAT_MS 周期 → 断言单周期 beat 翻转次数不翻倍（旧 beatTimer 已取消）；
  - 呼吸断言（范围限定呼吸元素行——进度条当前段与阶段行，排除小生物行）：活动任务下两帧快照（beat=0/1）着色档位交替；
  - 小生物断言（独立于呼吸断言）：两帧帧字符随 beat 切换；stall 注入 → 呼吸元素固定 dimColor 两帧一致、小生物抖腿态两帧继续切换（职责所在，两者断言互不矛盾）；
  - companion=off → 渲染树无小生物节点，beat 照常翻转（呼吸仍在）；
  - closureCard 非空 + guardWarned.length > 0 → 取敬礼（优先级断言）。
- L3：`claude plugin test plugins/flow-deck` 全量 + `claude plugin validate plugins/flow-deck`（均从仓库根运行）。

### 验收标准

1. 面板可见时呼吸元素以 800ms 周期两档交替（两帧快照差异仅在着色；断言范围排除小生物行）；面板关闭后 beat 停止翻转（替身断言）。逐条 PASS/FAIL 附测试输出。
2. stall 注入后呼吸元素两帧快照完全一致（停跳转灰）；小生物抖腿态两帧继续动画（独立断言，互不矛盾）。
3. 六态小生物各自渲染正确，`companion=off` 时缺席且呼吸不受影响。
4. 红线 1-3 各有一条定向测试且通过；全量测试无回归。

### 代码评审节点

- beat 回调是否无数据面 IO（逐行核对，含异常路径；panes 可见性判定除外）；
- beatTimer 生命周期与 780-781 模式一致（session.start 内创建、创建前取消旧例并重置 beat，重复 session.start 不累积定时器）；
- 呼吸元素清单是否越界（只限进度条当前段与阶段行，DAG/评分/git 一律静止）；
- 小生物状态优先级与共识表一致（敬礼最高、睡觉兜底）。

### 分级与验证流程

T2 标准。依据：多文件、邻近既有防抖契约（红线 1，帧误写数据 atoms 即破坏 gitSnapshotKey 防抖）但不改契约本身，测试模式有先例。按 T2 流程：执行代理实施 → 审计代理证据包模式收口。

---

## 收尾（T0，主控直做）

1. 版本 0.18.0：`.claude-plugin/plugin.json` 与 `.codex-plugin/plugin.json` 对齐升版（marketplace.json 无版本字段，不动）。
2. README.md：按现有条目风格补记四功能（通关卡两出口、皮肤术语表、呼吸与停跳、小生物六态与配置），更新"轮询开销"表（新增：beat 节拍 800ms 仅面板可见时翻转一个布尔 atom）。
3. 最小真机验收（先例：plans/flow-deck/2026-11-01-native-ui-redesign.md 的"收口与真机目检"）：Claude Code 真机过五项——深浅主题（`/theme` 两档）、窄宽面板（<44 列去边框形态）、工作流与文件树/文档页签切换、停滞表现（人为停滞场景）、面板关闭后表现；结果记入下方"观察期检查单"头部的真机目检区，与自动化结果分开记录。
4. 两周观察期检查单（不阻塞发布，记入本文档尾）：余光察觉停滞、战报可复述、10 秒理解皮肤、小生物抬头率。
5. 收尾验证命令（从仓库根运行）：`claude plugin test plugins/flow-deck`、`claude plugin validate plugins/flow-deck`。

## 观察期检查单（发布后两周回填）

真机目检（发布前收尾批执行，与自动化结果分开记录）：
- [ ] 深浅主题两档（`/theme`）：通关卡/战报/呼吸/小生物配色随主题
- [ ] 窄面板 <44 列：去边框形态无布局破坏、小生物 ≤4 列占位不换行
- [ ] 工作流 ↔ 文件树 ↔ 文档页签切换：各形态保持
- [ ] 停滞表现：呼吸元素灰档停跳、小生物抖腿态继续动画
- [ ] 面板关闭后：beat 停翻、重开后恢复

- [ ] 停滞灰档是否被余光察觉（人为停滞场景自测）
- [ ] 最近一次全绿战报能否被复述出至少一个数字
- [ ] 未用过 deck 的人 10 秒能否说出面板在干什么（皮肤默认 mission-control 下）
- [ ] 一周内是否抬头看小生物 / 主动向他人展示
