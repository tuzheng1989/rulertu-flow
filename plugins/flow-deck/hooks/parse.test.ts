import { describe, expect, test } from 'claude-code/testing'

import {
  buildPlanReview,
  countIssues,
  depStatuses,
  extractRound,
  guardDecision,
  isPassing,
  normalizePath,
  parseBatchScope,
  parseDepGraph,
  parseExecution,
  parseReviewJson,
  parseStateJson,
  sparkline,
} from './parse'
import type { BatchScope } from '../types'

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

  test('parseExecution 校验上报并容错 store 旧值', () => {
    const full = parseExecution({
      plan: 'demo',
      batch: 'B2',
      phase: '执行',
      tLevel: 'T1',
      testsPassed: 12,
      testsTotal: 15,
      evidenceDir: 'plans/.flow-evidence',
      updatedAt: 1000,
    })
    expect(full).toEqual({
      plan: 'demo',
      batch: 'B2',
      phase: '执行',
      tLevel: 'T1',
      testsPassed: 12,
      testsTotal: 15,
      evidenceDir: 'plans/.flow-evidence',
      updatedAt: 1000,
    })
    // 必填缺失
    expect(parseExecution({ plan: 'demo' })).toBe(null)
    expect(parseExecution({ plan: '', batch: 'B1', phase: '开工' })).toBe(null)
    // store 旧值：updatedAt 缺失补 0，未知字段忽略
    expect(parseExecution({ plan: 'p', batch: 'B1', phase: '收口' })).toEqual({
      plan: 'p',
      batch: 'B1',
      phase: '收口',
      updatedAt: 0,
    })
    // 类型不符
    expect(parseExecution(null)).toBe(null)
    expect(parseExecution([1])).toBe(null)
    expect(parseExecution('x')).toBe(null)
    // 字段类型错则忽略该可选字段，不整体拒绝
    expect(parseExecution({ plan: 'p', batch: 'B1', phase: '开工', testsTotal: '5' })).toEqual({
      plan: 'p',
      batch: 'B1',
      phase: '开工',
      updatedAt: 0,
    })
  })

  test('normalizePath 归一化分隔符并剥工作目录前缀', () => {
    const cwd = 'C:\\Users\\tuzhe\\repo'
    expect(normalizePath('src\\app.ts', cwd)).toBe('src/app.ts')
    expect(normalizePath('C:\\Users\\TUZHE\\repo\\src\\app.ts', cwd)).toBe('src/app.ts')
    expect(normalizePath('C:/Users/tuzhe/repo/src/app.ts', 'C:/Users/tuzhe/repo/')).toBe(
      'src/app.ts',
    )
    // 非工作目录下的路径原样（仅分隔符归一）
    expect(normalizePath('C:\\other\\a.ts', cwd)).toBe('C:/other/a.ts')
    expect(normalizePath('src/a.ts', '')).toBe('src/a.ts')
  })

  test('parseBatchScope 校验边界声明', () => {
    const scope = parseBatchScope({ plan: 'demo', batch: 'B2', files: ['a.ts', 'b.ts'] })
    expect(scope).toEqual({ plan: 'demo', batch: 'B2', files: ['a.ts', 'b.ts'] })
    // files 中非字符串与空串被过滤
    expect(parseBatchScope({ plan: 'p', batch: 'B1', files: ['a.ts', 3, ''] })).toEqual({
      plan: 'p',
      batch: 'B1',
      files: ['a.ts'],
    })
    expect(parseBatchScope({ plan: 'p', batch: 'B1' })).toBe(null)
    expect(parseBatchScope({ plan: 'p', batch: 'B1', files: 'a.ts' })).toBe(null)
    expect(parseBatchScope({ plan: '', batch: 'B1', files: [] })).toBe(null)
    expect(parseBatchScope('x')).toBe(null)
  })

  test('guardDecision 判定越界并归一化比较', () => {
    const cwd = 'C:\\repo'
    const scope: BatchScope = {
      plan: 'demo',
      batch: 'B2',
      files: ['src\\a.ts', 'C:/repo/lib/b.ts'],
    }
    // 未声明边界放行
    expect(guardDecision(null, 'Edit', { file_path: 'x.ts' }, cwd)).toEqual({ kind: 'pass' })
    // 非文件写入工具放行
    expect(guardDecision(scope, 'Bash', { command: 'ls' }, cwd)).toEqual({ kind: 'pass' })
    // 界内（含反斜杠声明、绝对路径声明、大小写差异）
    expect(guardDecision(scope, 'Edit', { file_path: 'C:\\repo\\src\\a.ts' }, cwd)).toEqual({
      kind: 'pass',
    })
    expect(guardDecision(scope, 'Write', { file_path: 'LIB\\B.TS' }, cwd)).toEqual({ kind: 'pass' })
    // 越界：保留调用方原样路径供提示
    expect(guardDecision(scope, 'Edit', { file_path: 'C:\\repo\\other\\c.ts' }, cwd)).toEqual({
      kind: 'outOfScope',
      path: 'C:\\repo\\other\\c.ts',
    })
    // file_path 缺失或空放行
    expect(guardDecision(scope, 'Edit', {}, cwd)).toEqual({ kind: 'pass' })
    expect(guardDecision(scope, 'Edit', { file_path: '' }, cwd)).toEqual({ kind: 'pass' })
  })

  test('parseDepGraph 校验波次依赖声明', () => {
    const graph = parseDepGraph({
      plan: 'demo',
      batches: [
        { batch: 'B1', dependsOn: [] },
        { batch: 'B2', dependsOn: ['B1'] },
        { batch: 'B3', dependsOn: ['B1', 3, ''] },
        { batch: '' },
        'junk',
      ],
    })
    expect(graph).toEqual({
      plan: 'demo',
      batches: [
        { batch: 'B1', dependsOn: [] },
        { batch: 'B2', dependsOn: ['B1'] },
        { batch: 'B3', dependsOn: ['B1'] },
      ],
    })
    expect(parseDepGraph({ plan: 'p', batches: 'x' })).toBe(null)
    expect(parseDepGraph({ batches: [] })).toBe(null)
    expect(parseDepGraph(null)).toBe(null)
  })

  test('depStatuses 按 progress 标注三态', () => {
    const graph = parseDepGraph({
      plan: 'demo',
      batches: [{ batch: 'B1', dependsOn: [] }, { batch: 'B2', dependsOn: ['B1'] }],
    })
    if (graph === null) throw new Error('fixture 不可为 null')
    // 无记录全部待执行
    expect(depStatuses(graph, {})).toEqual([
      { batch: 'B1', dependsOn: [], status: 'pending' },
      { batch: 'B2', dependsOn: ['B1'], status: 'pending' },
    ])
    // 收口=完成；其他阶段=进行中；其他方案的记录不影响
    const progress = { 'demo#B1': '收口', 'demo#B2': '执行', 'other#B1': '收口' }
    expect(depStatuses(graph, progress)).toEqual([
      { batch: 'B1', dependsOn: [], status: 'done' },
      { batch: 'B2', dependsOn: ['B1'], status: 'active' },
    ])
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
