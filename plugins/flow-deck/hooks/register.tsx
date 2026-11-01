import { atom, read, update } from 'claude-code'
import type { EngineInterface, MatchedHook, PromptDecoration, Register } from 'claude-code'

import {
  DOC_SECTION_MAX_LINES,
  bannerPlan,
  collectChanges,
  depStatuses,
  gitSummaryParts,
  guardDecision,
  isGitQuiet,
  normalizePath,
  parseBatchScope,
  parseDepGraph,
  parseExecution,
  parseSections,
  phaseProgress,
  pipelineLinks,
  progressBar,
  scoreGauge,
  selectTaskView,
  sortEntries,
  sparkline,
  spinnerWord,
  toolMark,
  draftDecorations,
  humanDuration,
} from './parse'
import { createGitPoller, createPlanScanner, singleFlight } from './poll'
import { agentStatus, agentSummary, createAgentPoller } from './agents'
import { MARK, TONE } from './ui'
import type { ChangeState } from './parse'
import type {
  BatchScope,
  ExecutionReport,
  FlowTask,
  FsEntryLike,
  GitStatus,
  PlanReview,
} from '../types'

/** ui.render Pane 站点的事件入参（渲染辅助函数的 e 类型） */
type PaneArgs = Parameters<MatchedHook<'ui.render', { component: 'Pane' }>>[1]

const DECK_PANE_ID = 'deck'
const DECK_TITLE = 'Deck'
/** 本会话改动记录上限；超出挤出最旧 */
const TOUCHED_CAP = 50
const POLL_MS = 2000
const GIT_POLL_MS = 5000
const GIT_TIMEOUT_MS = 5000
const EXECUTION_STORE_KEY = 'lastExecution'
/** 执行上报停滞阈值：超过该时长未续报视为疑似停滞 */
const STALL_MS = 30 * 60_000

const plans = atom({ plugin: 'flow-deck', key: 'plans' } as const, [])
const notified = atom({ plugin: 'flow-deck', key: 'notified' } as const, [])
const baselined = atom({ plugin: 'flow-deck', key: 'baselined' } as const, false)
const execution = atom({ plugin: 'flow-deck', key: 'execution' } as const, null)
const currentTask = atom({ plugin: 'flow-deck', key: 'currentTask' } as const, null)
const batchScope = atom({ plugin: 'flow-deck', key: 'batchScope' } as const, null)
const guardWarned = atom({ plugin: 'flow-deck', key: 'guardWarned' } as const, [])
const progress = atom({ plugin: 'flow-deck', key: 'progress' } as const, {})
const deps = atom({ plugin: 'flow-deck', key: 'deps' } as const, null)
const gitStatus = atom({ plugin: 'flow-deck', key: 'git' } as const, null)
const agents = atom({ plugin: 'flow-deck', key: 'agents' } as const, { agents: [], loaded: false, error: false })
const lastRun = atom({ plugin: 'flow-deck', key: 'lastRun' } as const, null)
const stall = atom({ plugin: 'flow-deck', key: 'stall' } as const, null)
/** 文档浏览面板装载的文档：text 为 null 表示读取失败（error 记原因） */
const docFile = atom({ plugin: 'flow-deck', key: 'doc' } as const, null)
/** 文档浏览面板当前选中节在 parseSections 结果中的下标 */
const docSection = atom({ plugin: 'flow-deck', key: 'docSection' } as const, 0)
/** deck 面板当前页签；/deck 无参打开时保持上次所在页签 */
const activeTab = atom({ plugin: 'flow-deck', key: 'activeTab' } as const, 'flow')
/** 文件树面板当前浏览目录（相对会话工作目录）；null 表示根 */
const treeDir = atom({ plugin: 'flow-deck', key: 'treeDir' } as const, null)
/** 文件树面板最近一次目录列表；loaded 表示已取数（含空目录） */
const treeEntries = atom({ plugin: 'flow-deck', key: 'treeEntries' } as const, null)
/** 本会话 Edit/Write 改动记录（去重保序，最新在末尾） */
const touched = atom({ plugin: 'flow-deck', key: 'touched' } as const, [])

/** 上次写入 statusline 的文案；仅用于跳过重复写入（热加载后重算一次无妨） */
let lastStatus: string | undefined

/** 越界改动处理模式；register 时按 userConfig 覆盖（引擎要求钩子处于文件顶层，经此间接读取配置） */
let guardMode: 'warn' | 'deny' = 'warn'

/** 会话工作目录；tool.call 事件不带 cwd，自 session.start 缓存（先于首个工具调用触发） */
let sessionCwd = ''
let scanPlans: ReturnType<typeof createPlanScanner> | undefined
let refreshGit: (() => Promise<void>) | undefined
let refreshAgents: (() => Promise<void>) | undefined
/** 面板「刷新」按钮的全部数据重取；session.start 装配后可用 */
let refreshAll: (() => void) | undefined
let planTimer: ReturnType<EngineInterface['clock']['every']> | undefined
let gitTimer: ReturnType<EngineInterface['clock']['every']> | undefined

/** 自动侧边栏状态（官方 diff 面板范式）：本会话只自动试一次；用户手动开关过面板则不再打扰 */
let autoOpened = false
let manualDeck = false
/** 最近一次 AbovePrompt 绘制观测到的全屏布局状态（侧边栏可停靠的前提） */
let lastFullscreen = false
/** 自动侧边栏开关；register 时按 userConfig 覆盖 */
let autoOpenMode: 'on' | 'off' = 'on'

/** 越界拦截的 deny 文案 */
function guardDenyMessage(hit: GuardHit): string {
  return `${hit.tool} ${hit.path} 在批次 ${hit.batch} 边界外，已按 guardMode=deny 拦截。确需改动请先调用 flow_batch 更新边界。`
}

/** 越界放行的 warn 文案 */
function guardWarnMessage(hit: GuardHit): string {
  return `⚠ ${hit.tool} ${hit.path} 在批次 ${hit.batch} 边界外，已放行（guardMode=warn）`
}

/** 守卫动作：pass 放行；deny/warn 附工具名、越界路径、批次与去重键 */
export type GuardAction =
  | { action: 'pass' }
  | { action: 'deny' | 'warn'; tool: string; path: string; batch: string; key: string }

/** deny/warn 判定携带的越界信息（消息组装与去重共用） */
type GuardHit = Extract<GuardAction, { action: 'deny' | 'warn' }>

/** 读取边界并作出守卫判定；未声明边界或 cwd 未就绪时放行（fail-open） */
async function decideGuard($: EngineInterface, tool: string, file_path: unknown): Promise<GuardAction> {
  const scope: BatchScope | null = await read($, batchScope)
  const task = await read($, currentTask)
  if (scope === null || sessionCwd === '' || task?.kind !== 'implement' ||
      task.plan !== scope.plan || (task.batch !== undefined && task.batch !== scope.batch)) return { action: 'pass' }
  const decision = guardDecision(scope, tool, { file_path }, sessionCwd)
  if (decision.kind === 'pass') return { action: 'pass' }
  return { action: guardMode, tool, path: decision.path, batch: scope.batch, key: decision.key }
}

/** warn 越界提醒按归一化路径去重：同批同文件（含跨 Edit/Write）只提醒一次，批次重声明时清空 */
async function warnOnce($: EngineInterface, hit: GuardHit): Promise<void> {
  const seen = await read($, guardWarned)
  if (seen.includes(hit.key)) return
  await update($, guardWarned, prev => [...prev, hit.key].slice(-200))
  $.ui.log(guardWarnMessage(hit))
}

/** 一个方案的一行状态文案（statusline 与 toast 共用的口径） */
function summarize(plan: PlanReview): string {
  const latest = plan.rounds.at(-1) ?? null
  if (latest === null) return `「${plan.name}」评审 R${plan.round} 进行中 · 暂无评审结果`
  const mark = plan.passed ? ' · ✓ 已达标' : ''
  return `「${plan.name}」评审 R${plan.round}/5 · 最新 ${latest.score} 分${mark}`
}

/** 一条执行上报的摘要文案（横条与 toast 共用的口径） */
function describeExecution(report: ExecutionReport): string {
  const t = report.tLevel === undefined ? '' : ` · ${report.tLevel}`
  const tests =
    report.testsTotal === undefined ? '' : ` · 验证 ${report.testsPassed ?? 0}/${report.testsTotal}`
  return `${report.plan} · ${report.batch}${t} · ${report.phase}${tests}`
}

/** 读上次执行的跨会话记录；store 不可用或无记录时返回 null（best-effort） */
async function readLastExecution($: EngineInterface): Promise<ExecutionReport | null> {
  try {
    return parseExecution(await $.store.get(EXECUTION_STORE_KEY))
  } catch {
    return null
  }
}

async function readTaskView($: EngineInterface) {
  return selectTaskView(await read($, currentTask), {
    plans: await read($, plans),
    report: await read($, execution),
    scope: await read($, batchScope),
    graph: await read($, deps),
  })
}

/** 读取文档装入浏览面板；读失败时 text 置 null 记原因，面板内提示不崩 */
async function loadDoc($: EngineInterface, path: string): Promise<void> {
  let text: string | null = null
  let error: string | undefined
  try {
    text = await $.fs.read(path)
  } catch (cause) {
    error = String(cause)
  }
  await update($, docFile, () => ({ path, text, ...(error === undefined ? {} : { error }) }))
  await update($, docSection, () => 0)
}

/** 记录本会话 Edit/Write 改动路径（去重保序，cap 50）；守卫钩子放行分支调用，不阻塞链路 */
async function recordTouch($: EngineInterface, file_path: unknown): Promise<void> {
  if (typeof file_path !== 'string' || file_path === '' || sessionCwd === '') return
  const path = normalizePath(file_path, sessionCwd)
  const key = path.toLowerCase()
  try {
    await update($, touched, prev => {
      const rest = prev.filter(one => one.path.toLowerCase() !== key)
      return [...rest, { path, at: Date.now() }].slice(-TOUCHED_CAP)
    })
  } catch (error) {
    $.ui.log(`flow-deck 改动记录失败：${String(error)}`, { to: 'debug' })
  }
  // 自动侧边栏（官方 diff 面板范式）：agent 首次编辑时，若布局可停靠、用户未手动
  // 开关过面板且本会话未试过，则不抢键盘焦点地打开一次
  if (autoOpenMode === 'on' && !autoOpened && !manualDeck && lastFullscreen) {
    autoOpened = true
    try {
      const isOpen = (await $.ui.panes()).some(pane => pane.id === DECK_PANE_ID)
      if (!isOpen) {
        await $.ui.open({ id: DECK_PANE_ID, title: DECK_TITLE, focus: false })
        void refreshAgents?.().catch(() => {})
      }
    } catch (error) {
      $.ui.log(`flow-deck 自动侧边栏失败：${String(error)}`, { to: 'debug' })
    }
  }
}

/** 装载文件树目录列表；dir 为 null 表示会话工作目录根。读失败置空（面板内提示可重读）。 */
async function loadTree($: EngineInterface, dir: string | null): Promise<void> {
  let entries: FsEntryLike[] = []
  try {
    const listed = dir === null ? await $.fs.list() : await $.fs.list(dir)
    entries = listed.map(one => ({ name: one.name, kind: one.kind, isLink: one.isLink }))
  } catch (error) {
    $.ui.log(`flow-deck 目录读取失败：${String(error)}`, { to: 'debug' })
  }
  await update($, treeDir, () => dir)
  await update($, treeEntries, () => ({ entries, loaded: true }))
}

/** 心跳停滞检测：实施中且未收口的上报超过 STALL_MS 未续报时记分钟数；状态变化才写，避免无谓重绘 */
async function refreshStall($: EngineInterface): Promise<void> {
  const task = await read($, currentTask)
  const report = await read($, execution)
  const age = report === null || report.phase === '收口' ? 0 : Date.now() - report.updatedAt
  const minutes = task?.kind === 'implement' && age >= STALL_MS ? Math.floor(age / 60_000) : null
  if ((await read($, stall)) === minutes) return
  await update($, stall, () => minutes)
}

/** 跑一个 git 子命令；非零退出（含非 git 仓库的 128）或超时返回 null */
async function runGit($: EngineInterface, args: readonly string[]): Promise<string | null> {
  try {
    const result = await $.process.run(['git', ...args], { timeoutMs: GIT_TIMEOUT_MS })
    if (result.exitCode !== 0) return null
    return result.stdout
  } catch {
    return null
  }
}

/** 一个 git 文件行的显示文案；rename 显示 old → new */
function gitFileLabel(file: { path: string; oldPath?: string }): string {
  return file.oldPath === undefined ? file.path : `${file.oldPath} → ${file.path}`
}

/** 一轮扫描：更新面板数据、对新落盘轮次发 toast、刷新 statusline */
async function poll($: EngineInterface): Promise<void> {
  const found = await scanPlans!(Date.now())
  const previous = await read($, plans)
  const changed = JSON.stringify(previous) !== JSON.stringify(found)
  if (changed) await update($, plans, () => found)

  const seen = await read($, notified)
  const fresh = found.flatMap(plan =>
    plan.rounds
      .filter(round => !seen.includes(`${plan.dir}#R${round.round}`))
      .map(round => ({ plan, round })),
  )
  if (fresh.length > 0) {
    const keys = fresh.map(one => `${one.plan.dir}#R${one.round.round}`)
    await update($, notified, prev => [...prev, ...keys].slice(-200))
  }
  // 首轮扫描只做基线（存量轮次静默入账），避免新会话把历史评审全部重播
  const first = !(await read($, baselined))
  const task = await read($, currentTask)
  const lastFresh = fresh.filter(one => task?.kind === 'iterate' && one.plan.name === task.plan).at(-1) ?? null
  if (first) {
    await update($, baselined, () => true)
  } else if (lastFresh !== null) {
    const { plan, round } = lastFresh
    const mark = plan.passed ? ' · ✓ 已达标' : ''
    const counts =
      round.p0 === 0 && round.p1 === 0 && round.p2 === 0
        ? '无问题'
        : `P0×${round.p0} P1×${round.p1} P2×${round.p2}`
    $.ui.toast(`「${plan.name}」R${round.round} 评审完成：${round.score} 分 · ${counts}${mark}`)
  }

  // 历史评审仅作数据来源，不据此认定当前正在迭代。
  const lastPlan = bannerPlan(task?.kind === 'iterate' ? found.filter(plan => plan.name === task.plan) : [])
  const summary = lastPlan === null ? undefined : summarize(lastPlan)
  if (changed) $.ui.log(`flow-deck 扫描完成：${found.length} 个方案`, { to: 'debug' })
  if (summary !== lastStatus) {
    lastStatus = summary
    $.ui.status(summary)
  }
}

const renderFlowBody = async ($: EngineInterface, e: PaneArgs) => {
  const { Box, Text, Button } = $.ui.resolve(e)
  const task = await read($, currentTask)
  const { plans: list, graph, report, scope } = await readTaskView($)
  const progressMap: Record<string, string> = await read($, progress)
  const snapshot = await read($, agents)
  const crumbs = await read($, lastRun)
  const stallMinutes = await read($, stall)
  const wide = e.props.bodyColumns >= 44
  const nodes = graph === null ? [] : depStatuses(graph, progressMap)
  const links = pipelineLinks(nodes)
  const done = nodes.filter(node => node.status === 'done').length
  const passing = list.filter(plan => plan.passed)
  // 无事不扰：达标方案折叠为一行，未达标排前并逐个展示
  const activePlans = [...list].sort((a, b) => Number(a.passed) - Number(b.passed)).filter(plan => !plan.passed)
  const names = new Map(snapshot.agents.map(agent => [agent.id, agent.name || agent.description || agent.id]))

  const agentsSection = (
    <Box flexDirection="column" gap={1}>
      <Box>
        <Text bold wrap="truncate-end">{MARK.title}子代理{snapshot.loaded ? ` · ${agentSummary(snapshot.agents)}` : ''}</Text>
        <Button key="flow-refresh" hotkey="r" plain onPress={() => refreshAll?.()}>刷新</Button>
      </Box>
      {snapshot.error && <Text color={TONE.warn} wrap="truncate-end">刷新失败，自动重试；{snapshot.loaded ? '以下为上次快照，状态可能已过期。' : '暂未取得子代理状态。'}</Text>}
      {!snapshot.loaded && !snapshot.error && <Text dimColor>正在读取当前会话的子代理…</Text>}
      {snapshot.loaded && snapshot.agents.length === 0 && <Text dimColor>当前会话暂无子代理。</Text>}
      {snapshot.agents.map(agent => {
        const status = agentStatus(agent.status)
        return (
          <Box key={agent.id} flexDirection="column" borderStyle={wide ? 'round' : undefined} borderColor={status.color} borderDimColor paddingX={wide ? 1 : 0} hover={{ borderDimColor: false }}>
            <Box>
              <Text bold color={status.color} wrap="truncate-end">{status.mark} {status.label} · {agent.name || agent.description || agent.id}</Text>
              <Button key={`agent-view-${agent.id}`} plain dimColor onPress={() => {
                void $.ui.view({ agentId: agent.id }).then(result => {
                  if ('deny' in result && result.deny !== undefined) $.ui.toast(`无法查看子代理：${result.deny}`)
                }).catch(error => {
                  $.ui.log(`flow-deck 查看子代理失败：${String(error)}`, { to: 'debug' })
                })
              }}>查看</Button>
            </Box>
            <Text dimColor wrap="truncate-middle">{agent.type} · {agent.id}</Text>
            {agent.description !== '' && <Text wrap="truncate-end">任务：{agent.description}</Text>}
            {agent.parentId !== undefined && <Text dimColor wrap="truncate-middle">↳ 父代理：{names.get(agent.parentId) ?? agent.parentId}</Text>}
            {agent.spawnedBy !== undefined && <Text dimColor wrap="truncate-end">来源插件：{agent.spawnedBy}</Text>}
          </Box>
        )
      })}
    </Box>
  )

  if (task === null) {
    return (
      <Box flexDirection="column" gap={1}>
        <Box flexDirection="column">
          <Text>当前无方案迭代或实施任务。</Text>
          <Text dimColor>运行 plan-iterate 开始方案迭代，或 implement-plan 开始实施。</Text>
          {crumbs !== null && <Text dimColor wrap="truncate-end">上次执行：{describeExecution(crumbs)}</Text>}
        </Box>
        {agentsSection}
        <Text dimColor wrap="truncate-end">/deck 关闭 · 面板内按 r 刷新</Text>
      </Box>
    )
  }

  const phase = report === null ? null : phaseProgress(report.phase)
  return (
    <Box flexDirection="column" gap={1}>
      <Box flexDirection="column">
        <Text bold color={TONE.accent}>{MARK.title}工作流 · {task.kind === 'iterate' ? '方案迭代' : '方案实施'} · {task.plan}</Text>
        {task.kind === 'iterate' && <Text dimColor wrap="truncate-end">评审 {list.length} · 待达标 {list.length - passing.length} · 已达标 {passing.length}</Text>}
        {task.kind === 'implement' && graph !== null && <Text dimColor wrap="truncate-end">批次 {done}/{nodes.length} 收口</Text>}
      </Box>
      {task.kind === 'iterate' && list.length === 0 && <Text dimColor>方案迭代进行中，等待评审结果落盘。</Text>}
      {task.kind === 'implement' && report === null && <Text dimColor>实施任务已开始，等待阶段进度上报。</Text>}
      {report !== null && phase !== null && (
        <Box flexDirection="column" borderStyle={wide ? 'round' : undefined} borderColor={TONE.accent} paddingX={wide ? 1 : 0}>
          <Text bold color={TONE.accent} wrap="truncate-end">{MARK.run} 当前执行 · {report.plan}</Text>
          <Text wrap="truncate-end">
            {report.batch}
            {report.tLevel !== undefined && <Text backgroundColor={TONE.accent} color="inverseText"> {report.tLevel} </Text>}
            {' '}· {report.phase}
          </Text>
          {phase.total > 0 && (
            <Text wrap="truncate-end">
              <Text color={TONE.ok}>{progressBar(phase.index, phase.total)}</Text>
              <Text> </Text>
              <Text color={phase.index >= phase.total ? TONE.ok : TONE.warn} bold>{phase.current} · {phase.index}/{phase.total}</Text>
            </Text>
          )}
          {phase.total === 0 && <Text dimColor wrap="truncate-end">{phase.current}</Text>}
          {stallMinutes !== null && <Text color={TONE.warn} wrap="truncate-end">{MARK.alert} 疑似停滞 · 距上次上报 {stallMinutes} 分钟</Text>}
          {report.testsTotal !== undefined && (
            <Text color={report.testsTotal > 0 && report.testsPassed === report.testsTotal ? TONE.ok : TONE.warn} wrap="truncate-end">
              验证 {progressBar(report.testsPassed ?? 0, report.testsTotal)} {report.testsPassed ?? 0}/{report.testsTotal}
            </Text>
          )}
          {report.evidenceDir !== undefined && <Text dimColor wrap="truncate-middle">证据 {report.evidenceDir}</Text>}
        </Box>
      )}
      {scope !== null && <Text dimColor wrap="truncate-end">{MARK.info} 边界 · {scope.plan} / {scope.batch} · {scope.files.length} 文件 · {guardMode}</Text>}
      {activePlans.length > 0 && (
        <Text bold>{MARK.title}plan-iterate 评审 · 8.5 分且无 P0/P1 达标</Text>
      )}
      {activePlans.map(plan => {
        const latest = plan.rounds.at(-1) ?? null
        const previous = plan.rounds.at(-2) ?? null
        const delta = latest === null || previous === null ? null : latest.score - previous.score
        const tone = plan.passed ? TONE.ok : latest !== null && latest.p0 > 0 ? TONE.bad : TONE.warn
        return (
          <Box key={plan.dir} flexDirection="column" borderStyle={wide ? 'round' : undefined} borderColor={tone} borderDimColor paddingX={wide ? 1 : 0} hover={{ borderDimColor: false }}>
            <Text bold color={tone} wrap="truncate-end">{plan.passed ? MARK.done : MARK.run} {plan.name}</Text>
            <Text wrap="truncate-end">
              <Text color={tone}>{latest === null ? '等待结果' : `${latest.score.toFixed(1)} / 10`}</Text>
              <Text dimColor> · R{plan.round}/5 · {plan.passed ? '已达标' : '待达标'}</Text>
            </Text>
            {latest !== null && (
              <Text wrap="truncate-end">
                <Text color={tone}>{scoreGauge(latest.score)}</Text>
                <Text dimColor> {sparkline(plan.rounds.slice(-12).map(round => round.score))}</Text>
                {delta !== null && <Text color={delta > 0 ? TONE.ok : delta < 0 ? TONE.bad : undefined}> {delta > 0 ? '↑' : delta < 0 ? '↓' : '='}{Math.abs(delta).toFixed(1)}</Text>}
              </Text>
            )}
            <Text wrap="truncate-end">
              {latest === null && <Text dimColor>暂无已落盘的评审结果</Text>}
              {latest !== null && latest.p0 > 0 && <Text color={TONE.bad}>P0×{latest.p0} </Text>}
              {latest !== null && latest.p1 > 0 && <Text color={TONE.warn}>P1×{latest.p1} </Text>}
              {latest !== null && latest.p2 > 0 && <Text dimColor>P2×{latest.p2}</Text>}
              {latest !== null && latest.p0 === 0 && latest.p1 === 0 && latest.p2 === 0 && (
                <Text dimColor>无问题</Text>
              )}
            </Text>
          </Box>
        )
      })}
      {passing.length > 0 && <Text color={TONE.ok} wrap="truncate-end">{MARK.done} 已达标 {passing.length} 个方案（已折叠）</Text>}
      {graph !== null && (
        <Box flexDirection="column" gap={1}>
          <Text bold wrap="truncate-end">{MARK.title}执行 DAG（{graph.plan}）</Text>
          <Text color={TONE.accent} wrap="truncate-end">
            {nodes.flatMap((node, index) => {
              const glyph = (
                <Text key={node.batch}
                  color={node.status === 'done' ? TONE.ok : node.status === 'active' ? TONE.warn : undefined}
                  dimColor={node.status === 'pending'}>
                  {node.status === 'done' ? MARK.nodeDone : node.status === 'active' ? MARK.nodeRun : MARK.nodeWait}
                </Text>
              )
              if (index === nodes.length - 1) return [glyph]
              const linkStatus = links[index]
              const link = (
                <Text key={`${node.batch}-link`}
                  color={linkStatus === 'done' ? TONE.ok : linkStatus === 'active' ? TONE.warn : undefined}
                  dimColor={linkStatus === 'pending'}>
                  {linkStatus === 'pending' ? '╌' : '━'}
                </Text>
              )
              return [glyph, link]
            })}
            {' '}{done}/{nodes.length} 收口 · {nodes.filter(node => node.status === 'active').length} 进行中
          </Text>
          {nodes.map((node, index) => (
            <Box key={node.batch} flexDirection="column">
              <Text dimColor={node.status === 'pending'} color={node.status === 'done' ? TONE.ok : node.status === 'active' ? TONE.warn : undefined} wrap="truncate-end">
                {node.status === 'done' ? `${MARK.done} ` : node.status === 'active' ? `${MARK.run} ` : `${MARK.idle} `}{node.batch}
              </Text>
              <Text dimColor wrap="truncate-end">{index === nodes.length - 1 ? '└' : '│'} {progressMap[`${graph.plan}#${node.batch}`] ?? '待执行'}{node.dependsOn.length > 0 ? ` · ← ${node.dependsOn.join('、')}` : ' · 起点'}</Text>
            </Box>
          ))}
        </Box>
      )}
      {agentsSection}
      <Text dimColor wrap="truncate-end">/deck 关闭 · 面板内按 r 刷新</Text>
    </Box>
  )
}

const renderDocBody = async ($: EngineInterface, e: PaneArgs) => {
  const { Box, Text, Button, Select, Markdown } = $.ui.resolve(e)
  const doc = await read($, docFile)
  const wide = e.props.bodyColumns >= 44
  if (doc === null) {
    return (
      <Box flexDirection="column">
        <Text>未打开文档。</Text>
        <Text dimColor>用法：/doc &lt;相对路径&gt; 打开要浏览的文档。</Text>
      </Box>
    )
  }

  const sendEdit = async () => {
    const wanted = await read($, docSection)
    const sections = doc.text === null ? [] : parseSections(doc.text)
    const current = sections[Math.min(Math.max(wanted, 0), sections.length - 1)]
    if (current === undefined) {
      $.ui.toast('文档为空，没有可发送的节。')
      return
    }
    const draft = `请修改 ${doc.path} 的「${current.title}」一节（第 ${current.start}–${current.end} 行）：`
    try {
      const box = await $.prompt.read()
      await $.prompt.fill({ text: draft, mode: box.text.trim() === '' ? 'replace' : 'append' })
    } catch (error) {
      $.ui.log(`flow-deck 修改请求填入失败：${String(error)}`, { to: 'debug' })
    }
  }
  const reload = () => {
    void loadDoc($, doc.path).catch(error => {
      $.ui.log(`flow-deck 文档重读失败：${String(error)}`, { to: 'debug' })
    })
  }
  if (doc.text === null) {
    return (
      <Box flexDirection="column" gap={1}>
        <Text bold color={TONE.bad} wrap="truncate-end">{MARK.title}文档 · {doc.path}</Text>
        <Text color={TONE.bad} wrap="truncate-end">读取失败：{doc.error ?? '未知原因'}</Text>
        <Box>
          <Button key="doc-reload" hotkey="r" plain onPress={reload}>重读</Button>
        </Box>
      </Box>
    )
  }
  const sections = parseSections(doc.text)
  if (sections.length === 0) {
    return (
      <Box flexDirection="column" gap={1}>
        <Text bold color={TONE.accent} wrap="truncate-end">{MARK.title}文档 · {doc.path} · 空文档</Text>
        <Text dimColor>文档没有内容：/doc &lt;另一路径&gt; 换一篇，或按 r 重读。</Text>
        <Box>
          <Button key="doc-reload" hotkey="r" plain onPress={reload}>重读</Button>
        </Box>
      </Box>
    )
  }
  const wanted = await read($, docSection)
  const index = Math.min(Math.max(wanted, 0), sections.length - 1)
  const current = sections[index]
  const allLines = doc.text.split('\n')
  const body = allLines.slice(current.start - 1, current.end)
  const truncated = body.length > DOC_SECTION_MAX_LINES
  const shown = truncated ? body.slice(0, DOC_SECTION_MAX_LINES) : body
  return (
    <Box flexDirection="column" gap={1}>
      <Text bold color={TONE.accent} wrap="truncate-end">{MARK.title}文档 · {doc.path} · {sections.length} 节 · {allLines.length} 行</Text>
      <Select
        key="doc-section"
        label="节"
        options={sections.map((section, i) => ({ value: String(i), text: `${section.title}` }))}
        value={String(index)}
        onSelect={value => { void update($, docSection, () => Number(value)) }}
      />
      <Box flexDirection="column" borderStyle={wide ? 'round' : undefined} paddingX={wide ? 1 : 0}>
        <Text bold wrap="truncate-end">
          {MARK.title}{current.title} · 第 {current.start}–{current.end} 行
          {truncated ? ` · 截断显示前 ${DOC_SECTION_MAX_LINES} 行` : ''}
        </Text>
        <Markdown key="doc-body" text={shown.join('\n')} />
      </Box>
      <Box>
        <Button key="doc-send" hotkey="e" variant="primary" onPress={() => { void sendEdit() }}>发给 Claude</Button>
        <Button key="doc-reload" hotkey="r" plain onPress={reload}>重读</Button>
      </Box>
      <Text dimColor wrap="truncate-end">/deck doc &lt;路径&gt; 换一篇 · e 把修改请求填入输入框（补意图后回车）</Text>
    </Box>
  )
}

const renderFilesBody = async ($: EngineInterface, e: PaneArgs) => {
  const { Box, Text, Button, Select } = $.ui.resolve(e)
  const status: GitStatus | null = await read($, gitStatus)
  const touchedList = await read($, touched)
  const scope = await read($, batchScope)
  const dir = await read($, treeDir)
  const tree = await read($, treeEntries)
  const scopeSet = new Set((scope?.files ?? []).map(file => normalizePath(file, sessionCwd).toLowerCase()))
  const rows = collectChanges(status, touchedList)
  const STATE_MARK: Record<ChangeState, { label: string; color?: string; dim?: boolean }> = {
    conflict: { label: '冲突', color: TONE.bad },
    staged: { label: '暂存', color: TONE.ok },
    unstaged: { label: '改', color: TONE.warn },
    untracked: { label: '新', dim: true },
  }
  const gitMark = (path: string): { label: string; color?: string } | null => {
    if (status === null) return null
    if (status.conflicts.some(file => file.path === path)) return { label: '冲突', color: TONE.bad }
    if (status.staged.some(file => file.path === path)) return { label: '暂存', color: TONE.ok }
    if (status.unstaged.some(file => file.path === path)) return { label: '改', color: TONE.warn }
    if (status.untracked.some(file => file.path === path)) return { label: '新' }
    return null
  }
  return (
    <Box flexDirection="column" gap={1}>
      <Text bold color={TONE.accent} wrap="truncate-end">{MARK.title}文件 · {dir === null ? '工作目录' : dir}</Text>
      {status === null && <Text dimColor>当前目录不是 git 仓库，或状态尚未取到；自动重试中。</Text>}
      {status !== null && (
        <Box flexDirection="column">
          <Text wrap="truncate-middle">
            <Text bold>{status.branch}</Text>
            {status.upstream !== null && <Text dimColor> → {status.upstream}</Text>}
            {status.ahead > 0 && <Text color={TONE.ok}> ↑{status.ahead}</Text>}
            {status.behind > 0 && <Text color={TONE.warn}> ↓{status.behind}</Text>}
            {(status.added > 0 || status.removed > 0) && (
              <Text>
                {status.added > 0 && <Text color={TONE.added}> +{status.added}</Text>}
                {status.removed > 0 && <Text color={TONE.removed}> −{status.removed}</Text>}
              </Text>
            )}
          </Text>
          {isGitQuiet(status) && <Text color={TONE.ok}>{MARK.done} 工作区干净{status.upstream === null ? ' · 未设置上游' : '，与上游同步'}</Text>}
        </Box>
      )}
      <Box flexDirection="column">
        <Text bold wrap="truncate-end">{MARK.title}改动{rows.length > 0 ? ` · ${rows.length}` : ''}</Text>
        {rows.length === 0 && <Text dimColor>仓库无改动，本会话也没有文件记录。</Text>}
        {rows.map(row => {
          const mark = row.state === null ? null : STATE_MARK[row.state]
          return (
            <Text key={row.path} wrap="truncate-middle">
              <Text color={row.touched ? TONE.accent : undefined} dimColor={!row.touched}>{row.touched ? MARK.run : MARK.idle}</Text>
              <Text> {row.path}</Text>
              {mark !== null && <Text color={mark.color} dimColor={mark.dim === true}> · {mark.label}</Text>}
              {scopeSet.has(row.path.toLowerCase()) && <Text color={TONE.accent}> {MARK.pin} 本批</Text>}
            </Text>
          )
        })}
      </Box>
      <Box flexDirection="column">
        <Text bold wrap="truncate-end">{MARK.title}目录</Text>
        {!tree?.loaded && <Text dimColor>正在读取目录…</Text>}
        {tree?.loaded && (
          <Select
            key="tree-dir"
            label="进入子目录"
            options={[
              { value: '', text: dir === null ? '工作目录（当前）' : '… 工作目录' },
              ...sortEntries(tree.entries).filter(one => one.kind === 'dir').map(one => ({
                value: dir === null ? one.name : `${dir}/${one.name}`,
                text: `${one.name}/`,
              })),
            ]}
            value=""
            onSelect={value => { void loadTree($, value === '' ? null : value) }}
          />
        )}
        {tree?.loaded && tree.entries.length === 0 && <Text dimColor>（空目录）读取失败或无内容，按 r 重读。</Text>}
        {tree?.loaded && sortEntries(tree.entries).map(entry => {
          const path = dir === null ? entry.name : `${dir}/${entry.name}`
          const mark = entry.kind === 'dir' ? null : gitMark(path)
          return (
            <Text key={entry.name} wrap="truncate-middle">
              {entry.kind === 'dir' ? `${entry.name}/` : entry.name}
              {mark !== null && <Text color={mark.color} dimColor={mark.color === undefined}> · {mark.label}</Text>}
              {entry.kind !== 'dir' && scopeSet.has(path.toLowerCase()) && <Text color={TONE.accent}> {MARK.pin} 本批</Text>}
            </Text>
          )
        })}
      </Box>
      <Box>
        <Button key="tree-reload" hotkey="r" plain onPress={() => { void loadTree($, dir) }}>重读</Button>
      </Box>
      <Text dimColor wrap="truncate-end">/deck 关闭 · ● 本会话改动 ○ 其他改动 · r 重读目录</Text>
    </Box>
  )
}

export const register: Register = (on, options) => {
  guardMode = options.guardMode === 'deny' ? 'deny' : 'warn'
  autoOpenMode = options.autoOpen === 'off' ? 'off' : 'on'

  on('session.start', async ($, e, next) => {
    sessionCwd = e.cwd
    lastStatus = undefined
    await update($, currentTask, () => null)
    await update($, execution, () => null)
    await update($, batchScope, () => null)
    await update($, plans, () => [])
    await update($, notified, () => [])
    await update($, guardWarned, () => [])
    await update($, baselined, () => false)
    await update($, progress, () => ({}))
    await update($, deps, () => null)
    await update($, agents, () => ({ agents: [], loaded: false, error: false }))
    await update($, stall, () => null)
    await update($, docFile, () => null)
    await update($, docSection, () => 0)
    await update($, treeDir, () => null)
    await update($, treeEntries, () => null)
    await update($, touched, () => [])
    autoOpened = false
    manualDeck = false
    planTimer?.cancel()
    gitTimer?.cancel()
    scanPlans = createPlanScanner({
      list: path => path === undefined ? $.fs.list() : $.fs.list(path),
      read: path => $.fs.read(path),
    })
    await $.command.register({ name: 'deck', description: '开关 flow-deck 面板：/deck 直开，/deck flow|tree|doc [路径] 直达页签' })
    await $.tool.register({
      name: 'flow_task',
      description: '声明当前工作流任务：iterate 方案迭代，implement 方案实施，idle 结束、暂停或取消。历史评审和路线图不会自动激活面板。',
      inputSchema: {
        type: 'object',
        properties: {
          kind: { type: 'string', enum: ['iterate', 'implement', 'idle'] },
          plan: { type: 'string', description: '方案名；iterate 使用 .plan-iterate 下的目录名，idle 时可省略' },
          batch: { type: 'string', description: '实施批次（可选）' },
        },
        required: ['kind'],
      },
    })
    await $.tool.register({
      name: 'flow_report',
      description:
        'implement-plan 执行进度上报。每完成一个阶段（开工/派单/执行/验证/收口）调用一次；' +
        '进度会实时显示在输入框上方横条，并跨会话保留以便续接。',
      inputSchema: {
        type: 'object',
        properties: {
          plan: { type: 'string', description: '方案名（方案文档文件名去扩展名）' },
          batch: { type: 'string', description: '批次标识，如 B2' },
          phase: { type: 'string', description: '当前阶段：开工 | 派单 | 执行 | 验证 | 收口' },
          tLevel: { type: 'string', description: '风险定级：T0 | T1 | T2 | T3' },
          testsPassed: { type: 'number', description: '已通过的定向测试数' },
          testsTotal: { type: 'number', description: '定向测试总数' },
          evidenceDir: { type: 'string', description: '证据目录路径' },
        },
        required: ['plan', 'batch', 'phase'],
      },
    })
    await $.tool.register({
      name: 'flow_batch',
      description:
        'implement-plan 批次边界声明。每批开工时调用一次，声明本批允许改动的文件集合' +
        '（来自委派单的改动锚点）；此后本批对边界外文件的编辑会被守卫拦截或提醒。',
      inputSchema: {
        type: 'object',
        properties: {
          plan: { type: 'string', description: '方案名（方案文档文件名去扩展名）' },
          batch: { type: 'string', description: '批次标识，如 B2' },
          files: {
            type: 'array',
            items: { type: 'string' },
            description: '本批允许改动的文件路径（相对会话工作目录或绝对路径）',
          },
        },
        required: ['plan', 'batch', 'files'],
      },
    })
    await $.tool.register({
      name: 'flow_deps',
      description:
        'optimization-plan 波次依赖声明。路线图定稿时调用一次，把波次依赖图声明为机器可读' +
        '清单；仪表盘面板将按推荐执行顺序绘制执行进度图。',
      inputSchema: {
        type: 'object',
        properties: {
          plan: { type: 'string', description: '方案名（方案文档文件名去扩展名）' },
          batches: {
            type: 'array',
            description: '批次依赖节点，按推荐执行顺序排列',
            items: {
              type: 'object',
              properties: {
                batch: { type: 'string', description: '批次标识，如 B2' },
                dependsOn: {
                  type: 'array',
                  items: { type: 'string' },
                  description: '依赖的前置批次标识列表',
                },
              },
              required: ['batch'],
            },
          },
        },
        required: ['plan', 'batches'],
      },
    })
    const last = await readLastExecution($)
    await update($, lastRun, () => last)
    if (last !== null) $.ui.toast(`上次执行：${describeExecution(last)}`)
    const refreshPlans = singleFlight(async () => {
      try {
        await poll($)
      } catch (error) {
        $.ui.log(String(error), { to: 'debug' })
      }
    })
    const gitPoller = createGitPoller(args => runGit($, args), async status => {
      await update($, gitStatus, () => status)
    })
    const tickGit = singleFlight(async () => {
      try {
        await gitPoller(Date.now())
      } catch (error) {
        $.ui.log(String(error), { to: 'debug' })
      }
    })
    refreshGit = singleFlight(async () => {
      await gitPoller(Date.now(), true)
    })
    const refreshAgentList = createAgentPoller(() => $.agent.list(), async snapshot => {
      await update($, agents, () => snapshot)
    })
    refreshAgents = refreshAgentList
    const refreshAgentPane = async () => {
      try {
        if ((await $.ui.panes()).some(pane => pane.id === DECK_PANE_ID)) await refreshAgentList()
      } catch (error) {
        $.ui.log(`flow-deck 子代理刷新失败：${String(error)}`, { to: 'debug' })
      }
    }
    void refreshPlans()
    void tickGit()
    refreshAll = () => {
      void refreshPlans()
      void refreshGit?.()
      void refreshAgents?.()
    }
    planTimer = $.clock.every(POLL_MS, async () => {
      await Promise.all([refreshPlans(), refreshAgentPane(), refreshStall($)])
    })
    gitTimer = $.clock.every(GIT_POLL_MS, tickGit)
    return next(e)
  })

  on('command.run', { command: 'deck' }, async ($, e) => {
    const arg = e.args.trim()
    const isOpen = (await $.ui.panes()).some(pane => pane.id === DECK_PANE_ID)
    if (arg === '') {
      if (isOpen) {
        await $.ui.close({ id: DECK_PANE_ID })
        manualDeck = true
        return { text: '已关闭 flow-deck 面板。' }
      }
      manualDeck = true
      await $.ui.open({ id: DECK_PANE_ID, title: DECK_TITLE, focus: true })
      void refreshAgents?.().catch(error => {
        $.ui.log(`flow-deck 子代理刷新失败：${String(error)}`, { to: 'debug' })
      })
      return { text: '已打开面板（1 工作流 · 2 文件 · 3 文档，Esc 回输入框）。' }
    }
    if (arg === 'flow' || arg === 'tree') {
      await update($, activeTab, () => arg === 'tree' ? 'files' : 'flow')
      if (arg === 'tree') await loadTree($, null)
      manualDeck = true
      if (!isOpen) await $.ui.open({ id: DECK_PANE_ID, title: DECK_TITLE, focus: true })
      return { text: arg === 'tree' ? '已切到文件页签。' : '已切到工作流页签。' }
    }
    if (arg === 'doc' || arg.startsWith('doc ')) {
      const path = arg.slice(3).trim()
      if (path !== '') {
        await loadDoc($, path)
        await update($, activeTab, () => 'doc')
        manualDeck = true
        if (!isOpen) await $.ui.open({ id: DECK_PANE_ID, title: DECK_TITLE, focus: true })
        return { text: `文档已装载：${path}` }
      }
      await update($, activeTab, () => 'doc')
      manualDeck = true
      if (!isOpen) await $.ui.open({ id: DECK_PANE_ID, title: DECK_TITLE, focus: true })
      return { text: '已切到文档页签；装载文档用 /deck doc <相对路径>。' }
    }
    return { text: '用法：/deck [flow|tree|doc [相对路径]]' }
  })

  on('tool.call', { tool: 'mcp__flow-deck__flow_task' }, async ($, e) => {
    if (e.kind !== 'iterate' && e.kind !== 'implement' && e.kind !== 'idle') {
      return { result: 'kind 必须为 iterate、implement 或 idle', isError: true }
    }
    if (e.kind !== 'idle' && (typeof e.plan !== 'string' || e.plan.trim() === '')) {
      return { result: '活动任务必须提供 plan', isError: true }
    }
    const task: FlowTask | null = e.kind === 'idle' ? null : {
      kind: e.kind, plan: e.plan as string,
      ...(typeof e.batch === 'string' && e.batch !== '' ? { batch: e.batch } : {}),
    }
    await update($, execution, () => null)
    await update($, batchScope, () => null)
    await update($, currentTask, () => task)
    lastStatus = undefined
    $.ui.status(undefined)
    return { result: task === null ? '当前任务已结束' : `当前任务：${task.kind === 'iterate' ? '方案迭代' : '方案实施'} · ${task.plan}` }
  })

  on('tool.call', { tool: 'mcp__flow-deck__flow_report' }, async ($, e) => {
    const report = parseExecution(e)
    if (report === null) {
      return { result: 'plan、batch、phase 为必填字符串', isError: true }
    }
    const stamped: ExecutionReport = { ...report, updatedAt: Date.now() }
    await update($, execution, () => stamped)
    await update($, progress, prev => ({
      ...prev,
      [`${stamped.plan}#${stamped.batch}`]: stamped.phase,
    }))
    await update($, currentTask, () => stamped.phase === '收口' ? null : {
      kind: 'implement', plan: stamped.plan, batch: stamped.batch,
    })
    const scope = await read($, batchScope)
    if (stamped.phase === '收口' || (scope !== null && (scope.plan !== stamped.plan || scope.batch !== stamped.batch))) {
      await update($, batchScope, () => null)
    }
    lastStatus = undefined
    $.ui.status(undefined)
    try {
      await $.store.set(EXECUTION_STORE_KEY, stamped)
    } catch (error) {
      $.ui.log(`flow-deck 跨会话持久化失败：${String(error)}`, { to: 'debug' })
    }
    return { result: '进度已上报' }
  })

  on('tool.call', { tool: 'mcp__flow-deck__flow_batch' }, async ($, e) => {
    const scope = parseBatchScope(e)
    if (scope === null) {
      return { result: 'plan、batch 为必填字符串，files 为非空字符串数组', isError: true }
    }
    await update($, batchScope, () => scope)
    // 边界变了越界集合随之变化，应允许再次提醒
    await update($, guardWarned, () => [])
    await update($, currentTask, () => ({ kind: 'implement', plan: scope.plan, batch: scope.batch }))
    lastStatus = undefined
    $.ui.status(undefined)
    return { result: `批次边界已声明：${scope.batch} 共 ${scope.files.length} 个文件` }
  })

  on('tool.call', { tool: 'mcp__flow-deck__flow_deps' }, async ($, e) => {
    const graph = parseDepGraph(e)
    if (graph === null || graph.batches.length === 0) {
      return { result: 'plan 为必填字符串，batches 为非空数组（每项含 batch）', isError: true }
    }
    await update($, deps, () => graph)
    return { result: `波次依赖已声明：${graph.plan} 共 ${graph.batches.length} 批` }
  })

  // 引擎要求钩子处于文件顶层或内联；Edit/Write 入参类型不同，守卫判定已下沉
  // decideGuard 纯函数，warn 去重共享 warnOnce，这里内联两份薄壳；
  // 放行分支（pass/warn）追加改动记录供 /tree 面板展示，判定与返回值零改动
  on('tool.call', { tool: 'Edit' }, async ($, e, next) => {
    const verdict = await decideGuard($, e.tool, e.file_path)
    if (verdict.action === 'pass') {
      await recordTouch($, e.file_path)
      return next(e)
    }
    if (verdict.action === 'deny') return { deny: guardDenyMessage(verdict) }
    await warnOnce($, verdict)
    await recordTouch($, e.file_path)
    return next(e)
  })
  on('tool.call', { tool: 'Write' }, async ($, e, next) => {
    const verdict = await decideGuard($, e.tool, e.file_path)
    if (verdict.action === 'pass') {
      await recordTouch($, e.file_path)
      return next(e)
    }
    if (verdict.action === 'deny') return { deny: guardDenyMessage(verdict) }
    await warnOnce($, verdict)
    await recordTouch($, e.file_path)
    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: DECK_PANE_ID }, async ($, e) => {
    const { Box, Button } = $.ui.resolve(e)
    const active = await read($, activeTab)
    const tabsRow = (
      <Box>
        <Button key="tab-flow" hotkey="1" plain dimColor={active !== 'flow'} onPress={() => { void update($, activeTab, () => 'flow') }}>工作流</Button>
        <Button key="tab-files" hotkey="2" plain dimColor={active !== 'files'} onPress={() => { void update($, activeTab, () => 'files') }}>文件</Button>
        <Button key="tab-doc" hotkey="3" plain dimColor={active !== 'doc'} onPress={() => { void update($, activeTab, () => 'doc') }}>文档</Button>
        <Button key="view-main" plain onPress={() => { void $.ui.view({}).catch(error => {
          $.ui.log(`flow-deck 切回主对话失败：${String(error)}`, { to: 'debug' })
        }) }}>主对话</Button>
      </Box>
    )
    const body = active === 'files' ? await renderFilesBody($, e)
      : active === 'doc' ? await renderDocBody($, e)
        : await renderFlowBody($, e)
    return (
      <Box flexDirection="column" gap={1}>
        {tabsRow}
        {body}
      </Box>
    )
  })

  // Spinner 行（视线常驻）：实施中报批次与阶段，迭代中报评审轮次，无任务时报运行中的子代理；
  // 只重写 word，不碰 suffix/message（引擎继续画时长与 token），无话可说时透传
  on('ui.render', { component: 'Spinner' }, async ($, e, next) => {
    const task = await read($, currentTask)
    const report = task?.kind === 'implement' ? await read($, execution) : null
    const list = task?.kind === 'iterate' ? await read($, plans) : []
    const plan = task?.kind === 'iterate' ? list.find(one => one.name === task.plan) : undefined
    const running = task === null
      ? (await read($, agents)).agents.filter(agent => agent.status === 'running')
      : []
    const word = spinnerWord(task, report, plan, running)
    if (word === null) return next(e)
    return next({ ...e, props: { ...e.props, word } })
  })

  // Edit/Write 工具行的批次合规标注（紧凑行自绘）：界内 ◆、越界放行 ⚠、拦截 ✗；
  // ctrl+o 展开态、中断行与真实错误行透传引擎原样；判定与守卫同一口径（guardDecision）
  on('ui.render', { component: 'ToolUse' }, async ($, e, next) => {
    const tool = e.props.tool
    if (tool !== 'Edit' && tool !== 'Write') return next(e)
    const scope = await read($, batchScope)
    const task = await read($, currentTask)
    const active = scope !== null && sessionCwd !== '' && task?.kind === 'implement' &&
      task.plan === scope.plan && (task.batch === undefined || task.batch === scope.batch)
    const decision = active
      ? guardDecision(scope, tool, e.props.input, sessionCwd)
      : ({ kind: 'pass' } as const)
    const intercepted = decision.kind === 'outOfScope' && guardMode === 'deny'
    if (e.props.isExpanded === true || e.props.isInterrupted === true ||
        (e.props.isErrored === true && !intercepted)) return next(e)
    const mark = toolMark(active, decision.kind === 'outOfScope', guardMode)
    const input = e.props.input as { file_path?: unknown }
    const rawPath = typeof input.file_path === 'string' ? input.file_path : ''
    const path = sessionCwd === '' ? rawPath : normalizePath(rawPath, sessionCwd)
    const { Box, Text } = $.ui.resolve(e)
    const inBoundary = active && decision.kind === 'pass'
    return (
      <Box>
        <Text wrap="truncate-end">
          <Text bold>{tool}</Text>
          {rawPath === ''
            ? <Text dimColor> {tool === 'Edit' ? '编辑中…' : '写入中…'}</Text>
            : <Text> {path}</Text>}
          {inBoundary && <Text color={TONE.accent}> {MARK.pin}</Text>}
          {mark !== null && <Text color={mark.tone === 'bad' ? TONE.bad : mark.tone === 'warn' ? TONE.warn : TONE.accent}> {mark.text}</Text>}
          {e.props.isRunning === true && <Text dimColor> ·</Text>}
        </Text>
      </Box>
    )
  })

  // 输入框守卫预览：实施中有边界时，草稿里的路径 token 实时标色（界内绿/越界黄），
  // 把守卫从「事后拦截」提前到「打字时可见」；paint 只挂本插件的装饰，草稿一改即失效重画
  on('prompt.edit', { origin: { kind: 'composer' } }, async ($, e, next) => {
    const scope = await read($, batchScope)
    const task = await read($, currentTask)
    const active = scope !== null && sessionCwd !== '' && task?.kind === 'implement' &&
      task.plan === scope.plan && (task.batch === undefined || task.batch === scope.batch)
    let decorations: PromptDecoration[] = []
    if (active) {
      const keys = new Set(scope.files.map(file => normalizePath(file, sessionCwd).toLowerCase()))
      decorations = draftDecorations(e.text, keys, sessionCwd).map(row => ({
        start: row.start,
        end: row.end,
        color: row.inScope ? TONE.ok : TONE.warn,
        underline: row.inScope ? undefined : true,
      }))
    }
    try {
      await $.prompt.paint({ text: e.text, decorations })
    } catch (error) {
      $.ui.log(`flow-deck 输入框预览失败：${String(error)}`, { to: 'debug' })
    }
    return next(e)
  })

  // 后台任务完成通知行（含子代理收尾）：状态点 + 名称 + 耗时；ctrl+o 展开态透传引擎原样
  on('ui.render', { component: 'UserMessage', props: { origin: { kind: 'task-notification' } } }, async ($, e, next) => {
    if (e.props.isExpanded === true) return next(e)
    const task = e.props.task
    const name = e.props.from?.name ?? task?.id ?? '后台任务'
    const duration = task?.durationMs === undefined ? '' : ` · ${humanDuration(task.durationMs)}`
    const status = task?.status
    const mark = status === 'completed'
      ? { glyph: MARK.done, color: TONE.ok as string | undefined }
      : status === 'failed'
        ? { glyph: MARK.bad, color: TONE.bad }
        : { glyph: MARK.idle, color: undefined }
    const { Box, Text } = $.ui.resolve(e)
    return (
      <Box>
        <Text wrap="truncate-end">
          <Text color={mark.color}>{mark.glyph}</Text>
          <Text> {name}</Text>
          {duration !== '' && <Text dimColor>{duration}</Text>}
        </Text>
      </Box>
    )
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (typeof e.viewport?.isFullscreen === 'boolean') lastFullscreen = e.viewport.isFullscreen
    if (e.props.hasSurvey) return next(e)
    if (e.props.maxRows < 1) return next(e)
    const { report, scope } = await readTaskView($)
    const git = await read($, gitStatus)
    // 工作区干净且与上游同步时不占横条
    const gitLine = git !== null && !isGitQuiet(git) ? git : null
    if (report === null && scope === null && gitLine === null) return next(e)
    const { counts, lines } = gitLine === null ? { counts: null, lines: null } : gitSummaryParts(gitLine)
    const { Box, Text } = $.ui.resolve(e)
    // 单行空间优先展示冲突，否则保留执行；截断长行，避免挤占输入区。
    const showGit = gitLine !== null && (e.props.maxRows >= 2 || (report === null && scope === null) || gitLine.conflicts.length > 0)
    const showFlow = e.props.maxRows >= 2 || !showGit
    return (
      <Box flexDirection="column">
        {showFlow && report !== null && (
          <Text wrap="truncate-end">
            <Text color={TONE.accent}>{MARK.run} flow </Text>
            <Text>{describeExecution(report)}</Text>
            {scope !== null && scope.plan === report.plan && scope.batch === report.batch && <Text dimColor> · 守卫 {scope.files.length} 文件</Text>}
          </Text>
        )}
        {showFlow && report === null && scope !== null && (
          <Text dimColor wrap="truncate-end">
            ▸ {scope.plan} · {scope.batch} · 守卫 {scope.files.length} 文件
          </Text>
        )}
        {showGit && gitLine !== null && (
          <Text wrap="truncate-end">
            <Text color={gitLine.conflicts.length > 0 ? TONE.bad : TONE.accent}>{MARK.info} git </Text>
            {gitLine.conflicts.length > 0 && <Text color={TONE.bad}>{MARK.bad}冲突{gitLine.conflicts.length} · </Text>}
            <Text>{gitLine.branch}</Text>
            {gitLine.ahead > 0 && <Text color={TONE.ok}> ↑{gitLine.ahead}</Text>}
            {gitLine.behind > 0 && <Text color={TONE.warn}> ↓{gitLine.behind}</Text>}
            {counts !== null && <Text dimColor> · {counts}</Text>}
            {lines !== null && <Text dimColor> · </Text>}
            {gitLine.added > 0 && <Text color={TONE.added}>+{gitLine.added}</Text>}
            {gitLine.removed > 0 && <Text color={TONE.removed}> −{gitLine.removed}</Text>}
          </Text>
        )}
      </Box>
    )
  })
}
