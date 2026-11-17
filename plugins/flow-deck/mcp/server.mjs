#!/usr/bin/env node
// flow-deck Issues 面板的 stdio MCP server（零依赖，NDJSON over stdin/stdout）。
// 机制依据：ZCode 插件面板 ui.surfaces——manifest 里 surface.server 指向本 server，
// 面板 HTML 经 resources/read 以 ui://flow-deck/panel.html 供给（mimeType 必须
// text/html;profile=mcp-app）。协议范式对照官方 zcode-site 0.5.0 dist/server.mjs。
// 数据源：gh issue list（解析校验移植自 hooks/parse.ts parseGhIssues），
// 60s TTL 缓存对齐原版 GH_ISSUE_POLL_MS 轮询节奏；宿主不轮询，面板打开/点刷新时拉取。

import { execFile } from 'node:child_process'
import { readFile } from 'node:fs/promises'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { dirname, join, resolve } from 'node:path'
import { once } from 'node:events'

const PANEL_URI = 'ui://flow-deck/panel.html'
const ISSUES_URI = 'ui://flow-deck/issues.json'
const PANEL_MIME = 'text/html;profile=mcp-app'
const ISSUES_MIME = 'application/json'
const GH_TIMEOUT_MS = 5000 // 对齐原版 GIT_TIMEOUT_MS（hooks/register.tsx:62）
const CACHE_TTL_MS = 60_000 // 对齐原版 GH_ISSUE_POLL_MS（hooks/register.tsx:66）
const GH_ARGS = ['issue', 'list', '--state', 'open', '--limit', '20', '--json', 'number,title,url,labels']
const MCP_ROOT_DIR = join(dirname(fileURLToPath(import.meta.url)), '..')

/** 一条 GitHub open issue（gh issue list --json number,title,url,labels 的字段子集） */
export function parseGhIssues(stdout) {
  let data
  try {
    data = JSON.parse(stdout)
  } catch {
    return null
  }
  if (!Array.isArray(data)) return null
  const issues = []
  for (const item of data) {
    if (typeof item !== 'object' || item === null) continue
    if (typeof item.number !== 'number' || typeof item.title !== 'string' ||
        typeof item.url !== 'string') continue
    const labels = Array.isArray(item.labels)
      ? item.labels
        .map((label) => (typeof label === 'object' && label !== null ? label.name : undefined))
        .filter((name) => typeof name === 'string')
      : []
    issues.push({ number: item.number, title: item.title, url: item.url, labels })
  }
  return issues
}

/** gh 执行器；返回面板数据负载。原版失败静默（register.tsx:1278-1291），面板场景改为携带原因 */
export async function runGh(exec = execFileOrNull) {
  try {
    const { stdout, stderr } = await exec(GH_ARGS)
    const issues = parseGhIssues(stdout)
    if (issues === null) return { error: 'gh_failed', message: 'gh 输出解析失败（非 JSON 数组）' }
    return { issues, fetchedAt: Date.now() }
  } catch (error) {
    return { error: 'gh_failed', message: describeGhError(error) }
  }
}

function describeGhError(error) {
  if (error?.code === 'ENOENT') return 'gh 命令不可用（未安装或不在 PATH）'
  const stderr = typeof error?.stderr === 'string' ? error.stderr.trim() : ''
  if (stderr) return `gh 调用失败：${stderr.split('\n')[0].slice(0, 200)}`
  if (error?.killed || error?.signal) return `gh 调用超时（>${GH_TIMEOUT_MS}ms）`
  return `gh 调用失败：${String(error?.message ?? error)}`
}

function execFileOrNull(args) {
  return new Promise((resolve, reject) => {
    execFile('gh', args, { timeout: GH_TIMEOUT_MS, windowsHide: true }, (error, stdout, stderr) => {
      if (error) {
        error.stderr = stderr
        reject(error)
      } else {
        resolve({ stdout, stderr })
      }
    })
  })
}

/** TTL 缓存容器：新鲜（<60s）直接回缓存，否则跑 gh；force 用于面板刷新按钮 */
export function createIssueStore(run = runGh, now = Date.now) {
  let cache = null
  return {
    async read(force = false) {
      if (!force && cache !== null && now() - cache.at < CACHE_TTL_MS) return cache.payload
      const payload = await run()
      cache = { at: now(), payload }
      return payload
    },
  }
}

/** MCP 方法路由：消息对象进、响应对象出（notification 返回 null）。deps 注入便于测试 */
export async function handleMessage(message, { store = createIssueStore(), panelPath = join(MCP_ROOT_DIR, 'mcp', 'panel.html'), serverInfo } = {}) {
  if (message === null || typeof message !== 'object' || message.jsonrpc !== '2.0') {
    return { jsonrpc: '2.0', id: null, error: { code: -32600, message: 'Invalid Request' } }
  }
  const { id, method, params } = message
  const isNotification = id === undefined || id === null
  const reply = (result) => (isNotification ? null : { jsonrpc: '2.0', id, result })
  const fail = (code, messageText) =>
    isNotification ? null : { jsonrpc: '2.0', id, error: { code, message: messageText } }

  switch (method) {
    case 'initialize':
      return reply({
        protocolVersion: typeof params?.protocolVersion === 'string' ? params.protocolVersion : '2025-06-18',
        capabilities: { resources: {}, tools: {} },
        serverInfo: serverInfo ?? { name: 'flow-deck-issues', version: '0.0.0' },
      })
    case 'notifications/initialized':
    case 'notifications/cancelled':
      return null
    case 'ping':
      return reply({})
    case 'tools/list':
      return reply({
        tools: [{
          name: 'refresh_issues',
          title: '刷新 GitHub Issues',
          description: '强制重新拉取当前仓库的 GitHub open issues（忽略 60s 缓存）',
          inputSchema: { type: 'object', properties: {}, additionalProperties: false },
          _meta: { ui: { visibility: ['app'] } }, // 只对面板可见，不进模型工具列表（zcode-site 先例）
        }],
      })
    case 'tools/call': {
      if (params?.name !== 'refresh_issues') return fail(-32602, `Unknown tool: ${params?.name}`)
      const payload = await store.read(true)
      return reply({
        content: [{ type: 'text', text: JSON.stringify(payload) }],
        structuredContent: payload,
        isError: payload.error !== undefined,
      })
    }
    case 'resources/list':
      return reply({
        resources: [
          { uri: PANEL_URI, name: 'flow-deck Issues 面板', mimeType: PANEL_MIME },
          { uri: ISSUES_URI, name: 'GitHub open issues', mimeType: ISSUES_MIME },
        ],
      })
    case 'resources/read': {
      const uri = params?.uri
      if (uri === PANEL_URI) {
        try {
          return reply({ contents: [{ uri, mimeType: PANEL_MIME, text: await readFile(panelPath, 'utf8') }] })
        } catch (error) {
          return fail(-32603, `面板资源读取失败：${String(error?.message ?? error)}`)
        }
      }
      if (uri === ISSUES_URI) {
        const payload = await store.read(false)
        return reply({ contents: [{ uri, mimeType: ISSUES_MIME, text: JSON.stringify(payload) }] })
      }
      return fail(-32602, `Unknown resource: ${uri}`)
    }
    default:
      return fail(-32601, `Method not found: ${method}`)
  }
}

async function readServerInfo() {
  try {
    const manifest = JSON.parse(await readFile(join(MCP_ROOT_DIR, '.claude-plugin', 'plugin.json'), 'utf8'))
    return { name: 'flow-deck-issues', version: manifest.version ?? '0.0.0' }
  } catch {
    return { name: 'flow-deck-issues', version: '0.0.0' }
  }
}

export async function main() {
  const serverInfo = await readServerInfo()
  const store = createIssueStore()
  const write = (message) => process.stdout.write(`${JSON.stringify(message)}\n`)
  let buffer = ''
  let inFlight = 0
  let stdinEnded = false
  const maybeExit = () => { if (stdinEnded && inFlight === 0) process.exit(0) }
  process.stdin.setEncoding('utf8')
  process.stdin.on('data', (chunk) => {
    buffer += chunk
    let index
    while ((index = buffer.indexOf('\n')) !== -1) {
      const line = buffer.slice(0, index).replace(/\r$/, '')
      buffer = buffer.slice(index + 1)
      if (line.trim() === '') continue
      let message = null
      try {
        message = JSON.parse(line)
      } catch {
        write({ jsonrpc: '2.0', id: null, error: { code: -32700, message: 'Parse error' } })
        continue
      }
      inFlight += 1
      handleMessage(message, { store, serverInfo })
        .then((response) => { if (response !== null) write(response) })
        .catch((error) => {
          process.stderr.write(`flow-deck server 处理消息失败：${String(error?.stack ?? error)}\n`)
          if (message.id !== undefined && message.id !== null) {
            write({ jsonrpc: '2.0', id: message.id, error: { code: -32603, message: 'Internal error' } })
          }
        })
        .finally(() => { inFlight -= 1; maybeExit() })
    }
  })
  await once(process.stdin, 'end')
  stdinEnded = true
  maybeExit()
}

// 直接以 node 启动（manifest command:"node"）时自启；被 import 时不执行
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  await main()
}
