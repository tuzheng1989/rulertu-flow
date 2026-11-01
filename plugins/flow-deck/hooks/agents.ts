import type { AgentInfo, ThemeKey } from 'claude-code'
import type { AgentSnapshot } from '../types'
import { singleFlight } from './poll'
import { MARK, TONE } from './ui'

export function agentStatus(status: string): { label: string; mark: string; color?: ThemeKey } {
  switch (status) {
    case 'running': return { label: '运行中', mark: MARK.run, color: TONE.accent }
    case 'completed': return { label: '已完成', mark: MARK.done, color: TONE.ok }
    case 'failed': return { label: '失败', mark: MARK.bad, color: TONE.bad }
    case 'killed': return { label: '已停止', mark: MARK.idle, color: TONE.warn }
    default: return { label: status || '未知', mark: MARK.idle }
  }
}

/** 未知状态保留原文，不将等待、空闲或新宿主状态误判为运行/完成。 */
export function agentSummary(agents: readonly AgentInfo[]): string {
  const count = (status: string) => agents.filter(agent => agent.status === status).length
  const other = agents.filter(agent => !['running', 'completed', 'failed', 'killed'].includes(agent.status)).length
  return `运行中 ${count('running')} · 完成 ${count('completed')} · 失败 ${count('failed')} · 停止 ${count('killed')}` +
    (other > 0 ? ` · 其他 ${other}` : '')
}

/** 只读宿主清单；相同快照不重绘，失败保留旧值并明确标记过期，下轮可恢复。 */
export function createAgentPoller(
  list: () => Promise<AgentInfo[]>,
  publish: (snapshot: AgentSnapshot) => Promise<void>,
) {
  let snapshot: AgentSnapshot = { agents: [], loaded: false, error: false }
  return singleFlight(async () => {
    let next: AgentSnapshot
    try {
      const agents = (await list()).map(agent => ({ ...agent })).sort((a, b) =>
        Number(b.status === 'running') - Number(a.status === 'running') || a.id.localeCompare(b.id))
      next = { agents, loaded: true, error: false }
    } catch {
      next = { ...snapshot, error: true }
    }
    if (JSON.stringify(next) === JSON.stringify(snapshot)) return
    await publish(next)
    snapshot = next
  })
}
