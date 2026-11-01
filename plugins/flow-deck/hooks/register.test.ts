import { describe, expect, mock, test } from 'claude-code/testing'
import type { AgentSnapshot } from '../types'

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
    let gitWritten = false
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
      // 首次写入用真实快照顶替，之后放行（模拟轮询取到 git 数据）
      if (!gitWritten) {
        gitWritten = true
        return next({ ...e, value: gitSnapshot })
      }
      return next(e)
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
      ['.plan-iterate/beta/review-R3.json', '{"score":6.8,"issues":[{"severity":"P1"}]}'],
    ])
    const dirs = new Map<string, Array<{ name: string; kind: 'file' | 'dir'; size: number; mtimeMs: number; isLink: boolean }>>([
      ['', [{ name: '.plan-iterate', kind: 'dir', size: 0, mtimeMs: 0, isLink: false }]],
      ['.plan-iterate', [{ name: 'beta', kind: 'dir', size: 0, mtimeMs: 0, isLink: false }]],
      ['.plan-iterate/beta', [
        { name: 'review-R3.json', kind: 'file', size: 44, mtimeMs: 2, isLink: false },
        { name: 'state.json', kind: 'file', size: 28, mtimeMs: 1, isLink: false },
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

  test('实施上报超时未续报时提示疑似停滞，同值不重复写状态', async ($, on) => {
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
      // 风险定级在面板执行卡内为反色 chip（accent 底 + inverseText）
      const chips = await pane.findAll({ type: 'Text', text: ' T1 ' })
      expect(chips.some(seg => seg.props.backgroundColor === 'claude')).toBe(true)
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

  test('flow_deps 声明后面板绘制执行 DAG 区块与分色总览条', async $ => {
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

  test('没有评审或 DAG 时，上报仍显示执行卡片（极简阶段条）；宽窄面板跨表面渲染', async $ => {
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
  // 1. 有数据卡片的渲染（plan 卡片、git 面板、横条 git 行）——宿主规则不允许测试
  //    模块写插件状态（$.state 调用权在按 hooks.json 声明的模块静态扫描，*.test.ts
  //    扫描结果恒空），且 git 数据经 $.process.run 进入而测试引擎无 process 设施；
  //    数据组装已由 parse.test.ts 的 buildPlanReview / buildGitStatus 用例覆盖。
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
})
