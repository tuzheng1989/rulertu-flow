# B2 委派单：write-report 组建（long-text 引擎 + 三 mode）

- 方案：plans/work-skills/2026-11-13-skill-consolidation.md（详案第 2 节 B2，T3）
- 证据目录：plans/work-skills/.flow-evidence/2026-11-13-skill-consolidation/B2/
- 仓库：C:\Users\tuzhe\runspace\rulertu-flow（Windows Git Bash）
- 纪律：**不 git commit**；用 `git mv` 保 rename 追踪；只动边界内文件；版本号（插件/根 manifest）不动（B3 管）

## 目标

把 `long-text`（通用长文档引擎）、`sn-research-report`（成稿）、`sn-report-audit`（引用审计）、`sn-report-format-discovery`（格式研究）四个顶层技能合并组建为单一技能 `skills/write-report/`，删除四个原目录。

## 目标布局（含主控补充裁定）

```
skills/write-report/
├── SKILL.md                # 新写，≤200 行：定位、mode 路由表、触发词分流、引擎精华
├── LICENSE.txt             # ← long-text 原样随迁
├── .claude/agents/         # ← long-text 四 Subagent 定义原样随迁（引擎架构，方案布局图未点名，主控裁定随迁）
│   ├── analyzer.md / converter.md / reviewer.md / writer.md
├── modes/
│   ├── compose.md          # ← sn-research-report/SKILL.md（329 行）改写
│   ├── audit.md            # ← sn-report-audit/SKILL.md（121 行）改写
│   └── format.md           # ← sn-report-format-discovery/SKILL.md（274 行）改写
├── references/
│   ├── writing-styles.md / document-structures.md / import-guidelines.md   # ← long-text 原样随迁
│   └── engine/             # 新增：long-text SKILL.md 正文的操作细节拆分（主控裁定，见"引擎收敛规则"）
├── templates/              # ← long-text 5 个模板原样随迁
├── scripts/                # ← long-text 3 个 py 原样随迁（merge/parse-docx/parse-pdf）
└── examples/               # ← long-text import-example/ 原样随迁
```

## 改动清单

### A1. 资产随迁（git mv，纯 rename 零内容改动）

- `long-text/references/` 3 文件 → `write-report/references/`
- `long-text/templates/` 5 文件 → `write-report/templates/`
- `long-text/scripts/` 3 py → `write-report/scripts/`（若存在 __pycache__ 不迁移，删）
- `long-text/examples/` → `write-report/examples/`
- `long-text/.claude/agents/` 4 文件 → `write-report/.claude/agents/`
- `long-text/LICENSE.txt` → `write-report/LICENSE.txt`

### A2. 引擎收敛（long-text/SKILL.md 785 行 → 主文档精华 + references/engine/ 细节）

**主控裁定规则**（实现方案要点 1"精华写入主文档，细节留 references/"，风险表"不删节引擎说明"）：

- **进新 SKILL.md 的精华**：Overview 定位、模式选择判断流程（创建 vs 编辑 vs 导入）、三种模式对比表、Subagent 架构分工概述（Writer/Reviewer/Analyzer/Converter 各一句职责 + 协作关系）、工作区概念简介、指向 references/engine/ 的索引。
- **拆到 references/engine/ 的细节**（按主题分文件，文件名自定但语义清晰，例如）：
  - 导入模式完整 7 Step 操作手册（含命令、代码块、模板引用）
  - 创建模式与编辑模式的完整流程
  - 工作区与 00-structure/00-style-guide/00-source-info 文件体系说明
  - 参考资料处理、最终整合等末端流程
- 拆分原则：**内容零丢失**（删除的只有重复导航语，技术内容、命令、模板引用全部保留在新位置）；references/engine/ 各文件头部注明"本文件为 write-report 引擎细节，入口见 SKILL.md"。

### A3. 三份 mode 文档改写（git mv 保追踪 + 内容改写）

- `git mv sn-research-report/SKILL.md write-report/modes/compose.md`（audit、format 同法），然后改写：
  1. **删 YAML frontmatter**（mode 文档不是顶层 skill，frontmatter 失效）；正文最前加一行说明：`> 本文件为 write-report 的 compose mode（原 sn-research-report skill，2026-11-13 组建进 write-report）。执行入口与 mode 路由见 SKILL.md。`
  2. **互引清理**：正文中"请用 sn-research-report / sn-report-audit / sn-report-format-discovery"类跨 skill 指引改为 mode 语义（"先回 SKILL.md 路由，选择对应 mode"或直接指向对方 mode 文档相对路径）。**对 deep-research 的引用保留**（跨技能分工指引，B1 已接线）。
  3. **统一术语**：报告、研究材料、来源数据（替换各文档自创的"稿件/素材/语料"等不一致叫法，仅在造成歧义处替换，不做全文同义替换）。
  4. **自包含契约**：每个 mode 文档完整保留自己的输入要求、输出产物、执行流程、边界声明（验收 3）；实现细节允许留路标（如"长文档分段编辑操作见 ../SKILL.md 引擎模式与 references/engine/"）。
  5. **compose.md 专项**：明确两种输入入口——① deep-research 产物目录（report.md + research-process.md + sources.json）；② 任意已有文稿路径。原文已有此语义，改写时让它成为显式小节。
  6. **audit.md 专项**：「仅产出分级审计报告（P0-P3），不自动改报告，修正建议经用户确认」的边界表述**原文保留**，一字不改。
  7. **format.md 专项**：保留"完全独立可复用 + 可嵌入 deep research 工作流（report_shape 依据）"的双重定位表述。

### A4. 新写 SKILL.md（≤200 行，硬约束）

结构建议（行数预算供参考，不是硬性小节划分）：

1. **YAML frontmatter**：`name: write-report`；`description` 含触发词分流（见下）；`user-invocable` 按仓库同类 skill 惯例（看 skills/ 下其他顶层技能的写法对齐）。
2. **定位段**（≤10 行）：write-report 是什么、与 deep-research 的分工（成稿后处理 vs 从零调研）。
3. **mode 路由表**：三行——mode 名、用途一句话、典型触发语。
4. **触发词分流**（方案要点 5 原文，全部写入 description 与正文路由表）：
   - 「写 / 改 / 润色 / 压缩 / 扩写 报告」→ compose
   - 「核查引用 / 查证出处 / 怀疑幻觉」→ audit
   - 「这类报告该长什么样 / 章节结构规范」→ format
5. **引擎精华**（见 A2 清单，约 60-90 行预算）。
6. **资产索引**：references/（3 主题文件 + engine/）、templates/、scripts/、examples/、.claude/agents/ 各一行用途说明。

### A5. 原目录清零

4 个源目录（long-text、sn-research-report、sn-report-audit、sn-report-format-discovery）经 git mv 后顶层无残留。

## 设计决策（主控已定夺）

1. `.claude/agents/` 与 LICENSE.txt 随迁（方案布局图未点名，按"引擎架构不删节"精神裁定）。
2. 引擎细节拆 `references/engine/`（方案"细节留 references/"的可落地解释）。
3. mode 文档自包含 = **契约自包含**（输入/输出/流程/边界），实现细节可留路标。
4. compose 与 long-text 引擎的场景重叠**不做流程融合**（方案只要求互引清理与术语统一；重叠兑现已由"同入口"达成）。执行中若发现源文档间实质矛盾（同一操作两套说法），停下上报，不自行裁决。
5. 版本号、插件 manifest、deep-research SKILL.md 产物后处理段——全部 B3。

## TDD 边界

- 无新代码逻辑（scripts 原样随迁），**不写新单元测试**。
- 回归接缝：随迁后的 3 个 py 脚本各跑一次最小加载验证（`--help` 或文档内最小调用），证明随迁可执行。
- 行为冒烟（验收 4）见下节，真实执行不 mock。

## 定向测试映射（锚点 → 命令/验证）

| 锚点 | 验证 |
|---|---|
| A1 资产随迁 | `git status --porcelain` rename 全程 R 追踪；`find write-report -type f \| wc -l` 与源清单一致（17 项随迁 + 3 mode + 1 SKILL.md + engine 新文件） |
| A2 引擎收敛 | 新 SKILL.md `wc -l` ≤ 200；references/engine/ 文件齐全；**零丢失核验**：long-text/SKILL.md 的每个二级标题主题在 [新 SKILL.md ∪ references/engine/] 中可找到对应内容（Executor 自查 + 列映射表进日志） |
| A3 mode 改写 | `grep -rn "sn-research-report\|sn-report-audit\|sn-report-format-discovery" skills/write-report/` 零命中（方案验收 2 原文）；audit.md 边界句原文保留（diff 可证） |
| A4 SKILL.md | `wc -l` ≤ 200；触发词三组全在 description 与路由表 |
| A5 清零 | `ls \| grep -E "long-text\|sn-research-report\|sn-report-audit\|sn-report-format-discovery"` 零输出 |
| 脚本随迁回归 | 3 个 py 各一次最小加载验证 |
| 验收 4 冒烟 | 见下节 |

## 验收 4 冒烟：audit mode 行为验证

1. 在证据目录构造样稿 `smoke-sample.md`：3-5 段小报告，含 3 条引用，其中 1 条为**明显幻觉**（虚构不存在的论文/作者/数据，风格仿真但可判定），1 条真实可核（如 anthropics/claude-code 官方页），1 条格式瑕疵（著录字段缺失）。
2. **严格按 audit.md 文档流程执行**（Executor 自己作为执行者走查文档，模拟"新会话只读 audit.md 能否执行"）：产出分级审计报告 `smoke-audit-report.md` 落证据目录。
3. 断言：① 幻觉引用被标 P0（或文档规定的最高级）；② 格式瑕疵被检出；③ `smoke-sample.md` 内容零改动（执行前后 `git hash-object` 或 diff 对比）；④ 审计报告含修正建议但未直接改样稿。
4. 联网核验按 audit.md 自身规则执行；若流程要求外部搜索，一条幻觉引用做真实验证即可，成本控制在样稿规模。

## 回报要求

- 完整日志写 `evidence/B2/executor-log.md`：改动清单（rename 记录）、A2 主题→去向映射表、每条验收命令与退出码、冒烟产物与断言结果。
- 冒烟产物（smoke-sample.md、smoke-audit-report.md）落证据目录。
- 发现源文档间实质矛盾或方案歧义时停下上报，不自行扩改。
