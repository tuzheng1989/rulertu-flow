---
name: plugin-release
description: rulertu-flow 仓库维护者的插件发布闭环——仓库门禁、升版与 CHANGELOG 检查、提交推送 GitHub、zcode marketplace/plugins 更新本机缓存、版本与内容一致性验证。当用户说"发布插件"、"更新 rulertu-flow 插件"、"发版"、"把仓库插件改动同步到本机"、"发布并验证插件"、"插件发布后验证"等时使用。边界：rulertu-flow:update 技能负责消费者侧全量工具链更新（所有市场、npm/pip 组件）；本技能只管本仓库插件的发布-更新-验证闭环，属仓库维护者流程，依赖本仓库与 gh/git。
---

# plugin-release — rulertu-flow 插件发布闭环

把仓库里的插件改动走完 **门禁 → 升版检查 → CHANGELOG → 提交推送 → 本机更新 → 验证** 六个阶段。本机 rulertu-flow 市场源是 GitHub 远程（`tuzheng1989/rulertu-flow`），**未推送的改动 CLI 更新拉不到**，所以推送是闭环的必经环节（推送前必须征求用户确认）。

**背景事实**（均已实测，写在这里避免重复踩坑）：

- 本机已安装 4 个本市场插件：`rulertu-flow`、`agent-skills`、`work-skills`、`flow-deck`（scope 均为 user）；`copyright-skills`、`rulertu-frontend` 未安装，不在更新范围。
- 缓存位置 `~/.zcode/cli/plugins/cache/rulertu-flow/<插件>/<版本>/`，内容是 git 追踪文件的全量复制。
- `plugins update` 按版本号判断更新——**改了内容但没升版，远端版本号没变，更新不会拉新内容**。发布前必须双 manifest（`.claude-plugin/plugin.json` + `.codex-plugin/plugin.json`）同步升版。
- 插件更新只是暂存新缓存，**当前会话仍跑旧版本**，重启 ZCode 会话才生效。
- `scripts/validate_repo.py` 有 4 条存量 ERROR（family-skills / secret-skills 本地未上架目录所致），是长期基线；通过标准是**存量外零新增**。

## 阶段 0：摸底

```bash
git status --short && git log origin/main..HEAD --oneline   # 未提交改动 + 未推送提交
```

确定本次发布涉及哪些插件：用户点名的优先；否则从未提交改动和未推送提交的文件路径（`plugins/<插件名>/...` 前缀）推断。**两者都为空 = 无可发布内容**，向用户报告后直接结束，不要硬走后续阶段。

## 阶段 1：仓库门禁 + 升版检查

```bash
python scripts/validate_repo.py
```

4 条存量 ERROR（见上）之外出现任何新增 ERROR → 先修复再继续，不带病发布。

然后逐个涉及插件做升版检查：

```bash
git diff origin/main..HEAD --name-only -- plugins/<插件名>   # 有无待发布改动
cat plugins/<插件名>/.claude-plugin/plugin.json               # 当前版本
```

- 改动插件的双 manifest 版本**必须已高于远端已发布版本**（即缓存里正在用的版本）。未升版 → 用 AskUserQuestion 问用户升 patch 还是 minor（或暂不发布该插件），改完双 manifest 再继续。**不问就擅自定版本 = 违规**。
- 双 manifest 版本不一致 → 直接指出并同步修正。

## 阶段 2：CHANGELOG 检查

每个涉及插件在 `CHANGELOG.md` 的 `## Unreleased` 段应有一条对应条目（`- <插件名> <版本>：<改动详情>`，仓库惯例是详细条目）。缺失时提醒用户补写或代为起草后经用户确认写入，再继续。

## 阶段 3：提交推送（推送前必须确认）

1. 未提交改动按仓库提交样式（conventional commits，scope = 插件名，如 `feat(flow-deck): ...`）草拟提交信息，执行 `git commit`。
2. **推送是外发操作：`git push` 前用 AskUserQuestion 征求用户确认**，展示将推送的提交列表。用户拒绝则停在推送前，后续阶段作废。

## 阶段 4：本机更新

```bash
zcode plugins marketplace update rulertu-flow
zcode plugins update <插件名>@rulertu-flow     # 逐个涉及插件；未安装的跳过并说明
```

`zcode` 不在 PATH 时降级 `node "C:\Program Files (x86)\ZCode\resources\glm\zcode.cjs" ...`（与 update 技能同口径）。更新命令失败时完整阅读报错再处理，不要盲目重试。

## 阶段 5：验证

```bash
python .agents/skills/plugin-release/scripts/verify_plugins.py [插件名 ...]
```

脚本一次跑完四项并输出汇总（门禁存量外零新增 / 仓库版本 == 缓存版本 / git 追踪文件逐个与缓存比对，仅行尾差异记 WARN / `zcode plugins validate` 结构校验），退出码 1 即存在失败项。把汇总表转述给用户；有 FAIL 先溯源修复再重跑，**贴出最终通过的证据**（脚本末尾的汇总段）。

## 阶段 6：收尾

两条必说：

1. 插件更新需**重启 ZCode 会话**才在会话内生效，当前会话仍是旧版。
2. 若验证有 WARN（仅行尾差异），说明判定已通过但列出行尾差异文件数，供用户知晓。
