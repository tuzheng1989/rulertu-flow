# B2 Executor 报告：sn-search-producthunt 通道接入 deep-research（0.6.1 → 0.7.0）

日期：2026-11-10 · 执行者：rulertu-flow:executor · 委派单：B2（五文档位接线 + 版本三处收口）

## 改动清单（全部为既有文件加法式修改，未改既有五通道语义与枚举值）

| 文件 | 改动 |
|------|------|
| `plugins/work-skills/skills/deep-research/SKILL.md` | 8 处：frontmatter description 追加 v0.7.0 句 + version 0.7.0；映射表加 product 行（L146）；子工具选择加 product 条（L153）；normalize 映射加 sn-search-producthunt 条（L161）；实现说明表加 product 行（L397）；降级注枚举补 product（L408）；prose 5→6 通道（L420）；prose 条目清单加 product 通道描述（L428） |
| `plugins/work-skills/skills/deep-research/agents/research-node-query.md` | 4 处：schema 枚举加 product（L25）；字段说明枚举同步（L38）；选择指南表加 product 行（L81）；选择原则补两句数据边界（L88-89） |
| `plugins/work-skills/skills/deep-research/docs/SEARCH_MIGRATION.md` | 末尾追加 `## v0.7.0：product 通道（Product Hunt）` 节（L71 起），四小节：背景（L73）/通道架构（L77）/数据定位与使用边界（L85）/匿名访问可能收紧（L89） |
| `CHANGELOG.md` | `## Unreleased` 标题后插入 `work-skills 2.4.0` 条目，既有条目（含并行会话写入的 agent-skills 1.5.0）未动 |
| `plugins/work-skills/.claude-plugin/plugin.json` | version 2.3.2 → 2.4.0 |
| `plugins/work-skills/.codex-plugin/plugin.json` | version 2.3.2 → 2.4.0 |

## 验证命令记录

### L1（机械化一致性）

命令 1（委派单指定，绝对路径适配 cwd）：

```
grep -n "product" plugins/work-skills/skills/deep-research/SKILL.md plugins/work-skills/skills/deep-research/agents/research-node-query.md
```

退出码 0。逐行人工核对结论：

**product 枚举三处声明位（一致出现）：**
1. SKILL.md 映射表：L146
2. query 节点 schema：L25（`<academic|code|social_cn|social_en|product|web>`）
3. query 节点选择指南表：L81

**调用约定/子工具位：** SKILL.md L153（子工具选择）、L161（normalize 映射，无包络 JSON 代码块，仅内联字段说明）。

**降级枚举处：**
- SKILL.md L408：`(academic/code/social/product)`——已补 product ✓
- SKILL.md L433（原 L429）：「专门通道失败统一降级到 MCP web-search-prime」为通用表述、无枚举字样，语义覆盖 product，按委派单 c) 无需改文 ✓
- SKILL.md 3.2 降级规则段与 pseudocode：「专门通道」「脚本 success:false」为通用判断，恰好覆盖 producthunt 失败形态（success:false + 退出码 1），未改动 ✓

**其余命中行（非接线位，确认无需处理）：**
- SKILL.md L3（frontmatter v0.7.0 句）、L420/L428（prose 位）
- query 节点 L88-89（选择原则两句）、L147（既有示例查询词 "products vendors"，非通道枚举，既有内容未动）

**包络 JSON 单一出处检查：**

```
grep -rn '"success"' SKILL.md agents/ docs/   # deep-research 目录内
```

退出码 1（零命中）——deep-research 全文档面无包络 JSON 定义；agents/ 下各节点的 ```json 块均为各自输出 schema（clarify/brief/reflect 等），与 producthunt 包络无关。对照组 `grep -n '"success"' plugins/work-skills/skills/sn-search-producthunt/SKILL.md` → L53 唯一命中。包络定义只在 B1 一处 ✓

### L2（红线回归）

```
cd plugins/work-skills/skills/deep-research && PYTHONIOENCODING=utf-8 python scripts/test_state_manager.py
```

退出码 0，`测试结果: 31/31 通过`，无失败无警告（完整输出见上方会话记录；本批未碰该模块，基线保持）。

### 版本一致性

```
grep -n '"version"' plugins/work-skills/.claude-plugin/plugin.json plugins/work-skills/.codex-plugin/plugin.json
grep -n "^version:" plugins/work-skills/skills/deep-research/SKILL.md
grep -c "work-skills 2.4.0" CHANGELOG.md
```

结果：.claude-plugin L4 `"version": "2.4.0"` / .codex-plugin L3 `"version": "2.4.0"` / SKILL.md L4 `version: 0.7.0` / CHANGELOG 含 `work-skills 2.4.0` 1 处。四者一致（2.4.0 / 2.4.0 / 0.7.0）✓

## 验收标准逐条回报

1. **query 节点指南含 product 适用行 — PASS**：research-node-query.md L81（行号证据）；链路演练由主控执行。
2. **降级路径按既有规则触发 — PASS**：L1 核对降级枚举处（SKILL.md L408）一致带上 product；L433 与 3.2 降级规则段为通用表述语义覆盖。
3. **test_state_manager.py 31/31 — PASS**：退出码 0，31/31 通过。
4. **五个文档位表述无矛盾、包络定义只在 B1 一处 — PASS**：映射表（L146）/调用约定（L153、L161）/降级（L408、L433）/实现说明表（L397）/prose（L420、L428）互查一致；`"success"` 包络零命中 deep-research 文档面。
5. **版本三处一致 — PASS**：CHANGELOG `work-skills 2.4.0` / 双 manifest 2.4.0 / frontmatter 0.7.0。

## 实现决策与假设（委派单未明说处的裁量）

1. **枚举位置**：委派单 L25 写「加 `|product`」未指明位置，选择插在 web 之前（`...social_en|product|web>`），L25 与 L38 同步同序——保持 web 作为兜底/默认通道居末的既有语义结构（选择原则「不确定时默认 web」）。
2. **SEARCH_MIGRATION「通道架构表加行」**：实现为 v0.7.0 新节自带架构表（格式仿 v0.5.0 节三列表），不改 v0.5.0 历史节的五通道表——历史节记录当时状态，不追溯修改。
3. **表格行内代码样式**：product 映射表行沿用既有行的反引号包裹命令样式（委派单给的行文本无反引号，视为内容指定而非格式指定）。
4. **CHANGELOG 并行改动**：编辑时文件在读取后被并行会话再次修改（Edit 提示 modified on disk），锚定 `## Unreleased` 标题 + agent-skills 1.5.0 前缀插入，应用干净、既有条目零改动，插入后 head 复核位置正确。

## 范围外发现（未顺手修改）

- 无新增。CHANGELOG 并行会话改动属委派单已知情况，见上。

## 提交状态

未提交未推送（遵守委派单）。改动全部在工作区。
