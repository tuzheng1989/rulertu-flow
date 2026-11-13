---
name: write-report
description: |
  报告与长文档工作台：上层是三个报告 mode——compose（成稿与改写）、audit（引用审计）、
  format（报告格式研究）；下层是源自 long-text 的长文档引擎（创建 / 导入 / 编辑三模式 +
  Writer/Reviewer/Analyzer/Converter Subagent 协作架构）。

  **报告 mode 触发分流**：
  - 「写 / 改 / 润色 / 压缩 / 扩写 报告」→ compose mode（成稿与改写）
  - 「核查引用 / 查证出处 / 怀疑幻觉」→ audit mode（引用与参考文献真实性审计）
  - 「这类报告该长什么样 / 章节结构规范」→ format mode（报告格式与结构研究）

  **引擎模式触发**：
  - 创建模式：用户说"帮我写份长文档"、"写个手册/教程/书稿"、"从零开始写"（创作型长文档，无现成材料；注意：研究报告类的"写报告"优先走上方 mode 路由）
  - 导入模式：用户说"导入文档"、"把这份文档转成章节工作区"、"基于...改写"
  - 编辑模式：用户说"编辑文档"、"修改第X章"、"更新内容"

  与 deep-research 的分工：deep-research 负责从零调研、联网取证与迭代搜索循环；
  write-report 负责成稿后处理——已有 deep-research 产物或任意文稿要改写、审计引用、
  研究报告格式，或进行长文档创作与编辑。用户没有现成材料而要求"深度研究/调研"时，
  优先 deep-research。
---

# write-report — 报告与长文档工作台

## 定位

write-report 是报告成稿后处理与长文档创作的单一入口。上层三个报告 mode 各自自包含（输入、输出、流程、边界见 `modes/` 对应文档），底层长文档引擎解决大模型写长文档的两大核心问题：

1. **Token 限制**：单次输出无法覆盖完整文档
2. **一致性难题**：多次输出导致结构和风格不一致

引擎方法：固定章节结构骨架 + 统一风格指南，Writer 逐章创作、Reviewer 审查、循环修改直到达标，最后脚本合并。

```
输入需求 → 创建稳定结构骨架（章节大纲，固定）→ 定义统一风格标准（风格指南，固定）
→ Writer 撰写章节 → Reviewer 审查质量 → 循环修改直到达标 → 自动整合最终文档
→ 输出完整长文档
```

## mode 路由

| mode | 用途 | 典型触发语 |
|---|---|---|
| compose | 报告成稿与改写（终稿生成 / 写作修改） | 「写 / 改 / 润色 / 压缩 / 扩写 报告」 |
| audit | 引用与参考文献审计（P0-P3 分级报告，不自动改报告） | 「核查引用 / 查证出处 / 怀疑幻觉」 |
| format | 报告格式与结构研究（独立使用，或为 deep research 的 report_shape 提供依据） | 「这类报告该长什么样 / 章节结构规范」 |

命中后读取 `modes/<mode>.md` 并严格按该文档执行。

**与引擎的分流**：面向读者交付的研究 / 分析 / 调研报告（尤其已有研究材料或文稿）走 compose；手册、教程、书稿、技术报告等创作型长文档，或需要分章工作区 + Subagent 协作流程的，走引擎模式。泛化的「写个报告」且无现成材料时：研究报告 → 引导先经 deep-research 取得材料再走 compose；创作型长文档 → 走引擎创建模式；无法判断 → 询问用户。

**长文档请求不进 mode**，直接按下方引擎模式判断执行。

## 引擎模式

### 模式判断流程

```
用户请求
    │
    ├─> 包含"导入"、"转换"、"从<某份文档>开始"、"基于<现有文档>"？
    │   └─> YES → 导入模式
    │
    ├─> 包含"创建"、"写"、"生成"、"撰写"？且无"从"字
    │   └─> YES → 创建模式
    │
    ├─> 包含"编辑"、"修改"、"更新"、"优化"、"调整"等关键词？
    │   └─> YES → 检查是否有现有引擎工作区
    │       ├─> 有 → 编辑模式
    │       └─> 无 → 提示先创建或导入
    │
    └─> 不明确 → 询问用户意图
```

### 三种模式对比

| 特征 | 创建模式 | 导入模式 | 编辑模式 |
|-----|---------|---------|---------|
| 触发条件 | 从零开始创建 | 导入现有文档 | 已有文档需修改 |
| 输入来源 | 用户需求描述 | 文档/网页/粘贴 | 引擎工作区 |
| 首步操作 | 创建结构大纲 | 获取并分析文档 | 定位目标章节 |
| 核心输出 | 全套章节文件 | 转换后的章节文件 | 修改后的章节 |
| 使用 Subagent | Writer, Reviewer | Analyzer, Converter, Writer, Reviewer | Writer, Reviewer |

各模式完整操作手册（命令、代码块、模板引用）：`references/engine/`。

### Subagent 架构

| Subagent | 职责 |
|---|---|
| Writer | 逐章撰写内容，遵循结构大纲与风格指南；修改模式下按 Reviewer 建议定向修改 |
| Reviewer | 对照结构大纲与风格指南审查所有章节（结构合规、风格一致、段落质量、格式规范、术语使用、整体连贯） |
| Analyzer | 导入模式：分析文档元信息、章节层级、内容特征与语言风格，产出结构分析（JSON） |
| Converter | 导入模式：按结构分析将原始文档转换为引擎范式的 chapter-*.md 章节文件 |

协作关系：Writer 产出 → Reviewer 审查 → 不通过则 Writer 修改（循环最多 3 次，超过报告用户请求人工介入）；导入模式先由 Analyzer 结构分析，Converter 按分析结果切章。四个 Subagent 定义随技能分发于 `.claude/agents/`。

> 术语：引擎源自合并前的 long-text 技能，下述文件中出现的 "Long-Text 范式 / Long-Text 系统 / long-text 工作区" 字样均指本引擎，同义。

### 工作区概念

引擎工作区是一个目录：`00-structure.md`（章节大纲，固定）、`00-style-guide.md`（风格指南，固定）、`00-source-info.md`（导入模式的原始文档信息）、`chapter-*.md`（各章内容）、`final-output.md`（`scripts/merge.py` 整合产物）；导入模式工作区另含 `references/`（原始内容与索引）。文件体系与输出清单详见 `references/engine/workspace-and-files.md`。

## 资产索引

| 路径 | 用途 |
|---|---|
| `modes/compose.md` / `modes/audit.md` / `modes/format.md` | 三个报告 mode 的完整执行契约（自包含） |
| `references/engine/import-mode.md` | 导入模式 7 Step 完整手册 |
| `references/engine/create-edit-modes.md` | 创建模式与编辑模式完整流程及快速示例 |
| `references/engine/workspace-and-files.md` | 工作区文件体系与输出清单 |
| `references/engine/practices-troubleshooting.md` | 引擎最佳实践与故障排除 |
| `references/writing-styles.md` | 写作风格参考库 |
| `references/document-structures.md` | 文档结构参考库 |
| `references/import-guidelines.md` | 导入模式使用指南 |
| `templates/` | 5 个模板：结构大纲、从文档生成结构、风格指南、源信息、单章节 |
| `scripts/merge.py` | 章节整合脚本（所有模式） |
| `scripts/parse-pdf.py` / `scripts/parse-docx.py` | PDF / DOCX 解析（分别需要 PyMuPDF / python-docx） |
| `examples/import-example/` | 导入示例 |
| `.claude/agents/` | Writer / Reviewer / Analyzer / Converter 四个 Subagent 定义 |
| `LICENSE.txt` | MIT 许可证 |
