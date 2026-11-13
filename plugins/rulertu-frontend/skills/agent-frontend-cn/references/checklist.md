# 交付前检查清单与翻车模式对照

## 一、交付前检查清单

逐项过，任何一项答不上来就是缺口。

### 事件流

- [ ] 同一帧到达两次（SSE 重连/重放），界面会不会翻倍或叠行？
- [ ] 从非 0 游标接入（刷新后续订），漏掉的前置帧有没有补齐路径（如工具回执补行）？
- [ ] 事件 JSON 畸形时是炸流、静默吞，还是 warn 后跳过？
- [ ] 终态判定：新增一种后端终态，前端会误判成"仍在跑"还是误判成"已完成"？（应倾向前者）
- [ ] interrupt 后流有没有自动续接？被动标签页能否看到别处发起的恢复？
- [ ] 断网重连上限、退避、4xx 不重试都定了吗？

### 一致性（金标准：刷新前后一致）

- [ ] 跑完一轮后，读回替换发生前后的内容逐字一致吗？
- [ ] 读回与并发提交赛跑：旧请求的读回会不会落到新请求的消息上（序号对账）？
- [ ] 消息里塞了任何"仅运行期存在"的信息（标签、拼接文本）吗？刷新后会消失或错位吗？
- [ ] 附件 chips：运行期 references 与后端落库的同一份同形吗？
- [ ] 侧栏标题：占位、权威值、title_source 三者的覆盖规则，刷新前后同一副面孔吗？

### 并发与生命周期

- [ ] 多会话/多卡片并发：流式标志、AbortController、计时器、心跳是否全部 per-key？全局单例会互相顶掉。
- [ ] 会话删除后，在途回调与 SSE 尾事件有没有墓碑拦截？
- [ ] 组件卸载后，残留 timer 会不会对已卸载组件 setState？
- [ ] 回放与实时互斥了吗？执行中的会话能发起回放吗？

### HITL

- [ ] 审批卡载荷畸形时有没有兜底卡（批准/拒绝），而不是白屏？
- [ ] 提交审批后输入区状态机是否完整走完（提交中→续流→运行态）？
- [ ] waiting_human 的工具调用显示为"等人批准"而非"失败"？
- [ ] 取消请求失败时用户能看到警告吗？

### 历史与还原

- [ ] 历史载入与实时投影走同一个帧翻译、同一套展示集谓词吗？
- [ ] 续页游标有"游标必须变化 + 页数上限"双保险吗？
- [ ] 还原快照与事件路径共用终态映射吗？paused 还原出来 running=false 吗？
- [ ] 还原视图 live=false；续订起点用快照的 event_cursor 吗？
- [ ] 取消态快照把 pending 补投影成 skipped（区分两种 reason）了吗？
- [ ] 重产物（终稿/节点详情）是否懒加载 + inflight 去重 + 会话切走丢弃？
- [ ] 新建会话前插封顶后，与刷新后重新拉首页逐项一致吗？
- [ ] 删除会话：流/计时器/心跳/游标/store key 全清 + 墓碑拦迟到写入？
- [ ] 占位标题规则在起跑与历史回填两处逐字同源吗？

### 渲染细节

- [ ] 文本截断按 Unicode 码点切分了吗（`Array.from`，不是 `.slice`）？
- [ ] 流式转历史时，思考块展开态、key 会不会残留？
- [ ] 相邻 text chunk 合并了吗（避免上千个 Markdown 实例）？
- [ ] 用户上滚后流式输出还会强行拽底吗？

## 二、常见翻车模式 → 解法对照

| 翻车现象 | 根因 | 解法 |
|---|---|---|
| 跑完只有一句"调度完成"，刷新后凭空多出整篇正文 | 运行期气泡没在终态读回替换 | 终态事件触发窄读回，整轮换权威版本 |
| 跑完看到的和刷新后不一样 | 实时/历史两套映射各写一份 | 唯一 `frameToMessage`；chunk 只做预览，完整帧为准 |
| 一张卡在跑，别的卡发不出消息 | 全局 streaming 单 boolean | per-session Map |
| 澄清答完，卡还挂着 / 消息错轮 | 读回覆盖了新请求的消息 | 请求序号对账 + unclaimed 认领标记 |
| 用户正要批的工具调用显示红色失败 | waiting_human 与 failed 合流 | 工具状态三态变四态 |
| 取消后界面"已终止"，后台还在烧 token | 断流后收不到终态事件，且取消请求失败被吞 | HTTP 旁路取消 + 失败警告 + 409 安全回读 |
| 条件分支刚说完"不会走"又变回"等着跑" | 终态集合漏了 skipped，投影把它复活 | FINISHED 含 done/failed/cancelled/skipped |
| 新一轮开跑，上一轮的排队/升级提示还挂着 | 提示只置不清 | 起跑帧 + 终态帧双层清除 |
| 回放能看，实时渲染不出来 | 回放与实时两段投影代码 | 纯函数 reducer，三路共用 |
| emoji 标题/chips 乱码 | 按 code unit 截断 | `Array.from` 按码点切 |
| node 消息把循环中间轮当成节点完成 | 内容帧与状态帧职责不分 | 帧只给内容，状态由 STEP_FINISHED/iteration 翻 |
| 刷新后条件分支从"不会走"变回"待执行" | 快照还原漏 skipped 档 | 快照 status 映射含 skipped；取消态补投影 |
| 切回历史轮，上一轮的图/终稿消失 | 每会话只有一份 Run 视图 | 轮次视图 byRun 存档 |
| 删除的会话又"复活" | 在途回调重建了 map | 删除时全量清理 + 墓碑集合拦迟到写入 |
| 续页历史漏显轮间消息 | 只取了首页跨轮消息 | 沿 next_message_cursor 续页，去重重排 |

## 三、事件语义速查（AG-UI 形态，按 harness 映射）

以 AG-UI 事件名为准，其它 harness 对应到同语义即可：

| 事件 | 语义 | 前端职责 |
|---|---|---|
| RUN_STARTED / run.executing / run.resumed | 真起跑 | 清排队/锁提示；恢复运行态 |
| TEXT_MESSAGE_CHUNK | 正文增量 | 合并追加 + 状态气泡预览 |
| REASONING_MESSAGE_CHUNK | 思考增量 | 追加 thinking |
| TOOL_CALL_CHUNK / TOOL_CALL_RESULT | 工具开始/回执 | 交错流行；按 id 配对去重；四态 |
| STEP_STARTED / STEP_FINISHED | 节点起止 | 翻节点状态；收口后推进就绪集 |
| STATE_DELTA | 权威状态补丁 | 消费 skipped 投影；running 节点不可被 skip 覆盖 |
| *.message（完整帧） | 阶段收口一次性内容 | upsert 落消息/节点，**不拼 chunk** |
| RUN_FINISHED (interrupt) | HITL 中断 | 置 waiting_human、渲染卡、保持 live |
| RUN_FINISHED / RUN_ERROR | 终态 | 读回、收口、关流、停心跳 |
| run.queued / run.escalated / asset.lock.* | 非终态提示 | 幂等置位；起跑清；终态兜底清 |
| route.selected / result.ready（带判别键） | 请求族事件 | 族判别靠 payload `mode`；result.ready 是唯一 final 锚点 |

## 四、本方法论的代码形态参考

提炼源：调度型 agent 前端（React + TS + Zustand + Vite + SCSS Modules）。若在同类仓库中工作，可按此文件地图找同类物：

- 事件 reducer（纯函数、三路共用）：`stores/requestEvents.ts`
- 事件大分派 + Run 视图：`stores/runs.ts`（start/resumeLive/abort/decideApproval 全生命周期）
- 消息 store 与读回对账：`stores/chat.ts`（requestSeqs/turnReloadSeqs/unclaimed）
- 帧翻译唯一处：`utils/messageFrame.ts`
- SSE 传输：`api/client.ts` 的 `streamResponseEvents`
- 卡片：`components/chat/` 下 ApprovalCard / ClarificationCard / DataCard + 各自 `*Metadata.ts` 解析器
- 工具渲染器注册表：`components/chat/tools/`
- 回放：`stores/replay.ts`
- 轮次布局：`hooks/useTurnLayout.ts`
- 会话列表/历史加载/读回：`stores/chat.ts`（loadSessions/loadMoreSessions/loadSessionHistory）
- 快照还原：`stores/runs.ts` 的 `responseToSnapshot`、`restoreSessionSnapshot`、`openHistoryRun`
- 执行面：`components/runs/`（RunSidePanel / DagGraph / BlocksRenderer / ChartRenderer）
- 搜索/导出/连接状态：`hooks/useMessageSearch.ts`、`utils/exportMarkdown.ts`、`utils/exportHtml.ts`、`hooks/useConnectionStatus.ts`

不在该仓库时，按语义对号入座，不按文件名。
