import type {
  BatchDep,
  BatchScope,
  DepGraph,
  ExecutionReport,
  FlowTask,
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
