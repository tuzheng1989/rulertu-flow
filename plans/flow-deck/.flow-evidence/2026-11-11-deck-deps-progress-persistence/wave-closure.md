# 波次收口：deck-deps-progress-persistence（2026-11-12）

## 三批收口记录

| 批 | 提交 | 版本 | 验收 | 审计 |
|----|------|------|------|------|
| B1 持久化 + 拓扑下推 | d2aa8b3 | 0.21.0 | G1-G7/G9 八条 PASS（154/154） | 可收口，P2×2 已归 B2 消化 |
| B2 backfill 补报通道 | 262315e | 0.22.0 | G10-G12 三条 PASS（157/157） | 可收口，P2×2（:1317 措辞归 B3 已清扫 / 行号漂移记档） |
| B3 阶段缩减 5→2 | 28aeeeb | 0.23.0 | G14-G17 四条 PASS（159/159） | 可收口，P2×3 记档（diff.patch 已补齐） |

## 波次收口验证

- 全量测试：159 pass / 0 fail（2026-11-12，收口时复跑）
- validate：passed with warnings（author/LICENSE/icon 为仓库既有基线）
- 累积差异：30 文件 +3271/−42（含方案与证据文档；代码部分 10 文件）
- 红线：帧三红线用例全过，beat 机制零触碰（三批审计各自确认）
- 工作区：干净，全部入库

## 待办：真机验证（G8/G13/G17 真机部分）

前置：push 三提交 → 更新本机 flow-deck 插件至 0.23.0（注意本会话的 flow-deck 工具是安装版 2.7.0 插件提供，本会话上报数据走旧版代码，**新版本的 store 键需在新会话重新造数**）。

1. **G8 跨会话往返**：新会话 A `flow_deps` 声明 + `flow_report`（phase:'验证'，tests 全绿）→ 结束会话 → 新会话 B `flow_task` implement 同方案 → `/deck`：轨道图出现、该批 done；
2. **G13 backfill 补报**：新会话 A 声明 B1 并收口但**漏报**（或直接跳过收口上报）→ 新会话 B 经 implement-plan 开工 B2（核对后补报 backfill）→ `/deck`：B1 done 且 B2 任务/边界不受扰；也可手动 `flow_report(plan, batch:'B1', phase:'收口', backfill:true)` 模拟；
3. **G17 真机体感**：实际跑一批 implement-plan，确认每批仅两次上报（执行/验证），验证全绿自动通关卡。

任一真机项失败：回本方案对应批次返工，不静默降级。
