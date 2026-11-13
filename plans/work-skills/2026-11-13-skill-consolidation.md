# work-skills 技能整合：搜索通道收编 + write-report 组建

- **日期**：2026-11-13
- **状态**：B1 已收口（2026-11-13，Executor+Auditor T2 全流程，验收 10/10；独立评审经用户裁定跳过）；B2 待开工；B3 待开工
- **目标插件**：work-skills（deep-research 0.7.0 → 0.8.0；插件 2.5.0 → 2.6.0；新增 write-report 1.0.0）
- **关联仓**：evoCenter（vault，仅 CLAUDE.md 引用联动，无代码改动）

---

## 0. 背景与已完成（M0 物理迁移，已执行未提交）

2026-11-13 已将 evoCenter `.claude/skills/` 下 8 个 skill 物理迁入本仓 `plugins/work-skills/skills/`：

| 迁入 skill | 规模 | 去向（本方案） |
|---|---|---|
| sn-search-image | 48 行 + 1 脚本 | B1 → deep-research image 通道 |
| sn-research-report | 329 行 | B2 → write-report modes/compose |
| sn-report-audit | 121 行 | B2 → write-report modes/audit |
| sn-report-format-discovery | 274 行 | B2 → write-report modes/format |
| sn-da-excel-workflow | 288 行 + capability/×10 | 留 skills/ 顶层，不整合 |
| sn-da-image-caption | 238 行 + scripts | 留 skills/ 顶层，不整合 |
| sn-da-large-file-analysis | 370 行 | 留 skills/ 顶层，不整合 |
| sn-da-non-spreadsheet-analysis | 143 行 + capability/×2 | 留 skills/ 顶层，不整合 |

- sn-search-image 已补 `user-invocable: false`（与既有 sn-search-* 通道系列一致）。
- 两仓当前均为未提交状态：evoCenter 侧 8 个目录为未暂存删除（D），本仓侧为 untracked 新增。**建议 B1 开工前两仓各自提交一次，建立回滚锚点。**
- evoCenter 剩余 5 个（agnes-image、agnes-video、llm-wiki、obsidian-canvas-creator、pelago）为 vault 特定技能，不再迁移。
- gongwen-docx 原列迁移项，用户已于当日自行删除，该项作废。

### 调研结论（已核实，执行代理免复测）

1. **deep-research 通道架构**：web=MCP、academic=deepxiv CLI、code / social_cn / social_en / product = sn-search-* 脚本（`user-invocable: false`，其 SKILL.md 仅为子命令契约文档）。deep-research 的 SKILL.md 以跨目录相对路径 `../sn-search-*/scripts/...` 引用，目录重组即断。
2. **config.json 路径残留 bug**：`channels` 区 4 处 script entry 写的是 `.claude/skills/sn-search-*/scripts/...`（项目本地旧布局），与 SKILL.md 实际路径不一致。orchestrator.py 不消费该文件，属文档性误导，B1 一并修正。
3. **deep-research 自带 finalize 成稿环节**（research-node-finalize 直接产出 report.md / research-process.md / sources.json），与 sn-research-report 全文零引用、纯松耦合——报告类整合为独立 skill（write-report）而非并入 deep-research 的依据。
4. **long-text（785 行）是通用长文档引擎**：创建/导入/编辑三模式 + Writer/Reviewer/Analyzer/Converter Subagent 架构 + templates/references/scripts/examples 齐全，与 sn-research-report 的成稿/改写场景高度重叠，四合一是兑现既有重叠而非强行捏合。

---

## 1. 路线图

### 批次矩阵

| 批次 | 内容 | 价值 | 成本 | 级 |
|---|---|---|---|---|
| B1 | 搜索通道收编：5 个搜索 skill 移入 deep-research 内部，接线 + 修旧路径 | 高（消灭跨目录相对路径，通道退役即删子目录） | 中（动 deep-research 契约文件） | T2 |
| B2 | write-report 组建：long-text 为引擎 + compose / audit / format 三 mode | 高（成稿、改稿、审计、格式研究单入口） | 高（四 skill 内容合并改写） | T3 |
| B3 | 联动收尾：版本号、描述、衔接段、evoCenter CLAUDE.md | 中 | 低 | T1 |

### 波次依赖

```
B1 搜索收编 ─┐
             ├──▶ B3 联动收尾
B2 write-report ─┘        （B1 与 B2 相互独立，可并行；B3 依赖两者）
```

---

## 2. 详案

### B1：搜索通道收编（T2）

**目标布局**：

```
deep-research/
├── scripts/
│   ├── orchestrator.py
│   ├── state_manager.py
│   └── channels/                 # 新增：全部搜索通道落位于此
│       ├── code/                 # ← sn-search-code
│       ├── social_cn/            # ← sn-search-social-cn
│       ├── social_en/            # ← sn-search-social-en
│       ├── product/              # ← sn-search-producthunt
│       └── image/                # ← sn-search-image（新增通道）
```

每个 channel 子目录保留原 scripts/、requirements.txt，原 SKILL.md 改名为 `CHANNEL.md`（通道契约文档，含子命令、输入输出 JSON 包络、依赖）。

**改动清单**：

1. 移动 5 个目录进 `scripts/channels/`（目录名映射：code / social_cn / social_en / product / image，与既有通道键一致）。
2. `SKILL.md` 通道表更新：4 处 `../sn-search-*/scripts/` → `scripts/channels/*/scripts/`；通道表新增 image 行。
3. image 通道定义：Bash 调 `scripts/channels/image/scripts/serper_image_search.py "{query}" --num N --json`，输出 `{title, imageUrl, pageUrl, source_domain}` 映射为标准 `items[]` 包络；env `SERPER_API_KEY`，缺失时 fallback web；定位为 web 通道的配图/视觉证据增强，`source_tier: secondary`。
4. `config.json`：channels 区整体重写为 channels/ 新路径；删除 `.claude/skills/` 旧前缀残留；新增 image 条目。
5. `SEARCH_MIGRATION.md` 补一节：2026-11-13 五通道物理收编 + image 通道上线记录。
6. work-skills/skills/ 下 5 个 sn-search-* 目录清零。

**验收**：

- [ ] 四个脚本通道各跑一次冒烟（code 通道 GitHub 搜索匿名可用；image 无 key 时验证参数校验报错路径而非栈崩溃）。
- [ ] `grep -r "\.\./sn-search-" deep-research/` 零命中；`grep -r "\.claude/skills/" deep-research/` 零命中。
- [ ] `ls plugins/work-skills/skills/ | grep sn-search` 零命中。

### B2：write-report 组建（T3）

**目标布局**：

```
skills/write-report/
├── SKILL.md                # 短入口（≤200 行）：定位、mode 路由表、触发词分流
├── modes/
│   ├── compose.md          # ← sn-research-report：成稿与改写
│   ├── audit.md            # ← sn-report-audit：引用与参考文献审计
│   └── format.md           # ← sn-report-format-discovery：格式与结构研究
├── references/             # ← long-text：writing-styles / document-structures / import-guidelines
├── templates/              # ← long-text
├── scripts/                # ← long-text（含可保留的脚本资产）
└── examples/               # ← long-text（import-example 随迁）
```

**内容改写要点**：

1. long-text 三模式（创建/导入/编辑）与 Subagent 架构为 write-report 底层引擎，精华写入 SKILL.md 主文档，细节留 references/。
2. 三份 mode 文档改写：删除互相「请用 XX skill」的跨 skill 引用，统一术语（报告、研究材料、来源数据）；各 mode 独立可读，不依赖 modes/ 之外文件即可执行。
3. compose mode 明确两种输入入口：deep-research 产物目录（report.md + research-process.md + sources.json）/ 任意已有文稿路径。
4. **audit 边界原样保留**：仅产出分级审计报告（P0-P3），不自动改报告，修正建议经用户确认——合并不改变此解耦设计。
5. description 触发词分流：「写/改/润色/压缩/扩写报告」→ compose；「核查引用/查证出处/怀疑幻觉」→ audit；「这类报告该长什么样/章节结构规范」→ format。
6. 删除 4 个原目录：long-text、sn-research-report、sn-report-audit、sn-report-format-discovery。

**验收**：

- [ ] SKILL.md ≤ 200 行。
- [ ] `grep -rn "sn-research-report\|sn-report-audit\|sn-report-format-discovery" skills/write-report/` 零命中（互引清理）。
- [ ] 三份 mode 文档各自可独立执行（自包含输入输出契约）。
- [ ] 新旧场景冒烟：拿一段带幻觉引用的样稿走 audit mode，产出 P0-P3 报告且未改动原文。

### B3：联动收尾（T1）

1. `plugins/work-skills/.claude-plugin/plugin.json`：2.5.0 → 2.6.0，description 补「数据分析、报告成稿与审计」。
2. 根 `.claude-plugin/marketplace.json` 的 work-skills 条目描述同步。
3. deep-research：版本 0.7.0 → 0.8.0，description 补 image 通道一句；SKILL.md 末尾新增「产物后处理」段——report.md 生成后可选接 write-report（compose 改稿 / audit 审计），指引而非自动执行。
4. evoCenter `CLAUDE.md`：调研工作表中 sn-research-report / sn-report-audit / sn-report-format-discovery 三行收敛为一行 write-report（write-report 组装后）。
5. （B1 收口移交）channels/ 内旧布局路径清理：三个 CHANNEL.md 依赖安装指引（code / social_cn / social_en）与三个 search_utils.py 缺 httpx 运行时报错指引的 `skills/sn-search-<X>/requirements.txt` → 新路径；SEARCH_MIGRATION.md 收编节代码围栏排版修正；producthunt_search.py User-Agent 是否更名定夺。

**验收**：

- [ ] 两处插件描述与版本号一致。
- [ ] evoCenter CLAUDE.md 无失效 skill 引用（本地已删的 sn-* 三件套不再被点名）。

---

## 3. 风险与回滚

| 风险 | 缓解 | 回滚 |
|---|---|---|
| B1 移动后通道路径断裂 | 移动与改引用同批完成，验收 grep 兜底 | git revert B1 提交 |
| B2 合并后触发歧义（审计被当改稿调） | description 写明分流词；audit「不自动改报告」边界原文保留 | git 恢复 4 个原目录 |
| mode 文档丢失 long-text 细节 | references/templates/examples 原样随迁，主文档只做收敛不删节引擎说明 | 同上 |
| M0 未提交状态被后续批次污染 | B1 开工前两仓各提交一次（evoCenter 记录 D，本仓记录 untracked 新增） | 提交锚点即回滚点 |

## 4. 范围外声明

- sn-da 四件套保持 skills/ 顶层独立（内部 capability/ 相对编排不受 B1/B2 影响），后续视使用频率再评估是否组包。
- agnes-image / agnes-video 留 evoCenter，未迁入（与 work-skills 定位契合度一般，待定）。
- evoCenter 侧 nuwa-skill / update-project / youtube-transcript / gongwen-docx 已由用户自行删除，与本仓无关。
