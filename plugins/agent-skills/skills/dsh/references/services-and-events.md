# 服务、事件与三角色能力设计

> 精编自官方 `docs/user/develop/framework/service.md`、`events.md`、`docs/user/develop/practice/index.md`、`docs/cordis-primer.md`（v0.2.2-rc.3）。

## 服务与依赖注入

`tools`、`llm`、`agents` 都是服务——挂在 `ctx` 具名键上的能力。任何插件都可以对外提供服务。

**消费服务**：声明 `inject`，`apply` 运行时每个所列服务都已就绪；服务未就绪则插件等待而非报错。

```ts
export const inject = ['tools', 'llm']
export function apply(ctx: Context) { /* ctx.tools、ctx.llm 已就绪 */ }
```

**提供服务**：继承 `Service`，构造时声明服务名，用 declaration merging 给 `ctx` 补类型：

```ts
import { Service, type Context } from '@deepseek-ai/cordis'

declare module '@deepseek-ai/cordis' {
  interface Context {
    metrics: MetricsService
  }
}

export default class MetricsService extends Service {
  static inject = ['llm']            // 服务可依赖其他服务
  constructor(ctx: Context) {
    super(ctx, 'metrics')            // 服务名，消费方经 ctx.metrics 访问
  }
  record(event: string, value: number) { /* 公开服务方法 */ }
}
```

**必需 vs 可选依赖**：`inject` 是必需（服务不在则不加载）；可选依赖省略 inject，用 `ctx.get('metrics')?.` 在使用点查询。

**服务隔离**：`cordis.yml` 可让不同插件组看到同一服务的独立实例——每个组自己的 provider 实例互不越界：

```yaml
- id: group-a
  name: '@deepseek-ai/cordis-plugin-group'
  group: true
  isolate:
    shell: true
  config:
    - name: '@deepseek-ai/dsh-bash-local'
      config: { timeoutMs: 5000 }
    - name: './src/plugin-a.ts'
```

内置服务的完整服务名、公开方法、源码位置由仓库生成到各子系统页（`docs/subsystems/*.md`）——以生成区与 TypeScript 接口为准，不要维护第二份静态清单。

## 事件系统

事件是插件间通信核心，`namespace/action` 命名。监听器经 `ctx.on` 注册，是 effect：插件卸载自动移除。

| 模式 | 派发方法 | 等待 | 顺序 | 返回值 |
|------|---------|------|------|--------|
| `emit` | `ctx.emit` | 否 | 注册序广播，返回值忽略 | 无 |
| `waterfall` | `ctx.waterfall` | 否（异步可用） | 注册序 | 有 |
| `parallel` | — | 是 | 所有监听器并行 | 无 |
| `serial` | `ctx.serial` | 是 | 注册序，await 每个结果 | 有（首个非空值即停） |
| `bail` | `ctx.bail` | 否 | 注册序，到首个 bail 值停 | 有 |

**waterfall = around 中间件**：监听器收 `(...args, next)`，调 `next()` 把（可包装的）结果传给下游；**不调 `next()` 即短路**——这是设计使然，用于拦截与网关行为。协作式监听器通常修改共享请求/决策对象后委托；拥有决策权的策略监听器可以不 `next()` 直接返回。

```ts
// 派发
const output = await ctx.waterfall('my-plugin/transform', input, async () => input)
// 监听：next() 必须调用
ctx.on('my-plugin/transform', async (_input, next) => {
  const downstream = await next()
  return downstream.trim()
})
```

**类型化事件**：

```ts
declare module '@deepseek-ai/cordis' {
  interface Events {
    'my-plugin/ready': (payload: { id: string }) => void
    'my-plugin/transform': (input: string, next: () => Promise<string>) => Promise<string>
  }
}
```

**dsh 事件语义**：`agent/pre-step`、`agent/request`、`llm/stream`、`tools/*` 三事件是 waterfall；`agent/turn-stopping` 是 serial 且无 `next()`。`turn/*`、`step/*`、`tool/call`、`tool/result`、`compaction/*` 是**持久会话事件类型**而非 Cordis 事件——观察它们监听 `session/event` 并检查 `event.type`。

示例：工具日志插件

```ts
import type { Context } from '@deepseek-ai/cordis'
import '@deepseek-ai/dsh-tools'

export const name = 'tool-logger'
export function apply(ctx: Context) {
  ctx.on('tools/result', (exec, result) => {
    console.log(`[tool] ${exec.name}(${JSON.stringify(exec.arguments)})`)
    const text = result.content.map(b => b.type === 'text' ? b.text : '').join('')
    console.log(`[tool result] ${text.slice(0, 100)}`)
  })
}
```

## 三角色能力设计（capability seam）

能力通用到需要可替换实现时（如 Bash 执行），拆三个角色：

- **Service Definition**：定义 Cordis 服务与 Request/Result 类型（例：`dsh-shell`）
- **Service Provider**：实现它（例：`dsh-bash-local`——本机执行）
- **Consumer**：把能力暴露为模型可调工具（例：`dsh-tool-bash`）

```text
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│  dsh-shell   │────▶│  dsh-bash-local  │     │ dsh-tool-bash│
│(definition) │     │    (provider)     │     │(consumer/tool)│
└─────────────┘     └──────────────────┘     └──────────────┘
       ▲                                            │
       └────────────────────────────────────────────┘
                    inject: ['shell']
```

- Provider 与 Consumer **互不依赖**，都只依赖 Definition。
- 换 provider = 换 `cordis.yml` 一行，Definition 与工具不动。
- 一个角色不算 seam；加能力 = 设计全三个角色。

**最小三连**（教程摘录）：

```ts
// 1) Definition：抽象 Service + Request/Result 类型
declare module '@deepseek-ai/cordis' { interface Context { myCap: MyCapService } }
export abstract class MyCapService extends Service {
  constructor(ctx: Context) { super(ctx, 'myCap') }
  abstract execute(request: MyCapRequest): Promise<MyCapResult>
}

// 2) Provider：继承并实现，ctx.plugin 挂载
class MyCapLocal extends MyCapService {
  async execute(request: MyCapRequest) { return { output: request.input.toUpperCase() } }
}
export const name = 'my-cap-local'
export function apply(ctx: Context) { ctx.plugin(MyCapLocal) }

// 3) Consumer：工具经 ctx.myCap 调用
export const name = 'tool-my-cap'
export const inject = ['tools', 'myCap']
export function apply(ctx: Context) {
  ctx.tools.register(defineTool({
    /* ... */
    async execute(args) { return (await ctx.myCap.execute({ input: args.input })).output },
  }))
}
```

组合：`cordis.yml` 两行（provider + consumer）。

**设计守则**：

- **不预先拆包**——角色需要独立演进才拆；简单工具插件不需要。
- **Definition 拥有 Request/Result 类型**。
- **显式优于隐式**——默认值在显式 `resolve(request): Spec` 步骤收拢，不在 `run()` 里散布 `?? default`。
- 接缝（seam）是"换一个 provider 就换掉整个产品行为"的机制：文件系统与子进程 provider 共享一个执行世界，把两者指向远程沙箱，Bash、PTY、LSP 一起迁移，无需 fork provider。子代理 provider 同理（新子 Agent 到另一产品的委派回合）。

## 实务守则（Cordis primer）

- 行为封装进插件：工具管线事件归 `ctx.tools`，模型流归 `ctx.llm`，live Agent 协调归 `ctx.agents`。
- 拦截与策略优先用**事件**；直接能力调用优先用**服务方法**。
- 每个注册都要有析构器：`ctx.effect()` 返回清理函数，或用自带清理的 Cordis helper。卸载顺序敏感 → 相关工作收进同一个 effect。
