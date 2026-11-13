# B1 主控抽查记录

日期：2026-11-13。抽查人：主控。Executor 回报后、派 Auditor 前执行。

## 抽查项与结果

| 抽查项 | 命令 | 结果 |
|---|---|---|
| grep 相对路径零命中（复跑） | `grep -rn "\.\./sn-search-" deep-research/` | 零命中（rc=1）✓ 可采信 |
| grep 旧前缀零命中（复跑） | `grep -rn "\.claude/skills/" deep-research/ --include="*.json" --include="*.md" \| grep -v INSTALL.md \| grep -v README.md` | 零命中（rc=1）✓ 可采信 |
| 顶层清零（复跑） | `ls \| grep sn-search` | 零输出 ✓ |
| rename 追踪 | `git status --porcelain` | 全程 R/RM，5 目录搬迁追踪完好 ✓ |
| state_manager 回归（复跑） | `python deep-research/scripts/test_state_manager.py` | 31/31 通过 ✓ 可采信 |
| SKILL.md/config.json 锚点改动核验 | 通读改动区 | 与委派单锚点一致，image 行/条目落位正确 ✓ |

## 主控修正（边界内，1 处）

- deep-research/SKILL.md 424 行（原 420 行，行号因改动偏移）：`product=sn-search-producthunt 脚本` → `product=channels/product 脚本`。委派单对该行只指定了改"分派通道数"，名称残留为主控补充修正（活引用性质，旧目录名已不存在）。

## 对 Executor 待决事项的处置

1. **三个 CHANNEL.md 依赖指引旧路径**（`skills/sn-search-<X>/requirements.txt`）：**接受不改**。CHANNEL.md 契约文档的依赖指引属于 B3 联动收尾或后续维护范围，不触发任何 B1 验收项，避免本批扩面。已记入 B3 待办（见下）。
2. **SKILL.md 424 行名称残留**：主控已修（见上）。
3. **image 冒烟文案**（`Serper image search is unavailable in the current environment.`）：**接受不改**。脚本"原样随迁"边界正确；该消息为确定性缺 key 退出路径，语义足以定位问题。验收（非栈崩溃、确定性退出）已满足。
4. **description 第 3 行 `sn-search-*` 字样**：版本历史描述（v0.5.0 记录），历史事实不改写；B3 升版时按方案统一处理 description。

## 移交 B3 的待办（新增，源自本次抽查）

- 三个 CHANNEL.md 依赖安装指引的旧布局路径更新（code / social_cn / social_en）。

## 移交 B3 的待办（追补，源自 Auditor 审计 2026-11-13）

- **P2-1**：search_utils.py ×3（code / social_cn / social_en）第 21 行缺 httpx 报错指引内嵌旧布局路径 `skills/sn-search-<X>/requirements.txt`，收编后已失效——与 CHANNEL.md 指引一并更新。
- **P3-1**：SEARCH_MIGRATION.md 收编节代码块围栏错位（两行说明文字被裹进 ``` 内），B3 顺手修。
- **P3-3**：producthunt_search.py:44 User-Agent "sn-search-producthunt/1.0" 历史标识，是否更名 B3 定夺。

## 结论

Executor 回报的关键验收项经复跑全部成立，标注可采信。B1 执行阶段通过，移交 Auditor 证据包审计。
