import { describe, expect, test } from 'claude-code/testing'

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
  test('空状态给出提示文案', async $ => {
    const ui = await $.ui.mount({
      plugin: 'flow-deck',
      surface: 'terminal',
      component: 'Pane',
      requestId: 'flow',
      props: paneProps('Flow 评审仪表盘'),
    })
    await ui.find({ text: /未发现活跃的 plan-iterate 评审/ })
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
      await ui.find({ text: /demo · B2 · T1 · 执行 · 验证 12\/15/ })
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

  test('flow_deps 声明后面板绘制执行 DAG 区块', async $ => {
    const declared = await $.tool.call({
      tool: 'mcp__flow-deck__flow_deps',
      plan: 'demo',
      batches: [{ batch: 'B1', dependsOn: [] }, { batch: 'B2', dependsOn: ['B1'] }],
    })
    expect(declared.result).toBe('波次依赖已声明：demo 共 2 批')
    // B1 收口 → ✓；B2 未上报 → ○
    await $.tool.call({
      tool: 'mcp__flow-deck__flow_report',
      plan: 'demo',
      batch: 'B1',
      phase: '收口',
    })
    const ui = await $.ui.mount({
      plugin: 'flow-deck',
      surface: 'terminal',
      component: 'Pane',
      requestId: 'flow',
      props: paneProps('Flow 评审仪表盘'),
    })
    await ui.find({ text: /▍执行 DAG（demo）/ })
    await ui.find({ text: /← B1/ })
    await ui.find({ type: 'Text', text: '✓ B1' })
    await ui.find({ type: 'Text', text: '○ B2' })
    await ui.unmount()
  })

  test('flow_deps 缺 batches 返回错误结果', async $ => {
    const result = await $.tool.call({ tool: 'mcp__flow-deck__flow_deps', plan: 'demo' })
    expect(result.isError).toBe(true)
  })

  // 两类路径不经自动化测试，改由会话内 fixture 端到端确认：
  // 1. 有数据卡片的渲染（plan 卡片、git 面板、横条 git 行）——宿主规则不允许测试
  //    模块写插件状态（$.state 调用权按 hooks.json 声明的模块静态扫描，*.test.ts
  //    扫描结果恒空），且 git 数据经 $.process.run 进入而测试引擎无 process 设施；
  //    数据组装已由 parse.test.ts 的 buildPlanReview / buildGitStatus 用例覆盖。
  // 2. /flow 与 /git 命令链路——测试引擎里 $.ui.open 是无实现的 dispatch，需猜测
  //    UiOpenResult 应答形状才能喂饱链路；该处理器与官方 pane 示例同构。
})
