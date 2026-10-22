# Changelog

## Unreleased

- flow-deck 0.7.0：新增 `/flow-agents` 子代理监控面板，直接读取宿主当前会话的子代理与进程内队友清单，展示状态汇总、任务、类型、ID 与父代理关系；运行中优先，仅打开时每 2 秒查询，关闭后停止，失败保留快照并标记过期。新增状态变化、未知状态、失败恢复、防重入与终端/桌面宽窄渲染测试。
- flow-deck 0.6.1、rulertu-flow 2.5.1：修复 `/flow` 把历史评审、路线图或收口记录当成当前任务的问题；新增 `flow_task` 区分方案迭代、方案实施与空闲，配套技能同步开始/结束状态，面板与横条只展示当前任务的数据，任务结束或切换后撤下旧执行显示与边界守卫。新增任务切换、历史数据过滤与收口回归测试。
- rulertu-flow 版本升至 2.5.0：commit 与 pr 技能加入时漏 bump 版本号，marketplace 已拉到新文件但插件版本仍为 2.4.0，缓存副本不刷新导致技能不可见；升版触发重装后生效。
- flow-deck 0.6.0：面板增加概览、评审评分条与分差、执行阶段轨迹、验证进度和批次收口进度；窄面板去边框，长路径截断，横条遵守可用行数并优先提示冲突。评审目录发现降为 30 秒，已知目录仍每 2 秒检查并按文件元数据缓存；Git 改为改动 5 秒 / 空闲 15 秒 / 非仓库 60 秒重试，无对应 tracked 改动时跳过 diff；快照无变化不写状态，慢查询防重入，打开 /git 异步强制刷新。新增轮询开销与宽窄面板回归测试。
- 新增插件 `rulertu-frontend` 0.1.0：前端开发工程师代理 `frontend-dev`（界面开发、前端排障、性能优化与浏览器验收，双 manifest 双 marketplace 注册）加 6 个 z.ai 官方技能（Apache-2.0，保留 LICENSE 与 NOTICE）——网页界面开发、前端问题排查与修复、网页性能优化、网页功能与兼容性测试、前端需求与验收设计、页面交互与状态开发；接入时剥离智谱平台专属元数据（openai.yaml / marketplace.yaml / platform-metadata.json / DISTRIBUTION-CHANGES.md），agent 技能路由覆盖全部 6 个技能。
- 修正 plan-iterate 的归一化测试：额外字段按现有兼容逻辑剥除，保留不完整输入的拒绝检查，并补充异构后端 issue 字段归一化用例。
- rulertu-flow 新增 `commit` 与 `pr` 两个写作技能：默认用中文面向项目维护者，依据实际 diff 写清问题与变化，按需补充原因、约束及验证证据；文案长度随改动复杂度调整，实际提交与 PR 操作沿用已有授权。
- flow-deck 0.5.1：评审横条达标即撤——statusline 只展示最后一个未达标方案（`bannerPlan`），方案达标瞬间 toast 播报后横条即撤下，不再常驻已完结评审的残留状态；`/flow` 面板不受影响，仍展示全部方案与轮次历史。多方案并存时名字排序更靠后的达标方案不再挤占未达标方案的横条位。
- flow-deck 0.5.0：git 仓库状态可视化——每 3 秒轮询 `git status --porcelain=v1 -b` 与两次 `diff --numstat`；工作区脏或与上游有偏差时输入框上方横条新增 `▸ git` 行（分支、↑ahead/↓behind、暂存/改/新计数、`+行 −行`，冲突红字优先），`/git` 命令 toggle 详情面板（冲突/已暂存/未暂存/未跟踪四分区，每区超 15 条折叠计数，行级增删着色汇总）。非 git 仓库全程静默；statusline 与 `/flow` 面板不受影响。
- flow-deck 0.4.1：`/flow` 改为 toggle 语义——面板已开时再输入即关闭（经 `$.ui.panes()` 感知），与引擎原生关闭方式互不干扰。
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
