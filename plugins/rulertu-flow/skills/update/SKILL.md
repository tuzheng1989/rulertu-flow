---
name: update
description: 一键更新本机 Claude Code 工具链的外部组件（所有 marketplaces、已安装 plugins、openwiki、codegraph、open-code-review(ocr)、deepeval）。当用户说"更新 claude code 环境"、"update everything"、"整体更新"、"更新全部插件/插件市场"、"update plugins"、"刷新 codegraph/openwiki/ocr/deepeval"等时触发此技能。即使用户只说"帮我更新一下环境"或"把 claude code 相关的都更新一下"，只要涉及上述组件的升级就用本技能。注意：Claude Code 本体无法在运行中自我更新，已从本技能移除——如需升级本体请退出会话后用 `claude update` 手动处理。
---

# /update — Claude Code 工具链外部组件一键更新

把本机 Claude Code 工具链的 6 类外部组件一次性更新到位，逐项报告「更新前 → 更新后」版本，单步失败不中断整体流程，最后给出汇总表。

> **Claude Code 本体不在此技能范围内**：它无法在运行中自我更新（会话内的进程无法替换自身），放在 skill 里既跑不通也容易误导。如需升级本体，请退出会话后手动 `claude update`。

## 步骤 0：先检测缺失组件，询问后再启动

脚本对**未安装**的 npm/pip 组件（openwiki、codegraph、ocr、deepeval）默认跳过并给出手动安装命令；仅当通过 `UPDATE_INSTALL`（逗号分隔组件名）显式勾选时才会新装。因此启动前先做一步检测：

```bash
npm list -g openwiki @colbymchenry/codegraph @alibaba-group/open-code-review --depth=0 2>/dev/null
python -m pip show deepeval 2>/dev/null | head -2
```

- **无缺失**：直接启动脚本，不传 `UPDATE_INSTALL`。
- **有缺失**：用 AskUserQuestion（multiSelect）列出未安装组件让用户勾选要装哪些，把勾选项拼成 `UPDATE_INSTALL=openwiki,codegraph,ocr,deepeval` 的子集再启动。**不问就装 = 违规**；用户全部不选则不传该变量。
- marketplaces / plugins 无「安装」概念，不参与此步骤。

## 怎么跑（必须后台跑，避免超时）

脚本已内置代理预检、容错、版本采集与汇总。**必须以后台任务方式运行**——17 个 plugin 逐个更新、两个 `npm install`，整体常超过前台 10 分钟时限。前台同步跑必然被超时杀断，导致 plugin 循环跑不完。

用 Bash 工具，设 `run_in_background: true`（`<技能目录>` 即本 SKILL.md 所在目录，调用技能时已知，不要写死绝对路径）：

```bash
bash <技能目录>/scripts/update.sh
# 有勾选安装时：
UPDATE_INSTALL=openwiki,codegraph bash <技能目录>/scripts/update.sh
```

启动后**不要干等**：告诉用户「更新已在后台进行，预计 5-10 分钟，完成后我会汇报」，然后等后台完成通知。完成后用 Read 读取任务输出文件（通知里给的 `.output` 路径），把末尾「==================== 汇总 ====================」那段原样转述给用户，并补上下面两条收尾提示。

> 读取输出时可用 `sed 's/\x1b\[[0-9;]*m//g'` 去掉颜色码，便于粘贴。
> 若用户想看实时进度，可中途 Read 那个 `.output` 文件——脚本是逐步 flush 的。

## 代理预检（启动时自动，无需手动 export）

marketplace/plugins 走 github、npm 包（openwiki/codegraph/ocr）走 npm registry，在本机通常直连可用；但受限网络（如 github 间歇性拦截）下仍可能需要代理。脚本**在进程内 `export *_PROXY`，子进程（npm/curl）自动继承，用户无需在 shell 里手动设置**。代理来源解析顺序：

1. 已有的 `HTTPS_PROXY` / `https_proxy` / `ALL_PROXY` / `all_proxy` / `HTTP_PROXY` / `http_proxy` 环境变量；
2. `UPDATE_PROXY` 环境变量（一次性指定，如 `UPDATE_PROXY=http://127.0.0.1:7890`）；
3. 持久配置文件 `proxy.env`（位于本技能目录下，与 SKILL.md 同级；首次探测成功后自动写入，下次免探测，已加入 .gitignore 不入库）。

启动后用 curl 探测 `github.com` 是否可达（curl 自动走已 export 的代理）。**不可达时自动探测本地常见代理端口**（Clash `7890` / Clash Verge `7897` / V2RayN `10809` / `1080` / `2080` 等），命中即 export 并写入 `proxy.env` 记住。探测列表全失败才提示用户启动代理并退出。

- 删掉 `proxy.env` 即可重新触发探测。
- 若只想更新不依赖 github 的组件（npm 包 openwiki/codegraph/ocr），设 `UPDATE_NO_PROXY_GATE=1` 跳过闸门强制运行（marketplace/plugins 可能失败，其余步骤照跑）。

> 所有更新步骤均走 github（marketplace/plugins）或 npm registry（openwiki/codegraph/ocr），无任何步骤依赖 `downloads.claude.ai`。


## 脚本做了什么（6 步）

| # | 组件 | 命令 | 版本采集 |
|---|---|---|---|
| 1 | 所有 marketplaces | `claude plugin marketplace update`（无参 = 全部） | 市场计数 |
| 2 | 已安装 plugins | 循环 `claude plugin update <id> --scope <scope>`（id+scope 来自 `claude plugin list --json`） | 逐个 前→后 |
| 3 | openwiki | `npm install -g openwiki@latest` | `npm list -g openwiki --depth=0 --json` |
| 4 | codegraph | `npm install -g @colbymchenry/codegraph@latest` | `codegraph --version` |
| 5 | open-code-review (ocr) | `npm install -g @alibaba-group/open-code-review@latest` | `npm list -g @alibaba-group/open-code-review --depth=0 --json` |
| 6 | deepeval | `python -m pip install --upgrade deepeval` + `npx -y skills update deepeval` | `pip show deepeval` 的 Version / `npx skills ls \| grep deepeval` |

> ocr 是纯 CLI（命令名 `ocr`），非常驻 MCP server，更新无文件锁问题（与 openwiki 同类）。

> **plugins 必须带 `--scope`**：CLI 默认 `--scope user`，而很多插件装在 `local`/`project` 作用域，不带 scope 会报 `Plugin "X" not found`。脚本从 JSON 读每项的 `scope` 一并传入。

## 必须告知用户的两条收尾提示

1. **plugins 更新需重启 Claude Code 才生效**：CLI 会提示 "restart required to apply"，更新只是暂存了新版本，当前会话仍跑旧版本。
2. **codegraph 更新会自动终止其运行进程**：codegraph MCP server 运行时持有 `node.exe`，直接 `npm install` 会报 `EBUSY`。脚本在更新前用 PowerShell **精确终止** `ExecutablePath` 含 `codegraph` 的 `node.exe` 进程（不误伤其他 node；codegraph 自带 watchdog，被杀重启是其设计常态），更新完成后 `.claude.json` 配置原样保留 → **重启 Claude Code 会话即自动恢复**。当前会话内 codegraph 工具会临时不可用直到重启。若仍未杀净（如进程在更新中被 respawn），脚本识别 `EBUSY` 并提示换会话重跑。

## 重要纠错（勿再踩）

`codegraph upgrade` 这个子命令**不存在**（会报 `unknown command 'upgrade'`）。codegraph 是 npm 全局包 `@colbymchenry/codegraph`，更新一律走 `npm install -g @colbymchenry/codegraph@latest`。脚本里已是正确写法，这里写明是为了防止后续有人想当然地改回 `codegraph upgrade`。

## 逐项手动验证命令（脚本之外，排查用）

- marketplaces：`claude plugin marketplace list` / `claude plugin marketplace update`
- plugins：`claude plugin list --json` / `claude plugin update <name@marketplace>`
- openwiki：`npm view openwiki version`（最新版）/ `npm list -g openwiki --depth=0`
- codegraph：`npm view @colbymchenry/codegraph version` / `codegraph --version`
- open-code-review(ocr)：`npm view @alibaba-group/open-code-review version`（最新版）/ `npm list -g @alibaba-group/open-code-review --depth=0` / `ocr --version`
- deepeval：`pip index versions deepeval` 或 `python -m pip install --upgrade deepeval`（最新版）/ `deepeval --version` / `npx skills ls | grep deepeval`

> Claude Code 本体：`claude --version` / `claude update`（退出会话后手动跑，不在本技能流程内）。

## 环境前提

- Windows 11 + Git Bash（Unix 语法）；`claude`、`npm`、`codegraph`、`python` 均在 PATH。
- npm 全局包目录为 `%APPDATA%\npm`（即 `~/AppData/Roaming/npm`）。
