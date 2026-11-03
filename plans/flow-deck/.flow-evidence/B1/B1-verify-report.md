# B1 主控机械验证报告（T1）

日期：2026-11-03 ｜ 验证人：主控（implement-plan T1 流程）

## 结论

**B1 通过收口。** Executor 回报与主控独立核验一致，全量测试两源全绿（Executor S7-full.log 与主控亲跑均 117 pass / 0 fail），差异范围严格限于声明的 8 文件，红线零违规。

## 机械验证清单

| # | 核验项 | 结果 |
|---|---|---|
| 1 | 差异范围：8 文件（types/parse/poll/register/plugin.json + 三测试文件），+1271/−39，探针文件无残留 | ✅ |
| 2 | 红线 3：poll.ts 仅 import 与 123/128 两行装配改动；查询命令、116 节流门、129-131 档位、133-137 防抖逐行零改动；guardDecision 零触碰 | ✅ |
| 3 | 条目 2a 代次门：`capturedGeneration = ++gitGeneration` 为 session.start 回调首句（无 await 先于一切异步）→ 清空 gitStatus → 重建 timer；publish 回调 `prev => capturedGeneration === gitGeneration ? status : prev` 比对与写入同回调（四交错时序逐一推演成立，含 update 已调用回调未执行场景） | ✅ |
| 4 | 条目 3 收口组装语句顺序：① firstReportAt 判 minutes → ② scope 前置校验 → ③ gitStatus 取数（null/byPath 缺失/任一侧 failed → 整体 null + statsAt 缺省）→ ④ 并入 stamped，先于 execution/progress 更新 | ✅ |
| 5 | 条目 4 清卡统一规则：四直接出口（flow_task 统一清、flow_report 非收口、flow_batch、session.start 重置）+ 收口三分支（写新卡 / 清卡 / 同 plan#batch 全绿重复经重放幂等保留）；重放后 stamped.closure = 现存卡 closure，lastRun（4b）与 store（995 行同一变量）无"无 closure stamped 覆盖两出口"通路 | ✅ |
| 6 | 条目 4 guardWarned 条件清理：flow_task 按 prevTask plan/batch 相等判定（含 idle 清）、flow_report 非收口分支异批清/同批不清（在 currentTask 更新前读旧值）、flow_batch 既有行为不动 | ✅ |
| 7 | 条目 4a parseExecution closure 透传：files 非法丢整个 closure；added/removed/minutes 缺省规范化 null；statsAt 可缺省 | ✅ |
| 8 | 条目 6 通关卡：独立装配分支（不经 selectTaskView）、graphMatches 判定、按各批实际状态着色（depStatuses）、本批节点 bold 高亮、全图 done 才全 done 色、plan 不匹配只渲染战报行 | ✅ |
| 9 | 条目 5 战报格式：null → `—` 与真实 0 可区分；minutes 注明"自首次边界声明"；files 注明"声明边界"；statsAt 附"统计截至 HH:MM" | ✅ |
| 10 | 条目 9 皮肤：五处点名文案切换（标题行 phase / 进度条与验证行 / DAG 标题 / 空态行 / 停滞提示），default 词表与现行文案逐字一致（基线回归前提） | ✅ |
| 11 | 红线 2：渲染层 ANSI 字面量色名 grep 零命中，TONE 取值 57 处 | ✅ |
| 12 | 测试证据：Executor S7-full.log 117/0 + 主控亲跑（b1-verify.log）117/0，退出码 0 | ✅ |
| 13 | 抽查测试断言质量：幂等重放测试经 state.set 拦截捕获真实写入、closure 逐字段 toEqual；guardWarned 测试走真实越界 warn 路径——无同义反复 | ✅ |

## 偏离与备注（Executor 声明 6 项，主控核附意见）

1. **代次门四交错测试未落地**（测试引擎不泵 session.start 内 `void tickGit()` 链的 process.run 替身事件，场景不可构造）：清空兜底半段已有"跨会话收口"测试覆盖；门禁半段实现已逐行核对正确。→ 留收尾批真机验证补强。
2. **首报 minutes 精确断言降级**（mock.clock 不操纵 Date.now）：三态写入分支 `if (!firstReportAt.has(key))` 已逐行核对，起点保留语义正确。
3. **store 出口断言移除**（测试引擎无 `$.store.set`）：实现上三出口同源 stamped 变量，代码路径正确；真机端到端留收尾批。
4. **mission-control 空态行复合文案** `待命 · 当前无方案迭代或实施任务。`：兼顾术语映射与既有断言子串匹配，主控认可（避免为文案改动扩散修改 4 处既有测试）。
5. **既有测试适配 2 处**（git 顶替改恒顶替、4 测试显式固定 default 皮肤）：因 B1 session.start 清空 gitStatus 使原"首写顶替"模式失效，适配合理。
6. **`SKIN_TERMS.score` 无渲染接线点**：现行渲染本无"评分"文案，词条备用非越界（映射外文案零改动已核）。

## 环境备注

- 基线 flaky（开工前已声明）：register.test.ts 重渲染测试负载下 timeout（既有问题，与本次改动无关）；本轮验证两源均未触发。
- 渲染树对比拆组③（companion=on 含小生物行）属 B2 范围，本批不适用。

## 产物

- 改动：未提交（路线图约定 B1+B2 完成后合并发布 0.18.0）
- 测试日志：S7-full.log（Executor）、b1-verify.log（主控，$CLAUDE_JOB_DIR/tmp，已核对一致）
