# flow-deck B2 批次（呼吸面板 + 驻场小生物）T2 独立审计报告

审计人：Auditor（opus 独立上下文）｜ 日期：2026-11-03 ｜ 主控复核：采纳

## 结论：PASS

B2 契约（帧三红线 + §B2 条目 1-5 + 验收 1-4 + 代码评审节点 4 项）全部满足，证据链真实自洽，独立复跑全绿。无 P0/P1。3 条 P2 记档不阻断。建议 B2 收口通过，进入收尾批。

## 审计清单逐项结果

**1. 红线 1（beat 写入点全集）— PASS**
全仓库 grep `beat`：写入点仅两处——`plugins/flow-deck/hooks/register.tsx:910`（session.start 重置 `update($, beat, () => 0)`）与 `register.tsx:1050`（beatTimer 回调翻转 `b => (b === 1 ? 0 : 1)`），与预期完全一致；`beat` atom 声明于 register.tsx:82、类型注册于 types/index.d.ts:207（`beat: 0 | 1`，PluginState 22 键全集中最后一键）。帧回调路径零写入其余 PluginState 键（回调体逐行见第 2 项）。定向测试 register.test.ts:1844（22 键快照拦截 + 预热后 2400ms 窗口 + 翻转序列独立期望 `[1,0,1]`，register.test.ts:1874-1876）设计成立，与主控抽查结论一致。

**2. 红线 2（回调逐行核对，含异常路径）— PASS**
register.tsx:1046-1059：① `$.ui.panes()`（1048，可见性判定，允许）；② `Array.isArray(panes) && panes.some(pane => pane.id === DECK_PANE_ID)`（1049，防御 + 判定）；③ `update($, beat, ...)`（1050，帧翻转，允许）；④ catch 内仅 `$.ui.log(..., { to: 'debug' })`（1054，内嵌 try/catch 防日志设施不可用）。无 git / `$.agent.list` / `$.fs.*` / `$.store.*`。

**3. 红线 3（门控照抄 + fail-closed）— PASS**
门控模式与 refreshAgentPane（register.tsx:1027）一致（`panes().some(pane => pane.id === DECK_PANE_ID)`），另加 `Array.isArray` 防御，方向为 fail-closed。吞错且不 cancel 定时器（clock.every 实例未被取消，下一 tick 重试）。「面板不可见即停帧」由 register.test.ts:1879 验证：panes 不含 deck → beat 不变；panes 抛错 → beat 不变；恢复后下一 tick 正常翻转（1904-1914）。

**4. beatTimer 生命周期（条目 1 + 偏离 1）— PASS，偏离 1 判 ACCEPT**
session.start 内创建（register.tsx:1046，模式同 1039/1042 planTimer/gitTimer）；创建前 register.tsx:909 `beatTimer?.cancel()` + 910 `update($, beat, () => 0)`，顺序为「先 cancel 后重置」，与方案原文「创建前先 beatTimer?.cancel() 取消旧实例并 update($, beat, () => 0)」逐字一致。Executor 声明的偏离（重置位于 cancel 区紧邻处 909-910，而非 atom 重置清单 882-901）语义等价且更贴合方案「生命周期模式同 780-781 取消旧 planTimer/gitTimer」的指引——重置与取消同区，两操作时序紧邻，无中间 await 窗口。重复 session.start 不累积：register.test.ts:1917-1938（两次 session.start 后单周期翻转恰 `[1]`）。

**5. 呼吸元素清单（代码评审节点）— PASS（附 P2-1 记档）**
`breathAccent` 全文件仅两处消费：register.tsx:551（执行阶段行，含 batch 与阶段文案的行级着色）与 register.tsx:558（阶段进度条）。`beatFrame` 仅 395-410 计算区。逐项越界检查：AbovePrompt 输入区横条（呼吸符号零引用，grep 证明 breathAccent/beatFrame 不出现在该区域）；DAG（register.tsx:612-646，节点态着色静态）；评审卡（574-611，tone 静态）；git 行（横条区，静态）；tLevel chip（553，backgroundColor 静态）——全部静止。stall 非空时 register.tsx:410 `stallMinutes === null && beatFrame === 1` 使 breathAccent 恒 false → 两呼吸元素恒 dimColor，且小生物不受该灰档约束（抖腿态测试 1978 验证）。验证计数全绿 ✓ 前缀（566-567）纯派生自 `testsTotal > 0 && testsPassed === testsTotal`，无独立状态。
P2-1：「阶段进度条**当前段**」落地为整条着色（558）。改动前该 Text 节点即为整条单色 TONE.ok（git diff 证实 `-<Text color={TONE.ok}>`），拆段需改 progressBar 结构；视觉边界仍限定在方案点名的两个元素内。此解读未出现在 Executor 偏离清单中，记档观察期复核。

**6. creatureState（代码评审节点）— PASS**
parse.ts:435-442：优先级 敬礼（closureCard 非空）> 捂脸（`currentTask !== null && guardWarned.length > 0`，按长度判定）> 抖腿（stall 非空）> 分身（agents 有 running）> 干活（currentTask 非空）> 睡觉兜底，与共识表逐字一致。纯函数：输入 CreatureSources 全为只读快照（parse.ts:424-431），无 IO 无变异。B1 接缝两处均正确：敬礼态直接消费 closureCard（B1 四出口清卡即退位）；捂脸以 currentTask 为门——即使 B1 条件清理失效，收口后 currentTask 置 null 也关门（L1 对照用例 parse.test.ts:973 专门验证该防线）。L1 覆盖：阶梯+组合取最高（parse.test.ts:902-935）、空数组不命中（937-947）、警告态四路转换+对照（949-974）。

**7. creatureFrames — PASS**
parse.ts:446-453：六态 × 两帧 = 12 常量完整，每帧 2 个盲文字符（≤4 显示列），每态两帧互异。宽度断言测试真实且有效（parse.test.ts:976-992）：键集合相等 + 逐帧码点数 ≤4 + 盲文区段 0x2800-0x28FF 校验 + `f0 !== f1`。

**8. companion 配置（条目 4）— PASS**
plugin.json（diff 确认）：`companion` options `["on","off"]`、default `"on"`；register.tsx:874 按配置覆盖，默认 on。off 时 creature 恒 null（register.tsx:399-407），渲染层跳过而 `breathAccent` 计算不依赖 creature——呼吸与节拍器不受影响。测试佐证 register.test.ts:2013-2044：盲文 Text 节点零匹配、beat 照常翻转 `[1]`、beat=1 帧呼吸条 accent（2042）。

**9. §B2 验收标准 1-4 — 全 PASS**
1. PASS：两档交替（1940-1976，beat=0 dim / beat=1 accent，双元素各断言 color+dimColor，且断言对象经盲文正则排除小生物行 1965-1966）；面板关闭停帧（1879）。「两帧差异仅在着色」由 1844（beat 窗口内非 beat 键零写入）+ 1940（渲染纯派生）联合成立。
2. PASS：stall 注入后呼吸两帧恒 dim、抖腿两帧继续切换（1978-2011，且 2042 证明同 beat=1 无 stall 时为 accent，stall 覆盖真实生效）。
3. PASS：六态——状态机 L1 穷尽（902-935）+ 渲染集成覆盖睡觉（拆组③ 2073-2109）/抖腿（1978）/敬礼（2046）/捂脸反向（2069），clone/work 经统一 `creatureFrames[state][beat]` 索引与帧表测试传导；companion=off 缺席且呼吸不受影响（2013）。
4. PASS：红线 1/3 各有定向测试且通过（1844/1879），红线 2 无 IO 由逐行核对成立（方案本身的 L2 清单亦只要求红线 1/3 测试，红线 2 为代码评审节点）；全量无回归见下方独立复跑。

**10. 偏离 2-5 合理性 — 全 ACCEPT**
- 偏离 2（执行阶段行行级着色、chip 静态）：行级是「行」的自然读法；tLevel chip 为反色块，accent/dim 翻转会破坏反色可读性，静态合理。ACCEPT。
- 偏离 3（标题行右端行尾占位、truncate 可能截断）：占位在标题 Button 行尾（register.tsx:538）与无任务行尾（469-471），单行、≤4 列、超宽不扩展均满足；窄面板截断风险已被方案收尾批真机目检清单「窄面板 <44 列」项覆盖。ACCEPT（P2-2 记档）。
- 偏离 4（小生物 dimColor 着色）：方案未指定小生物颜色；dimColor 与「克制」基调一致，不引入新色。ACCEPT。
- 偏离 5（帧图案自拟）：方案仅约束「盲文两帧静态常量、≤4 列」，图案未指定；帧表测试保证两帧互异可感知。ACCEPT。

**11. 证据真实性抽查 — PASS**
- 日志链自洽：probe.log（探针红，125/3，dump 的真实文案 `B2 · 执行`/`━━━━━━────`/` ⠋⠂` 与现行代码字符串一致）→ S1 红（125/3）→ S2 二轮红（失败签名不同：companion=off 期望 professionalBlue 得 undefined，与中间修复态一致）→ S3/S5 绿（128/0）→ S6/S7 绿（130/0，拆组③两条新增）→ S4 validate 通过（仅 LICENSE/ICON 仓库级既有警告）。
- 测试数算术吻合：B1 收口 117（B1/S7-full.log:129）→ B2 首绿 128 = +11（register 7 条：红线1/红线3/生命周期/呼吸/小生物/companion/优先级 + parse 4 条：阶梯/空数组/警告转换/帧宽）→ +2 拆组③ = 130。逐条与代码对得上名。
- 拆组③补齐两条：register.test.ts:2073（default）与 2092（mission-control），双皮肤锚点值一一对应（Box 7 / Text 6 / dimColor 4 / color 0），仅文案断言不同——名实相符，且仅出现在 S6/S7。
- 双皮肤既有测试 Box 10→11 适配：双皮肤同态测试 B1 时已存在（B1/S7-full.log:104-105 pass），B2 在无任务分支新增 creature 时包一层 Box（register.tsx:469-471）恰 +1；两皮肤同步改为同值 11（register.test.ts:1215、1254），测试本旨（跨皮肤结构一致）未弱化。绝对基线由拆组①承担且显式固定 companion=off（register.test.ts:289）。适配理由成立。
- L1/L2 映射名实相符：方案 §B2「如何验证」清单逐条在案（见第 6/9 项行号），无缺漏、无改名偷换。

**12. 独立复跑 — PASS**
- `claude plugin test plugins/flow-deck`（仓库根）：**130 pass / 0 fail，exit 0**（Ran 130 tests across 4 files, 17.99s）。
- `claude plugin validate plugins/flow-deck`（仓库根）：**Validation passed with warnings，exit 0**（警告仅 LICENSE_MISSING / ICON_MISSING，为仓库级既有项，与 S4 证据一致，非 B2 引入）。
- 无 timeout 类失败，未触发 flaky 复跑规则。

## 问题分级清单

- **P0：无**
- **P1：无**
- **P2（记档，不阻断）**：
  1. 「阶段进度条当前段」落地为整条着色（register.tsx:558）——解读偏离方案字面「当前段」，但改动前该节点即整条单色、拆段需重构 progressBar，视觉边界仍在两元素内；未列入 Executor 偏离清单。观察期如认为已完成段不该呼吸再拆段。
  2. 标题行行尾小生物在极窄面板可能被截断（偏离 3 已自曝）；由收尾批真机目检「窄面板 <44 列」项覆盖，届时重点核对该项。
  3. 双皮肤同态测试的 Box 绝对计数（11）会随未来结构改动漂移，属该测试固有维护成本（其本旨是双皮肤等值断言），无需动作。

## 对 B2 收口的建议

**建议收口通过。** 理由：帧三红线在实现与测试两层均闭环（写入点全集 2 处、回调零数据面 IO、门控 fail-closed 且保活）；六态状态机与共识逐字一致且 B1 接缝（closureCard 敬礼、guardWarned 条件清理语义）有对照用例防线；证据链两轮红→绿真实、测试数算术逐条吻合；独立复跑 130/0 + validate exit 0。3 条 P2 均为记档性质，其中 P2-2 转入收尾批真机目检清单对应项执行。可进入收尾批（0.18.0 版本 + README + 真机目检）。

## 主控复核附注（2026-11-03）

- 审计范围锁定 B2、B1 明确排除，未越界；输入为具体清单，意见具体可核。
- P2-1 采纳记档：改动前节点即整条单色，整条呼吸为最小改动解；观察期复核项。
- P2-2 已标注转入收尾批真机目检「窄面板 <44 列」项执行。
- B2 收口通过。
