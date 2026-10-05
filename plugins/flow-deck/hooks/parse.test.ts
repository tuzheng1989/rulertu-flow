import { describe, expect, test } from 'claude-code/testing'

import {
  buildGitStatus,
  buildPlanReview,
  countIssues,
  depStatuses,
  extractRound,
  guardDecision,
  gitSummaryParts,
  isGitQuiet,
  isPassing,
  normalizePath,
  parseBatchScope,
  parseDepGraph,
  parseExecution,
  parseNumstat,
  parsePorcelain,
  parseReviewJson,
  parseStateJson,
  sparkline,
} from './parse'
import type { BatchScope, GitStatus } from '../types'

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

  test('parsePorcelain 解析各头行变体', () => {
    // 无上游
    expect(parsePorcelain('## main\n')).toEqual({
      branch: 'main',
      upstream: null,
      ahead: 0,
      behind: 0,
      files: [],
    })
    // 有上游 + ahead/behind
    expect(parsePorcelain('## main...origin/main [ahead 2, behind 1]\n')).toEqual({
      branch: 'main',
      upstream: 'origin/main',
      ahead: 2,
      behind: 1,
      files: [],
    })
    // 有上游无偏差
    expect(parsePorcelain('## dev...origin/dev\n M a.ts\n')).toMatchObject({
      branch: 'dev',
      upstream: 'origin/dev',
      ahead: 0,
      behind: 0,
    })
    // unborn 分支
    expect(parsePorcelain('## No commits yet on main\n')).toEqual({
      branch: 'main',
      upstream: null,
      ahead: 0,
      behind: 0,
      files: [],
    })
    // detached HEAD
    expect(parsePorcelain('## HEAD (no branch)\n')).toMatchObject({
      branch: 'HEAD*',
      upstream: null,
    })
    // 非 git 输出（无头行）拒绝
    expect(parsePorcelain('fatal: not a git repository\n')).toBe(null)
    expect(parsePorcelain('')).toBe(null)
  })

  test('parsePorcelain 按 XY 码收集文件行', () => {
    const parsed = parsePorcelain(
      [
        '## main',
        '?? new.txt',
        ' M work.ts',
        'M  staged.ts',
        'MM both.ts',
        'A  added.ts',
        'D  gone.ts',
        ' D unstaged-del.ts',
        'R  old.ts -> renamed.ts',
        'UU conflict.ts',
      ].join('\n') + '\n',
    )
    if (parsed === null) throw new Error('fixture 不可为 null')
    expect(parsed.files).toEqual([
      { code: '??', path: 'new.txt' },
      { code: ' M', path: 'work.ts' },
      { code: 'M ', path: 'staged.ts' },
      { code: 'MM', path: 'both.ts' },
      { code: 'A ', path: 'added.ts' },
      { code: 'D ', path: 'gone.ts' },
      { code: ' D', path: 'unstaged-del.ts' },
      { code: 'R ', path: 'renamed.ts', oldPath: 'old.ts' },
      { code: 'UU', path: 'conflict.ts' },
    ])
  })

  test('parsePorcelain 剥带引号路径的引号', () => {
    const parsed = parsePorcelain('## main\n?? "path with space.txt"\n')
    if (parsed === null) throw new Error('fixture 不可为 null')
    expect(parsed.files).toEqual([{ code: '??', path: 'path with space.txt' }])
  })

  test('parseNumstat 累加行级增删并跳过二进制', () => {
    expect(parseNumstat('5\t3\ta.ts\n12\t0\tb.ts\n')).toEqual({ added: 17, removed: 3 })
    expect(parseNumstat('-\t-\tbinary.png\n2\t1\tc.ts\n')).toEqual({ added: 2, removed: 1 })
    expect(parseNumstat('')).toEqual({ added: 0, removed: 0 })
    expect(parseNumstat('junk line\n')).toEqual({ added: 0, removed: 0 })
  })

  test('buildGitStatus 组装快照并按 XY 分类', () => {
    const porcelain = parsePorcelain(
      [
        '## main...origin/main [ahead 1, behind 2]',
        '?? fresh.txt',
        ' M work.ts',
        'M  staged.ts',
        'A  added.ts',
        'R  old.ts -> renamed.ts',
        ' D del-later.ts',
        'UU clash.ts',
      ].join('\n') + '\n',
    )
    if (porcelain === null) throw new Error('fixture 不可为 null')
    const status: GitStatus = buildGitStatus(porcelain, { added: 45, removed: 3 }, { added: 7, removed: 9 }, 1000)
    expect(status).toEqual({
      branch: 'main',
      upstream: 'origin/main',
      ahead: 1,
      behind: 2,
      staged: [
        { code: 'M ', path: 'staged.ts' },
        { code: 'A ', path: 'added.ts' },
        { code: 'R ', path: 'renamed.ts', oldPath: 'old.ts' },
      ],
      unstaged: [
        { code: ' M', path: 'work.ts' },
        { code: ' D', path: 'del-later.ts' },
      ],
      untracked: [{ code: '??', path: 'fresh.txt' }],
      conflicts: [{ code: 'UU', path: 'clash.ts' }],
      added: 52,
      removed: 12,
      fetchedAt: 1000,
    })
  })

  test('isGitQuiet 判定干净且同步', () => {
    const base = {
      branch: 'main',
      upstream: null,
      ahead: 0,
      behind: 0,
      staged: [],
      unstaged: [],
      untracked: [],
      conflicts: [],
      added: 0,
      removed: 0,
    }
    expect(isGitQuiet({ ...base, fetchedAt: 0 })).toBe(true)
    // 有任何文件动静或偏差都不安静
    expect(isGitQuiet({ ...base, untracked: [{ code: '??', path: 'a' }], fetchedAt: 0 })).toBe(false)
    expect(isGitQuiet({ ...base, ahead: 2, fetchedAt: 0 })).toBe(false)
    expect(isGitQuiet({ ...base, conflicts: [{ code: 'UU', path: 'a' }], fetchedAt: 0 })).toBe(false)
    expect(isGitQuiet({ ...base, staged: [{ code: 'M ', path: 'a' }], fetchedAt: 0 })).toBe(false)
  })

  test('gitSummaryParts 拼计数段与行级段', () => {
    const base = {
      branch: 'main',
      upstream: null,
      ahead: 0,
      behind: 0,
      staged: [],
      unstaged: [],
      untracked: [],
      conflicts: [],
      added: 0,
      removed: 0,
    }
    // 全空 → 两段均 null
    expect(gitSummaryParts({ ...base, fetchedAt: 0 })).toEqual({ counts: null, lines: null })
    // 计数与行级
    expect(
      gitSummaryParts({
        ...base,
        staged: [{ code: 'M ', path: 'a' }, { code: 'A ', path: 'b' }],
        unstaged: [{ code: ' M', path: 'c' }, { code: ' M', path: 'd' }, { code: ' M', path: 'e' }],
        untracked: [{ code: '??', path: 'f' }],
        added: 45,
        removed: 12,
        fetchedAt: 0,
      }),
    ).toEqual({ counts: '暂存2 改3 新1', lines: '+45 −12' })
    // 为 0 的计数类省略；行级只显示非零侧
    expect(gitSummaryParts({ ...base, unstaged: [{ code: ' M', path: 'c' }, { code: ' M', path: 'd' }], fetchedAt: 0 })).toEqual({
      counts: '改2',
      lines: null,
    })
    expect(gitSummaryParts({ ...base, added: 3, removed: 0, fetchedAt: 0 })).toEqual({
      counts: null,
      lines: '+3',
    })
    expect(gitSummaryParts({ ...base, removed: 5, fetchedAt: 0 })).toEqual({
      counts: null,
      lines: '−5',
    })
  })
})
