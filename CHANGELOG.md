# Changelog

## Unreleased

- flow-deck 0.4.0：波次依赖 DAG 可视化——新增 `flow_deps` 工具（`mcp__flow-deck__flow_deps`），optimization-plan 路线图定稿时声明波次依赖图；`/flow` 面板新增「执行 DAG」区块，按推荐执行顺序逐批标注三态（收口 ✓ 绿 / 进行中 ● 黄 / 待执行 ○ 灰）与依赖箭头。`flow_report` 顺带累积各批阶段记录（此前仅保留当前批）。技能侧协同：optimization-plan「文档分层」节加声明义务（工具不存在静默跳过）。
- flow-deck 0.3.0：锚点边界守卫——新增 `flow_batch` 工具（`mcp__flow-deck__flow_batch`），每批派单完成后声明本批允许改动的文件集合；此后对边界外文件的 Edit/Write 按 `guardMode` 配置处理（默认 `warn` 越界提醒后放行，可切 `deny` 硬拦截），未声明边界或 cwd 未就绪时静默放行。路径比较归一化分隔符、工作目录前缀与大小写（Windows 友好）。技能侧协同：implement-plan「进度上报」小节补 `flow_batch` 义务（派单完成后声明边界，工具不存在静默跳过）。已知平台行为：工具执行期间 toast 不显示，越界提醒走 transcript 系统通知。
- flow-deck 0.2.0：执行期进度上报——新增 `flow_report` 工具（`mcp__flow-deck__flow_report`），implement-plan 各阶段（开工/派单/执行/验证/收口）完成即上报，输入框上方横条实时显示批次/T级/验证进度；上报跨会话保留，新会话启动时 toast 提醒上次执行位置。技能侧协同：implement-plan 新增「进度上报」小节（工具不存在时静默跳过，不绑定插件安装），证据目录约定固化为方案未指定时用方案文档同目录 `.flow-evidence/`。
- 新增插件 `flow-deck` 0.1.0（mod 形态，仅 Claude Code 生效）：plan-iterate 评审进度实时可视化——`/flow` 打开评审仪表盘面板（轮次进度、评分趋势条、P0/P1/P2 计数、达标标记），评审文件落盘即弹 toast 提醒，statusline 常驻当前评审摘要；轮询消费 `.plan-iterate/<plan名>/` 下的 `state.json` 与 `review-RN.json`，对工作流零侵入。Codex 侧 manifest 为占位元数据。
- work-skills Codex manifest 版本补对齐 1.3.0（上版漏更，门禁拦截）。
- work-skills 1.2.0：新增 `screen-condense`（录屏自动精简，离线画面变化分析 + 抽帧变速压缩为指定时长无声 MP4，附时间对应表），自 `.codex/skills` 收编；双 manifest 版本对齐 1.2.0。
- 门禁基线修复：Codex marketplace 补 `copyright-skills` 条目，agent-skills 双 manifest 版本对齐 1.1.0，`validate_repo.py` 恢复通过。
- copyright-skills 1.1.0：软著链路整改——表述治理（删除无出处的"2026.3.15 新版审查规则 / 官方查重 / 必被驳回 / 征信"类表述，改按内部口径并附官网核对记录与 URL）、新增权属文件决策表与权属清单 JSON（references/ownership.md）、登记表重定位为在线填报工作底稿并新增 `check_submission.py` 提交前校验、说明书/源码构建器整改（证据移出 docx 正文改入 audit JSON、`build_source_docx.py` 新增 `--first` 入口前置、新增 `render_check.py` 渲染实测，后端自动选择本机 Word COM，无需安装 LibreOffice）、补齐 pytest 测试基建（52 用例）。
- 新增插件 `work-skills`：17 个工作型技能（深度研究、战略分析、文档转换、思维工具等），自个人技能库收编；`url-to-md` 剥离 node_modules，改为首次使用 `bun install` 重建。
- 新增插件 `agent-skills`：5 个 Agent 工程技能（ai-agent-design 知识包统一路由、agent-evaluator、deepagents、deepagents-update、model-info）；ai-agent-design 以 pack 收纳为单个注册技能，原书插图不随插件分发。
- `validate_repo.py`：marketplace 条目按名称查找（不再依赖数组顺序），并遍历所有插件校验双宿主 manifest 一致性、skills 目录与技能 frontmatter。
- CI 的 Codex 安装冒烟测试覆盖全部三个插件；README 新增选择性与安装范围（user/project/local）说明。

## 2.3.0

- 咨询权分类下放：技术歧义类（一次修复失败后仍有多个可信方案、接缝选型歧义且不动边界与公共契约）允许 Executor 直连 Advisor，输入要件强制自包含（委派单原文、试错清单、锚点、具体选择题），意见原文落盘证据目录；边界、公共契约与批次范围类仍必须上报主控。
- Advisor 角色适配双委派方：Executor 委派时涉及边界的建议标注"需主控裁决"；选择题偏颇时先点明再作答。
- Codex 侧 Executor 无嵌套代理能力时降级为主控按同规格派发，输入要件不降。
- `validate_repo.py`：解除版本硬编码与 executor 模型钉死（改为禁止 wrapper 内钉模型），新增直连机制与上报标记防回退锚点。

## 2.0.0

- Breaking: 插件安装根从仓库根迁移到 `plugins/rulertu-flow`，1.x 用户需要卸载并重新安装。
- 新增 Codex manifest 与团队 marketplace，保留 Claude Code manifest、marketplace 和代理入口。
- Codex 固定 Executor=`gpt-5.6-terra`/medium、Auditor=`gpt-5.6-sol`/high、Advisor=`gpt-5.6-sol`/xhigh；Claude Code 保留 Executor=Sonnet、Auditor/Advisor=Opus，并以薄封装读取共享角色正文。
- Executor 默认只跑定向测试，全量回归移动到波次收口并限定三个例外。
- plan-iterate 新增跨平台 Python 后端、原子 `state.json`、严格 schema 校验和旧 `session.txt` 迁移。
- plan-iterate 在 Codex 宿主外调 Claude Code、在 Claude Code 宿主外调 Codex CLI，并共享评审协议与跨后端状态迁移。
- 新增 Windows/Ubuntu CI、标准库单元测试和仓库发布门禁。
