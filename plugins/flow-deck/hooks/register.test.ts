import { describe, expect, mock, test } from 'claude-code/testing'
import { clipboardArgv, describeExecution, envPlatform } from './register'
import { creatureFrames } from './parse'
import type { AgentSnapshot, GitStatus } from '../types'

/** 帧字符串含 \ ( ) 等 regex 元字符，按帧查渲染节点前先转义；^$ 锚定整行精确匹配
 *  （帧行间存在前缀包含，如 facepalm 行1 是 salute 行1 的前缀，子串匹配会串态） */
const frameRe = (line: string): RegExp => new RegExp(`^${line.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}$`)

function paneProps(title: string) {
  return {
    title,
    isFocused: false,
    bodyColumns: 60,
    placement: 'dock' as const,
    scroll: { offset: 0, bodyRows: 20 },
    view: {},
  }
}

function bandProps() {
  return {
    hasSurvey: false,
    isWorking: false,
    maxRows: 3,
    bodyColumns: 80,
    scroll: { offset: 0, bodyRows: 3 },
    view: {},
  }
}

/** unified diff hunk fixture：标题/Code 渲染断言与 process.run mock 共用
 *  （hunk 头行数须与两侧实际行数一致，引擎绘制前做 unified-diff 解析校验） */
const DIFF_HUNK = [
  'diff --git a/hooks/a.ts b/hooks/a.ts',
  'index 1111111..2222222 100644',
  '--- a/hooks/a.ts',
  '+++ b/hooks/a.ts',
  '@@ -1,2 +1,3 @@',
  ' line1',
  ' line2',
  '+added line',
].join('\n')

/** diff 视图用例共用的 process.run 分流：git diff（非 numstat）按 diffResult 应答，
 *  其余（status/numstat/gh）按 exitCode 128 静默——非仓库惯例口径，numstat 单列防止
 *  轮询侧 numstat 查询被 hunk 文本污染（diffCalls 捕获发起过的 diff argv）。
 *  注：process.run 事件载荷的字段名是 argv（含超时等选项在 init），非 args */
function diffRunner(diffCalls: string[][], diffResult: { exitCode: number; stdout: string }) {
  return ($: unknown, e: { argv?: string[] }) => {
    const args = e.argv ?? []
    if (args[0] === 'git' && args.includes('diff') && !args.includes('--numstat')) {
      diffCalls.push(args)
      return { value: { exitCode: diffResult.exitCode, stdout: diffResult.stdout, stderr: '' } }
    }
    return { value: { exitCode: 128, stdout: '', stderr: '' } }
  }
}

/** 剥离渲染树中的不稳定句柄（press 等），保留结构与文案与 props（基线对比用） */
function stableTree(nodes: unknown): unknown {
  if (Array.isArray(nodes)) return nodes.map(stableTree)
  if (typeof nodes === 'object' && nodes !== null) {
    const record = nodes as Record<string, unknown>
    const out: Record<string, unknown> = {}
    for (const [key, value] of Object.entries(record)) {
      if (key === 'press') continue
      out[key] = stableTree(value)
    }
    return out
  }
  return nodes
}

/** 改动前空态渲染树基线（probe 取自 0.17.0 代码：无任务、无通关卡、companion=off、artDirection=default）。
 *  断言渲染层改动不破坏既有空态结构；press 句柄等不稳定字段经 stableTree 剥离。 */
const EMPTY_PANE_BASELINE = `[{"type":"Box","props":{"flexDirection":"column","gap":1},"text":"工作面板文件树文件查看器主对话当前无方案迭代或实施任务。运行 plan-iterate 开始方案迭代，或 implement-plan 开始实施。▍子代理刷新正在读取当前会话的子代理…/deck 关闭 · 面板内按 r 刷新","children":[{"type":"Box","props":{"gap":2},"children":[{"type":"Button","props":{"key":"tab-flow","label":"工作面板","hotkey":"1","plain":true,"dimColor":false}},{"type":"Button","props":{"key":"tab-files","label":"文件树","hotkey":"2","plain":true,"dimColor":true}},{"type":"Button","props":{"key":"tab-doc","label":"文件查看器","hotkey":"3","plain":true,"dimColor":true}},{"type":"Button","props":{"key":"view-main","label":"主对话"}}]},{"type":"Box","props":{"flexDirection":"column","gap":1},"children":[{"type":"Box","props":{"flexDirection":"column"},"children":[{"type":"Text","children":["当前无方案迭代或实施任务。"]},{"type":"Text","props":{"dimColor":true},"children":["运行 plan-iterate 开始方案迭代，或 implement-plan 开始实施。"]}]},{"type":"Box","props":{"flexDirection":"column","gap":1},"children":[{"type":"Box","props":{"gap":2},"children":[{"type":"Text","props":{"bold":true,"wrap":"truncate-end"},"children":["▍","子代理",""]},{"type":"Button","props":{"key":"flow-refresh","label":"刷新","hotkey":"r","plain":true}}]},{"type":"Text","props":{"dimColor":true},"children":["正在读取当前会话的子代理…"]}]},{"type":"Text","props":{"dimColor":true,"wrap":"truncate-end"},"children":["/deck 关闭 · 面板内按 r 刷新"]}]}]},{"type":"Box","props":{"gap":2},"text":"工作面板文件树文件查看器主对话","children":[{"type":"Button","props":{"key":"tab-flow","label":"工作面板","hotkey":"1","plain":true,"dimColor":false}},{"type":"Button","props":{"key":"tab-files","label":"文件树","hotkey":"2","plain":true,"dimColor":true}},{"type":"Button","props":{"key":"tab-doc","label":"文件查看器","hotkey":"3","plain":true,"dimColor":true}},{"type":"Button","props":{"key":"view-main","label":"主对话"}}]},{"type":"Button","key":"tab-flow","props":{"key":"tab-flow","label":"工作面板","hotkey":"1","plain":true,"dimColor":false},"text":"工作面板","children":[]},{"type":"Button","key":"tab-files","props":{"key":"tab-files","label":"文件树","hotkey":"2","plain":true,"dimColor":true},"text":"文件树","children":[]},{"type":"Button","key":"tab-doc","props":{"key":"tab-doc","label":"文件查看器","hotkey":"3","plain":true,"dimColor":true},"text":"文件查看器","children":[]},{"type":"Button","key":"view-main","props":{"key":"view-main","label":"主对话"},"text":"主对话","children":[]},{"type":"Box","props":{"flexDirection":"column","gap":1},"text":"当前无方案迭代或实施任务。运行 plan-iterate 开始方案迭代，或 implement-plan 开始实施。▍子代理刷新正在读取当前会话的子代理…/deck 关闭 · 面板内按 r 刷新","children":[{"type":"Box","props":{"flexDirection":"column"},"children":[{"type":"Text","children":["当前无方案迭代或实施任务。"]},{"type":"Text","props":{"dimColor":true},"children":["运行 plan-iterate 开始方案迭代，或 implement-plan 开始实施。"]}]},{"type":"Box","props":{"flexDirection":"column","gap":1},"children":[{"type":"Box","props":{"gap":2},"children":[{"type":"Text","props":{"bold":true,"wrap":"truncate-end"},"children":["▍","子代理",""]},{"type":"Button","props":{"key":"flow-refresh","label":"刷新","hotkey":"r","plain":true}}]},{"type":"Text","props":{"dimColor":true},"children":["正在读取当前会话的子代理…"]}]},{"type":"Text","props":{"dimColor":true,"wrap":"truncate-end"},"children":["/deck 关闭 · 面板内按 r 刷新"]}]},{"type":"Box","props":{"flexDirection":"column"},"text":"当前无方案迭代或实施任务。运行 plan-iterate 开始方案迭代，或 implement-plan 开始实施。","children":[{"type":"Text","children":["当前无方案迭代或实施任务。"]},{"type":"Text","props":{"dimColor":true},"children":["运行 plan-iterate 开始方案迭代，或 implement-plan 开始实施。"]}]},{"type":"Text","props":{},"text":"当前无方案迭代或实施任务。","children":["当前无方案迭代或实施任务。"]},{"type":"Text","props":{"dimColor":true},"text":"运行 plan-iterate 开始方案迭代，或 implement-plan 开始实施。","children":["运行 plan-iterate 开始方案迭代，或 implement-plan 开始实施。"]},{"type":"Box","props":{"flexDirection":"column","gap":1},"text":"▍子代理刷新正在读取当前会话的子代理…","children":[{"type":"Box","props":{"gap":2},"children":[{"type":"Text","props":{"bold":true,"wrap":"truncate-end"},"children":["▍","子代理",""]},{"type":"Button","props":{"key":"flow-refresh","label":"刷新","hotkey":"r","plain":true}}]},{"type":"Text","props":{"dimColor":true},"children":["正在读取当前会话的子代理…"]}]},{"type":"Box","props":{"gap":2},"text":"▍子代理刷新","children":[{"type":"Text","props":{"bold":true,"wrap":"truncate-end"},"children":["▍","子代理",""]},{"type":"Button","props":{"key":"flow-refresh","label":"刷新","hotkey":"r","plain":true}}]},{"type":"Text","props":{"bold":true,"wrap":"truncate-end"},"text":"▍子代理","children":["▍","子代理",""]},{"type":"Button","key":"flow-refresh","props":{"key":"flow-refresh","label":"刷新","hotkey":"r","plain":true},"text":"刷新","children":[]},{"type":"Text","props":{"dimColor":true},"text":"正在读取当前会话的子代理…","children":["正在读取当前会话的子代理…"]},{"type":"Text","props":{"dimColor":true,"wrap":"truncate-end"},"text":"/deck 关闭 · 面板内按 r 刷新","children":["/deck 关闭 · 面板内按 r 刷新"]}]`

describe('pane', () => {
  test('打开时立即读宿主清单并自动刷新，关闭后停止查询，新会话清空快照', async ($, on) => {
    const clock = mock.clock(on)
    let open = false
    let calls = 0
    let status = 'running'
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: open ? [{ id: 'deck', title: 'Deck', isShown: true, isFocused: false, isPlaced: true }] : [] }))
    on('ui.open', { id: 'deck' }, () => {
      open = true
      return { value: { isPlaced: true } }
    })
    on('ui.close', { id: 'deck' }, () => {
      open = false
      return { value: undefined }
    })
    on('agent.list', () => {
      calls++
      return { value: [{ id: 'a1', name: 'executor', type: 'runner', description: '实现面板', status }] }
    })
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await clock.advance(2000)
    expect(calls).toBe(0)
    await $.command.run({ command: 'deck', args: '' })
    await clock.settle()
    expect(calls).toBe(1)
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow 当前任务'),
    })
    expect(await ui.find({ text: /● 运行中 · executor/ })).not.toBeUndefined()
    // 子代理区保留 Claude Code 一致的橙（deck 主色调已改蓝，此处不跟随）
    const runningLine = await ui.find({ type: 'Text', text: /● 运行中 · executor/ })
    expect(runningLine?.props.color).toBe('claude')
    status = 'completed'
    await clock.advance(2000)
    expect(calls).toBe(2)
    expect(await ui.find({ text: /✓ 已完成 · executor/ })).not.toBeUndefined()
    await $.command.run({ command: 'deck', args: '' })
    await clock.advance(4000)
    expect(calls).toBe(2)
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    expect(await ui.find({ text: /executor/ })).toBeUndefined()
    await ui.unmount()
  })

  test('会话内只注册 deck 一个命令', async ($, on) => {
    const commands: string[] = []
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => {
      commands.push(e.name)
      return { value: { name: e.name } }
    })
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('ui.status', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('fs.list', () => ({ value: [] }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    expect(commands).toEqual(['deck'])
  })

  test('统一改动清单：● 本会话 ○ 其他 ◆ 本批三态同屏', async ($, on) => {
    const clock = mock.clock(on)
    const gitSnapshot: GitStatus = {
      branch: 'main', upstream: 'origin/main', ahead: 0, behind: 0,
      staged: [], unstaged: [{ code: ' M', path: 'hooks/a.ts' }],
      untracked: [{ code: '??', path: 'plans/b.md' }], conflicts: [],
      added: 3, removed: 1, fetchedAt: 0,
    }
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('ui.status', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('ui.open', () => ({ value: { isPlaced: true } }))
    on('ui.close', () => ({ value: undefined }))
    on('fs.list', () => ({ value: [] }))
    on('tool.call', async ($, e, next) => {
      void next
      return { result: 'reached-bottom' }
    })
    on('state.set', { plugin: 'flow-deck', key: 'git' }, ($, e, next) => {
      // 恒以真实快照顶替（session.start 清空与轮询失败退避的 null 写入一并顶替，
      // 模拟轮询持续取到 git 数据的稳定状态）
      return next({ ...e, value: gitSnapshot })
    })
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await $.tool.call({ tool: 'Edit', file_path: 'C:\\repo\\docs/c.md' })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'p', batch: 'B1', files: ['docs/c.md', 'hooks/a.ts'] })
    expect((await $.command.run({ command: 'deck', args: 'tree' })).text).toBe('已切到文件树页签。')
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Deck'),
    })
    expect(await ui.find({ text: /▍改动 · 3/ })).not.toBeUndefined()
    expect(await ui.find({ text: /● docs\/c\.md/ })).not.toBeUndefined()
    expect(await ui.find({ text: /○ hooks\/a\.ts/ })).not.toBeUndefined()
    expect(await ui.find({ text: /○ plans\/b\.md/ })).not.toBeUndefined()
    expect(await ui.find({ text: /◆ 本批/ })).not.toBeUndefined()
    await ui.unmount()
    void clock
  })

  test('/deck toggle 开关面板，参数切页签不误关', async ($, on) => {
    let open = false
    let opened = 0
    let closed = 0
    on('ui.panes', () => ({ value: open ? [{ id: 'deck', title: 'Deck', isShown: true, isFocused: false, isPlaced: true }] : [] }))
    on('ui.open', { id: 'deck' }, () => {
      open = true
      opened++
      return { value: { isPlaced: true } }
    })
    on('ui.close', { id: 'deck' }, () => {
      open = false
      closed++
      return { value: undefined }
    })
    expect((await $.command.run({ command: 'deck', args: '' })).text).toContain('已打开面板')
    expect(opened).toBe(1)
    expect((await $.command.run({ command: 'deck', args: 'tree' })).text).toBe('已切到文件树页签。')
    expect(closed).toBe(0)
    expect((await $.command.run({ command: 'deck', args: 'flow' })).text).toBe('已切到工作面板页签。')
    expect((await $.command.run({ command: 'deck', args: '' })).text).toBe('已关闭 flow-deck 面板。')
    expect(closed).toBe(1)
  })

  test('/deck 打开未停靠时如实报告引擎原因', async ($, on) => {
    on('ui.panes', () => ({ value: [] }))
    on('ui.open', () => ({ value: { isPlaced: false, reason: 'below its floor of 110 columns (now 80)' } }))
    const opened = await $.command.run({ command: 'deck', args: '' })
    expect(opened.text).toContain('面板暂未停靠')
    expect(opened.text).toContain('110 columns')
    // 页签直达分支同样转述
    const tree = await $.command.run({ command: 'deck', args: 'tree' })
    expect(tree.text).toContain('面板暂未停靠')
  })

  test('子代理面板区分加载中、空清单、刷新失败和过期快照', async ($, on) => {
    let snapshot: AgentSnapshot = { agents: [], loaded: false, error: false }
    on('state.set', { plugin: 'flow-deck', key: 'agents' }, ($, e, next) => next({ ...e, value: snapshot }))
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    for (const [loaded, error, pattern] of [
      [false, false, /正在读取当前会话/],
      [true, false, /当前会话暂无子代理/],
      [false, true, /暂未取得子代理状态/],
      [true, true, /上次快照，状态可能已过期/],
    ] as const) {
      snapshot = { agents: [], loaded, error }
      await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
      const ui = await $.ui.mount({
        plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
        props: paneProps('Flow 当前任务'),
      })
      expect(await ui.find({ text: pattern })).not.toBeUndefined()
      await ui.unmount()
    }
  })

  test('子代理状态、任务与父代理关系在终端和桌面宽窄面板中可见', async ($, on) => {
    const snapshot: AgentSnapshot = {
      loaded: true, error: false,
      agents: [
        { id: 'a1', name: 'executor', type: 'runner', description: '实现面板', status: 'running' },
        { id: 'a2', type: 'reviewer', description: '检查边界', status: 'failed', parentId: 'a1', spawnedBy: 'workflow' },
        { id: 'a3', type: 'runner', description: '定向测试', status: 'completed' },
        { id: 'a4', type: 'runner', description: '取消任务', status: 'killed' },
        { id: 'a5', type: 'runner', description: '等待任务', status: 'queued', parentId: 'missing-parent' },
      ],
    }
    on('state.set', { plugin: 'flow-deck', key: 'agents' }, ($, e, next) => next({ ...e, value: snapshot }))
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    for (const surface of ['terminal', 'desktop'] as const) {
      for (const bodyColumns of [28, 80]) {
        const ui = await $.ui.mount({
          plugin: 'flow-deck', surface, component: 'Pane', requestId: 'deck',
          props: { ...paneProps('Flow 当前任务'), bodyColumns },
        })
        for (const text of [/运行中 1 · 完成 1 · 失败 1 · 停止 1 · 其他 1/, /● 运行中 · executor/,
          /✗ 失败 · 检查边界/, /✓ 已完成/, /○ 已停止/, /○ queued/, /任务：实现面板/,
          /父代理：executor/, /父代理：missing-parent/, /来源插件：workflow/]) {
          expect(await ui.find({ text })).not.toBeUndefined()
        }
        const boxes = await ui.findAll({ type: 'Box' })
        expect(boxes.some(box => box.props.borderStyle === 'round')).toBe(bodyColumns >= 44)
        await ui.unmount()
      }
    }
  })

  test('只有路线图声明时提示无当前任务，不显示实施面板', async $ => {
    await $.tool.call({
      tool: 'mcp__flow-deck__flow_deps', plan: '待实施方案',
      batches: [{ batch: 'B1', dependsOn: [] }],
    })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow'),
    })
    expect(await ui.find({ text: /当前无方案迭代或实施任务/ })).not.toBeUndefined()
    expect(await ui.find({ text: /执行 DAG/ })).toBeUndefined()
    await ui.unmount()
  })

  test('批次收口后撤下执行卡片和边界，提示无当前任务', async $ => {
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'demo', batch: 'B1', files: ['a.ts'] })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B1', phase: '执行' })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B1', phase: '收口' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow'),
    })
    expect(await ui.find({ text: /当前无方案迭代或实施任务/ })).not.toBeUndefined()
    expect(await ui.find({ text: /当前执行|◇ 边界/ })).toBeUndefined()
    await ui.unmount()
  })

  test('空状态给出提示文案', async $ => {
    const ui = await $.ui.mount({
      plugin: 'flow-deck',
      surface: 'terminal',
      component: 'Pane',
      requestId: 'deck',
      props: paneProps('Flow 评审仪表盘'),
    })
    expect(await ui.find({ text: /当前无方案迭代或实施任务/ })).not.toBeUndefined()
    await ui.unmount()
  })

  test('基线回归：default 皮肤空态渲染树与改动前一致', { options: { artDirection: 'default', companion: 'off' } }, async ($, on) => {
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow 当前任务'),
    })
    expect(JSON.stringify(stableTree(await ui.findAll({})))).toBe(EMPTY_PANE_BASELINE)
    await ui.unmount()
  })

  test('describeExecution 战报格式：closure 存在升级为战报，null 显示 — 与真实 0 可区分', () => {
    // 无 closure 保持原格式
    expect(describeExecution({ plan: 'demo', batch: 'B2', phase: '执行', updatedAt: 0 }))
      .toBe('demo · B2 · 执行')
    // 战报格式：文件数注明声明边界、分钟注明自首次边界声明
    expect(describeExecution({
      plan: 'demo', batch: 'B2', phase: '收口', updatedAt: 0,
      closure: { files: 3, added: 842, removed: 96, minutes: 41 },
    })).toBe('B2 · 3 文件（声明边界） · +842 −96 · 41 分钟（自首次边界声明） · 全绿')
    // 统计不可用/无首报起点 → —（不折算 0）
    expect(describeExecution({
      plan: 'demo', batch: 'B2', phase: '收口', updatedAt: 0,
      closure: { files: 3, added: null, removed: null, minutes: null },
    })).toBe('B2 · 3 文件（声明边界） · — · — · 全绿')
    // 真实 0 显示数值，两态可区分
    expect(describeExecution({
      plan: 'demo', batch: 'B2', phase: '收口', updatedAt: 0,
      closure: { files: 2, added: 0, removed: 0, minutes: 0 },
    })).toBe('B2 · 2 文件（声明边界） · +0 −0 · 0 分钟（自首次边界声明） · 全绿')
    // statsAt 存在附统计截至 HH:MM
    expect(describeExecution({
      plan: 'demo', batch: 'B2', phase: '收口', updatedAt: 0,
      closure: { files: 1, added: 1, removed: 1, minutes: 1, statsAt: Date.now() },
    })).toMatch(/统计截至 \d{2}:\d{2}$/)
  })

  test('clipboardArgv 平台命令表：win32 锁编码链与 ReadToEnd 保真口径，darwin/linux 直用系统命令，未适配返回 null', () => {
    // win32：显式设 UTF8 输入编码 + ReadToEnd 单串（clip.exe 会被 OEM 代码页误解码中文、$Input 逐行
    // 管道会把行尾归一成 CRLF，均不可用）——锁死命令全文防误改回任一劣化口径
    const win = clipboardArgv('win32')
    expect(win?.slice(0, 3)).toEqual(['powershell.exe', '-NoProfile', '-Command'])
    expect(win?.[3]).toContain('[Console]::InputEncoding=[System.Text.Encoding]::UTF8')
    expect(win?.[3]).toContain('Set-Clipboard -Value ([Console]::In.ReadToEnd())')
    // darwin / linux：系统自带命令
    expect(clipboardArgv('darwin')).toEqual(['pbcopy'])
    expect(clipboardArgv('linux')).toEqual(['xclip', '-selection', 'clipboard'])
    // 未适配平台：null → 按钮路径 toast 报错不抛
    expect(clipboardArgv('freebsd')).toBeNull()
  })

  test('envPlatform 环境变量推断平台：OS=Windows_NT 判 win，HOME 前缀判 mac/linux，余者未适配', () => {
    // Windows 恒有 OS=Windows_NT（引擎沙箱无 process 全局，环境变量是唯一平台信号）
    expect(envPlatform({ OS: 'Windows_NT' })).toBe('win32')
    expect(envPlatform({ OS: 'Windows_NT', HOME: 'C:\\Users\\tu' })).toBe('win32')
    // mac 的 HOME 以 /Users/ 开头；Linux 为 /home/<user> 或 /root
    expect(envPlatform({ HOME: '/Users/tu' })).toBe('darwin')
    expect(envPlatform({ HOME: '/home/tu' })).toBe('linux')
    expect(envPlatform({ HOME: '/root' })).toBe('linux')
    // 未知环境（OS 缺失且 HOME 形态不识别）→ 未适配
    expect(envPlatform({})).toBe('other')
    expect(envPlatform({ HOME: '/opt/somewhere' })).toBe('other')
  })

  test('空态面包屑：跨会话恢复的上次执行显示在无任务面板', async ($, on) => {
    mock.clock(on)
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('store.get', () => ({ value: { plan: 'demo', batch: 'B2', phase: '收口', updatedAt: 1 } }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow 当前任务'),
    })
    expect(await ui.find({ text: /上次执行：demo · B2 · 收口/ })).not.toBeUndefined()
    await ui.unmount()
  })

  test('session.start 恢复 store 的 progress 与 deps：同方案实施任务面板接续渲染 DAG', { options: { artDirection: 'default' } }, async ($, on) => {
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    // 跨会话恢复替身：store.get 载荷带 key（实测 {"key":"lastExecution"} 形态），按 key 分流
    on('store.get', (_$, e) => ({
      value: e.key === 'progressMap' ? { 'demo#B1': '收口' }
        : e.key === 'depsGraph' ? { plan: 'demo', batches: [{ batch: 'B1' }, { batch: 'B2', dependsOn: ['B1'] }] }
        : undefined,
    }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_task', kind: 'implement', plan: 'demo' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow 评审仪表盘'),
    })
    expect(await ui.find({ text: /▍执行 DAG（demo）/ })).not.toBeUndefined()
    expect(await ui.find({ type: 'Text', text: '✓ B1' })).not.toBeUndefined()
    expect(await ui.find({ type: 'Text', text: '○ B2' })).not.toBeUndefined()
    expect(await ui.find({ text: /1\/2 收口/ })).not.toBeUndefined()
    // 恢复状态照常着色：done 绿、pending dim
    const doneLine = await ui.find({ type: 'Text', text: '✓ B1' })
    expect(doneLine?.props.color).toBe('success')
    const waitLine = await ui.find({ type: 'Text', text: '○ B2' })
    expect(waitLine?.props.dimColor).toBe(true)
    await ui.unmount()
  })

  test('store 坏形状恢复降级为空：无 DAG 区块、无异常，行为同清空现状', { options: { artDirection: 'default' } }, async ($, on) => {
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    // progress 整体非对象、deps 缺合法 plan：双双降级（空 map / null）
    on('store.get', (_$, e) => ({
      value: e.key === 'progressMap' ? 'garbage'
        : e.key === 'depsGraph' ? { plan: 123 }
        : undefined,
    }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_task', kind: 'implement', plan: 'demo' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow 评审仪表盘'),
    })
    expect(await ui.find({ text: /执行 DAG/ })).toBeUndefined()
    // 面板照常渲染任务标题，无异常中断
    expect(await ui.find({ text: /工作面板 · 方案实施/ })).not.toBeUndefined()
    await ui.unmount()
  })

  test('恢复数据拓扑下推渲染：B2 收口 B1 无记录 → B1 推导 done 且文本「收口」', { options: { artDirection: 'default' } }, async ($, on) => {
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('store.get', (_$, e) => ({
      value: e.key === 'progressMap' ? { 'demo#B2': '收口' }
        : e.key === 'depsGraph' ? { plan: 'demo', batches: [{ batch: 'B1' }, { batch: 'B2', dependsOn: ['B1'] }] }
        : undefined,
    }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_task', kind: 'implement', plan: 'demo' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow 评审仪表盘'),
    })
    // B1 无记录但被下推：状态符号与文本行同源（done 且「收口」），n/m 计数含推导节点
    const doneLine = await ui.find({ type: 'Text', text: '✓ B1' })
    expect(doneLine?.props.color).toBe('success')
    expect(await ui.find({ text: /收口 · 起点/ })).not.toBeUndefined()
    expect(await ui.find({ text: /待执行/ })).toBeUndefined()
    expect(await ui.find({ text: /2\/2 收口/ })).not.toBeUndefined()
    await ui.unmount()
  })

  test('任务数据与子代理状态同屏，面板内刷新按钮可触发全部重取', async ($, on) => {
    const clock = mock.clock(on)
    let calls = 0
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    const snapshot = {
      loaded: true, error: false,
      agents: [{ id: 'a1', name: 'executor', type: 'runner', description: '定向测试', status: 'running' }],
    }
    on('state.set', { plugin: 'flow-deck', key: 'agents' }, ($, e, next) => next({ ...e, value: snapshot }))
    on('agent.list', () => {
      calls++
      return { value: [{ id: 'a1', name: 'executor', type: 'runner', description: '定向测试', status: 'running' }] }
    })
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '执行' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow 当前任务'),
    })
    expect(await ui.find({ text: /当前执行 · demo/ })).not.toBeUndefined()
    expect(await ui.find({ text: /● 运行中 · executor/ })).not.toBeUndefined()
    const buttons = await ui.findAll({ type: 'Button' })
    const refresh = buttons.find(button => button.props.key === 'flow-refresh')
    expect(refresh?.props.hotkey).toBe('r')
    expect(refresh?.props.key).toBe('flow-refresh')
    // 页签行三枚数字热键按钮也在树上
    expect(buttons.some(button => button.props.hotkey === '1')).toBe(true)
    await $.ui.press({ plugin: 'flow-deck', key: 'flow-refresh', requestId: 'deck', surface: 'terminal' })
    await clock.settle()
    expect(calls).toBeGreaterThan(0)
    await ui.unmount()
  })

  test('达标方案折叠为一行，未达标方案照常逐个展示', async ($, on) => {
    const clock = mock.clock(on)
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('ui.status', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    const files = new Map<string, string>([
      ['.plan-iterate/demo/state.json', '{"backend":"glm","round":2}'],
      ['.plan-iterate/demo/review-R1.json', '{"score":7,"issues":[]}'],
      ['.plan-iterate/demo/review-R2.json', '{"score":9,"issues":[]}'],
    ])
    const dirs = new Map<string, Array<{ name: string; kind: 'file' | 'dir'; size: number; mtimeMs: number; isLink: boolean }>>([
      ['', [{ name: '.plan-iterate', kind: 'dir', size: 0, mtimeMs: 0, isLink: false }]],
      ['.plan-iterate', [{ name: 'demo', kind: 'dir', size: 0, mtimeMs: 0, isLink: false }]],
      ['.plan-iterate/demo', [
        { name: 'review-R1.json', kind: 'file', size: 22, mtimeMs: 2, isLink: false },
        { name: 'review-R2.json', kind: 'file', size: 22, mtimeMs: 3, isLink: false },
        { name: 'state.json', kind: 'file', size: 28, mtimeMs: 1, isLink: false },
      ]],
    ])
    // 引擎把 $.fs.list/read 的路径解析为相对插件 cwd 的绝对路径再转发；从路径中
    // 提取 .plan-iterate 起的相对部分做分发（无该段的视为根目录列表）
    const relOf = (value: unknown): string => {
      const norm = typeof value === 'string' ? value.replaceAll('\\', '/') : ''
      const at = norm.indexOf('.plan-iterate')
      return at === -1 ? '' : norm.slice(at)
    }
    on('fs.list', ($, e) => ({ value: dirs.get(relOf(e.path)) ?? [] }))
    on('fs.read', ($, e) => ({ value: files.get(relOf(e.path)) ?? '' }))
    on('ui.log', () => ({ value: undefined }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await clock.settle()
    await $.tool.call({ tool: 'mcp__flow-deck__flow_task', kind: 'iterate', plan: 'demo' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow 当前任务'),
    })
    expect(await ui.find({ text: /✓ 已达标 1 个方案（已折叠）/ })).not.toBeUndefined()
    expect(await ui.find({ text: /● demo/ })).toBeUndefined()
    expect(await ui.find({ text: /最新 R2\/5 · 评审 1 · 待达标 0 · 已达标 1/ })).not.toBeUndefined()
    await ui.unmount()
  })

  test('未达标评审卡画达标刻度条，▏ 固定在 8.5 位置', async ($, on) => {
    const clock = mock.clock(on)
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('ui.status', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    const files = new Map<string, string>([
      ['.plan-iterate/beta/state.json', '{"backend":"glm","round":3}'],
      ['.plan-iterate/beta/review-R2.json', '{"score":6.5,"issues":[{"severity":"P1"}]}'],
      ['.plan-iterate/beta/review-R3.json', '{"score":6.8,"issues":[{"severity":"P1"}]}'],
    ])
    const dirs = new Map<string, Array<{ name: string; kind: 'file' | 'dir'; size: number; mtimeMs: number; isLink: boolean }>>([
      ['', [{ name: '.plan-iterate', kind: 'dir', size: 0, mtimeMs: 0, isLink: false }]],
      ['.plan-iterate', [{ name: 'beta', kind: 'dir', size: 0, mtimeMs: 0, isLink: false }]],
      ['.plan-iterate/beta', [
        { name: 'review-R2.json', kind: 'file', size: 44, mtimeMs: 1, isLink: false },
        { name: 'review-R3.json', kind: 'file', size: 44, mtimeMs: 2, isLink: false },
        { name: 'state.json', kind: 'file', size: 28, mtimeMs: 0, isLink: false },
      ]],
    ])
    const relOf = (value: unknown): string => {
      const norm = typeof value === 'string' ? value.replaceAll('\\', '/') : ''
      const at = norm.indexOf('.plan-iterate')
      return at === -1 ? '' : norm.slice(at)
    }
    on('fs.list', ($, e) => ({ value: dirs.get(relOf(e.path)) ?? [] }))
    on('fs.read', ($, e) => ({ value: files.get(relOf(e.path)) ?? '' }))
    on('ui.log', () => ({ value: undefined }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await clock.settle()
    await $.tool.call({ tool: 'mcp__flow-deck__flow_task', kind: 'iterate', plan: 'beta' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow 当前任务'),
    })
    expect(await ui.find({ text: /● beta/ })).not.toBeUndefined()
    expect(await ui.find({ type: 'Text', text: '━━━━━━━──▏─' })).not.toBeUndefined()
    expect(await ui.find({ text: 'R2 6.5 · R3 6.8' })).not.toBeUndefined()
    expect(await ui.find({ text: /最新 R3\/5 · 评审 1 · 待达标 1 · 已达标 0/ })).not.toBeUndefined()
    await ui.unmount()
  })

  test('点工作面板方案名把方案文档装入文件查看器：卡片走 plan_path，实施标题走 plans/ 约定兜底', async ($, on) => {
    const clock = mock.clock(on)
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('ui.status', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    const toasts: string[] = []
    on('ui.toast', ($, e) => {
      toasts.push(e.text)
      return { value: undefined }
    })
    const files = new Map<string, string>([
      ['.plan-iterate/beta/state.json', JSON.stringify({ backend: 'glm', round: 1, plan_path: 'C:\\repo\\plans\\work\\beta.md' })],
      ['.plan-iterate/beta/review-R1.json', JSON.stringify({ score: 6.8, issues: [{ severity: 'P1' }] })],
      ['plans/work/beta.md', '# 方案\n内容'],
      ['plans/work/impl.md', '# 实施\n内容'],
    ])
    const dirs = new Map<string, Array<{ name: string; kind: 'file' | 'dir'; size: number; mtimeMs: number; isLink: boolean }>>([
      ['', [
        { name: '.plan-iterate', kind: 'dir', size: 0, mtimeMs: 0, isLink: false },
        { name: 'plans', kind: 'dir', size: 0, mtimeMs: 0, isLink: false },
      ]],
      ['.plan-iterate', [{ name: 'beta', kind: 'dir', size: 0, mtimeMs: 0, isLink: false }]],
      ['.plan-iterate/beta', [
        { name: 'review-R1.json', kind: 'file', size: 40, mtimeMs: 2, isLink: false },
        { name: 'state.json', kind: 'file', size: 60, mtimeMs: 1, isLink: false },
      ]],
      ['plans', [{ name: 'work', kind: 'dir', size: 0, mtimeMs: 0, isLink: false }]],
      ['plans/work', [
        { name: 'beta.md', kind: 'file', size: 12, mtimeMs: 4, isLink: false },
        { name: 'impl.md', kind: 'file', size: 12, mtimeMs: 5, isLink: false },
      ]],
    ])
    // 引擎把 $.fs.list/read 的路径规范化为绝对路径转发；剥出 .plan-iterate 或 plans 起的相对段分发
    const relOf = (value: unknown): string => {
      const norm = typeof value === 'string' ? value.replaceAll('\\', '/') : ''
      const at = Math.max(norm.indexOf('.plan-iterate'), norm.indexOf('plans'))
      return at === -1 ? '' : norm.slice(at)
    }
    on('fs.list', ($, e) => ({ value: dirs.get(relOf(e.path)) ?? [] }))
    on('fs.read', ($, e) => ({ value: files.get(relOf(e.path)) ?? '' }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await clock.settle()
    await $.tool.call({ tool: 'mcp__flow-deck__flow_task', kind: 'iterate', plan: 'beta' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow 当前任务'),
    })
    expect(await ui.find({ text: /● beta/ })).not.toBeUndefined()
    // 评审卡片：state.json 的 plan_path（绝对路径剥 cwd 前缀后装载）
    await $.ui.press({ plugin: 'flow-deck', key: 'plan-open-.plan-iterate/beta', requestId: 'deck', surface: 'terminal' })
    expect(await ui.find({ text: /▍文件查看器 · plans\/work\/beta\.md · 1 节 · 2 行/ })).not.toBeUndefined()
    // 实施任务标题：无评审目录，按 plans/<插件>/<方案名>.md 约定兜底
    await $.ui.press({ plugin: 'flow-deck', key: 'tab-flow', requestId: 'deck', surface: 'terminal' })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_task', kind: 'implement', plan: 'impl' })
    // 先确认面板已切到新任务（避免按压命中旧渲染树的闭包）
    expect(await ui.find({ text: /▍工作面板 · 方案实施 · impl/ })).not.toBeUndefined()
    await $.ui.press({ plugin: 'flow-deck', key: 'task-plan-open', requestId: 'deck', surface: 'terminal' })
    await clock.settle()
    expect(await ui.find({ text: /▍文件查看器 · plans\/work\/impl\.md · 1 节 · 2 行/ })).not.toBeUndefined()
    // 两处都找不到时 toast 说明，不切页签
    await $.ui.press({ plugin: 'flow-deck', key: 'tab-flow', requestId: 'deck', surface: 'terminal' })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_task', kind: 'implement', plan: 'ghost' })
    expect(await ui.find({ text: /▍工作面板 · 方案实施 · ghost/ })).not.toBeUndefined()
    await $.ui.press({ plugin: 'flow-deck', key: 'task-plan-open', requestId: 'deck', surface: 'terminal' })
    await clock.settle()
    expect(toasts.some(text => text.includes('未找到「ghost」的方案文档'))).toBe(true)
    await ui.unmount()
  })

  test('/tree 面板：改动清单去重、批次标注、目录导航与开关', async ($, on) => {
    const clock = mock.clock(on)
    const upPanes: string[] = []
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('ui.status', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: upPanes.map(id => ({ id })) }))
    on('ui.open', ($, e) => {
      if (!upPanes.includes(e.id)) upPanes.push(e.id)
      return { value: { isPlaced: true } }
    })
    on('ui.close', ($, e) => {
      const at = upPanes.indexOf(e.id)
      if (at !== -1) upPanes.splice(at, 1)
      return { value: undefined }
    })
    // 底层应答：插件守卫钩子放行（next）时由本钩子收口
    on('tool.call', async ($, e, next) => {
      void next
      return { result: 'reached-bottom' }
    })
    const dirs = new Map<string, Array<{ name: string; kind: 'file' | 'dir'; size: number; mtimeMs: number; isLink: boolean }>>([
      ['', [
        { name: 'readme.md', kind: 'file', size: 1, mtimeMs: 1, isLink: false },
        { name: 'src', kind: 'dir', size: 0, mtimeMs: 1, isLink: false },
      ]],
      ['src', [{ name: 'index.ts', kind: 'file', size: 1, mtimeMs: 1, isLink: false }]],
    ])
    // 引擎把 $.fs.list 的路径解析为相对插件 cwd 的绝对路径转发；按尾段识别目标目录
    const relOf = (value: unknown): string => {
      if (typeof value !== 'string') return ''
      const norm = value.replaceAll('\\', '/')
      return norm.endsWith('/src') ? 'src' : ''
    }
    on('fs.list', ($, e) => ({ value: dirs.get(relOf(e.path)) ?? [] }))
    on('fs.read', ($, e) => {
      const norm = typeof e.path === 'string' ? e.path.replaceAll('\\', '/') : ''
      if (!norm.endsWith('src/a.ts')) throw new Error('ENOENT: ' + String(e.path))
      return { value: '# 标题\n正文' }
    })
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await $.tool.call({ tool: 'Edit', file_path: 'C:\\repo\\src\\a.ts' })
    await $.tool.call({ tool: 'Edit', file_path: 'C:\\repo\\src\\a.ts' })
    await $.tool.call({ tool: 'Edit', file_path: 'C:\\repo\\readme.md' })
    expect((await $.command.run({ command: 'deck', args: 'tree' })).text).toContain('文件树页签')
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('文件'),
    })
    expect(await ui.find({ text: /▍文件树 · 工作目录/ })).not.toBeUndefined()
    expect(await ui.find({ text: /▍改动 · 2/ })).not.toBeUndefined()
    expect(await ui.find({ text: /src\/a\.ts/ })).not.toBeUndefined()
    expect(await ui.find({ text: /src\// })).not.toBeUndefined()
    // 目录行点击进入该目录
    await $.ui.press({ plugin: 'flow-deck', key: 'dir-open-src', requestId: 'deck', surface: 'terminal' })
    await clock.settle()
    expect(await ui.find({ text: /▍文件树 · src/ })).not.toBeUndefined()
    expect(await ui.find({ text: /index\.ts/ })).not.toBeUndefined()
    // 「← 上级」回工作目录
    await $.ui.press({ plugin: 'flow-deck', key: 'dir-up', requestId: 'deck', surface: 'terminal' })
    await clock.settle()
    expect(await ui.find({ text: /▍文件树 · 工作目录/ })).not.toBeUndefined()
    await $.ui.press({ plugin: 'flow-deck', key: 'dir-open-src', requestId: 'deck', surface: 'terminal' })
    await clock.settle()
    // 批次边界内文件标注（边界声明本身不改变目录列表）
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'p', batch: 'B1', files: ['src/index.ts'] })
    expect(await ui.find({ text: /◆ 本批/ })).not.toBeUndefined()
    // 点击改动清单文件行 → 切到文档页签并装载该文件
    await $.ui.press({ plugin: 'flow-deck', key: 'file-open-src/a.ts', requestId: 'deck', surface: 'terminal' })
    expect(await ui.find({ text: /▍文件查看器 · src\/a\.ts · 1 节 · 2 行/ })).not.toBeUndefined()
    await ui.unmount()
    // /deck tree 语义为切页签：已开时不关闭；关闭统一走无参 /deck
    expect((await $.command.run({ command: 'deck', args: 'tree' })).text).toBe('已切到文件树页签。')
    expect((await $.command.run({ command: 'deck', args: '' })).text).toBe('已关闭 flow-deck 面板。')
  })

  test('改动记录上限 50：挤出最旧，重复路径不重复记录', async ($, on) => {
    const clock = mock.clock(on)
    void clock
    let lastTouched: { path: string; at: number }[] = []
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('ui.status', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('tool.call', async ($, e, next) => {
      void next
      return { result: 'reached-bottom' }
    })
    on('state.set', { plugin: 'flow-deck', key: 'touched' }, ($, e, next) => {
      lastTouched = e.value as { path: string; at: number }[]
      return next(e)
    })
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    for (let i = 0; i < 51; i++) {
      await $.tool.call({ tool: 'Edit', file_path: `C:\\repo\\f${i}.ts` })
    }
    expect(lastTouched).toHaveLength(50)
    expect(lastTouched[0]?.path).toBe('f1.ts')
    expect(lastTouched.at(-1)?.path).toBe('f50.ts')
  })

  test('实施上报超时未续报时提示疑似停滞，同值不重复写状态', { options: { artDirection: 'default' } }, async ($, on) => {
    const clock = mock.clock(on)
    let stallWrites = 0
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    on('state.set', { plugin: 'flow-deck', key: 'currentTask' }, ($, e, next) =>
      next({ ...e, value: { kind: 'implement', plan: 'demo', batch: 'B2' } }))
    on('state.set', { plugin: 'flow-deck', key: 'execution' }, ($, e, next) =>
      next({ ...e, value: { plan: 'demo', batch: 'B2', phase: '执行', updatedAt: Date.now() - 31 * 60_000 } }))
    on('state.set', { plugin: 'flow-deck', key: 'stall' }, ($, e, next) => {
      stallWrites++
      return next(e)
    })
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow 当前任务'),
    })
    expect(await ui.find({ text: /疑似停滞/ })).toBeUndefined()
    await clock.advance(2000)
    expect(await ui.find({ text: /疑似停滞 · 距上次上报 31 分钟/ })).not.toBeUndefined()
    await clock.advance(2000)
    // 停滞分钟数未跨分钟变化：不应重复写状态触发重绘
    expect(stallWrites).toBe(2)
    await ui.unmount()
  })

  test('flow_report 缺必填字段时返回错误结果', async $ => {
    const result = await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo' })
    expect(result.isError).toBe(true)
    expect(result.result).toBe('plan、batch、phase 为必填字符串')
  })

  test('收口组装：全绿收口写通关卡，行数为声明边界合计，minutes 自首报起点', async ($, on) => {
    const clock = mock.clock(on)
    const closureWrites: unknown[] = []
    const gitSnapshot = {
      branch: 'main', upstream: null, ahead: 0, behind: 0,
      staged: [], unstaged: [], untracked: [], conflicts: [],
      added: 842, removed: 96, fetchedAt: 777000,
      byPath: { 'src/a.ts': [800, 90], 'src/b.ts': [42, 6], 'docs/c.md': [0, 0] },
      numstatSides: { worktree: 'ok', cached: 'ok' },
    }
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('state.set', { plugin: 'flow-deck', key: 'git' }, ($, e, next) => {
      // session.start 的清空写入顶替为快照，模拟轮询已取到 git 数据
      return next({ ...e, value: gitSnapshot })
    })
    on('state.set', { plugin: 'flow-deck', key: 'closureCard' }, ($, e, next) => {
      closureWrites.push(e.value)
      return next(e)
    })
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    // 声明边界：绝对路径与反斜杠分隔符写法各一，验证归一化贯通（byPath 键为小写正斜杠）
    await $.tool.call({
      tool: 'mcp__flow-deck__flow_batch', plan: 'demo', batch: 'B2',
      files: ['src/a.ts', 'C:\\REPO\\SRC\\B.TS', 'docs/c.md'],
    })
    clock.set(clock.now() + 120_000)
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '执行' })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '验证', testsPassed: 1, testsTotal: 3 })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '验证', testsPassed: 3, testsTotal: 3 })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '收口', testsPassed: 3, testsTotal: 3 })
    const card = closureWrites.at(-1) as { plan: string; batch: string; closure: { files: number; added: number | null; removed: number | null; minutes: number | null; statsAt?: number } }
    // 引擎 mock.clock 不操纵 Date.now（clock.set 仅驱动定时器队列），声明与收口同秒完成 →
    // minutes 为真实流逝取整 0；「起点存在（0 而非 null）」即为可断言口径，起点推进的精确
    // 差值断言留待真实时长（>1 分钟）场景或代码评审核对 firstReportAt 三态分支
    expect(card).toEqual({
      plan: 'demo', batch: 'B2',
      closure: { files: 3, added: 842, removed: 96, minutes: 0, statsAt: 777000 },
    })
  })

  test('统计三态：git 快照为 null → —；byPath 无 scope 文件 → 真实 0 且 statsAt 有值', async ($, on) => {
    const closureWrites: unknown[] = []
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('state.set', { plugin: 'flow-deck', key: 'git' }, ($, e, next) => next(e))
    on('state.set', { plugin: 'flow-deck', key: 'closureCard' }, ($, e, next) => {
      closureWrites.push(e.value)
      return next(e)
    })
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    // 场景 a：gitStatus 为 null（轮询失败退避/待首轮查询）→ 统计不可用
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'demo', batch: 'B2', files: ['src/a.ts'] })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '收口', testsPassed: 1, testsTotal: 1 })
    expect(closureWrites.at(-1)).toEqual({
      plan: 'demo', batch: 'B2',
      closure: { files: 1, added: null, removed: null, minutes: 0 },
    })
  })

  test('统计可用但 byPath 不含 scope 文件 → 真实 0（与 — 可区分）且 statsAt 有值', async ($, on) => {
    const closureWrites: unknown[] = []
    const sparseSnapshot = {
      branch: 'main', upstream: null, ahead: 0, behind: 0,
      staged: [], unstaged: [], untracked: [], conflicts: [],
      added: 5, removed: 1, fetchedAt: 888000,
      byPath: { 'other.ts': [5, 1] },
      numstatSides: { worktree: 'ok', cached: 'ok' },
    }
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('state.set', { plugin: 'flow-deck', key: 'git' }, ($, e, next) => next({ ...e, value: sparseSnapshot }))
    on('state.set', { plugin: 'flow-deck', key: 'closureCard' }, ($, e, next) => {
      closureWrites.push(e.value)
      return next(e)
    })
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'demo', batch: 'B3', files: ['src/a.ts'] })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B3', phase: '收口', testsPassed: 1, testsTotal: 1 })
    expect(closureWrites.at(-1)).toEqual({
      plan: 'demo', batch: 'B3',
      closure: { files: 1, added: 0, removed: 0, minutes: 0, statsAt: 888000 },
    })
  })

  test('失败收口：tests 不全绿必不写卡且清既有卡', async ($, on) => {
    const closureWrites: unknown[] = []
    const gitSnapshot = {
      branch: 'main', upstream: null, ahead: 0, behind: 0,
      staged: [], unstaged: [], untracked: [], conflicts: [],
      added: 1, removed: 1, fetchedAt: 1,
      byPath: { 'src/a.ts': [1, 1] },
      numstatSides: { worktree: 'ok', cached: 'ok' },
    }
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('state.set', { plugin: 'flow-deck', key: 'git' }, ($, e, next) => next({ ...e, value: gitSnapshot }))
    on('state.set', { plugin: 'flow-deck', key: 'closureCard' }, ($, e, next) => {
      closureWrites.push(e.value)
      return next(e)
    })
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'demo', batch: 'B2', files: ['src/a.ts'] })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '收口', testsPassed: 3, testsTotal: 3 })
    expect(closureWrites.at(-1)).not.toBeNull()
    // 不全绿的收口 → 清卡（且不写新卡）
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '收口', testsPassed: 2, testsTotal: 3 })
    expect(closureWrites.at(-1)).toBeNull()
  })

  test('收口边界缺失或他批残留：closure 整体不写入，store 值不含 closure', async ($, on) => {
    const closureWrites: unknown[] = []
    const gitSnapshot = {
      branch: 'main', upstream: null, ahead: 0, behind: 0,
      staged: [], unstaged: [], untracked: [], conflicts: [],
      added: 1, removed: 1, fetchedAt: 1,
      byPath: { 'src/a.ts': [1, 1] },
      numstatSides: { worktree: 'ok', cached: 'ok' },
    }
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('state.set', { plugin: 'flow-deck', key: 'git' }, ($, e, next) => next({ ...e, value: gitSnapshot }))
    on('state.set', { plugin: 'flow-deck', key: 'closureCard' }, ($, e, next) => {
      closureWrites.push(e.value)
      return next(e)
    })
    // store 出口经 $.store.set 持久化，测试引擎无该设施（仅 store.get 钩子可应答），
    // store 值断言留待会话内端到端验证（同 register.test.ts 尾注既有先例）。
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    // 场景 a：无边界声明（scope null）直接收口
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '收口', testsPassed: 1, testsTotal: 1 })
    expect(closureWrites.at(-1)).toBeNull()
    // 场景 b：scope 被更早的异批报告清掉后收口（batchScope 为 null）
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'demo', batch: 'B2', files: ['src/a.ts'] })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B9', phase: '执行' })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '收口', testsPassed: 1, testsTotal: 1 })
    expect(closureWrites.at(-1)).toBeNull()
    // 场景 c：scope 为他批残留（plan/batch 不匹配）
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'other', batch: 'B1', files: ['src/a.ts'] })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '收口', testsPassed: 1, testsTotal: 1 })
    expect(closureWrites.at(-1)).toBeNull()
  })

  test('清卡统一规则：同 plan#batch 全绿重复收口三出口幂等保留（重放），他批错配清卡', async ($, on) => {
    const closureWrites: unknown[] = []
    const lastRunWrites: unknown[] = []
    const gitSnapshot = {
      branch: 'main', upstream: null, ahead: 0, behind: 0,
      staged: [], unstaged: [], untracked: [], conflicts: [],
      added: 3, removed: 2, fetchedAt: 5,
      byPath: { 'src/a.ts': [3, 2] },
      numstatSides: { worktree: 'ok', cached: 'ok' },
    }
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('state.set', { plugin: 'flow-deck', key: 'git' }, ($, e, next) => next({ ...e, value: gitSnapshot }))
    on('state.set', { plugin: 'flow-deck', key: 'closureCard' }, ($, e, next) => {
      closureWrites.push(e.value)
      return next(e)
    })
    on('state.set', { plugin: 'flow-deck', key: 'lastRun' }, ($, e, next) => {
      lastRunWrites.push(e.value)
      return next(e)
    })
    // store 出口经 $.store.set 持久化，测试引擎无该设施，store 值断言留待会话内端到端（见文件尾注先例）
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'demo', batch: 'B2', files: ['src/a.ts'] })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '收口', testsPassed: 1, testsTotal: 1 })
    const firstCard = closureWrites.at(-1)
    expect(firstCard).not.toBeNull()
    const lastRunAfterFirst = lastRunWrites.at(-1)
    expect(lastRunAfterFirst).toHaveProperty('closure')
    // 重复上报同 plan#batch 全绿收口（scope 已被首次收口清空、校验必不过）→ 重放保留出口
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '收口', testsPassed: 1, testsTotal: 1 })
    expect(closureWrites.at(-1)).toEqual(firstCard)
    expect(lastRunWrites.at(-1)).toHaveProperty('closure')
    // 重放口径：closure 原样保留（updatedAt 为本次上报时刻，两次收口自然不同）
    expect((lastRunWrites.at(-1) as { closure: unknown }).closure)
      .toEqual((lastRunAfterFirst as { closure: unknown }).closure)
    // 他批错配收口（异键）→ 旧卡必清、不冒充本次收口
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B3', phase: '收口', testsPassed: 1, testsTotal: 1 })
    expect(closureWrites.at(-1)).toBeNull()
  })

  test('guardWarned 条件清理：同批阶段上报保留去重，异批上报清空残留', async ($, on) => {
    const logs: string[] = []
    const guardWrites: unknown[] = []
    on('ui.log', ($, e) => {
      logs.push(JSON.stringify(e))
      return { value: undefined }
    })
    on('state.set', { plugin: 'flow-deck', key: 'guardWarned' }, ($, e, next) => {
      guardWrites.push(e.value)
      return next(e)
    })
    on('tool.call', async ($, e, next) => {
      void next
      return { result: 'reached-bottom' }
    })
    on('session.start', async ($, e, next) => {
      void next
      return { cwd: 'C:\\repo' }
    })
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    // ① 同批去重保留：同批越界提醒一次 → 同批阶段上报 → 同文件再次越界不重复提醒
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'demo', batch: 'B2', files: ['src/a.ts'] })
    await $.tool.call({ tool: 'Edit', file_path: 'C:\\repo\\other\\c.ts', old_string: 'x', new_string: 'y' })
    expect(logs.filter(t => t.includes('边界外')).length).toBe(1)
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '执行' })
    await $.tool.call({ tool: 'Edit', file_path: 'C:\\repo\\other\\c.ts', old_string: 'x', new_string: 'y' })
    expect(logs.filter(t => t.includes('边界外')).length).toBe(1)
    // ② 异批清理：直接 flow_report 上报异批执行阶段 → guardWarned 被清理（写入空数组）。
    //    注意异批上报同时清空 batchScope（既有行为），守卫 fail-open 不再产生新提醒，
    //    故清理动作直接以 guardWarned 写入观测，不经“再次越界提醒”间接断言。
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B3', phase: '执行' })
    expect(guardWrites.at(-1)).toEqual([])
  })

  test('首报起点三态：同键重新声明不重置起点，异批声明记新键', async ($, on) => {
    const clock = mock.clock(on)
    const closureWrites: unknown[] = []
    const gitSnapshot = {
      branch: 'main', upstream: null, ahead: 0, behind: 0,
      staged: [], unstaged: [], untracked: [], conflicts: [],
      added: 0, removed: 0, fetchedAt: 9,
      byPath: { 'src/a.ts': [0, 0] },
      numstatSides: { worktree: 'ok', cached: 'ok' },
    }
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('state.set', { plugin: 'flow-deck', key: 'git' }, ($, e, next) => next({ ...e, value: gitSnapshot }))
    on('state.set', { plugin: 'flow-deck', key: 'closureCard' }, ($, e, next) => {
      closureWrites.push(e.value)
      return next(e)
    })
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'demo', batch: 'B2', files: ['src/a.ts'] })
    // 同键重新声明（边界调整，files 集合变化）→ 起点不变；异批声明记新键起点。
    // 引擎 mock.clock 不操纵 Date.now（clock.set 仅驱动定时器队列），声明与收口同秒完成，
    // 分钟差值断言不可构造——此处断言「起点存在（minutes 为数值而非 null）」与「异批新键
    // 同样有起点」，三态分支的起点保留语义由代码评审核对 firstReportAt 的 has(key) 判定
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'demo', batch: 'B2', files: ['src/a.ts', 'src/b.ts'] })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '收口', testsPassed: 1, testsTotal: 1 })
    const minutes = (closureWrites.at(-1) as { closure: { minutes: number | null } }).closure.minutes
    expect(typeof minutes).toBe('number')
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'demo', batch: 'B3', files: ['src/a.ts'] })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B3', phase: '收口', testsPassed: 1, testsTotal: 1 })
    expect(typeof (closureWrites.at(-1) as { closure: { minutes: number | null } }).closure.minutes).toBe('number')
  })

  test('重复收口三出口完整序列：收口 → 重复收口 → idle → 新会话恢复，出口逐字段一致', async ($, on) => {
    const closureWrites: unknown[] = []
    const lastRunWrites: unknown[] = []
    const toasts: string[] = []
    const gitSnapshot = {
      branch: 'main', upstream: null, ahead: 0, behind: 0,
      staged: [], unstaged: [], untracked: [], conflicts: [],
      added: 3, removed: 2, fetchedAt: 5,
      byPath: { 'src/a.ts': [3, 2] },
      numstatSides: { worktree: 'ok', cached: 'ok' },
    }
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('state.set', { plugin: 'flow-deck', key: 'git' }, ($, e, next) => next({ ...e, value: gitSnapshot }))
    on('state.set', { plugin: 'flow-deck', key: 'closureCard' }, ($, e, next) => {
      closureWrites.push(e.value)
      return next(e)
    })
    on('state.set', { plugin: 'flow-deck', key: 'lastRun' }, ($, e, next) => {
      lastRunWrites.push(e.value)
      return next(e)
    })
    on('ui.toast', ($, e) => {
      toasts.push(e.text)
      return { value: undefined }
    })
    // 新会话恢复的 store.get 应答（引擎无 $.store.set，恢复值由替身直接给出）：
    // 替身在测试开头注册（引擎禁止 $ 首调后注册），null 字段原样透传经恢复路径校验
    let storeAnswer: unknown = undefined
    on('store.get', () => ({ value: storeAnswer }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'demo', batch: 'B2', files: ['src/a.ts'] })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '收口', testsPassed: 1, testsTotal: 1 })
    // 重复上报收口 → 出口保留（卡 + lastRun atom；store 出口留待端到端）
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '收口', testsPassed: 1, testsTotal: 1 })
    const cardValue = closureWrites.at(-1)
    expect(cardValue).not.toBeNull()
    expect(lastRunWrites.at(-1)).toHaveProperty('closure')
    // idle → 卡清空，lastRun atom 仍含 closure
    await $.tool.call({ tool: 'mcp__flow-deck__flow_task', kind: 'idle' })
    expect(closureWrites.at(-1)).toBeNull()
    expect(lastRunWrites.at(-1)).toHaveProperty('closure')
    // 新会话恢复：lastRun atom 含 closure（null 字段原样透传）、toast 为战报格式
    storeAnswer = { plan: 'demo', batch: 'B2', phase: '收口', updatedAt: 1, closure: { files: 1, added: null, removed: null, minutes: null } }
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    expect(lastRunWrites.at(-1)).toHaveProperty('closure')
    expect(toasts.some(text => text.includes('全绿'))).toBe(true)
    // 跨会话恢复断言：parseExecution 透传后 null 未折算（间接经 toast 文案断言）
    expect(toasts.some(text => text.includes('声明边界'))).toBe(true)
  })

  test('全绿后 idle 或下一批上报 → 通关卡消失、出口保留', async ($, on) => {
    const closureWrites: unknown[] = []
    const lastRunWrites: unknown[] = []
    const gitSnapshot = {
      branch: 'main', upstream: null, ahead: 0, behind: 0,
      staged: [], unstaged: [], untracked: [], conflicts: [],
      added: 3, removed: 2, fetchedAt: 5,
      byPath: { 'src/a.ts': [3, 2] },
      numstatSides: { worktree: 'ok', cached: 'ok' },
    }
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('state.set', { plugin: 'flow-deck', key: 'git' }, ($, e, next) => next({ ...e, value: gitSnapshot }))
    on('state.set', { plugin: 'flow-deck', key: 'closureCard' }, ($, e, next) => {
      closureWrites.push(e.value)
      return next(e)
    })
    on('state.set', { plugin: 'flow-deck', key: 'lastRun' }, ($, e, next) => {
      lastRunWrites.push(e.value)
      return next(e)
    })
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'demo', batch: 'B2', files: ['src/a.ts'] })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '收口', testsPassed: 1, testsTotal: 1 })
    expect(closureWrites.at(-1)).not.toBeNull()
    // 下一批执行上报（非收口）→ 清空
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B3', phase: '执行' })
    expect(closureWrites.at(-1)).toBeNull()
    // store 与 lastRun 保留含 closure 统计
    expect(lastRunWrites.at(-1)).toHaveProperty('closure')
  })

  test('通关卡装配：deps 匹配渲染轨道图按实际状态着色，未声明或他方案 deps 只渲染战报行', { options: { artDirection: 'default' } }, async ($, on) => {
    const gitSnapshot = {
      branch: 'main', upstream: null, ahead: 0, behind: 0,
      staged: [], unstaged: [], untracked: [], conflicts: [],
      added: 3, removed: 2, fetchedAt: 5,
      byPath: { 'src/a.ts': [3, 2] },
      numstatSides: { worktree: 'ok', cached: 'ok' },
    }
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('state.set', { plugin: 'flow-deck', key: 'git' }, ($, e, next) => next({ ...e, value: gitSnapshot }))
    const depsCall = { tool: 'mcp__flow-deck__flow_deps', plan: 'demo', batches: [
      { batch: 'B1', dependsOn: [] }, { batch: 'B2', dependsOn: ['B1'] }, { batch: 'B3', dependsOn: ['B2'] },
    ] }
    // 场景 a：deps 匹配 → 轨道图混合状态（B1 done 色，B2/B3 待执行维持现状）
    await $.tool.call(depsCall)
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'demo', batch: 'B1', files: ['src/a.ts'] })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B1', phase: '收口', testsPassed: 1, testsTotal: 1 })
    let ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow'),
    })
    expect(await ui.find({ text: /通关 · demo \/ B1/ })).not.toBeUndefined()
    expect(await ui.find({ text: /执行 DAG（demo）/ })).not.toBeUndefined()
    expect(await ui.find({ text: /全绿/ })).not.toBeUndefined()
    const doneB1 = await ui.find({ type: 'Text', text: '✓ B1' })
    expect(doneB1?.props.color).toBe('success')
    expect(doneB1?.props.bold).toBe(true)
    const pendingB3 = await ui.find({ type: 'Text', text: '○ B3' })
    expect(pendingB3?.props.dimColor).toBe(true)
    expect(await ui.find({ text: /1\/3 收口/ })).not.toBeUndefined()
    await ui.unmount()
    // 场景 b：deps 为他方案残留（plan 不匹配，与未声明 deps 同一渲染分支）→ 只渲染战报行
    await $.tool.call({ tool: 'mcp__flow-deck__flow_task', kind: 'idle' })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_deps', plan: 'other', batches: [{ batch: 'B1', dependsOn: [] }] })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'demo', batch: 'B2', files: ['src/a.ts'] })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '收口', testsPassed: 1, testsTotal: 1 })
    ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow'),
    })
    expect(await ui.find({ text: /通关 · demo \/ B2/ })).not.toBeUndefined()
    expect(await ui.find({ text: /执行 DAG（demo）/ })).toBeUndefined()
    await ui.unmount()
  })

  test('全线点亮：依赖图内全部批次收口才全图 done 色（B1 条目 6 唯一触发）', async ($, on) => {
    const gitSnapshot = {
      branch: 'main', upstream: null, ahead: 0, behind: 0,
      staged: [], unstaged: [], untracked: [], conflicts: [],
      added: 3, removed: 2, fetchedAt: 5,
      byPath: { 'src/a.ts': [3, 2] },
      numstatSides: { worktree: 'ok', cached: 'ok' },
    }
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('state.set', { plugin: 'flow-deck', key: 'git' }, ($, e, next) => next({ ...e, value: gitSnapshot }))
    await $.tool.call({ tool: 'mcp__flow-deck__flow_deps', plan: 'demo', batches: [
      { batch: 'B1', dependsOn: [] }, { batch: 'B2', dependsOn: ['B1'] }, { batch: 'B3', dependsOn: ['B2'] },
    ] })
    for (const batch of ['B1', 'B2', 'B3']) {
      await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'demo', batch, files: ['src/a.ts'] })
      await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch, phase: '收口', testsPassed: 1, testsTotal: 1 })
    }
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow'),
    })
    expect(await ui.find({ text: /通关 · demo \/ B3/ })).not.toBeUndefined()
    expect(await ui.find({ text: /3\/3 收口/ })).not.toBeUndefined()
    const glyphs = (await ui.findAll({ type: 'Text', text: '■' })).filter(seg => seg.text === '■')
    expect(glyphs.length).toBeGreaterThan(0)
    expect(glyphs.every(seg => seg.props.color === 'success')).toBe(true)
    await ui.unmount()
  })

  test('双皮肤同态对比：default 与 mission-control 结构与非文案信息一致，仅文案不同', { options: { artDirection: 'default' } }, async ($, on) => {
    const gitSnapshot = {
      branch: 'main', upstream: null, ahead: 0, behind: 0,
      staged: [], unstaged: [], untracked: [], conflicts: [],
      added: 3, removed: 2, fetchedAt: 5,
      byPath: { 'src/a.ts': [3, 2] },
      numstatSides: { worktree: 'ok', cached: 'ok' },
    }
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('state.set', { plugin: 'flow-deck', key: 'git' }, ($, e, next) => next({ ...e, value: gitSnapshot }))
    await $.tool.call({ tool: 'mcp__flow-deck__flow_deps', plan: 'demo', batches: [
      { batch: 'B1', dependsOn: [] }, { batch: 'B2', dependsOn: ['B1'] },
    ] })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'demo', batch: 'B1', files: ['src/a.ts'] })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B1', phase: '收口', testsPassed: 1, testsTotal: 1 })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow'),
    })
    // default 词表：原文案逐字保留
    expect(await ui.find({ text: /当前无方案迭代或实施任务。/ })).not.toBeUndefined()
    expect(await ui.find({ text: /执行 DAG（demo）/ })).not.toBeUndefined()
    const boxes = await ui.findAll({ type: 'Box' })
    const texts = await ui.findAll({ type: 'Text' })
    // 结构与非文案信息锚点值（与 mission-control 测试的期望值一一对应）
    expect(boxes.length).toBe(11)
    const colored = texts.filter(node => typeof node.props.color === 'string')
    expect(colored.length).toBeGreaterThan(0)
    expect(colored.some(node => node.props.color === 'success')).toBe(true)
    await ui.unmount()
  })

  test('双皮肤同态对比：mission-control 词表换文案不改结构', async ($, on) => {
    const gitSnapshot = {
      branch: 'main', upstream: null, ahead: 0, behind: 0,
      staged: [], unstaged: [], untracked: [], conflicts: [],
      added: 3, removed: 2, fetchedAt: 5,
      byPath: { 'src/a.ts': [3, 2] },
      numstatSides: { worktree: 'ok', cached: 'ok' },
    }
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('state.set', { plugin: 'flow-deck', key: 'git' }, ($, e, next) => next({ ...e, value: gitSnapshot }))
    await $.tool.call({ tool: 'mcp__flow-deck__flow_deps', plan: 'demo', batches: [
      { batch: 'B1', dependsOn: [] }, { batch: 'B2', dependsOn: ['B1'] },
    ] })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'demo', batch: 'B1', files: ['src/a.ts'] })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B1', phase: '收口', testsPassed: 1, testsTotal: 1 })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow'),
    })
    // mission-control 词表：换文案、结构与色档不变
    expect(await ui.find({ text: /待命 · 当前无方案迭代或实施任务。/ })).not.toBeUndefined()
    expect(await ui.find({ text: /轨道图（demo）/ })).not.toBeUndefined()
    const boxes = await ui.findAll({ type: 'Box' })
    const texts = await ui.findAll({ type: 'Text' })
    expect(boxes.length).toBe(11)
    const colored = texts.filter(node => typeof node.props.color === 'string')
    expect(colored.length).toBeGreaterThan(0)
    expect(colored.some(node => node.props.color === 'success')).toBe(true)
    await ui.unmount()
  })

  test('flow_report 上报驱动横条（terminal 与 desktop 同构）', async $ => {
    const result = await $.tool.call({
      tool: 'mcp__flow-deck__flow_report',
      plan: 'demo',
      batch: 'B2',
      phase: '执行',
      tLevel: 'T1',
      testsPassed: 12,
      testsTotal: 15,
    })
    expect(result.result).toBe('进度已上报')
    for (const surface of ['terminal', 'desktop'] as const) {
      const ui = await $.ui.mount({
        plugin: 'flow-deck',
        surface,
        component: 'AbovePrompt',
        props: bandProps(),
      })
      expect(await ui.find({ text: /demo · B2 · T1 · 执行 · 验证 12\/15/ })).not.toBeUndefined()
      await ui.unmount()
      const pane = await $.ui.mount({
        plugin: 'flow-deck',
        surface,
        component: 'Pane',
        requestId: 'deck',
        props: { ...paneProps('Flow'), bodyColumns: 80 },
      })
      // 风险定级在面板执行卡内为反色 chip（accent 底 + inverseText；accent 已改为蓝）
      const chips = await pane.findAll({ type: 'Text', text: ' T1 ' })
      expect(chips.some(seg => seg.props.backgroundColor === 'professionalBlue')).toBe(true)
      await pane.unmount()
    }
  })

  // 「无上报时横条让位」不单测：该分支就是 return next(e)，链底兜底是引擎语义，
  // 测试引擎没有实现可喂（M1 时 $.ui.open 同理）。
  // 「/flow toggle 开关」不做自动化：依赖 $.ui.panes/open/close 三个无实现设施，
  // 引擎文档的 toggle 示例即此形态，由会话内端到端验证。

  test('flow_batch 声明边界后 deny 模式拦截越界 Edit', { options: { guardMode: 'deny' } }, async ($, on) => {
    // session.start 首行缓存 cwd；随后 command.register 在测试引擎无实现被跳过，
    // 链底由本测试应答
    on('session.start', async ($, e, next) => {
      void next
      return { cwd: 'C:\\repo' }
    })
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    const declared = await $.tool.call({
      tool: 'mcp__flow-deck__flow_batch',
      plan: 'demo',
      batch: 'B2',
      files: ['src/a.ts', 'src/b.ts'],
    })
    expect(declared.result).toBe('批次边界已声明：B2 共 2 个文件')

    const denied = await $.tool.call({
      tool: 'Edit',
      file_path: 'C:\\repo\\other\\c.ts',
      old_string: 'x',
      new_string: 'y',
    })
    expect(denied.deny).toContain('边界外')
  })

  test('deny 模式下界内 Edit 放行到真工具', { options: { guardMode: 'deny' } }, async ($, on) => {
    // 底层应答：插件钩子放行（next）时由本钩子收口并留标记
    on('tool.call', async ($, e, next) => {
      void next
      return { result: 'reached-bottom' }
    })
    on('session.start', async ($, e, next) => {
      void next
      return { cwd: 'C:\\repo' }
    })
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await $.tool.call({
      tool: 'mcp__flow-deck__flow_batch',
      plan: 'demo',
      batch: 'B2',
      files: ['src/a.ts'],
    })
    const allowed = await $.tool.call({
      tool: 'Edit',
      file_path: 'SRC\\A.TS',
      old_string: 'x',
      new_string: 'y',
    })
    expect(allowed.result).toBe('reached-bottom')
  })

  test('未声明边界时 Edit 不受守卫', async ($, on) => {
    on('tool.call', async ($, e, next) => {
      void next
      return { result: 'reached-bottom' }
    })
    on('session.start', async ($, e, next) => {
      void next
      return { cwd: 'C:\\repo' }
    })
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    const result = await $.tool.call({
      tool: 'Edit',
      file_path: 'C:\\repo\\anything.ts',
      old_string: 'x',
      new_string: 'y',
    })
    expect(result.result).toBe('reached-bottom')
  })

  // warn 模式越界提醒的去重行为：ui.log 是无实现的 dispatch，mock 成计数器；
  // 消息字段名未证实，先 JSON.stringify 兜底匹配（断言子串不含反斜杠）。
  test('warn 模式越界提醒按文件去重，重新声明边界后再次提醒', async ($, on) => {
    const logs: string[] = []
    on('ui.log', ($, e) => {
      logs.push(JSON.stringify(e))
      return { value: undefined }
    })
    on('tool.call', async ($, e, next) => {
      void next
      return { result: 'reached-bottom' }
    })
    on('session.start', async ($, e, next) => {
      void next
      return { cwd: 'C:\\repo' }
    })
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'demo', batch: 'B2', files: ['src/a.ts'] })
    // 界内编辑不产生告警
    await $.tool.call({ tool: 'Edit', file_path: 'C:\\repo\\src\\a.ts', old_string: 'x', new_string: 'y' })
    expect(logs.filter(t => t.includes('边界外')).length).toBe(0)
    // 首次越界提醒；同文件异写法与跨工具再次编辑静默；异文件各自提醒
    await $.tool.call({ tool: 'Edit', file_path: 'C:\\repo\\other\\c.ts', old_string: 'x', new_string: 'y' })
    await $.tool.call({ tool: 'Edit', file_path: 'C:\\repo\\OTHER\\C.TS', old_string: 'x', new_string: 'y' })
    await $.tool.call({ tool: 'Write', file_path: 'C:\\repo\\other\\c.ts', content: 'z' })
    await $.tool.call({ tool: 'Edit', file_path: 'C:\\repo\\other\\d.ts', old_string: 'x', new_string: 'y' })
    expect(logs.filter(t => t.includes('边界外')).length).toBe(2)
    expect(logs.some(t => t.includes('⚠ Edit') && t.includes('B2'))).toBe(true)
    // flow_batch 重新声明边界后同文件恢复提醒
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'demo', batch: 'B2', files: ['src/a.ts'] })
    await $.tool.call({ tool: 'Edit', file_path: 'C:\\repo\\other\\c.ts', old_string: 'x', new_string: 'y' })
    expect(logs.filter(t => t.includes('边界外')).length).toBe(3)
  })

  test('flow_deps 声明后面板绘制执行 DAG 区块与分色总览条', { options: { artDirection: 'default' } }, async $ => {
    const declared = await $.tool.call({
      tool: 'mcp__flow-deck__flow_deps',
      plan: 'demo',
      batches: [
        { batch: 'B1', dependsOn: [] },
        { batch: 'B2', dependsOn: ['B1'] },
        { batch: 'B3', dependsOn: ['B2'] },
      ],
    })
    expect(declared.result).toBe('波次依赖已声明：demo 共 3 批')
    // B1 收口 → ✓；B2 进行中 → ●；B3 未上报 → ○
    await $.tool.call({
      tool: 'mcp__flow-deck__flow_report',
      plan: 'demo',
      batch: 'B1',
      phase: '收口',
    })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '执行' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck',
      surface: 'terminal',
      component: 'Pane',
      requestId: 'deck',
      props: paneProps('Flow 评审仪表盘'),
    })
    expect(await ui.find({ text: /▍执行 DAG（demo）/ })).not.toBeUndefined()
    expect(await ui.find({ text: /← B1/ })).not.toBeUndefined()
    expect(await ui.find({ type: 'Text', text: '✓ B1' })).not.toBeUndefined()
    expect(await ui.find({ type: 'Text', text: '● B2' })).not.toBeUndefined()
    expect(await ui.find({ text: /1\/3 收口/ })).not.toBeUndefined()
    // 总览条按批着色：收口 ■ 绿、进行 ▣ 黄、待执行 □ 灰（分段文本经引擎文本匹配，颜色查 props）
    const dones = await ui.findAll({ type: 'Text', text: '■' })
    expect(dones.some(seg => seg.props.color === 'success')).toBe(true)
    const actives = await ui.findAll({ type: 'Text', text: '▣' })
    expect(actives.some(seg => seg.props.color === 'warning')).toBe(true)
    const pendings = await ui.findAll({ type: 'Text', text: '□' })
    expect(pendings.some(seg => seg.props.dimColor === true)).toBe(true)
    // 流水线连线取下游状态：B2 进行中 → ━（warn），B3 未上报 → ╌（dim）
    const solidLinks = await ui.findAll({ type: 'Text', text: '━' })
    expect(solidLinks.some(seg => seg.props.color === 'warning')).toBe(true)
    const dashedLinks = await ui.findAll({ type: 'Text', text: '╌' })
    expect(dashedLinks.some(seg => seg.props.dimColor === true)).toBe(true)
    await ui.unmount()
  })

  test('flow_deps 缺 batches 返回错误结果', async $ => {
    const result = await $.tool.call({ tool: 'mcp__flow-deck__flow_deps', plan: 'demo' })
    expect(result.isError).toBe(true)
  })

  test('没有评审或 DAG 时，上报仍显示执行卡片（极简阶段条）；宽窄面板跨表面渲染', { options: { artDirection: 'default' } }, async $ => {
    await $.tool.call({
      tool: 'mcp__flow-deck__flow_report',
      plan: '执行方案', batch: 'B3', phase: '验证', testsPassed: 8, testsTotal: 10,
    })
    for (const surface of ['terminal', 'desktop'] as const) {
      for (const bodyColumns of [28, 80]) {
        const ui = await $.ui.mount({
          plugin: 'flow-deck', surface, component: 'Pane', requestId: 'deck',
          props: { ...paneProps('Flow'), bodyColumns },
        })
        expect(await ui.find({ text: /当前执行 · 执行方案/ })).not.toBeUndefined()
        // 极简阶段条：比例条 + 当前阶段名与序号，不再罗列全部阶段
        expect(await ui.find({ text: /验证 · 4\/5/ })).not.toBeUndefined()
        expect(await ui.find({ type: 'Text', text: '━━━━━━━━──' })).not.toBeUndefined()
        expect(await ui.find({ text: /✓ 开工/ })).toBeUndefined()
        expect(await ui.find({ text: /验证 .*8\/10/ })).not.toBeUndefined()
        expect(await ui.find({ text: /当前无方案迭代或实施任务/ })).toBeUndefined()
        const boxes = await ui.findAll({ type: 'Box' })
        expect(boxes.some(box => box.props.borderStyle === 'round')).toBe(bodyColumns >= 44)
        await ui.unmount()
      }
    }
  })

  test('切换方案后单行横条撤下旧上报，并截断长名称', async $ => {
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: '旧方案', batch: 'B1', files: ['old.ts'] })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: '当前方案', batch: 'B2', phase: '执行' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'AbovePrompt',
      props: { ...bandProps(), maxRows: 1, bodyColumns: 24 },
    })
    expect(await ui.find({ text: /当前方案/ })).not.toBeUndefined()
    expect(await ui.find({ text: /守卫/ })).toBeUndefined()
    expect((await ui.find({ type: 'Text' }))?.props.wrap).toBe('truncate-end')
    await ui.unmount()
  })

  test('实施切迭代、结束、再实施时，终端和桌面只展示当前任务', async $ => {
    await $.tool.call({
      tool: 'mcp__flow-deck__flow_deps', plan: '旧实施',
      batches: [{ batch: 'B1', dependsOn: [] }],
    })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: '旧实施', batch: 'B1', files: ['a.ts'] })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: '旧实施', batch: 'B1', phase: '执行' })
    const started = await $.tool.call({ tool: 'mcp__flow-deck__flow_task', kind: 'iterate', plan: '当前迭代' })
    expect(started.result).toBe('当前任务：方案迭代 · 当前迭代')
    for (const surface of ['terminal', 'desktop'] as const) {
      for (const bodyColumns of [28, 80]) {
        const ui = await $.ui.mount({
          plugin: 'flow-deck', surface, component: 'Pane', requestId: 'deck',
          props: { ...paneProps('Flow'), bodyColumns },
        })
        expect(await ui.find({ text: /▍工作面板 · 方案迭代 · 当前迭代/ })).not.toBeUndefined()
        expect(await ui.find({ text: /等待评审结果落盘/ })).not.toBeUndefined()
        expect(await ui.find({ text: /当前执行|执行 DAG|◇ 边界|旧实施/ })).toBeUndefined()
        await ui.unmount()
      }
    }
    await $.tool.call({ tool: 'mcp__flow-deck__flow_task', kind: 'idle' })
    const idle = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck', props: paneProps('Flow'),
    })
    expect(await idle.find({ text: /当前无方案迭代或实施任务/ })).not.toBeUndefined()
    await idle.unmount()
    await $.tool.call({ tool: 'mcp__flow-deck__flow_task', kind: 'implement', plan: '新实施', batch: 'B2' })
    const implementing = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck', props: paneProps('Flow'),
    })
    expect(await implementing.find({ text: /▍工作面板 · 方案实施 · 新实施/ })).not.toBeUndefined()
    expect(await implementing.find({ text: /等待阶段进度上报/ })).not.toBeUndefined()
    expect(await implementing.find({ text: /当前迭代|旧实施|执行 DAG/ })).toBeUndefined()
    await implementing.unmount()
  })

  test('flow_task 拒绝无效声明，并保留当前任务', async $ => {
    await $.tool.call({ tool: 'mcp__flow-deck__flow_task', kind: 'iterate', plan: 'demo' })
    for (const input of [{ kind: 'other' }, { kind: 'implement' }, { kind: 'iterate', plan: ' ' }]) {
      const result = await $.tool.call({ tool: 'mcp__flow-deck__flow_task', ...input })
      expect(result.isError).toBe(true)
    }
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck', props: paneProps('Flow'),
    })
    expect(await ui.find({ text: /▍工作面板 · 方案迭代 · demo/ })).not.toBeUndefined()
    await ui.unmount()
  })

  test('迭代开始后旧实施边界不再拦截文件编辑', { options: { guardMode: 'deny' } }, async ($, on) => {
    on('tool.call', async ($, e, next) => {
      void next
      return { result: 'reached-bottom' }
    })
    on('session.start', async ($, e, next) => {
      void next
      return { cwd: 'C:\\repo' }
    })
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: '旧实施', batch: 'B1', files: ['a.ts'] })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_task', kind: 'iterate', plan: '新方案' })
    const result = await $.tool.call({ tool: 'Edit', file_path: 'plans/new.md', old_string: 'a', new_string: 'b' })
    expect(result.result).toBe('reached-bottom')
  })

  // 两类路径不经自动化测试，改由会话内 fixture 端到端确认：
  // 1. 有数据卡片的渲染（plan 卡片、横条 git 行）——宿主规则不允许测试模块写插件状态
  //    （$.state 调用权在按 hooks.json 声明的模块静态扫描，*.test.ts 扫描结果恒空），
  //    git 快照只能经 on('state.set') 拦截顶替（本文件既有 fixture 口径）间接供给；
  //    数据组装已由 parse.test.ts 的 buildPlanReview / buildGitStatus 用例覆盖。
  //    （注：process 设施在测试引擎可用——本文件 20 余处 on('process.run') mock 与
  //    B1 的 diff/Issues 用例均实证；事件载荷字段为 argv。）
  // 2. /flow 与 /git 命令链路——测试引擎里 $.ui.open 是无实现的 dispatch，需猜测
  //    UiOpenResult 应答形状才能喂饱链路；该处理器与官方 pane 示例同构。

  test('/doc 无路径时给用法提示', async ($, on) => {
    on('ui.panes', () => ({ value: [] }))
    on('ui.open', () => ({ value: { isPlaced: true } }))
    const result = await $.command.run({ command: 'deck', args: 'doc' })
    expect(result.text).toContain('文件查看器页签')
  })

  test('/doc 装载文档，选节后 e 把修改请求填入输入框', async ($, on) => {
    const clock = mock.clock(on)
    const files = new Map<string, string>([['docs/plan.md', '# 一\n正文一\n## 二\n正文二']])
    const relOf = (value: unknown): string => {
      const norm = typeof value === 'string' ? value.replaceAll('\\', '/') : ''
      return norm.includes('docs/plan.md') ? 'docs/plan.md' : norm
    }
    on('fs.read', ($, e) => {
      const rel = relOf(e.path)
      if (!files.has(rel)) throw new Error('ENOENT: ' + String(e.path))
      return { value: files.get(rel) }
    })
    on('ui.panes', () => ({ value: [] }))
    on('ui.open', () => ({ value: { isPlaced: true } }))
    on('ui.close', () => ({ value: undefined }))
    let draftBox = { text: '', cursor: 0 }
    on('prompt.read', () => ({ value: draftBox }))
    const fills: Array<{ text: string; mode?: string }> = []
    on('prompt.fill', ($, e) => {
      fills.push({ text: e.text, mode: e.mode })
      return { isFilled: true }
    })
    await $.command.run({ command: 'deck', args: 'doc docs/plan.md' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('文档浏览'),
    })
    expect(await ui.find({ text: /▍文件查看器 · docs\/plan\.md · 2 节 · 4 行/ })).not.toBeUndefined()
    // 节标题下拉的选项显示节标题（SelectOption 字段是 label，缺省会画成 value 序号）
    const selector = await ui.find({ type: 'Select' })
    expect(selector?.props.options?.map((option: { label?: string }) => option.label)).toEqual(['一', '二'])
    // 默认全文模式：浏览行显示全文标题，Markdown 渲染整篇
    expect(await ui.find({ text: /▍全文 · 4 行/ })).not.toBeUndefined()
    const body = await ui.find({ type: 'Markdown' })
    expect(body).not.toBeUndefined()
    expect(body?.props.text).toBe('# 一\n正文一\n## 二\n正文二')
    // 全文模式的 e 锚定到整篇文件
    await $.ui.press({ plugin: 'flow-deck', key: 'doc-send', requestId: 'deck', surface: 'terminal' })
    await clock.settle()
    expect(fills).toHaveLength(1)
    expect(fills[0].text).toBe('请修改 docs/plan.md 文件：')
    // Select 选节切到单节模式，e 锚定该节
    await $.ui.select({ plugin: 'flow-deck', key: 'doc-section', value: '1', requestId: 'deck', surface: 'terminal' })
    expect(await ui.find({ text: /▍二 · 第 3–4 行/ })).not.toBeUndefined()
    const nextBody = await ui.find({ type: 'Markdown' })
    expect(nextBody?.props.text).toBe('## 二\n正文二')
    await $.ui.press({ plugin: 'flow-deck', key: 'doc-send', requestId: 'deck', surface: 'terminal' })
    await clock.settle()
    expect(fills).toHaveLength(2)
    expect(fills[1].mode).toBe('replace')
    expect(fills[1].text).toBe('请修改 docs/plan.md 的「二」一节（第 3–4 行）：')
    draftBox = { text: '已有草稿', cursor: 0 }
    await $.ui.press({ plugin: 'flow-deck', key: 'doc-send', requestId: 'deck', surface: 'terminal' })
    await clock.settle()
    expect(fills).toHaveLength(3)
    expect(fills[2].mode).toBe('append')
    // 切回全文
    await $.ui.press({ plugin: 'flow-deck', key: 'doc-sec-all', requestId: 'deck', surface: 'terminal' })
    expect(await ui.find({ text: /▍全文 · 4 行/ })).not.toBeUndefined()
    await ui.unmount()
  })

  test('doc 复制全文：c 把 doc.text 原文经 stdin 送剪贴板命令并 toast 确认', async ($, on) => {
    const clock = mock.clock(on)
    const body = '# 计划\n中文正文\n\n末行'
    const files = new Map<string, string>([['docs/plan.md', body]])
    const relOf = (value: unknown): string => {
      const norm = typeof value === 'string' ? value.replaceAll('\\', '/') : ''
      return norm.includes('docs/plan.md') ? 'docs/plan.md' : norm
    }
    on('fs.read', ($, e) => {
      const rel = relOf(e.path)
      if (!files.has(rel)) throw new Error('ENOENT: ' + String(e.path))
      return { value: files.get(rel) }
    })
    // 引擎沙箱无 process 全局，实现走 env.get 推断平台；测试沙箱同样无 process，用 win32 字面量
    on('env.get', ($, e) => ({ value: e.name === 'OS' ? 'Windows_NT' : 'C:\\Users\\tu' }))
    on('ui.panes', () => ({ value: [] }))
    on('ui.open', () => ({ value: { isPlaced: true } }))
    on('ui.close', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    const toasts: string[] = []
    on('ui.toast', ($, e) => {
      toasts.push(e.text)
      return { value: undefined }
    })
    const runs: Array<{ argv: string[]; stdin?: string; timeoutMs?: number }> = []
    const clip = clipboardArgv('win32') as string[]
    on('process.run', ($, e) => {
      const argv = e.argv ?? []
      const init = (e.init ?? {}) as { stdin?: string; timeoutMs?: number }
      runs.push({ argv, stdin: init.stdin, timeoutMs: init.timeoutMs })
      return { value: { exitCode: argv[0] === clip[0] ? 0 : 128, stdout: '', stderr: '' } }
    })
    await $.command.run({ command: 'deck', args: 'doc docs/plan.md' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('文档浏览'),
    })
    const buttons = await ui.findAll({ type: 'Button' })
    expect(buttons.some(button => button.props.key === 'doc-copy')).toBe(true)
    await $.ui.press({ plugin: 'flow-deck', key: 'doc-copy', requestId: 'deck', surface: 'terminal' })
    await clock.settle()
    const copyRun = runs.find(run => run.argv[0] === clip[0])
    expect(copyRun).not.toBeUndefined()
    expect(copyRun?.argv).toEqual(clip)
    // 数据源是 doc.text 原文（非 enhanceMarkdown 渲染增强文本）
    expect(copyRun?.stdin).toBe(body)
    expect(copyRun?.timeoutMs).toBe(5000)
    expect(toasts.some(text => text.includes('已复制全文'))).toBe(true)
    await ui.unmount()
  })

  test('doc 复制全文：剪贴板命令非零退出时 toast 失败、不报成功', async ($, on) => {
    const clock = mock.clock(on)
    const body = '# 标题\n正文'
    const files = new Map<string, string>([['docs/plan.md', body]])
    const relOf = (value: unknown): string => {
      const norm = typeof value === 'string' ? value.replaceAll('\\', '/') : ''
      return norm.includes('docs/plan.md') ? 'docs/plan.md' : norm
    }
    on('fs.read', ($, e) => {
      const rel = relOf(e.path)
      if (!files.has(rel)) throw new Error('ENOENT: ' + String(e.path))
      return { value: files.get(rel) }
    })
    on('ui.panes', () => ({ value: [] }))
    on('ui.open', () => ({ value: { isPlaced: true } }))
    on('ui.close', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    const toasts: string[] = []
    on('ui.toast', ($, e) => {
      toasts.push(e.text)
      return { value: undefined }
    })
    on('env.get', ($, e) => ({ value: e.name === 'OS' ? 'Windows_NT' : 'C:\\Users\\tu' }))
    const runs: string[][] = []
    const clip = clipboardArgv('win32') as string[]
    on('process.run', ($, e) => {
      const argv = e.argv ?? []
      runs.push(argv)
      return { value: { exitCode: argv[0] === clip[0] ? 1 : 128, stdout: '', stderr: 'boom' } }
    })
    await $.command.run({ command: 'deck', args: 'doc docs/plan.md' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('文档浏览'),
    })
    await $.ui.press({ plugin: 'flow-deck', key: 'doc-copy', requestId: 'deck', surface: 'terminal' })
    await clock.settle()
    // 命令确实发出且 stdin 仍送全文
    expect(runs.some(argv => argv[0] === clip[0])).toBe(true)
    expect(toasts.some(text => text.includes('复制失败'))).toBe(true)
    expect(toasts.some(text => text.includes('已复制全文'))).toBe(false)
    await ui.unmount()
  })

  test('doc 复制全文：剪贴板命令抛异常（如 linux 无 xclip）落 catch 分支 toast 失败', async ($, on) => {
    const clock = mock.clock(on)
    const body = '# 标题\n正文'
    const files = new Map<string, string>([['docs/plan.md', body]])
    const relOf = (value: unknown): string => {
      const norm = typeof value === 'string' ? value.replaceAll('\\', '/') : ''
      return norm.includes('docs/plan.md') ? 'docs/plan.md' : norm
    }
    on('fs.read', ($, e) => {
      const rel = relOf(e.path)
      if (!files.has(rel)) throw new Error('ENOENT: ' + String(e.path))
      return { value: files.get(rel) }
    })
    on('ui.panes', () => ({ value: [] }))
    on('ui.open', () => ({ value: { isPlaced: true } }))
    on('ui.close', () => ({ value: undefined }))
    const logs: string[] = []
    on('ui.log', ($, e) => {
      logs.push(e.text)
      return { value: undefined }
    })
    const toasts: string[] = []
    on('ui.toast', ($, e) => {
      toasts.push(e.text)
      return { value: undefined }
    })
    on('env.get', ($, e) => ({ value: e.name === 'OS' ? 'Windows_NT' : 'C:\\Users\\tu' }))
    const clip = clipboardArgv('win32') as string[]
    on('process.run', ($, e) => {
      const argv = e.argv ?? []
      if (argv[0] === clip[0]) throw new Error('spawn xclip ENOENT')
      return { value: { exitCode: 128, stdout: '', stderr: '' } }
    })
    await $.command.run({ command: 'deck', args: 'doc docs/plan.md' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('文档浏览'),
    })
    await $.ui.press({ plugin: 'flow-deck', key: 'doc-copy', requestId: 'deck', surface: 'terminal' })
    await clock.settle()
    expect(toasts.some(text => text.includes('复制失败'))).toBe(true)
    expect(toasts.some(text => text.includes('已复制全文'))).toBe(false)
    expect(logs.some(text => text.includes('flow-deck 复制全文异常'))).toBe(true)
    await ui.unmount()
  })

  test('doc 节内容以 Markdown 渲染，终端与桌面均通过引擎校验', async ($, on) => {
    const clock = mock.clock(on)
    const files = new Map<string, string>([['docs/plan.md', '# 一\n正文一\n## 二\n正文二']])
    const relOf = (value: unknown): string => {
      const norm = typeof value === 'string' ? value.replaceAll('\\', '/') : ''
      return norm.includes('docs/plan.md') ? 'docs/plan.md' : norm
    }
    on('fs.read', ($, e) => {
      const rel = relOf(e.path)
      if (!files.has(rel)) throw new Error('ENOENT: ' + String(e.path))
      return { value: files.get(rel) }
    })
    on('ui.panes', () => ({ value: [] }))
    on('ui.open', () => ({ value: { isPlaced: true } }))
    on('ui.close', () => ({ value: undefined }))
    await $.command.run({ command: 'deck', args: 'doc docs/plan.md' })
    for (const surface of ['terminal', 'desktop'] as const) {
      const view = await $.ui.mount({
        plugin: 'flow-deck', surface, component: 'Pane', requestId: 'deck',
        props: paneProps('文档浏览'),
      })
      const rendered = await view.find({ type: 'Markdown' })
      expect(rendered).not.toBeUndefined()
      expect(rendered?.props.text).toBe('# 一\n正文一\n## 二\n正文二')
      await view.unmount()
    }
  })

  // ---- B1 变更对比视图 + 地址输入栏（L2 替身编排） ----

  test('改动清单点击 staged 文件 → 「变更对比」标题与 Code(format=diff)', async ($, on) => {
    const clock = mock.clock(on)
    const gitSnapshot: GitStatus = {
      branch: 'main', upstream: 'origin/main', ahead: 0, behind: 0,
      staged: [{ code: 'M ', path: 'hooks/a.ts' }], unstaged: [], untracked: [], conflicts: [],
      added: 1, removed: 0, fetchedAt: 0,
    }
    const diffCalls: string[][] = []
    const reads: unknown[] = []
    on('fs.read', ($, e) => {
      reads.push(e.path)
      throw new Error('ENOENT: ' + String(e.path))
    })
    on('process.run', diffRunner(diffCalls, { exitCode: 0, stdout: DIFF_HUNK }))
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('ui.status', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('ui.open', () => ({ value: { isPlaced: true } }))
    on('fs.list', () => ({ value: [] }))
    on('state.set', { plugin: 'flow-deck', key: 'git' }, ($, e, next) => next({ ...e, value: gitSnapshot }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await clock.settle()
    await $.command.run({ command: 'deck', args: 'tree' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Deck'),
    })
    expect(await ui.find({ text: /hooks\/a\.ts/ })).not.toBeUndefined()
    await $.ui.press({ plugin: 'flow-deck', key: 'file-open-hooks/a.ts', requestId: 'deck', surface: 'terminal' })
    await clock.settle()
    expect(await ui.find({ text: /▍变更对比 · hooks\/a\.ts/ })).not.toBeUndefined()
    const code = await ui.find({ type: 'Code' })
    expect(code?.props.format).toBe('diff')
    expect(String(code?.props.source)).toContain('+added line')
    // staged 路径走 diff 装载，不读全文
    expect(reads).toEqual([])
    await ui.unmount()
  })

  test('untracked 点击 → process.run args 含 --no-index 并装入 diff', async ($, on) => {
    const clock = mock.clock(on)
    const gitSnapshot: GitStatus = {
      branch: 'main', upstream: 'origin/main', ahead: 0, behind: 0,
      staged: [], unstaged: [], untracked: [{ code: '??', path: 'plans/b.md' }], conflicts: [],
      added: 0, removed: 0, fetchedAt: 0,
    }
    const diffCalls: string[][] = []
    // 真实语义（本机 Git 2.49 实测）：--no-index 有差异时 exitCode=1（POSIX diff 约定），非 0
    on('process.run', diffRunner(diffCalls, { exitCode: 1, stdout: DIFF_HUNK }))
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('ui.status', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('ui.open', () => ({ value: { isPlaced: true } }))
    on('fs.list', () => ({ value: [] }))
    on('state.set', { plugin: 'flow-deck', key: 'git' }, ($, e, next) => next({ ...e, value: gitSnapshot }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await clock.settle()
    await $.command.run({ command: 'deck', args: 'tree' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Deck'),
    })
    await $.ui.press({ plugin: 'flow-deck', key: 'file-open-plans/b.md', requestId: 'deck', surface: 'terminal' })
    await clock.settle()
    const noIndex = diffCalls.find(args => args.includes('--no-index'))
    expect(noIndex).not.toBeUndefined()
    expect(noIndex?.at(-1)).toBe('plans/b.md')
    const code = await ui.find({ type: 'Code' })
    expect(code?.props.format).toBe('diff')
    expect(await ui.find({ text: /▍变更对比 · plans\/b\.md/ })).not.toBeUndefined()
    await ui.unmount()
  })

  test('untracked 无实质 hunk（空文件仅 diff 头 / exit 0 空 stdout）→ 无未提交变更空态', async ($, on) => {
    const clock = mock.clock(on)
    const gitSnapshot: GitStatus = {
      branch: 'main', upstream: 'origin/main', ahead: 0, behind: 0,
      staged: [], unstaged: [], untracked: [{ code: '??', path: 'plans/b.md' }], conflicts: [],
      added: 0, removed: 0, fetchedAt: 0,
    }
    const diffCalls: string[][] = []
    // 真实语义（本机 Git 2.49 实测）：空文件 vs /dev/null 也是 exit 1，stdout 仅 diff 头（无 @@ hunk 行）
    let stdout = 'diff --git a/plans/b.md b/plans/b.md\nnew file mode 100644\nindex 0000000..e69de29\n--- /dev/null\n+++ b/plans/b.md\n'
    on('fs.read', ($, e) => {
      const norm = typeof e.path === 'string' ? e.path.replaceAll('\\', '/') : ''
      if (!norm.endsWith('plans/b.md')) throw new Error('ENOENT: ' + String(e.path))
      return { value: '' }
    })
    on('process.run', ($, e) => {
      const args = (e as { argv?: string[] }).argv ?? []
      if (args[0] === 'git' && args.includes('diff') && !args.includes('--numstat')) {
        diffCalls.push(args)
        return { value: { exitCode: 1, stdout, stderr: '' } }
      }
      return { value: { exitCode: 128, stdout: '', stderr: '' } }
    })
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('ui.status', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('ui.open', () => ({ value: { isPlaced: true } }))
    on('fs.list', () => ({ value: [] }))
    on('state.set', { plugin: 'flow-deck', key: 'git' }, ($, e, next) => next({ ...e, value: gitSnapshot }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await clock.settle()
    await $.command.run({ command: 'deck', args: 'tree' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Deck'),
    })
    await $.ui.press({ plugin: 'flow-deck', key: 'file-open-plans/b.md', requestId: 'deck', surface: 'terminal' })
    await clock.settle()
    // 空文件本无可展示变更：仅头的输出归入空 diff 态（不退全文，也不把纯头文本喂给 Code）
    expect(await ui.find({ text: /▍变更对比 · plans\/b\.md/ })).not.toBeUndefined()
    expect(await ui.find({ text: /无未提交变更（快照可能已过期）/ })).not.toBeUndefined()
    // 第二口径（审计原设想的 exit 0 空 stdout）同样归空态——经「重读变更」按钮重拉驱动
    stdout = ''
    await $.ui.press({ plugin: 'flow-deck', key: 'doc-reload-diff', requestId: 'deck', surface: 'terminal' })
    await clock.settle()
    expect(await ui.find({ text: /无未提交变更（快照可能已过期）/ })).not.toBeUndefined()
    expect(diffCalls.length).toBeGreaterThanOrEqual(2)
    await ui.unmount()
  })

  test('state=null 行（仅本会话记录）点击保持原文件全文，与改前一致', async ($, on) => {
    const clock = mock.clock(on)
    const gitSnapshot: GitStatus = {
      branch: 'main', upstream: 'origin/main', ahead: 0, behind: 0,
      staged: [], unstaged: [], untracked: [], conflicts: [],
      added: 0, removed: 0, fetchedAt: 0,
    }
    const diffCalls: string[][] = []
    const readPaths: string[] = []
    on('fs.read', ($, e) => {
      const norm = typeof e.path === 'string' ? e.path.replaceAll('\\', '/') : ''
      if (!norm.endsWith('docs/c.md')) throw new Error('ENOENT: ' + String(e.path))
      readPaths.push(norm)
      return { value: '# 标题\n正文' }
    })
    on('process.run', diffRunner(diffCalls, { exitCode: 0, stdout: DIFF_HUNK }))
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('ui.status', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('ui.open', () => ({ value: { isPlaced: true } }))
    on('fs.list', () => ({ value: [] }))
    on('tool.call', async ($, e, next) => {
      void next
      return { result: 'reached-bottom' }
    })
    on('state.set', { plugin: 'flow-deck', key: 'git' }, ($, e, next) => next({ ...e, value: gitSnapshot }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await clock.settle()
    await $.tool.call({ tool: 'Edit', file_path: 'C:\\repo\\docs\\c.md' })
    await $.command.run({ command: 'deck', args: 'tree' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Deck'),
    })
    expect(await ui.find({ text: /● docs\/c\.md/ })).not.toBeUndefined()
    await $.ui.press({ plugin: 'flow-deck', key: 'file-open-docs/c.md', requestId: 'deck', surface: 'terminal' })
    await clock.settle()
    expect(await ui.find({ text: /▍文件查看器 · docs\/c\.md · 1 节 · 2 行/ })).not.toBeUndefined()
    expect(readPaths).toHaveLength(1)
    // state=null 不发起任何 diff 查询
    expect(diffCalls).toEqual([])
    await ui.unmount()
  })

  test('diff 空串 → 「无未提交变更」提示与「查看全文」按钮', async ($, on) => {
    const clock = mock.clock(on)
    const gitSnapshot: GitStatus = {
      branch: 'main', upstream: 'origin/main', ahead: 0, behind: 0,
      staged: [{ code: 'M ', path: 'hooks/a.ts' }], unstaged: [], untracked: [], conflicts: [],
      added: 0, removed: 0, fetchedAt: 0,
    }
    const diffCalls: string[][] = []
    on('process.run', diffRunner(diffCalls, { exitCode: 0, stdout: '' }))
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('ui.status', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('ui.open', () => ({ value: { isPlaced: true } }))
    on('fs.list', () => ({ value: [] }))
    on('state.set', { plugin: 'flow-deck', key: 'git' }, ($, e, next) => next({ ...e, value: gitSnapshot }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await clock.settle()
    await $.command.run({ command: 'deck', args: 'tree' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Deck'),
    })
    await $.ui.press({ plugin: 'flow-deck', key: 'file-open-hooks/a.ts', requestId: 'deck', surface: 'terminal' })
    await clock.settle()
    expect(await ui.find({ text: /无未提交变更（快照可能已过期）/ })).not.toBeUndefined()
    const buttons = await ui.findAll({ type: 'Button' })
    expect(buttons.some(button => button.props.key === 'doc-view-file')).toBe(true)
    // diff 视图不提供复制全文（决策边界：复制按钮只在全文视图操作行）
    expect(buttons.some(button => button.props.key === 'doc-copy')).toBe(false)
    await ui.unmount()
  })

  test('diff 两级命令均失败 → 退化为 loadDoc 全文（D3 兜底）', async ($, on) => {
    const clock = mock.clock(on)
    const gitSnapshot: GitStatus = {
      branch: 'main', upstream: 'origin/main', ahead: 0, behind: 0,
      staged: [{ code: 'M ', path: 'hooks/a.ts' }], unstaged: [], untracked: [], conflicts: [],
      added: 1, removed: 0, fetchedAt: 0,
    }
    const diffCalls: string[][] = []
    const readPaths: string[] = []
    on('fs.read', ($, e) => {
      const norm = typeof e.path === 'string' ? e.path.replaceAll('\\', '/') : ''
      if (!norm.endsWith('hooks/a.ts')) throw new Error('ENOENT: ' + String(e.path))
      readPaths.push(norm)
      return { value: '# 标题\n正文' }
    })
    on('process.run', diffRunner(diffCalls, { exitCode: 128, stdout: '' }))
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('ui.status', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('ui.open', () => ({ value: { isPlaced: true } }))
    on('fs.list', () => ({ value: [] }))
    on('state.set', { plugin: 'flow-deck', key: 'git' }, ($, e, next) => next({ ...e, value: gitSnapshot }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await clock.settle()
    await $.command.run({ command: 'deck', args: 'tree' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Deck'),
    })
    await $.ui.press({ plugin: 'flow-deck', key: 'file-open-hooks/a.ts', requestId: 'deck', surface: 'terminal' })
    await clock.settle()
    expect(await ui.find({ text: /▍文件查看器 · hooks\/a\.ts · 1 节 · 2 行/ })).not.toBeUndefined()
    expect(readPaths).toHaveLength(1)
    // 两级 diff 均发起过（HEAD 口径与工作区口径），均失败后才退化
    expect(diffCalls.length).toBe(2)
    expect(diffCalls[0]).toEqual(['git', 'diff', 'HEAD', '--', 'hooks/a.ts'])
    expect(diffCalls[1]).toEqual(['git', 'diff', '--', 'hooks/a.ts'])
    await ui.unmount()
  })

  test('全文视图「查看变更」进 diff，diff 视图「查看全文」切回；无变更文件不显示按钮（G6）', async ($, on) => {
    const clock = mock.clock(on)
    const gitSnapshot: GitStatus = {
      branch: 'main', upstream: 'origin/main', ahead: 0, behind: 0,
      staged: [], unstaged: [{ code: ' M', path: 'hooks/a.ts' }], untracked: [], conflicts: [],
      added: 1, removed: 0, fetchedAt: 0,
    }
    const diffCalls: string[][] = []
    on('fs.read', ($, e) => {
      const norm = typeof e.path === 'string' ? e.path.replaceAll('\\', '/') : ''
      if (norm.endsWith('hooks/a.ts')) return { value: '# 标题\n正文' }
      throw new Error('ENOENT: ' + String(e.path))
    })
    on('process.run', diffRunner(diffCalls, { exitCode: 0, stdout: DIFF_HUNK }))
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('ui.status', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('ui.open', () => ({ value: { isPlaced: true } }))
    on('fs.list', () => ({ value: [] }))
    on('state.set', { plugin: 'flow-deck', key: 'git' }, ($, e, next) => next({ ...e, value: gitSnapshot }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await clock.settle()
    await $.command.run({ command: 'deck', args: 'doc hooks/a.ts' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Deck'),
    })
    expect(await ui.find({ text: /▍文件查看器 · hooks\/a\.ts/ })).not.toBeUndefined()
    // 变更清单含该文件（unstaged）→ 显示「查看变更」
    const buttons = await ui.findAll({ type: 'Button' })
    expect(buttons.some(button => button.props.key === 'doc-view-diff')).toBe(true)
    await $.ui.press({ plugin: 'flow-deck', key: 'doc-view-diff', requestId: 'deck', surface: 'terminal' })
    await clock.settle()
    expect(await ui.find({ text: /▍变更对比 · hooks\/a\.ts/ })).not.toBeUndefined()
    const code = await ui.find({ type: 'Code' })
    expect(code?.props.format).toBe('diff')
    // 「查看全文」切回
    await $.ui.press({ plugin: 'flow-deck', key: 'doc-view-file', requestId: 'deck', surface: 'terminal' })
    await clock.settle()
    expect(await ui.find({ text: /▍文件查看器 · hooks\/a\.ts/ })).not.toBeUndefined()
    expect(await ui.find({ type: 'Code' })).toBeUndefined()
    // 不在变更清单的文件不显示「查看变更」（D8 条件分支）
    await $.command.run({ command: 'deck', args: 'doc docs/other.md' })
    await clock.settle()
    const buttonsAfter = await ui.findAll({ type: 'Button' })
    expect(buttonsAfter.some(button => button.props.key === 'doc-view-diff')).toBe(false)
    await ui.unmount()
  })

  test('空态显示打开文件输入栏：submit 有效路径装载，空白输入不动作（G7）', async ($, on) => {
    const clock = mock.clock(on)
    const readPaths: string[] = []
    on('fs.read', ($, e) => {
      const norm = typeof e.path === 'string' ? e.path.replaceAll('\\', '/') : ''
      if (!norm.endsWith('docs/x.md')) throw new Error('ENOENT: ' + String(e.path))
      readPaths.push(norm)
      return { value: '# 标题\n正文' }
    })
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('ui.status', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('ui.open', () => ({ value: { isPlaced: true } }))
    on('fs.list', () => ({ value: [] }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await clock.settle()
    await $.command.run({ command: 'deck', args: 'doc' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Deck'),
    })
    const input = await ui.find({ type: 'Input' })
    expect(input).not.toBeUndefined()
    expect(input?.props.label).toBe('打开文件')
    // 空白输入不动作（$.ui.input 驱动字段为 text，引擎运行时签名自述）
    await $.ui.input({ plugin: 'flow-deck', key: 'doc-open', requestId: 'deck', surface: 'terminal', kind: 'submit', text: '   ' })
    await clock.settle()
    expect(readPaths).toEqual([])
    // 有效路径装载并切视图
    await $.ui.input({ plugin: 'flow-deck', key: 'doc-open', requestId: 'deck', surface: 'terminal', kind: 'submit', text: 'docs/x.md' })
    await clock.settle()
    expect(readPaths).toHaveLength(1)
    expect(await ui.find({ text: /▍文件查看器 · docs\/x\.md · 1 节 · 2 行/ })).not.toBeUndefined()
    await ui.unmount()
  })

  // ---- B1 GitHub Issues 区块（L2 替身编排） ----

  test('gh 正常 → 工作面板尾部 GitHub Issues 区块：条目、链接、标签；60s 定时器随面板可见拉取', async ($, on) => {
    const clock = mock.clock(on)
    const ghCalls: string[][] = []
    on('process.run', ($, e) => {
      const args = (e as { argv?: string[] }).argv ?? []
      if (args[0] === 'gh') {
        ghCalls.push(args)
        return {
          value: {
            exitCode: 0,
            stdout: JSON.stringify([
              { number: 12, title: '修复守卫', url: 'https://github.com/x/y/issues/12', labels: [{ name: 'bug' }, { name: 'P1' }] },
              { number: 13, title: '补文档', url: 'https://github.com/x/y/issues/13', labels: [] },
            ]),
          },
        }
      }
      return { value: { exitCode: 128, stdout: '', stderr: '' } }
    })
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('ui.status', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [{ id: 'deck', title: 'Deck', isShown: true, isFocused: false, isPlaced: true }] }))
    on('fs.list', () => ({ value: [] }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await clock.settle()
    await $.tool.call({ tool: 'mcp__flow-deck__flow_task', kind: 'implement', plan: 'demo', batch: 'B2' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Deck'),
    })
    expect(await ui.find({ text: /▍GitHub Issues · 2 open/ })).not.toBeUndefined()
    expect(await ui.find({ text: /#12 修复守卫/ })).not.toBeUndefined()
    expect(await ui.find({ text: /#13 补文档/ })).not.toBeUndefined()
    expect(await ui.find({ text: /· bug P1/ })).not.toBeUndefined()
    const link = await ui.find({ type: 'Link' })
    expect(link?.props.href).toBe('https://github.com/x/y/issues/12')
    // gh 命令口径：open 状态、限量 20、JSON 字段集
    expect(ghCalls[0]).toEqual(['gh', 'issue', 'list', '--state', 'open', '--limit', '20', '--json', 'number,title,url,labels'])
    // 60s 独立轮询：面板可见时下一 tick 再拉（首拉已发生，advance 后计数增长）
    const firstPulls = ghCalls.length
    await clock.advance(60_000)
    expect(ghCalls.length).toBeGreaterThan(firstPulls)
    await ui.unmount()
  })

  test('gh 失败区块静默不绘制且面板其余不受影响；空列表刷新后显示无 open issue', async ($, on) => {
    const clock = mock.clock(on)
    let ghStdout: string | null = null
    on('process.run', ($, e) => {
      const args = (e as { argv?: string[] }).argv ?? []
      if (args[0] === 'gh') {
        return ghStdout === null
          ? { value: { exitCode: 1, stdout: '', stderr: 'gh: not a git repository' } }
          : { value: { exitCode: 0, stdout: ghStdout } }
      }
      return { value: { exitCode: 128, stdout: '', stderr: '' } }
    })
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('ui.status', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('fs.list', () => ({ value: [] }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await clock.settle()
    await $.tool.call({ tool: 'mcp__flow-deck__flow_task', kind: 'implement', plan: 'demo', batch: 'B2' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Deck'),
    })
    expect(await ui.find({ text: /GitHub Issues/ })).toBeUndefined()
    expect(await ui.find({ text: /▍工作面板 · 方案实施 · demo/ })).not.toBeUndefined()
    expect(await ui.find({ text: /▍子代理/ })).not.toBeUndefined()
    // 切空列表 fixture，「刷新」按钮重拉（refreshAll 含 Issues）→ 空列表态
    ghStdout = '[]'
    await $.ui.press({ plugin: 'flow-deck', key: 'flow-refresh', requestId: 'deck', surface: 'terminal' })
    await clock.settle()
    expect(await ui.find({ text: /▍GitHub Issues · 0 open/ })).not.toBeUndefined()
    expect(await ui.find({ text: /无 open issue/ })).not.toBeUndefined()
    await ui.unmount()
  })

  test('空态（无任务/通关后）面板同样绘制 GitHub Issues 区块：标题与条目在场', async ($, on) => {
    const clock = mock.clock(on)
    on('process.run', ($, e) => {
      const args = (e as { argv?: string[] }).argv ?? []
      if (args[0] === 'gh') {
        return {
          value: {
            exitCode: 0,
            stdout: JSON.stringify([
              { number: 12, title: '修复守卫', url: 'https://github.com/x/y/issues/12', labels: [{ name: 'bug' }] },
            ]),
          },
        }
      }
      return { value: { exitCode: 128, stdout: '', stderr: '' } }
    })
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('ui.status', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('fs.list', () => ({ value: [] }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await clock.settle()
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Deck'),
    })
    // 确认走的是空态分支（无任务），区块与空态同屏
    expect(await ui.find({ text: /当前无方案迭代或实施任务/ })).not.toBeUndefined()
    expect(await ui.find({ text: /▍GitHub Issues · 1 open/ })).not.toBeUndefined()
    expect(await ui.find({ text: /#12 修复守卫/ })).not.toBeUndefined()
    const link = await ui.find({ type: 'Link' })
    expect(link?.props.href).toBe('https://github.com/x/y/issues/12')
    await ui.unmount()
  })

  test('自动侧边栏：非全屏或 autoOpen=off 时编辑不自动开面板', async ($, on) => {
    const clock = mock.clock(on)
    let opened = 0
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('ui.status', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('fs.list', () => ({ value: [] }))
    on('ui.panes', () => ({ value: [] }))
    on('ui.open', () => {
      opened++
      return { value: { isPlaced: true } }
    })
    on('tool.call', async ($, e, next) => {
      void next
      return { result: 'reached-bottom' }
    })
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    // AbovePrompt 未观测到全屏布局（测试引擎无 viewport）：首次编辑不得自动开
    await $.tool.call({ tool: 'Edit', file_path: 'C:\\repo\\a.ts' })
    await clock.settle()
    expect(opened).toBe(0)
  })

  test('自动侧边栏：autoOpen=off 时即使全屏也不开（配置守门）', { options: { autoOpen: 'off' } }, async ($, on) => {
    const clock = mock.clock(on)
    let opened = 0
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('ui.status', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('fs.list', () => ({ value: [] }))
    on('ui.panes', () => ({ value: [] }))
    on('ui.open', () => {
      opened++
      return { value: { isPlaced: true } }
    })
    on('tool.call', async ($, e, next) => {
      void next
      return { result: 'reached-bottom' }
    })
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await $.tool.call({ tool: 'Edit', file_path: 'C:\\repo\\a.ts' })
    await clock.settle()
    expect(opened).toBe(0)
  })

  test('子代理行查看按钮把主视图切到该代理，deny 时 toast 说明', async ($, on) => {
    const snapshot: AgentSnapshot = {
      loaded: true, error: false,
      agents: [{ id: 'a1', name: 'executor', type: 'runner', description: '执行批次', status: 'running' }],
    }
    const views: unknown[] = []
    let denyNext = false
    const toasts: string[] = []
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('ui.status', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('fs.list', () => ({ value: [] }))
    on('ui.toast', ($, e) => {
      toasts.push(e.text)
      return { value: undefined }
    })
    on('ui.view', ($, e) => {
      views.push(e.agentId ?? {})
      return denyNext ? { value: { deny: 'not person-initiated' } } : { value: {} }
    })
    on('state.set', { plugin: 'flow-deck', key: 'agents' }, ($, e, next) => next({ ...e, value: snapshot }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Deck'),
    })
    await $.ui.press({ plugin: 'flow-deck', key: 'agent-view-a1', requestId: 'deck', surface: 'terminal' })
    expect(views).toEqual(['a1'])
    denyNext = true
    await $.ui.press({ plugin: 'flow-deck', key: 'agent-view-a1', requestId: 'deck', surface: 'terminal' })
    expect(toasts.some(text => text.includes('无法查看子代理'))).toBe(true)
    await $.ui.press({ plugin: 'flow-deck', key: 'view-main', requestId: 'deck', surface: 'terminal' })
    expect(views.at(-1)).toEqual({})
    await ui.unmount()
  })

  test('后台任务完成通知行：状态点、名称与耗时', async ($, on) => {
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('ui.status', () => ({ value: undefined }))
    on('store.get', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('fs.list', () => ({ value: [] }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'UserMessage',
      props: {
        origin: { kind: 'task-notification' },
        task: { id: 'a1', status: 'completed', durationMs: 3200 },
        from: { name: 'executor' },
      },
    })
    expect(await ui.find({ text: /✓ executor · 3\.2s/ })).not.toBeUndefined()
    await ui.unmount()
    const failed = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'UserMessage',
      props: {
        origin: { kind: 'task-notification' },
        task: { id: 'a2', status: 'failed', durationMs: 64_000 },
        from: { name: 'reviewer' },
      },
    })
    expect(await failed.find({ text: /✗ reviewer · 1m 4s/ })).not.toBeUndefined()
    await failed.unmount()
  })

  test('跨会话收口：session.start 清空后、新快照落地前收口 → 统计不可用而非旧 cwd 值', async ($, on) => {
    const closureWrites: unknown[] = []
    let session1Done = false
    let statusCalls = 0
    const gitSnapshot = {
      branch: 'old', upstream: null, ahead: 0, behind: 0,
      staged: [], unstaged: [], untracked: [], conflicts: [],
      added: 99, removed: 88, fetchedAt: 5,
      byPath: { 'src/a.ts': [99, 88] },
      numstatSides: { worktree: 'ok', cached: 'ok' },
    }
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [] }))
    on('state.set', { plugin: 'flow-deck', key: 'git' }, ($, e, next) => {
      // 仅第一次会话期间把清空写入顶替为旧快照；第二次 session.start 的清空放行真实 null
      return session1Done ? next(e) : next({ ...e, value: gitSnapshot })
      return next(e)
    })
    on('state.set', { plugin: 'flow-deck', key: 'closureCard' }, ($, e, next) => {
      closureWrites.push(e.value)
      return next(e)
    })
    on('process.run', async ($, e) => {
      const args = (e as { args?: string[] }).args ?? []
      if (args.includes('status')) {
        statusCalls += 1
        if (statusCalls === 2) {
          // 新会话首轮 status 查询挂起：收口发生在新快照落地前
          await new Promise<void>(() => {})
        }
        return { value: { exitCode: 0, stdout: '## old\n M old-file.ts\n' } }
      }
      return { value: { exitCode: 0, stdout: '' } }
    })
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    session1Done = true
    // 第二次会话：代次递增、清空 gitStatus，新首轮查询挂起未落地
    await $.session.start({ cwd: 'C:\\other', surface: 'terminal', isInteractive: false })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_batch', plan: 'demo', batch: 'B2', files: ['src/a.ts'] })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '收口', testsPassed: 1, testsTotal: 1 })
    // 统计不可用（gitStatus 已清空、新快照未落地）而非上一 cwd 旧快照值
    expect(closureWrites.at(-1)).toEqual({
      plan: 'demo', batch: 'B2',
      closure: { files: 1, added: null, removed: null, minutes: 0 },
    })
  })

  // ---- B2 呼吸面板 + 驻场小生物（L2 替身编排） ----

  test('红线1：连发 3 次 beat tick，除 beat 外全部 PluginState 键快照不变', async ($, on) => {
    const clock = mock.clock(on)
    const STATE_KEYS = [
      'plans', 'notified', 'baselined', 'currentTask', 'execution', 'batchScope', 'guardWarned',
      'progress', 'deps', 'git', 'agents', 'lastRun', 'closureCard', 'stall', 'doc', 'docSection',
      'docMode', 'treeDir', 'treeEntries', 'touched', 'activeTab', 'beat',
    ] as const
    const writes: { key: string; value: unknown }[] = []
    let settled = false
    for (const key of STATE_KEYS) {
      on('state.set', { plugin: 'flow-deck', key }, ($, e, next) => {
        if (settled) writes.push({ key, value: e.value })
        return next(e)
      })
    }
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    on('ui.panes', () => ({ value: [{ id: 'deck', title: 'Deck', isShown: true, isFocused: false, isPlaced: true }] }))
    on('agent.list', () => ({ value: [{ id: 'a1', name: 'executor', type: 'runner', description: '稳定快照', status: 'running' }] }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    // 预热一轮 planTimer：agents 首写落地；此后 poller 同值去重，beat 窗口内不再有非 beat 写入
    await clock.advance(2000)
    settled = true
    await clock.advance(2400)
    const nonBeat = writes.filter(w => w.key !== 'beat')
    expect(nonBeat).toEqual([])
    expect(writes.filter(w => w.key === 'beat').map(w => w.value)).toEqual([1, 0, 1])
  })

  test('红线3：面板不可见或 panes 查询失败即停帧；定时器保活，下一 tick 恢复翻转', async ($, on) => {
    const clock = mock.clock(on)
    const flips: unknown[] = []
    on('state.set', { plugin: 'flow-deck', key: 'beat' }, ($, e, next) => {
      flips.push(e.value)
      return next(e)
    })
    let panes: unknown = [{ id: 'deck', title: 'Deck', isShown: true, isFocused: false, isPlaced: true }]
    let panesThrow = false
    on('ui.panes', () => {
      if (panesThrow) throw new Error('panes 查询失败')
      return { value: panes }
    })
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await clock.settle()
    flips.length = 0
    await clock.advance(800)
    expect(flips).toEqual([1])
    panes = []
    await clock.advance(800)
    expect(flips).toEqual([1])
    panesThrow = true
    await clock.advance(800)
    expect(flips).toEqual([1])
    panesThrow = false
    panes = [{ id: 'deck', title: 'Deck', isShown: true, isFocused: false, isPlaced: true }]
    await clock.advance(800)
    expect(flips).toEqual([1, 0])
  })

  test('节拍器生命周期：连续两次 session.start 后单周期翻转不翻倍', async ($, on) => {
    const clock = mock.clock(on)
    const flips: unknown[] = []
    on('state.set', { plugin: 'flow-deck', key: 'beat' }, ($, e, next) => {
      flips.push(e.value)
      return next(e)
    })
    on('ui.panes', () => ({ value: [{ id: 'deck', title: 'Deck', isShown: true, isFocused: false, isPlaced: true }] }))
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    flips.length = 0
    await clock.advance(800)
    expect(flips).toEqual([1])
  })

  test('呼吸断言：活动任务两帧着色档位交替（范围限定呼吸元素行，排除小生物行）', { options: { artDirection: 'default' } }, async ($, on) => {
    const clock = mock.clock(on)
    on('ui.panes', () => ({ value: [{ id: 'deck', title: 'Deck', isShown: true, isFocused: false, isPlaced: true }] }))
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '执行' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow'),
    })
    // beat=0 帧：呼吸元素 dim 档；确认断言对象非小生物行（盲文帧不参与呼吸）
    // beat=0 帧：呼吸元素 dim 档；确认断言对象非小生物行（盲文帧不参与呼吸）
    const phaseRow0 = await ui.find({ type: 'Text', text: /B2 · 执行/ })
    const bar0 = (await ui.findAll({ type: 'Text' })).find(node => node.text === '━━━━━━────')
    expect(phaseRow0?.props.color).toBeUndefined()
    expect(phaseRow0?.props.dimColor).toBe(true)
    expect(bar0?.props.color).toBeUndefined()
    expect(bar0?.props.dimColor).toBe(true)
    expect(/^\s*[\u2800-\u28FF]+\s*$/.test(String(phaseRow0?.text))).toBe(false)
    expect(/^\s*[\u2800-\u28FF]+\s*$/.test(String(bar0?.text))).toBe(false)
    await clock.advance(800)
    // beat=1 帧：accent 高亮档
    const phaseRow1 = await ui.find({ type: 'Text', text: /B2 · 执行/ })
    const bar1 = (await ui.findAll({ type: 'Text' })).find(node => node.text === '━━━━━━────')
    expect(phaseRow1?.props.color).toBe('professionalBlue')
    expect(phaseRow1?.props.dimColor).toBe(false)
    expect(bar1?.props.color).toBe('professionalBlue')
    expect(bar1?.props.dimColor).toBe(false)
    await ui.unmount()
  })

  test('小生物断言：两帧字符随 beat 切换；stall 注入后呼吸固定 dim、抖腿态继续切换', { options: { artDirection: 'default' } }, async ($, on) => {
    const clock = mock.clock(on)
    // 停滞注入（模式同既有停滞测试）：execution 顶替为 31 分钟前，planTimer 首轮 tick 写入 stall
    on('state.set', { plugin: 'flow-deck', key: 'execution' }, ($, e, next) =>
      next({ ...e, value: { plan: 'demo', batch: 'B2', phase: '执行', updatedAt: Date.now() - 31 * 60_000 } }))
    on('ui.panes', () => ({ value: [{ id: 'deck', title: 'Deck', isShown: true, isFocused: false, isPlaced: true }] }))
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '执行' })
    // planTimer 首轮 tick：refreshStall 写入 stall=31；期间 beat 已翻两帧回到 0
    await clock.advance(2000)
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow'),
    })
    const creature0 = await ui.find({ type: 'Text', text: frameRe(creatureFrames.legshake[0][0]) })
    const bar0 = (await ui.findAll({ type: 'Text' })).find(node => node.text === '━━━━━━────')
    expect(creature0).not.toBeUndefined()
    expect(bar0?.props.dimColor).toBe(true)
    await clock.advance(800)
    // 呼吸元素两帧固定 dim（停跳即死）；小生物抖腿态两帧继续切换
    const creature1 = await ui.find({ type: 'Text', text: frameRe(creatureFrames.legshake[1][0]) })
    const bar1 = (await ui.findAll({ type: 'Text' })).find(node => node.text === '━━━━━━────')
    expect(creature1).not.toBeUndefined()
    expect(bar1?.props.dimColor).toBe(true)
    await ui.unmount()
  })

  test('companion=off：渲染树无小生物节点，beat 照常翻转（呼吸仍在）', { options: { companion: 'off' } }, async ($, on) => {
    const clock = mock.clock(on)
    const flips: unknown[] = []
    on('state.set', { plugin: 'flow-deck', key: 'beat' }, ($, e, next) => {
      flips.push(e.value)
      return next(e)
    })
    on('ui.panes', () => ({ value: [{ id: 'deck', title: 'Deck', isShown: true, isFocused: false, isPlaced: true }] }))
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    await $.tool.call({ tool: 'mcp__flow-deck__flow_report', plan: 'demo', batch: 'B2', phase: '执行' })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow'),
    })
    expect(await ui.find({ type: 'Text', text: frameRe(creatureFrames.work[0][0]) })).toBeUndefined()
    flips.length = 0
    await clock.advance(800)
    expect(flips).toEqual([1])
    // 呼吸仍在：beat=1 帧呼吸元素 accent 高亮
    const bar = (await ui.findAll({ type: 'Text' })).find(node => node.text === '━━━━━━────')
    expect(bar?.props.color).toBe('professionalBlue')
    await ui.unmount()
  })

  test('closureCard 非空 + guardWarned 非空 + 任务在场 → 取敬礼（优先级断言）', async ($, on) => {
    // 三个输入全部注入：若优先级失守，捂脸会压过敬礼
    on('state.set', { plugin: 'flow-deck', key: 'closureCard' }, ($, e, next) =>
      next({ ...e, value: { plan: 'demo', batch: 'B2', closure: { files: 1, added: null, removed: null, minutes: null } } }))
    on('state.set', { plugin: 'flow-deck', key: 'guardWarned' }, ($, e, next) =>
      next({ ...e, value: ['src/a.ts'] }))
    on('state.set', { plugin: 'flow-deck', key: 'currentTask' }, ($, e, next) =>
      next({ ...e, value: { kind: 'implement', plan: 'demo', batch: 'B2' } }))
    on('session.start', () => ({ cwd: 'C:\\repo' }))
    on('command.register', ($, e) => ({ value: { name: e.name } }))
    on('tool.register', ($, e) => ({ value: { name: e.name } }))
    on('fs.list', () => ({ value: [] }))
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: '' } }))
    on('store.get', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    on('ui.log', () => ({ value: undefined }))
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow'),
    })
    const salute = await ui.find({ type: 'Text', text: frameRe(creatureFrames.salute[0][0]) })
    expect(salute?.props.dimColor).toBeUndefined()
    expect(await ui.find({ type: 'Text', text: frameRe(creatureFrames.facepalm[0][0]) })).toBeUndefined()
    await ui.unmount()
  })

  test('拆组③：companion=on 无任务睡觉态，default 皮肤结构与非文案信息锚点', { options: { artDirection: 'default', companion: 'on' } }, async $ => {
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow'),
    })
    const boxes = await ui.findAll({ type: 'Box' })
    const texts = await ui.findAll({ type: 'Text' })
    // 与拆组③（B）mission-control 测试一一对应的锚点值：结构与非文案信息一致，仅文案不同
    expect(boxes.length).toBe(7)
    expect(texts.length).toBe(9)
    expect(texts.filter(node => node.props.dimColor === true).length).toBe(3)
    expect(texts.filter(node => typeof node.props.color === 'string').length).toBe(0)
    const creature = await ui.find({ type: 'Text', text: frameRe(creatureFrames.sleep[0][0]) })
    expect(creature?.props.dimColor).toBeUndefined()
    // 文案为 default 词表
    expect(await ui.find({ text: /当前无方案迭代或实施任务/ })).not.toBeUndefined()
    await ui.unmount()
  })

  test('拆组③：companion=on 无任务睡觉态，mission-control 皮肤结构与非文案信息一致（仅文案不同）', { options: { artDirection: 'mission-control', companion: 'on' } }, async $ => {
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'deck',
      props: paneProps('Flow'),
    })
    const boxes = await ui.findAll({ type: 'Box' })
    const texts = await ui.findAll({ type: 'Text' })
    // 与拆组③（A）default 测试一一对应的锚点值：结构与非文案信息一致，仅文案不同
    expect(boxes.length).toBe(7)
    expect(texts.length).toBe(9)
    expect(texts.filter(node => node.props.dimColor === true).length).toBe(3)
    expect(texts.filter(node => typeof node.props.color === 'string').length).toBe(0)
    const creature = await ui.find({ type: 'Text', text: frameRe(creatureFrames.sleep[0][0]) })
    expect(creature?.props.dimColor).toBeUndefined()
    // 文案为 mission-control 词表
    expect(await ui.find({ text: /待命 · 当前无方案迭代或实施任务/ })).not.toBeUndefined()
    await ui.unmount()
  })
})
