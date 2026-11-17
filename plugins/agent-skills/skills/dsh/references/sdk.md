# SDK：用 TypeScript / Python 驱动 dsh runtime

> 精编自官方 `packages/sdk/client/README.md`、`docs/user/guide/python-sdk.md`、`python/sdk/`（v0.2.2-rc.3）。SDK = 从另一个进程经**换行分隔 JSON-RPC（stdio）**驱动完整 dsh runtime；TS 与 Python 是同一协议的双实现。SDK 不创建"开发者项目"，profile + patch 即应用配置。

## 选型

| 需求 | 路径 |
|------|------|
| 一次性任务，脚本编排 | `dsh headless "任务"`（无需 SDK） |
| Python 应用内嵌入 | Python SDK `deepseek-harness-sdk` |
| TypeScript/Node 应用内嵌入 | TS SDK `@deepseek-ai/dsh-sdk-client` |
| 其他语言 / 自定义客户端 | 直接讲 JSON-RPC 协议（`packages/sdk/protocol/`），自启 `dsh --profile sdk` |
| 给浏览器用户完整 UI | 不用 SDK，跑 `dsh web` |

## TypeScript SDK

安装 `@deepseek-ai/dsh-sdk-client`；未显式给 `dshBin` 时解析同版本 `@deepseek-ai/dsh` 可执行文件。基本用法：

```ts
import { DeepSeekHarness } from '@deepseek-ai/dsh-sdk-client'
import { brandString } from '@deepseek-ai/dsh-brand'
import type { ReasoningEffortId } from '@deepseek-ai/dsh-llm/types'

await using harness = new DeepSeekHarness({
  profile: 'sdk',
  dshHome: '/absolute/path/to/dsh-home',   // 显式 home，避免误读默认
  patches: ['./automation.cordis.yml'],     // 可选：按序叠加 patch
  provider: 'deepseek-official',
  model: 'deepseek-v4-flash',
  reasoningEffort: brandString<ReasoningEffortId>('max'),
  maxTokens: 49_152,                        // 根 Agent 每请求输出上限，in-process 后代继承
})
const result = await harness.run('say hi')
console.log(result.finalResponse)
```

要点：

- 子进程**惰性启动**，实例持有跨 `run()` 复用；`close()` 或 `await using` 确保回收子进程。
- `start()` 走有界 `initialize` 握手（携带 cwd、provider/model 路由、可选 reasoningEffort、可选 maxTokens）；服务端校验精确路由后才会接受 prompt。`initializeTimeoutMs` 默认 10 秒。
- `run(input, { sessionId?, onNotification? })` 接受文本或 `SdkPromptContentBlock[]`（内联 raster 块 = base64 + mimeType，成为持久附件）。返回 `RunResult { sessionId, finalResponse, finishReason, events, notifications }`；`finalResponse` 是该区间最后提交的根会话助手文本（不是因果归因于该 prompt 的响应——steering、注入上下文等其他排队工作可能先行贡献）。
- `harness.session(id?)` 开命名/新会话句柄；`session.run()` 同样收文本或块数组，也支持斜杠命令（`/compact`、`/plan` 等）；无法识别的输入按普通 prompt 原序处理。
- `resumeSession(savedId)` 恢复持久会话（保留历史与目录、修复被打断的末回合、不发新输入）；复用原 home 与 workspace。缺失/不可读/不兼容/被占用都拒绝且不造替代会话。外部进程（shell、浏览器）不在恢复范围。
- `getWorkingDirectory()` / `setWorkingDirectory(path)` 读改生效目录（相对路径基于会话当前目录）。

### 客户端接管审批

```ts
await using harness = new DeepSeekHarness({
  dshHome: '/absolute/path/to/isolated-dsh-home',
  approvalRequests: true,
})
harness.client.start()
harness.client.onRequest(async (method, params) => {
  if (method !== 'approval/request') throw new Error(`Unsupported request: ${method}`)
  return { outcome: 'allowed-once' }   // 'allowed-once' | 'rejected' | 'cancelled'
})
console.log((await harness.run('List the installed plugins.')).finalResponse)
```

启用 `approvalRequests: true` 而没装 handler → unknown-request 错误且审批**关死**。被拒 handler 返回 JSON-RPC 错误，runtime 把该审批判为关闭。

### 原生用户提问（ask_user_question）

传 `onUserQuestion` 回调：收 `{ requestId, sessionId, questions }` 与 `{ signal }`，返回 `{ answers: [{ id, selected, custom? }] }` 或 `{ cancelled: true }`。计划评审（`exit_plan_mode` 的 plan 在 question detail 里）同走此通道；计划评审被取消则本机回合结束、计划模式保持。回调抛错 = provider 错误；缺失/畸形答案**绝不算批准**。

### 低层 HarnessClient

`run()` 之下的协议客户端：显式 `start()` / `initialize()` / `prompt()` / `request()` / `close()` + 通知订阅。

- `prompt()` 只入队即返回消息 id，不等活动。
- `subscribe(filter?)` 返回可 await 的 `NotificationSubscription`（`next()` / `tryNext()` / 异步迭代）；`subscribeSessionTree(id)` 客户端侧过滤一个会话树（沿 `subagent.started` 血缘）。
- 任务型消费者：先订阅，`request('session/wait', { sessionId })` 等托管后代与根总结回合，`tryNext()` 排空队列。
- 类型化错误：`JsonRpcResponseError` / `RequestTimeoutError` / `SdkProtocolError` / `TransportClosedError`（消息含退出码与有界 stderr 尾）。
- `close()` = 协议 shutdown（默认 1s 上界）→ stdin EOF → SIGTERM → SIGKILL 阶梯直到进程退出；幂等；关后拒复用。`HarnessClientOptions.env` 整体替换子进程环境；凭据策略归调用方（`scrubbedParentEnv` 是隔离派生的共享擦洗基底）。

Node 部署做包管理操作（plugin 安装）需要可用 pnpm；Python runtime wheel 可显式下载自带 Node/pnpm。

## Python SDK

```sh
python -m pip install deepseek-harness-sdk   # 需 Python ≥ 3.10；自带 runtime wheel 与 dsh 命令
```

最小示例（`python/sdk/examples/minimal.py`）与库内用法：

```python
from pathlib import Path
from deepseek_harness import DeepSeekHarness

workspace = Path("/absolute/path/to/disposable-workspace").resolve()
dsh_home = Path("/absolute/path/to/example-dsh-home").resolve()
with DeepSeekHarness(
    provider="deepseek-official",
    model="deepseek-v4-flash",
    max_tokens=49_152,
    cwd=str(workspace),
    dsh_home=str(dsh_home),          # SDK 从不静默读 ~/.dsh
    profile="sdk-minimal",
) as harness:
    result = harness.run(
        "Inspect the repository and fix the failing tests.",
        session_id="example-001",
    )
print(result.final_response)
```

- 子进程惰性启动，context-manager 退出前复用。profile、其持久 patch、home patch、`patches` 元组构成应用配置；没有"完整 Cordis 树"入口——Python 只暴露 profile 选择与有序 patch 文件。
- 持久插件：`dsh plugin --profile sdk-minimal add <包>`（初始化 profile 后；此管理命令需装 pnpm，启动运行时不需要）。
- 每-launch patch：`patches=("/absolute/path/to/editor.patch.yml",)`；持久 patch：编辑 `$DSH_HOME/profiles/sdk-minimal/cordis.patch.yml`。
- opt-in `str_replace_editor` patch：

```yaml
- insert:
    - id: tool-str-replace-editor
      name: '@deepseek-ai/dsh-tool-str-replace-editor'
```

- Team mode：用标准 `sdk` profile（`sdk-minimal` 无子代理/Teams 服务），patch `- { id: agent-team, config: { defaultEnabled: true } }` 经 `patches` 传入；注意整行替换语义（自定义 `maxTasks` 一并复述）。

### `sdk-minimal` profile 行为表

| 属性 | 值 |
|------|-----|
| 系统提示 | `DSH_SYSTEM_PROMPT`，回退 "You are a helpful software engineer assistant." |
| 模型 | `--model` → `DSH_MODEL` → `deepseek-v4-flash` |
| 模型可见工具 | `bash`（Linux/macOS）或 `pwsh`（Windows）、`read_image`、`working_directory` |
| shell 超时 | 300 秒 |
| 上下文压缩 | 自动（额外模型请求总结旧历史；完整保留 Session 日志） |
| 会话持久化 | 未压缩 JSONL @ `<dsh_home>/sessions` |
| 权限 | 锁定 `danger-full-access`——**务必用一次性目录或容器** |

单一 bundle 自持完整树、不含 `dsh-base`：无文本文件工具、设置、托管凭据、OTel、Web 工具、子代理、本地 instruction 发现。DeepSeek session-log contributor 默认上传（`session-log-deepseek.enabled: false` 关闭）。装好的 wheel 仍含完整 `web` profile——`dsh web` 指向显式 `DSH_HOME` 可在同一部署提供浏览器 UI（web 不能服务 Python SDK 客户端）。

### 隔离纪律

- profile、插件、凭据、设置、会话需要隔离 → 用全新 `dsh_home`。
- 独立工作 → 全新 `session_id`；复用 harness + home + id 仅为了继续同一持久会话。
- 其余 profile 合法性：必须含 `@deepseek-ai/dsh-sdk-app` 或其他 JSON-RPC server 行；缺 server 行、插件未解析、patch 非法 → 启动期失败，**不回退**其他组合。
