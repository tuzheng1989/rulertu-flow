import type { FsEntry } from 'claude-code'
import { buildGitStatus, buildPlanReview, extractRound, parseNumstat, parsePorcelain } from './parse'
import type { GitStatus, PlanReview } from '../types'

export const DISCOVERY_MS = 30_000
export const GIT_ACTIVE_MS = 5_000
export const GIT_IDLE_MS = 15_000
export const GIT_RETRY_MS = 60_000
const SKIP_DIRS = new Set(['node_modules', '.git', '.venv', 'venv', '__pycache__', 'dist', 'build'])

/** 慢查询未完成时跳过后续 tick；失败后仍允许下一轮重试。 */
export function singleFlight(task: () => Promise<void>): () => Promise<void> {
  let busy = false
  return async () => {
    if (busy) return
    busy = true
    try {
      await task()
    } finally {
      busy = false
    }
  }
}

/** 仅发现目录时遍历项目；平时只查看已知评审根，按文件元数据缓存解析结果。 */
export function createPlanScanner(fs: {
  list: (path?: string) => Promise<FsEntry[]>
  read: (path: string) => Promise<string>
}) {
  let roots = new Set<string>()
  let discoveredAt = -Infinity
  const cache = new Map<string, { signature: string; plan: PlanReview }>()

  async function list(path: string) {
    try {
      return path === '' ? await fs.list() : await fs.list(path)
    } catch {
      return []
    }
  }

  async function discover(rel: string, depth: number, found: Set<string>): Promise<void> {
    if (depth > 4) return
    for (const entry of await list(rel)) {
      if (entry.kind !== 'dir' || SKIP_DIRS.has(entry.name)) continue
      const child = rel === '' ? entry.name : `${rel}/${entry.name}`
      if (entry.name === '.plan-iterate') found.add(child)
      else await discover(child, depth + 1, found)
    }
  }

  return async (now: number): Promise<PlanReview[]> => {
    if (now - discoveredAt >= DISCOVERY_MS) {
      const found = new Set<string>()
      await discover('', 0, found)
      roots = found
      discoveredAt = now
    }
    const plans: PlanReview[] = []
    const live = new Set<string>()
    for (const root of roots) {
      for (const entry of await list(root)) {
        if (entry.kind !== 'dir') continue
        const dir = `${root}/${entry.name}`
        live.add(dir)
        try {
          const files = (await fs.list(dir))
            .filter(file => file.kind === 'file' && (file.name === 'state.json' || extractRound(file.name) !== null))
            .sort((a, b) => a.name.localeCompare(b.name))
          if (!files.some(file => file.name === 'state.json')) continue
          const stamps = files.map(file => [file.name, file.mtimeMs, file.size])
          const signature = JSON.stringify(stamps)
          const cached = cache.get(dir)
          if (cached?.signature === signature) {
            plans.push(cached.plan)
            continue
          }
          const reviews = []
          let state = ''
          for (const file of files) {
            const text = await fs.read(`${dir}/${file.name}`)
            if (file.name === 'state.json') state = text
            else reviews.push({ round: extractRound(file.name)!, text })
          }
          const plan = buildPlanReview(entry.name, dir, state, reviews)
          cache.set(dir, { signature, plan })
          plans.push(plan)
        } catch {
          // 原子替换/删除中的文件留待下一轮；不将半次读取写入缓存。
          const cached = cache.get(dir)
          if (cached) plans.push(cached.plan)
        }
      }
    }
    for (const dir of cache.keys()) if (!live.has(dir)) cache.delete(dir)
    return plans.sort((a, b) => a.name.localeCompare(b.name) || a.dir.localeCompare(b.dir))
  }
}

/** 时间戳不参与比较，避免仅取数时间变化就触发整棵 UI 刷新。 */
export function gitSnapshotKey(status: GitStatus | null): string {
  if (status === null) return 'null'
  const { fetchedAt, ...visible } = status
  void fetchedAt
  return JSON.stringify(visible)
}

export function createGitPoller(
  run: (args: readonly string[]) => Promise<string | null>,
  publish: (status: GitStatus | null) => Promise<void>,
) {
  let nextAt = -Infinity
  let previous: string | undefined
  let inFlight: Promise<void> | undefined
  async function poll(now: number, force: boolean): Promise<void> {
    if (!force && now < nextAt) return
    const text = await run(['--no-optional-locks', '-c', 'core.quotePath=false', 'status', '--porcelain=v1', '-b'])
    let status: GitStatus | null = null
    if (text !== null) {
      const porcelain = parsePorcelain(text)
      if (porcelain === null) return
      // 无对应 tracked 更改时省掉 diff；不按 porcelain 缓存行数，同一 M 状态内容仍会变化。
      const base = buildGitStatus(porcelain, { added: 0, removed: 0 }, { added: 0, removed: 0 }, now)
      const [worktree, cached] = await Promise.all([
        base.unstaged.length + base.conflicts.length > 0 ? run(['diff', '--no-ext-diff', '--no-textconv', '--numstat']) : null,
        base.staged.length > 0 ? run(['diff', '--cached', '--no-ext-diff', '--no-textconv', '--numstat']) : null,
      ])
      status = buildGitStatus(porcelain, parseNumstat(worktree ?? ''), parseNumstat(cached ?? ''), now)
      nextAt = now + (porcelain.files.length > 0 ? GIT_ACTIVE_MS : GIT_IDLE_MS)
    } else {
      nextAt = now + GIT_RETRY_MS
    }
    const key = gitSnapshotKey(status)
    if (key !== previous) {
      await publish(status)
      previous = key
    }
  }
  return (now: number, force = false): Promise<void> => {
    if (inFlight) return inFlight
    inFlight = poll(now, force).finally(() => { inFlight = undefined })
    return inFlight
  }
}
