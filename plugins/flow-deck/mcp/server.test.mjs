// flow-deck mcp server 单测（node:test，不依赖 claude-code/testing——那是 Claude Code SDK 专属）。
// 覆盖：parseGhIssues 四情形（对齐 hooks/register.test.ts:2549-2650 范式）、gh 错误归类、
// TTL 缓存、handleMessage 协议路由、子进程级 NDJSON 冒烟（不触发真实 gh 的路径）。
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { once } from 'node:events'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const { parseGhIssues, runGh, createIssueStore, handleMessage } = await import('./server.mjs')

const GOOD_ROWS = JSON.stringify([
  { number: 1, title: '修复登录', url: 'https://github.com/o/r/issues/1', labels: [{ name: 'bug' }, { name: 'P0' }] },
  { number: 2, title: '新增导出', url: 'https://github.com/o/r/issues/2', labels: [] },
])

// ---- parseGhIssues（移植自 hooks/parse.ts:285-307，校验口径必须一致）----
test('parseGhIssues 正常列表：labels 取 .name', () => {
  const issues = parseGhIssues(GOOD_ROWS)
  assert.deepEqual(issues, [
    { number: 1, title: '修复登录', url: 'https://github.com/o/r/issues/1', labels: ['bug', 'P0'] },
    { number: 2, title: '新增导出', url: 'https://github.com/o/r/issues/2', labels: [] },
  ])
})

test('parseGhIssues 空列表', () => {
  assert.deepEqual(parseGhIssues('[]'), [])
})

test('parseGhIssues 坏 JSON 与非数组返回 null', () => {
  assert.equal(parseGhIssues('not json'), null)
  assert.equal(parseGhIssues('{"issues":[]}'), null)
})

test('parseGhIssues 坏条目剔除不弃整份，缺 labels 视为空数组', () => {
  const issues = parseGhIssues(JSON.stringify([
    null,
    { title: '缺 number' },
    { number: 'x', title: 'number 类型错', url: 'u' },
    { number: 3, title: '缺 url' },
    { number: 7, title: '合法', url: 'u7' },
    { number: 8, title: '合法无 labels', url: 'u8', labels: [{ other: 1 }, 'raw'] },
  ]))
  assert.deepEqual(issues, [
    { number: 7, title: '合法', url: 'u7', labels: [] },
    { number: 8, title: '合法无 labels', url: 'u8', labels: [] },
  ])
})

// ---- runGh：gh 失败归类（原版静默，面板场景携带原因）----
const ghErrorStub = (errorFactory) => async () => { throw errorFactory() }

test('runGh gh 不存在 → ENOENT 文案', async () => {
  const payload = await runGh(ghErrorStub(() => Object.assign(new Error('spawn gh ENOENT'), { code: 'ENOENT' })))
  assert.equal(payload.error, 'gh_failed')
  assert.match(payload.message, /gh 命令不可用/)
})

test('runGh gh 非零退出 → stderr 首行', async () => {
  const payload = await runGh(ghErrorStub(() => Object.assign(new Error('exit 1'), { stderr: 'not a git repository\nsecond line' })))
  assert.equal(payload.error, 'gh_failed')
  assert.equal(payload.message, 'gh 调用失败：not a git repository')
})

test('runGh gh 超时', async () => {
  const payload = await runGh(ghErrorStub(() => Object.assign(new Error('timeout'), { killed: true })))
  assert.match(payload.message, /超时/)
})

test('runGh 坏输出 → 解析失败文案', async () => {
  const payload = await runGh(async () => ({ stdout: '[]]', stderr: '' }))
  assert.match(payload.message, /解析失败/)
})

test('runGh 正常 → issues + fetchedAt', async () => {
  const payload = await runGh(async () => ({ stdout: GOOD_ROWS, stderr: '' }))
  assert.equal(payload.error, undefined)
  assert.equal(payload.issues.length, 2)
  assert.ok(payload.fetchedAt > 0)
})

// ---- createIssueStore：60s TTL ----
test('issueStore 新鲜缓存不重拉，过期与 force 重拉', async () => {
  let clock = 1000
  let calls = 0
  const store = createIssueStore(async () => { calls += 1; return { issues: [], fetchedAt: clock } }, () => clock)
  await store.read(false); assert.equal(calls, 1)
  clock += 30_000
  await store.read(false); assert.equal(calls, 1, '30s 内走缓存')
  clock += 31_000
  await store.read(false); assert.equal(calls, 2, '超 60s 重拉')
  await store.read(false); assert.equal(calls, 2)
  await store.read(true); assert.equal(calls, 3, 'force 忽略缓存')
})

// ---- handleMessage 协议路由 ----
const stubStore = createIssueStore(async () => ({ issues: [{ number: 1, title: 't', url: 'u', labels: [] }], fetchedAt: 1 }), () => 0)
const deps = { store: stubStore, panelPath: join(dirname(fileURLToPath(import.meta.url)), 'panel.html'), serverInfo: { name: 'flow-deck-issues', version: '0.24.0' } }
const msg = (id, method, params) => ({ jsonrpc: '2.0', id, method, params })

test('initialize 回显协议版本与能力', async () => {
  const res = await handleMessage(msg(1, 'initialize', { protocolVersion: '2025-11-25' }), deps)
  assert.equal(res.result.protocolVersion, '2025-11-25')
  assert.deepEqual(res.result.capabilities, { resources: {}, tools: {} })
  assert.equal(res.result.serverInfo.name, 'flow-deck-issues')
})

test('notifications 与 ping', async () => {
  assert.equal(await handleMessage({ jsonrpc: '2.0', method: 'notifications/initialized' }, deps), null)
  assert.deepEqual((await handleMessage(msg(2, 'ping'), deps)).result, {})
})

test('tools/list 含 refresh_issues 且 app 可见性隔离', async () => {
  const tool = (await handleMessage(msg(3, 'tools/list'), deps)).result.tools[0]
  assert.equal(tool.name, 'refresh_issues')
  assert.deepEqual(tool._meta, { ui: { visibility: ['app'] } })
})

test('tools/call refresh_issues 走 force 缓存返回 structuredContent', async () => {
  const res = await handleMessage(msg(4, 'tools/call', { name: 'refresh_issues', arguments: {} }), deps)
  assert.equal(res.result.isError, false)
  assert.equal(res.result.structuredContent.issues[0].number, 1)
  assert.equal((await handleMessage(msg(5, 'tools/call', { name: 'nope' }), deps)).error.code, -32602)
})

test('resources/list 与 resources/read（panel.html + issues.json）', async () => {
  const resources = (await handleMessage(msg(6, 'resources/list'), deps)).result.resources
  assert.deepEqual(resources.map((r) => r.uri), ['ui://flow-deck/panel.html', 'ui://flow-deck/issues.json'])
  assert.equal(resources[0].mimeType, 'text/html;profile=mcp-app')

  const panel = (await handleMessage(msg(7, 'resources/read', { uri: 'ui://flow-deck/panel.html' }), deps)).result
  assert.ok(panel.contents[0].text.startsWith('<!doctype html>'))
  assert.equal(panel.contents[0].mimeType, 'text/html;profile=mcp-app')

  const issues = (await handleMessage(msg(8, 'resources/read', { uri: 'ui://flow-deck/issues.json' }), deps)).result
  assert.equal(issues.contents[0].mimeType, 'application/json')
  assert.equal(JSON.parse(issues.contents[0].text).issues[0].number, 1)
  assert.equal((await handleMessage(msg(9, 'resources/read', { uri: 'ui://x/y' }), deps)).error.code, -32602)
})

test('未知方法与非法消息', async () => {
  assert.equal((await handleMessage(msg(10, 'foo/bar'), deps)).error.code, -32601)
  assert.equal((await handleMessage({ jsonrpc: '1.0', id: 11, method: 'ping' }, deps)).error.code, -32600)
})

// ---- 子进程级 NDJSON 冒烟（仅不触发 gh 的路径）----
test('子进程 stdio 冒烟：initialize → tools/list → resources/read panel.html', { timeout: 15000 }, async () => {
  const serverPath = join(dirname(fileURLToPath(import.meta.url)), 'server.mjs')
  const child = spawn(process.execPath, [serverPath], { stdio: ['pipe', 'pipe', 'pipe'] })
  const lines = []
  let stderr = ''
  child.stdout.setEncoding('utf8')
  child.stderr.setEncoding('utf8')
  child.stdout.on('data', (chunk) => lines.push(...chunk.split('\n').filter(Boolean)))
  child.stderr.on('data', (chunk) => { stderr += chunk })
  const send = (m) => child.stdin.write(`${JSON.stringify(m)}\n`)
  send(msg(1, 'initialize', { protocolVersion: '2025-06-18' }))
  send(msg(2, 'tools/list'))
  send(msg(3, 'resources/read', { uri: 'ui://flow-deck/panel.html' }))
  send(msg(4, 'foo'))
  await new Promise((resolve) => {
    const timer = setInterval(() => {
      if (lines.length >= 4) { clearInterval(timer); resolve() }
    }, 50)
    setTimeout(() => { clearInterval(timer); resolve() }, 8000)
  })
  child.kill()
  const responses = lines.map((line) => JSON.parse(line))
  const byId = Object.fromEntries(responses.filter((r) => r.id !== null).map((r) => [r.id, r]))
  assert.equal(byId[1].result.serverInfo.name, 'flow-deck-issues')
  assert.equal(byId[2].result.tools[0].name, 'refresh_issues')
  assert.ok(byId[3].result.contents[0].text.startsWith('<!doctype html>'))
  assert.equal(byId[4].error.code, -32601)
})

// 回归：stdin EOF 早于异步处理完成时不得提前退出（首版在 gh 慢响应场景下被 process.exit 截断）
test('子进程 EOF 竞争：stdin 写完即关，慢异步响应仍完整写出', { timeout: 15000 }, async () => {
  const serverPath = join(dirname(fileURLToPath(import.meta.url)), 'server.mjs')
  // 剥离 PATH 使 gh 必然 ENOENT：请求走异步 catch 路径，同时覆盖错误负载端到端
  const child = spawn(process.execPath, [serverPath], {
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env, PATH: '' },
  })
  const lines = []
  child.stdout.setEncoding('utf8')
  child.stdout.on('data', (chunk) => lines.push(...chunk.split('\n').filter(Boolean)))
  child.stdin.write(`${JSON.stringify(msg(1, 'initialize', { protocolVersion: '2025-06-18' }))}\n`)
  child.stdin.write(`${JSON.stringify(msg(2, 'resources/read', { uri: 'ui://flow-deck/issues.json' }))}\n`)
  child.stdin.end() // 立即关流：EOF 先于 gh ENOENT 的异步处理到达
  const [exitCode] = await once(child, 'exit')
  assert.equal(exitCode, 0)
  const byId = Object.fromEntries(lines.map((line) => JSON.parse(line)).map((r) => [r.id, r]))
  assert.equal(byId[1].result.serverInfo.name, 'flow-deck-issues')
  const payload = JSON.parse(byId[2].result.contents[0].text)
  assert.equal(payload.error, 'gh_failed')
  assert.match(payload.message, /gh 命令不可用/)
})
