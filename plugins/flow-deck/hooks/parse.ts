import type {
  BatchDep,
  BatchScope,
  DepGraph,
  ExecutionReport,
  FlowTask,
  FsEntryLike,
  GitFileState,
  GitStatus,
  PlanReview,
  ReviewRound,
} from '../types'

/** plan-iterate 的达标线：最新轮评分不低于它且无 P0/P1 问题 */
export const PASS_SCORE = 8.5

type FlowData = {
  plans: PlanReview[]
  report: ExecutionReport | null
  scope: BatchScope | null
  graph: DepGraph | null
}

/** 面板与横条共用当前任务口径；存量记录不能激活任务。 */
export function selectTaskView(task: FlowTask | null, data: FlowData): FlowData {
  const implementing = task?.kind === 'implement'
  const matchesBatch = (value: { plan: string; batch: string } | null) =>
    implementing && value !== null && value.plan === task.plan &&
    (task.batch === undefined || value.batch === task.batch)
  return {
    plans: task?.kind === 'iterate' ? data.plans.filter(plan => plan.name === task.plan) : [],
    report: matchesBatch(data.report) && data.report?.phase !== '收口' ? data.report : null,
    scope: matchesBatch(data.scope) ? data.scope : null,
    graph: implementing && data.graph?.plan === task.plan ? data.graph : null,
  }
}

/** 固定长度静态进度条，无动画或逐帧更新。 */
export function progressBar(value: number, total: number, width = 10): string {
  const ratio = total > 0 && Number.isFinite(value) && Number.isFinite(total)
    ? Math.max(0, Math.min(1, value / total)) : 0
  const filled = Math.round(ratio * width)
  return '━'.repeat(filled) + '─'.repeat(width - filled)
}

/** 评审达标刻度条：`▏` 固定在达标线位置（由 pass 决定，不随 score 移动），实格随 score 伸缩。 */
export function scoreGauge(score: number, width = 10, pass = PASS_SCORE): string {
  const clamp = (value: number) => (Number.isFinite(value) ? Math.max(0, Math.min(10, value)) : 0)
  const filled = Math.round((clamp(score) / 10) * width)
  const gauge = '━'.repeat(filled) + '─'.repeat(width - filled)
  const at = Math.max(0, Math.min(width, Math.round((clamp(pass) / 10) * width)))
  return gauge.slice(0, at) + '▏' + gauge.slice(at)
}

/** 流水线连线状态序列：连线状态 = 右侧节点状态（流向由下游决定）；单节点或空图无连线。 */
export function pipelineLinks(nodes: readonly DepNode[]): DepNodeStatus[] {
  return nodes.slice(1).map(node => node.status)
}

/** 目录浏览排序：目录在前，各自按名称字典序。 */
export function sortEntries(entries: readonly FsEntryLike[]): FsEntryLike[] {
  return [...entries].sort((a, b) =>
    a.kind === b.kind ? a.name.localeCompare(b.name) : a.kind === 'dir' ? -1 : 1)
}

/** 统一改动清单的一行：touched 为本会话 agent 改动，state 为 git 状态（无则 null） */
export type ChangeState = 'conflict' | 'staged' | 'unstaged' | 'untracked'

export type ChangeRow = {
  path: string
  touched: boolean
  state: ChangeState | null
}

/** Spinner 行的重写词；null 表示无话可说（钩子透传引擎原样） */
export function spinnerWord(
  task: FlowTask | null,
  report: ExecutionReport | null,
  plan: PlanReview | undefined,
  running: readonly { name?: string; description?: string; id?: string }[],
): string | null {
  if (task === null) {
    if (running.length === 0) return null
    if (running.length === 1) {
      const one = running[0]
      const name = one.name || one.description || one.id
      const desc = one.name && one.description ? ` · ${one.description}` : ''
      // Spinner 词过长会挤压引擎附带的时长与 token 计数，截断兜底
      return `↻ ${name}${desc}`.slice(0, 40)
    }
    return `↻ ${running.length} 个子代理运行中`
  }
  if (task.kind === 'implement') {
    if (report === null || report.phase === '收口') return null
    // 阶段名已是「验证」时计数直接跟在后面，避免「验证 · 验证」重复
    const tests = report.testsTotal === undefined ? ''
      : ` · ${report.phase === '验证' ? '' : '验证 '}${report.testsPassed ?? 0}/${report.testsTotal}`
    return `${report.batch} · ${report.phase}${tests}`
  }
  if (plan === undefined) return `评审 ${task.plan}`
  const latest = plan.rounds.at(-1) ?? null
  return latest === null
    ? `评审 R${plan.round} 进行中`
    : `评审 R${latest.round} · ${latest.score} 分`
}

/** Edit/Write 工具行的批次标注；null 表示界内或无活动边界（不加标注） */
export type ToolMark = { text: string; tone: 'accent' | 'warn' | 'bad' }

export function toolMark(
  active: boolean,
  outOfScope: boolean,
  guardMode: 'warn' | 'deny',
): ToolMark | null {
  if (!active || !outOfScope) return null
  return guardMode === 'deny'
    ? { text: `${'✗'} 拦截`, tone: 'bad' }
    : { text: `${'⚠'} 越界`, tone: 'warn' }
}

/** 输入框守卫预览的一段装饰：草稿中带扩展名的路径 token 及其是否落在批次边界内 */
export type DraftDecoration = { start: number; end: number; inScope: boolean }

/** 草稿中路径样式 token（含扩展名才判定，避免误高亮普通词）的守卫预览判定；
 *  cwd 与守卫判定同基准（token 写绝对路径时同样剥前缀），保证预览与拦截口径一致 */
export function draftDecorations(text: string, scopeKeys: ReadonlySet<string>, cwd = ''): DraftDecoration[] {
  const out: DraftDecoration[] = []
  const re = /[A-Za-z0-9_.\-\\/]+\.[A-Za-z]{1,6}/g
  let match: RegExpExecArray | null
  while ((match = re.exec(text)) !== null) {
    const key = normalizePath(match[0], cwd).toLowerCase()
    out.push({ start: match.index, end: match.index + match[0].length, inScope: scopeKeys.has(key) })
  }
  return out
}

/** 毫秒时长的短格式（3.2s / 1m 4s），与宿主回合行的口径相近 */
export function humanDuration(ms: number): string {
  if (!Number.isFinite(ms) || ms < 0) return '0s'
  const seconds = ms / 1000
  if (seconds < 60) return Number.isInteger(seconds) ? `${seconds}s` : `${seconds.toFixed(1)}s`
  // 整秒后再 divmod，避免 59.5s 以上被进位成「x m 60s」
  const total = Math.round(seconds)
  return `${Math.floor(total / 60)}m ${total % 60}s`
}

/** 同一路径多 git 状态时取行动意义更靠前的（冲突 > 未暂存 > 暂存 > 未跟踪） */
const STATE_RANK: Record<ChangeState, number> = { conflict: 0, unstaged: 1, staged: 2, untracked: 3 }

/** 统一改动清单：git 四组文件 ∪ 本会话记录，路径小写折叠去重（会话记录保留首见原样路径）。
 *  git 为 null 时退化为会话清单（state 全 null）。排序：会话组在前、冲突优先、路径字典序。 */
export function collectChanges(
  git: GitStatus | null,
  touched: readonly { path: string }[],
): ChangeRow[] {
  const byKey = new Map<string, ChangeRow>()
  const addGit = (files: readonly GitFileState[], state: ChangeState) => {
    for (const file of files) {
      const key = file.path.toLowerCase()
      const existing = byKey.get(key)
      if (existing === undefined || existing.state === null ||
          STATE_RANK[state] < STATE_RANK[existing.state]) {
        byKey.set(key, { path: existing?.path ?? file.path, touched: existing?.touched ?? false, state })
      }
    }
  }
  if (git !== null) {
    addGit(git.conflicts, 'conflict')
    addGit(git.staged, 'staged')
    addGit(git.unstaged, 'unstaged')
    addGit(git.untracked, 'untracked')
  }
  for (const one of touched) {
    const key = one.path.toLowerCase()
    const existing = byKey.get(key)
    if (existing === undefined) byKey.set(key, { path: one.path, touched: true, state: null })
    else byKey.set(key, { ...existing, touched: true })
  }
  return [...byKey.values()].sort((a, b) =>
    a.touched !== b.touched ? (a.touched ? -1 : 1)
      : (a.state === 'conflict') !== (b.state === 'conflict') ? (a.state === 'conflict' ? -1 : 1)
        : a.path.localeCompare(b.path))
}

/** 五阶段序进度：index 从 1 计（完成比例 index/total）；未知阶段无序号（total 0，渲染退化为纯文字） */
export type PhaseProgress = {
  current: string
  index: number
  total: number
}

/** 执行上报的极简进度条数据：`progressBar(index, total)` 即条，右侧 `current · index/total` */
export function phaseProgress(phase: string): PhaseProgress {
  const phases = ['开工', '派单', '执行', '验证', '收口']
  const index = phases.indexOf(phase)
  return { current: phase, index: index === -1 ? 0 : index + 1, total: index === -1 ? 0 : phases.length }
}

/** 评分趋势条可用的 Unicode 方块字符，下标 0（▁）到 7（█） */
const BLOCKS = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█'] as const

export type SeverityCounts = {
  p0: number
  p1: number
  p2: number
}

/** 从文件名提取评审轮次：review-R2.json → 2；其余返回 null */
export function extractRound(fileName: string): number | null {
  const match = /^review-R(\d+)\.json$/.exec(fileName)
  return match === null ? null : Number(match[1])
}

/** 按 P0/P1/P2 统计问题数；未知 severity 忽略 */
export function countIssues(issues: readonly unknown[]): SeverityCounts {
  const counts = { p0: 0, p1: 0, p2: 0 }
  for (const issue of issues) {
    const severity = (issue as { severity?: unknown } | null)?.severity
    if (severity === 'P0') counts.p0 += 1
    else if (severity === 'P1') counts.p1 += 1
    else if (severity === 'P2') counts.p2 += 1
  }
  return counts
}

/** 达标判定：最新轮 score >= 8.5 且无 P0/P1 */
export function isPassing(score: number, counts: SeverityCounts): boolean {
  return score >= PASS_SCORE && counts.p0 === 0 && counts.p1 === 0
}

/** 解析 review-RN.json 文本；坏 JSON 或结构不符返回 null */
export function parseReviewJson(text: string, round: number): ReviewRound | null {
  let data: unknown
  try {
    data = JSON.parse(text)
  } catch {
    return null
  }
  if (typeof data !== 'object' || data === null) return null
  const record = data as { score?: unknown; issues?: unknown }
  if (typeof record.score !== 'number' || !Array.isArray(record.issues)) return null
  return { round, score: record.score, ...countIssues(record.issues) }
}

export type PlanState = {
  backend?: string
  round?: number
}

/** 解析 state.json 文本；坏 JSON 或结构不符（含数组）返回 null */
export function parseStateJson(text: string): PlanState | null {
  let data: unknown
  try {
    data = JSON.parse(text)
  } catch {
    return null
  }
  if (typeof data !== 'object' || data === null || Array.isArray(data)) return null
  const record = data as { backend?: unknown; round?: unknown }
  const state: PlanState = {}
  if (typeof record.backend === 'string') state.backend = record.backend
  if (typeof record.round === 'number') state.round = record.round
  return state
}

/** 评分趋势条：每轮一个字符，0-10 分映射到 ▁-█ */
export function sparkline(scores: readonly number[]): string {
  return scores
    .map(score => BLOCKS[Math.max(0, Math.min(7, Math.round((score / 10) * 7)))])
    .join('')
}

/** 校验并归一化 flow_report 上报（来自模型工具入参或 $.store 旧值），不符返回 null */
export function parseExecution(value: unknown): ExecutionReport | null {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return null
  const record = value as Record<string, unknown>
  if (typeof record.plan !== 'string' || record.plan === '') return null
  if (typeof record.batch !== 'string' || record.batch === '') return null
  if (typeof record.phase !== 'string' || record.phase === '') return null
  const report: ExecutionReport = {
    plan: record.plan,
    batch: record.batch,
    phase: record.phase,
    updatedAt: typeof record.updatedAt === 'number' ? record.updatedAt : 0,
  }
  if (typeof record.tLevel === 'string') report.tLevel = record.tLevel
  if (typeof record.testsPassed === 'number') report.testsPassed = record.testsPassed
  if (typeof record.testsTotal === 'number') report.testsTotal = record.testsTotal
  if (typeof record.evidenceDir === 'string') report.evidenceDir = record.evidenceDir
  return report
}

/** 校验并归一化 flow_batch 边界声明，不符返回 null */
export function parseBatchScope(value: unknown): BatchScope | null {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return null
  const record = value as Record<string, unknown>
  if (typeof record.plan !== 'string' || record.plan === '') return null
  if (typeof record.batch !== 'string' || record.batch === '') return null
  if (!Array.isArray(record.files)) return null
  const files = record.files.filter((file): file is string => typeof file === 'string' && file !== '')
  return { plan: record.plan, batch: record.batch, files }
}

/** 路径归一化：反斜杠转正斜杠；绝对路径剥掉工作目录前缀（大小写不敏感比较） */
export function normalizePath(path: string, cwd: string): string {
  const unified = path.replace(/\\/g, '/')
  const cwdUnified = cwd.replace(/\\/g, '/').replace(/\/+$/, '')
  if (cwdUnified !== '' && unified.toLowerCase().startsWith(`${cwdUnified.toLowerCase()}/`)) {
    return unified.slice(cwdUnified.length + 1)
  }
  return unified
}

export type GuardDecision =
  | { kind: 'pass' }
  | { kind: 'outOfScope'; path: string; key: string }

/** 判定一次文件写入是否越出批次边界；未声明边界或非文件写入工具一律放行。
 *  key 为去重用归一化小写路径，与界内比较同口径；path 保留调用方原样路径供提示 */
export function guardDecision(
  scope: BatchScope | null,
  tool: string,
  input: unknown,
  cwd: string,
): GuardDecision {
  if (scope === null) return { kind: 'pass' }
  if (tool !== 'Edit' && tool !== 'Write') return { kind: 'pass' }
  const record = (typeof input === 'object' && input !== null ? input : {}) as Record<string, unknown>
  if (typeof record.file_path !== 'string' || record.file_path === '') return { kind: 'pass' }
  const keys = new Set(scope.files.map(file => normalizePath(file, cwd).toLowerCase()))
  const target = normalizePath(record.file_path, cwd).toLowerCase()
  return keys.has(target) ? { kind: 'pass' } : { kind: 'outOfScope', path: record.file_path, key: target }
}

/** 校验并归一化 flow_deps 波次依赖声明，不符返回 null */
export function parseDepGraph(value: unknown): DepGraph | null {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return null
  const record = value as Record<string, unknown>
  if (typeof record.plan !== 'string' || record.plan === '') return null
  if (!Array.isArray(record.batches)) return null
  const batches = []
  for (const entry of record.batches) {
    if (typeof entry !== 'object' || entry === null) continue
    const node = entry as Record<string, unknown>
    if (typeof node.batch !== 'string' || node.batch === '') continue
    const dependsOn = Array.isArray(node.dependsOn)
      ? node.dependsOn.filter((dep): dep is string => typeof dep === 'string' && dep !== '')
      : []
    batches.push({ batch: node.batch, dependsOn })
  }
  return { plan: record.plan, batches }
}

export type DepNodeStatus = 'done' | 'active' | 'pending'

export type DepNode = BatchDep & {
  status: DepNodeStatus
}

/** 结合各批阶段记录标注状态：收口=完成，有记录=进行中，未上报=待执行 */
export function depStatuses(graph: DepGraph, progress: Record<string, string>): DepNode[] {
  return graph.batches.map(node => {
    const phase = progress[`${graph.plan}#${node.batch}`]
    if (phase === undefined) return { ...node, status: 'pending' as const }
    return { ...node, status: phase === '收口' ? ('done' as const) : ('active' as const) }
  })
}

/** 组装一个方案的评审概览；stateText 为 null 时仅靠评审文件推导 */
export function buildPlanReview(
  name: string,
  dir: string,
  stateText: string | null,
  reviews: readonly { round: number; text: string }[],
): PlanReview {
  const rounds = reviews
    .map(review => parseReviewJson(review.text, review.round))
    .filter((round): round is ReviewRound => round !== null)
    .sort((a, b) => a.round - b.round)
  const state = stateText === null ? null : parseStateJson(stateText)
  const latest = rounds.at(-1) ?? null
  return {
    name,
    dir,
    backend: state?.backend,
    round: state?.round ?? (latest === null ? 0 : latest.round),
    rounds,
    passed: latest !== null && isPassing(latest.score, latest),
  }
}

/** 横条展示的方案：名字排序的最后一个未达标方案；全部达标或无方案时为 null（横条撤下） */
export function bannerPlan(plans: readonly PlanReview[]): PlanReview | null {
  return plans.filter(plan => !plan.passed).at(-1) ?? null
}

/** git status --porcelain=v1 -b 的一行原始文件记录（分类前） */
export type PorcelainFile = {
  /** 原始 XY 码 */
  code: string
  /** 文件路径（rename 为新路径；带引号输出已剥引号） */
  path: string
  /** rename 原路径 */
  oldPath?: string
}

/** git status --porcelain=v1 -b 头行与文件行的解析结果 */
export type PorcelainStatus = {
  branch: string
  upstream: string | null
  ahead: number
  behind: number
  files: PorcelainFile[]
}

/** 合并冲突的 XY 码全集 */
const CONFLICT_CODES = new Set(['UU', 'AA', 'DD', 'AU', 'UA', 'DU', 'UD'])

/** 剥 porcelain 输出对特殊路径加的引号（quotePath=false 下仅含控制字符等罕见路径仍带） */
function unquotePath(path: string): string {
  if (path.startsWith('"') && path.endsWith('"') && path.length >= 2) {
    return path.slice(1, -1)
  }
  return path
}

/** 解析 git status --porcelain=v1 -b 的 stdout；无 ## 头行（非 git 仓库输出）返回 null */
export function parsePorcelain(stdout: string): PorcelainStatus | null {
  const header = stdout.split('\n').find(line => line.startsWith('## '))
  if (header === undefined) return null

  // 头行变体：## main / ## main...origin/main [ahead 2, behind 1] /
  // ## No commits yet on main（unborn）/ ## HEAD (no branch)（detached）
  const body = header.slice(3).trim()
  let branch: string
  let upstream: string | null = null
  let ahead = 0
  let behind = 0
  if (body === 'HEAD (no branch)') {
    branch = 'HEAD*'
  } else if (body.startsWith('No commits yet on ')) {
    branch = body.slice('No commits yet on '.length)
  } else {
    const dots = body.indexOf('...')
    if (dots === -1) {
      branch = body
    } else {
      branch = body.slice(0, dots)
      const rest = body.slice(dots + 3)
      const bracket = rest.indexOf(' [')
      upstream = bracket === -1 ? rest : rest.slice(0, bracket)
      const marks = bracket === -1 ? '' : rest.slice(bracket + 2, rest.lastIndexOf(']'))
      const aheadMatch = /\bahead (\d+)/.exec(marks)
      const behindMatch = /\bbehind (\d+)/.exec(marks)
      if (aheadMatch !== null) ahead = Number(aheadMatch[1])
      if (behindMatch !== null) behind = Number(behindMatch[1])
    }
  }

  const files: PorcelainFile[] = []
  for (const line of stdout.split('\n')) {
    if (line === '' || line.startsWith('## ')) continue
    const code = line.slice(0, 2)
    const rest = line.slice(3)
    if (rest === '') continue
    const arrow = rest.indexOf(' -> ')
    if (arrow !== -1) {
      files.push({
        code,
        path: unquotePath(rest.slice(arrow + 4)),
        oldPath: unquotePath(rest.slice(0, arrow)),
      })
    } else {
      files.push({ code, path: unquotePath(rest) })
    }
  }
  return { branch, upstream, ahead, behind, files }
}

/** 解析 git diff --numstat 的 stdout，累加行级增删；二进制行（-\t-）与非法行跳过 */
export function parseNumstat(stdout: string): { added: number; removed: number } {
  let added = 0
  let removed = 0
  for (const line of stdout.split('\n')) {
    const parts = line.split('\t')
    if (parts.length < 3) continue
    const lineAdded = Number(parts[0])
    const lineRemoved = Number(parts[1])
    if (!Number.isNaN(lineAdded)) added += lineAdded
    if (!Number.isNaN(lineRemoved)) removed += lineRemoved
  }
  return { added, removed }
}

/** 组装 git 状态快照：XY 码分类 + 两次 numstat 合计行级增删 */
export function buildGitStatus(
  porcelain: PorcelainStatus,
  worktreeNumstat: { added: number; removed: number },
  cachedNumstat: { added: number; removed: number },
  fetchedAt: number,
): GitStatus {
  const staged: GitFileState[] = []
  const unstaged: GitFileState[] = []
  const untracked: GitFileState[] = []
  const conflicts: GitFileState[] = []
  for (const file of porcelain.files) {
    if (CONFLICT_CODES.has(file.code)) {
      conflicts.push(file)
    } else if (file.code === '??') {
      untracked.push(file)
    } else {
      // charAt 越界返回空串，includes('') 为 false，免于索引 undefined
      if ('MADRC'.includes(file.code.charAt(0))) staged.push(file)
      if ('MD'.includes(file.code.charAt(1))) unstaged.push(file)
    }
  }
  return {
    branch: porcelain.branch,
    upstream: porcelain.upstream,
    ahead: porcelain.ahead,
    behind: porcelain.behind,
    staged,
    unstaged,
    untracked,
    conflicts,
    added: worktreeNumstat.added + cachedNumstat.added,
    removed: worktreeNumstat.removed + cachedNumstat.removed,
    fetchedAt,
  }
}

/** 工作区干净且与上游同步；此时横条不画 git 行 */
export function isGitQuiet(status: GitStatus): boolean {
  return (
    status.staged.length === 0 &&
    status.unstaged.length === 0 &&
    status.untracked.length === 0 &&
    status.conflicts.length === 0 &&
    status.ahead === 0 &&
    status.behind === 0
  )
}

/** 横条 git 行的计数段与行级段文案；各自无内容时为 null（冲突计数由渲染层独立红字展示） */
export function gitSummaryParts(
  status: GitStatus,
): { counts: string | null; lines: string | null } {
  const counts: string[] = []
  if (status.staged.length > 0) counts.push(`暂存${status.staged.length}`)
  if (status.unstaged.length > 0) counts.push(`改${status.unstaged.length}`)
  if (status.untracked.length > 0) counts.push(`新${status.untracked.length}`)
  let lines: string | null = null
  if (status.added > 0 && status.removed > 0) lines = `+${status.added} −${status.removed}`
  else if (status.added > 0) lines = `+${status.added}`
  else if (status.removed > 0) lines = `−${status.removed}`
  return { counts: counts.length === 0 ? null : counts.join(' '), lines }
}

/** 文档浏览面板单节渲染的行数上限；超长节截断显示，草稿行号仍用全节范围 */
export const DOC_SECTION_MAX_LINES = 60

/** 文档浏览面板全文模式的行数上限（Pane 内容超高时引擎侧可滚动） */
export const DOC_ALL_MAX_LINES = 400

/** 文档浏览面板的一个节（行号 1 起且双端包含） */
export type DocSection = {
  /** 节标题（# 号后的文字）；文档开头正文为「开头」，无标题整篇为「全文」 */
  title: string
  /** 标题层级 1-6；合成节为 0 */
  level: number
  start: number
  end: number
}

/** 按 markdown 标题把文档切为节。fenced code block 内的 # 不算标题（``` 与
 *  ~~~ 行翻转围栏状态，闭栏不校验同字符同长度）。首个标题前的正文成「开头」
 *  节（纯空白行不设节）；无标题且非空时整篇为「全文」节；空文本返回空数组。 */
export function parseSections(text: string): DocSection[] {
  const lines = text.split('\n')
  const headings: { line: number; title: string; level: number }[] = []
  let fence = false
  for (let i = 0; i < lines.length; i++) {
    if (/^ {0,3}(```|~~~)/.test(lines[i])) {
      fence = !fence
      continue
    }
    if (fence) continue
    const heading = /^ {0,3}(#{1,6}) (.*)$/.exec(lines[i])
    if (heading === null) continue
    headings.push({ line: i + 1, title: heading[2].trim() || '(无标题)', level: heading[1].length })
  }
  if (headings.length === 0) {
    if (lines.every(line => line.trim() === '')) return []
    return [{ title: '全文', level: 0, start: 1, end: lines.length }]
  }
  const sections: DocSection[] = []
  const first = headings[0].line
  if (first > 1 && lines.slice(0, first - 1).some(line => line.trim() !== '')) {
    sections.push({ title: '开头', level: 0, start: 1, end: first - 1 })
  }
  headings.forEach((heading, index) => {
    const end = index + 1 < headings.length ? headings[index + 1].line - 1 : lines.length
    sections.push({ title: heading.title, level: heading.level, start: heading.line, end })
  })
  return sections
}

// ---- 文件查看器的 markdown 图表增强（表格对齐重排 + mermaid graph TD 子集自绘） ----

/** 终端显示宽度：CJK 与全角字符计 2，其余计 1（简版 wcwidth，覆盖常用区间） */
function displayWidth(text: string): number {
  let width = 0
  for (const ch of text) {
    const code = ch.codePointAt(0) ?? 0
    const wide = code >= 0x1100 && (
      code <= 0x115f ||
      (code >= 0x2e80 && code <= 0xa4cf) ||
      (code >= 0xac00 && code <= 0xd7a3) ||
      (code >= 0xf900 && code <= 0xfaff) ||
      (code >= 0xfe30 && code <= 0xfe4f) ||
      (code >= 0xff00 && code <= 0xff60) ||
      (code >= 0xffe0 && code <= 0xffe6)
    )
    width += wide ? 2 : 1
  }
  return width
}

const TABLE_ROW = /^\s*\|.*\|\s*$/
const TABLE_SEP = /^\s*\|\s*:?-{1,}[-\s:|]*\|\s*$/

const cellsOf = (line: string): string[] =>
  line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(cell => cell.trim().replace(/\\\|/g, '|'))

/** 把 markdown 表格行（含分隔行）重排为等宽对齐的 Unicode 表格；无有效表格行时原样返回 */
export function renderAsciiTable(lines: readonly string[]): string[] {
  const rows = lines
    .filter(line => TABLE_ROW.test(line) && !TABLE_SEP.test(line))
    .map(cellsOf)
  if (rows.length === 0) return [...lines]
  const columns = Math.max(...rows.map(row => row.length))
  const widths: number[] = Array.from({ length: columns }, (_, c) =>
    Math.max(3, ...rows.map(row => displayWidth(row[c] ?? ''))))
  const border = (left: string, mid: string, right: string) =>
    left + widths.map(w => '─'.repeat(w + 2)).join(mid) + right
  const renderRow = (row: readonly string[]) =>
    '│ ' + widths.map((w, c) => {
      const cell = row[c] ?? ''
      return cell + ' '.repeat(Math.max(0, w - displayWidth(cell)))
    }).join(' │ ') + ' │'
  return [border('┌', '┬', '┐'), renderRow(rows[0]), border('├', '┼', '┤'),
    ...rows.slice(1).map(renderRow), border('└', '┴', '┘')]
}

/** mermaid 子集解析出的一个节点 */
type MermaidNode = { id: string; label: string }
/** mermaid 子集解析出的一条边 */
type MermaidEdge = { from: string; to: string }

/** 剥掉节点形状语法取标签：A[文本] / A(文本) / A */
function nodeLabel(token: string): MermaidNode {
  const m = /^([\w-]+)(?:\[([^\]]*)\]|\(([^)]*)\))?\s*$/.exec(token.trim())
  if (m === null) return { id: token.trim(), label: token.trim() }
  return { id: m[1], label: m[2] ?? m[3] ?? m[1] }
}

/** 解析 mermaid graph TD 基本子集（节点与箭头链），自绘 Unicode 分层流程图；
 *  非 TD 声明、无节点无边或含不认识的行时返回 null（调用方保持代码块原样） */
export function renderMermaidGraph(source: string): string[] | null {
  const lines = source.split('\n').map(line => line.trim())
    .filter(line => line !== '' && !line.startsWith('%%'))
  const head = /^(?:graph|flowchart)\s+(TD|TB)\s*$/i.exec(lines[0] ?? '')
  if (head === null || lines.length < 2) return null
  const nodes = new Map<string, MermaidNode>()
  const edges: MermaidEdge[] = []
  for (const line of lines.slice(1)) {
    if (/^(?:classDef|class|style|click|subgraph\b|end\s*$)/.test(line)) return null
    // 按链式箭头切分：A --> B --> C / A --- B / A -.-> B
    const segments = line.split(/\s*(?:-\.->|-->)\s*|\s*-{3,}\s*/)
    if (segments.length < 2) {
      const node = nodeLabel(line)
      if (!/^[\w-]+$/.test(node.id)) return null
      nodes.set(node.id, node)
      continue
    }
    const ids: string[] = []
    for (const token of segments) {
      const node = nodeLabel(token)
      if (!/^[\w-]+$/.test(node.id)) return null
      nodes.set(node.id, node)
      ids.push(node.id)
    }
    for (let i = 1; i < ids.length; i++) edges.push({ from: ids[i - 1], to: ids[i] })
  }
  if (nodes.size === 0 || edges.length === 0) return null

  // 分层固定点收敛：layer(to) = max(layer(from)+1)；环内未继续更新的节点保持原层
  const layer = new Map<string, number>()
  for (const id of nodes.keys()) layer.set(id, 0)
  for (let round = 0; round < nodes.size; round++) {
    let changed = false
    for (const edge of edges) {
      const next = (layer.get(edge.from) ?? 0) + 1
      if (next > (layer.get(edge.to) ?? 0)) {
        layer.set(edge.to, next)
        changed = true
      }
    }
    if (!changed) break
  }
  const layers: string[][] = []
  for (const [id, depth] of layer) {
    if (layers[depth] === undefined) layers[depth] = []
    layers[depth].push(id)
  }
  const liveLayers = layers.filter(list => list !== undefined)
  if (liveLayers.length === 0) return null

  const width = Math.max(3, ...[...nodes.values()].map(node => displayWidth(node.label)))
  const gap = 4
  const startOf = new Map<string, number>()
  for (const list of liveLayers) {
    let cursor = 0
    for (const id of list) {
      startOf.set(id, cursor)
      cursor += width + gap
    }
  }
  const totalCols = Math.max(width, ...liveLayers.map(list => list.length * (width + gap) - gap))

  const rowCount = liveLayers.length * 3 + (liveLayers.length - 1) * 2
  const grid: string[][] = Array.from({ length: rowCount }, () => Array.from({ length: totalCols }, () => ' '))
  const put = (row: number, col: number, ch: string) => {
    if (row >= 0 && row < rowCount && col >= 0 && col < totalCols) grid[row][col] = ch
  }

  const startColOf = (layerIndex: number, slot: number) => startOf.get(liveLayers[layerIndex][slot]) ?? 0
  const centerOf = (layerIndex: number, slot: number) => startColOf(layerIndex, slot) + Math.floor(width / 2)

  liveLayers.forEach((list, layerIndex) => {
    const top = layerIndex * 5
    let cursor = 0
    put(top, cursor, '┌')
    for (const _ of list) {
      for (let c = 1; c <= width; c++) put(top, cursor + c, '─')
      cursor += width
      if (cursor < totalCols) {
        for (let g = 0; g < gap; g++) put(top, cursor + g, ' ')
        put(top, cursor + Math.floor(gap / 2), '┬')
      }
      cursor += gap
    }
    put(top, Math.min(totalCols - 1, cursor), '┐')

    list.forEach((id, slot) => {
      const label = nodes.get(id)?.label ?? id
      const padLeft = Math.floor((width - displayWidth(label)) / 2)
      let cell = startColOf(layerIndex, slot) + 1
      for (let pad = 0; pad < padLeft; pad++) { put(top + 1, cell, ' '); cell += 1 }
      for (const ch of label) {
        put(top + 1, cell, ch)
        if (displayWidth(ch) === 2) { cell += 1; put(top + 1, cell, '') }
        cell += 1
      }
      for (; cell < startColOf(layerIndex, slot) + 1 + width; cell++) put(top + 1, cell, ' ')
    })

    cursor = 0
    put(top + 2, cursor, '└')
    for (const _ of list) {
      for (let c = 1; c <= width; c++) put(top + 2, cursor + c, '─')
      cursor += width
      if (cursor < totalCols) {
        for (let g = 0; g < gap; g++) put(top + 2, cursor + g, ' ')
        put(top + 2, cursor + Math.floor(gap / 2), '┴')
      }
      cursor += gap
    }
    put(top + 2, Math.min(totalCols - 1, cursor), '┘')
  })

  // 连线区：父节点底部中心下行，横向走线到子节点列，子节点顶画 ▼
  for (const edge of edges) {
    const fromLayer = layer.get(edge.from) ?? 0
    const toLayer = layer.get(edge.to) ?? 0
    if (toLayer <= fromLayer) continue
    const fromSlot = liveLayers[fromLayer].indexOf(edge.from)
    const toSlot = liveLayers[toLayer].indexOf(edge.to)
    if (fromSlot === -1 || toSlot === -1) continue
    const top = fromLayer * 5 + 3
    const bottom = toLayer * 5 - 1
    const fc = centerOf(fromLayer, fromSlot)
    const tc = centerOf(toLayer, toSlot)
    put(top, fc, '│')
    for (let row = top + 1; row < bottom; row++) put(row, fc, '│')
    if (fc === tc) {
      put(bottom, tc, '▼')
      continue
    }
    const hr = bottom - 1
    for (let row = top + 1; row < hr; row++) put(row, fc, '│')
    put(hr, fc, fc < tc ? '└' : '┘')
    for (let c = Math.min(fc, tc) + 1; c < Math.max(fc, tc); c++) put(hr, c, '─')
    put(hr, tc, fc < tc ? '┌' : '┐')
    put(bottom, tc, '▼')
  }

  return grid.map(row => row.join('').replace(/\s+$/, ''))
}

const MERMAID_FENCE = /^\s*```\s*mermaid\b/i
const CODE_FENCE = /^\s*```/

/** 文件查看器的 markdown 预处理：表格重排为等宽对齐表格，mermaid graph TD
 *  子集自绘为 Unicode 流程图（解析失败保持代码块原样），其余内容原样透传 */
/** HTML 分页式节码窗口：恒含首尾节，窗口平移补满 5 个（当前居中、靠边时窗口平移），间断处以 -1 表示省略号 */
export function pagerWindow(current: number, total: number): number[] {
  if (total <= 0) return []
  const clamp = Math.min(Math.max(current, 0), total - 1)
  const windowStart = Math.min(Math.max(clamp - 2, 0), Math.max(0, total - 5))
  const wanted = new Set<number>([0, total - 1])
  for (let i = windowStart; i < windowStart + 5 && i < total; i++) wanted.add(i)
  const list = [...wanted].sort((a, b) => a - b)
  const out: number[] = []
  for (let i = 0; i < list.length; i++) {
    if (i > 0 && list[i] - list[i - 1] > 1) out.push(-1)
    out.push(list[i])
  }
  return out
}

export function enhanceMarkdown(text: string): string {
  const lines = text.split('\n')
  const out: string[] = []
  let i = 0
  let fence = false
  while (i < lines.length) {
    if (fence) {
      out.push(lines[i])
      if (CODE_FENCE.test(lines[i])) fence = false
      i += 1
      continue
    }
    if (MERMAID_FENCE.test(lines[i])) {
      const block: string[] = [lines[i]]
      i += 1
      while (i < lines.length && !CODE_FENCE.test(lines[i])) { block.push(lines[i]); i += 1 }
      block.push(lines[i] ?? '```')
      i += 1
      const drawn = renderMermaidGraph(block.slice(1, -1).join('\n'))
      if (drawn === null) out.push(...block)
      else out.push('```', ...drawn, '```')
      continue
    }
    if (CODE_FENCE.test(lines[i])) {
      fence = true
      out.push(lines[i])
      i += 1
      continue
    }
    if (TABLE_ROW.test(lines[i]) && i + 1 < lines.length && TABLE_SEP.test(lines[i + 1])) {
      const block: string[] = []
      while (i < lines.length && TABLE_ROW.test(lines[i])) { block.push(lines[i]); i += 1 }
      out.push(...renderAsciiTable(block))
      continue
    }
    out.push(lines[i])
    i += 1
  }
  return out.join('\n')
}
