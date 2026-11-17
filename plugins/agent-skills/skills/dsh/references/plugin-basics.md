# 插件开发基础：第一个插件、生命周期与配置

> 精编自官方 `docs/user/develop/basic/index.md`、`config.md`、`docs/user/develop/framework/index.md`、`docs/cordis-primer.md`（v0.2.2-rc.3）。

## 插件是什么

dsh 里插件 = 一个导出 `apply` 函数的 TypeScript 模块。框架加载插件时调用 `apply`，传入 `ctx` 上下文对象，插件经它在共享上下文上注册能力：

```ts
import type { Context } from '@deepseek-ai/cordis'

export const name = 'hello-plugin'

export function apply(ctx: Context) {
  console.log('[hello-plugin] plugin loaded!')
}
```

## 本地加载（--patch overlay）

创建 `scratch-plugin/cordis.yml`（插件路径必须**绝对路径**——patch 只贡献配置，不改变 loader 的解析基目录）：

```yaml
- insert:
    - id: hello
      name: '/absolute/path/to/deepseek-harness/scratch-plugin/src/my-plugin.ts'
```

启动：

```sh
pnpm dsh web --patch ./scratch-plugin/cordis.yml
```

启动日志出现 `[hello-plugin] plugin loaded!` 即成功。声明依赖：

```ts
export const inject = ['tools']   // apply 运行前 ctx.tools 已就绪

export function apply(ctx: Context) {
  ctx.tools.register(/* ... */)
}
```

## 三种插件形式

| 形式 | 写法 | 适用 |
|------|------|------|
| 函数（推荐起步） | `export const name` + `export function apply(ctx)` | 绝大多数场景 |
| 对象 | `export default { name, inject, apply(ctx) }` | 需要 inject 的简单插件 |
| 类 | `export default class X extends Service { static inject = [...]; constructor(ctx) { super(ctx, 'key') } }` | **插件要向别人提供服务**时（见 [[services-and-events.md]]） |

## Fiber 生命周期

每个已加载插件拥有一个 **Fiber** 作用域，状态机：

```text
PENDING → LOADING → ACTIVE
                 ↘ FAILED
ACTIVE → UNLOADING → DISPOSED
```

| 状态 | 含义 |
|------|------|
| PENDING | 已声明，但所需依赖未就绪 |
| LOADING | 依赖就绪，`apply` 执行中 |
| ACTIVE | 运行中 |
| FAILED | `apply` 抛错 |
| UNLOADING | 卸载中，释放资源 |
| DISPOSED | 完全卸载 |

关键行为：

- **依赖驱动**：`inject` 的服务消失（如 provider 被替换）→ 插件自动卸载（ACTIVE → DISPOSED），服务回来时自动重载。
- **自动清理**：经 `ctx` 的一切注册（事件监听、工具、定时器……）在卸载时自动回退，无需手工 removeListener/clearInterval。需要显式清理的资源（网络连接等）用 `ctx.effect()` 提供析构器：

```ts
ctx.effect(() => {
  const timer = setInterval(() => console.log('heartbeat'), 5000)
  return () => clearInterval(timer)   // 卸载时执行
})
```

- **卸载顺序**：析构器按注册逆序调用，但多个异步析构器并发执行、无串行完成保证——顺序敏感的清理放进**同一个** `ctx.effect()` 里串行 await。
- **嵌套上下文**：`ctx.plugin(child)` 创建子 Fiber，继承父上下文、生命周期独立、随父卸载。`const fiber = ctx.plugin(p)` 拿到的句柄可 `await fiber.dispose()` 手动提前停止。
- **HMR 热替换**：`dsh-hmr` 启用时编辑插件源文件 = 卸载旧实例（注册自动清理）→ 加载新代码 → 跑新 `apply`。

## 插件配置（Schemastery）

导出 `Config` **类型** + **同名 Schemastery schema**，默认值直接写在 schema 字段上；`apply` 收第二个参数：

```ts
import type { Context } from '@deepseek-ai/cordis'
import Schema from '@deepseek-ai/schemastery'

export const name = 'my-plugin'

export interface Config {
  greeting: string
  maxRetries: number
  verbose?: boolean
}

export const Config: Schema<Config> = Schema.object({
  greeting: Schema.string().default('Hello'),
  maxRetries: Schema.number().default(3),
  verbose: Schema.boolean().default(false),
})

export function apply(ctx: Context, config: Config) {
  console.log(config.greeting)   // 用户值或 schema 默认
}
```

patch 里供给配置：

```yaml
- insert:
    - id: hello
      name: './src/my-plugin.ts'
      config:
        greeting: 'Hi there'
        maxRetries: 5
```

设计原则：

1. **可调值不许硬编码**——两个部署可能想设不同值的字段必须是配置项。检验标准：`cordis.yml` 能不改代码改值。
2. **非法配置要响亮失败**——自包含约束进 schema（加载期校验并报可行动错误）；需要引用服务/已注册资源的约束走依赖注入。
3. **不要导出普通对象当 `Config`**——它不实现 Cordis 要求的 Standard Schema 接口。
4. **与 HMR 协作**——配置编辑 = 热替换插件：旧实例卸载、新实例加载；注册是 effect 所以不会残留旧注册。

## 下一步

- 加模型可见工具 → [[tools.md]]
- 向外提供服务 / 事件通信 → [[services-and-events.md]]
- 打包安装发布 → [[publishing.md]]
- Cordis 系统学习 → 官方 `docs/cordis-tutorial/`（01-first-plugin → 07-into-the-harness 七篇，无需 API key）
