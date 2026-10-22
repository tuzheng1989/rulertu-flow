import { describe, expect, test } from 'claude-code/testing'
import type { AgentInfo } from 'claude-code'
import type { AgentSnapshot } from '../types'
import { agentStatus, agentSummary, createAgentPoller } from './agents'

const worker: AgentInfo = { id: 'a1', name: 'executor', description: '实现子代理面板', type: 'executor', status: 'running' }

describe('agent monitor', () => {
  test('生命周期变化更新清单；相同清单、不同返回顺序不重复写状态', async () => {
    const writes: AgentSnapshot[] = []
    let rows: AgentInfo[] = [{ ...worker, status: 'completed' }, { ...worker, id: 'a2' }]
    const poll = createAgentPoller(async () => rows, async value => { writes.push(value) })
    await poll()
    expect(writes[0].agents.map(agent => agent.id)).toEqual(['a2', 'a1'])
    rows = [...rows].reverse()
    await poll()
    expect(writes.length).toBe(1)
    rows = rows.map(agent => ({ ...agent, status: agent.id === 'a2' ? 'failed' : 'killed' }))
    await poll()
    expect(agentSummary(writes[1].agents)).toBe('运行中 0 · 完成 0 · 失败 1 · 停止 1')
    rows = []
    await poll()
    expect(writes[2]).toEqual({ agents: [], loaded: true, error: false })
  })

  test('查询失败保留旧值并标记过期；重试恢复时清除错误', async () => {
    const writes: AgentSnapshot[] = []
    let fail = true
    const poll = createAgentPoller(async () => {
      if (fail) throw new Error('unavailable')
      return [worker]
    }, async value => { writes.push(value) })
    await poll()
    expect(writes[0]).toEqual({ agents: [], loaded: false, error: true })
    fail = false
    await poll()
    fail = true
    await poll()
    await poll()
    expect(writes.length).toBe(3)
    expect(writes[2]).toEqual({ agents: [worker], loaded: true, error: true })
    fail = false
    await poll()
    expect(writes[3].error).toBe(false)
  })

  test('未知状态保留原文，等待/空闲不计为运行中', () => {
    expect(agentStatus('idle').label).toBe('idle')
    expect(agentStatus('').label).toBe('未知')
    expect(agentSummary([{ ...worker, status: 'queued' }, { ...worker, id: 'a2', status: 'idle' }]))
      .toBe('运行中 0 · 完成 0 · 失败 0 · 停止 0 · 其他 2')
  })

  test('慢查询防重入', async () => {
    let release!: (rows: AgentInfo[]) => void
    let calls = 0
    const poll = createAgentPoller(() => {
      calls++
      return new Promise(resolve => { release = resolve })
    }, async () => {})
    const first = poll()
    await poll()
    expect(calls).toBe(1)
    release([worker])
    await first
  })
})
