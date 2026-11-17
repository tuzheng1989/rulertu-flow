# LLM 适配器：接入新的模型 Provider

> 精编自官方 `docs/user/develop/practice/llm-adapter.md`（v0.2.2-rc.3）。适用场景：接入**全新协议**的模型 API；OpenAI 兼容网关不用写代码，走 [[models.md]] 的自定义 provider 配置即可。

## 概览

LLM adapter 继承 `LlmAdapter`（`@deepseek-ai/dsh-llm`）并实现 `stream()`：把 dsh 的 provider 无关请求翻译成 provider API 调用，把响应翻译回 dsh chunk。

## 最小实现

```ts
import type { Context } from '@deepseek-ai/cordis'
import Schema from '@deepseek-ai/schemastery'
import { LlmAdapter, type GenerateOptions, type StreamChunk } from '@deepseek-ai/dsh-llm'

class MyAdapter extends LlmAdapter {
  constructor(private readonly apiKey: string) { super() }

  async *stream(options: GenerateOptions): AsyncIterable<StreamChunk> {
    // 1. options.messages 转成 provider 格式
    // 2. 调 provider 流式 API
    // 3. 响应转成 StreamChunk 序列
  }
}

export interface Config { apiKey: string; providers: string[] }
export const Config: Schema<Config> = Schema.object({
  apiKey: Schema.string().required(),
  providers: Schema.array(Schema.string()).required(),
})

export const name = 'my-llm-adapter'
export const inject = ['llm']

export function apply(ctx: Context, config: Config) {
  const adapter = new MyAdapter(config.apiKey)
  ctx.llm.registerAdapter(config.providers, adapter)
}
```

## StreamChunk 协议

```ts
import { brandString } from '@deepseek-ai/dsh-brand'
import type { StreamChunk, ToolCallId } from '@deepseek-ai/dsh-llm'

async function* exampleChunks(): AsyncIterable<StreamChunk> {
  yield { type: 'block-start', index: 0, blockType: 'text' }          // 1. 每个内容块以 block-start 开
  yield { type: 'text-delta', index: 0, text: 'Hello' }               // 2. 文本经 text-delta 流出
  yield { type: 'text-delta', index: 0, text: ' world' }
  yield { type: 'block-end', index: 0, block: { type: 'text', text: 'Hello world' } }  // 3. 以 block-end 收（含完整块）

  yield { type: 'block-start', index: 1, blockType: 'tool-call' }     // 4. 工具调用块
  yield { type: 'tool-call-delta', index: 1, id: brandString<ToolCallId>('call-123'),
          name: 'bash', argumentsDelta: '{"command":"ls"}' }          //    原始 JSON 文本可一次或多次给
  yield { type: 'block-end', index: 1, block: {
          type: 'tool-call', id: brandString<ToolCallId>('call-123'),
          name: 'bash', arguments: '{"command":"ls"}' } }

  yield { type: 'usage', usage: { inputTokens: 100, outputTokens: 50 } }  // 5. usage 在 finish 前
  yield { type: 'finish', reason: { kind: 'stop' } }                  // 6. finish 是最后一个 chunk
  // 请求工具执行改用 { kind: 'tool-calls' }
}
```

硬规则：每个 `block-start` 配对 `block-end`；`index` 从 0 递增标示块序；`finish` 收尾；`usage` 先于 `finish`。

## GenerateOptions 与模型解析

`stream()` 收 `GenerateOptions`：模型、适配器自有的 reasoning-effort id、对话历史、系统提示、工具 schema、生成参数、stop 序列、abort signal。以 `@deepseek-ai/dsh-llm` 导出的 TS 类型为准；provider 不支持的字段**抛 `LlmError`（带稳定 code）**，不许静默丢弃。

覆写 `resolveModel(provider, model, signal?)` 一次查询返回精确 provider/model 身份 + 可选 `context` / `reasoning` 元数据；reasoning 元数据含有序不透明 id、显示名与可选配置默认；保留适配器权威可选列表（上游能力 API 返回 `off` 就保留 `off`），不要把值提升成核心枚举。省略 `reasoning` = 该模型无可选推理档位能力。服务在 `stream()` 前校验聚合并拒绝不支持的显式档位。signal 用于异步查询的取消。

## 注册与接线

```ts
ctx.llm.registerAdapter(['my-provider'], adapter)   // 首参 = 该适配器接管的 provider 路由
```

`GenerateOptions.provider` 选适配器，`GenerateOptions.model` 直接传适配器自有模型 id（无需生命周期注册）。适配器能向选择器广告模型列表则覆写 `listModels()`。

cordis.yml 接线（agent-loop 行指向 provider/model）：

```yaml
- id: my-llm
  name: './src/my-llm-adapter.ts'
  config:
    apiKey: !!js process.env.MY_API_KEY
    providers:
      - my-provider

- id: agent-loop
  name: '@deepseek-ai/dsh-agent-loop'
  config:
    agents:
      - id: main
        provider: my-provider
        model: my-model-v1
```

## 错误处理与 HTTP 纪律

- 传输/协议失败抛 `LlmError`，稳定 code。`new LlmError` 只接受 `LLM_FAILURE_CODES` 内置码；适配器自有 code 走 `LlmError.fromFailure`。agent loop 保留错误与 code 用于诊断与策略，**不会**自动把普通 `Error` 转换。
- 每个 provider HTTP 请求必须合并 `attributionHeaders()` 并转发 `options.signal`。

```ts
import { attributionHeaders, LlmAdapter, LlmError, type GenerateOptions, type StreamChunk } from '@deepseek-ai/dsh-llm'

class HttpAdapter extends LlmAdapter {
  constructor(private readonly endpoint: string) { super() }
  async *stream(options: GenerateOptions): AsyncIterable<StreamChunk> {
    const response = await fetch(this.endpoint, {
      method: 'POST',
      headers: { 'content-type': 'application/json', ...attributionHeaders() },
      body: JSON.stringify({ model: options.model, messages: options.messages }),
      ...options.signal ? { signal: options.signal } : {},
    })
    if (!response.ok) {
      throw LlmError.fromFailure({
        message: `Provider API error: ${response.status}`,
        code: 'PROVIDER_HTTP_ERROR',
        status: response.status,
      })
    }
    // 解析响应，产出完整 chunk 序列……
    yield { type: 'finish', reason: { kind: 'stop' } }
  }
}
```

## 参考实现

仓库内两个完整实现对照阅读，同一契约两种 provider SDK：

- `packages/llm/llm-deepseek/` — DeepSeek Messages API
- `packages/llm/llm-pi-ai/` — 另一种 API 形态（多协议目录、compat 开关、模型发现在此实现）

配套 cookbook：`docs/cookbook/adding-an-llm-adapter.md`。
