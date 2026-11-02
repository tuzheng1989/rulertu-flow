import type { ThemeKey } from 'claude-code'

/**
 * 语义色 token：全文界面颜色只经此表取值（出处：plans/flow-deck/2026-11-01-native-ui-redesign.md §设计契约）。
 * ThemeKey 跟随用户 /theme 与换肤类 mod 自动适配；渲染层禁用 ANSI 字面量色名。
 */
export const TONE = {
  /** 面板标题、flow 前缀、进行中强调、chip 底色（2026-11-02 应用户要求由 claude 橙改为蓝） */
  accent: 'professionalBlue',
  /** 子代理区强调色：保留与 Claude Code 子代理展示一致的橙 */
  agent: 'claude',
  /** 完成/达标/已暂存/ahead/干净（承接旧 green） */
  ok: 'success',
  /** 警告/待达标/未暂存/behind/停滞（承接旧 yellow） */
  warn: 'warning',
  /** 失败/冲突/P0/越界（承接旧 red） */
  bad: 'error',
  /** git 行级新增（+N） */
  added: 'diffAdded',
  /** git 行级删除（−N） */
  removed: 'diffRemoved',
} as const satisfies Record<string, ThemeKey>

/** 状态符号表：一词一义（出处同上）。面板标题、状态点、DAG 节点与连线只经此表取值。 */
export const MARK = {
  /** 面板/区块标题前缀（唯一标题标记） */
  title: '▍',
  /** 活动中 */
  run: '●',
  /** 非活动：待执行/未知状态/子代理已停止 */
  idle: '○',
  /** 完成/达标/干净 */
  done: '✓',
  /** 失败/冲突 */
  bad: '✗',
  /** DAG 节点：收口 */
  nodeDone: '■',
  /** DAG 节点：进行中 */
  nodeRun: '▣',
  /** DAG 节点：待执行 */
  nodeWait: '□',
  /** 非状态信息行前缀（横条 git 行、批次边界行） */
  info: '◇',
  /** 预警/疑似停滞（区别于 ✗：尚未失败） */
  alert: '⚠',
  /** 批次边界内文件标注（/tree 面板） */
  pin: '◆',
} as const
