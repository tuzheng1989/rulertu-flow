import type { BatchScope, ExecutionReport, PlanReview, ReviewRound } from '../types'

/** plan-iterate 的达标线：最新轮评分不低于它且无 P0/P1 问题 */
export const PASS_SCORE = 8.5

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
  | { kind: 'outOfScope'; path: string }

/** 判定一次文件写入是否越出批次边界；未声明边界或非文件写入工具一律放行 */
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
  return keys.has(target) ? { kind: 'pass' } : { kind: 'outOfScope', path: record.file_path }
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
