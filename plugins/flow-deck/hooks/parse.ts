import type { PlanReview, ReviewRound } from '../types'

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
  const latest = rounds.length > 0 ? rounds[rounds.length - 1] : null
  return {
    name,
    dir,
    backend: state?.backend,
    round: state?.round ?? (latest === null ? 0 : latest.round),
    rounds,
    passed: latest !== null && isPassing(latest.score, latest),
  }
}
