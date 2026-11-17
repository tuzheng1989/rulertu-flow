# 安装、启动与 CLI 速查

> 精编自官方 `README.md`、`apps/cli/README.md`、`apps/cli/reference/README.md`、`docs/user/guide/index.md`（v0.2.2-rc.3）。

## 三种安装运行路径

### 路径 1：npm 直接跑（最快）

```sh
npx @deepseek-ai/dsh web
```

默认在 `http://127.0.0.1:3080` 启动 Web UI 并打开浏览器；SSH 环境只打印 host URL；`--no-open` 不开浏览器。需要 Node.js（运行 npm 包），Python SDK 路径除外。

### 路径 2：源码运行

```sh
git clone https://github.com/deepseek-ai/deepseek-harness.git
cd deepseek-harness
pnpm install
pnpm run build
pnpm dsh web
```

开发要求：Node.js ≥ 24.9、Corepack 启用的 pnpm（仓库锁定 `pnpm@11.28.5`）、Git ≥ 2.26。`pnpm run build` 产出制品后 `pnpm dsh web` 直接用制品启动不再重建；`pnpm run dev:web` = 构建 + 启动 + 源码变更时重建客户端 bundle。

### 路径 3：Python SDK（自带运行时，无需系统 Node）

```sh
python -m pip install deepseek-harness-sdk
```

安装包含匹配的原生 runtime wheel 与 `dsh` 命令。详见 [[sdk.md]]。

## 五种内置 Profile

| Profile | 启动命令 | 用途 |
|---------|---------|------|
| `web` | `dsh web` | 浏览器完整 UI（插件管理、设置、会话） |
| `headless` | `dsh headless "任务"` 或 `dsh --profile headless "任务"` | 一次性任务：新建持久会话 → 打印最终答案 → 退出 |
| `sdk` | `dsh sdk` 或 `dsh --profile sdk` | JSON-RPC stdio 服务，供 TS/Python SDK 驱动 |
| `sdk-minimal` | `dsh --profile sdk-minimal` | 独立最小树：无 `dsh-base`、无子代理/Teams，工具仅 shell + `read_image` + `working_directory` |
| `acp` | `dsh --profile acp` | ACP stdio 自动化客户端服务 |

要点：
- 前四种与 `acp` 首次使用时自动从模板初始化到 `$DSH_HOME/profiles/<name>`。
- 自定义 profile：`dsh --profile <name> --from-default-profile <template>` 从模板创建/重置（目标名不能与五个内置名冲突，`desktop` 名保留给 Electron）。
- 调用目录即默认工作区根。

## CLI 命令速查

| 命令 | 作用 |
|------|------|
| `dsh <name>` | `dsh --profile <name>` 的简写；`plugin` 是保留管理命令名 |
| `dsh web [--port 8080] [--no-open]` | 启动 Web profile（`--port` 属于 web 应用） |
| `dsh --profile headless "任务"` | 一次性运行 |
| `dsh plugin --profile <name> <pnpm 参数>` | 管理该 profile 的插件（转发 pnpm；`add`/`remove`/`list`…） |
| `dsh --profile <name> --from-default-profile <模板>` | 用内置模板重建该 profile |
| `dsh --profile <name> --dump-default-config` | 只打印 bundle 层 |
| `dsh --profile <name> --dump-config` | 加上 profile/home patch 与 `--patch` 层；注释标明每行来源 |
| `dsh --profile <name> --dump-config-schema` | 打印组合树的 JSON Schema 而非配置值 |
| `dsh --version` / `dsh --help` | 版本 / 启动器帮助 |

环境变量：`DSH_HOME`（默认 `~/.dsh`）；凭据解析顺序 = 继承环境 → `$DSH_HOME/.credentials.yaml` → 调用目录 `.env` → `$DSH_HOME/.env`。API key 常用 `DEEPSEEK_API_KEY`，可选 `DEEPSEEK_BASE_URL`。

## Web UI 最小上手流程

1. 启动 `dsh web`，打开 `http://127.0.0.1:3080`。
2. **Settings → Models**：填 DeepSeek API key（[platform.deepseek.com](https://platform.deepseek.com/) 申请），保存即生效，无需重启。
3. **Choose workspace**：添加并选中项目目录——未选工作区前会话输入框不可用。
4. 发任务，例如「总结这个仓库并列出主要包」。Agent 可读写工作区文件、跑命令、委派子代理、维护计划；权限策略默认把文件写入限制在工作区内，风险操作先询问。

## 无头验证（CI / 冒烟）

```sh
export DEEPSEEK_API_KEY=sk-...
npx @deepseek-ai/dsh --profile headless "summarize this workspace"
```

输出最终答案后退出；会话持久化在 `$DSH_HOME/profiles/headless` 对应的 home 中。

## 部署提示

- 反向代理发布 Web UI：见官方 `docs/user/guide/public-deployments.md`。
- 网络代理：见 `docs/user/guide/network-proxy.md`。
- 桌面版（Electron）与 npm CLI 共享产品数据但包/激活/锁文件相互独立；`desktop` profile 名保留。

## 故障排查

- 启动失败退出码 1：`$DSH_HOME/logs/`（默认 `~/.dsh/logs/`）下有 `startup-<timestamp>-<uuid>.log` 完整诊断。
- patch 目标行不存在：`--dump-config` 在 stderr 报告 unmatched patch target。
- 插件版本不兼容：`engines.dsh` 范围不满足会在安装与启动时拒绝，可用显式豁免（`version-exemptions` / `allow-version`），需自担风险。
- 配置改动不生效：确认 profile 是否启用 HMR（base 默认启用 config-only HMR；headless/SDK/ACP 默认关闭，改完需重启）。
