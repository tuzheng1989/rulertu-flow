# Changelog

## Unreleased

- work-skills 1.2.0：新增 `screen-condense`（录屏自动精简，离线画面变化分析 + 抽帧变速压缩为指定时长无声 MP4，附时间对应表），自 `.codex/skills` 收编；双 manifest 版本对齐 1.2.0。
- 门禁基线修复：Codex marketplace 补 `copyright-skills` 条目，agent-skills 双 manifest 版本对齐 1.1.0，`validate_repo.py` 恢复通过。
- copyright-skills 1.1.0：软著链路整改——表述治理（删除无出处的"2026.3.15 新版审查规则 / 官方查重 / 必被驳回 / 征信"类表述，改按内部口径并附官网核对记录与 URL）、新增权属文件决策表与权属清单 JSON（references/ownership.md）、登记表重定位为在线填报工作底稿并新增 `check_submission.py` 提交前校验、说明书/源码构建器整改（证据移出 docx 正文改入 audit JSON、`build_source_docx.py` 新增 `--first` 入口前置、新增 `render_check.py` 渲染实测，后端自动选择本机 Word COM，无需安装 LibreOffice）、补齐 pytest 测试基建（52 用例）。
- 新增插件 `work-skills`：17 个工作型技能（深度研究、战略分析、文档转换、思维工具等），自个人技能库收编；`url-to-md` 剥离 node_modules，改为首次使用 `bun install` 重建。
- 新增插件 `agent-skills`：5 个 Agent 工程技能（ai-agent-design 知识包统一路由、agent-evaluator、deepagents、deepagents-update、model-info）；ai-agent-design 以 pack 收纳为单个注册技能，原书插图不随插件分发。
- `validate_repo.py`：marketplace 条目按名称查找（不再依赖数组顺序），并遍历所有插件校验双宿主 manifest 一致性、skills 目录与技能 frontmatter。
- CI 的 Codex 安装冒烟测试覆盖全部三个插件；README 新增选择性与安装范围（user/project/local）说明。

## 2.0.0

- Breaking: 插件安装根从仓库根迁移到 `plugins/rulertu-flow`，1.x 用户需要卸载并重新安装。
- 新增 Codex manifest 与团队 marketplace，保留 Claude Code manifest、marketplace 和代理入口。
- Codex 固定 Executor=`gpt-5.6-terra`/medium、Auditor=`gpt-5.6-sol`/high、Advisor=`gpt-5.6-sol`/xhigh；Claude Code 保留 Executor=Sonnet、Auditor/Advisor=Opus，并以薄封装读取共享角色正文。
- Executor 默认只跑定向测试，全量回归移动到波次收口并限定三个例外。
- plan-iterate 新增跨平台 Python 后端、原子 `state.json`、严格 schema 校验和旧 `session.txt` 迁移。
- plan-iterate 在 Codex 宿主外调 Claude Code、在 Claude Code 宿主外调 Codex CLI，并共享评审协议与跨后端状态迁移。
- 新增 Windows/Ubuntu CI、标准库单元测试和仓库发布门禁。
