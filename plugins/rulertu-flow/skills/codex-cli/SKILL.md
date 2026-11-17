---
name: codex-cli
description: 直接驱动 Codex CLI 的通用指南：非交互执行（codex exec）、会话保持（thread_id 提取与 exec resume）、指定模型（-m）、思考档（-c model_reasoning_effort）、沙箱分级、profile、结构化输出与会话管理命令。当用户要求让 Codex 执行写任务、指定模型或思考档跑 Codex、续接或管理 Codex 会话、诊断 codex 登录环境，或 codex-consult 只读通道覆盖不了的场景时使用；跨模型第二意见与只读咨询归 codex-consult，方案评审归 plan-iterate。
---

# codex-cli — 直接驱动 Codex CLI

在 ZCode 会话里把任务直接交给本机 Codex CLI 非交互执行，或管理其会话与环境。全部命令按本机 **codex 0.169.0**（npm 全局 `@openai/codex`，Git Bash PATH 可用）实测校准；仓库 CI 锁定 0.150.1，旗标以 `codex exec --help` 实时输出为准。

## 分工（先读）

| 需求 | 归属 |
|---|---|
| 跨模型第二意见、只读咨询、implement-plan T3 独立意见 | `codex-consult`（脚本封装、退出码协议、产物自动落盘） |
| 方案文档评审迭代 | `plan-iterate`（评审 schema 与轮次状态机） |
| 写任务、指定模型/思考档、会话管理、profile/登录诊断等直接驱动 | 本技能 |

只读问询优先 `codex-consult`——它有协议化退出码与产物落盘；本技能面向封装通道不覆盖的场景。

## 授权与安全

- 用户点名 Codex/GPT 时直接跑；agent 自发外调（如想拿第二意见）先说明意图，征得同意再跑。
- `codex exec` 会把 prompt 与所指向目录的内容发往 OpenAI 服务端并消耗 Codex 账号配额；涉密内容不外调。
- 沙箱默认 `read-only`；`workspace-write` 仅在用户明确要求改动时使用，并说清可写范围（可 `--add-dir <DIR>` 追加可写目录）。`danger-full-access` 与 `--dangerously-bypass-approvals-and-sandbox` 禁用。
- 模型不可用时阻断并报告，不静默换模型。

## 前置检查

```bash
codex --version      # 确认在 PATH
codex login status   # Logged in using ChatGPT 才可用；未登录 → codex login
```

Windows 下 Git Bash 直接跑 `codex` 即可（npm 全局装）；Python 无 shell 调用需把 `codex.cmd` 解析为 `node .../node_modules/@openai/codex/bin/codex.js`——插件已有实现：`<插件根>/scripts/codex_exec.py` 的 `resolve_cli`。

## 非交互执行骨架

```bash
codex exec -s read-only -C <目标目录> --json -o <last.md> "<任务指令>" > <events.jsonl> 2> <stderr.log>
```

- 事件流与最终回复**都落文件**，不要让 JSONL 刷进对话上下文；给用户看 `-o` 文件内容即可。
- `-s`：`read-only` / `workspace-write` / `danger-full-access`（禁用）。
- `-C` 工作根目录；目录不是 git 仓库时加 `--skip-git-repo-check`。
- 长指令防转义走 stdin：`cat <task.txt> | codex exec - ...`。
- 需要结构化输出：`--output-schema <schema.json>` 约束最终回复形状。
- 其他常用：`-i/--image <FILE>` 附图、`--ephemeral` 不落会话文件、`--trust` 保存目录信任、`-p <profile>` 叠层 `$CODEX_HOME/<name>.config.toml`（如 `-p glm` 切配置组）。

## 保持会话

1. 首轮运行后从事件流取会话 id——首个 `thread.started` 事件的 `thread_id`：
   ```bash
   grep '"thread.started"' <events.jsonl> | head -1
   ```
2. 续接（继承原会话上下文）：
   ```bash
   codex exec resume <session-id> --json -o <last2.md> "<追加指令>" > <events2.jsonl> 2>&1
   ```
   - resume **没有** `-s`/`-C` 旗标：沙箱与工作目录沿用原会话；`-m`、`-c`、`-o`、`--json`、`--ephemeral` 可用。
   - 非 git 且非受信目录下 resume 同样要加 `--skip-git-repo-check`（实测：不带则退出码 1 报 "Not inside a trusted directory"）。
   - `--last` 续最近会话有误续风险，优先显式 id。
3. 会话 id 在对话内记住即可；跨对话续接由调用方自行落盘（遵守仓库目录约定，不写技能目录）。

事件流关键类型：`thread.started`（thread_id）→ `turn.started` → `item.completed`（`agent_message` 为回复正文）→ `turn.completed`（usage 用量）。

会话族命令：`codex exec fork <id> "<prompt>"` 分叉新会话；`codex queue <id> "<msg>"` 排队消息；`codex archive`/`codex delete <id|名称>` 归档清理。`codex resume`/`codex agents` 是交互式选择器，agent 场景不可用。

## 指定模型与思考档

```bash
codex exec -m gpt-5.6-terra ...          # 模型：-m/--model（env MODEL）
codex exec -m gpt-5.6-sol -c model_reasoning_effort=high ...   # 思考档：配置覆盖
```

- 思考档取值 `minimal|low|medium|high|xhigh`，**没有独立 `--effort` 旗**，一律 `-c model_reasoning_effort=<档>`。
- `-c key=value` 值按 TOML 解析、解析失败回退原始字符串，裸词（如 `high`）直接可用。
- 本机常用模型：`gpt-5.6-terra`（执行）、`gpt-5.6-sol`（评审/裁决），与 implement-plan 角色路由同源。

## 场景速查

| 场景 | 命令骨架 |
|---|---|
| 只读问询/第二意见 | 走 `codex-consult`，不直接 exec |
| 写任务 | `codex exec -s workspace-write -C <目录> --json -o <out> "<任务>"` |
| 续会话 | `codex exec resume <id> --json -o <out2> "<追加>"` |
| 指定模型+思考档 | `codex exec -m <model> -c model_reasoning_effort=<档> ...` |
| 结构化输出 | `codex exec --output-schema <schema.json> --json -o <out> ...` |
| 一次性不留痕 | 加 `--ephemeral` |
| 切配置组 | `-p <profile>`（profile 文件在 `$CODEX_HOME/`） |
| 诊断 | `codex doctor`（安装/配置/auth/运行时健康） |

## 重要纠错（勿再踩）

- 排队消息的顶层命令是 **`codex queue`**，不是 `codex send`。
- 思考档没有 `--effort` 旗；写 `--effort high` 会报未知参数。
- `codex resume` 是交互式选择器，不能在非交互 shell 里当续会话用；非交互续会话只有 `codex exec resume`。
- 仓库外目录（含 resume）都要 `--skip-git-repo-check`，报错文案是 "Not inside a trusted directory"。

## 环境前提

Windows 11 + Git Bash；`codex` 在 PATH（npm 全局 `%APPDATA%\npm`）；已 `codex login`（ChatGPT 或 `CODEX_API_KEY`）。
