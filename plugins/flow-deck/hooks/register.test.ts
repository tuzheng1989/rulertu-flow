import { describe, test } from 'claude-code/testing'

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

  // 两类路径不经自动化测试，改由会话内 fixture 端到端确认：
  // 1. 有数据卡片的渲染——宿主规则不允许测试模块写插件状态（$.state 调用权按
  //    hooks.json 声明的模块静态扫描，*.test.ts 扫描结果恒空）；数据组装已由
  //    parse.test.ts 的 buildPlanReview 用例覆盖。
  // 2. /flow 命令链路——测试引擎里 $.ui.open 是无实现的 dispatch，需猜测
  //    UiOpenResult 应答形状才能喂饱链路；该处理器与官方 pane 示例同构。
})
