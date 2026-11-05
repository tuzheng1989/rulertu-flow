# 方案：deck 变更对比视图 + 文件查看器地址输入栏 + GitHub Issues 区块 + brainstorm 回报收敛

- 方案名：`deck-diff-view-and-doc-input`
- 日期：2026-11-06
- 状态：待评审
- 涉及插件：flow-deck（B1，主体）、work-skills/brainstorm（B2）
- 需求来源：用户四项（2026-11-06 会话）

## 需求

1. **变更对比视图**：deck 文件树页签的「改动」清单中，git 变更文件点击后跳转文件查看器显示**变更对比（diff）**而非原文件全文。
2. **地址输入栏**：文件查看器空态提供输入栏，可直接输入文件地址打开文件，替代现在只有用法提示的空态。
3. **GitHub Issues 区块**：工作面板下方显示当前仓库 open issue 列表，通关后可据此开展下一步任务。
4. **brainstorm 回报收敛**：最终回报只报最终产出（洞察/设计/分支），不铺分析过程，避免阅读时混淆。

## 关键调研结论（方案钉点）

- 引擎面板组件含 **`Code`**：`format: 'diff'` 直接渲染 unified-diff hunks，自带 gutter、增删着色、hunk 行号；一次绘制可承载 100000 字符；mid-hunk 截断不解析（引擎 d.ts `CodeProps`，bundled-skills/2.1.314 实证）。**diff 行分类与配色无需自写**。
- 引擎面板组件含 **`Input`**：单行文本框，`onSubmit` 闭包经 `ui.input` 事件（kind: change|submit + value 全文）驱动；props 有 key/label/placeholder/submitLabel/autoFocus。测试宿主可 `$.ui.input({...})` 驱动。
- 引擎面板组件含 **`Link`**：OSC 8 超链接（终端不支持时 dim 显示 URL）；children 为内联文本。
- `runGit`（register.tsx:328）经 `$.process.run(['git', ...args])` 执行命令，cwd 即会话工作目录（既有轮询实证）；同通路可调 `gh`。`gh issue list` 在 clone 内自动推断 repo（docs/agents/issue-tracker.md 约定同口径）。
- `openInDoc`（register.tsx:267）→ `loadDoc`（:217）用 `$.fs.read` 装入 `docFile` atom `{ path, text, error? }`；改动清单行点击在 register.tsx:831。
- `collectChanges`（parse.ts:154）产出 `ChangeRow { path, touched, state }`，state ∈ conflict/staged/unstaged/untracked。
- 工作面板渲染尾部（register.tsx:655 附近）：子代理区之后、底部提示行之前是 Issues 区块的插入位。
- 轮询常量：`POLL_MS=2000`（:56）、`GIT_POLL_MS=5000`（:57）；`refreshAll`（:1042）聚合三个刷新入口。
- brainstorm 三模式手册中，深钻「输出格式」强制铺四段（钻探计划+下钻过程+洞察+边界）；创意产出卡五要素含大段论证；evals.json 断言 1/2/7 与新回报形态直接冲突，须同步改写。

## 设计裁决与取舍

| # | 裁决 | 取舍说明 |
|---|------|---------|
| D1 | diff 载入 `docFile` 复用文件查看器（加 `kind: 'file'\|'diff'`），不开新页签 | 沿 0.17.0「方案名直达查看器」先例，查看器已是通用内容面板 |
| D2 | diff 渲染用引擎 `Code format='diff'`，不自写行分类纯函数 | 引擎原生增删着色；删除原设想的 parse.ts diff 解析函数 |
| D3 | diff 取 `git diff HEAD -- <path>`（staged+unstaged 合并口径），null 退 `git diff -- <path>`（unborn HEAD 兜底），仍 null 退 `loadDoc` 全文 | 两级兜底后行为退化为现状，不产生死视图 |
| D4 | untracked 走 `git diff --no-index -- /dev/null <path>`（全 + diff），失败退 `loadDoc` | Windows git 对 /dev/null 有内建处理（不确定点 U1，失败路径已兜底） |
| D5 | state=null（仅会话 touched）行点击保持 `loadDoc` 原文 | 无 git 基线无 diff 可言；untracked/conflict 有基线进 diff |
| D6 | 目录浏览区文件行点击保持原文不变 | 需求字面是「git 变更的文件列表」（改动清单区）；目录区浏览语义为主，如需扩展另行小改 |
| D7 | diff 视图不给节导航与「发给 Claude」；给「查看全文」「重读变更」 | 行号锚定草稿对 diff 无意义；极简 |
| D8 | 全文视图对有 git 变更的文件加「查看变更」按钮（反向切换） | 渲染时已可廉价重算；双向闭环避免退页签绕行 |
| D9 | diff 不截断 | 引擎单次绘制 100000 字符上限远超常规文件 diff；超长场景真机观察（U2） |
| D10 | 输入栏只在空态出现，常驻不加 | 需求字面；已打开时换文件走目录点击/`/deck doc` |
| D11 | 输入路径不做存在性预检 | `loadDoc` 读取失败既有错误视图即反馈 |
| D12 | Issues 数据经 `gh issue list --state open --limit 20 --json number,title,url,labels` 拉取，repo 由 gh 在 clone 内自动推断 | 插件通用（任何 GitHub 仓库面板即用），不硬编码 repo 名 |
| D13 | Issues 失败静默：gh 不在/非 GitHub 仓库/查询失败 → 区块整体不绘制 | 非目标目录零噪音；空列表显示「无 open issue」（对「通关后下一步」场景空态即信息） |
| D14 | Issues 轮询独立 60s（`GH_ISSUE_POLL_MS=60_000`）且仅面板可见时拉取（beatTimer 的 panes 判定模式），另随「刷新」按钮即时拉 | issue 变化慢，不随 2s 主轮询；无 gh 进程空转 |
| D15 | brainstorm 只改**回报形态**，不改执行流程（四问照答、五步照走、筛选照做、开场四问保留） | 质量机制全保留；用户痛点是收尾报告混淆，非流程 |
| D16 | brainstorm 统一原则写 SKILL.md 共享规则一处（权威），三手册引用 | 单一出处 |
| D17 | 深钻产出条目的单行核心论证保留（如「为什么有效」一句），多段推理链退场（落过程记录/按需展开） | evals 3/4/5 的「附对抗性检验/机制论证」质量断言以附注形态保留 |

## 路线图

| 批次 | 内容 | 级 | 依赖 |
|------|------|----|----|
| B1 | flow-deck：变更对比视图 + 地址输入栏 + GitHub Issues 区块（0.19.0） | T2 | — |
| B2 | brainstorm 回报收敛（2.3.2） | T1 | B1（执行顺序：共用根 CHANGELOG 串行写；工作区还有未提交的 work-skills 2.3.1 alphaXiv 改动，B2 提交前应先提交它） |

批次无技术依赖；B1 与 B2 文件集除根 CHANGELOG 外互斥。B1 三个功能合并的依据：同一文件集（register.tsx/types/测试/manifest）、同一测试基建（mount 用例同 mock 设施）、顺序实施——上下文连续信号；合并后 T 级就高（T2）。

---

## B1 详案：flow-deck 变更对比视图 + 地址输入栏 + GitHub Issues 区块

### 五要素 · 如何改

**契约扩展（先锚）**

- `plugins/flow-deck/types/index.d.ts:192`：`doc` 键类型 `{ path: string; text: string | null; error?: string }` 扩展为 `{ path: string; text: string | null; error?: string; kind?: 'file' | 'diff' }`。`kind` 可选、缺省 `'file'`，纯加法；docFile 为内存 atom 不入 `$.store`，无跨会话兼容问题。
- `plugins/flow-deck/types/index.d.ts` PluginState 新增键 `ghIssues`（加法）：`{ issues: { number: number; title: string; url: string; labels: string[] }[]; loaded: boolean; error: boolean }`——形态沿 `agents` 键（loaded/error 语义一致）。

**register.tsx 改动（按锚点顺序）**

1. `register.tsx:217`（loadDoc 之后）新增顶层函数 `loadDiff($, path, state: ChangeState)`：
   - `state === 'untracked'`：`runGit(['diff', '--no-index', '--', '/dev/null', path])`；
   - 其余（conflict/staged/unstaged）：`runGit(['diff', 'HEAD', '--', path])`，返回 null 时退 `runGit(['diff', '--', path])`；
   - 得到文本（含空串）→ `update($, docFile, () => ({ path, text, kind: 'diff' }))`；两级命令均 null → 兜底调 `loadDoc($, path)`（D3/D4）；
   - 装入前 `update($, docSection, () => 0)`、`update($, docMode, () => 'all')`，与 loadDoc 同口径。
2. `register.tsx:267` `openInDoc` 增可选参 `state?: ChangeState | null`：state 为四种 git 态之一时走 `loadDiff`，否则 `loadDoc`。既有调用点（:293 方案名、:298 兜底、:862 目录文件行、:1097 deck doc）不传参，行为不变（G8）。
3. `register.tsx:831` 改动清单行 `onPress` 改传 `row.state`：`void openInDoc($, row.path, row.state)`。
4. `register.tsx:661` `renderDocBody`：
   - 空态分支（:665-672，`doc === null`）：替换提示文案为输入栏 + 一行 dim 提示——
     `<Input key="doc-open" label="打开文件" placeholder="文件路径，如 docs/plan.md" submitLabel="打开" autoFocus onSubmit={...} />`；onSubmit 内 `value.trim()` 空串忽略，否则 `void openInDoc($, normalizePath(value, sessionCwd))`（D10/D11）。
   - 文档态（kind 缺省 'file'）：标题行下按钮区增「查看变更」`Button key="doc-view-diff"`——仅当重算的变更清单含 `doc.path` 且其 state 非 null 时绘制；onPress `void openInDoc($, doc.path, state)`（D8）。渲染头部补一次 `read($, gitStatus)` + `read($, touched)`，经 `collectChanges` 查 path（函数已从 parse.ts 导入）。
   - 新增 `doc.kind === 'diff'` 分支：`doc.text === null` 走既有错误视图；`doc.text === ''` 显示「无未提交变更（快照可能已过期）」+「查看全文」；否则标题「▍变更对比 · {path}」+ `<Code key="doc-diff" format="diff" source={doc.text} wrap="truncate-end" />` + 按钮行「查看全文」`key="doc-view-file"`（onPress `loadDoc`）与「重读变更」`key="doc-reload-diff" hotkey="r"`（onPress `loadDiff` 重跑，state 重算同 D8 口径）。节导航、Select、「发给 Claude」在 diff 分支不绘制（D7）。
5. **GitHub Issues 区块**（新增，集中三处）：
   - `parse.ts` 新增顶层纯函数 `parseGhIssues(stdout: string): { number: number; title: string; url: string; labels: string[] }[] | null`：`JSON.parse` 失败或非数组返回 null；逐条校验 number 为 number、title/url 为 string 才收；`labels` 取每项 `.name`（string 才收），缺 labels 视为空数组。
   - register.tsx：新 atom `ghIssues`（形态见契约）；`GH_ISSUE_POLL_MS = 60_000` 常量沿 :56 区；session.start 装配段（:1014 gitPoller 附近）新增 `refreshIssues = singleFlight(async () => {...})`：`$.process.run(['gh', 'issue', 'list', '--state', 'open', '--limit', '20', '--json', 'number,title,url,labels'], { timeoutMs: GIT_TIMEOUT_MS })`——exitCode≠0 或抛错 → `update($, ghIssues, () => ({ issues: [], loaded: true, error: true }))`；stdout 经 `parseGhIssues` 为 null → 同 error 态；成功 → `{ issues, loaded: true, error: false }`。timer `issuesTimer = $.clock.every(GH_ISSUE_POLL_MS, ...)`：panes 含 deck 才调 refreshIssues（beatTimer :1054 的判定模式）；`refreshAll`（:1042）加 `void refreshIssues?.()`；session.start 末尾 `void refreshIssues()` 首拉。
   - `renderFlowBody` 尾部（:655 子代理区之后、底部提示行之前）插入区块：仅 `loaded && !error` 绘制——标题 `{MARK.title}GitHub Issues · {n} open`；n=0 显示 `{MARK.done} 无 open issue`（TONE.ok）；否则每条一行 `<Link key={'issue-'+number} href={url}>`，children `<Text wrap="truncate-end">#{number} {title}</Text>` + 有标签时 `<Text dimColor> · {labels.join(' ')}</Text>`（D12/D13/D14）。

**测试（register.test.ts 新增，参照 :1578 `/doc 装载文档` 用例形态）**

- mock 要点：`on('process.run')` 按 `e.args` 分流——git `status`/`numstat` 照既有 fixture，`diff` 系列 args 返回 hunk 文本或 exitCode 128，`gh issue list` args 返回 JSON fixture 或 exitCode≠0；`on('fs.read')` 照既有 doc 用例。
- 用例清单：
  1. 改动清单点击 tracked 改动文件 → `$.ui.press({ key: 'file-open-hooks/a.ts', ... })` → `find({ type: 'Code' })` props.format === 'diff'、source 含 hunk 标记，标题含「变更对比」；
  2. 点击 untracked 行 → 断言 process.run 收到的 args 含 `--no-index`；
  3. 点击仅 touched（state null）行 → fs.read 被调、标题仍「文件查看器」（现状不变）；
  4. diff 命令返回空串 → 「无未提交变更」文案 + 「查看全文」按钮存在；
  5. diff 两级命令均 exitCode≠0 → fs.read 被调（退化为全文，D3）；
  6. 空态 `find({ type: 'Input' })` 存在 → `$.ui.input({ plugin: 'flow-deck', key: 'doc-open', requestId: 'deck', surface: 'terminal', kind: 'submit', value: 'docs/x.md' })` → fs.read 收到该路径；value 为空白时不触发 fs.read；
  7. 全文视图「查看变更」press → diff 视图；diff 视图「查看全文」press → 回全文（双向闭环）。
- L1（parse.test.ts）：`parseGhIssues` 四例——合法 JSON 全字段、坏 JSON 返回 null、缺 labels 的条目收为空数组、number 非 number 的条目被剔除。

**收尾（并入本批，主控 T0 直做）**

- 双 manifest `plugins/flow-deck/.claude-plugin/plugin.json` 与 `.codex-plugin/plugin.json`：0.18.1 → **0.19.0**；
- 根 CHANGELOG.md Unreleased 加 0.19.0 条目（三个功能合并一条，沿 0.11.0 多功能先例），并**顺带补录断档**：0.18.0/0.18.1（提交 fa773e5/51ac5c9）发布时未写 CHANGELOG，本次按其提交说明各补一条简要条目。

### 五要素 · 如何验证

- **L1**：`parseGhIssues` 四例（parse.test.ts）；diff/输入栏无新纯函数（D2），既有 L1 全量回归。
- **L2**：上节 7 个 mount 用例 + parseGhIssues L1，执行代理随锚点各自 TDD 红绿；Issues 区块的 mount 断言随用例 1 的 mock 设施顺带覆盖（gh fixture 注入后 `find({ text: /#12/ })`）。
- **L3 真机目检**（不可自动化，收口时主控逐项过）：diff 增删着色与 gutter 观感、Input 聚焦环与 submit 后字段残留行为（U3）、长 diff 滚动、untracked no-index 在本机 git 实测（U1）、Issues 区块在真仓库的显示与本机非 GitHub 目录的静默（U5）。
- **红线回归**：`claude plugin test plugins/flow-deck` 全量（含既有全部用例）+ `claude plugin validate plugins/flow-deck`。

### 五要素 · 验收标准（逐条 PASS/FAIL + 证据）

| # | 断言 | 证据 |
|---|------|------|
| G1 | staged/unstaged/conflict 文件在改动清单点击 → doc 页签出现「▍变更对比 · <path>」标题与 Code(format=diff) 元素 | 用例 1 输出 |
| G2 | untracked 点击 → process.run args 含 --no-index，装入 diff | 用例 2 |
| G3 | state=null 行点击 → 原文件全文，与改前一致 | 用例 3 |
| G4 | diff 空串 → 「无未提交变更」+「查看全文」 | 用例 4 |
| G5 | diff 命令两级失败 → 退化 loadDoc 全文 | 用例 5 |
| G6 | 全文视图有变更文件显示「查看变更」；press 进 diff；「查看全文」切回 | 用例 7 |
| G7 | 空态显示 Input；submit 有效路径装载；空白输入不动作 | 用例 6 |
| G8 | 方案名点击、`/deck doc`、目录文件行、节导航、e 草稿等既有路径行为不变 | 既有用例全绿 |
| G9 | gh 正常 → 工作面板尾部出现「GitHub Issues」区块，条目含 #号+标题+标签，Link href 为 issue url | mount 用例 + fixture |
| G10 | gh 失败/非 GitHub 仓库 → 区块不绘制，面板其余不受影响；空列表 → 「无 open issue」 | mount 用例 |
| G11 | `claude plugin test` 全绿 + `validate` 通过 | 测试与校验输出 |
| G12 | 双 manifest 0.19.0 一致 + CHANGELOG 条目落盘 | 文件 diff |

### 五要素 · 代码评审节点

- `loadDiff` 的两级兜底是否严格（HEAD diff 成功但返回空串 ≠ null，空串是合法结果非失败）；
- 「查看变更」按钮重算 `collectChanges` 的 path 匹配口径与改动清单一致（小写折叠）；
- Input onSubmit 闭包内异常是否吞（`$.ui.log` debug 模式，沿 loadDoc 先例）；
- diff 分支遗漏 `docMode`/`docSection` 重置导致的切换残留；
- Issues 的 `singleFlight` 与 timer 判定不产生并发 gh 进程堆积；error 态后下一轮询能自愈回正常态；
- 引擎静态扫描约束：`loadDiff`、refreshIssues 闭包体等收 `$` 的辅助必须是模块顶层 function（闭包内定义会被 validate 拒绝——MEMORY 已知坑）；
- 顺带修正 register.test.ts:1563-1569 的过时注释（「测试引擎无 process 设施」与文件内 20 余处既有 `on('process.run')` mock 矛盾），只改注释不动测试逻辑。

### 五要素 · 分级与验证流程

**T2**。依据：多文件（tsx、d.ts 契约、测试、双 manifest）；邻近 PluginState 契约（`doc`/`ghIssues` 键）但均为加法扩展不改存量语义；引入只读外部进程依赖（gh）但失败静默无状态副作用；有既有 mount 测试覆盖同渲染路径。执行代理实施 → 审计代理（证据包模式），流程按 implement-plan 查表。

---

## B2 详案：brainstorm 回报收敛

### 五要素 · 如何改

前置状态：工作区含未提交的 work-skills 2.3.1（deep-research alphaXiv）改动；B2 开工前由用户（或主控征得同意）先提交该工作，避免 manifest 版本叠放混乱。

1. **SKILL.md 共享规则节（:62-67）新增「最终回报」条目（权威陈述，D16）**：
   > **最终回报**：一次任务的收尾回复以最终产出开头并为主体（深钻=核心洞察，创意=设计卡，扩散=分支清单/交接概览）；执行过程（钻探计划、下钻链、透镜轮换、盘点/解构/筛选记录）默认不铺陈进主回复——压缩为一行摘要，用户说「看过程」再完整展开。
2. **mode-deepdive.md**：
   - `:103-122`「输出格式」改：💎 核心洞察置顶为主体（每条洞察 + 一行验证方式）；📋 钻探计划与 ⛏️ 下钻过程默认不进主回复（一句话摘要带过，完整版按需展开或落过程记录）；🔗 边界之外保留一句。
   - `:150-155`「注意事项」：`被证伪的路径要保留展示` 改为 `被证伪的路径保留在过程记录中（用户要看过程时完整呈现），主回复不铺陈`。
   - 场景入口五个「产出」行（:83-99）：机制论证/对抗性检验/外部验证方式**保留为每条产出一行附注**（D17），删除「附完整论证链」的铺陈暗示（如有）。
   - 开场硬规则（深度四问 :20-26）**不动**（D15：开工对齐机制非回报形态）。
3. **mode-creative.md**：
   - `:63-74` 第 5 步产出五要素卡改四件套：**关联路径 + 合理点合并为一行「成立依据」**；设计描述、意外点、试金石保留（试金石必填规则不变）。完整生效条件核对过程不进主回复。
   - `:123-135` 完整示例卡同步为新四件套形态。
4. **mode-diverge.md**：`:72-77` 日志使用策略「用户要求总结：给出地图概览」补「只给分支清单与状态概览，不铺每轮透镜轮换的生长过程」。
5. **evals.json 同步**（断言与新回报形态冲突处）：
   - eval 1 改写：「应产出本质问题界定、差异点、增量判定标准（洞察置顶为主体），钻探计划与下钻过程默认不铺陈主回复」；
   - eval 2/3/4/5 微调：「每个附**一句话**机制论证/对抗性检验/验证方式」；
   - eval 7 改写：五步流程**内部执行**不变，但「主回复以设计卡为主体，盘点/解构/筛选过程不铺陈」；
   - eval 6/8 不动（模式判别断言，与回报形态无关）。

### 五要素 · 如何验证

- **机械核对清单**（主控执行）：
  1. SKILL.md 新条目存在且为全库唯一权威陈述（三手册只有引用无复制）；
  2. 深钻/创意手册中不再有「四段全铺」「五要素全铺」的强制格式残留（grep 输出格式节）；
  3. 「被证伪路径」口径全文一致（保留记录、主回复不铺陈）；
  4. evals.json 八条断言逐一与新回报形态无冲突；
  5. 双 manifest 2.3.2 一致 + CHANGELOG 条目。
- **纸面推演**：对 evals 1/7 的 prompt 各写一段「改后理想回复结构」样例（洞察段→边界段／设计卡×n），确认与手册描述自洽。
- 无 L1/L2（纯文档）；无红线回归（不改代码与测试）。

### 五要素 · 验收标准

| # | 断言 | 证据 |
|---|------|------|
| G1 | SKILL.md「最终回报」条目存在且三手册无重复定义 | grep 输出 |
| G2 | 深钻输出格式节不再强制四段全铺；洞察置顶 | 文件节选 |
| G3 | 创意产出卡为四件套（成立依据一行合并）；示例卡同步 | 文件节选 |
| G4 | 扩散总结口径补全（只给分支概览） | 文件节选 |
| G5 | evals 1/2/7 改写、3/4/5 微调后逐条无冲突 | 逐条核对表 |
| G6 | 双 manifest 2.3.2 + CHANGELOG 条目 | 文件 diff |

### 五要素 · 代码评审节点

- 深钻「外部验证方式」与创意「试金石」的必填性未被回报收敛削弱（质量门仍在手册正文中）；
- 「开场宣告」「开场四问」等开工交互未被误删（D15 边界）；
- evals 3/4/5 微调后仍能区分「好产出」（附论证）与「坏产出」（裸清单），判别力未丢失。

### 五要素 · 分级与验证流程

**T1**。依据：纯技能文档行为约束（无代码、无契约邻近、无外部状态）；加法式修订 + 断言同步。执行代理实施 → 主控亲自机械验证收口（上清单），无审计代理。

---

## 不确定点（实施时消解）

| # | 不确定点 | 消解方式 | 兜底 |
|---|---------|---------|------|
| U1 | Windows git 对 `--no-index /dev/null` 字面量的处理 | 实施时本机实测一次 | 失败退 loadDoc（D4 已内建） |
| U2 | 超长 diff（>100k 字符）真机表现 | 真机目检 | 后续小改加 hunk 边界截断，本方案不做 |
| U3 | Input submit 后字段文本是否残留 | 真机目检 | 残留则下次渲染置 value=''（受控清空） |
| U4 | `$.ui.input` 测试驱动签名细节（text vs value 参数名） | 实施时以 tsc 与测试宿主为准 | 事件契约（kind+value）已确认，参数名以类型报错修正 |
| U5 | gh CLI 不在 PATH / 目录非 GitHub 仓库时 process.run 的失败形态（抛错 vs exit≠0） | 实施时以 mock 与真机覆盖两种形态 | 两形态都归入 error 静默路径（D13 已内建） |
