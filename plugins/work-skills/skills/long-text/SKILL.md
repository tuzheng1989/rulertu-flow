---
name: long-text
description: |
  长文档智能撰写与编辑系统。支持三种工作模式：创建、导入、编辑。

  **核心特性**：
  - 创建模式：从零开始结构化撰写长文档
  - 导入模式：将现有文档/网页转换为 long-text 格式
  - 编辑模式：精准定位并修改已有章节
  - Subagent 协作架构 (Writer + Reviewer + Analyzer + Converter)
  - 统一风格指南确保一致性

  **使用场景**：
  - 创建技术报告、用户手册、研究论文
  - 将 PDF/DOCX/网页转换为可编辑的 long-text 格式
  - 二次编辑已有长文档的特定章节

  **触发方式**：
  - 创建模式：用户说"帮我写份长文档"、"写个报告"、"从零开始"
  - 导入模式：用户说"导入文档"、"转换为long-text"、"基于...改写"
  - 编辑模式：用户说"编辑文档"、"修改第X章"、"更新内容"

  **工作模式**：
  - 创建模式：从零开始创建
  - 导入模式：导入现有文档/网页
  - 编辑模式：修改已有文档

  **架构**：v2.0.0 新增导入模式，新增 Analyzer/Converter Subagent
version: 2.0.0
license: MIT
---

# Long-Text — 长文档智能撰写与编辑

## Overview

Long-text 是一个专门用于长文档创作和编辑的智能系统。它通过结构化的分章撰写机制和统一的风格指南，解决了大模型在处理长文档时的两大核心问题：

1. **Token 限制**：单次输出无法覆盖完整文档
2. **一致性难题**：多次输出导致结构和风格不一致

```
输入需求
    ↓
┌─────────────────────┐
│  创建稳定结构骨架    │ ← 章节大纲（固定）
├─────────────────────┤
│  定义统一风格标准    │ ← 风格指南（固定）
├─────────────────────┤
│  Writer 撰写章节    │ ← Subagent 逐章创作
├─────────────────────┤
│  Reviewer 审查质量  │ ← Subagent 检查合规
├─────────────────────┤
│  循环修改直到达标    │ ← Writer 执行修改
├─────────────────────┤
│  自动整合最终文档    │ ← 脚本合并
└─────────────────────┘
    ↓
输出完整长文档
```

---

## 模式选择

### 创建模式 vs 编辑模式

| 特征 | 创建模式 | 编辑模式 |
|-----|---------|---------|
| 触发条件 | 从零开始创建 | 已有文档需修改 |
| 首步操作 | 创建结构大纲 | 定位目标章节 |
| 核心输出 | 全套章节文件 | 修改后的章节 |
| 必要文件 | 00-structure.md<br>00-style-guide.md | 读取现有结构/风格文件 |

### 模式判断流程

```
用户请求
    │
    ├─> 包含"导入"、"转换"、"从...开始"、"基于..."？
    │   └─> YES → 导入模式 (Import Mode)
    │
    ├─> 包含"创建"、"写"、"生成"、"撰写"？且无"从"字
    │   └─> YES → 创建模式 (Create Mode)
    │
    ├─> 包含"编辑"、"修改"、"更新"、"优化"、"调整"等关键词？
    │   └─> YES → 检查是否有现有 long-text 工作区
    │       ├─> 有 → 编辑模式 (Edit Mode)
    │       └─> 无 → 提示先创建或导入
    │
    └─> 不明确 → 询问用户意图
```

### 三种模式对比

| 特征 | 创建模式 | 导入模式 | 编辑模式 |
|-----|---------|---------|---------|
| 触发条件 | 从零开始创建 | 导入现有文档 | 已有文档需修改 |
| 输入来源 | 用户需求描述 | 文档/网页/粘贴 | long-text 工作区 |
| 首步操作 | 创建结构大纲 | 获取并分析文档 | 定位目标章节 |
| 核心输出 | 全套章节文件 | 转换后的章节文件 | 修改后的章节 |
| 使用 Subagent | Writer, Reviewer | Analyzer, Converter, Writer, Reviewer | Writer, Reviewer |

---

## 导入模式 (Import Mode) 🆕

将现有文档或网页转换为 long-text 范式，使其可以被编辑模式修改。

### 导入流程

```
输入文档/网页
    ↓
┌─────────────────────────────────────┐
│  1. 确定输入类型                  │
│     ├─ 文件路径 (.pdf, .docx, .md) │
│     ├─ URL (http/https)           │
│     └─ 直接粘贴文本                 │
├─────────────────────────────────────┤
│  2. 获取文档内容                  │
│     ├─ 本地文档 → 解析脚本         │
│     ├─ 网页 → meta-web            │
│     └─ 粘贴 → 直接处理            │
├─────────────────────────────────────┤
│  3. 分析文档结构 (Analyzer)        │
│     ├─ 提取文档元信息             │
│     ├─ 识别章节层级               │
│     ├─ 生成结构分析 (JSON)        │
│     └─ 分析语言风格特征           │
├─────────────────────────────────────┤
│  4. 创建工作区                   │
│     mkdir -p .longText/{title}/   │
├─────────────────────────────────────┤
│  5. 生成 Long-Text 文件           │
│     ├─ 00-structure.md           │
│     ├─ 00-style-guide.md         │
│     ├─ 00-source-info.md         │
│     └─ chapter-*.md (Converter)  │
├─────────────────────────────────────┤
│  6. 处理参考资料                 │
│     ├─ 保存原始内容               │
│     └─ 创建参考资料索引           │
├─────────────────────────────────────┤
│  7. 整合最终文档 (可选)          │
│     python scripts/merge.py         │
└─────────────────────────────────────┘
    ↓
输出到 .longText/{title}/
    ↓
可继续进入编辑模式修改
```

### Step 1: 确定输入类型

询问用户或自动检测输入类型：

```yaml
输入类型检测:
  ├─ 文件路径: 检测文件扩展名 (.pdf, .docx, .md, .txt)
  ├─ URL: 检测 http/https 开头
  ├─ 直接粘贴: 用户直接提供文本内容
  └─ 未指定: 询问用户输入类型
```

### Step 2: 获取文档内容

#### 2.1 本地文档

使用对应的解析脚本：

```bash
# PDF 文档
python scripts/parse-pdf.py {input_path} --output {workspace}/raw-content.md

# DOCX 文档
python scripts/parse-docx.py {input_path} --output {workspace}/raw-content.md

# Markdown/TXT 文档
直接读取文件内容
```

#### 2.2 网页内容

使用 meta-web 技能获取：

```yaml
调用 meta-web:
  url: {user_provided_url}
  保存到: {workspace}/raw-content.md
```

### Step 3: 分析文档结构

**调用 analyzer subagent**：

```yaml
使用 Task 工具启动 analyzer:
  subagent_type: general-purpose
  prompt: |
    你是文档结构分析专家。请分析以下文档内容并提取结构信息。

    ## 输入文档
    {raw_content}

    ## 分析任务

    1. **文档元信息**
       - 提取标题（文档的第一个 H1 或第一行）
       - 识别作者、日期等元信息（如有）
       - 估计文档类型（技术报告、论文、教程等）

    2. **章节结构**
       - 识别所有标题层级 (H1-H6)
       - 确定章节划分
       - 为每个章节生成内容概述

    3. **内容特征**
       - 识别代码块、表格、图片
       - 检测引用链接
       - 分析语言风格特征

    ## 输出格式 (JSON)

    ```json
    {
      "meta": {
        "title": "文档标题",
        "author": "作者（如有）",
        "date": "日期（如有）",
        "type": "文档类型",
        "estimated_word_count": 字数估计
      },
      "structure": [
        {
          "level": 2,
          "title": "章节标题",
          "content_preview": "内容预览（50字）",
          "word_count": 字数估计
        }
      ],
      "features": {
        "has_code_blocks": true/false,
        "has_tables": true/false,
        "has_images": true/false,
        "has_references": true/false
      },
      "style_hints": {
        "tone": "正式/半正式/非正式",
        "person": "第一/第二/第三/无人称",
        "language": "中文/英文/混合"
      }
    }
    ```

  返回结果保存到: structure_analysis
```

### Step 4: 创建工作区

```bash
# 生成文档标题的 URL 安全版本
title_slug=$(echo "{meta.title}" | sed -e 's/[^a-zA-Z0-9]/-/g' -e 's/--*/-/g' -e 's/^-\|-$//g')

# 创建工作区
mkdir -p .longText/{title_slug}/references/{raw,indexed}
```

### Step 5: 生成 Long-Text 文件

#### 5.1 生成 00-structure.md

使用 `templates/structure-from-doc.md` 模板：

```markdown
# 文档结构大纲

## 文档元信息
- **文档标题**: {meta.title}
- **创建时间**: {current_date}
- **来源**: {source_type} - {source_path/URL}
- **文档类型**: {meta.type}

## 章节结构

| 序号 | 章节标题 | 内容概述 | 预估字数 | 状态 |
|-----|---------|---------|---------|------|
{for chapter in structure}
| {chapter.id} | {chapter.title} | {chapter.preview} | {chapter.word_count} | imported |
{endfor}
```

#### 5.2 生成 00-style-guide.md

根据分析结果生成风格指南：

```markdown
# 语言风格指南

## 语气与口吻
- **整体语气**: {style_hints.tone}
- **人称使用**: {style_hints.person}

## 用词规范
- **语言**: {style_hints.language}
- **专业术语**: 首次出现时需要解释

## 格式规范
- **标题层级**: H2 作为章节标题
- **代码块**: 指定语言标识
- **引用**: 保留原文链接

## 编辑建议
- 本文档为转换导入，编辑时请保持原有风格
- 如需调整风格，请修改本指南
```

#### 5.3 生成 00-source-info.md

使用 `templates/source-info-template.md` 模板。

#### 5.4 生成章节文件

**调用 converter subagent**：

```yaml
使用 Task 工具启动 converter:
  subagent_type: general-purpose
  prompt: |
    你是文档转换专家。请将原始文档内容转换为 Long-Text 范式的章节文件。

    ## 输入信息
    - 原始内容: {raw_content}
    - 结构分析: {structure_analysis}
    - 工作区: {workspace_dir}

    ## 转换规则

    1. **章节划分**
       - 按照 structure.structure 中的章节划分
       - 每个章节保存为 chapter-{N}.md
       - 章节标题使用 H2

    2. **内容处理**
       - 保留所有代码块（保持原语言标识）
       - 保留表格（Markdown 格式）
       - 图片引用转换为：`![图片描述](原始URL)`

    3. **引用处理**
       - 保留原文中的超链接
       - 添加引用注释格式：`[来源: 原URL]`

    4. **文件命名**
       - 使用两位数字序号：01, 02, 03...
       - 文件名格式：chapter-{N}.md

    ## 输出要求

    为每个章节生成独立文件，保存到 {workspace_dir}/

    返回生成的文件列表。

  返回结果保存到: chapter_list
```

### Step 6: 处理参考资料

```bash
# 保存原始内容
cp {workspace}/raw-content.md \
   {workspace}/references/raw/original-content.md

# 创建参考资料索引
cat > {workspace}/references/index.md << EOF
# 参考资料

## 原始文档
- **来源**: {source_type} - {source_path/URL}
- **文件**: references/raw/original-content.md

## 章节引用
各章节内容来自原始文档的对应部分。

## 外部链接
{提取并列表原文中的所有外部链接}
EOF
```

### Step 7: 整合最终文档（可选）

```bash
# 使用 merge 脚本
python scripts/merge.py \
  --workspace .longText/{title_slug}/ \
  --output final-output.md
```

### 导入完成后的选项

```markdown
✅ 导入完成！

**工作区位置**: .longText/{title}/

接下来您可以：
1. 编辑特定章节：进入编辑模式修改 chapter-*.md
2. 审查文档质量：调用 reviewer subagent 检查一致性
3. 继续撰写：使用 writer subagent 添加新章节
4. 重新整合：运行 merge.py 更新 final-output.md
```

---

## 创建模式 (Create Mode)

### Step 1: 需求收集

在开始创作前，收集以下关键信息：

```markdown
请提供以下信息以开始长文档创作：

1. **文档主题**：这份文档的核心主题是什么？
2. **目标读者**：谁会阅读这份文档？（技术背景、行业等）
3. **文档用途**：文档用于什么场景？（内部参考、对外发布、学术等）
4. **篇幅预估**：预期总字数或章节数量
5. **风格偏好**（可选）：有特定的写作风格要求吗？
   - 正式/非正式
   - 简洁/详尽
   - 技术深度（入门/中级/专家）
6. **特殊要求**（可选）：需要包含/避免的内容、格式要求等
```

### Step 2: 创建章节结构大纲

创建 `00-structure.md` 文件，使用 `templates/structure-template.md` 作为模板：

```markdown
# 文档结构大纲

## 文档元信息
- **文档标题**: [填写]
- **创建时间**: [YYYY-MM-DD]
- **目标读者**: [填写]
- **预期字数**: [填写]
- **文档类型**: [技术报告/用户手册/研究论文/白皮书]

## 章节结构

| 序号 | 章节标题 | 内容概述 | 预估字数 | 状态 |
|-----|---------|---------|---------|------|
| 01 | [章节标题] | [简要描述本章内容] | [字数] | pending |
| 02 | [章节标题] | [简要描述本章内容] | [字数] | pending |
| ... | ... | ... | ... | ... |

## 全局引用
- **参考资料**: [URL或文件路径]
- **图片资源**: [目录路径]
- **数据来源**: [说明]
```

**状态说明**：
- `pending` - 待创建
- `in_progress` - 创建中
- `completed` - 已完成
- `reviewed` - 已审阅

### Step 3: 创建语言风格指南

创建 `00-style-guide.md` 文件，使用 `templates/style-guide-template.md` 作为模板：

```markdown
# 语言风格指南

## 语气与口吻
- **整体语气**: [正式/半正式/非正式]
- **人称使用**: [第一人称/第二人称/第三人称/无人称]
- **情感倾向**: [客观中立/积极鼓励/谨慎保守]

## 用词规范
- **专业术语**:
  - 首次出现时需要解释: [是/否]
  - 中英文混排规则: [说明]
- **常用词汇偏好**:
  - 使用：[词汇列表]
  - 避免：[词汇列表]

## 句式结构
- **句式长度**: [简短/中等/较长]
- **段落长度**: 建议每段 X-Y 句话
- **过渡表达**: [常用过渡词]

## 格式规范
- **标题层级**: [说明各级标题使用场景]
- **列表使用**: [何时有序/无序]
- **代码块**: [格式要求]
- **引用标注**: [标注方式]
```

### Step 4: 逐章创建内容（调用 Writer Subagent）

**调用 writer subagent** 生成每个章节：

```markdown
主控指令：
"调用 writer subagent，根据 00-structure.md 和 00-style-guide.md 逐章撰写内容"
```

**执行流程**：
1. 读取 `00-structure.md` 获取当前待写章节
2. 调用 writer subagent 生成 `chapter-N.md`
3. 更新 `00-structure.md` 中的章节状态为 `completed`
4. 重复直到所有章节完成

**Writer Subagent 职责**：
- 读取章节结构和风格指南
- 撰写符合要求的章节内容
- 确保覆盖所有内容概述要点
- 遵循风格指南的所有规范

### Step 5: 内容审查（调用 Reviewer Subagent）

**调用 reviewer subagent** 审查所有章节：

```markdown
主控指令：
"调用 reviewer subagent，对照 00-structure.md 和 00-style-guide.md 审查所有章节"
```

**审查流程**：
1. Reviewer 读取所有章节文件
2. 对照 `00-structure.md` 检查结构合规性
3. 对照 `00-style-guide.md` 检查风格一致性
4. 检查段落质量、格式规范、术语使用、整体连贯性
5. 生成审查报告

**审查结果处理**：
- **全部通过** → 进入 Step 7 整合文档
- **发现问题** → 进入 Step 6 执行修改

**Reviewer Subagent 审查维度**：
| 维度 | 检查内容 |
|-----|---------|
| 结构合规 | 章节内容覆盖结构大纲要求 |
| 风格一致 | 语气、人称、用词符合风格指南 |
| 段落质量 | 段落长度、过渡自然度 |
| 格式规范 | 标题层级、代码块、列表格式 |
| 术语使用 | 专业术语首次解释 |
| 整体连贯 | 章节间逻辑连贯 |

### Step 6: 执行修改（调用 Writer Subagent）

根据 reviewer 建议，**调用 writer subagent** 执行修改：

```markdown
主控指令：
"调用 writer subagent（修改模式），根据 reviewer 的建议修改章节"
```

**修改流程**：
1. Writer 读取 reviewer 的修改建议
2. 定位目标段落/内容
3. 执行具体修改
4. 返回修改结果
5. **回到 Step 5 重新审查**

**循环机制**：
- 重复 Step 5-6 直到 reviewer 审查通过
- 最大循环次数：3 次
- 超过 3 次 → 报告用户，请求人工介入

### Step 7: 整合最终文档

使用 `scripts/merge.py` 脚本自动整合：

```bash
python scripts/merge.py --workspace workspace/{project-name}
```

整合完成后，手动审阅并调整：
- 检查章节间过渡是否自然
- 检查是否有重复或遗漏
- 检查格式是否统一

---

## 编辑模式 (Edit Mode)

### Step 1: 定位目标章节

```markdown
请指定需要编辑的章节：

**当前文档结构**：
1. [章节标题] - (已完成)
2. [章节标题] - (已完成) ← 当前目标
3. [章节标题] - (已完成)

您想编辑第几章？或者描述您想修改的内容位置。
```

**定位方式**：
1. 按章节序号定位（如"编辑第3章"）
2. 按关键词搜索定位（如"编辑提到'API设计'的章节"）
3. 按内容描述定位（如"编辑介绍架构的部分"）

### Step 2: 遵循风格指南修改

**调用 writer subagent（修改模式）** 进行修改：

```markdown
主控指令：
"调用 writer subagent，修改 chapter-N.md，严格遵循 00-style-guide.md"
```

或手动打开目标 `chapter-N.md` 文件，严格遵循 `00-style-guide.md` 进行修改。

### Step 3: 可选审查（建议）

修改完成后，**可调用 reviewer subagent** 检查修改内容：

```markdown
主控指令：
"调用 reviewer subagent，审查 chapter-N.md 的修改内容"
```

这可以确保修改后的内容仍然符合结构和风格要求。

### Step 4: 更新结构大纲（如需要）

如果编辑涉及结构调整，同步更新 `00-structure.md`。

### Step 5: 重新整合文档

```bash
python scripts/merge.py --workspace workspace/{project-name}
```

---

## 快速开始示例

### 示例 1：创建技术报告

```
用户: 我需要写一份关于微服务架构的技术报告，大概5000字，
      目标读者是技术团队的中级开发者。

系统: [进入创建模式]
      1. 收集需求信息
      2. 创建 00-structure.md
      3. 创建 00-style-guide.md
      4. 调用 writer subagent 生成 chapter-01.md, chapter-02.md, ...
      5. 调用 reviewer subagent 审查所有章节
      6. 如有问题，调用 writer subagent 执行修改（循环直到通过）
      7. 运行 merge.py 整合文档
```

### 示例 2：编辑现有文档

```
用户: 帮我修改这份文档的第三章，把API设计部分详细展开，
      并更新示例代码。

系统: [进入编辑模式]
      1. 读取 00-structure.md 定位第3章
      2. 调用 writer subagent（修改模式）修改 chapter-03.md
      3. （可选）调用 reviewer subagent 审查修改内容
      4. 运行 merge.py 重新整合
```

---

## 最佳实践

1. **结构先行**：始终先创建稳定的结构大纲，避免频繁调整
2. **风格固定**：风格指南一旦确定，尽量避免大幅修改
3. **独立章节**：每章保持内容独立性，降低耦合度
4. **信任 Subagent**：
   - Writer 专注于内容创作，无需人工干预
   - Reviewer 自动检查质量，减少人工审阅工作
   - 修改循环自动进行，直到达到质量标准
5. **定期整合**：每完成 2-3 章后可进行预整合，检查连贯性
6. **版本管理**：建议使用 Git 管理工作区，便于回溯
7. **循环控制**：如审查循环超过 3 次，建议检查风格指南是否过于严格

---

## 故障排除

| 问题 | 可能原因 | 解决方案 |
|-----|---------|---------|
| 章节间内容重复 | 结构大纲划分不清 | 重新审视章节边界 |
| 风格不一致 | 未严格遵循风格指南 | 重新阅读指南并修改 |
| 整合后格式错乱 | 章节内标题层级混乱 | 统一使用 H2 作为章节标题 |
| 找不到目标章节 | 章节序号不连续 | 检查 00-structure.md |

---

## 输出文件清单

### 创建模式输出

```
workspace/{project-name}/
├── 00-structure.md      # 章节结构大纲
├── 00-style-guide.md    # 语言风格指南
├── chapter-01.md        # 第1章
├── chapter-02.md        # 第2章
├── ...                  # 更多章节
└── final-output.md      # 最终整合文档
```

### 导入模式输出

```
.longText/{title}/
├── 00-structure.md      # 章节结构大纲（从文档导入）
├── 00-style-guide.md    # 语言风格指南（根据分析生成）
├── 00-source-info.md    # 原始文档信息
├── chapter-01.md        # 第1章（转换后）
├── chapter-02.md        # 第2章（转换后）
├── ...                  # 更多章节
├── references/          # 参考资料
│   ├── index.md         # 参考资料索引
│   └── raw/            # 原始内容
│       └── original-content.md
└── final-output.md      # 最终整合文档（可选）
```

### Subagent 配置文件

```
.claude/
├── agents/
│   ├── writer.md        # Writer Subagent 配置（创建/编辑模式）
│   ├── reviewer.md      # Reviewer Subagent 配置（质量审查）
│   ├── analyzer.md     # 🆕 Analyzer Subagent 配置（导入模式）
│   └── converter.md    # 🆕 Converter Subagent 配置（导入模式）
```

### 模板文件

```
templates/
├── structure-template.md       # 创建模式：章节结构大纲模板
├── structure-from-doc.md      # 🆕 导入模式：从文档生成结构模板
├── style-guide-template.md    # 创建模式：风格指南模板
├── source-info-template.md    # 🆕 导入模式：源信息模板
└── chapter-template.md         # 单章节内容模板
```

### 解析脚本

```
scripts/
├── merge.py              # 章节整合脚本（所有模式）
├── parse-pdf.py          # 🆕 PDF 文档解析脚本
└── parse-docx.py         # 🆕 DOCX 文档解析脚本
```

---

## 参考资源

**模板文件**：
- `templates/structure-template.md` - 创建模式：章节结构大纲模板
- `templates/structure-from-doc.md` - 导入模式：从文档生成结构模板
- `templates/style-guide-template.md` - 创建模式：语言风格指南模板
- `templates/source-info-template.md` - 导入模式：源信息模板
- `templates/chapter-template.md` - 单章节内容模板

**解析脚本**：
- `scripts/merge.py` - 章节整合脚本（所有模式）
- `scripts/parse-pdf.py` - PDF 文档解析（需要 `pip install PyMuPDF`）
- `scripts/parse-docx.py` - DOCX 文档解析（需要 `pip install python-docx`）

**参考资料**：
- `references/writing-styles.md` - 写作风格参考库
- `references/document-structures.md` - 文档结构参考库
- `templates/style-guide-template.md` - 语言风格指南模板
- `templates/chapter-template.md` - 单章节内容模板
- `scripts/merge.py` - 章节整合脚本
- `references/writing-styles.md` - 写作风格参考库
- `references/document-structures.md` - 文档结构参考库
