# Profile、Bundle 与 Patch：组合机制与定制配方

> 精编自官方 `apps/cli/README.md`、`apps/cli/reference/README.md`、`packages/bundle/base/README.md`、`docs/user/develop/basic/publish.md`（v0.2.2-rc.3）。

## 两个概念、两份清单

| 概念 | 回答的问题 | 清单位置 |
|------|-----------|---------|
| **Bundle** | 这个包**贡献**什么配置层？ | package.json → `"dsh": { "bundle": { "patch": "./cordis.patch.yml" } }` |
| **Profile** | 哪些 bundle 按什么顺序**组合**这套设置？ | `$DSH_HOME/profiles/<name>/package.json` → `"dsh": { "profile": { "bundles": [...] } }` |

bundle 是作者发布的东西；profile 是用户 `dsh --profile <name>` 启动的东西。一个包不会两者都是。

profile 目录两文件：`package.json`（out-of-tree 依赖 + `dsh.profile` 有序 bundles 清单）+ `cordis.patch.yml`（用户自己的 patch 层）。**手写不必**：模板初始化与 `dsh plugin` 自动维护。

## 四层组合顺序（后层按行覆盖前层）

```text
1. dsh.profile.bundles 清单中每个 bundle 的 patch，依清单顺序（dsh-base 恒为首层）
2. profile 自己的 cordis.patch.yml
3. home 级 $DSH_HOME/cordis.patch.yml   ← 机器级偏好，高于每个 profile
4. --patch <path> 覆盖层，按 argv 顺序
```

- 覆盖 = 按 `id` 定位行并**替换该行完整 config**（不深合并）：想改一个键必须复述该行需要的所有键。
- patch 也可 `insert` 插入新行。
- 内置 bundle（`@deepseek-ai/dsh-base` 等）永远从 dsh 安装本身解析；out-of-tree 包由 profile 目录里的 pnpm 管理。
- 应用参数不是第五层——通过普通 app-owned 服务解析（`cmdlineArgs`），详见官方 CLI reference。

## 检视组合结果

```sh
dsh --profile web --dump-config          # 完整树 + 每行来源注释
dsh --profile web --dump-default-config  # 只有 bundle 层
dsh --profile web --dump-config-schema   # JSON Schema 形式
```

打印的每一行都可以被你自己的 patch 替换；unmatched patch target 会在 stderr 报告。dump 会初始化缺失的 profile 文件，但从不运行 app 命令行 provider（携带 app 参数的 dump 会被拒绝）。

## HMR（配置热重载）

YAML 控制：`dsh-base` 启用 config-only `dsh-hmr`（watch profile 清单与两级 patch，序列化单次重载）；`headless`/`sdk`/`acp` 默认关闭；`sdk-minimal` 不含。profile patch 可覆盖默认。没开 HMR 的改动要重启进程生效。插件源码热替换（编辑源文件触发卸载→重载→新 `apply`）同样由 `dsh-hmr` 承载。

## 最小自定义 profile

```json
{
  "name": "my-profile",
  "private": true,
  "dsh": { "profile": { "bundles": ["@deepseek-ai/dsh-base"] } }
}
```

放到 `$DSH_HOME/profiles/my-profile/package.json`，然后 `dsh my-profile "任务"` 即得一个带模型连接、全工具集、持久会话、默认权限策略的可用 Agent。追加 bundle：

```sh
dsh plugin --profile my-profile add <package>
```

## 常用定制配方

配方都走「在 profile/home patch 里写一行覆盖」。注意整行替换语义。

### opt-in `str_replace_editor`（base-backed profile）

```yaml
- insert:
    - id: tool-str-replace-editor
      name: '@deepseek-ai/dsh-tool-str-replace-editor'
      config:
        maxOutputChars: 16000
```

### 开启 Team mode（协作子代理 + 共享任务板）

```yaml
- id: agent-team
  config:
    defaultEnabled: true
    # 覆盖整行：原本自定义的 maxTasks 等要一并复述
```

Team 模式默认按根会话关闭；开启后根会话的协作工具树生效，子代理共享模式。`sdk-minimal` 不含 Teams，需用标准 `sdk` profile。

### 启用子代理中断工具

```yaml
- id: tool-subagent-control
  config:
    interrupt: true   # base 默认 false；普通子代理与 Teams 将获得 interrupt_agent
```

### 切换 shell 栈（Windows 用 bash）

`dsh-base` 按 platform 门控：macOS/Linux 装 bash 栈，Windows 装 PowerShell 孪生栈（每机恰好一套）。想换栈必须**同时**禁用两条现役行、启用两条目标行，否则 profile 加载失败（`ctx.fs` 双注册等会拒载）。

### 收紧文件写入

保持沙箱化 filesystem provider 为**唯一**文件写路径；在其上再叠普通 filesystem provider 会让 profile 拒载。

## 凭据与环境

- 凭据解析顺序：继承环境 → `$DSH_HOME/.credentials.yaml` → 调用目录 `.env` → `$DSH_HOME/.env`；托管凭据文档不会物化进 `process.env`。
- 两个 `.env` 是普通启动环境层；`DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` 常用。
- 会话日志上传（DeepSeek session-log contributor）默认开启，`session-log-deepseek.enabled: false` 可关；OTel 上传默认 `FEEDBACK_ONLY`（仅反馈事件带上下文），`DISABLED` 完全关闭捕获。

## 版本兼容

安装与启动都会校验 bundle 的 `engines.dsh` SemVer 范围（未声明则查 `@deepseek-ai/dsh*` peer 依赖）对照 `dsh --version`。不兼容插件拒绝加载；确需跳过可用显式逐版本豁免（`version-exemptions` / `allow-version` / `revoke-version`），风险自担。
