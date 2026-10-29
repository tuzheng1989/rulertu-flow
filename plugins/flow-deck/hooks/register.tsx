import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import {
  DOC_SECTION_MAX_LINES,
  bannerPlan,
  depStatuses,
  gitSummaryParts,
  guardDecision,
  isGitQuiet,
  parseBatchScope,
  parseDepGraph,
  parseExecution,
  parseSections,
  phaseProgress,
  progressBar,
  selectTaskView,
  sparkline,
} from './parse'
import { createGitPoller, createPlanScanner, singleFlight } from './poll'
import { agentStatus, agentSummary, createAgentPoller } from './agents'
import type {
  BatchScope,
  ExecutionReport,
  FlowTask,
  GitFileState,
  GitStatus,
  PlanReview,
} from '../types'

const PANE_ID = 'flow'
const GIT_PANE_ID = 'flow-git'
const DOC_PANE_ID = 'flow-doc'
const DOC_TITLE = '文档浏览'
const POLL_MS = 2000
const GIT_POLL_MS = 5000
const GIT_TIMEOUT_MS = 5000
const MAX_GIT_FILES = 15
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
function gitFileLabel(file: GitFileState): string {
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

export const register: Register = (on, options) => {
  guardMode = options.guardMode === 'deny' ? 'deny' : 'warn'

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
    planTimer?.cancel()
    gitTimer?.cancel()
    scanPlans = createPlanScanner({
      list: path => path === undefined ? $.fs.list() : $.fs.list(path),
      read: path => $.fs.read(path),
    })
    await $.command.register({ name: 'flow', description: '开关当前方案迭代或实施任务面板（含子代理运行状态）' })
    await $.command.register({ name: 'git', description: '打开 git 仓库状态面板' })
    await $.command.register({ name: 'flow-agents', description: '打开工作流面板（子代理状态在面板内，已开时不再重复打开）' })
    await $.command.register({ name: 'doc', description: '开关文档浏览面板：/doc <相对路径> 打开文档，选节后可把修改请求填入输入框' })
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
        if ((await $.ui.panes()).some(pane => pane.id === PANE_ID)) await refreshAgentList()
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

  on('command.run', { command: 'flow' }, async $ => {
    // toggle：面板已开则关闭（引擎原生关闭键同样可用，这里补键盘流的对称入口）
    const isUp = (await $.ui.panes()).some(pane => pane.id === PANE_ID)
    if (isUp) {
      await $.ui.close({ id: PANE_ID })
      return { text: '已关闭工作流面板。' }
    }
    await $.ui.open({ id: PANE_ID, title: 'Flow 当前任务' })
    void refreshAgents?.().catch(error => {
      $.ui.log(`flow-deck 子代理刷新失败：${String(error)}`, { to: 'debug' })
    })
    return { text: '已打开工作流面板（含子代理状态）。' }
  })

  on('command.run', { command: 'git' }, async $ => {
    const isUp = (await $.ui.panes()).some(pane => pane.id === GIT_PANE_ID)
    if (isUp) {
      await $.ui.close({ id: GIT_PANE_ID })
      return { text: '已关闭 git 仓库状态面板。' }
    }
    void refreshGit?.().catch(error => {
      $.ui.log(`flow-deck git 刷新失败：${String(error)}`, { to: 'debug' })
    })
    await $.ui.open({ id: GIT_PANE_ID, title: 'Git 仓库状态' })
    return { text: '已打开 git 仓库状态面板。' }
  })

  on('command.run', { command: 'flow-agents' }, async $ => {
    // 幂等打开：子代理状态已并入工作流面板，重复打开不误关（toggle 由 /flow 负责）
    const isUp = (await $.ui.panes()).some(pane => pane.id === PANE_ID)
    if (isUp) return { text: '工作流面板已打开，子代理状态在面板内。' }
    await $.ui.open({ id: PANE_ID, title: 'Flow 当前任务' })
    void refreshAgents?.().catch(error => {
      $.ui.log(`flow-deck 子代理刷新失败：${String(error)}`, { to: 'debug' })
    })
    return { text: '已打开工作流面板（含子代理状态）。' }
  })

  on('command.run', { command: 'doc' }, async ($, e) => {
    // toggle 与装载一体：带路径打开并读文件，无路径时已开则关、未开给用法
    const target = e.args.trim()
    const isUp = (await $.ui.panes()).some(pane => pane.id === DOC_PANE_ID)
    if (target !== '') {
      await loadDoc($, target)
      if (!isUp) await $.ui.open({ id: DOC_PANE_ID, title: DOC_TITLE })
      return { text: `文档面板已打开：${target}` }
    }
    if (isUp) {
      await $.ui.close({ id: DOC_PANE_ID })
      return { text: '已关闭文档面板。' }
    }
    return { text: '用法：/doc <相对路径> 打开文档浏览面板。' }
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
  // decideGuard 纯函数，warn 去重共享 warnOnce，这里内联两份薄壳
  on('tool.call', { tool: 'Edit' }, async ($, e, next) => {
    const verdict = await decideGuard($, e.tool, e.file_path)
    if (verdict.action === 'pass') return next(e)
    if (verdict.action === 'deny') return { deny: guardDenyMessage(verdict) }
    await warnOnce($, verdict)
    return next(e)
  })
  on('tool.call', { tool: 'Write' }, async ($, e, next) => {
    const verdict = await decideGuard($, e.tool, e.file_path)
    if (verdict.action === 'pass') return next(e)
    if (verdict.action === 'deny') return { deny: guardDenyMessage(verdict) }
    await warnOnce($, verdict)
    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: PANE_ID }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const task = await read($, currentTask)
    const { plans: list, graph, report, scope } = await readTaskView($)
    const progressMap: Record<string, string> = await read($, progress)
    const snapshot = await read($, agents)
    const crumbs = await read($, lastRun)
    const stallMinutes = await read($, stall)
    const wide = e.props.bodyColumns >= 44
    const nodes = graph === null ? [] : depStatuses(graph, progressMap)
    const done = nodes.filter(node => node.status === 'done').length
    const passing = list.filter(plan => plan.passed)
    // 无事不扰：达标方案折叠为一行，未达标排前并逐个展示
    const activePlans = [...list].sort((a, b) => Number(a.passed) - Number(b.passed)).filter(plan => !plan.passed)
    const names = new Map(snapshot.agents.map(agent => [agent.id, agent.name || agent.description || agent.id]))

    const agentsSection = (
      <Box flexDirection="column" gap={1}>
        <Box>
          <Text bold wrap="truncate-end">▍子代理{snapshot.loaded ? ` · ${agentSummary(snapshot.agents)}` : ''}</Text>
          <Button key="flow-refresh" hotkey="r" plain onPress={() => refreshAll?.()}>刷新</Button>
        </Box>
        {snapshot.error && <Text color="yellow" wrap="truncate-end">刷新失败，自动重试；{snapshot.loaded ? '以下为上次快照，状态可能已过期。' : '暂未取得子代理状态。'}</Text>}
        {!snapshot.loaded && !snapshot.error && <Text dimColor>正在读取当前会话的子代理…</Text>}
        {snapshot.loaded && snapshot.agents.length === 0 && <Text dimColor>当前会话暂无子代理。</Text>}
        {snapshot.agents.map(agent => {
          const status = agentStatus(agent.status)
          return (
            <Box key={agent.id} flexDirection="column" borderStyle={wide ? 'round' : undefined} borderColor={status.color} paddingX={wide ? 1 : 0}>
              <Text bold color={status.color} wrap="truncate-end">{status.mark} {status.label} · {agent.name || agent.description || agent.id}</Text>
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
          <Text dimColor wrap="truncate-end">/flow 关闭 · /git 仓库状态 · 面板内按 r 刷新</Text>
        </Box>
      )
    }

    const phase = report === null ? null : phaseProgress(report.phase)
    return (
      <Box flexDirection="column" gap={1}>
        <Box flexDirection="column">
          <Text bold color="cyan">FLOW / {task.kind === 'iterate' ? '方案迭代' : '方案实施'} · {task.plan}</Text>
          {task.kind === 'iterate' && <Text dimColor wrap="truncate-end">评审 {list.length} · 待达标 {list.length - passing.length} · 已达标 {passing.length}</Text>}
          {task.kind === 'implement' && graph !== null && <Text dimColor wrap="truncate-end">批次 {done}/{nodes.length} 收口</Text>}
        </Box>
        {task.kind === 'iterate' && list.length === 0 && <Text dimColor>方案迭代进行中，等待评审结果落盘。</Text>}
        {task.kind === 'implement' && report === null && <Text dimColor>实施任务已开始，等待阶段进度上报。</Text>}
        {report !== null && phase !== null && (
          <Box flexDirection="column" borderStyle={wide ? 'round' : undefined} borderColor="cyan" paddingX={wide ? 1 : 0}>
            <Text bold color="cyan" wrap="truncate-end">● 当前执行 · {report.plan}</Text>
            <Text wrap="truncate-end">{report.batch}{report.tLevel === undefined ? '' : ` · ${report.tLevel}`} · {report.phase}</Text>
            {phase.total > 0 && (
              <Text wrap="truncate-end">
                <Text color="green">{progressBar(phase.index, phase.total)}</Text>
                <Text> </Text>
                <Text color={phase.index >= phase.total ? 'green' : 'yellow'} bold>{phase.current} · {phase.index}/{phase.total}</Text>
              </Text>
            )}
            {phase.total === 0 && <Text dimColor wrap="truncate-end">{phase.current}</Text>}
            {stallMinutes !== null && <Text color="yellow" wrap="truncate-end">⚠ 疑似停滞 · 距上次上报 {stallMinutes} 分钟</Text>}
            {report.testsTotal !== undefined && (
              <Text color={report.testsTotal > 0 && report.testsPassed === report.testsTotal ? 'green' : 'yellow'} wrap="truncate-end">
                验证 {progressBar(report.testsPassed ?? 0, report.testsTotal)} {report.testsPassed ?? 0}/{report.testsTotal}
              </Text>
            )}
            {report.evidenceDir !== undefined && <Text dimColor wrap="truncate-middle">证据 {report.evidenceDir}</Text>}
          </Box>
        )}
        {scope !== null && <Text dimColor wrap="truncate-end">◇ 边界 · {scope.plan} / {scope.batch} · {scope.files.length} 文件 · {guardMode}</Text>}
        {activePlans.length > 0 && (
          <Text bold>▍plan-iterate 评审 · 8.5 分且无 P0/P1 达标</Text>
        )}
        {activePlans.map(plan => {
          const latest = plan.rounds.at(-1) ?? null
          const previous = plan.rounds.at(-2) ?? null
          const delta = latest === null || previous === null ? null : latest.score - previous.score
          const tone = plan.passed ? 'green' : latest !== null && latest.p0 > 0 ? 'red' : 'yellow'
          return (
            <Box key={plan.dir} flexDirection="column" borderStyle={wide ? 'round' : undefined} borderColor={tone} paddingX={wide ? 1 : 0}>
              <Text bold color={tone} wrap="truncate-end">{plan.passed ? '✓' : '●'} {plan.name}</Text>
              <Text wrap="truncate-end">
                <Text color={tone}>{latest === null ? '等待结果' : `${latest.score.toFixed(1)} / 10`}</Text>
                <Text dimColor> · R{plan.round}/5 · {plan.passed ? '已达标' : '待达标'}</Text>
              </Text>
              {latest !== null && (
                <Text wrap="truncate-end">
                  <Text color={tone}>{progressBar(latest.score, 10)}</Text>
                  <Text dimColor> {sparkline(plan.rounds.slice(-12).map(round => round.score))}</Text>
                  {delta !== null && <Text color={delta > 0 ? 'green' : delta < 0 ? 'red' : undefined}> {delta > 0 ? '↑' : delta < 0 ? '↓' : '='}{Math.abs(delta).toFixed(1)}</Text>}
                </Text>
              )}
              <Text wrap="truncate-end">
                {latest === null && <Text dimColor>暂无已落盘的评审结果</Text>}
                {latest !== null && latest.p0 > 0 && <Text color="red">P0×{latest.p0} </Text>}
                {latest !== null && latest.p1 > 0 && <Text color="yellow">P1×{latest.p1} </Text>}
                {latest !== null && latest.p2 > 0 && <Text dimColor>P2×{latest.p2}</Text>}
                {latest !== null && latest.p0 === 0 && latest.p1 === 0 && latest.p2 === 0 && (
                  <Text dimColor>无问题</Text>
                )}
              </Text>
            </Box>
          )
        })}
        {passing.length > 0 && <Text color="green" wrap="truncate-end">✓ 已达标 {passing.length} 个方案（已折叠）</Text>}
        {graph !== null && (
          <Box flexDirection="column" gap={1}>
            <Text bold wrap="truncate-end">▍执行 DAG（{graph.plan}）</Text>
            <Text color="cyan" wrap="truncate-end">
              {nodes.map(node => (
                <Text key={node.batch}
                  color={node.status === 'done' ? 'green' : node.status === 'active' ? 'yellow' : undefined}
                  dimColor={node.status === 'pending'}>
                  {node.status === 'done' ? '■' : node.status === 'active' ? '▣' : '□'}
                </Text>
              ))}
              {' '}{done}/{nodes.length} 收口 · {nodes.filter(node => node.status === 'active').length} 进行中
            </Text>
            {nodes.map((node, index) => (
              <Box key={node.batch} flexDirection="column">
                <Text dimColor={node.status === 'pending'} color={node.status === 'done' ? 'green' : node.status === 'active' ? 'yellow' : undefined} wrap="truncate-end">
                  {node.status === 'done' ? '✓ ' : node.status === 'active' ? '● ' : '○ '}{node.batch}
                </Text>
                <Text dimColor wrap="truncate-end">{index === nodes.length - 1 ? '└' : '│'} {progressMap[`${graph.plan}#${node.batch}`] ?? '待执行'}{node.dependsOn.length > 0 ? ` · ← ${node.dependsOn.join('、')}` : ' · 起点'}</Text>
              </Box>
            ))}
          </Box>
        )}
        {agentsSection}
        <Text dimColor wrap="truncate-end">/flow 关闭 · /git 仓库状态 · 面板内按 r 刷新</Text>
      </Box>
    )
  })

  on('ui.render', { component: 'Pane', requestId: DOC_PANE_ID }, async ($, e) => {
    const { Box, Text, Button, Select } = $.ui.resolve(e)
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
          <Text bold color="red" wrap="truncate-end">DOC / {doc.path}</Text>
          <Text color="red" wrap="truncate-end">读取失败：{doc.error ?? '未知原因'}</Text>
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
          <Text bold color="cyan" wrap="truncate-end">DOC / {doc.path} · 空文档</Text>
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
        <Text bold color="cyan" wrap="truncate-end">DOC / {doc.path} · {sections.length} 节 · {allLines.length} 行</Text>
        <Select
          key="doc-section"
          label="节"
          options={sections.map((section, i) => ({ value: String(i), text: `${section.title}` }))}
          value={String(index)}
          onSelect={value => { void update($, docSection, () => Number(value)) }}
        />
        <Box flexDirection="column" borderStyle={wide ? 'round' : undefined} paddingX={wide ? 1 : 0}>
          <Text bold wrap="truncate-end">
            {'#'.repeat(Math.max(current.level, 1))} {current.title} · 第 {current.start}–{current.end} 行
            {truncated ? ` · 截断显示前 ${DOC_SECTION_MAX_LINES} 行` : ''}
          </Text>
          {shown.map((line, i) => (
            <Text key={current.start + i} wrap="truncate-end">{line === '' ? ' ' : line}</Text>
          ))}
        </Box>
        <Box>
          <Button key="doc-send" hotkey="e" plain onPress={() => { void sendEdit() }}>发给 Claude</Button>
          <Button key="doc-reload" hotkey="r" plain onPress={reload}>重读</Button>
        </Box>
        <Text dimColor wrap="truncate-end">/doc 关闭 · e 把修改请求填入输入框（补意图后回车）</Text>
      </Box>
    )
  })

  on('ui.render', { component: 'Pane', requestId: GIT_PANE_ID }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const status: GitStatus | null = await read($, gitStatus)

    if (status === null) {
      return (
        <Box flexDirection="column">
          <Text>当前目录不是 git 仓库，或状态尚未取到。</Text>
          <Text dimColor>自动重试；在仓库内打开会话后，/git 可重新取数。</Text>
        </Box>
      )
    }

    return (
      <Box flexDirection="column" gap={1}>
        <Text bold color="cyan">GIT / 仓库状态</Text>
        <Text wrap="truncate-middle">
          <Text bold>{status.branch}</Text>
          {status.upstream !== null && <Text dimColor> → {status.upstream}</Text>}
          {status.ahead > 0 && <Text color="green"> ↑{status.ahead}</Text>}
          {status.behind > 0 && <Text color="yellow"> ↓{status.behind}</Text>}
        </Text>
        <Text dimColor wrap="truncate-end">冲突 {status.conflicts.length} · 暂存 {status.staged.length} · 修改 {status.unstaged.length} · 新增 {status.untracked.length}</Text>
        {(status.added > 0 || status.removed > 0) && (
          <Box>
            {status.added > 0 && <Text color="green">+{status.added}</Text>}
            {status.removed > 0 && <Text color="red"> −{status.removed}</Text>}
            <Text dimColor> 行级改动（tracked 合计）</Text>
          </Box>
        )}
        {isGitQuiet(status) && <Text color="green">✓ 工作区干净{status.upstream === null ? ' · 未设置上游' : '，与上游同步'}</Text>}
        {status.conflicts.length > 0 && (
          <Box flexDirection="column">
            <Text bold color="red">
              ▍冲突（{status.conflicts.length}）
            </Text>
            {status.conflicts.slice(0, MAX_GIT_FILES).map(file => (
              <Text key={file.path} color="red" wrap="truncate-middle">
                ✗ {file.code} {gitFileLabel(file)}
              </Text>
            ))}
            {status.conflicts.length > MAX_GIT_FILES && (
              <Text dimColor>…还有 {status.conflicts.length - MAX_GIT_FILES} 个</Text>
            )}
          </Box>
        )}
        {status.staged.length > 0 && (
          <Box flexDirection="column">
            <Text bold color="green">
              ▍已暂存（{status.staged.length}）
            </Text>
            {status.staged.slice(0, MAX_GIT_FILES).map(file => (
              <Text key={file.path} color="green" wrap="truncate-middle">
                {file.code} {gitFileLabel(file)}
              </Text>
            ))}
            {status.staged.length > MAX_GIT_FILES && (
              <Text dimColor>…还有 {status.staged.length - MAX_GIT_FILES} 个</Text>
            )}
          </Box>
        )}
        {status.unstaged.length > 0 && (
          <Box flexDirection="column">
            <Text bold color="yellow">
              ▍未暂存（{status.unstaged.length}）
            </Text>
            {status.unstaged.slice(0, MAX_GIT_FILES).map(file => (
              <Text key={file.path} color="yellow" wrap="truncate-middle">
                {file.code} {gitFileLabel(file)}
              </Text>
            ))}
            {status.unstaged.length > MAX_GIT_FILES && (
              <Text dimColor>…还有 {status.unstaged.length - MAX_GIT_FILES} 个</Text>
            )}
          </Box>
        )}
        {status.untracked.length > 0 && (
          <Box flexDirection="column">
            <Text bold>▍未跟踪（{status.untracked.length}）</Text>
            {status.untracked.slice(0, MAX_GIT_FILES).map(file => (
              <Text key={file.path} dimColor wrap="truncate-middle">
                {file.code} {gitFileLabel(file)}
              </Text>
            ))}
            {status.untracked.length > MAX_GIT_FILES && (
              <Text dimColor>…还有 {status.untracked.length - MAX_GIT_FILES} 个</Text>
            )}
          </Box>
        )}
      </Box>
    )
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
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
            <Text color="cyan">● flow </Text>
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
            <Text color={gitLine.conflicts.length > 0 ? 'red' : 'cyan'}>◇ git </Text>
            {gitLine.conflicts.length > 0 && <Text color="red">✗冲突{gitLine.conflicts.length} · </Text>}
            <Text>{gitLine.branch}</Text>
            {gitLine.ahead > 0 && <Text color="green"> ↑{gitLine.ahead}</Text>}
            {gitLine.behind > 0 && <Text color="yellow"> ↓{gitLine.behind}</Text>}
            {counts !== null && <Text dimColor> · {counts}</Text>}
            {lines !== null && <Text dimColor> · </Text>}
            {gitLine.added > 0 && <Text color="green">+{gitLine.added}</Text>}
            {gitLine.removed > 0 && <Text color="red"> −{gitLine.removed}</Text>}
          </Text>
        )}
      </Box>
    )
  })
}
