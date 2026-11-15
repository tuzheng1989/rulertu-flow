---
name: update
description: 一键更新本机 ZCode 工具链的外部组件（所有 marketplaces、已安装 plugins、openwiki、codegraph、open-code-review(ocr)、deepeval、agent-skills（~/share/agent-skills 下的 skill git 仓库））。当用户说"更新 zcode 环境"、"update everything"、"整体更新"、"更新全部插件/插件市场"、"update plugins"、"刷新 codegraph/openwiki/ocr/deepeval/agent-skills"等时触发此技能。即使用户只说"帮我更新一下环境"或"把 zcode 相关的都更新一下"，只要涉及上述组件的升级就用本技能。注意：ZCode 本体无法在运行中自我更新，已从本技能移除——桌面版经应用内更新（检查更新/重启获取新版），CLI 无 `zcode update` 子命令（已实测确认）。
---

# /update — ZCode 工具链外部组件一键更新

把本机 ZCode 工具链的 7 类外部组件一次性更新到位，逐项报告「更新前 → 更新后」版本，单步失败不中断整体流程，最后给出汇总表。

> **ZCode 本体不在此技能范围内**：它无法在运行中自我更新（会话内的进程无法替换自身），CLI 也无 `zcode update` 子命令。桌面版经应用内更新分发新版：请在 ZCode 桌面端检查更新，或重启应用获取。

> **zcode CLI 不在 PATH**（桌面版默认不注册）：脚本内置 `resolve_zcode`——优先 PATH 中的 `zcode`，降级用 node 执行已知安装位置的 `zcode.cjs`（`/c/Program Files (x86)/ZCode/resources/glm/zcode.cjs` 等），无需用户手动配置。

## 步骤 0：先检测缺失组件，询问后再启动

脚本对**未安装**的 npm/pip 组件（openwiki、codegraph、ocr、deepeval）默认跳过并给出手动安装命令；仅当通过 `UPDATE_INSTALL`（逗号分隔组件名）显式勾选时才会新装。因此启动前先做一步检测：

```bash
npm list -g openwiki @colbymchenry/codegraph @alibaba-group/open-code-review --depth=0 2>/dev/null
python -m pip show deepeval 2>/dev/null | head -2
```

- **无缺失**：直接启动脚本，不传 `UPDATE_INSTALL`。
- **有缺失**：用 AskUserQuestion（multiSelect）列出未安装组件让用户勾选要装哪些，把勾选项拼成 `UPDATE_INSTALL=openwiki,codegraph,ocr,deepeval` 的子集再启动。**不问就装 = 违规**；用户全部不选则不传该变量。
- marketplaces / plugins / agent-skills 无「安装」概念，不参与此步骤。

## 怎么跑（必须后台跑，避免超时）

脚本已内置 zcode CLI 解析、代理预检、容错、版本采集与汇总。**必须以后台任务方式运行**——已装插件逐个更新、两个 `npm install`，整体常超过前台 10 分钟时限。前台同步跑必然被超时杀断，导致 plugin 循环跑不完。

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

> 所有更新步骤均走 github（marketplace/plugins/agent-skills）或 npm registry（openwiki/codegraph/ocr），无任何步骤依赖厂商下载站。

## 脚本做了什么（7 步）

| # | 组件 | 命令 | 版本采集 |
|---|---|---|---|
| 1 | 所有 marketplaces | `zcode plugins marketplace update`（无参 = 全部） | `plugins marketplace list` 市场计数 |
| 2 | 已安装 plugins | 循环 `zcode plugins update <id>`（id 来自 `plugins list --json`；默认 user scope 失败时自动补试 `-s project`） | 更新前后两次 `plugins list --json` 的 version 对比 |
| 3 | openwiki | `npm install -g openwiki@latest` | `npm list -g openwiki --depth=0 --json` |
| 4 | codegraph | `npm install -g @colbymchenry/codegraph@latest` | `codegraph --version` |
| 5 | open-code-review (ocr) | `npm install -g @alibaba-group/open-code-review@latest` | `npm list -g @alibaba-group/open-code-review --depth=0 --json` |
| 6 | deepeval | `python -m pip install --upgrade deepeval` + `npx -y skills update deepeval` | `pip show deepeval` 的 Version / `npx skills ls \| grep deepeval` |
| 7 | agent-skills | 循环 `git -C <仓库> pull --ff-only`（`~/share/agent-skills/` 下每个 git 仓库） | 前→后 HEAD 短哈希 |

> ocr 是纯 CLI（命令名 `ocr`），非常驻 MCP server，更新无文件锁问题（与 openwiki 同类）。

> **plugins 无原生 update-all**：CLI 语义是 `update <plugin> [-s <scope>]`（scope 仅 user/project 两值）。`list --json` 不回显 scope，脚本先按默认 user scope 更新，失败自动补试 `-s project`。版本对比靠更新前后两次 `list --json`（含 `version` 字段），不解析更新命令的文本输出。

> **agent-skills 是符号链接的单一源**：`~/.zcode/skills` 里的条目指向 `~/share/agent-skills/` 下的 git 仓库，`git pull` 后链接处即时生效，无需重启。`--ff-only` 保证不产生合并提交；本地有改动或分叉的仓库会报错跳过，需用户自行处理。目录缺失或无仓库时跳过，并在输出中给出手动安装命令（clone + mklink）。脚本只更新已存在的仓库，不维护「期望 skill 清单」——单个 skill 是否缺失由用户自行判断。

## 必须告知用户的两条收尾提示

1. **plugins 更新需重启 ZCode 会话才生效**：更新只是暂存了新版本，当前会话仍跑旧版本。
2. **codegraph 更新会自动终止其运行进程**：codegraph MCP server 运行时持有 `node.exe`，直接 `npm install` 会报 `EBUSY`。脚本在更新前用 PowerShell **精确终止** `ExecutablePath` 含 `codegraph` 的 `node.exe` 进程（不误伤其他 node；codegraph 自带 watchdog，被杀重启是其设计常态），更新完成后 MCP 配置原样保留 → **重启 ZCode 会话即自动恢复**。当前会话内 codegraph 工具会临时不可用直到重启。若仍未杀净（如进程在更新中被 respawn），脚本识别 `EBUSY` 并提示换会话重跑。

## 重要纠错（勿再踩）

`codegraph upgrade` 这个子命令**不存在**（会报 `unknown command 'upgrade'`）。codegraph 是 npm 全局包 `@colbymchenry/codegraph`，更新一律走 `npm install -g @colbymchenry/codegraph@latest`。脚本里已是正确写法，这里写明是为了防止后续有人想当然地改回 `codegraph upgrade`。

`zcode plugins` 的子命令清单（已实测，0.17.1）：`list [--json] [--available]` / `install <plugin>[@marketplace] [-s <scope>]` / `uninstall` / `enable` / `disable` / `update <plugin> [-s <scope>]` / `validate <path>` / `marketplace add|list|remove|update [name]`。scope 仅 `user`（默认）与 `project` 两值。

## 逐项手动验证命令（脚本之外，排查用）

- marketplaces：`zcode plugins marketplace list` / `zcode plugins marketplace update`
- plugins：`zcode plugins list --json` / `zcode plugins update <name@marketplace>`
- openwiki：`npm view openwiki version`（最新版）/ `npm list -g openwiki --depth=0`
- codegraph：`npm view @colbymchenry/codegraph version` / `codegraph --version`
- open-code-review(ocr)：`npm view @alibaba-group/open-code-review version`（最新版）/ `npm list -g @alibaba-group/open-code-review --depth=0` / `ocr --version`
- deepeval：`pip index versions deepeval` 或 `python -m pip install --upgrade deepeval`（最新版）/ `deepeval --version` / `npx skills ls | grep deepeval`
- agent-skills：`git -C ~/share/agent-skills/<name> log --oneline -1`（当前版本）/ `git -C ~/share/agent-skills/<name> pull --ff-only`

> zcode CLI 本体版本：`zcode --version`；不在 PATH 时 `node "<安装目录>/resources/glm/zcode.cjs" --version`。ZCode 桌面版本体升级走应用内更新，不在本技能流程内。

## 环境前提

- Windows 11 + Git Bash（Unix 语法）；`npm`、`codegraph`、`python`、`git`、`node` 均在 PATH；`zcode` 在 PATH 或 ZCode 桌面版装在默认位置（脚本自动解析）。
- npm 全局包目录为 `%APPDATA%\npm`（即 `~/AppData/Roaming/npm`）。
