import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import {
  bannerPlan,
  buildGitStatus,
  buildPlanReview,
  depStatuses,
  extractRound,
  gitSummaryParts,
  guardDecision,
  isGitQuiet,
  parseBatchScope,
  parseDepGraph,
  parseExecution,
  parseNumstat,
  parsePorcelain,
  sparkline,
} from './parse'
import type {
  BatchScope,
  DepGraph,
  ExecutionReport,
  GitFileState,
  GitStatus,
  PlanReview,
} from '../types'

const PANE_ID = 'flow'
const GIT_PANE_ID = 'flow-git'
const POLL_MS = 2000
const GIT_POLL_MS = 3000
const GIT_TIMEOUT_MS = 5000
const MAX_DEPTH = 4
const MAX_GIT_FILES = 15
const SKIP_DIRS = new Set(['node_modules', '.git'])
const EXECUTION_STORE_KEY = 'lastExecution'

const plans = atom({ plugin: 'flow-deck', key: 'plans' } as const, [])
const notified = atom({ plugin: 'flow-deck', key: 'notified' } as const, [])
const baselined = atom({ plugin: 'flow-deck', key: 'baselined' } as const, false)
const execution = atom({ plugin: 'flow-deck', key: 'execution' } as const, null)
const batchScope = atom({ plugin: 'flow-deck', key: 'batchScope' } as const, null)
const progress = atom({ plugin: 'flow-deck', key: 'progress' } as const, {})
const deps = atom({ plugin: 'flow-deck', key: 'deps' } as const, null)
const gitStatus = atom({ plugin: 'flow-deck', key: 'git' } as const, null)

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

const ZERO_LINES = { added: 0, removed: 0 } as const

/** 一轮 git 取数：status + 双 numstat → 快照入 atom；非 git 仓库记 null（面板与横条静默） */
async function pollGit($: EngineInterface): Promise<void> {
  const porcelainText = await runGit($, [
    '-c',
    'core.quotePath=false',
    'status',
    '--porcelain=v1',
    '-b',
  ])
  if (porcelainText === null) {
    await update($, gitStatus, () => null)
    return
  }
  const porcelain = parsePorcelain(porcelainText)
  if (porcelain === null) return
  // numstat 失败不阻塞状态展示，按 0 行计
  const [worktree, cached] = await Promise.all([
    runGit($, ['diff', '--numstat']),
    runGit($, ['diff', '--cached', '--numstat']),
  ])
  const status = buildGitStatus(
    porcelain,
    worktree === null ? ZERO_LINES : parseNumstat(worktree),
    cached === null ? ZERO_LINES : parseNumstat(cached),
    Date.now(),
  )
  await update($, gitStatus, () => status)
}

/** 一个 git 文件行的显示文案；rename 显示 old → new */
function gitFileLabel(file: GitFileState): string {
  return file.oldPath === undefined ? file.path : `${file.oldPath} → ${file.path}`
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

  // 达标即撤：横条只留给未达标方案（达标瞬间 toast 已播报，常驻无增量价值）；
  // 面板不受影响，仍展示全部方案与轮次历史
  const lastPlan = bannerPlan(found)
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
    await $.command.register({ name: 'git', description: '打开 git 仓库状态面板' })
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
    if (last !== null) $.ui.toast(`上次执行：${describeExecution(last)}`)
    $.clock.every(POLL_MS, () => {
      void poll($).catch(error => {
        $.ui.log(`flow-deck 轮询失败：${String(error)}`, { to: 'debug' })
      })
    })
    // git 轮询：启动先取一次数（面板打开前即有数据），此后按独立周期刷新
    void pollGit($).catch(error => {
      $.ui.log(`flow-deck git 轮询失败：${String(error)}`, { to: 'debug' })
    })
    $.clock.every(GIT_POLL_MS, () => {
      void pollGit($).catch(error => {
        $.ui.log(`flow-deck git 轮询失败：${String(error)}`, { to: 'debug' })
      })
    })
    return next(e)
  })

  on('command.run', { command: 'flow' }, async $ => {
    // toggle：面板已开则关闭（引擎原生关闭键同样可用，这里补键盘流的对称入口）
    const isUp = (await $.ui.panes()).some(pane => pane.id === PANE_ID)
    if (isUp) {
      await $.ui.close({ id: PANE_ID })
      return { text: '已关闭评审仪表盘。' }
    }
    await $.ui.open({ id: PANE_ID, title: 'Flow 评审仪表盘' })
    return { text: '已打开评审仪表盘。' }
  })

  on('command.run', { command: 'git' }, async $ => {
    const isUp = (await $.ui.panes()).some(pane => pane.id === GIT_PANE_ID)
    if (isUp) {
      await $.ui.close({ id: GIT_PANE_ID })
      return { text: '已关闭 git 仓库状态面板。' }
    }
    await $.ui.open({ id: GIT_PANE_ID, title: 'Git 仓库状态' })
    return { text: '已打开 git 仓库状态面板。' }
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

  on('tool.call', { tool: 'mcp__flow-deck__flow_deps' }, async ($, e) => {
    const graph = parseDepGraph(e)
    if (graph === null || graph.batches.length === 0) {
      return { result: 'plan 为必填字符串，batches 为非空数组（每项含 batch）', isError: true }
    }
    await update($, deps, () => graph)
    return { result: `波次依赖已声明：${graph.plan} 共 ${graph.batches.length} 批` }
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
    const graph: DepGraph | null = await read($, deps)
    const progressMap: Record<string, string> = await read($, progress)

    if (list.length === 0 && graph === null) {
      return (
        <Box flexDirection="column">
          <Text>未发现活跃的 plan-iterate 评审或波次依赖声明。</Text>
          <Text dimColor>运行 plan-iterate / optimization-plan 后自动出现；/flow 可随时打开本面板。</Text>
        </Box>
      )
    }

    return (
      <Box flexDirection="column">
        {list.length > 0 && (
          <Text bold>▍plan-iterate 评审</Text>
        )}
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
        {graph !== null && (
          <Box flexDirection="column">
            <Text bold>▍执行 DAG（{graph.plan}）</Text>
            {depStatuses(graph, progressMap).map(node => (
              <Box key={node.batch} flexDirection="row">
                <Text
                  dimColor={node.status === 'pending'}
                  color={node.status === 'done' ? 'green' : node.status === 'active' ? 'yellow' : undefined}
                >
                  {node.status === 'done' ? '✓ ' : node.status === 'active' ? '● ' : '○ '}
                </Text>
                <Text dimColor={node.status === 'pending'}>{node.batch}</Text>
                {node.dependsOn.length > 0 && <Text dimColor> ← {node.dependsOn.join('、')}</Text>}
              </Box>
            ))}
          </Box>
        )}
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
          <Text dimColor>每 {Math.round(GIT_POLL_MS / 1000)} 秒自动刷新；在仓库根或其子目录打开会话即可。</Text>
        </Box>
      )
    }

    return (
      <Box flexDirection="column">
        <Box flexDirection="row">
          <Text bold>{status.branch}</Text>
          {status.upstream !== null && <Text dimColor> → {status.upstream}</Text>}
          {status.ahead > 0 && <Text color="green"> ↑{status.ahead}</Text>}
          {status.behind > 0 && <Text color="yellow"> ↓{status.behind}</Text>}
        </Box>
        {(status.added > 0 || status.removed > 0) && (
          <Box>
            {status.added > 0 && <Text color="green">+{status.added}</Text>}
            {status.removed > 0 && <Text color="red"> −{status.removed}</Text>}
            <Text dimColor> 行级改动（tracked 合计）</Text>
          </Box>
        )}
        {isGitQuiet(status) && <Text color="green">✓ 工作区干净，与上游同步</Text>}
        {status.conflicts.length > 0 && (
          <Box flexDirection="column">
            <Text bold color="red">
              ▍冲突（{status.conflicts.length}）
            </Text>
            {status.conflicts.slice(0, MAX_GIT_FILES).map(file => (
              <Text key={file.path} color="red">
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
              <Text key={file.path} color="green">
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
              <Text key={file.path} color="yellow">
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
              <Text key={file.path} dimColor>
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
    const report = await read($, execution)
    const scope = await read($, batchScope)
    const git = await read($, gitStatus)
    // 工作区干净且与上游同步时不占横条
    const gitLine = git !== null && !isGitQuiet(git) ? git : null
    if (report === null && scope === null && gitLine === null) return next(e)
    const { counts, lines } = gitLine === null ? { counts: null, lines: null } : gitSummaryParts(gitLine)
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
        {gitLine !== null && (
          <Box>
            <Text dimColor>▸ git </Text>
            <Text>{gitLine.branch}</Text>
            {gitLine.ahead > 0 && <Text color="green"> ↑{gitLine.ahead}</Text>}
            {gitLine.behind > 0 && <Text color="yellow"> ↓{gitLine.behind}</Text>}
            {gitLine.conflicts.length > 0 && (
              <Text color="red"> · ✗冲突{gitLine.conflicts.length}</Text>
            )}
            {counts !== null && <Text dimColor> · {counts}</Text>}
            {lines !== null && <Text dimColor> · {lines}</Text>}
          </Box>
        )}
      </Box>
    )
  })
}
