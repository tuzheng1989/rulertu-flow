import { describe, expect, test } from 'claude-code/testing'

import {
  bannerPlan,
  collectChanges,
  draftDecorations,
  enhanceMarkdown,
  humanDuration,
  pagerWindow,
  renderAsciiTable,
  renderMermaidGraph,
  spinnerWord,
  toolMark,
  progressBar,
  phaseProgress,
  pipelineLinks,
  scoreGauge,
  sortEntries,
  buildGitStatus,
  buildPlanReview,
  countIssues,
  creatureState,
  creatureFrames,
  depStatuses,
  extractRound,
  guardDecision,
  gitSummaryParts,
  isGitQuiet,
  isPassing,
  normalizePath,
  parseBatchScope,
  parseDepGraph,
  numstatByPath,
  SKIN_TERMS,
  parseExecution,
  parseGhIssues,
  parseNumstat,
  parseSections,
  parsePorcelain,
  parseProgressMap,
  parseReviewJson,
  parseStateJson,
  roundScores,
  sparkline,
  selectTaskView,
} from './parse'
import type { CreatureState, DepNode, ExecutionReport, FlowTask, PlanReview } from './parse'
import type { AgentSnapshot, BatchScope, FsEntryLike, GitStatus } from '../types'

describe('parse', () => {
  test('当前任务筛选不把历史评审、执行、边界或路线图当成活动任务', () => {
    const current = buildPlanReview('当前迭代', 'plans/.plan-iterate/当前迭代', '{"round":2}', [
      { round: 1, text: '{"score":7,"issues":[]}' },
      { round: 2, text: '{"score":9,"issues":[]}' },
    ])
    const history = buildPlanReview('旧评审', 'plans/.plan-iterate/旧评审', '{"round":1}', [])
    const data = {
      plans: [current, history],
      report: { plan: '实施', batch: 'B1', phase: '执行', updatedAt: 1 },
      scope: { plan: '实施', batch: 'B2', files: ['a.ts'] },
      graph: { plan: '实施', batches: [{ batch: 'B1', dependsOn: [] }] },
    }
    const empty = { plans: [], report: null, scope: null, graph: null }
    expect(selectTaskView(null, data)).toEqual(empty)
    expect(selectTaskView({ kind: 'iterate', plan: '当前迭代' }, data)).toEqual({ ...empty, plans: [current] })
    expect(selectTaskView({ kind: 'implement', plan: '实施', batch: 'B1' }, data)).toEqual({
      ...empty, report: data.report, graph: data.graph,
    })
    expect(selectTaskView({ kind: 'implement', plan: '其他方案' }, data)).toEqual(empty)
    expect(selectTaskView({ kind: 'implement', plan: '实施', batch: 'B1' }, {
      ...data, report: { ...data.report, phase: '收口' },
    }).report).toBeNull()
  })

  test('进度条处理零总数和越界值，未知阶段保留原文', () => {
    expect(progressBar(0, 0)).toBe('──────────')
    expect(progressBar(5, 10)).toBe('━━━━━─────')
    expect(progressBar(12, 10)).toBe('━━━━━━━━━━')
    expect(progressBar(-1, 10)).toBe('──────────')
    expect(progressBar(NaN, 10)).toBe('──────────')
  })

  test('达标刻度条：▏ 固定在达标线位置，不随分数移动', () => {
    expect(scoreGauge(6.8)).toBe('━━━━━━━──▏─')
    expect(scoreGauge(0)).toBe('─────────▏─')
    expect(scoreGauge(8.5)).toBe('━━━━━━━━━▏─')
    expect(scoreGauge(10)).toBe('━━━━━━━━━▏━')
    expect(scoreGauge(12)).toBe('━━━━━━━━━▏━')
    expect(scoreGauge(-1)).toBe('─────────▏─')
  })

  test('达标刻度条：pass 可调，pass=10 时刻度在串尾', () => {
    expect(scoreGauge(10, 10, 10)).toBe('━━━━━━━━━━▏')
    expect(scoreGauge(5, 10, 5)).toBe('━━━━━▏─────')
  })

  test('流水线连线状态取右侧节点，单节点无连线', () => {
    const nodes: DepNode[] = [
      { batch: 'B1', dependsOn: [], status: 'done' },
      { batch: 'B2', dependsOn: ['B1'], status: 'active' },
      { batch: 'B3', dependsOn: ['B2'], status: 'pending' },
    ]
    expect(pipelineLinks(nodes)).toEqual(['active', 'pending'])
    expect(pipelineLinks(nodes.slice(0, 1))).toEqual([])
    expect(pipelineLinks([])).toEqual([])
  })

  test('目录排序：目录在前，各自按名称字典序，不改原数组', () => {
    const entries: FsEntryLike[] = [
      { name: 'readme.md', kind: 'file', isLink: false },
      { name: 'src', kind: 'dir', isLink: false },
      { name: 'a.ts', kind: 'file', isLink: false },
      { name: 'docs', kind: 'dir', isLink: false },
    ]
    expect(sortEntries(entries).map(one => one.name)).toEqual(['docs', 'src', 'a.ts', 'readme.md'])
    expect(entries.map(one => one.name)).toEqual(['readme.md', 'src', 'a.ts', 'docs'])
  })

  test('spinnerWord：实施报批次阶段、迭代报评审、无任务报子代理、无话可说返回 null', () => {
    const implement: FlowTask = { kind: 'implement', plan: 'demo', batch: 'B2' }
    const report: ExecutionReport = {
      plan: 'demo', batch: 'B2', phase: '验证', updatedAt: 0, testsPassed: 8, testsTotal: 12,
    }
    expect(spinnerWord(implement, report, undefined, [])).toBe('B2 · 验证 · 8/12')
    expect(spinnerWord(implement, { ...report, phase: '收口' }, undefined, [])).toBeNull()
    expect(spinnerWord(implement, null, undefined, [])).toBeNull()
    const iterate: FlowTask = { kind: 'iterate', plan: 'demo' }
    const plan: PlanReview = {
      name: 'demo', dir: '.plan-iterate/demo', round: 3, rounds: [
        { round: 2, score: 6.8, p0: 0, p1: 1, p2: 0 },
        { round: 3, score: 7.2, p0: 0, p1: 1, p2: 1 },
      ], passed: false,
    }
    expect(spinnerWord(iterate, null, plan, [])).toBe('评审 R3 · 7.2 分')
    expect(spinnerWord(iterate, null, { ...plan, rounds: [] }, [])).toBe('评审 R3 进行中')
    expect(spinnerWord(iterate, null, undefined, [])).toBe('评审 demo')
    expect(spinnerWord(null, null, undefined, [
      { name: 'executor', description: '执行批次', id: 'a1' },
    ])).toBe('↻ executor · 执行批次')
    expect(spinnerWord(null, null, undefined, [
      { name: 'long-name-agent', description: '一段相当长的任务描述会撑长 Spinner 行需要截断兜底', id: 'a9' },
    ])).toBe('↻ long-name-agent · 一段相当长的任务描述会撑长 Spinne')
    expect(spinnerWord(null, null, undefined, [
      { id: 'a1' }, { id: 'a2' },
    ])).toBe('↻ 2 个子代理运行中')
    expect(spinnerWord(null, null, undefined, [])).toBeNull()
  })

  test('toolMark：界内或无边界不加标注，越界按 guardMode 定文案', () => {
    expect(toolMark(false, false, 'warn')).toBeNull()
    expect(toolMark(true, false, 'warn')).toBeNull()
    expect(toolMark(true, false, 'deny')).toBeNull()
    expect(toolMark(true, true, 'warn')).toEqual({ text: '⚠ 越界', tone: 'warn' })
    expect(toolMark(true, true, 'deny')).toEqual({ text: '✗ 拦截', tone: 'bad' })
    expect(toolMark(false, true, 'warn')).toBeNull()
  })

  test('draftDecorations：带扩展名的 token 才判定，界内外分色', () => {
    const keys = new Set(['src/in.ts', 'docs/a.md'])
    const rows = draftDecorations('请改 src/in.ts 和 docs/b.md，顺便看看 note', keys)
    expect(rows).toEqual([
      { start: 3, end: 12, inScope: true },
      { start: 15, end: 24, inScope: false },
    ])
    expect(draftDecorations('没有路径的一句话', keys)).toEqual([])
  })

  test('humanDuration：秒与分钟两档，非法输入归零', () => {
    expect(humanDuration(3200)).toBe('3.2s')
    expect(humanDuration(64_000)).toBe('1m 4s')
    expect(humanDuration(0)).toBe('0s')
    expect(humanDuration(-5)).toBe('0s')
    expect(humanDuration(NaN)).toBe('0s')
  })

  test('renderAsciiTable：等宽对齐含中文，分隔行剥除', () => {
    const rows = renderAsciiTable([
      '| 批次 | 状态 |',
      '| --- | --- |',
      '| B1 | ✓收口 |',
    ])
    expect(rows).toHaveLength(5)
    expect(rows[0]).toMatch(/^┌/)
    expect(rows[1]).toContain('│ 批次')
    expect(rows[1]).toContain('│ 状态')
    expect(rows[3]).toContain('│ B1')
    expect(rows[3]).toContain('│ ✓收口')
    expect(rows[4]).toMatch(/^└/)
  })

  test('renderMermaidGraph：TD 链式与分叉自绘流程图，非 TD 返回 null', () => {
    const chain = renderMermaidGraph(['graph TD', 'A[开始] --> B[处理] --> C[结束]'].join('\n'))
    expect(chain).not.toBeNull()
    const drawn = chain.join('\n')
    expect(drawn).toContain('开始')
    expect(drawn).toContain('处理')
    expect(drawn).toContain('结束')
    expect(drawn).toContain('▼')
    // A 在 B 上一层
    const aRow = chain.findIndex(row => row.includes('开始'))
    const bRow = chain.findIndex(row => row.includes('处理'))
    expect(aRow).toBeLessThan(bRow)
    expect(renderMermaidGraph('graph LR\nA --> B')).toBeNull()
    expect(renderMermaidGraph('graph TD\nstyle A fill:#f9f')).toBeNull()
  })

  test('pagerWindow：窗口 5 个、首尾恒显、间断省略号', () => {
    expect(pagerWindow(0, 3)).toEqual([0, 1, 2])
    expect(pagerWindow(3, 12)).toEqual([0, 1, 2, 3, 4, 5, -1, 11])
    expect(pagerWindow(0, 12)).toEqual([0, 1, 2, 3, 4, -1, 11])
    expect(pagerWindow(11, 12)).toEqual([0, -1, 7, 8, 9, 10, 11])
    expect(pagerWindow(5, 6)).toEqual([0, 1, 2, 3, 4, 5])
  })

  test('enhanceMarkdown：表格重排与 mermaid 自绘，fence 内不处理', () => {
    const enhanced = enhanceMarkdown([
      '前言',
      '| a | b |',
      '| - | - |',
      '| 1 | 2 |',
      '',
      '```mermaid',
      'graph TD',
      'A --> B',
      '```',
      '```text',
      '| 不是表格 |',
      '| - |',
      '```',
    ].join('\n'))
    expect(enhanced).toContain('┌')
    expect(enhanced).toContain('│ a')
    expect(enhanced).toContain('▼')
    expect(enhanced).toContain('┌─┐')
    // fence 内的假表格保持原样
    expect(enhanced).toContain('| 不是表格 |')
  })

  test('统一改动清单：git 并集会话记录，会话组在前、冲突优先、路径排序', () => {
    const git = buildGitStatus(parsePorcelain([
      '## main...origin/main [ahead 1]',
      ' M hooks/a.ts',
      'M  hooks/b.ts',
      '?? plans/new.md',
      'UU plans/x.md',
    ].join('\n')), null, null, 0)
    const rows = collectChanges(git, [{ path: 'hooks/a.ts' }, { path: 'docs/only-session.md' }])
    expect(rows.map(row => `${row.touched ? '●' : '○'} ${row.path} ${row.state}`)).toEqual([
      '● docs/only-session.md null',
      '● hooks/a.ts unstaged',
      '○ plans/x.md conflict',
      '○ hooks/b.ts staged',
      '○ plans/new.md untracked',
    ])
  })

  test('统一改动清单：git 缺失退化为会话清单，路径大小写折叠去重', () => {
    expect(collectChanges(null, [{ path: 'A.ts' }, { path: 'a.ts' }])).toEqual([
      { path: 'A.ts', touched: true, state: null },
    ])
    expect(collectChanges(null, [])).toEqual([])
  })

  test('phaseProgress 两阶段序号；存量与未知阶段无序号（total 0 退化纯文字）', () => {
    // B3 上报契约缩为两阶段；存量持久化值（开工/派单）与未知阶段同走 indexOf -1 退化
    expect(phaseProgress('执行')).toEqual({ current: '执行', index: 1, total: 2 })
    expect(phaseProgress('验证')).toEqual({ current: '验证', index: 2, total: 2 })
    expect(phaseProgress('开工')).toEqual({ current: '开工', index: 0, total: 0 })
    expect(phaseProgress('自定义阶段')).toEqual({ current: '自定义阶段', index: 0, total: 0 })
  })
  test('extractRound 认识 review-RN.json', () => {
    expect(extractRound('review-R1.json')).toBe(1)
    expect(extractRound('review-R12.json')).toBe(12)
    expect(extractRound('state.json')).toBe(null)
    expect(extractRound('review-R1.log')).toBe(null)
  })

  test('roundScores 拼逐轮评分明细，升序且只留最近 8 轮', () => {
    expect(roundScores([])).toBe('')
    expect(roundScores([
      { round: 1, score: 6, p0: 0, p1: 0, p2: 0 },
      { round: 2, score: 6.5, p0: 0, p1: 1, p2: 0 },
    ])).toBe('R1 6.0 · R2 6.5')
    const twelve = Array.from({ length: 12 }, (_, i) => ({ round: i + 1, score: 5 + i * 0.1, p0: 0, p1: 0, p2: 0 }))
    expect(roundScores(twelve)).toBe(
      'R5 5.4 · R6 5.5 · R7 5.6 · R8 5.7 · R9 5.8 · R10 5.9 · R11 6.0 · R12 6.1',
    )
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

  test('parseStateJson 提取 backend、round 与 plan_path，忽略其余字段', () => {
    const state = parseStateJson(
      JSON.stringify({ backend: 'codex', round: 3, plan_path: 'plans/p.md', plan_sha256: 'x' }),
    )
    expect(state).toEqual({ backend: 'codex', round: 3, planPath: 'plans/p.md' })
    expect(parseStateJson(JSON.stringify({ plan_path: '' }))).toEqual({})
    expect(parseStateJson('[]')).toBe(null)
    expect(parseStateJson('nope')).toBe(null)
  })

  test('parseGhIssues 解析 gh issue list 输出：合法全字段、坏 JSON、缺 labels、非法条目剔除', () => {
    // 合法全字段：number/title/url/labels 原样收
    expect(parseGhIssues(JSON.stringify([
      { number: 12, title: '修复守卫', url: 'https://example.com/i/12', labels: [{ name: 'bug' }, { name: 'P1' }] },
      { number: 13, title: '补文档', url: 'https://example.com/i/13', labels: [] },
    ]))).toEqual([
      { number: 12, title: '修复守卫', url: 'https://example.com/i/12', labels: ['bug', 'P1'] },
      { number: 13, title: '补文档', url: 'https://example.com/i/13', labels: [] },
    ])
    // 坏 JSON 与非数组返回 null
    expect(parseGhIssues('{broken')).toBe(null)
    expect(parseGhIssues(JSON.stringify({ number: 1 }))).toBe(null)
    // 缺 labels 视为空数组；labels 内非 string 的 name 剔除
    expect(parseGhIssues(JSON.stringify([
      { number: 1, title: 't', url: 'u' },
      { number: 2, title: 't2', url: 'u2', labels: [{ name: 'ok' }, { name: 7 }, {}] },
    ]))).toEqual([
      { number: 1, title: 't', url: 'u', labels: [] },
      { number: 2, title: 't2', url: 'u2', labels: ['ok'] },
    ])
    // number 非 number 或 title/url 非 string 的条目整条剔除
    expect(parseGhIssues(JSON.stringify([
      { number: '12', title: 't', url: 'u', labels: [] },
      { number: 3, title: 9, url: 'u', labels: [] },
      { number: 4, title: 't', url: null, labels: [] },
      { number: 5, title: '合法', url: 'https://example.com/i/5', labels: [{ name: 'x' }] },
    ]))).toEqual([
      { number: 5, title: '合法', url: 'https://example.com/i/5', labels: ['x'] },
    ])
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

  test('parseExecution closure 透传：null 原样、缺省规范化为 null、非法整个丢弃', () => {
    // null 字段原样透传（真实统计不可用形态），不折算为 0
    const allNull = parseExecution({
      plan: 'demo', batch: 'B2', phase: '收口', updatedAt: 1,
      closure: { files: 3, added: null, removed: null, minutes: null },
    })
    expect(allNull?.closure).toEqual({ files: 3, added: null, removed: null, minutes: null })
    expect('removed' in (allNull?.closure ?? {})).toBe(true)
    // 部分缺失规范化为 null（不出现 undefined 形态）
    const partial = parseExecution({
      plan: 'demo', batch: 'B2', phase: '收口', updatedAt: 1,
      closure: { files: 3, added: 842 },
    })
    expect(partial?.closure).toEqual({ files: 3, added: 842, removed: null, minutes: null })
    // statsAt 为 number 时透传
    expect(parseExecution({
      plan: 'demo', batch: 'B2', phase: '收口', updatedAt: 1,
      closure: { files: 1, added: 0, removed: 0, minutes: 5, statsAt: 900 },
    })?.closure).toEqual({ files: 1, added: 0, removed: 0, minutes: 5, statsAt: 900 })
    // files 非法（字符串/缺失）→ 整个 closure 丢弃，视同缺省
    expect(parseExecution({
      plan: 'demo', batch: 'B2', phase: '收口', updatedAt: 1,
      closure: { files: '3', added: 1, removed: 1, minutes: 1 },
    })?.closure).toBeUndefined()
    expect(parseExecution({
      plan: 'demo', batch: 'B2', phase: '收口', updatedAt: 1,
      closure: { added: 1 },
    })?.closure).toBeUndefined()
    // closure 非对象 → 丢弃
    expect(parseExecution({
      plan: 'demo', batch: 'B2', phase: '收口', updatedAt: 1, closure: 'x',
    })?.closure).toBeUndefined()
    // closure 缺省 → 不出现
    expect(parseExecution({ plan: 'p', batch: 'B1', phase: '执行' })?.closure).toBeUndefined()
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
    // 越界：保留调用方原样路径供提示，key 为归一化小写路径
    expect(guardDecision(scope, 'Edit', { file_path: 'C:\\repo\\other\\c.ts' }, cwd)).toEqual({
      kind: 'outOfScope',
      path: 'C:\\repo\\other\\c.ts',
      key: 'other/c.ts',
    })
    // 同一文件异写法（分隔符/大小写）与上面 key 相同，path 保留原样
    expect(guardDecision(scope, 'Write', { file_path: 'C:/REPO/OTHER/C.TS' }, cwd)).toEqual({
      kind: 'outOfScope',
      path: 'C:/REPO/OTHER/C.TS',
      key: 'other/c.ts',
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

  test('parseProgressMap 校验跨会话进度恢复：合法全收、整体非对象 null、混值剔键、空对象合法', () => {
    expect(parseProgressMap({ 'demo#B1': '收口', 'demo#B2': '执行' })).toEqual({ 'demo#B1': '收口', 'demo#B2': '执行' })
    // 整体非对象（含数组与 null）：一律 null，恢复侧降级为空 map
    expect(parseProgressMap('garbage')).toBe(null)
    expect(parseProgressMap(['demo#B1'])).toBe(null)
    expect(parseProgressMap(null)).toBe(null)
    // 混合值：非 string 值的键剔除，其余键保留（个别坏键不弃整份，D9）
    expect(parseProgressMap({ 'demo#B1': '收口', 'demo#B2': 3, 'demo#B3': null })).toEqual({ 'demo#B1': '收口' })
    // 空对象合法
    expect(parseProgressMap({})).toEqual({})
  })

  test('depStatuses 按 progress 标注三态', () => {
    const graph = parseDepGraph({
      plan: 'demo',
      batches: [{ batch: 'B1', dependsOn: [] }, { batch: 'B2', dependsOn: ['B1'] }],
    })
    if (graph === null) throw new Error('fixture 不可为 null')
    // 无记录全部待执行
    expect(depStatuses(graph, {})).toEqual([
      { batch: 'B1', dependsOn: [], status: 'pending', phase: '待执行' },
      { batch: 'B2', dependsOn: ['B1'], status: 'pending', phase: '待执行' },
    ])
    // 收口=完成；其他阶段=进行中；其他方案的记录不影响
    const progress = { 'demo#B1': '收口', 'demo#B2': '执行', 'other#B1': '收口' }
    expect(depStatuses(graph, progress)).toEqual([
      { batch: 'B1', dependsOn: [], status: 'done', phase: '收口' },
      { batch: 'B2', dependsOn: ['B1'], status: 'active', phase: '执行' },
    ])
  })

  test('depStatuses 拓扑下推：done 沿 dependsOn 闭包传播，视图修正不改 progress 原文', () => {
    const graph = parseDepGraph({
      plan: 'demo',
      batches: [
        { batch: 'B1', dependsOn: [] },
        { batch: 'B2', dependsOn: ['B1'] },
        { batch: 'B3', dependsOn: ['B2'] },
      ],
    })
    if (graph === null) throw new Error('fixture 不可为 null')
    // B2 收口而 B1 无记录 → B1 推导 done 且阶段置「收口」（dependsOn 语义：下游收口前上游必已收口）
    const pushed = depStatuses(graph, { 'demo#B2': '收口' })
    expect(pushed.map(node => [node.batch, node.status, node.phase])).toEqual([
      ['B1', 'done', '收口'],
      ['B2', 'done', '收口'],
      ['B3', 'pending', '待执行'],
    ])
    // B3 收口沿 B2→B1 链式传递（含传递闭包）
    expect(depStatuses(graph, { 'demo#B3': '收口' }).map(node => node.status)).toEqual(['done', 'done', 'done'])
    // dependsOn 引用图中不存在的批次名：跳过不崩
    const dangling = parseDepGraph({ plan: 'demo', batches: [{ batch: 'B2', dependsOn: ['B9'] }] })
    if (dangling === null) throw new Error('fixture 不可为 null')
    expect(depStatuses(dangling, { 'demo#B2': '收口' })).toEqual([
      { batch: 'B2', dependsOn: ['B9'], status: 'done', phase: '收口' },
    ])
    // 末批漏报（无下游）→ 维持查表结果（覆盖面负断言）
    expect(depStatuses(graph, { 'demo#B1': '收口' }).map(node => node.status)).toEqual(['done', 'pending', 'pending'])
  })

  test('buildPlanReview 组装概览并以最新轮判定达标', () => {
    const plan = buildPlanReview(
      'demo',
      '.plan-iterate/demo',
      JSON.stringify({ backend: 'codex', round: 2, plan_path: 'plans/demo.md' }),
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
    expect(plan.docPath).toBe('plans/demo.md')
    expect(plan.round).toBe(2)
    expect(plan.rounds.map(round => round.round)).toEqual([1, 2])
    expect(plan.passed).toBe(true)

    // 无 state.json 时轮次回退到最新评审轮；最新轮有 P1 则不达标；docPath 缺失
    const failing = buildPlanReview('old', '.plan-iterate/old', null, [
      { round: 1, text: JSON.stringify({ score: 9, issues: [{ severity: 'P1' }] }) },
    ])
    expect(failing.round).toBe(1)
    expect(failing.passed).toBe(false)
    expect(failing.docPath).toBeUndefined()

    // 只有 state.json、评审尚未落盘：不达标，轮次取自 state
    const pending = buildPlanReview('new', '.plan-iterate/new', JSON.stringify({ round: 3 }), [])
    expect(pending.round).toBe(3)
    expect(pending.rounds).toEqual([])
    expect(pending.passed).toBe(false)
  })

  test('bannerPlan 选取横条方案:最后一个未达标者,全部达标撤下', () => {
    const passed = buildPlanReview('done', '.plan-iterate/done', null, [
      { round: 6, text: JSON.stringify({ score: 9.2, issues: [{ severity: 'P2' }] }) },
    ])
    const failing = buildPlanReview('wip', '.plan-iterate/wip', null, [
      { round: 1, text: JSON.stringify({ score: 7.0, issues: [{ severity: 'P0' }] }) },
    ])
    expect(passed.passed).toBe(true)
    expect(failing.passed).toBe(false)

    // 横条只留给未达标方案;名字排序在后的达标方案不占横条
    expect(bannerPlan([failing, passed])).toBe(failing)
    expect(bannerPlan([passed, failing])).toBe(failing)

    // 全部达标或无方案 → null(横条撤下)
    expect(bannerPlan([passed])).toBe(null)
    expect(bannerPlan([])).toBe(null)
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

  test('numstatByPath 逐文件聚合：多文件、空输出、非法行与二进制跳过', () => {
    expect(numstatByPath('5\t3\ta.ts\n12\t0\tb.ts\n')).toEqual(
      new Map([['a.ts', { a: 5, r: 3 }], ['b.ts', { a: 12, r: 0 }]]),
    )
    expect(numstatByPath('')).toEqual(new Map())
    expect(numstatByPath('junk line\n')).toEqual(new Map())
    // 二进制行（-\t-）沿用既有跳过口径，不计入任何文件
    expect(numstatByPath('-\t-\tbinary.png\n2\t1\tc.ts\n')).toEqual(
      new Map([['c.ts', { a: 2, r: 1 }]]),
    )
  })

  test('numstatByPath rename 目标路径还原：全量记法与花括号压缩记法', () => {
    // 全量记法取 => 右侧整段
    expect(numstatByPath('3\t0\ta/old.ts => b/new.ts\n')).toEqual(
      new Map([['b/new.ts', { a: 3, r: 0 }]]),
    )
    // 花括号压缩记法还原为 src/new/file.ts
    expect(numstatByPath('1\t2\tsrc/{old => new}/file.ts\n')).toEqual(
      new Map([['src/new/file.ts', { a: 1, r: 2 }]]),
    )
    // 深层目录的花括号记法
    expect(numstatByPath('4\t1\ta/b/{x.ts => y.ts}\n')).toEqual(
      new Map([['a/b/y.ts', { a: 4, r: 1 }]]),
    )
  })

  test('numstatByPath 键归一化：反斜杠转正斜杠并小写折叠', () => {
    expect(numstatByPath('2\t1\tSRC\\App.TS\n')).toEqual(
      new Map([['src/app.ts', { a: 2, r: 1 }]]),
    )
    expect(numstatByPath('1\t0\tDocs/{A => B}/Readme.MD\n')).toEqual(
      new Map([['docs/b/readme.md', { a: 1, r: 0 }]]),
    )
  })

  test('numstatByPath 引号路径：剥引号并解码八进制转义（UTF-8 字节还原）', () => {
    // 文档.md 的 UTF-8 字节序列的八进制转义形态
    expect(numstatByPath('2\t1\t"\\346\\226\\207\\346\\241\\243.md"\n')).toEqual(
      new Map([['文档.md', { a: 2, r: 1 }]]),
    )
    // 含空格路径双引号包裹，剥引号后原样保留
    expect(numstatByPath('1\t0\t"path with space.txt"\n')).toEqual(
      new Map([['path with space.txt', { a: 1, r: 0 }]]),
    )
    // \" 转义还原（文件名 we"ird.txt）；\\ 解码出的反斜杠按归一化口径转正斜杠（同 normalizePath 口径）
    expect(numstatByPath('1\t1\t"we\\"ird.txt"\n')).toEqual(
      new Map([['we"ird.txt', { a: 1, r: 1 }]]),
    )
    expect(numstatByPath('1\t1\t"a\\\\b.txt"\n')).toEqual(
      new Map([['a/b.txt', { a: 1, r: 1 }]]),
    )
    // 不以引号包裹的路径原样保留
    expect(numstatByPath('1\t0\tplain.md\n')).toEqual(
      new Map([['plain.md', { a: 1, r: 0 }]]),
    )
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
    const status: GitStatus = buildGitStatus(porcelain, '45\t3\twa.ts\n', '7\t9\tca.ts\n', 1000)
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
      numstatSides: { worktree: 'ok', cached: 'ok' },
      byPath: { 'wa.ts': [45, 3], 'ca.ts': [7, 9] },
    })
  })

  test('buildGitStatus 侧状态装配：两侧均成功 → ok/ok', () => {
    const porcelain = parsePorcelain('## main\nM  s.ts\n M w.ts\n')
    if (porcelain === null) throw new Error('fixture 不可为 null')
    const status = buildGitStatus(porcelain, '1\t0\tw.ts\n', '2\t0\ts.ts\n', 5)
    expect(status.numstatSides).toEqual({ worktree: 'ok', cached: 'ok' })
    expect(status.added).toBe(3)
  })

  test('buildGitStatus 侧状态装配：无 tracked 改动的一侧 skipped，对侧不受影响', () => {
    // 仅未暂存改动：cached 侧本不应查询（staged 空）→ skipped；worktree 发起且成功 → ok
    const porcelain = parsePorcelain('## main\n M w.ts\n')
    if (porcelain === null) throw new Error('fixture 不可为 null')
    const status = buildGitStatus(porcelain, '1\t0\tw.ts\n', null, 5)
    expect(status.numstatSides).toEqual({ worktree: 'ok', cached: 'skipped' })
    expect(status.added).toBe(1)
    // 反向：仅暂存改动
    const onlyStaged = parsePorcelain('## main\nM  s.ts\n')
    if (onlyStaged === null) throw new Error('fixture 不可为 null')
    const status2 = buildGitStatus(onlyStaged, null, '3\t1\ts.ts\n', 5)
    expect(status2.numstatSides).toEqual({ worktree: 'skipped', cached: 'ok' })
    expect(status2.removed).toBe(1)
  })

  test('buildGitStatus 侧状态装配：本应查询但返回 null → failed，与 skipped 可区分', () => {
    const porcelain = parsePorcelain('## main\nM  s.ts\n M w.ts\n')
    if (porcelain === null) throw new Error('fixture 不可为 null')
    // 两侧都有 tracked 改动，cached 查询失败（null）
    const status = buildGitStatus(porcelain, '1\t0\tw.ts\n', null, 5)
    expect(status.numstatSides).toEqual({ worktree: 'ok', cached: 'failed' })
    // 冲突文件计入 worktree 侧"本应查询"判定
    const clashing = parsePorcelain('## main\nUU c.ts\n')
    if (clashing === null) throw new Error('fixture 不可为 null')
    const status2 = buildGitStatus(clashing, null, null, 5)
    expect(status2.numstatSides).toEqual({ worktree: 'failed', cached: 'skipped' })
  })

  test('buildGitStatus byPath：同文件暂存+未暂存求和，键归一化，合计与 added/removed 一致', () => {
    const porcelain = parsePorcelain('## main\nM  Src\\A.TS\n')
    if (porcelain === null) throw new Error('fixture 不可为 null')
    const status = buildGitStatus(porcelain, '2\t1\tsrc/a.ts\n', '3\t0\tSRC/A.ts\n', 5)
    expect(status.byPath).toEqual({ 'src/a.ts': [5, 1] })
    expect(status.added).toBe(5)
    expect(status.removed).toBe(1)
    // rename 花括号记法还原目标路径进入 byPath
    const renamed = buildGitStatus(porcelain, '1\t2\tsrc/{old => new}/file.ts\n', null, 5)
    expect(renamed.byPath).toEqual({ 'src/new/file.ts': [1, 2] })
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

  test('parseSections 按标题切分，围栏内 # 不算标题', () => {
    expect(parseSections('# A\na1\n## B\nb1')).toEqual([
      { title: 'A', level: 1, start: 1, end: 2 },
      { title: 'B', level: 2, start: 3, end: 4 },
    ])
    // 开头正文与标题平级成「开头」节；纯空行开头不设节
    expect(parseSections('p1\n\n# A\nx')).toEqual([
      { title: '开头', level: 0, start: 1, end: 2 },
      { title: 'A', level: 1, start: 3, end: 4 },
    ])
    // 围栏内的 # 不算标题，围栏行归属当节
    expect(parseSections('# A\n```py\n# not-heading\n```\nz')).toEqual([
      { title: 'A', level: 1, start: 1, end: 5 },
    ])
    expect(parseSections('# A\n~~~\n# not-heading\n~~~\nz')).toEqual([
      { title: 'A', level: 1, start: 1, end: 5 },
    ])
    // 无标题非空文档整篇为「全文」节；空文本为空数组
    expect(parseSections('a\nb')).toEqual([{ title: '全文', level: 0, start: 1, end: 2 }])
    expect(parseSections('')).toEqual([])
    // 无空格的 #Title 与七连 # 不是标题
    expect(parseSections('#nospace\n##X\n####### seven\nbody')).toEqual([
      { title: '全文', level: 0, start: 1, end: 4 },
    ])
  })

  test('skin 术语表双词表快照：7 条映射一词一义，default 词表与现行文案逐字一致', () => {
    expect(SKIN_TERMS.default).toEqual({
      batch: '批次',
      execute: '执行',
      verify: '验证',
      score: '评分',
      deps: '执行 DAG',
      stall: '疑似停滞',
      noTask: '当前无方案迭代或实施任务。',
    })
    expect(SKIN_TERMS['mission-control']).toEqual({
      batch: '飞行阶段',
      execute: '阶段进行',
      verify: '数据校验',
      score: '燃料余量',
      deps: '轨道图',
      stall: '遥测丢失',
      noTask: '待命 · 当前无方案迭代或实施任务。',
    })
    // 两词表键集合一致（只换文案，不改信息量）
    expect(Object.keys(SKIN_TERMS['mission-control']).sort())
      .toEqual(Object.keys(SKIN_TERMS.default).sort())
  })

  test('creatureState 六态优先级阶梯：敬礼 > 捂脸 > 抖腿 > 分身 > 干活 > 睡觉（六态互斥）', () => {
    const task: FlowTask = { kind: 'implement', plan: 'demo', batch: 'B2' }
    const card = { plan: 'demo', batch: 'B2', closure: { files: 1, added: null, removed: null, minutes: null } }
    const snapshot = (status: string): AgentSnapshot => ({
      agents: [{ id: 'a1', description: '子代理', type: 'runner', status }],
      loaded: true, error: false,
    })
    const base = {
      closureCard: null, currentTask: null, guardWarned: [] as string[],
      stall: null as number | null,
      agents: { agents: [], loaded: true, error: false } as AgentSnapshot,
    }
    // 全空输入 → 睡觉兜底
    expect(creatureState(base)).toBe('sleep')
    // 单输入阶梯：六态各自命中且互斥
    const ladder = [
      creatureState({ ...base, closureCard: card }),
      creatureState({ ...base, currentTask: task, guardWarned: ['src/a.ts'] }),
      creatureState({ ...base, stall: 31 }),
      creatureState({ ...base, agents: snapshot('running') }),
      creatureState({ ...base, currentTask: task }),
      creatureState(base),
    ]
    expect(ladder).toEqual(['salute', 'facepalm', 'legshake', 'clone', 'work', 'sleep'])
    expect(new Set(ladder).size).toBe(6)
    // 组合输入取最高优先级：敬礼压过全部低优先级输入；捂脸压过抖腿+分身
    expect(creatureState({
      ...base, closureCard: card, currentTask: task, guardWarned: ['src/a.ts'],
      stall: 31, agents: snapshot('running'),
    })).toBe('salute')
    expect(creatureState({
      ...base, currentTask: task, guardWarned: ['src/a.ts'], stall: 31, agents: snapshot('running'),
    })).toBe('facepalm')
  })

  test('guardWarned 初始空数组不命中捂脸态，落到次优先级', () => {
    const task: FlowTask = { kind: 'implement', plan: 'demo', batch: 'B2' }
    const base = {
      closureCard: null, currentTask: task, guardWarned: [] as string[],
      stall: null as number | null,
      agents: { agents: [], loaded: true, error: false } as AgentSnapshot,
    }
    expect(creatureState(base)).toBe('work')
    expect(creatureState({ ...base, agents: { agents: [{ id: 'a1', description: 'x', type: 'runner', status: 'running' }], loaded: true, error: false } })).toBe('clone')
    expect(creatureState({ ...base, stall: 5 })).toBe('legshake')
  })

  test('警告态作用域转换（状态机输入侧）：收口/idle 退位，切新任务落干活', () => {
    const oldTask: FlowTask = { kind: 'implement', plan: 'demo', batch: 'B2' }
    const newTask: FlowTask = { kind: 'implement', plan: 'demo', batch: 'B3' }
    const base = {
      closureCard: null, currentTask: null, guardWarned: [] as string[],
      stall: null as number | null,
      agents: { agents: [], loaded: true, error: false } as AgentSnapshot,
    }
    const alarmed = { ...base, currentTask: oldTask, guardWarned: ['src/a.ts'] }
    expect(creatureState(alarmed)).toBe('facepalm')
    // 告警 → 收口（收口分支 currentTask 置 null，guardWarned 不清——B1 条目 4）：捂脸退位
    const closed = { ...alarmed, currentTask: null }
    expect(creatureState(closed)).toBe('sleep')
    // 收口态有 running 子代理 → 退位到次优先级分身而非睡觉
    expect(creatureState({
      ...closed, agents: { agents: [{ id: 'a1', description: 'x', type: 'runner', status: 'running' }], loaded: true, error: false },
    })).toBe('clone')
    // 告警 → idle（flow_task idle：currentTask 置 null）→ 同前退位
    expect(creatureState({ ...alarmed, currentTask: null, guardWarned: [] })).toBe('sleep')
    // 告警 → flow_task 切新任务（任务实际变化 → guardWarned 条件清理清空 + currentTask 换新）→ 干活
    expect(creatureState({ ...alarmed, currentTask: newTask, guardWarned: [] })).toBe('work')
    // 告警 → 收口 → flow_report 直接上报异批执行（不经 flow_task：非收口分支异批清理清空 + currentTask 换新）→ 干活
    expect(creatureState({ ...alarmed, currentTask: newTask, guardWarned: [] })).toBe('work')
    // 对照（输入侧语义）：若清理失效旧告警残留，新任务也会捂脸——B1 清理点保证 guardWarned 为空
    expect(creatureState({ ...alarmed, currentTask: newTask })).toBe('facepalm')
  })

  test('creatureFrames：六态两帧驻场猫卡通块，每帧 3-4 行、每行 ≤8 显示列、两帧整块不同', () => {
    const states: CreatureState[] = ['salute', 'facepalm', 'legshake', 'clone', 'work', 'sleep']
    expect(Object.keys(creatureFrames).sort()).toEqual([...states].sort())
    for (const state of states) {
      const [f0, f1] = creatureFrames[state]
      for (const frame of [f0, f1]) {
        expect(frame.length).toBeGreaterThanOrEqual(3)
        expect(frame.length).toBeLessThanOrEqual(4)
        for (const line of frame) {
          // 窄字符假设：码点数即显示列（限定非 CJK 可打印区，防宽字符混入破坏对齐）
          expect([...line].length).toBeLessThanOrEqual(8)
          for (const ch of line) {
            const code = ch.codePointAt(0) ?? 0
            expect(code).toBeGreaterThanOrEqual(0x20)
            expect(code).toBeLessThan(0x2e80)
          }
        }
      }
      expect(f0).not.toEqual(f1)
    }
  })
})
