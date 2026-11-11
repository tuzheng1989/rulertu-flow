# B2 审计报告：历史批次补报通道（backfill）

- 审计对象：flow-deck B2 批（flow_report backfill 旁路 + implement-plan 开工核对补报纪律）
- 审计模式：T2 证据包审计，只读核验（ auditor 契约：主控已抽查的测试证据默认采信，未重跑全量回归——全量回归属波次收口）
- 证据包：`plans/flow-deck/.flow-evidence/2026-11-11-deck-deps-progress-persistence/B2/`（delegation.md / diff.patch / test-red.log / test-green.log / test-final.log / validate-final.log）
- 契约权威：`plans/flow-deck/2026-11-11-deck-deps-progress-persistence.md` B2 详案 + 设计裁决 D11；前置 B1 已合入（d2aa8b3）

## 逐项结论

### 1. 差异范围 — PASS

- diff.patch 共 6 文件 250 行，与工作区 `git diff`（限同 6 文件）**逐字节一致**（`diff` 比对输出 IDENTICAL）。
- 6 文件全部在委派单边界内：`plugins/flow-deck/hooks/register.tsx`（+13）、`plugins/flow-deck/hooks/register.test.ts`（+132 新用例 / 2 处注释行替换）、`plugins/rulertu-flow/skills/implement-plan/SKILL.md`（:12/:18 两处）、双 manifest（version）、根 `CHANGELOG.md`（Unreleased 条目）。无边界外改动。
- 工作区第 7 个改动文件 `plans/flow-deck/2026-11-11-deck-deps-progress-persistence.md`（git stat 8 行变动）**确认存在且系主控委派前更新，非 Executor 改动**，内容为 G12 收尾补充：新增「收尾」节 1 行（双 manifest 0.22.0 + CHANGELOG）、测试规格新增 2 条（写入侧断言 = B1 审计 P2-2 消化；注释修正 = B1 审计 P2-1）、G10/G12 验收表证据列改写 2 行。与委派单内容一致，属方案-委派同步留痕。**注意：本批提交时应将这 8 行与 Executor 六文件改动归置清楚（分开提交或注明归属），避免误记为 Executor 越界改动。**

### 2. backfill 分流正确性（核心） — PASS

分流点位置：`register.tsx:1412-1415` parse 校验（`report === null` 报错）之后 → `:1420` 分流判定 → `:1421-1426` 旁路三步（progress update + persistProgress + return）。旁路 return（:1426）先于常规路径全部副作用（:1428-1509）。

副作用清单逐一核实（S1-S11，源码行号为当前工作区）：

| # | 副作用 | 常规路径行号 | backfill 是否触碰 | 核实方式 |
|---|--------|--------------|-------------------|----------|
| S1 | closureCard 组装/写入 | :1440-1478 | 未触碰 | 提前 return 前置；测试计数断言 |
| S2 | execution 写入 | :1479 | 未触碰 | 同上 |
| S3 | progress 写入 | :1480-1483 | **按设计触碰**（旁路自有 :1421-1424，键 `<plan>#<batch>` → phase） | diff + 测试 `writes.progress` 断言 |
| S4 | persistProgress | :1484 | **按设计触碰**（:1425，复用 B1 通道） | diff + store.set 断言 |
| S5 | lastRun | :1486-1488 | 未触碰 | return 前置 |
| S6 | guardWarned | :1490-1495 | 未触碰 | 同上 |
| S7 | currentTask | :1496-1498 | 未触碰 | 同上 + `.at(-1)` 末值断言 |
| S8 | batchScope 清理 | :1499-1501 | 未触碰 | 同上 |
| S9 | `lastStatus = undefined` + `$.ui.status(undefined)` | :1502-1503 | **未触碰**（重点核实：两行位于 :1502-1503，提前 return 在 :1426，确被绕过） | 源码通读 |
| S10 | `store.set(lastExecution)` | :1504-1508 | 未触碰 | 测试断言 lastExecution 恰写 1 次且属常规上报 |
| S11 | firstReportAt | flow_report 仅读 :1433；写仅 flow_batch :1520、session.start clear :1155 | 天然不在链路 | 全文件 grep `.set/.clear` |

- 严格判定：`:1420` 为 `e.backfill === true`，读原始事件字段（非 parse 产物），`'true'`（字符串）、`1` 等 truthy 非布尔值不走旁路，落入常规路径。
- inputSchema（`:1198`）描述含「仅用于开工核对时补齐前序批次」限定，与委派单逐字一致。
- 与 D11 / 详案「如何改」:164 逐项吻合：分流位置（parse 后一切副作用前）、旁路仅 progress + persistProgress、返回文案 `历史批次状态已补报：<plan>#<batch> → <phase>`。
- 收口组装四步（minutes 判定 / scope 校验 / git 取数 / stamped 并入，:1428-1467）均在旁路之后，不被执行。

### 3. 技能契约 — PASS

- SKILL.md `:12` 插入句与详案 :168 原文**逐字一致**（「核对到的收口事实与面板状态可能不符（跨会话漏报）……逐条带 `backfill: true` 补报（幂等，可重复）。」）。
- SKILL.md `:18` 改写与详案 :169 原文**逐字一致**（「工具不存在时静默跳过。常规上报漏报不补报不重试；开工核对发现的历史批次收口缺失，按开工检查点口径经 `backfill` 补报。」）。
- 全库 grep「不补报」：**规范陈述唯一出处为 SKILL.md:18（新口径）**。其余命中均为：plans/ 方案文档（历史动机陈述 :24/:159、改写指令 :169、B3 未来引文 :227、U4 :274——均属方案记档）、`.plan-iterate/` 评审归档、B2 证据包自身、`CHANGELOG.md:5`（0.22.0 条目自述新口径，属变更记档非契约陈述）。旧措辞「不补报、不重试」（带顿号）在技能目录已消失。
- `:16` 与 `:18` 共存自洽：`:16`「正常收口由 flow_report 自动撤下面板」描述**常规通道**——旁路代码实证不撤任务、不清边界（S7/S8），两通道互不干扰，该句仍然为真；`:18` 新口径的两域不相交——「常规上报漏报不补报不重试」约束本会话常规上报，「开工核对发现的历史批次收口缺失经 backfill 补报」约束跨会话前序批次且 `:12` 限定须证据目录或 git log 佐证、非本会话已上报。无自相矛盾。
- 技能目录（含 references/）内 backfill 引用仅 `:12`/`:18` 两处，无散布。

### 4. 测试证据 — PASS

- **157/0 对账成立**：B1 基线 154（`B1/test-final.log` 尾部「154 pass / 0 fail / Ran 154 tests」实证）+ 3 新用例 = 157；green 与 final 均「157 pass / 0 fail」。
- **红态真实**：red 日志「155 pass / 2 fail / Ran 157 tests」——两个失败恰为两个 backfill 行为用例，失败信息「Expected "历史批次状态已补报：demo#B1 → 收口" / Received "进度已上报"」证明红态指向新行为（旁路未实施时落入常规路径）；第三个新用例（持久化写入侧）测 B1 既有行为红态即绿，符合预期，不构成红绿纪律瑕疵。
- **三用例断言与委派单规格一致**：
  1. backfill 旁路：7 键 state.set 序列注册（test diff :48-54：currentTask/batchScope/closureCard/execution/lastRun/guardWarned/progress）、store.set 载荷 `{ key, value }`（:55-59）、返回文案精确匹配（:78）、progress 恰新增一次且只含补报键（:80）、持久化通道收补报后 map（:81-83）、6 个「当前执行」键计数不变（:85-90）、storeWrites 恰 +1（:91）、currentTask/batchScope 末值保持 B2（:93-94）。
  2. backfill 后常规上报回归：返回「进度已上报」、execution/currentTask/progress/batchScope 照常、progressMap 含全量键、lastExecution 恰写 1 次且属常规上报（:97-141）。
  3. 写入侧：flow_deps 落 `depsGraph`（dependsOn 缺省补空数组）、常规 flow_report 落 `progressMap` + `lastExecution`（objectContaining 吸收 updatedAt）（:143-175）。委派单测试规格 3 条全覆盖（「backfill 后 store.set 收到补报后 map」在用例 1 :81-83）。
- firstReportAt「无新记点」：模块级 Map 非 state.set 可观测，以源码级核实（S11：flow_report 链路无写点）替代；委派单括注本就限定「（state.set 序列）」为观测手段——接受。
- **注释修正只改注释未动逻辑**：原 `:1008`/`:1053`（HEAD 行号，diff hunk 2/3）两处「测试引擎无该设施」注释仅替换注释行，周边代码逐行核对零改动。
- **第三处旧措辞确未改动**：HEAD `:1185`「store 出口留待端到端」保持原样，现位于当前文件 `:1317`；Executor 记档行号 :1178 与实际 :1185 有 7 行漂移（内容定位无歧义），范围外如实上报属实。
- validate-final：「Validation passed with warnings」；警告项（LICENSE_MISSING / icon / author）与 B1 validate 日志**逐项一致**，系仓库既有状态，非本批引入。

### 5. 版本收尾 — PASS

- 双 manifest 同步 0.21.0 → 0.22.0：`.claude-plugin/plugin.json`（diff :21-22）与 `.codex-plugin/plugin.json`（diff :34-35）。
- CHANGELOG Unreleased 首位插入 0.22.0 条目，句式与 0.21.0 条目同构：`flow-deck X.Y.Z：<主题>（方案路径 B 批）——**工具侧**…**技能侧**…**测试**…双 manifest 同步升版 X.Y.Z。`；内容覆盖旁路行为、D11 幂等前提、技能口径改写、三用例与 B1 审计 P2-1/P2-2 消化、双 manifest 升版惯例句。

### 6. 红线 — PASS

- diff.patch 无任何 beat 相关改动：register.tsx 仅两个 hunk（inputSchema `:1195+` 与处理器 `:1413+`），beat 相关代码（`:92-94` atom、`:1160-1164` session.start 节拍器复位、`:1315-1332` beatTimer）零触碰。
- test-final 中红线 1（连发 3 次 beat tick 除 beat 外全键快照不变）、红线 3（面板不可见停帧）、节拍器生命周期、呼吸/小生物断言全部通过——帧三红线不受影响。

## 问题清单

| 级 | 问题 | 位置 | 说明与建议 |
|----|------|------|------------|
| P2 | 残留旧式措辞「store 出口留待端到端」未清扫 | `plugins/flow-deck/hooks/register.test.ts:1317`（HEAD :1185） | 与本批已证伪的「store.set 不可断言」旧口径同族但措辞较弱（单测内事实注记）。Executor 如实上报范围外未动，符合精准局部修改纪律；建议随 B3 批顺手清扫，不阻断本批 |
| P2 | 行号锚点漂移（纯记档层面） | Executor 记档 :1178 vs 实际 :1185；委派单 :922 vs 实际 :1008/:1053 | 均以内容定位无歧义，无实质影响；后续委派锚点建议取自最新 HEAD 复核 |
| 信息 | 方案文档 8 行主控改动与 Executor 改动同在工作区 | `plans/flow-deck/2026-11-11-deck-deps-progress-persistence.md` | 提交时分开提交或在 commit message 注明归属，避免误记为 Executor 越界 |

无 P0 / 无 P1。

## 完成度 / 证据真实性 / 契约对齐 / 独立验证证据

- **完成度**：G10 PASS（旁路只写 progress + 持久化，S1-S11 逐一核实）；G11 PASS（backfill 缺省 falsy，既有用例零改动全过）；G12 PASS（补报口径在场、旧口径已改、单一出处、双 manifest 0.22.0 + CHANGELOG 落盘）。G13 归最终波次收口，不在本单。
- **证据真实性**：diff.patch 与工作区逐字节一致；四份日志数字自洽（red 155/2 → green 157/0 → final 157/0，validate passed-with-preexisting-warnings）；主控已抽查复跑一致（标注可采信）。
- **契约对齐**：委派单锚点、D11、详案「如何改 / 如何验证 / 验收标准 / 代码评审节点」逐条核对，无弱化、无越界。
- **独立验证证据**：① `diff <(diff.patch) <(git diff -- <6 文件>)` → IDENTICAL（250 行）；② `git show HEAD:…register.test.ts | grep '无该设施\|留待端到端'` → 三处 :1008/:1053/:1185；③ `B1/test-final.log` 尾部 → 154/0；④ flow_report 处理器（:1411-1510）源码通读副作用逐行比对；⑤ 全库 grep「不补报」与技能目录 grep「backfill」。

## 建议下一步

可收口提交。提交时将方案文档 8 行主控更新与 B2 六文件改动归置清楚（分开提交或注明归属）；P2 残留措辞并入 B3 顺手修正清单。

## 总结论

**可收口。** 核心旁路行为、技能契约改写、测试对账与版本收尾逐项核实无弱化，无 P0/P1 问题。
