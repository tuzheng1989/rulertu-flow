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
        props: { hasSurvey: false, isWorking: false, maxRows: 3, bodyColumns: 80 },
      })
      await ui.find({ text: /demo · B2 · T1 · 执行 · 验证 12\/15/ })
      await ui.unmount()
    }
  })

  // 「无上报时横条让位」不单测：该分支就是 return next(e)，链底兜底是引擎语义，
  // 测试引擎没有实现可喂（M1 时 $.ui.open 同理）。

  // 两类路径不经自动化测试，改由会话内 fixture 端到端确认：
  // 1. 有数据卡片的渲染——宿主规则不允许测试模块写插件状态（$.state 调用权按
  //    hooks.json 声明的模块静态扫描，*.test.ts 扫描结果恒空）；数据组装已由
  //    parse.test.ts 的 buildPlanReview 用例覆盖。
  // 2. /flow 命令链路——测试引擎里 $.ui.open 是无实现的 dispatch，需猜测
  //    UiOpenResult 应答形状才能喂饱链路；该处理器与官方 pane 示例同构。
})
