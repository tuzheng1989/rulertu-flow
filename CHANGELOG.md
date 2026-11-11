# Changelog

## Unreleased

- flow-deck 0.22.0：`flow_report` 历史批次补报通道（方案 `plans/flow-deck/2026-11-11-deck-deps-progress-persistence.md` B2 批）——**工具侧**：inputSchema 加可选 `backfill`（描述限定「仅用于开工核对时补齐前序批次」防误用为常规通道），处理器在 parse 校验后、一切副作用前分流：`backfill: true` 时只做 progress 更新（键 `<plan>#<batch>` → phase）+ `persistProgress` 持久化（复用 B1 通道）并返回「历史批次状态已补报」文案；closureCard/execution/lastRun/guardWarned/currentTask/batchScope/statusline/lastExecution 全部不触碰，firstReportAt 记点只在 flow_batch 天然不在链路（D11 旁路隔离：常规通道的收口上报会撤任务清边界，补报走同链路会破坏当前批次，旁路是补报可幂等重放的前提）。**技能侧**：implement-plan 开工核对从「只核对不回写」扩展为「核对后补报」——核对到的收口事实与面板状态可能不符（跨会话漏报），会话有 `flow_report` 时对证据目录或 git log 佐证已收口且非本会话已上报的前序批次逐条带 `backfill: true` 补报（幂等，无法佐证不臆测补报）；「不补报、不重试」旧口径改写为「常规上报漏报不补报不重试；开工核对发现的历史批次收口缺失按开工检查点口径经 backfill 补报」。**测试**：新增 backfill 旁路用例（七个「当前执行」键 state.set 序列零触碰 + store.set 落值断言）、backfill 后接常规上报回归用例、持久化写入侧用例（flow_deps 落 depsGraph、常规 flow_report 落 progressMap 与 lastExecution——B1 审计 P2-2 消化，on('store.set') 钩子 B1 探针实证可应答）；修正两处「测试引擎无 store.set 设施」过时注释（P2-1）。双 manifest 同步升版 0.22.0。

- flow-deck 0.21.0：轨道图跨会话状态持久化 + 渲染层拓扑下推（方案 `plans/flow-deck/2026-11-11-deck-deps-progress-persistence.md` B1 批）——**持久化**：`progress` 与 `deps` 两个内存 atom 经 `$.store` 独立键（`progressMap` / `depsGraph`）跨会话保留，`flow_report` 每次进度更新后、`flow_deps` 声明后各自 best-effort 写入（try/catch 降级 + 调试日志，范式同 `lastExecution`），持久化失败不阻塞工具返回；**恢复**：`session.start` 把两行清空替换为「先取后写」恢复（`readPersistedProgress` / `readPersistedDeps` 顶层函数 + `parseProgressMap` 新校验纯函数），store 不可用或坏形状降级为空 map / null——行为同清空现状，`currentTask` 等清空语义不动，恢复的图待同方案实施声明后才显示（「依赖图只在实施对应方案时显示」契约保持）；**拓扑下推**：`depStatuses` 渲染纯函数改两遍——第一遍逐节点查表（现状），第二遍任一节点收口 ⇒ 其 dependsOn 闭包（含传递）强制 done 且阶段置「收口」（栈迭代 + 已处理集合，环终止、悬空批次名跳过），`DepNode` 加 `phase` 字段供两处节点文本行取用（消除 ✓ 符号与「待执行」文本自相矛盾）；只修非末批漏报，视图修正不改写持久化数据。新增 `parseProgressMap` 纯函数（L1 四例：合法全收 / 整体非对象 null / 混值剔键 / 空对象合法）、`depStatuses` 下推四例（B2 收口推 B1、B3 链式传递、悬空引用不崩、末批漏报负断言）与三个 mount 用例（恢复-渲染往返、坏形状降级、拓扑下推渲染；store.get 替身按事件载荷的 key 字段分流）。双 manifest 同步升版 0.21.0。

- work-skills 2.5.0：新增 `sag` 技能（本地语义搜索）——迁自 SAG Wiki desktop CLI 装到 `~/.claude/skills/sag` 的全局副本，单一源归位本仓 plugins/work-skills/skills/sag/；剥离平台安装元数据（技能运行不需要，且会诱使 SAG 桌面版把仓库目录当安装点）；frontmatter 中文化 description 补触发词并加 metadata.source 记录上游来源（canonical 源 Zleap-AI/SAG-Wiki cli/skills/sag，正文保留英文原文以便与上游 diff 同步）；三个 references（setup/parameters/ignores）原样迁移，无本机特定路径。当晚 SAG 桌面版自动重装了一份更新版全局副本（SKILL.md 新增 Check time/revisions/scope 证据核对节，references 零变化，且新版不再带 .sag-install.json 标记），已二次同步正文并再删全局副本；SAG 桌面版无禁用自动安装的 CLI 配置项，后续若再自动重装按同法同步或直接删。codex manifest longDescription 22→23 个技能并补 sag，capabilities 加 Search。双 manifest 同步升版 2.5.0。

- work-skills 2.4.0：deep-research 0.7.0 搜索通道扩展，新增 product 通道接入 Product Hunt——通道入口为新技能 `sn-search-producthunt`（Bash 脚本直调官方 MCP 端点，匿名 JSON-RPC 无需 OAuth/key，只封装上游 7 个只读工具而非注册 17 工具全量常驻（含写操作）的 MCP server，离线测试 33/33）；deep-research 侧五文档位加法接线：搜索通道映射表加 product 行 + 子工具选择（子命令按 query 语义选：search/semantic/alternatives/profile/category/leaderboard/categories，契约单一出处 sn-search-producthunt/SKILL.md 不复制）、normalize 映射补「输出已含 source_type:"product"，items[] 直接入 search_results」、实现说明表与多源 prose 升 6 通道并同步降级枚举；query 节点 source_type 枚举与选择指南加 product，选择原则补数据边界（maker 自报默认 source_tier: secondary、关键事实需与 web/academic 交叉验证，榜单≠竞品全集、竞品发现优先 alternatives/semantic）；搜索层活文档 SEARCH_MIGRATION.md 追加 v0.7.0 节（数据边界与匿名访问可能收紧，收紧时脚本 success:false 由既有降级规则兜底）。双 manifest 同步升版 2.4.0。

- agent-skills 1.5.0：新增 `jev-agent-design`，沿 awesome-jev-hub 及社区精选清单追溯原项目，整理动作循环、浏览器、模型与技能路由、事件唤醒、上下文压缩、检索验证、权限门控和 MCP 判断工具；结合用户文章与无人机/驾驶仿真原项目，补充分层时间契约、状态可观测性和遥感低空试点假设；新增跨案例设计哲学、风险退路对比与决策卡，附故障处理和评测指南，区分项目自述、局部源码核验及待验证建议。同步双 manifest、marketplace 描述和 README。

- agent-skills 1.4.0：agent-retrieval 技能同步检索库 0.2.0（judge 端口收编 + Jev 题型实验线终局 #13/#14/#15）——新增 `references/judges.md`（Judge 端口族编排：exact 短路留调用方、`select_with_judge` 弃权语义与无默认门槛、JevJudge/ChatJudge 并列实现取舍、候选投影单一出处（name+description 截 2000 字符，tags/use_when/avoid_when 不进判定输入）、判定链 fail-fast 不降级与嵌入链 fail-open 的刻意不对称、排查分类表）；L4 Jev 精排题型两档并存终局写入 SKILL.md 路由表与 config-selection（noul 默认维持硬 recall 下限场景 / score 量规 P(3) 折叠供分级排序消费处——三独立样本 NDCG@10 +0.028/+0.030/+0.042 CI 下界全正无衰减、~1.4× input tokens；机制结论排序信息几乎全在第 3 档——期望折叠稀释、P(≥2) 主动有害 −0.05；准入红线：判定读数不得单独作准入闸，端点对纯问候语稳定 P(3)=0.96 三连复现；量化噪声背景 0.01 量化 + 同臂抖动 0.02–0.05）；CorpusProjection 声明式投影写入 ranking-api（双形态条款、doc2query-- 分离钩子）；docgen 库内一等客户端写入 config-selection（DocGenClient/build_docgen/docgen_corpus_text、identity 未接入 corpus_hash 的接线口径、推理模型关思考参数已固化）；消融验证流程补 `agent_retrieval.stats` 库内出口（paired_report 参数冻结 10k 重采样/种子 20261022/CI95）；安装矩阵补 `[judge]`/`[docgen]`/`[all]` 与 GitHub Release wheel 直装通道（PyPI trusted publisher 待修）、core-concepts 分层架构表加 judges/expansion/stats 三行、API 总览 37→48 符号、SKILL.md 触发词补 Judge 端口/ChatJudge/P(3)/题型。双 manifest 同步升版 1.4.0。

- flow-deck 0.20.0：文件查看器全文视图「复制全文」按钮——引擎无原生剪贴板 API，经 `$.process.run` 调平台剪贴板命令、全文走 stdin 管道（UTF-8）：Windows 用 PowerShell 显式设输入编码后 `Set-Clipboard -Value ([Console]::In.ReadToEnd())`（实测两处坑：clip.exe 被 OEM 代码页误解码 UTF-8 中文、`$Input` 逐行管道把行尾归一成 CRLF，故用 ReadToEnd 单串保真口径），macOS 用 `pbcopy`，Linux 用 `xclip`（不做 wl-copy 回退，缺命令时失败 toast 报错）；引擎沙箱无 `process` 全局（实测 ReferenceError），平台经 `$.env.get('OS'/'HOME')` 字面量读取 + `envPlatform` 纯函数推断（Windows_NT 恒判 win，HOME 前缀判 mac/linux，未知判未适配），未适配平台、非零退出、命令缺失统一 toast 反馈、细节进调试日志；复制内容为面板装载的 doc.text 原文（非重读盘、非渲染增强文本）。无热键低密度按钮（0.16.3 分治约定，不加 plain）。新增 `clipboardArgv`/`envPlatform` 纯函数（平台命令表 + 环境变量推断）与四条用例（纯函数两例 + mount 用例：成功 stdin 断言、非零退出、命令抛异常）与 diff 视图负断言。双 manifest 同步升版 0.20.0。

- work-skills 2.3.2：brainstorm 回报收敛——收尾回复以最终产出开头并为主体（深钻=核心洞察置顶、创意=设计卡、扩散=分支清单/交接概览），执行过程（钻探计划、下钻链、透镜轮换、盘点/解构/筛选记录）默认压缩为一行摘要不铺陈，用户说"看过程"再展开（统一原则写入 SKILL.md 共享规则，三手册引用）；深钻输出格式洞察置顶、五场景产出行明确"一行附注"口径、被证伪路径保留在过程叙述中；创意产出卡五要素改四件套（关联路径+合理点合并为一行"成立依据"，生效条件逐条核对照常执行只报结论），示例卡与边界定义同步；evals 1/7 改写、2/3/4/5 微调为"一句话论证"口径。只改回报形态，执行流程不动：深度四问照答、创意五步照走、双轴筛选照做、试金石与外部验证方式必填不放松。双 manifest 同步升版 2.3.2。

- flow-deck 0.19.0：变更对比视图 + 文件查看器地址输入栏 + GitHub Issues 区块（方案 `plans/flow-deck/2026-11-06-deck-diff-view-and-doc-input.md` B1 批）——**变更对比视图**：文件树页签「改动」清单的 git 变更文件（conflict/staged/unstaged/untracked）点击后装载 diff 而非全文（复用文件查看器，`doc.kind='diff'` 契约加法扩展）：tracked 走 `git diff HEAD` 合并口径（unborn HEAD 退工作区口径），untracked 走 `--no-index` 全 + 视图，两级命令均失败退全文（不产生死视图）；渲染用引擎 `Code format='diff'` 原生增删着色（不自写行分类），不截断；diff 视图不绘制节导航与「发给 Claude」，给「重读变更」（r）；全文视图对变更清单内的文件加「查看变更」按钮（渲染时重算 `collectChanges`，小写折叠匹配）双向闭环；state=null 的仅本会话记录行保持原文不变。**地址输入栏**：文件查看器空态由纯提示改为 `Input` 输入栏（autoFocus），submit 有效路径装载（路径经 cwd 归一化，不做存在性预检——读取失败既有错误视图即反馈），空白输入忽略。**GitHub Issues 区块**：工作面板尾部列当前仓库 open issue（`gh issue list --state open --limit 20 --json`，repo 由 gh 自动推断），条目含 #号+标题（OSC 8 链接）与 dim 标签行；`ghIssues` 状态契约加法扩展，60s 独立轮询且仅面板可见时拉取（不随 2s 主轮询），「刷新」按钮随拉，失败（gh 不在/非 GitHub 仓库/解析失败）区块整体静默，空列表显示「无 open issue」；新增 `parseGhIssues` 纯函数（L1 四例）。L2 新增 9 个 mount 用例（diff 装载/兜底/双向闭环、输入栏、Issues 三态）。双 manifest 同步升版 0.19.0。

- flow-deck 0.18.1 补录：驻场小生物重设计为顶部驻场猫——真机目检发现行尾盲文挂件（2×4 列 dimColor）感知不可见，经两轮迭代与四方案比选定稿面板顶部独立驻场区 3-4 行字符画（耳/脸/爪/尾动画语言，普通前景色），删除两处行尾挂件，加大各态两帧动作幅度；帧表契约重写（每帧 3-4 行、显示列断言防宽字符、两帧整块不同），`companion=off` 与基线逐字一致的约束保持（提交 51ac5c9，发布时未写 CHANGELOG，补录）。

- flow-deck 0.18.0 补录：收口仪式通关卡、控制台皮肤、呼吸面板与驻场小生物——全绿收口后空态渲染通关卡战报（声明边界文件数、numstat 逐文件 ±行数、耗时自首次边界声明起算，统计不可用显示 — 与真实 0 可区分，重复收口幂等保留；numstat 解析贯通到逐文件并区分每侧查询状态，session.start 代次门拦截旧会话在途 git 快照）；800ms 节拍器驱动执行卡两档呼吸、停滞停跳；`artDirection` 配置切换飞行控制台词表皮肤（只换文案不改结构）；`companion=off` 关闭小生物（提交 fa773e5，发布时未写 CHANGELOG，补录）。

- flow-deck 0.17.0：工作面板方案名点击直达文件查看器 + 主色调改蓝——标题行、当前执行行与 plan-iterate 评审卡的方案名改为可点击（`plain` 按钮 + 方案名下划线，沿 0.16.3 整行链接约定），点击装载方案文档并切到文件查看器页签：优先取评审目录 `state.json` 的 `plan_path`（新增 `PlanReview.docPath` 契约，绝对路径经 cwd 归一化），implement 任务常无评审目录，退而按仓库约定即时扫 `plans/<插件>/<方案名>.md`，两处皆无时 toast 说明不切页签。主色调 `TONE.accent` 由 `claude`（橙）改为 `professionalBlue`（蓝，面板标题/flow 前缀/执行卡边框/DAG 总览/tLevel chip 底色等全量跟随）；子代理区新增 `TONE.agent = 'claude'` 语义色保留与 Claude Code 子代理展示一致的橙（运行中状态行与卡片边框不跟随主色变化）。双 manifest 同步升版 0.17.0。

- flow-deck 0.16.3：按钮与文本的视觉区分（分治策略）——无热键的低密度操作按钮（子代理「查看」、「全文」「‹ 上一节」「下一节 ›」与分页数字、「← 上级」、「主对话」）去掉 `plain`，终端画成 `[ label ]` 括号样式；文件树高密度整行按钮（改动清单、目录行、文件行）保持 `plain` 但主名（路径/文件名/目录名）加下划线（改动行的状态点 `●`/`○` 不下划线）。带热键的按钮（`r: 刷新` 等）与页签行（亮暗对比选中态）维持原样。顺手补齐 codex manifest 漏升的 0.16.2。双 manifest 同步升版 0.16.3。

- work-skills 2.3.1：deep-research 0.6.1 深读层引入 alphaXiv 增强——3.2b 新增两个公开端点（无需 key、不动五通道搜索与既有降级规则）：`alphaxiv.org/abs/{id}` AI paper blog（web-reader 抓取，作 deepxiv 渐进精读前置导读，快速筛选省额度）与 `/abs/{id}.md` 论文全文 markdown（curl 直取，作 deepxiv paper 降级备选，深读降级链扩为 deepxiv paper → alphaXiv .md → arXiv 原页）；交叉验证明确 AI blog 与论文同源、只作理解校验不计入独立来源；社区讨论区为 SPA 抓取不可靠，仅附链接人工浏览。双 manifest 同步升版 2.3.1。

- flow-deck 0.16.0：文件查看器 markdown 图表增强——表格重排为等宽对齐的 Unicode 表格（CJK 按 2 列计宽），mermaid `graph TD` 基本子集（节点与箭头链，含链式声明）自绘为 Unicode 分层流程图（box-drawing 框线 + ▼ 箭头，分层固定点收敛，环内节点保持原层；classDef/style/subgraph 等不支持的语法整体保持代码块原样），`enhanceMarkdown` 管道在渲染前预处理（fenced code 内不处理）。双 manifest 同步升版 0.16.0。

- flow-deck 0.15.0：页签改名与文件查看器浏览交互改造——三个页签更名（工作流→工作面板、文件→文件树、文档→文件查看器，页内标题/返回文案/README 同步）；文件查看器的「浏览」从 Select 下拉改为横向平铺按钮行（「全文」+ 各节标题，flexWrap 自动换行，当前项亮/其余暗），与页签行同款交互；「发给 Claude」与「重读」按钮之间加宽松间距。双 manifest 同步升版 0.15.0。

- flow-deck 0.14.2：文件页签目录导航改为点击交互——目录行直接点击进入（原 Select 下拉在侧边栏里难以操作，已移除），非根目录显示「← 上级」按钮逐级返回。双 manifest 同步升版 0.14.2。

- flow-deck 0.14.1：工作流页签的「刷新」按钮与「▍子代理」标题文本之间加宽松间距（gap 2），与页签行口径一致。双 manifest 同步升版 0.14.1。

- flow-deck 0.14.0：文档页签默认全文模式——修复「点开文件只看到第一节 1–2 行」的阅读体验问题（多数文档第一节是标题/引言，天然很短）。装载文档默认渲染整篇（引擎 Markdown 样式，超 400 行截断，Pane 内可滚动）；「浏览」下拉首项「全文」、选节切单节模式（单节超 60 行截断）。`e` 的修改请求按模式分流锚定：全文模式填「请修改 <路径> 文件：」，单节模式保持「请修改 <路径> 的「<节标题>」一节（第 a–b 行）」。新增 `docMode` 状态契约与 `DOC_ALL_MAX_LINES` 常量。双 manifest 同步升版 0.14.0。

- flow-deck 0.13.0：文件页签点击直达文档——「改动」清单与「目录」区的文件行改为可点击（plain Button），点击即切到文档页签并装载该文件（目录行保持纯文本，进目录仍走 Select）；页签行加宽松间距（gap 2）。`openInDoc` 辅助函数复用 loadDoc 与页签切换。双 manifest 同步升版 0.13.0。

- flow-deck 0.12.0：视线常驻与交互深度（方案 B6/B7 批，参照官方 diff 面板范式）——**自动侧边栏**：全屏布局下 agent 首次编辑文件时面板自动打开（不抢键盘焦点；用户手动开关过面板则本会话不再自动开；`autoOpen` 配置默认 on）；**Spinner 行**：实施中重写为 `批次 · 阶段 · 验证 x/y`、迭代中 `评审 R{n} · 分数`、无任务时报运行中的子代理，无话可说透传引擎原样；**Edit/Write 工具行**批次合规标注（界内 `◆` / 越界放行 `⚠ 越界` / 拦截 `✗ 拦截`，ctrl+o 展开态透传）；**输入框守卫预览**：实施中有边界时草稿路径 token 实时标色（界内绿/越界黄下划线），守卫提前到打字时可见；**子代理「查看」按钮**把主视图切到该代理的实时输出（`$.ui.view`，deny 时 toast 说明），页签行加「主对话」按钮；**后台任务完成通知行**显示状态点、名称与耗时。新增 `spinnerWord`/`toolMark`/`draftDecorations`/`humanDuration` 纯函数（L1 覆盖），重写逻辑不经 mount 测试（测试引擎对透传分支无链底），自动开栏正向路径与 prompt.paint 参数捕获亦不经自动化测试——渲染观感与上述路径以真机目检为准。双 manifest 同步升版 0.12.0。

- flow-deck 0.11.0：`/deck` 统一命令与面板页签化（方案 B5 批）——五个命令收敛为一个 `/deck`（无参开关并保持页签，`/deck flow|tree|doc [路径]` 直达页签），`/flow` `/git` `/flow-agents` `/doc` `/tree` 全部退役；单一面板顶部页签行（数字热键 1/2/3 切换，Esc 回输入框，打开即持焦）；`/git` 与 `/tree` 合并为文件页签——git 头行 + 统一改动清单（git 改动 ∪ 本会话记录，`●` 本会话 / `○` 其他 / `◆ 本批` 边界标注）+ 目录浏览，原四分区退役。工作流与文档页签内容不变。新增 `collectChanges` 合并排序纯函数（会话组在前、冲突优先、路径字典序，路径小写折叠去重）与 `activeTab` 状态契约。双 manifest 同步升版 0.11.0。

- flow-deck 0.10.0：界面深度原生重构（方案 `plans/flow-deck/2026-11-01-native-ui-redesign.md`，四批）——全部界面颜色从 ANSI 字面量迁移到引擎主题语义 key（`claude`/`success`/`warning`/`error`/`diffAdded`/`diffRemoved`，随 `/theme` 与换肤 mod 自动适配），符号表一词一义化（`▍` 标题、`●` 进行中、`○` 非活动，killed 由 `■` 并入 `○`），面板标题改版（`FLOW /` → `▍工作流 ·` 等）。新增两件标志可视化：执行 DAG 流水线总览条（节点+连线按下游状态着色）与评审达标刻度条（十格条内固定 `▏` 8.5 达标线）；执行卡风险定级改反色 chip（accent 底）；/doc「发给 Claude」升 primary 按钮、节内容改引擎 Markdown 渲染（标题/列表/代码块与回复同源，双表面校验通过）、节标题去 `#` 前缀统一 `▍`；评审卡与子代理卡常态暗边框、悬停提亮（全屏终端渐进增强）。新增 `/tree` 文件树面板：本会话改动清单实时记录 Edit/Write（去重保序上限 50，warn 放行同样记录），叠加 git 状态标注与批次边界 `◆ 本批` 标注，目录 Select 导航按需读取无轮询。修复 0.9.0 遗留的 `doc`/`docSection` 状态契约缺失（validate 报错）。双 manifest 同步升版 0.10.0。


- work-skills 2.2.0：新增 `writing-for-human`（面向人类读者的写作、改稿与审阅——先写意思、段落主线、短而完整、解释抽象词、模板句式服务于完整意思，附写作细则与校准示例两份参考文档）；自 evoCenter 项目技能收编，细则文件与引用去「仓库」化，保留 `agents/openai.yaml` 宿主接口元数据（screen-condense 同款先例）。README 技能清单同步为 22 个。双 manifest 同步升版。

- flow-deck 0.9.0 补录：`/doc` 文档浏览面板——按 markdown 标题分节（Select 选节，节超 60 行截断），按 `e` 把「请修改 <路径> 的「<节标题>」一节（第 a–b 行）」草稿填入输入框，人补完意图后走正常 Edit/Write 链路，批次边界守卫继续生效；面板只读定位不落盘。Codex manifest 版本上版漏更，本次补对齐 0.9.0。

- rulertu-flow 2.7.0：optimization-plan 新增「批次粒度」节——按上下文流向划界的一句话原则（后批需要前批上下文则合并、批次独立性是质量来源则隔离、两者皆不涉及按 T 级分界），含隔离信号（基线先行、验证独立、并行互斥、爆炸半径、端到端真依赖）、连续信号（合并后 T 级就高、批内多锚点各自 TDD；仅消费接口的依赖归中性）、收尾分流（轻量收尾主控 T0 直做）与双自包含规模上限；波次收口已含全量回归，方案不再为纯验证立收口批。定稿前自审加第 6 条粒度审查，description 补「批次划分」触发分支。七份真实方案纸面重划验证（本仓库 2 份 + rhetra-harness 5 份）：合计 32→27 批（−16%），减批集中于小批密集型方案（copyright 7→4、dual-model 3→2、protocol-defect-fix 5→4），四个大型 T2/T3 工程方案粒度饱和保持原样——下界保护成立；扩展测试暴露并修正三处判据（接口依赖误判连续、收尾文件数判据机械、隔离信号漏端到端真依赖）。推导记录见 `docs/2026-10-29-batch-granularity.md`。双 manifest 同步升版。


- work-skills 2.1.0：`work-summary` 增加全局工作区、跨周期总结复用及团队模式；分别检查时间和主题覆盖，保留证据、状态、指标口径与资料缺口。新增工作区配置、候选发现和防覆盖输出脚本及针对性测试，双 manifest 同步升版。

- work-skills 2.0.0：`weekly-report` 更名为 `work-summary`（旧调用名需迁移），支持日度、周度、月度、季度、半年度、年度和自定义周期。新增分窗口采集、分尺度融合与证据回查；采集器支持显式起止时间及左闭右开边界，修复数据源缺失时的返回值。双 manifest 同步升版。

- rulertu-flow 2.6.0：commit/pr 技能内联路由——description 与正文新增「触发与提醒」节，写明两个触发场景（会话内任何 `git commit`、PR 创建或更新的文案先经技能起草；完成其他任务需要提交时主动提醒）；implement-plan 波次收口与 optimization-plan 方案定稿环节挂技能指针。新增 PreToolUse 提交守卫 hook（`hooks/commit-router.js`）：识别 `git commit` 与 `gh pr create/edit`，transcript 未见对应技能加载时经 `additionalContext` 向模型提醒一次，已加载或已提醒过则静默，任何异常 fail-open 放行不拦截；附命令识别与判定测试（`node --test hooks/`）。
- agent-skills 1.3.0：新增 `proactive-agent-design`，提供主动型 Agent 的 6A 架构设计、评审诊断和主动行为评测三个入口，含设计九问、六环知识卡、边界与领域卡、四份交付模板及来源校准记录。校准 Awareness 运行时架构和三层评测图号，保留【导读】【共创】分级；双 manifest 同步升版，README 技能清单补齐现有 `rhetra` 后共 8 个。

- work-skills 1.4.0：新增 `article-guide`（文章互动导读——选项式确定熟悉度与学习目标、知识地图与推荐路线、分块讲解与讨论、按需搜索延展、学习笔记与续学断点），附笔记与续学约定参考文档；根 README 技能清单同步为 20 个。双 manifest 版本对齐 1.4.0。

- flow-deck 0.8.1：批次守卫 warn 提醒降噪——文案附触发工具名（Edit/Write）并去掉与宿主渲染前缀重复的"flow-deck："字样；越界提醒按归一化路径去重，同批同文件（含跨 Edit/Write）只提醒一次，`flow_batch` 重新声明边界或新会话时重置去重。deny 拦截不去重，每次越界照常拦截。新增 warn 去重与重置及 key 归一化测试。

- flow-deck 0.8.0：`/flow-agents` 独立面板并入工作流面板（引擎多面板为标签页模型，同刻仅显示一个）——子代理状态作为常驻区块画进 `/flow` 面板，无任务时同样可见，`/flow-agents` 改为幂等打开该面板（已开不误关），仅面板打开时维持 2 秒子代理查询。执行阶段轨迹改为极简进度条（比例条 + 当前阶段名与序号，不再罗列全部阶段名）；执行 DAG 新增按批着色的分段总览条（■ 收口 / ▣ 进行 / □ 待执行）叠加原依赖树。新增实施停滞提示（上报超 30 分钟未续报显示"疑似停滞"与间隔分钟数，状态变化才写避免无谓重绘）、空态面包屑（无任务时显示跨会话恢复的上次执行摘要）、达标评审折叠为一行（未达标照常逐个展示）、面板内 `r` 热键刷新按钮（子代理区块标题行，重取评审/git/子代理全部数据）。新增阶段进度、DAG 分色、折叠、停滞、刷新按钮与面板合并迁移测试。

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
