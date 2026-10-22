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
    on('ui.panes', () => ({ value: open ? [{ id: 'flow', title: 'Flow 当前任务', isShown: true, isFocused: false, isPlaced: true }] : [] }))
    on('ui.open', { id: 'flow' }, () => {
      open = true
      return { value: { isPlaced: true } }
    })
    on('ui.close', { id: 'flow' }, () => {
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
    await $.command.run({ command: 'flow-agents' })
    await clock.settle()
    expect(calls).toBe(1)
    const ui = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'flow',
      props: paneProps('Flow 当前任务'),
    })
    expect(await ui.find({ text: /● 运行中 · executor/ })).not.toBeUndefined()
    status = 'completed'
    await clock.advance(2000)
    expect(calls).toBe(2)
    expect(await ui.find({ text: /✓ 已完成 · executor/ })).not.toBeUndefined()
    await $.command.run({ command: 'flow' })
    await clock.advance(4000)
    expect(calls).toBe(2)
    await $.session.start({ cwd: 'C:\\repo', surface: 'terminal', isInteractive: false })
    expect(await ui.find({ text: /executor/ })).toBeUndefined()
    await ui.unmount()
  })

  test('/flow-agents 幂等打开合并面板，重复调用不关闭，由 /flow 关闭', async ($, on) => {
    let open = false
    let opened = 0
    let closed = 0
    on('ui.panes', () => ({ value: open ? [{ id: 'flow', title: 'Flow 当前任务', isShown: true, isFocused: false, isPlaced: true }] : [] }))
    on('ui.open', { id: 'flow' }, () => {
      open = true
      opened++
      return { value: { isPlaced: true } }
    })
    on('ui.close', { id: 'flow' }, () => {
      open = false
      closed++
      return { value: undefined }
    })
    expect((await $.command.run({ command: 'flow-agents' })).text).toBe('已打开工作流面板（含子代理状态）。')
    expect((await $.command.run({ command: 'flow-agents' })).text).toBe('工作流面板已打开，子代理状态在面板内。')
    expect(opened).toBe(1)
    expect(closed).toBe(0)
    expect((await $.command.run({ command: 'flow' })).text).toBe('已关闭工作流面板。')
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
        plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'flow',
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
          plugin: 'flow-deck', surface, component: 'Pane', requestId: 'flow',
          props: { ...paneProps('Flow 当前任务'), bodyColumns },
        })
        for (const text of [/运行中 1 · 完成 1 · 失败 1 · 停止 1 · 其他 1/, /● 运行中 · executor/,
          /✗ 失败 · 检查边界/, /✓ 已完成/, /■ 已停止/, /○ queued/, /任务：实现面板/,
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
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'flow',
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
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'flow',
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
      requestId: 'flow',
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
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'flow',
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
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'flow',
      props: paneProps('Flow 当前任务'),
    })
    expect(await ui.find({ text: /当前执行 · demo/ })).not.toBeUndefined()
    expect(await ui.find({ text: /● 运行中 · executor/ })).not.toBeUndefined()
    const button = await ui.find({ type: 'Button' })
    expect(button?.props.hotkey).toBe('r')
    expect(button?.props.key).toBe('flow-refresh')
    await $.ui.press({ plugin: 'flow-deck', key: 'flow-refresh', requestId: 'flow', surface: 'terminal' })
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
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'flow',
      props: paneProps('Flow 当前任务'),
    })
    expect(await ui.find({ text: /✓ 已达标 1 个方案（已折叠）/ })).not.toBeUndefined()
    expect(await ui.find({ text: /● demo/ })).toBeUndefined()
    await ui.unmount()
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
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'flow',
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

  // warn 模式的越界提醒不做自动化：$.ui.log 在测试引擎是无实现的 dispatch
  // （同 $.ui.open），其判定逻辑与 deny 共用 guardDecision 纯函数（已覆盖）。

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
      requestId: 'flow',
      props: paneProps('Flow 评审仪表盘'),
    })
    expect(await ui.find({ text: /▍执行 DAG（demo）/ })).not.toBeUndefined()
    expect(await ui.find({ text: /← B1/ })).not.toBeUndefined()
    expect(await ui.find({ type: 'Text', text: '✓ B1' })).not.toBeUndefined()
    expect(await ui.find({ type: 'Text', text: '● B2' })).not.toBeUndefined()
    expect(await ui.find({ text: /1\/3 收口/ })).not.toBeUndefined()
    // 总览条按批着色：收口 ■ 绿、进行 ▣ 黄、待执行 □ 灰（分段文本经引擎文本匹配，颜色查 props）
    const dones = await ui.findAll({ type: 'Text', text: '■' })
    expect(dones.some(seg => seg.props.color === 'green')).toBe(true)
    const actives = await ui.findAll({ type: 'Text', text: '▣' })
    expect(actives.some(seg => seg.props.color === 'yellow')).toBe(true)
    const pendings = await ui.findAll({ type: 'Text', text: '□' })
    expect(pendings.some(seg => seg.props.dimColor === true)).toBe(true)
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
          plugin: 'flow-deck', surface, component: 'Pane', requestId: 'flow',
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
          plugin: 'flow-deck', surface, component: 'Pane', requestId: 'flow',
          props: { ...paneProps('Flow'), bodyColumns },
        })
        expect(await ui.find({ text: /FLOW \/ 方案迭代 · 当前迭代/ })).not.toBeUndefined()
        expect(await ui.find({ text: /等待评审结果落盘/ })).not.toBeUndefined()
        expect(await ui.find({ text: /当前执行|执行 DAG|◇ 边界|旧实施/ })).toBeUndefined()
        await ui.unmount()
      }
    }
    await $.tool.call({ tool: 'mcp__flow-deck__flow_task', kind: 'idle' })
    const idle = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'flow', props: paneProps('Flow'),
    })
    expect(await idle.find({ text: /当前无方案迭代或实施任务/ })).not.toBeUndefined()
    await idle.unmount()
    await $.tool.call({ tool: 'mcp__flow-deck__flow_task', kind: 'implement', plan: '新实施', batch: 'B2' })
    const implementing = await $.ui.mount({
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'flow', props: paneProps('Flow'),
    })
    expect(await implementing.find({ text: /FLOW \/ 方案实施 · 新实施/ })).not.toBeUndefined()
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
      plugin: 'flow-deck', surface: 'terminal', component: 'Pane', requestId: 'flow', props: paneProps('Flow'),
    })
    expect(await ui.find({ text: /FLOW \/ 方案迭代 · demo/ })).not.toBeUndefined()
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
  //    模块写插件状态（$.state 调用权按 hooks.json 声明的模块静态扫描，*.test.ts
  //    扫描结果恒空），且 git 数据经 $.process.run 进入而测试引擎无 process 设施；
  //    数据组装已由 parse.test.ts 的 buildPlanReview / buildGitStatus 用例覆盖。
  // 2. /flow 与 /git 命令链路——测试引擎里 $.ui.open 是无实现的 dispatch，需猜测
  //    UiOpenResult 应答形状才能喂饱链路；该处理器与官方 pane 示例同构。
})
