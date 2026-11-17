# 工具：defineTool DSL 与内置工具目录

> 精编自官方 `docs/user/develop/basic/tool.md`、`docs/tool-catalog.md`、`docs/cookbook/adding-a-tool.md` 索引（v0.2.2-rc.3）。

## 写一个工具插件

`defineTool` 从 `@deepseek-ai/dsh-tools` 导入。完整最小示例（greet 工具）：

```ts
import type { Context } from '@deepseek-ai/cordis'
import { defineTool } from '@deepseek-ai/dsh-tools'

export const name = 'greet-tool'
export const inject = ['tools']

export function apply(ctx: Context) {
  ctx.tools.register(defineTool({
    name: 'greet',
    description: 'Greet someone by name.',
    parameters: {
      name: { type: 'string', required: true, description: 'The name to greet' },
    },
    output: {
      schema: { type: 'string' },
      render: (_args, value) => [{ type: 'text', text: value }],
    },
    async execute(args) {
      return `Hello, ${args.name}!`
    },
  }))
}
```

要点：

- `inject = ['tools']` 让 Cordis 等工具注册表就绪。
- `defineTool` 从 `parameters` **推断并校验** `args`。
- `execute` 返回 `output.schema` 声明的规范值；`output.render` 把规范值转成模型可见内容。
- 注册即工具 schema 加入 prompt 组装；卸载即回退。

运行验证：`pnpm dsh web --patch ./scratch-plugin/cordis.yml` → 打开 Web UI → 问「Use the greet tool to greet Ada.」

进阶能力（嵌套 schema、后台工作、策略钩子、PTC 模式、UI 卡片）查官方 `docs/cookbook/adding-a-tool.md`。

## 内置工具目录（tool-catalog 摘要）

按包归组；完整 schema 查生成文档 `docs/tool-catalog.md`。

| 包 | 工具 | 说明 |
|----|------|------|
| `dsh-tool-fs` | `read` `write` `edit` `read_image` `apply_patch` | 默认文件编辑集（base 装配） |
| `dsh-tool-fs-search` | `glob` `grep` | 文件搜索 |
| `dsh-tool-str-replace-editor` | `str_replace_editor` | 显式 opt-in 的编辑器 |
| `dsh-tool-bash` / `dsh-tool-bash-persistent` | `bash` | shell（macOS/Linux；persistent 为持久会话版） |
| `dsh-tool-pwsh` / `dsh-tool-pwsh-persistent` | `pwsh` | Windows PowerShell 孪生栈 |
| `dsh-tool-terminal` | `terminal_open/read/send/close/list/signal` | 持久终端 |
| `dsh-tool-executor-ptc` | `run_code` | PTC（programmatic tool calling）模式：模型写代码编排工具调用 |
| `dsh-tool-ask-user` | `ask_user_question` | 向用户提问（SDK 经 `onUserQuestion` 回调应答） |
| `dsh-plan-mode` | `exit_plan_mode` | 计划模式出口 |
| `dsh-action-cards` | `propose_action` | 交互式行动卡片 |
| `dsh-plugin-manager` | `plugin_manager` | 安装/管理 bundle（Creator 模式） |
| `dsh-tool-cordis` | `cordis_inspect_list/query` | 只读运行时检视 |
| `dsh-mcp-resources` | `list_mcp_resources(_templates)` `read_mcp_resource` | MCP 资源读取（装了 MCP 客户端才有） |
| 浏览器 | `stagehand_*`（act/extract/navigate/observe/screenshot/tabs） | browser-use 实验线 |
| `dsh-tool-office` | `office_convert/recalculate/render` | Office 文档处理 |
| `dsh-tool-present` | `present` | 演示产出 |

`dsh-base` 开箱即含：文件编辑、shell、web 搜索、HTTP(S) fetch、子代理（`subagent` / `subagent_fork` + `send_message` 操控）、任务与目标跟踪、`working_directory`、MCP 资源挂载（配置了 MCP 客户端才有工具）。

## 工具消费的执行管线

工具调用流经守卫管线：`tools/pre-execute → tools/execute → tools/post-execute`（waterfall，监听器必须 `next()`）。策略（审批、沙箱、记录）挂在这三个事件上，不侵入工具本体。`ctx.tools.execute()` 收原始批次与并发上限。

## 设计建议（官方 cookbook 精神）

1. 简单能力 = **一个工具插件**即可，别预设拆包。
2. 能力要可替换时才上三角色拆分（Service Definition / Provider / Consumer）——见 [[services-and-events.md]]。
3. 工具结果是模型上下文：保持 `render` 输出紧凑、结构化、可截断。
4. 涉及副作用的工具考虑接审批/沙箱策略而非自带兜圈子。
5. 有 UI 呈现需求的工具（进度、卡片）查 `adding-a-tool.md` 的 UI cards 章节。
