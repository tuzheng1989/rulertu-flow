---
name: update
description: 一键更新本机 AI 工具链的外部组件：zcode / claude / codex 三个宿主的 marketplaces 与已装 plugins（按检测到的 CLI 动态编排，缺哪个宿主跳过哪段），外加 openwiki、codegraph、open-code-review(ocr)、deepeval、agent-skills（~/share/agent-skills 下的 skill git 仓库）。当用户说"更新 zcode 环境"、"update everything"、"整体更新"、"更新全部插件/插件市场"、"update plugins"、"更新 claude/codex 插件"、"刷新 codegraph/openwiki/ocr/deepeval/agent-skills"等时触发此技能。即使用户只说"帮我更新一下环境"或"把工具链都更新一下"，只要涉及上述组件的升级就用本技能。注意：ZCode 本体与 Claude Code 本体不在范围内（前者桌面版应用内更新，后者自带 auto-update）；Codex 本体例外，有官方 `codex update`。
---

# /update — 本机 AI 工具链外部组件一键更新

把本机 AI 工具链的外部组件一次性更新到位，逐项报告「更新前 → 更新后」版本，单步失败不中断整体流程，最后给出汇总表。

> **宿主段按检测动态编排**：zcode / claude / codex 三段各自独立，CLI 存在才入列——缺哪个宿主跳过哪段，步骤编号按实际将执行的段计算。检测不到任何宿主 CLI 时仅更新固定段（npm/pip 组件与 agent-skills）。

> **宿主本体更新不在范围内（codex 例外）**：ZCode 本体无法在运行中自我更新（桌面版经应用内更新分发新版，CLI 无 `zcode update` 子命令，已实测确认）；Claude Code 自带 auto-update 且会话内进程无法自替换（沿用 claude-code 留档分支的判断）；Codex 有官方 `codex update` 子命令，脚本在 codex 段执行——在 codex 会话内运行时运行中的 exe 被文件锁住会失败（Windows），如实报告不中断。

> **zcode CLI 不在 PATH**（桌面版默认不注册）：脚本内置 `resolve_zcode`——优先 PATH 中的 `zcode`，降级用 node 执行已知安装位置的 `zcode.cjs`（`/c/Program Files (x86)/ZCode/resources/glm/zcode.cjs` 等），无需用户手动配置。claude / codex 是 CLI-first 分发，PATH 能找到即视为已安装。

## 步骤 0：先检测缺失组件，询问后再启动

脚本对**未安装**的 npm/pip 组件（openwiki、codegraph、ocr、deepeval）默认跳过并给出手动安装命令；仅当通过 `UPDATE_INSTALL`（逗号分隔组件名）显式勾选时才会新装。因此启动前先做一步检测：

```bash
npm list -g openwiki @colbymchenry/codegraph @alibaba-group/open-code-review --depth=0 2>/dev/null
python -m pip show deepeval 2>/dev/null | head -2
```

- **无缺失**：直接启动脚本，不传 `UPDATE_INSTALL`。
- **有缺失**：用 AskUserQuestion（multiSelect）列出未安装组件让用户勾选要装哪些，把勾选项拼成 `UPDATE_INSTALL=openwiki,codegraph,ocr,deepeval` 的子集再启动。**不问就装 = 违规**；用户全部不选则不传该变量。
- marketplaces / plugins / agent-skills 无「安装」概念，不参与此步骤。宿主段也不参与——CLI 不存在即整段跳过，CLI 存在即整段执行。

## 怎么跑（必须后台跑，避免超时）

脚本已内置宿主检测、zcode CLI 解析、代理预检、容错、版本采集与汇总。**必须以后台任务方式运行**——三个宿主的插件逐个更新、多个 `npm install`，整体常超过前台 10 分钟时限。前台同步跑必然被超时杀断，导致 plugin 循环跑不完。

用 Bash 工具，设 `run_in_background: true`（`<技能目录>` 即本 SKILL.md 所在目录，调用技能时已知，不要写死绝对路径）：

```bash
bash <技能目录>/scripts/update.sh
# 有勾选安装时：
UPDATE_INSTALL=openwiki,codegraph bash <技能目录>/scripts/update.sh
```

启动后**不要干等**：告诉用户「更新已在后台进行，预计 5-10 分钟，完成后我会汇报」，然后等后台完成通知。完成后用 Read 读取任务输出文件（通知里给的 `.output` 路径），把末尾「==================== 汇总 ====================」那段原样转述给用户，并补上「必须告知的收尾提示」。

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

> 所有更新步骤均走 github（marketplace/plugins/agent-skills）、npm registry（openwiki/codegraph/ocr）或各宿主官方更新通道（codex update），无步骤依赖厂商下载站。

## 脚本做了什么（宿主段 + 固定段，按检测动态编排）

三宿主都在时共 11 步（2×3 宿主段 + 5 固定段），步骤编号动态计算：

| 段 | 组件 | 命令 | 版本采集 |
|---|---|---|---|
| zcode | marketplaces | `zcode plugins marketplace update`（无参 = 全部） | `marketplace list` 市场计数 |
| zcode | 已装 plugins | 循环 `zcode plugins update <id>`（默认 user scope 失败自动补试 `-s project`；`zcode-plugins-official` 整市场跳过） | 更新前后两次 `list --json` 的 version 对比 |
| claude | marketplaces | `claude plugin marketplace update`（无参 = 全部） | `marketplace list` 计 `❯` |
| claude | 已装 plugins | 循环 `claude plugin update <id> --scope <scope>`（scope 直接取自 `list --json`，按 id+scope 去重） | 更新前后两次 `list --json` 的 version 对比 |
| codex | 插件 | `codex plugin marketplace upgrade`（无参 = 全部 Git 市场快照） | 前后两次 `plugin list` 的 installed 行 diff |
| codex | CLI 本体 | `codex update` | `codex --version` |
| 固定 | openwiki | `npm install -g openwiki@latest` | `npm list -g openwiki --depth=0 --json` |
| 固定 | codegraph | `npm install -g @colbymchenry/codegraph@latest` | `codegraph --version` |
| 固定 | open-code-review (ocr) | `npm install -g @alibaba-group/open-code-review@latest` | `npm list -g … --depth=0 --json` |
| 固定 | deepeval | `python -m pip install --upgrade deepeval` + `npx -y skills update deepeval` | `pip show deepeval` / `npx skills ls \| grep deepeval` |
| 固定 | agent-skills | 循环 `git -C <仓库> pull --ff-only`（`~/share/agent-skills/` 下每个 git 仓库） | 前→后 HEAD 短哈希 |

> **codex 没有 per-plugin update 命令**（`codex plugin` 只有 add/list/marketplace/remove，已实测 0.170.0）：已装插件直接从 marketplace 快照路径加载（`plugin list` 的 SOURCE 列即快照路径），刷新快照即更新插件，新会话即时读取新版。这是三宿主里唯一「免重启生效」的插件更新。

> **plugins 无原生 update-all**：zcode 语义是 `update <plugin> [-s <scope>]`（scope 仅 user/project）；claude 语义是 `update <plugin> --scope <scope>`（scope 有 user/project/local/managed 四值，直接取自 list --json 不猜测）。版本对比靠更新前后两次列表采集，不解析更新命令的文本输出。

> **agent-skills 是符号链接的单一源**：`~/.zcode/skills` 里的条目指向 `~/share/agent-skills/` 下的 git 仓库，`git pull` 后链接处即时生效，无需重启。`--ff-only` 保证不产生合并提交；本地有改动或分叉的仓库会报错跳过，需用户自行处理。目录缺失或无仓库时跳过，并在输出中给出手动安装命令（clone + mklink）。脚本只更新已存在的仓库，不维护「期望 skill 清单」。

## 必须告知用户的收尾提示

1. **zcode / claude 的 plugins 更新需重启对应宿主会话才生效**：更新只是暂存了新版本，当前会话仍跑旧版本。
2. **codex 插件随快照即时生效**（新会话读取新版），无需重启动作。
3. **codegraph 更新会自动终止其运行进程**：codegraph MCP server 运行时持有 `node.exe`，直接 `npm install` 会报 `EBUSY`。脚本在更新前用 PowerShell **精确终止** `ExecutablePath` 含 `codegraph` 的 `node.exe` 进程（不误伤其他 node；codegraph 自带 watchdog，被杀重启是其设计常态），更新完成后 MCP 配置原样保留 → **重启 ZCode 会话即自动恢复**。当前会话内 codegraph 工具会临时不可用直到重启。若仍未杀净（如进程在更新中被 respawn），脚本识别 `EBUSY` 并提示换会话重跑。

## 重要纠错（勿再踩）

`codegraph upgrade` 这个子命令**不存在**（会报 `unknown command 'upgrade'`）。codegraph 是 npm 全局包 `@colbymchenry/codegraph`，更新一律走 `npm install -g @colbymchenry/codegraph@latest`。脚本里已是正确写法，这里写明是为了防止后续有人想当然地改回 `codegraph upgrade`。

**codex 没有 per-plugin update**：不要找 `codex plugin update <name>`，它不存在也不需要——快照即加载源。`codex plugin marketplace upgrade` 就是 codex 的插件更新命令。

**Claude Code 本体不要加进脚本**：`claude update` 虽存在，但会话内运行时进程无法自替换（Windows 文件锁），且 Claude Code 自带 auto-update——留档分支已明确排除，勿加回来。

`zcode plugins` 的子命令清单（已实测，0.17.1）：`list [--json] [--available]` / `install <plugin>[@marketplace] [-s <scope>]` / `uninstall` / `enable` / `disable` / `update <plugin> [-s <scope>]` / `validate <path>` / `marketplace add|list|remove|update [name]`。scope 仅 `user`（默认）与 `project` 两值。

`claude plugin` 的关键子命令（已实测，2.1.322）：`list [--json]` / `install|update|uninstall <plugin> [-s|--scope <user|project|local|managed>]` / `marketplace add|list|update|remove [name]`。`plugin list --json` 字段：`id` / `version` / `scope` / `enabled` / `installPath`；同一 id 可能有多条记录（不同 scope/项目），按 id+scope 去重后更新。

`codex plugin` 的子命令清单（已实测，0.170.0）：`add` / `list`（无 --json）/ `marketplace add|list|upgrade|remove` / `remove`。`marketplace upgrade [name]` 省略名即刷新全部 Git 市场快照。

## 扩展：新增宿主段

1. 先实测该宿主 CLI 的插件子命令与输出格式（list 是否有 --json、update 是否带 scope、市场刷新动词），把已验证的命令写进脚本头注释。
2. 实现 `update_<host>_marketplaces` / `update_<host>_plugins`（或合并为一个函数）：签名 `(step_label)`，内部用 `section "$1" "标题"`，汇总行以宿主名开头；拿不到版本对比就学 codex 段做前后列表 diff。
3. 在「宿主检测与执行计划」处加一行检测（`command -v <cli>`）和一行 `PLAN+=()` 挂载。
4. 本体更新默认不纳入：除非宿主有官方自更新子命令且在会话外运行无文件锁问题（codex 是目前唯一例外）。

## 逐项手动验证命令（脚本之外，排查用）

- zcode：`zcode plugins marketplace list` / `zcode plugins marketplace update` / `zcode plugins list --json` / `zcode plugins update <name@marketplace>`
- claude：`claude plugin marketplace list` / `claude plugin marketplace update` / `claude plugin list --json` / `claude plugin update <name@marketplace> --scope <scope>`
- codex：`codex plugin list` / `codex plugin marketplace upgrade` / `codex update` / `codex --version`
- openwiki：`npm view openwiki version`（最新版）/ `npm list -g openwiki --depth=0`
- codegraph：`npm view @colbymchenry/codegraph version` / `codegraph --version`
- open-code-review(ocr)：`npm view @alibaba-group/open-code-review version`（最新版）/ `npm list -g @alibaba-group/open-code-review --depth=0` / `ocr --version`
- deepeval：`pip index versions deepeval` 或 `python -m pip install --upgrade deepeval`（最新版）/ `deepeval --version` / `npx skills ls | grep deepeval`
- agent-skills：`git -C ~/share/agent-skills/<name> log --oneline -1`（当前版本）/ `git -C ~/share/agent-skills/<name> pull --ff-only`

> 各宿主 CLI 本体版本：`zcode --version`（不在 PATH 时 `node "<安装目录>/resources/glm/zcode.cjs" --version`）/ `claude --version` / `codex --version`。ZCode 桌面版本体升级走应用内更新，不在本技能流程内。

## 环境前提

- Windows 11 + Git Bash（Unix 语法）；`npm`、`codegraph`、`python`、`git`、`node` 均在 PATH；`zcode` 在 PATH 或 ZCode 桌面版装在默认位置（脚本自动解析）；`claude` / `codex` 在 PATH（不存在则对应宿主段整段跳过）。
- npm 全局包目录为 `%APPDATA%\npm`（即 `~/AppData/Roaming/npm`）。
