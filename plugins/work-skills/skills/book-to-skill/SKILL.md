---
name: book-to-skill
description: Convert a user-provided book, manual, long article, course transcript, podcast transcript, or video transcript into an installable Codex or OpenCode Skill or selective Skill Pack. Use when an agent must preserve source chapters faithfully, compress explanatory knowledge for retrieval, distill transferable methods into executable skills, or plan a controlled hybrid of those outputs. Supports PDF, EPUB, DOCX, HTML, RTF, Markdown, text, MOBI, and AZW inputs through host capabilities or bundled extraction tools.
---

# Book to Skill

把长内容转换为 Agent 可安装的 Skill。始终保持 Agent 为控制层：由 Agent 理解内容、选择模式、制定混合计划和编写目标 Skill；Python 只负责确定性的提取、章节构建、目录脚手架和结构验证。

## 核心规则

- 把用户提供的内容作为知识边界，不凭记忆补写来源没有的结论。
- 单模式能够满足目标时，只生成一种产物。
- 只有内容或用户目标确实跨越多个模式时才使用 hybrid。
- Hybrid 先规划组件、章节范围和用途，不默认生成三种全书产物。
- 严格隔离来源内容、知识压缩和方法推导；衍生内容永远不进入 faithful references。
- 先验证提取和结构，再编写目标 `SKILL.md`。
- 目标 Skill 的 frontmatter 只包含 `name` 和 `description`。

## 1. 确认输入和目标

检查输入路径、内容元信息、输出位置、目标用户和实际任务。只有缺失信息会改变模式或产物时才提问；否则采用合理默认值并说明。

至少确定：

- 输入能否提取为有效文本。
- 用户需要精确依据、快速理解、可执行方法，还是其中的组合。
- 是否允许引入来源之外的知识；默认不允许。
- 输出语言、术语保留方式和处理范围。
- 内容是整本书还是选定章节；视频、播客和课程使用时间戳、分 P、集数或讲次作为来源位置。

没有可访问文本时停止，不凭记忆蒸馏。扫描 PDF、无字幕视频或无法提取的音频先交给宿主 OCR、字幕或转写能力。

## 2. 提取并检查语料

优先使用宿主已有且质量可靠的文档能力；需要可重复处理、批量章节构建或宿主能力不足时使用内置工具。

检查本地能力：

```bash
python scripts/extract.py --check
```

单独提取：

```bash
python scripts/extract.py <input> --output-dir <work-dir>
```

支持：

- TXT、Markdown：编码检测。
- HTML、EPUB、DOCX、RTF：可选库与标准库回退。
- PDF：Docling、pdftotext、pypdf、pdfminer 可用能力回退。
- MOBI、AZW、AZW3：需要 Calibre `ebook-convert`。

脚本不自动安装依赖。缺少能力时报告缺失项和回退方案，只有用户授权后才安装。

抽查开头、中部、结尾和复杂章节。空白、乱码、明显错序或 OCR 质量不足时不要继续生成。

## 3. 选择模式

读取 [references/mode-selection.md](references/mode-selection.md)，对用户目标和主要章节评估：

- `F`：原文依赖度。
- `K`：知识压缩价值。
- `M`：方法迁移价值。

模式固定为：

- `faithful`：原文保真，一个 Skill 加完整或选定章节 references。
- `knowledge`：知识压缩，一个高密度知识型 Skill。
- `methods`：方法蒸馏，多个原子、可执行、可测试 Skills。
- `hybrid`：只组合有明确用途的组件和章节范围。

用户明确指定时优先服从，但如果该选择会丢失权威规则、产生明显误导或无法形成有效 Skill，要说明风险并提出替代方案。

高置信度单模式可以直接执行并汇报判断。Hybrid 必须基于 `assets/build-plan.template.json` 生成计划，展示组件、范围、用途、排除项和预计 Skills，取得用户确认后再生成。

## 4. 执行对应模式

只读取被选模式的详细规范：

- Faithful：读取 [references/faithful-mode.md](references/faithful-mode.md)。
- Knowledge：读取 [references/knowledge-mode.md](references/knowledge-mode.md)。
- Methods：读取 [references/method-mode.md](references/method-mode.md)。
- Hybrid：读取 [references/hybrid-mode.md](references/hybrid-mode.md)，以及计划中实际组件的规范。

### Faithful 快速路径

对具有“第 N 章”“Chapter N”“N. Title”和 `N.N` 子章节的内容运行：

```bash
python scripts/pipeline.py <input> --skill-dir <target> [--pdf-mode auto|technical|text] [--force]
```

该命令只生成 `references/`；随后由 Agent 依据真实目录编写目标 `SKILL.md`。`--force` 只能替换带 `.book2skill-generated.json` 的目录。

没有稳定编号时由 Agent 按自然语义边界切分，不强行套用脚本。

### Knowledge

先提取规范化文本，再依据 `references/knowledge-mode.md` 和 `assets/knowledge-skill.template.md` 生成知识型 Skill。把衍生内容明确标为结构化解释，并让每个非显然结论能够回到来源章节。

### Methods

依据 `references/method-mode.md` 先理解全局、提取候选、验证方法价值，再按 `assets/method-skill.template.md` 生成独立叶子 Skills。未通过证据、迁移、执行、区分或压力测试的候选不交付。

### Hybrid

先创建目录骨架：

```bash
python scripts/scaffold_output.py <output> --mode hybrid --book-slug <slug> --components faithful methods
```

把确认后的计划写入 `build-plan.json`，按顺序生成选中组件。不要创建计划外目录。Pack 根目录不作为单个 Skill 安装；只安装 `skills/` 下的叶子 Skill。

## 5. 编写目标 Skill

所有可安装叶子目录必须包含 `SKILL.md`，且目录名与 `name` 一致。`description` 同时说明能力和具体触发条件。

正文只写 Agent 执行任务所需的非显然知识：

1. 内容边界。
2. 输入检查。
3. 按需读取资源的顺序。
4. 条件、例外、冲突或方法边界。
5. 输出和停止条件。
6. 交付前验证。

不要创建 README、安装指南或变更日志。详细知识放 references，输出模板放 assets。

## 6. 验证

读取 [references/validation-rules.md](references/validation-rules.md)，先运行结构验证，再执行该模式的语义抽查和真实任务测试。

```bash
python scripts/validate_output.py <output> --mode faithful|knowledge|methods|hybrid
```

Faithful 还应运行：

```bash
python scripts/validate_references.py <target>/references
```

结构脚本通过不代表语义质量通过。交付说明必须列出无法执行的抽查、盲测或来源核验。

## 7. 维护和再生成

- 把生成内容和人工内容分开。
- Faithful 只替换带生成标记的 references。
- Knowledge 更新时重查来源映射、术语和相互引用。
- Methods 更新时重新运行触发、诱饵、边界和兄弟 Skill 混淆测试。
- Hybrid 更新时先修改并重新确认计划，清理计划外产物前必须确认它们确为生成内容。

## 完成标准

只有以下条件全部满足才宣告完成：

- 模式选择与用户目标一致。
- Hybrid 的实际组件和确认计划一致。
- 所有可安装叶子 Skill 能正确触发并独立使用。
- 各模式目录契约和结构验证通过。
- 代表性检索或方法压力测试通过。
- 来源、衍生解释和方法推导身份清晰。
- 所有未解决的提取、覆盖、证据或测试风险已报告。
