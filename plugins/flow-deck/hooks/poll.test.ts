import { describe, expect, test } from 'claude-code/testing'
import type { FsEntry } from 'claude-code'
import type { GitStatus } from '../types'
import { createGitPoller, createPlanScanner, DISCOVERY_MS, GIT_IDLE_MS, GIT_RETRY_MS, singleFlight } from './poll'

function entry(name: string, kind: 'file' | 'dir', mtimeMs = 1): FsEntry {
  return { name, kind, mtimeMs, size: 10, isLink: false }
}

describe('polling cost and freshness', () => {
  test('unchanged plans reuse parsed objects without file reads or project traversal', async () => {
    const listed: string[] = []
    const reads: string[] = []
    let stamp = 1
    let extraRound = false
    let deleted = false
    const scan = createPlanScanner({
      async list(path) {
        listed.push(path ?? '.')
        if (path === undefined) return [entry('docs', 'dir'), entry('node_modules', 'dir')]
        if (path === 'docs') return [entry('.plan-iterate', 'dir')]
        if (path === 'docs/.plan-iterate') return deleted ? [] : [entry('demo', 'dir')]
        if (path === 'docs/.plan-iterate/demo') return [entry('state.json', 'file'), entry('review-R1.json', 'file', stamp), ...(extraRound ? [entry('review-R2.json', 'file')] : [])]
        throw new Error(`unexpected traversal: ${path}`)
      },
      async read(path) {
        reads.push(path)
        return path.endsWith('state.json') ? '{"round":1}' : `{"score":${stamp + 6},"issues":[]}`
      },
    })
    const first = await scan(0)
    expect(first[0]?.rounds[0]?.score).toBe(7)
    expect(reads.length).toBe(2)
    listed.length = 0
    reads.length = 0
    const second = await scan(2000)
    expect(second[0]).toBe(first[0])
    expect(reads.length).toBe(0)
    expect(listed).toEqual(['docs/.plan-iterate', 'docs/.plan-iterate/demo'])
    stamp = 2
    const changed = await scan(4000)
    expect(changed[0]?.rounds[0]?.score).toBe(8)
    extraRound = true
    expect((await scan(6000))[0]?.rounds.length).toBe(2)
    deleted = true
    expect(await scan(8000)).toEqual([])
    listed.length = 0
    await scan(DISCOVERY_MS)
    expect(listed.includes('.')).toBe(true)
  })

  test('new review roots are discovered after the slower discovery interval', async () => {
    let created = false
    const scan = createPlanScanner({
      async list(path) {
        if (path === undefined) return created ? [entry('.plan-iterate', 'dir')] : []
        if (path === '.plan-iterate') return [entry('new', 'dir')]
        return [entry('state.json', 'file')]
      },
      async read() { return '{"round":1}' },
    })
    expect(await scan(0)).toEqual([])
    created = true
    expect(await scan(2000)).toEqual([])
    expect((await scan(DISCOVERY_MS))[0]?.name).toBe('new')
  })

  test('clean git runs only status, backs off, and does not publish timestamp-only changes', async () => {
    const calls: string[][] = []
    const snapshots: (GitStatus | null)[] = []
    const poll = createGitPoller(async args => {
      calls.push([...args])
      return '## main...origin/main\n'
    }, async status => { snapshots.push(status) })
    await poll(0)
    await poll(5000)
    await poll(GIT_IDLE_MS)
    expect(calls.length).toBe(2)
    expect(calls.every(args => args.includes('status'))).toBe(true)
    expect(snapshots.length).toBe(1)
  })

  test('tracked content changes with identical porcelain still refresh line counts; untracked-only skips diffs', async () => {
    let porcelain = '## main\n M src/a.ts\n'
    let added = 2
    const calls: string[][] = []
    const snapshots: (GitStatus | null)[] = []
    const poll = createGitPoller(async args => {
      calls.push([...args])
      return args.includes('status') ? porcelain : `${added}\t1\tsrc/a.ts\n`
    }, async status => { snapshots.push(status) })
    await poll(0)
    expect(calls.length).toBe(2)
    expect(calls[1]?.includes('--cached')).toBe(false)
    added = 7
    await poll(5000)
    expect(snapshots.at(-1)?.added).toBe(7)
    porcelain = '## main\n?? new.txt\n'
    calls.length = 0
    await poll(10000)
    expect(calls.length).toBe(1)
    expect(snapshots.at(-1)?.added).toBe(0)
  })

  test('non-repositories retry slowly, and explicit open can force refresh', async () => {
    let calls = 0
    const poll = createGitPoller(async () => { calls += 1; return null }, async () => {})
    await poll(0)
    await poll(5000)
    expect(calls).toBe(1)
    await poll(GIT_RETRY_MS)
    expect(calls).toBe(2)
    await poll(GIT_RETRY_MS + 1, true)
    expect(calls).toBe(3)
  })

  test('timer and forced git refresh share one in-flight query', async () => {
    let calls = 0
    let finish: (value: string) => void = () => {}
    const poll = createGitPoller(async () => {
      calls += 1
      return new Promise<string>(resolve => { finish = resolve })
    }, async () => {})
    const first = poll(0)
    const forced = poll(5000, true)
    expect(calls).toBe(1)
    finish('## main\n')
    await Promise.all([first, forced])
  })

  test('slow scans never overlap and failed scans can retry', async () => {
    let calls = 0
    let finish: () => void = () => {}
    const scan = singleFlight(async () => {
      calls += 1
      await new Promise<void>(resolve => { finish = resolve })
    })
    const first = scan()
    await scan()
    expect(calls).toBe(1)
    finish()
    await first
    const second = scan()
    expect(calls).toBe(2)
    finish()
    await second
    let attempts = 0
    const retry = singleFlight(async () => { attempts += 1; throw new Error('transient') })
    await retry().catch(() => {})
    await retry().catch(() => {})
    expect(attempts).toBe(2)
  })
})
