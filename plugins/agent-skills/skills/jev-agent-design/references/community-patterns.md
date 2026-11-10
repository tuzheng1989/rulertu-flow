# 社区设计案例

检索时间：2026-11-10。入口为 [awesome-jev-hub](https://github.com/supermanc417-alt/awesome-jev-hub) 及其社区精选清单：其中 [v-modal](https://github.com/v-modal/awesome-jev-tools) 引出权限、检索与路由案例，[Anil-matcha](https://github.com/Anil-matcha/awesome-jev-by-typesafe) 引出唤醒与模型协作案例，[heyjunpenn](https://github.com/heyjunpenn/awesome-jev) 用于发现其他 Agent 工具。清单是发现入口，不是互相独立的验证。以下是有选择的案例，不是全目录审计。标注「源码核验」表示只阅读了所链接的局部代码，其他机制来自项目 README 的自述；均未运行或独立复现。链接指向可变化的分支，实施前复核。

## 有限动作循环

**[SystemOneHarness](https://github.com/HarnessRouter/SystemOneHarness)**（README）：环境声明有限动作和参数，harness 将观察编译成类型化问题，每步按动作风险与概率门控、执行并记录状态/分布/结果。结束区分 completed、incomplete、failed、cancelled。它是闭环控制器，不要求生成可执行代码。适合动作可枚举的环境；动态参数、错误状态和无合法动作仍由宿主定义。按自己的数据标定不同动作阈值，不能照搬演示数值。

## 浏览器动作

**[browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast)**（README + [agent.py 局部源码](https://github.com/browser-use/jev-ultrafast/blob/main/jev_ultrafast/agent.py)）：观察生成带索引的元素表，单次请求同时选择操作和各操作的兼容目标，仅消费所选操作对应目标；文本输入时交给小 LLM。源码用页面 fingerprint 检查观察是否过期、消费决策防重复执行，重复无变化时停止。README 要求独立验证 DONE，并声明对 iframe、canvas 等能力有限。借鉴时区分「索引是本次观察的临时引用」和真实目标：变化后重新观察，执行前检查新鲜度。

**[jev-browser-use](https://github.com/wy-coliney/jev-browser-use)**（README）：把导航、点击、滚动交给 Jev，文本输入、视觉判断和最终检查交给 Codex。两个项目对文本生成的分工不同，选型应取决于任务能力与现有宿主；项目的速度声称不是跨场景保证。

## 具身仿真与实时控制

**[jev-drone](https://github.com/RomanSlack/jev-drone)**（README；[文章所链仓库](https://github.com/dajiaohuang/jev-drone)是其 fork）：MuJoCo 中 CV 将深度和分割结果压成扇区距离、障碍顶边及目标状态；Jev 回答动作 Choice、风险 Score 和目标是否丢失 Noul。项目将约 2.5 Hz 的战术建议与 50 Hz 安全反射、500 Hz 飞控分开，反射可以覆盖建议，爬升需满足代码检查。作者报告的整段通过仅一次，基线三次；早期三种子实验双方均未通过，不能据此断言总体优势。项目里「文本状态输入」是该仿真的用法，不应推断 Jev 始终无法处理图像。

**[typesafe-playground](https://github.com/kavehmz/typesafe-playground)**（README）：驾驶模拟用结构化仿真传感器状态供 Jev 判断，界面摄像机画面供人查看，机械运动由程序模拟。作者称其为可见错误的交互实验，而非真实自动驾驶或严格基准。不能把这两个仿真推断为真实无人机/车辆安全性；跨域方法见 [具身与实时决策](embodied-systems.md)。

## 模型路由

**[jev-codex-router](https://github.com/0xNatoshi/jev-codex-router)**（README + [回测说明](https://github.com/0xNatoshi/jev-codex-router/blob/main/BACKTEST.md)）：Jev 根据有界状态判断能力档位、思考深度与路由租期；代码结合策略覆盖结果。执行模型收到完整 canonical replay，路由器看到的是较小的决策投影；故障走预设路线，提供关闭开关与本地决策日志。其历史节省率属于旧策略模拟，不能作为当前线上实测。适合每次调用成本差异明显且可观察结果的系统；重点测复杂任务被低配的代价、路由开销及切换后上下文保真。

**[jev-agent-skill-router](https://github.com/GodsBoy/jev-agent-skill-router)**（README；经 v-modal 清单发现）：候选目录排序后分批并行选择，每批保留候选并递归收缩，再用 need、ambiguity 和 fit 等判断生成 `route`、`no_skill` 或 `review`；路由器本身不加载技能。最终概率以 shortlist 为条件。项目的 72 个合成请求结果经过同集迭代，不能说明生产准确率；分批裁剪可能错失正确候选，应评估各阶段召回、漏路由、误路由及审核负担。

## 事件唤醒

**[wakegate](https://github.com/shitianfang/wakegate)**（README；经 Anil-matcha 清单发现）：Agent 休眠时保留等待目标，事件到来后用目标、事件和可选新观察判断是否值得唤醒 LLM；用户消息直接唤醒，连续跳过达到上限强制唤醒，失败按项目的 fail-open 路径继续唤醒。具体调度周期由宿主负责。关键是对「漏掉重要事件」和「多调用一次 LLM」的代价做权衡；事件文本会发往选定服务。

## 检索生成的双侧判断

**[Cribrix](https://github.com/david96182/cribrix)**（README；经 v-modal 清单发现）：先检索，再对每个片段分别判断相关性、是否提供答案证据、是否疑似注入；不足时拒答。生成后按断言检查支撑，并用代码检查数字；区分无文档、证据不足、无支撑、生成失败和验证器不可用等状态。项目报告基于 62 条标注问题和已录制调用的回放，置信区间较宽，基线与新方案检索窗口不同；相关性或模型验证也不能保证证据真实或抵御注入。

## 权限与动作审核

**[pi-verdict](https://github.com/jesset/pi-verdict)**（README；经 v-modal 清单发现）：先由确定性硬规则处理明确情形，灰区可选 Jev 等分类器输出 allow / ask / deny；无法判断时关闭，非交互环境的 ask 变为 deny。项目明确权限门不是沙箱。实现前检查宿主的真实权限边界，不能将模型 allow 当用户授权或替代操作系统隔离。

**[jev-engineering](https://github.com/eugeniughelbur/jev-engineering)**（README；经 v-modal 清单发现）：先硬拒绝、再处理安全快路径、再对灰区提问并由代码应用阈值；支持仅观察模式。其失败回到宿主原有权限流程，不等于无条件允许。项目自测展示了冒充授权的攻击仍可能通过、高阈值带来较多误升级，属于特定测试范围内的作者报告；将对抗输入视为不可信数据并依靠独立权限和隔离。

## 上下文压缩

**[fast-jev-compaction](https://github.com/tamaratran/fast-jev-compaction)**（README）：按 `tool_use_id` 配对工具调用与结果，固定首条和近期消息；对每组分别判断保留调用、保留结果，再保留原文、截断结果或成对移除。用户和助手文本保留原文。状态装不下、返回不合规或服务出错时抛错，由调用者决定退路；大请求分批并重复发送状态。适合工具结果冗长的长会话，代价是可能丢失未来才需要的证据；应测回找能力和 token 成本，不把本地默认窗口/阈值当通用值。

## 检索与记忆

**[blink](https://github.com/ellipsis-dev/blink)**（README）：按文件/目录名评分，将 walkers 分配给更可能的路径并递归；保存每条路径决策、终点和状态。结果中的百分比是 walker 到达比例，不能自动解释成文件真正相关的概率。路径名不足以表达语义时可能漏召回，适合与内容搜索或其他召回并用。

**[hippo-memory](https://github.com/kitfunso/hippo-memory)**（README）：本地记忆检索后可选择性用 Jev 重排；项目报告某私有开发者语料排名改善，同时报告另一组实验的回答率没有优于本地 cross-encoder。远端重排会发送记忆文本。评估应分开召回、重排和最终回答质量，记录语料、隐私与成本，别把单一排名提升外推成整体任务收益。

## 完成验证

**[Canny](https://github.com/qkal/Canny)**（README + [Jev 接口局部源码](https://github.com/qkal/Canny/blob/main/src/jev.ts)）：账本记录文件修改、命令和退出结果；确定性规则据事实阻止缺少检查的完成声明，Jev 对语义判断提出建议而不单独阻断。请求按内容缓存以便复放，项目使用不确定区间；服务不可用仍保留确定性检查。借鉴时记录「最后修改之后」的验证证据，区分模型建议、客观失败及未执行；实际阈值与缓存失效规则需由目标系统决定。

## MCP 判断工具

**[jev-mcp](https://github.com/jkudish/jev-mcp)**（README）：将核验、筛选、查找、重排、分类、diff 评审等判断封装为 MCP 工具，返回类型化结果。调用方仍须判断候选来源、证据充分性和工具的实际语义；工具名中的 verify 或 gate 不是正确性保证。适合已有 MCP 宿主，实施前检查当前版本的工具契约和发送给服务的数据。
