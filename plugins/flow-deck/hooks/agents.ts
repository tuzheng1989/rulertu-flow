import type { AgentInfo } from 'claude-code'
import type { AgentSnapshot } from '../types'
import { singleFlight } from './poll'

export function agentStatus(status: string): { label: string; mark: string; color?: string } {
  switch (status) {
    case 'running': return { label: '运行中', mark: '●', color: 'cyan' }
    case 'completed': return { label: '已完成', mark: '✓', color: 'green' }
    case 'failed': return { label: '失败', mark: '✗', color: 'red' }
    case 'killed': return { label: '已停止', mark: '■', color: 'yellow' }
    default: return { label: status || '未知', mark: '○' }
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
