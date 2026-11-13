# work-skills 数据分析整合：sn-da 四件套合并为 data-analysis

- **日期**：2026-11-13
- **状态**：已完成（2026-11-13）——B1 收口（Executor + Auditor + 第二意见 T3 全流程，P1 路径死指针等 5 项修复落地）；B2 收口（升版 2.7.0 + 全仓兜底）；评测基线见后续 agent-evaluator 评测产物
- **目标插件**：work-skills（data-analysis 新增；插件 2.6.0 → 2.7.0）
- **前序方案**：2026-11-13-skill-consolidation（已全部收口；本方案处理其"范围外声明"留待评估的 sn-da 四件套）

---

## 0. 背景与调研结论（锚点已核实）

上轮整合后 skills/ 顶层剩 4 个 sn-da 技能。2026-11-13 用户发起评估，调研结论：

1. **sn-da-image-caption（238 行 + caption.py 415 行）存在必要性低**：caption.py 是 SenseNova vision API 调用包装（`token.sensenova.cn`，sensenova-6.7-flash-lite，依赖 SN_API_KEY 链）；Claude Code 的 Read 工具原生具备视觉理解，外部 API 是冗余依赖。其管道后半段（解析 → DataFrame → 可视化 → Excel/CSV 导出，SKILL.md 107-231 行）是真实价值所在。
2. **三合一可行且同构 write-report 先例**：large-file-analysis（370 行）是 excel-workflow 的显式下游（SKILL.md:45/49/99/143 四处活引用，`>=10k` 行由 workflow 的 Step 2 大文件门触发）；non-spreadsheet-analysis（143 行 + capability/{word,pdf,ppt}-analysis）同属数据分析输入域。
3. **规模**：四技能合计 54 文件；子技能树两棵合计 **47 个 SKILL.md**（excel-workflow capability **44** + non-spreadsheet capability **3**，excel SKILL.md 的 sub-skill 索引表恰 44 条目交叉印证），目录结构原样保留。
4. **互引清单（实核）**：excel-workflow SKILL.md 四处 large-file 活引用（45/49/99/143 行）+ description 引 image-caption（1 处）；large-file SKILL.md 第 3 行 description 两处引用 excel-workflow；capability/doc 树内 **4 个文件**含旧名——table-theme-styling/SKILL.md 12/14 行（Python 注释引用 large-file 技能名）、pdf-analysis:110 / ppt-analysis:182 / word-analysis:185（各 1 处代码常量 `CAPTION = ".../sn-da-image-caption/scripts/caption.py"`）。non-spreadsheet 与 image-caption 的 description 层互引随 frontmatter 删除消除。
5. **外部引用**：evoCenter CLAUDE.md 无 sn-da 引用（rc=1）；本仓其他技能无 sn-da 引用。技能整合后无跨仓联动。

## 1. 路线图

### 批次矩阵

| 批次 | 内容 | 价值 | 成本 | 级 |
|---|---|---|---|---|
| B1 | data-analysis 组建：四合一 + caption.py 删除 + capability 随迁 + 互引清理 | 高（数据分析单入口，消灭 SenseNova 冗余依赖） | 高（四技能内容合并改写） | T3 |
| B2 | 联动收尾：插件升版 + 全仓残留兜底 + 状态回写 | 中 | 低 | T1 |

### 波次依赖

```
B1 组建 ──▶ B2 联动收尾（单波次顺序执行）
```

## 2. 详案

### B1：data-analysis 组建（T3）

**目标布局**：

```
skills/data-analysis/
├── SKILL.md                     # 新写，≤200 行：输入类型路由 + 触发词分流
├── modes/
│   ├── excel.md                 # ← sn-da-excel-workflow/SKILL.md 改写（常规编排六步）
│   ├── document.md              # ← sn-da-non-spreadsheet-analysis/SKILL.md 改写
│   └── image.md                 # ← sn-da-image-caption/SKILL.md 管道改写（视觉直读）
├── references/
│   └── large-file-engine.md     # ← sn-da-large-file-analysis/SKILL.md 改写（≥10k 行引擎）
├── capability/                  # ← excel-workflow 的 capability/ 全树原样随迁
└── doc-capability/              # ← non-spreadsheet-analysis 的 capability/ 随迁（word/pdf/ppt 三件）
```

**设计决策（主控已定夺）**：

1. **基底**：excel-workflow 为主体（capability 树最大），large-file 降为 references 引擎档（由 excel.md 的 Step 2 大文件门按行数指路），document 与 image 为并列输入 mode——与 write-report 的 mode 路由同构。
2. **caption.py 删除，不随迁**：SenseNova 依赖冗余；其"按图片类型选 prompt"启发式（SKILL.md 95-105 行 Prompt Strategy）转写为 image.md 的视觉提取指引（图表/表格/UI 截图/流程图四类各有提取要点）。caption.py 的工程便利（批量/缓存/压缩）随删除一并放弃——本机会话直读替代，`scripts/` 不随迁。
3. **image.md 管道语义转换**：数据源从"caption.py 输出文本"改为"会话视觉直读图片"，SKILL.md 107-231 行的解析/可视化/导出管道步骤保留（DataFrame 化、CJK 字体、调色板、Excel 导出均为真实资产）。
4. **doc-capability 命名**：non-spreadsheet 的 capability/（word/pdf/ppt 三件）与 excel 的 capability/ 同名冲突，随迁时改目录名 `doc-capability/`，目录结构与文件集合不变；树内路径引用同步更新（见决策 7）。
5. **触发词分流**（SKILL.md description，四组合并）：Excel 分析/透视表/分组统计等 → excel；Word/PDF/PPT 解析/发票提取/多文档对比 → document；图表提取/表格识别/OCR/截图转表格 → image；大文件/Parquet/流式读取 → excel（large-file 档）。**互斥边界写明**：图片编辑与生成不归本技能；文档格式转换归 anydoc-to-md（本技能管分析不管转换）；报告成稿与改写归 write-report。
6. **互引清理**：excel.md 四处 `sn-da-large-file-analysis` 活引用（45/49/99/143 行）→ `references/large-file-engine.md` 相对路径；description/frontmatter 层互引随删 frontmatter 消除。
7. **树内旧名引用处置（4 个文件，随迁后小改）**：
   - `capability/excel-table-styling/table-theme-styling/SKILL.md` 12/14 行 Python 注释中的技能名引用 → 改指 `references/large-file-engine.md`；
   - `doc-capability/{pdf,ppt,word}-analysis/SKILL.md` 各 1 处代码常量 `CAPTION = ".../sn-da-image-caption/scripts/caption.py"`（指向将被删除的 caption.py 的死引用）→ 该调用段改写为视觉直读指引（删除死常量，注明图片理解由会话视觉直读完成、流程见 `../modes/image.md`）；
   - **除以上 4 个文件外，两棵子技能树随迁零内容改动**（rename 追踪核验范围为其余全部文件）。

**改动清单**：

1. 先建 `data-analysis/` 父目录；`git mv sn-da-excel-workflow/capability data-analysis/capability`；`git mv` doc 三件 → `data-analysis/doc-capability/`。
2. `git mv` 四份 SKILL.md → 新位置（excel.md / large-file-engine.md / document.md / image.md）后改写：
   - 各文件删 frontmatter（不再是顶层 skill），加前缀行（`> 本文件为 data-analysis 的 <名>（原 sn-da-<X> skill，2026-11-13 组建）。入口与路由见 SKILL.md。`）
   - 互引清理 + 路径修正（capability 树路径、doc-capability 路径、大文件门指路）
   - excel.md 四处大文件门（45/49/99/143 行）：`Load sn-da-large-file-analysis skill` → `读 references/large-file-engine.md 并按其模式执行`
   - image.md：删 caption.py 用法节（16-94 行区域），保留管道节（107-229 行：Parsing Caption Results → Multi-Image Processing）改写数据源为视觉直读；Prompt Strategy（95-105 行）转写为四类图片的提取指引；Common Pitfalls（231-238 行）四条 caption 专属指引（Always caption first / Use --prompt / caption in two passes / Timeout）随 caption.py 删除或改写为视觉直读对应指引（超时类转为大图处理提示）
3. 按决策 7 处置 4 个文件的树内旧名引用（table-theme-styling + doc 三件）。
4. `git rm sn-da-image-caption/scripts/caption.py`（SenseNova 依赖，不随迁）。
5. 新写 `SKILL.md`（≤200 行）：frontmatter（name: data-analysis + 四组合并触发词 + 互斥边界）+ 输入类型路由表（扩展名 → mode）+ 各 mode 一句话定位 + capability/doc-capability 索引。frontmatter 风格对齐 write-report（name+description 简式）。
6. 四个源目录清零。

**如何验证**：

- L1 机械：`grep -rn "sn-da-" skills/data-analysis/` 零命中；`grep -rn "sensenova\|SN_API_KEY" skills/data-analysis/` 零命中；SKILL.md `wc -l` ≤ 200；capability 树 47 个 SKILL.md 计数守恒；顶层 `ls | grep sn-da` 零输出。
- L2 冒烟（真跑，不 mock）：
  - excel：构造小 xlsx（2 Sheet 简单数据），subagent 只读 data-analysis 文档执行分析 → 走 excel.md 流程产出统计结果
  - image：提供一张含表格的截图，subagent 只读文档执行提取 → 视觉直读产出结构化数据（不调外部 API）
- L3 路由推演：4 输入类型 + 边界 case（图片编辑请求应拒、文档转换请求应指 anydoc-to-md、报告改写应指 write-report），subagent 只读文档输出路由决策。

**验收标准**：

- [ ] grep 三条零命中（旧名 / sensenova / 顶层 sn-da）
- [ ] SKILL.md ≤ 200 行且四组触发词 + 互斥边界齐全
- [ ] capability 44 + doc-capability 3 = 47 个 SKILL.md 随迁计数守恒，除决策 7 的 4 个文件外树内零内容改动且无旧名残留
- [ ] excel 冒烟：小 xlsx 走 excel.md 六步产出正确统计
- [ ] image 冒烟：表格截图视觉直读产出结构化数据，全程无外部 API 调用
- [ ] 路由推演 7 条：4 类型正路由 + 3 边界正确分流/拒绝

**代码评审节点**：excel.md 大文件门改写后 ≥10k 判定逻辑保真；image.md 视觉直读指引是否足以替代 caption prompt 启发式；doc-capability 改名后 document.md 与三件内部路径一致性；除决策 7 的 4 个文件外两树随迁零内容改动（rename 追踪 + staged diff 核验）。

**分级依据**：T3——四技能契约合并改写、删除外部依赖脚本（caption.py）、新路由无既有测试覆盖；同 write-report 先例。

### B2：联动收尾（T1）

**如何改**：

1. `plugins/work-skills/.claude-plugin/plugin.json`：version 2.6.0 → 2.7.0（description 已含"数据分析"，B3 时已更新，不动）。
2. 根 `.claude-plugin/marketplace.json`：无 version 字段（B3 已确认），work-skills description 与 plugin.json 逐字一致（B3 已统一），不动。
3. 全仓残留兜底：`grep -rn "sn-da" --include="*.md" --include="*.json"` 仅允许命中历史方案文档与证据目录；skills/ 与插件 manifest 零命中。
4. 方案状态回写。

**如何验证**：版本核验 + 全仓 grep 兜底 + 红线复查（上两方案验收命令复跑）。

**验收标准**：

- [ ] plugin.json version=2.7.0，两 manifest description 逐字一致
- [ ] 全仓 `grep -rn "sn-da"` skills/ 与 manifest 零命中
- [ ] 前序红线（deep-research 两条、write-report 互引一条）仍零命中

**代码评审节点**：version 单处改动无连带；两 manifest 一致性核验方式可靠；grep 兜底范围覆盖 skills/ 与两个 manifest。

**分级依据**：T1——加法式版本改动 + grep 兜底，无契约邻近。

## 3. 风险与回滚

| 风险 | 缓解 | 回滚 |
|---|---|---|
| capability/doc-capability 树随迁夹带计划外内容改动 | git mv rename 追踪；除决策 7 的 4 个文件外 staged diff 核验零行变化 | git revert B1 提交 |
| image.md 视觉直读指引不足以替代 caption prompt 启发式 | 冒烟用真实表格截图验证提取质量；不足时在 image.md 补充分类提取要点 | git 恢复 image-caption 目录 |
| doc-capability 改名后内部路径断裂 | document.md 与三件 SKILL.md 路径逐一核验 + grep 兜底 | 同 B1 revert |
| 旧名残留引发路由歧义 | 三条 grep 零命中硬验收 + B2 全仓兜底 | 同上 |

## 4. 范围外声明

- anydoc-to-md 与 document mode 的边界只在 SKILL.md 分流表述中写清，不改 anydoc-to-md 任何文件。
- work-summary、其他顶层技能不动。
- 双技能评测基线（2026-11-13-skill-eval）不含 data-analysis；新技能评测另行发起。
