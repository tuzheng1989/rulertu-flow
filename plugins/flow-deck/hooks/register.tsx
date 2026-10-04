import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import {
  buildPlanReview,
  extractRound,
  guardDecision,
  parseBatchScope,
  parseExecution,
  sparkline,
} from './parse'
import type { BatchScope, ExecutionReport, PlanReview } from '../types'

const PANE_ID = 'flow'
const POLL_MS = 2000
const MAX_DEPTH = 4
const SKIP_DIRS = new Set(['node_modules', '.git'])
const EXECUTION_STORE_KEY = 'lastExecution'

const plans = atom({ plugin: 'flow-deck', key: 'plans' } as const, [])
const notified = atom({ plugin: 'flow-deck', key: 'notified' } as const, [])
const baselined = atom({ plugin: 'flow-deck', key: 'baselined' } as const, false)
const execution = atom({ plugin: 'flow-deck', key: 'execution' } as const, null)
const batchScope = atom({ plugin: 'flow-deck', key: 'batchScope' } as const, null)

/** 上次写入 statusline 的文案；仅用于跳过重复写入（热加载后重算一次无妨） */
let lastStatus: string | undefined

/** 越界改动处理模式；register 时按 userConfig 覆盖（引擎要求钩子处于文件顶层，经此间接读取配置） */
let guardMode: 'warn' | 'deny' = 'warn'

/** 会话工作目录；tool.call 事件不带 cwd，自 session.start 缓存（先于首个工具调用触发） */
let sessionCwd = ''

/** 越界拦截的 deny 文案 */
function guardDenyMessage(path: string, batch: string): string {
  return `flow-deck：${path} 在批次 ${batch} 边界外，已按 guardMode=deny 拦截。确需改动请先调用 flow_batch 更新边界。`
}

/** 越界放行的 warn 文案 */
function guardWarnMessage(path: string, batch: string): string {
  return `⚠ flow-deck：${path} 在批次 ${batch} 边界外，已放行（guardMode=warn）`
}

/** 守卫动作：pass 放行；deny/warn 附越界路径与所属批次 */
export type GuardAction =
  | { action: 'pass' }
  | { action: 'deny' | 'warn'; path: string; batch: string }

/** 读取边界并作出守卫判定；未声明边界或 cwd 未就绪时放行（fail-open） */
async function decideGuard($: EngineInterface, tool: string, file_path: unknown): Promise<GuardAction> {
  const scope: BatchScope | null = await read($, batchScope)
  if (scope === null || sessionCwd === '') return { action: 'pass' }
  const decision = guardDecision(scope, tool, { file_path }, sessionCwd)
  if (decision.kind === 'pass') return { action: 'pass' }
  return { action: guardMode, path: decision.path, batch: scope.batch }
}

/** 读文件，不存在或读不了时返回 null */
async function readTextIfExists($: EngineInterface, path: string): Promise<string | null> {
  try {
    if (!(await $.fs.exists(path))) return null
    return await $.fs.read(path)
  } catch {
    return null
  }
}

/** 读取一个方案目录（state.json + review-RN.json），无 state.json 视为非方案目录 */
async function readPlanDir(
  $: EngineInterface,
  planDir: string,
  name: string,
): Promise<PlanReview | null> {
  const stateText = await readTextIfExists($, `${planDir}/state.json`)
  if (stateText === null) return null
  let entries: Awaited<ReturnType<typeof $.fs.list>> = []
  try {
    entries = await $.fs.list(planDir)
  } catch {
    entries = []
  }
  const reviews: { round: number; text: string }[] = []
  for (const entry of entries) {
    const round = extractRound(entry.name)
    if (entry.kind !== 'file' || round === null) continue
    const text = await readTextIfExists($, `${planDir}/${entry.name}`)
    if (text !== null) reviews.push({ round, text })
  }
  return buildPlanReview(name, planDir, stateText, reviews)
}

/** 在工作目录下递归寻找 .plan-iterate 目录（深度受限，跳过依赖目录） */
async function scanForPlans(
  $: EngineInterface,
  rel: string,
  depth: number,
): Promise<PlanReview[]> {
  if (depth > MAX_DEPTH) return []
  let entries
  try {
    // 空串会被当字面路径处理失败，工作目录必须省略参数
    entries = rel === '' ? await $.fs.list() : await $.fs.list(rel)
  } catch {
    return []
  }
  const found: PlanReview[] = []
  for (const entry of entries) {
    if (entry.kind !== 'dir' || SKIP_DIRS.has(entry.name)) continue
    const child = rel === '' ? entry.name : `${rel}/${entry.name}`
    if (entry.name === '.plan-iterate') {
      let planDirs
      try {
        planDirs = await $.fs.list(child)
      } catch {
        continue
      }
      for (const planEntry of planDirs) {
        if (planEntry.kind !== 'dir') continue
        const plan = await readPlanDir($, `${child}/${planEntry.name}`, planEntry.name)
        if (plan !== null) found.push(plan)
      }
    } else {
      found.push(...(await scanForPlans($, child, depth + 1)))
    }
  }
  return found
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

/** 一轮扫描：更新面板数据、对新落盘轮次发 toast、刷新 statusline */
async function poll($: EngineInterface): Promise<void> {
  const found = (await scanForPlans($, '', 0)).sort((a, b) => (a.name < b.name ? -1 : 1))
  await update($, plans, () => found)

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
  const lastFresh = fresh.at(-1) ?? null
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

  // 多方案并存时 statusline 展示名字排序的最后一个；单方案（常态）即其本身
  const lastPlan = found.at(-1) ?? null
  const summary = lastPlan === null ? undefined : summarize(lastPlan)
  $.ui.log(`flow-deck 扫描完成：${found.length} 个方案`, { to: 'debug' })
  if (summary !== lastStatus) {
    lastStatus = summary
    $.ui.status(summary)
  }
}

export const register: Register = (on, options) => {
  guardMode = options.guardMode === 'deny' ? 'deny' : 'warn'

  on('session.start', async ($, e, next) => {
    sessionCwd = e.cwd
    await $.command.register({ name: 'flow', description: '打开 rulertu-flow 评审仪表盘' })
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
    const last = await readLastExecution($)
    if (last !== null) $.ui.toast(`上次执行：${describeExecution(last)}`)
    $.clock.every(POLL_MS, () => {
      void poll($).catch(error => {
        $.ui.log(`flow-deck 轮询失败：${String(error)}`, { to: 'debug' })
      })
    })
    return next(e)
  })

  on('command.run', { command: 'flow' }, async $ => {
    await $.ui.open({ id: PANE_ID, title: 'Flow 评审仪表盘' })
    return { text: '已打开评审仪表盘。' }
  })

  on('tool.call', { tool: 'mcp__flow-deck__flow_report' }, async ($, e) => {
    const report = parseExecution(e)
    if (report === null) {
      return { result: 'plan、batch、phase 为必填字符串', isError: true }
    }
    const stamped: ExecutionReport = { ...report, updatedAt: Date.now() }
    await update($, execution, () => stamped)
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
    return { result: `批次边界已声明：${scope.batch} 共 ${scope.files.length} 个文件` }
  })

  // 引擎要求钩子处于文件顶层或内联；Edit/Write 入参类型不同，守卫判定已下沉
  // decideGuard 纯函数，这里内联两份薄壳
  on('tool.call', { tool: 'Edit' }, async ($, e, next) => {
    const verdict = await decideGuard($, e.tool, e.file_path)
    if (verdict.action === 'pass') return next(e)
    if (verdict.action === 'deny') return { deny: guardDenyMessage(verdict.path, verdict.batch) }
    $.ui.log(guardWarnMessage(verdict.path, verdict.batch))
    return next(e)
  })
  on('tool.call', { tool: 'Write' }, async ($, e, next) => {
    const verdict = await decideGuard($, e.tool, e.file_path)
    if (verdict.action === 'pass') return next(e)
    if (verdict.action === 'deny') return { deny: guardDenyMessage(verdict.path, verdict.batch) }
    $.ui.log(guardWarnMessage(verdict.path, verdict.batch))
    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: PANE_ID }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const list = await read($, plans)

    if (list.length === 0) {
      return (
        <Box flexDirection="column">
          <Text>未发现活跃的 plan-iterate 评审。</Text>
          <Text dimColor>运行 plan-iterate 后自动出现；/flow 可随时打开本面板。</Text>
        </Box>
      )
    }

    return (
      <Box flexDirection="column">
        {list.map(plan => {
          const latest = plan.rounds.at(-1) ?? null
          return (
            <Box key={plan.dir} flexDirection="column">
              <Box flexDirection="row">
                <Text bold>{plan.name}</Text>
                <Text dimColor> · R{plan.round}/5 · </Text>
                {latest === null ? (
                  <Text dimColor>评审进行中</Text>
                ) : (
                  <Text bold color={plan.passed ? 'green' : 'yellow'}>
                    {latest.score} 分
                  </Text>
                )}
                {plan.passed && <Text color="green"> · ✓ 已达标</Text>}
              </Box>
              {plan.rounds.length > 0 && (
                <Text dimColor>
                  趋势 {sparkline(plan.rounds.map(round => round.score))}（8.5 分达标）
                </Text>
              )}
              <Box flexDirection="row">
                {latest === null && <Text dimColor>暂无已落盘的评审结果</Text>}
                {latest !== null && latest.p0 > 0 && <Text color="red">P0×{latest.p0} </Text>}
                {latest !== null && latest.p1 > 0 && <Text color="yellow">P1×{latest.p1} </Text>}
                {latest !== null && latest.p2 > 0 && <Text dimColor>P2×{latest.p2}</Text>}
                {latest !== null && latest.p0 === 0 && latest.p1 === 0 && latest.p2 === 0 && (
                  <Text dimColor>无问题</Text>
                )}
              </Box>
            </Box>
          )
        })}
      </Box>
    )
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    const report = await read($, execution)
    const scope = await read($, batchScope)
    if (report === null && scope === null) return next(e)
    const { Box, Text } = $.ui.resolve(e)
    return (
      <Box flexDirection="column">
        {report !== null && (
          <Box>
            <Text dimColor>▸ </Text>
            <Text>{describeExecution(report)}</Text>
            {scope !== null && <Text dimColor> · 守卫 {scope.files.length} 文件</Text>}
          </Box>
        )}
        {report === null && scope !== null && (
          <Text dimColor>
            ▸ {scope.plan} · {scope.batch} · 守卫 {scope.files.length} 文件
          </Text>
        )}
      </Box>
    )
  })
}
