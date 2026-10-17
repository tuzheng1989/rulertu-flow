# flow-deck

Claude Code 的工作流与 Git 状态面板。Codex manifest 仅提供占位元数据。

安装：`/plugin install flow-deck --marketplace tuzheng1989/rulertu-flow`。

- `/flow` 开关工作流面板：方案总览、评分与分差、P0/P1/P2、执行阶段和验证进度、批次依赖与收口进度。未达标方案优先展示。
- `/git` 开关仓库面板：分支与上下游差异、行数变化、冲突及暂存/未暂存/未跟踪文件；每类最多展示 15 条，长路径保留两端。
- 输入区上方最多占两行，遵守宿主可用行数；仅容一行时冲突优先，其次当前执行。达标评审仍从 statusline 撤下，通过 toast 通知。

使用 `flow_report`、`flow_batch`、`flow_deps` 上报的数据会直接更新界面，无动画计时器或新增依赖。终端与桌面共用 Text / Box，窄于 44 列时去掉卡片边框。

轮询开销与时效：

| 数据 | 刷新策略 |
| --- | --- |
| 已知评审目录 | 每 2 秒列目录；文件名、大小与修改时间不变时复用解析结果 |
| 新 `.plan-iterate` 根目录 | 启动时发现，此后每 30 秒搜索，最多四层；跳过依赖、构建目录 |
| Git 有文件改动 | 每 5 秒查询 status，仅对有 tracked 改动的一侧查询 diff 行数 |
| Git 无文件改动 | 每 15 秒仅查询 status；无上游偏差时隐藏横条 |
| 非仓库或 Git 查询失败 | 每 60 秒重试；打开 `/git` 会立即异步重查 |

相同快照不重复写插件状态；定时轮询与手动刷新共享防重入查询。以稳定干净仓库计算，Git 调用由每分钟约 60 次降至 4 次；这是调用次数估算，实际 CPU / I/O 取决于仓库规模。新评审根目录的首次展示可能延迟至 30 秒。

验证：`claude plugin test plugins/flow-deck`、`claude plugin validate plugins/flow-deck`（从仓库根运行）。测试覆盖缓存、发现延迟、文件变化、Git 分侧查询、退避与防重入，以及终端/桌面宽窄面板的渲染树；实际宿主绘制仍需在 Claude Code 中查看。
