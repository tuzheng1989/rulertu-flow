# flow-deck 深度原生界面重构方案（主题融合 + 标志组件 + 原生控件 + 文件树面板）

日期：2026-11-01 · 状态：自审修复后定稿 · 基线：worktree `flow-deck-redesign`（基点 9c6155c）
验证基线命令（红线回归，仓库根运行）：`claude plugin validate plugins/flow-deck` + `claude plugin test plugins/flow-deck`
锚点口径：全部 `文件:行号` 以基线 9c6155c 为准；前序批次会新增 JSX 行使后续批次锚点后移，执行时一律按内容特征重新定位，不盲用行号。

## 背景与目标

用户选定 C 路线（深度原生）并追加文件树融合批：不装第三方 filetree mod，文件树作为 flow-deck 自研面板，与批次守卫、git 状态同源联动。目标三条：

1. **融入**：全部界面颜色从 ANSI 字面量（cyan/green/yellow/red）迁移到引擎主题语义 key，面板随用户 `/theme` 与换肤类 mod 自动适配。
2. **辨识**：两个 flow-deck 独有的可视化（批次流水线条、评审达标刻度条）+ 原生控件（primary 按钮、反色 chip、hover、Markdown 渲染）。
3. **痛点**：`/tree` 文件树面板——本会话改动清单置顶 + 目录懒浏览 + 批次边界标注，解决「agent 跑完后要到系统资源管理器找改动文件」。

非目标：不追平第三方 filetree 的搜索/treemap/diff 视图；不做动画计时器；零新依赖；不触碰守卫判定（`guardDecision`）与轮询调度逻辑（poll.ts 语义不变）——这是本方案红线：**B1-B4 任一批次不得改变守卫放行/拦截行为与轮询节奏，只允许在既有钩子内追加渲染数据记录**。

## 设计契约（单一出处）

### 色彩映射

全文色彩只经 `hooks/ui.ts` 的 `TONE` 常量取值（`import type { ThemeKey } from 'claude-code'`，`as const satisfies Record<string, ThemeKey>`）：

| 键 | ThemeKey | 承接旧值 | 语义 |
| --- | --- | --- | --- |
| `accent` | `claude` | `cyan` | 面板标题、flow 前缀、进行中强调、chip 底色 |
| `ok` | `success` | `green` | 完成/达标/已暂存/ahead/干净 |
| `warn` | `warning` | `yellow` | 警告/待达标/未暂存/behind/停滞 |
| `bad` | `error` | `red` | 失败/冲突/P0/越界 |
| `added` | `diffAdded` | `green`（+行数） | 行级新增 |
| `removed` | `diffRemoved` | `red`（−行数） | 行级删除 |

规则：↑ahead/↓behind 用 `ok`/`warn`（分支导航语义）；+N/−N 行数用 `added`/`removed`（diff 语义）。次级文本沿用 `dimColor`；chip 文字色用 `inverseText`。23 个 ThemeKey 之外不用任何 raw color（若真机目检发现 `claude`/`diffAdded` 观感不可接受，回退方案记录于「风险与回退」）。

### 符号表

全文状态符号只经 `hooks/ui.ts` 的 `MARK` 常量取值，一词一义：

| 符号 | 键 | 唯一语义 |
| --- | --- | --- |
| `▍` | `title` | 面板/区块标题前缀（唯一标题标记；`●` 不再用于标题） |
| `●` | `run` | 活动中（含子代理运行中、DAG 节点 `▣` 的行内形式） |
| `○` | `idle` | 非活动（待执行/未知状态/子代理已停止——agents killed 并入此键，不再单用 `■`） |
| `✓` | `done` | 完成/达标/干净 |
| `✗` | `bad` | 失败/冲突 |
| `■` `▣` `□` | `nodeDone`/`nodeRun`/`nodeWait` | DAG 节点三态（保留现状字符） |
| `▏` | `gauge` | 评审达标线刻度（scoreGauge 内固定位置，由 pass 决定，不随 score 移动） |
| `╌` | `linkWait` | 流水线连线待执行段（下游 pending） |
| `◆` | `pin` | 批次边界内文件标注（B4 引入） |
| `↑` `↓` `←` `→` `↳` | 保留字面量 | ahead/behind/依赖/rename/父级 |

面板标题改版（B1）：`FLOW / …` → `▍工作流 · …`、`DOC / …` → `▍文档 · …`、`GIT / 仓库状态` → `▍仓库 · 状态`（分支仍在标题下首行）。保留 `◇ git`、`▸` 横条前缀。agents.ts 的 killed（已停止）改用 `MARK.idle`（○），同步更新 `register.test.ts` 中 `/■ 已停止/` 断言（现状 :141 附近）为 `/○ 已停止/`。

## 路线图

### 优先级矩阵（价值 × 成本）

| 批次 | 价值 | 成本 | 序 |
| --- | --- | --- | --- |
| B1 色彩与符号迁移 | 最高（全局融入根基） | 低（纯替换+断言更新） | 1 |
| B2 标志性组件 | 高（辨识度） | 中（两纯函数+渲染接入） | 2 |
| B3 Markdown/hover/分层 | 中高（原生质感） | 中（含真机形态探针） | 3 |
| B4 文件树面板 | 高（痛点直击） | 高（新面板+新钩子数据） | 4 |

### 波次依赖

B1 → B2 → B3 → B4，线性。依据：后续批次都在 `register.tsx` 渲染树内工作且消费 B1 的 `TONE`/`MARK`（文件集不互斥，不并行）；B2 的状态点行与 `MARK` 符号被 B4 复用；B3 与 B4 相互独立但共享收口真机目检，线性摊薄装载开销。B2 与 B3 在 doc 面板返回块内物理相邻（B2 改 :762 按钮，B3 主战场 :743-:760），线性顺序天然消解交叠。

## 详案

### B1 主题语义色迁移与符号统一（T1）

**如何改**：

1. 新建 `plugins/flow-deck/hooks/ui.ts`：按「设计契约」导出 `TONE`、`MARK` 两常量（含 ThemeKey 类型标注与一行注释说明来源本方案 §设计契约）。
2. `hooks/agents.ts:5-13`：`agentStatus` 返回色名 `'cyan'|'green'|'red'|'yellow'` → `TONE.accent|TONE.ok|TONE.bad|TONE.warn`，返回类型 `color?: string` 收窄为 `ThemeKey`；`mark` 字段改引 `MARK`，killed（已停止）由 `■` 改 `MARK.idle`（○，见符号表）；同步更新 `register.test.ts` 的 `/■ 已停止/` 断言。
3. `hooks/register.tsx` 逐点替换（色值字面量 → `TONE.*`；状态点字面量 → `MARK.*`）：
   - :550 刷新失败行 `color="yellow"` → `TONE.warn`；
   - :556-561 子代理卡 `borderColor={status.color}`（随 agents.ts 生效）、状态点 `status.mark`；
   - :586 面板标题 `color="cyan"` + 文案 `FLOW / …` → `TONE.accent` + `▍工作流 · …`；
   - :592-612 执行卡：`borderColor="cyan"`/标题 :594/进度 :598-:600/停滞 :604/验证 :606 → accent/ok/warn 映射；
   - :615 评审区标题、:621 `tone`（green/red/yellow → ok/bad/warn）、:624 状态点、:633 delta ↑↓ 色（green/red → ok/bad）、:638-:640 P0/P1/P2 色、:648 达标折叠行；
   - :649-671 DAG：总览行 :652 `cyan` → `TONE.accent`，:653-:659 与 :662-:669 三态色（green/yellow → ok/warn）、状态点/节点字符引 `MARK`；
   - :678-768 doc 面板：:715/:716 读取失败标题与正文（red → bad）、:727/:744 标题（cyan → accent）+ 文案 `DOC / …` → `▍文档 · …`；
   - :770-861 git 面板：:785 标题改版、:789-:790 ↑↓（green/yellow → ok/warn）、:793-:796 行数（green/red → **`TONE.added`/`TONE.removed`**）、:800 干净行、:801-:845 冲突/暂存/未暂存分区（red/green/yellow → bad/ok/warn）、分区标题前缀统一 `MARK.title`；
   - :863-905 横条：:880 `● flow`（cyan → accent，● 引 `MARK.run`）、:892 `◇ git` 色、:893-:900 冲突/↑↓/行数色（行数同样走 added/removed）。
4. `hooks/register.test.ts`：:495 `props.color === 'green'` → `'success'`、:497 `'yellow'` → `'warning'`；标题文案断言若命中旧 `FLOW /`、`DOC /` 字样同步更新（全文 grep 确认）。

**如何验证**：L1 既有全套（红线回归命令）+ `tsc -p plugins/flow-deck` 类型检查（ThemeKey 收窄是否成立）+ 改动 diff 逐行机械审查（只允许色值/符号/标题文案三类替换，不得出现逻辑改动）。

**验收标准**：
- 给 `claude plugin test plugins/flow-deck` → 全部通过（含更新后的颜色断言与 `/○ 已停止/` 断言）。
- 给 `grep -nE "['\"](cyan|green|yellow|red)['\"]" plugins/flow-deck/hooks/register.tsx plugins/flow-deck/hooks/agents.ts` → 0 命中（渲染层无 ANSI 字面量残留，单双引号均计；`ui.ts` 常量定义除外）。
- 给/不给守卫输入 → `guardDecision` 相关测试结果与基线完全一致（红线）。

**代码评审节点**：`ui.ts` 是否零逻辑纯常量；agents.ts 返回类型收窄后 `register.tsx:556` `borderColor` 接受 ThemeKey；标题改版是否漏改横条/面板文案一致性。

**分级与验证流程**：T1（界面调整、加法式替换、不邻近契约、有全套测试覆盖）→ 主控亲自机械验证收口，无审计代理。

### B2 标志性可视化组件（T2）

**如何改**：

1. `hooks/parse.ts` 新增两个纯函数：
   - `scoreGauge(score: number, width = 10, pass = PASS_SCORE): string`——十格 `━/─` 条，`▏` 为**固定达标线刻度**：位置恒为 `Math.round(clamp(pass/10) * width)`（0 基插入索引，clamp 到 `0..width`），由 `pass` 决定、不随 score 移动；实格数 `Math.round(clamp(score/10) * width)` 照旧。示例（width 10、pass 8.5、passAt=9）：score 6.8 → `━━━━━━━──▏─`（7 实 2 虚 + 刻度 + 1 虚）、score 8.5 → `━━━━━━━━━▏─`（刻度恰在实虚交界）、score 0 → `─────────▏─`、score 10 → `━━━━━━━━━▏━`、pass=10 → 刻度在串尾 `━…━▏`。
   - `pipelineLinks(nodes: readonly DepNode[]): readonly DepNodeStatus[]`——返回节点间连线状态序列（长度 `max(nodes.length - 1, 0)`），**连线状态 = 右侧节点状态**（流向由下游决定）：右侧 done/active 渲染 `━`（色随该节点 ok/warn），右侧 pending 渲染 `╌`（`dimColor`）。
2. `hooks/register.tsx` 渲染接入：
   - :631 评审卡评分行：`progressBar(latest.score, 10)` → `scoreGauge(latest.score)`（sparkline、delta 保持）；
   - :652-:661 DAG 总览行：节点字符与 `pipelineLinks` 连线交错渲染——节点 `■/▣/□` 沿用现有三态色；连线段 `━`（done/active 端，色随邻接节点取 ok/warn）或 `╌`（纯 pending，`dimColor`）；行尾统计文案保持 `N/M 收口`；
   - :595 执行卡 T 级渲染 chip 化：`tLevel` 存在时画 `<Text backgroundColor={TONE.accent} color="inverseText"> {tLevel} </Text>`，批号 `B2` 保持普通文本；
   - :762 doc 面板「发给 Claude」按钮加 `variant="primary"`；:548 面板刷新按钮保持 `plain`（次要操作，不升级）。
3. `hooks/parse.test.ts` 新增 L1 用例：scoreGauge（0/10、6.8、8.5 恰在刻度、10 满格、越界 clamp、pass=10）；pipelineLinks（单节点空数组、全 pending、done-active、active-pending、两 active）。
4. `hooks/register.test.ts`：DAG 总览行断言适配连线字符（:494-:500 findAll `■/▣/□` 颜色断言结构不变，应继续通过；若连线改变聚合文本匹配，按 `findAll({ type, text })` 粒度修正）；新增评审卡含 `▏` 断言。

**如何验证**：L1（parse.test 新用例）+ L2 渲染树（register.test：评审卡 `▏` 存在、DAG 行连线存在、chip 存在且 `props.backgroundColor === 'claude'`）+ 红线回归。

**验收标准**：
- 给 score 6.8 → `scoreGauge` 输出 `━━━━━━━──▏─`；给 score 0 → `─────────▏─`（刻度固定在 passAt 位置）；给 score 8.5 → `━━━━━━━━━▏─`；给 score 12 → 满格 `━━━━━━━━━▏━` 无越界字符；给 pass=10 → 刻度在串尾。
- 给 3 节点 [done, active, pending] → 总览行文本含 `■━▣╌□` 顺序字符（active→pending 段为 `╌`），各段颜色符合映射（连线段 dimColor）。
- 给 flow_report tLevel=T1 → 渲染树存在 `backgroundColor === 'claude'` 且文本含 `T1` 的 Text；不给 tLevel → 无该 Text。
- 红线回归全绿。

**代码评审节点**：`▏` 插入不改变 sparkline/delta 对齐；连线状态取右规则的实现与用例一致；chip 不出现在横条（横条空间窄，chip 只在面板内）。

**分级与验证流程**：T2（多文件、新增渲染逻辑与纯函数、邻近 UI 渲染契约但不改契约、有既有测试模式可循）→ 审计代理（证据包模式）。

### B3 /doc Markdown 渲染与 hover 增强（T2，含形态探针）

**如何改**：

1. `hooks/register.tsx:743-:760` doc 节内容块：区块标题行（现状 :754 为 `#` 前缀文本）改为 `MARK.title` 前缀（`▍<节标题> · 第 a–b 行` + 截断提示），正文 `shown.map(...)` 逐行 Text 替换为 `<Markdown key="doc-body" text={shown.join('\n')} />`；`DOC_SECTION_MAX_LINES` 截断逻辑保持在文本层（parse.ts 不动）。
2. hover 分层降噪：:556 子代理卡与 :623 评审卡 Box 加 `borderDimColor`（常态 dim 边框），并加 `hover={{ borderDimColor: false }}`（指针悬停提亮；`BoxHoverProps` 支持 borderDimColor 覆盖）；:593 执行卡保持常态亮边框不加 hover（关键卡常亮）。
3. `hooks/register.test.ts`：新增 doc 面板两 surface 循环用例（仿 :120/:330 既有循环模式）断言 `find({ type: 'Markdown' })`（text 含节内容首行）；hover 仅断言树通过（悬停行为属真机目检）。

**如何验证**：L2 渲染树（两 surface）+ 红线回归 + **真机形态探针**：`claude --plugin-dir plugins/flow-deck` 打开 /doc 与 /flow，确认 Markdown 标题/列表/代码块渲染正常、长节截断生效、悬停提亮可见（全屏终端）；探针结果回写本节（通过/问题记录）。

**验收标准**：
- 给含 fenced code 的文档节 → 渲染树含 `type: 'Markdown'` 且 text 首行等于节内容首行；节超 60 行 → text 内行数 ≤ 60。
- 给两 surface（terminal/desktop）→ 渲染树均通过引擎校验（mount 不报拒绝）。
- 红线回归全绿；真机探针通过后才允许本批收口。

**代码评审节点**：Markdown 不进横条与问题对话框路径；hover 对象必须已带 `key` 的 Box；截断提示文案随 Markdown 化是否仍准确（行数口径一致）。

**分级与验证流程**：T2（Markdown 元素首次引入、行为依赖引擎渲染，需探针验证）→ 审计代理（证据包）+ 主控真机探针。独立收口理由：探针批——Markdown 渲染行为未经验证，失败回退不得波及 B2 组件。

### B4 文件树面板（T2）

**如何改**：

1. `types/index.d.ts` 契约追加（不改既有字段）：`treeDir: string | null`（当前浏览目录，null=cwd 根）、`treeEntries: { entries: FsEntryLike[]; loaded: boolean } | null`、`touched: { path: string; at: number }[]`（本会话 Edit/Write 记录，去重保序，上限 50）。`FsEntryLike = { name: string; kind: string; isLink: boolean }` 与 `$.fs.list` 应答字段一致。
2. `hooks/register.tsx`：
   - 新 atom 三枚（:43-:59 区追加）；
   - `hooks/parse.ts` 或 ui.ts 不新增数据函数；目录排序纯函数 `sortEntries(entries)`（目录在前、字典序）放 parse.ts 供 L1；
   - :513-:526 既有 Edit/Write 守卫钩子：两处 `return next(e)`（pass 放行与 warn 放行）之前统一追加记录 `recordTouch($, e.file_path)`——warn 模式下越界放行的改动同样发生，必须记录；deny 分支（未发生改动）不记录；去重（大小写折叠，与守卫 key 同口径）更新 `touched`，cap 50。判定逻辑、分支顺序、返回值零改动。实现口径：采用 `await`（方案初稿为 `void`）——写完成才放行，换来测试断言确定性；recordTouch 内部 try/catch 兜底，守卫放行/拦截语义不变（波次审计 5 复核确认）；
   - `session.start`（:233-:385）注册 `/tree` 命令 + treeTimer 不需要（复用既有 2 秒 planTimer？否——目录列表仅在面板打开时懒加载，打开即 list 一次、切换目录时再 list，无轮询）；
   - 新 `ui.render` Pane 钩子（id `flow-tree`，标题「文件」）：
     - 标题行 `▍文件 · <treeDir ?? cwd 尾段>`；
     - 区块 `▍本会话改动`：touched 列表，每行 `✓/● 路径` + git 状态标注（与 `gitStatus` 文件集匹配，色沿 git 面板口径：暂存 ok/未暂存 warn/未跟踪 dim/冲突 bad）+ 批次边界内标注 `◆ · 本批`（与 `batchScope.files` 匹配）；空态「本会话尚无文件改动」；
     - 区块 `▍目录`：`sortEntries(treeEntries)` 列表——目录行 `名/`、文件行 `名 + git 状态标注`（git 码与色沿 git 面板口径），目录行 Button plain 热键（1-9，超 9 个用 Select 下拉选目录）；`r` 热键重载当前目录；
     - 底部提示行。
3. `hooks/register.test.ts`：经 `$.tool.call` 触发 Edit 记录 touched（测试引擎写状态的工具链路口径，mock `$.fs.list` 遵循 FsEntry `isLink` 必填与路径相对解析既往坑）；渲染断言：改动区含已记录路径、边界标注 `◆`、空态文案、目录排序。
4. `README.md`（插件）：`/tree` 条目与轮询开销表补一行（打开时读取，无轮询）；双 manifest（`.claude-plugin/plugin.json`、`.codex-plugin/plugin.json`）版本 0.9.0 → 0.10.0；根 `CHANGELOG.md` Unreleased 补条目（三处同步，0.9.0 漏更教训）。

**如何验证**：L1（sortEntries）+ L2 渲染树（touched/边界/空态）+ 红线回归 + 真机目检（/tree 打开、进入子目录、批次边界声明后标注出现）。

**验收标准**：
- 给 `$.tool.call` 一次 Edit（路径 P）→ 渲染树「本会话改动」含 P；重复同路径 → 单条；第 51 条 → 挤出最旧。
- 给 batchScope 含当前目录文件 F → F 行含 `◆ · 本批`；不给 → 无标注。
- 给含子目录与文件的 entries → 目录在前字典序；目录热键/Select 进入 → treeEntries 更新为新目录内容。
- `/tree` 已开再调 → 关闭（toggle 口径同 /git）；红线回归全绿。

**代码评审节点**：recordTouch 不阻塞 next（void + 内部 catch）；touched 去重键与守卫 key 口径一致（归一化路径）；`$.fs.list()` 无参调用（空串坑）；面板关闭不残留定时器（本面板无定时器，确认无遗漏）。

**分级与验证流程**：T2（新面板、新契约字段、新钩子数据流、有既往测试模式可循）。定级裁决：本批虽邻近守卫链路并在守卫钩子内追加副作用，但属红线明文授权的「既有钩子内追加渲染数据记录」（加法式、判定/分支顺序/返回值零改动、fail 路径不触及），故定 T2 不升 T3。→ 审计代理（证据包）+ 主控真机目检。

### B5 统一命令 /deck 与面板页签化（T2，用户测试后追加）

背景：用户测试 0.10.0 后提出——/git 与 /tree 信息重叠应合并；命令 5 个太多应统一。裁决：`/deck` 单命令 + 单面板三页签（工作流/文件/文档），git 信息以「统一改动清单」并入文件页签。

**如何改**：

1. `hooks/parse.ts` 新纯函数：`collectChanges(git, touched): ChangeRow[]`——git 四组文件 ∪ 本会话 touched 去重合并，每行 `{ path, touched, state }`（state ∈ conflict/staged/unstaged/untracked/null）；排序：touched 组在前、冲突优先、路径字典序。L1 用例覆盖并集去重、来源判定、排序与 git 为 null 退化为 touched 清单。
2. `types/index.d.ts` 契约追加：`activeTab: 'flow' | 'files' | 'doc'`。
3. `hooks/register.tsx`：
   - 单一 `DECK_PANE_ID = 'deck'`；`activeTab` atom（默认 'flow'）；旧 PANE_ID/GIT_PANE_ID/TREE_PANE_ID/DOC_PANE_ID 退役。
   - 命令收敛：仅注册 `deck`（description 含三页签用法）；`/deck` 无参 toggle（activeTab 保持）；`flow`/`tree`/`doc [路径]` 参数切页签（tree 映射 files 页签），doc 带路径先 loadDoc。旧 /flow /git /flow-agents /doc /tree 命令注册与钩子全部移除。
   - 单一 ui.render Pane 钩子（requestId 'deck'）：顶部页签行（三枚 Button，plain + hotkey 1/2/3，当前页亮、其余 dimColor）+ 按 activeTab 分支渲染——工作流页签（原 /flow 渲染树迁移）、文件页签（git 头行 + 统一改动清单 `▍改动`（● 本会话 / ○ 其他，◆ 本批）+ 目录浏览区迁移）、文档页签（原 /doc 渲染树迁移，含空态与错误态）。`$.ui.open({ focus: true })` 使面板持焦，数字热键直切页签；holdToasts 不开。
4. `hooks/register.test.ts`：全部 Pane mount 的 requestId 改 'deck' 并经 `$.ui.press`（key tab-flow/tab-files/tab-doc）切页签后再断言原内容；新增用例——统一改动清单（git ∪ touched 并集去重、● ○ 来源点、◆ 边界、git null 退化）、页签切换保持各页内容、/deck 参数分流（flow/tree/doc 直达、doc 带路径装载）、旧命令不再注册（session.start 后 command.register 捕获清单恰为 flow_task/flow_report/flow_batch/flow_deps 工具与 deck 命令）。
5. `README.md` 命令节重写（/deck 用法与页签说明、/tree /git 并入说明）；双 manifest 0.10.0 → 0.11.0；根 CHANGELOG 补条目。

**如何验证**：L1（collectChanges）+ L2（页签切换后各页渲染树、统一清单断言、参数分流）+ 红线回归 + 真机目检（/deck 打开、1/2/3 切页签、Esc 回输入框、/deck doc 直达）。

**验收标准**：
- 给 git 有 2 文件改动且 touched 含其中 1 个 + 另 1 个会话路径 → `▍改动` 恰 3 行：会话 2 行 ●、git 独有 1 行 ○；touched 独有行无 git 状态标注。
- 给 git null → 改动清单退化为 touched 全集（全 ●）。
- 给 flow_batch 边界含清单文件 → 该行 `◆ 本批`。
- `/deck` 无参已开再调 → 关闭；`/deck doc plans/x.md` → doc 页签且文档装载。
- 会话内只注册 deck 一个命令；红线回归全绿。

**代码评审节点**：三个页签渲染分支迁移后 hotkey 不冲突（1/2/3 页签、r 刷新、e 发给 Claude）；plain Button 不与 variant 混用（选中态用亮暗对比实现）；collectChanges 去重键与守卫 key 口径一致（normalizePath + toLowerCase）；open({ focus: true }) 不带 holdToasts。

**分级与验证流程**：T2（多文件、面板结构重构、不改契约既有字段语义、测试迁移面广但有既有模式可循）→ 审计代理（证据包）+ 主控真机目检。

### B6 视线常驻空间：自动侧边栏、Spinner 进度、工具行批次标注（T2）

背景：用户测试后要求「参考官方 mod 充分利用空间，体验第一」。官方 diff mod 的自动开栏范式（首次成功编辑自动开、仅可停靠布局、用户关过则不再打扰、数据先就位）与本插件守卫语义契合，照抄。

**如何改**：

1. 自动侧边栏：`session.start` 重置 `autoOpened`/`deckTouched` 模块标记；`recordTouch` 首次成功记录时——若 `userConfig.autoOpen !== 'off'`、本会话无人在场标记（`manual` atom：用户曾开或关过 deck 则不再自动开）、AbovePrompt 钩子缓存的 `viewport.isFullscreen === true`——`$.ui.open({ id: DECK_PANE_ID, title, focus: false })`（自动开不抢键盘，与手动开的 focus: true 区分）。本会话只试一次。manifest userConfig 追加 `autoOpen`（title 自动侧边栏，options on/off，默认 on）。
2. Spinner 进度：新 `ui.render { component: 'Spinner' }` 钩子——实施中（currentTask=implement 且 execution 非收口）重写 `word` 为 `B2 · 验证 8/12`；迭代中显示 `评审 R{n} · {score} 分`；有 running 子代理且无任务时显示 `↻ {name} · {description 截断}`（多个时 `{n} 个子代理运行中`）；其余 `next(e)` 透传。desktop 表面 `message` 同步（props 相同）。
3. 工具行批次标注：新 `ui.render { component: 'ToolUse' }` 钩子（matcher 无法按 props.tool 收窄 input 路径，钩子内 `e.props.tool` 分流 Edit/Write）——`isExpanded === true` 或非 Edit/Write 或 isErrored/isInterrupted 时 `next(e)` 透传；紧凑行自绘：状态图标（Edit/Write 各自引擎色）+ 工具名 + 路径（input.file_path）+ 批次标注——界内 `◆`（accent）、越界 warn 放行 `⚠ 越界`（warning）、deny 拦截 `✗ 拦截`（bad）、无任务时无标注。判定复用 `guardDecision`（守卫口径单一出处），纯展示不改写 input。
4. `register.test.ts`：Spinner 三态（实施词/迭代词/子代理词/透传）、工具行三态标注 + isExpanded 透传 + 非 Edit/Write 透传、自动侧边栏（autoOpen off 不开、非 fullscreen 不开、手动开过后不开、首次编辑开一次）。

**如何验证**：L2 渲染树（Spinner/ToolUse mount）+ 红线回归 + 真机目检（全屏终端 agent 编辑时侧边栏自动出现、spinner 词变化、工具行标注）。

**验收标准**：
- 给 autoOpen=off → 任何编辑不自动开；给非全屏 → 不开；给用户手动开/关过 → 不开；给首次编辑且全屏 → 恰开一次。
- 给实施 report（B2 验证 8/12）→ Spinner 词含 `B2` 与 `8/12`；给无任务多子代理 → 词含 `个子代理运行中`；给空闲无子代理 → next(e) 透传（词不变）。
- 给界内 Edit → 工具行含 `◆`；给越界 warn → 含 `⚠ 越界`；给 isExpanded → 树为引擎原行（透传）。
- 红线回归全绿。

**代码评审节点**：自动开不抢焦点（focus: false）；Spinner 重写不碰 `suffix`/`message`（引擎继续画时长与 token）；工具行自绘行在 ctrl+o 下让位（isExpanded 透传）；manual 标记在手动 open/close 两处设置。

**分级与验证流程**：T2（新站点 hook ×2、自动开栏状态机、邻近渲染契约但不改契约）→ 审计代理（证据包）+ 主控真机目检。

### B7 交互深度：输入框守卫预览、子代理查看、完成通知行（T2）

**如何改**：

1. 输入框守卫预览：新 `prompt.edit` 钩子（origin composer）——实施中有 batchScope 时读草稿，提取路径样式 token（`/[A-Za-z0-9_.\-\\\/]+\.[A-Za-z]{1,6}/g`），逐 token 按守卫口径（normalizePath+toLowerCase 对 scopeSet）判定：界内 `color: TONE.ok`、越界 `color: TONE.warn`，`$.prompt.paint({ text, decorations })`；无任务或无路径 token 时 paint 空清单清除。paint 失败静默（debug log）。
2. 子代理查看：面板子代理行（工作流页签）追加 plain Button `查看`（key `agent-view-{id}`）→ `$.ui.view({ agentId })`；resolve `{ deny }` 时 `$.ui.toast` 说明原因；面板页签行尾部追加「主对话」Button（key `view-main`）→ `$.ui.view({})`。
3. 完成通知行：新 `ui.render { component: 'UserMessage' }` 钩子，matcher `props.origin.kind: 'task-notification'`——`next(e)` 透传 `isExpanded`；紧凑行自绘：状态点（completed ✓ ok / failed ✗ bad / 其余 ○ idle）+ 任务名（from.name 或 task.id）+ 耗时（durationMs 人读格式）。
4. `register.test.ts`：paint 判定（界内 ok/越界 warn/无任务清除）、查看按钮 press → $.ui.view 调用与 deny toast、通知行三态 + isExpanded 透传。

**如何验证**：L2（paint 参数捕获、view 调用捕获、通知行渲染树）+ 红线回归 + 真机目检（输入路径实时变色、点查看切子代理视图、Esc 回主对话、通知行样式）。

**验收标准**：
- 给实施边界含 `src/a.ts`、草稿含 `src/a.ts` 与 `docs/b.md` → paint 收到两个 decoration：前者 success 后者 warning；给 idle → paint 收到空清单。
- 给 running agent 行按查看 → `$.ui.view` 收到该 agentId；给 deny 应答 → toast 含原因；按主对话 → view 收到 `{}`。
- 给 task-notification（completed, 3.2s）→ 通知行含 ✓、名称与 `3.2s`；isExpanded → 透传。
- 红线回归全绿。

**代码评审节点**：paint 仅在 composer origin（子代理转录不碰）；路径正则保守（含扩展名 token 才判定）；view 的 person-initiated 语义（仅 Button 触发）；通知行 isExpanded 让位 ctrl+o。

**分级与验证流程**：T2（prompt.edit/paint 首次引入、新站点 hook ×2）→ 审计代理（证据包）+ 主控真机目检。

## 收口与真机目检

四批各自收口后，末波统一目检清单（Claude Code 真机，`/theme` 深浅两档各一遍）：

1. `/flow`：标题/评审卡/执行卡/DAG/子代理区块颜色随主题；流水线条与达标刻度可见；chip 反色清晰。
2. `/doc`：Markdown 渲染标题/列表/代码块；截断提示准确；primary 按钮为 accent 色。
3. `/git`：+N/−N 行数呈 diff 色；四分区色随主题。
4. `/tree`：改动区即时反映会话内 Edit；边界标注出现；子目录导航可用。
5. 横条：单行/双行空间下优先级不变；窄终端（<44 列）无布局破坏。

收尾（主控 T0 直做）：CHANGELOG 条目已随 B4 落盘，确认双 manifest 版本一致后按 `rulertu-flow:commit` 起草提交。

## 风险与回退

- `claude`/`diffAdded`/`diffRemoved` 主题 key 在个别主题观感不佳 → 目检记录实际观感，仅该用途回退到 `TONE.ok`/`TONE.bad`（改动局限 ui.ts 单点 + 对应行）。
- Markdown 元素在窄面板换行异常或与截断口径冲突 → 回退该节内容为 B3 前的逐行 Text（独立回退，不影响其他批）。
- hover 在非全屏终端无效果 → 设计即为渐进增强，无功能依赖。
- `▏` 刻度在等宽字体外的对齐风险 → 终端场景为等宽，风险仅限非等宽导出，接受。
- touched 记录在高频 Edit 下写放大 → cap 50 + 去重已限流；`相同快照不重复写状态` 口径沿用。
