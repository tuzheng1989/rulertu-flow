# B2 Auditor 报告：deep-research product 通道接线（0.6.1 → 0.7.0）

- 日期：2026-11-10
- 审计对象：B2 批次（五文档位接线 + 版本三处收口）
- 审计方式：只读核验——git diff 全量逐处对照、grep 复跑、红线回归复跑、行号对账、横向矛盾扫描
- **最终判定：通过**（无 P0 / 无 P1；P2 记档 2 项，见第六节）

## 一、差异核验（边界与锚点）

### 1.1 git status 全表归属（7 M + 8 ?? 共 15 项）

| 条目 | 归属 | 判定 |
|---|---|---|
| M CHANGELOG.md | B2（边界 #4） | 边界内 |
| M plugins/work-skills/.claude-plugin/plugin.json | B2（#5） | 边界内 |
| M plugins/work-skills/.codex-plugin/plugin.json | B2（#6） | 边界内 |
| M plugins/work-skills/skills/deep-research/SKILL.md | B2（#1） | 边界内 |
| M plugins/work-skills/skills/deep-research/agents/research-node-query.md | B2（#2） | 边界内 |
| M plugins/work-skills/skills/deep-research/docs/SEARCH_MIGRATION.md | B2（#3） | 边界内 |
| M plans/work-skills/2026-11-10-producthunt-research-channel.md | **B1 修订轮勘误，非 B2 产物** | 边界外，P2-1 记档 |
| ?? .flow-evidence/B2/executor-report.md | B2 证据（#7） | 边界内 |
| ?? .flow-evidence/B2/orchestrator-l3.md | 主控验证记录 | 预期产物 |
| ?? .flow-evidence/B1/（executor-report.md、mcp-tools-schema.json） | B1 证据 | 预期产物 |
| ?? plugins/work-skills/skills/sn-search-producthunt/（3 文件） | B1 产物 | 预期产物 |

任务说明所列 agent-skills 并行改动已不在当前 status（并行会话已提交，见 6d7617d 等），无需排除处理。B2 边界外仅方案文档一项，经 diff 内容核对为 B1 勘误（自述「B1 批」+ 指向 B1 证据 + 与 B1 报告 §五.1 裁决建议逐字对应），非 B2 executor 越界。

### 1.2 六文件 diff 逐处对照方案 B2 节锚点

| 方案锚点 | 实际改动 | 判定 |
|---|---|---|
| SKILL.md L3-4 frontmatter | description 追加 v0.7.0 句（与方案文字逐字一致）+ version 0.7.0 | ✓ |
| SKILL.md L137-145 映射表 | L146 加 product 行，命令形态与方案一致 | ✓ |
| SKILL.md 调用约定（normalize） | L161「输出已含 source_type:"product"，items[] 直接入 search_results」 | ✓ |
| SKILL.md 降级枚举 L404 | L408 (academic/code/social/product) | ✓ |
| SKILL.md 实现说明表 L383-393 | L397 加 product 行（--limit 上限 8） | ✓ |
| SKILL.md prose L414-429 | L420 五通道→六通道、L428 加 product 条目 | ✓ |
| query 节点 L25 + L38 | 两处枚举同改同序（product 插 web 前） | ✓ |
| query 节点 L71-86 选择指南 | L81 加 product 行 + L88-89 选择原则两句 | ✓ |
| query 节点 L43-69 / L156 不改 | diff 无改动 | ✓（遵守方案「不改」） |
| SEARCH_MIGRATION 末尾追加 | v0.7.0 节四小节（L71/73/77/85/89），v0.5.0 历史节零改动 | ✓ |
| CHANGELOG Unreleased 顶部 | work-skills 2.4.0 条目，agent-skills 1.5.0 既有条目零改动 | ✓ |
| 双 manifest | 各仅 version 行 2.3.2 → 2.4.0 | ✓ |

另核：SKILL.md L153 子工具选择行（方案未单列锚点、属映射节自然延伸）明写「子命令契约详见 ../sn-search-producthunt/SKILL.md，不在此复制」。全 diff 无越界改动、无夹带无关修改。

## 二、契约一致性（方案代码评审节点）

1. **product 枚举三处声明位 + 降级枚举一致出现**：SKILL.md L146（映射表）/ research-node-query.md L25（schema）/ L81（选择指南）/ SKILL.md L408（降级注）四处一致；L25 与 L38 同步同序。
2. **包络 JSON 单一出处**：deep-research 文档面（SKILL.md + agents/*.md + docs/*.md）`grep '"success"'` 零命中；对照组 B1 sn-search-producthunt/SKILL.md L53 唯一定义；SEARCH_MIGRATION L91 仅引用失败信号（success:false + 退出码 1），不复制包络结构。
3. **选择指南两项声明齐备**：L88「maker 自报，source_tier: secondary，关键事实需与 web/academic 交叉验证」；L89「榜单只反映互动信号，竞品发现优先 alternatives/semantic」。
4. **参数形态与 B1 契约一致**：`--name`（SKILL.md L153 ↔ B1 SKILL.md L33-34）、`--date` 必填（L153 ↔ B1 L36）、limit 上限 8（L397 ↔ B1 L31/32/35/36）。
5. **降级规则 3.2 段**为通用表述（「脚本 success:false、报错、缺依赖」），pseudocode 走 CHANNEL_MAP 分派无枚举遗漏，product 经映射表自动纳入——executor「无需改文」判断与实际文本相符。

## 三、测试证据复核（Auditor 独立复跑）

1. **红线回归**：`PYTHONIOENCODING=utf-8 python scripts/test_state_manager.py` → `测试结果: 31/31 通过`，EXIT=0。与 executor、主控记录一致。
2. **grep product 一致性**：复跑输出与 executor 行号清单完全一致（SKILL.md L3/146/153/161/397/408/420/428；query L25/38/81/88-89；L147 为既有示例查询词，executor 已如实归类为非接线位）。
3. **版本四点一致**：.claude-plugin L4 = 2.4.0 / .codex-plugin L3 = 2.4.0 / SKILL.md L4 = 0.7.0 / CHANGELOG「work-skills 2.4.0」恰 1 处。SKILL.md 残留 0.6.1 字样均为历史注记（L3 版本史、L24 v0.6.1 注记、L195 alphaXiv 注释），非不一致。

在线 L3 演练（semantic 8/8 含 source_type:product ≥3、leaderboard 缺 --date 触发信号）采信主控记录（orchestrator-l3.md 已标注为主控抽查项，输出具体可信：首条 Reflect/reflect-notes、funding 字段实证）； Auditor 未复跑在线调用——上游限流约束下证据已双源一致，无可疑点。

## 四、Executor 回报可信度抽查

- **行号抽查**（5 组全部命中）：SKILL.md L146/161/397/408/428；query L25/81/88-89；SEARCH_MIGRATION L71/73/77/85/89。
- **命令记录抽查**（3 条全部对账一致）：31/31 回归、版本 grep（L4/L3/L4/1 处）、`'"success"'` grep 退出码 1。
- **事实性陈述核对**：CHANGELOG 内嵌「离线测试 33/33」与 B1 executor 报告修订轮 R4（Ran 33 tests, OK）一致。
- 4 条实现决策（枚举插 web 前、SEARCH_MIGRATION 历史节不追溯、表格行反引号样式、CHANGELOG 并行会话锚定插入）均合理且如实披露，无隐瞒。

## 五、表述矛盾扫描

- **五文档位互查**：映射表 L146 / 调用约定 L153+L161 / 降级 L408+3.2 / 实现说明表 L397 / prose L420+L428 对 product 表述一致，无矛盾。
- **「五通道」残留 3 处均为历史注记**：SKILL.md L22（v0.5.0 注记）、L24（v0.6.1 注记「不动五通道」）、SEARCH_MIGRATION L75（「v0.5.0 的五通道」历史引述）——历史状态记录不追溯修改是正确处理；现行表述 L420 已是 6 通道。
- **summary/reflect 节点透传核验**：两节点对 source_type 均无硬编码枚举（research-node-summary.md L14/L109、research-node-reflect.md L82/L226 均为通用表述），product 自动流转——方案「不改三节点」判断成立。
- **SEARCH_MIGRATION v0.7.0 节语义**与 SKILL.md、query 节点一致：secondary 默认、榜单偏置、匿名收紧 → success:false（退出码 1）→ 既有降级兜底、17 工具全量 vs 7 只读封装的架构动机。

## 六、问题清单

**P0（阻断）：无。**

**P1（需修复）：无。**

**P2（记档不阻断）：**

1. **方案文档改动归属留痕缺口**：`plans/work-skills/2026-11-10-producthunt-research-channel.md` 的工作区改动（B1 勘误块 + 子命令表 6 行按实测 schema 修订）不在 B2 七文件边界，也未在任何 executor/orchestrator 改动清单中显式声明。内容与 B1 修订轮裁决链路完全对应（B1 报告 §五.1 建议「方案第 0 节需同步勘误」+ R1 tools/list 探测授权 + mcp-tools-schema.json 证据落盘），判定为 B1 流程 sanctioned 的勘误写入、非 B2 越界；但「该写入由哪个角色执行」无留痕。建议：后续批次把方案勘误动作显式写入对应批次记录。
2. **SKILL.md 头部版本注记区（L12-24）无 v0.7.0 条目**：该区记录 v0.4.0/v0.4.1/v0.5.0/v0.6.1，本批未追加 v0.7.0。与 v0.6.0 先例一致（该处同样无 v0.6.0 条目），方案锚点仅要求 frontmatter（已承载 v0.7.0 句），不构成缺陷；仅记档供后续版本决定是否维护该注记区。

## 七、结论

- **完成度**：B2 委派范围（五文档位接线 + 版本三处收口）全部落地，与方案 B2 节锚点一一对应，无遗漏无夹带。
- **证据真实性**：executor 回报的行号清单、命令记录、事实性陈述经抽查全部对账一致，无虚报；主控 L3 记录口径限制（无 web-search-prime server，降级以触发信号 + 规则文本一致性覆盖）已如实披露，处理方式合理。
- **契约对齐**：验收 5 条逐条达成——验收 1/4/5 经 Auditor 独立复验，验收 2 采信主控演练 + Auditor 复核降级文本枚举，验收 3 经 Auditor 复跑（31/31）。代码评审节点四项（包络单一出处、枚举两处同步、source_tier secondary 写入、三呈现位语义一致）全部满足。
- **最终判定：通过。** 可进入波次收口；提交动作留待主控按流程执行。
