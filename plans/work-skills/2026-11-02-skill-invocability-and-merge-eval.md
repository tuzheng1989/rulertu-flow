# work-skills 技能可调用性标注与合并评估

- **日期**：2026-11-02
- **状态**：可调用性标注已实施（v2.3.0）；合并建议待决策

---

## 1. 依赖关系实测（不是印象，是 grep 全量结果）

对 22 个技能的 SKILL.md / references / scripts / agents 做交叉引用扫描：

| 依赖边 | 调用方式 | 说明 |
|---|---|---|
| writing-for-human → humanizer | **技能级调用** | 全插件唯一一条：明确写"调用同插件 humanizer 技能"作为写作最后一道工序 |
| deep-research → deepxiv / sn-search-* | **Bash 直调脚本**，不经技能调用 | 路径写死 `../sn-search-code/scripts/...`、`deepxiv search/paper` CLI |
| brainstorm ↔ inspiration-pacemaker | 仅互相提及 | 明确"不自动调用"，移交建议权在用户（三模式整合方案见 [2026-11-02-brainstorm-three-mode-merge.md](2026-11-02-brainstorm-three-mode-merge.md)） |
| strategic-analysis → deep-research | 仅提及 | 事实补全时可联网搜索，非硬依赖 |

**结论：严格意义上"纯依赖、无独立用户价值"的技能为 0 个。** 所有 22 个技能的 description 均面向用户触发词编写。

## 2. 实际标注（宽松标准：用户不点名、只被模型按需拉起）

采用的操作标准：用户表达需求时**从不说工具名**（"搜下 GitHub/知乎"、"帮我找论文"），技能由模型自动触发或被 deep-research 依赖——隐藏出斜杠菜单零损失，只减少菜单噪音。

已设 `user-invocable: false`（模型自动调用不受影响，仅从用户斜杠菜单隐藏）：

| 技能 | 理由 |
|---|---|
| sn-search-code | "搜下 GitHub" 类需求由模型拉起；deep-research code 通道依赖其脚本 |
| sn-search-social-cn | 同上（social_cn 通道） |
| sn-search-social-en | 同上（social_en 通道） |
| deepxiv（**最边缘的一档**） | "帮我找论文/读论文"均自然语言触发；deep-research academic 通道依赖其 CLI。若你习惯 `/deepxiv` 点名，删掉该行即可恢复 |

**未标注**：humanizer 虽被 writing-for-human 技能级调用，但其改稿/检测两种模式本身就是用户直接要的能力（"去 AI 味"），保留可点名。

字段语义备忘（changelog v2.1.0）：`user-invocable: false` = 从斜杠菜单隐藏、模型仍可调用；`disable-model-invocation: true` = 反向（仅用户可点名、模型不能调）。**依赖型技能勿用后者**，会切断依赖方的 Skill 工具调用路径。

## 3. 合并/去重评估

### 3.1 必须处理：完全重复（两处）

| 重复对 | 证据 | 建议 |
|---|---|---|
| `work-skills:paper-to-code` ↔ `~/.claude/skills/paper-to-code` | `diff -rq` 零差异，逐字节相同 | **删用户级副本**，保留插件版（随插件分发更新，且当前技能列表里两个同名竞争触发） |
| `work-skills:url-to-md` ↔ `~/.claude/skills/baoyu-url-to-markdown` | 4 个核心脚本（main/defuddle-converter/legacy-converter/cdp.ts）逐字节相同，url-to-md 是其裁剪版 SKILL.md | 二选一：留 work-skills 版（工具型、输出位置由项目指令决定）则删 baoyu 版；若要跟上游更新则反过来删 work-skills 版。**现状两者在同一触发词上竞争** |

### 3.2 已在途（不重复建议）

- brainstorm + inspiration-pacemaker 三模式整合：方案已评审待实施（见 2026-11-02-brainstorm-three-mode-merge.md）。

### 3.3 可合并：sn-search 三技能 → 一个

- 三者结构完全同构（scripts/ + SKILL.md，90–128 行），同一族搜索通道。
- 方案：合并为 `sn-search`，SKILL.md 做平台路由，脚本目录原样保留。
- **成本（必须一起改）**：deep-research/SKILL.md 中 `../sn-search-*/scripts/` 相对路径约 6 处 + `docs/SEARCH_MIGRATION.md`。合并时同步改写即可。
- 收益：斜杠/技能列表 −2，依赖安装说明合一。已设 user-invocable:false 后菜单收益消失，合并的剩余收益主要是列表整洁——**优先级降低，可做可不做**。

### 3.4 评估过、不建议合并

| 候选对 | 不合并理由 |
|---|---|
| md-to-pdf + html-to-pdf | 输入类型（Markdown/HTML）与转换管线不同，触发词清晰分离；合并只是把两份说明书装进一个目录，无共享逻辑 |
| url-to-md + anydoc-to-md | 输入通道（URL/本地文档）与技术栈（bun+TS / Python+Rust+OCR 路由）完全不同，故障模式互不相干；"都是转 md"是表面相似 |
| deep-research / company-research / strategic-analysis | 工作流正交：搜索循环写报告 / Playwright 爬官网存 JSON 出 DOCX / 思维框架参谋 |
| article-guide + feynman-tutor | 输入对象不同（一篇文章 vs 一个概念）。若想做"学习教练"双模式整合，可参照 brainstorm 三模式方案另立评审，本次不推动 |
