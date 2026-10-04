import { describe, expect, test } from 'claude-code/testing'

import {
  buildPlanReview,
  countIssues,
  extractRound,
  isPassing,
  parseReviewJson,
  parseStateJson,
  sparkline,
} from './parse'

describe('parse', () => {
  test('extractRound 认识 review-RN.json', () => {
    expect(extractRound('review-R1.json')).toBe(1)
    expect(extractRound('review-R12.json')).toBe(12)
    expect(extractRound('state.json')).toBe(null)
    expect(extractRound('review-R1.log')).toBe(null)
  })

  test('countIssues 按 P0/P1/P2 统计，未知 severity 忽略', () => {
    const counts = countIssues([
      { severity: 'P0' },
      { severity: 'P0' },
      { severity: 'P1' },
      { severity: 'P2' },
      { severity: 'P2' },
      { severity: 'P2' },
      { severity: 'X' },
    ])
    expect(counts).toEqual({ p0: 2, p1: 1, p2: 3 })
    expect(countIssues([])).toEqual({ p0: 0, p1: 0, p2: 0 })
  })

  test('isPassing 要求达标分且无 P0/P1', () => {
    expect(isPassing(8.5, { p0: 0, p1: 0, p2: 2 })).toBe(true)
    expect(isPassing(9, { p0: 0, p1: 0, p2: 0 })).toBe(true)
    expect(isPassing(9, { p0: 1, p1: 0, p2: 0 })).toBe(false)
    expect(isPassing(9, { p0: 0, p1: 1, p2: 0 })).toBe(false)
    expect(isPassing(8.4, { p0: 0, p1: 0, p2: 0 })).toBe(false)
  })

  test('parseReviewJson 解析合法输入、拒绝坏 JSON 与缺字段', () => {
    const good = parseReviewJson(
      JSON.stringify({ score: 8.7, issues: [{ severity: 'P2' }, { severity: 'P2' }] }),
      2,
    )
    expect(good).toEqual({ round: 2, score: 8.7, p0: 0, p1: 0, p2: 2 })
    expect(parseReviewJson('{broken', 1)).toBe(null)
    expect(parseReviewJson(JSON.stringify({ issues: [] }), 1)).toBe(null)
    expect(parseReviewJson(JSON.stringify({ score: '9' }), 1)).toBe(null)
  })

  test('parseStateJson 提取 backend 与 round，忽略其余字段', () => {
    const state = parseStateJson(
      JSON.stringify({ backend: 'codex', round: 3, plan_path: 'p.md', plan_sha256: 'x' }),
    )
    expect(state).toEqual({ backend: 'codex', round: 3 })
    expect(parseStateJson('[]')).toBe(null)
    expect(parseStateJson('nope')).toBe(null)
  })

  test('sparkline 把 0-10 分映射为方块字符并夹紧边界', () => {
    // 5 分 → round(3.5) = 4 → '▅'；10 分夹紧到下标 7 → '█'
    expect(sparkline([0, 5, 10])).toBe('▁▅█')
    expect(sparkline([])).toBe('')
  })

  test('buildPlanReview 组装概览并以最新轮判定达标', () => {
    const plan = buildPlanReview(
      'demo',
      '.plan-iterate/demo',
      JSON.stringify({ backend: 'codex', round: 2 }),
      [
        { round: 2, text: JSON.stringify({ score: 8.7, issues: [{ severity: 'P2' }] }) },
        {
          round: 1,
          text: JSON.stringify({ score: 7.0, issues: [{ severity: 'P0' }, { severity: 'P1' }] }),
        },
      ],
    )
    expect(plan.name).toBe('demo')
    expect(plan.backend).toBe('codex')
    expect(plan.round).toBe(2)
    expect(plan.rounds.map(round => round.round)).toEqual([1, 2])
    expect(plan.passed).toBe(true)

    // 无 state.json 时轮次回退到最新评审轮；最新轮有 P1 则不达标
    const failing = buildPlanReview('old', '.plan-iterate/old', null, [
      { round: 1, text: JSON.stringify({ score: 9, issues: [{ severity: 'P1' }] }) },
    ])
    expect(failing.round).toBe(1)
    expect(failing.passed).toBe(false)

    // 只有 state.json、评审尚未落盘：不达标，轮次取自 state
    const pending = buildPlanReview('new', '.plan-iterate/new', JSON.stringify({ round: 3 }), [])
    expect(pending.round).toBe(3)
    expect(pending.rounds).toEqual([])
    expect(pending.passed).toBe(false)
  })
})
