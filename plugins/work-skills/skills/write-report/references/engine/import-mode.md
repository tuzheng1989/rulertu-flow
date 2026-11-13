> 本文件为 write-report 引擎细节：导入模式（Import Mode）完整 7 Step 操作手册。入口与引擎概览见 SKILL.md。

## 导入模式 (Import Mode)

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

使用网页抓取能力获取（本仓环境优先用 url-to-md 技能或 MCP `web-reader`；源文档所称 meta-web 技能为旧环境依赖，不可用时以本仓能力替代）：

```yaml
抓取网页:
  url: {user_provided_url}
  保存到: {workspace}/raw-content.md
```

### Step 3: 分析文档结构

**调用 analyzer subagent**：

> 优先调用随技能分发的 `.claude/agents` 定义（插件 agent 形式）；宿主不支持时用 general-purpose + 本文提示词作替身。

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

> 优先调用随技能分发的 `.claude/agents` 定义（插件 agent 形式）；宿主不支持时用 general-purpose + 本文提示词作替身。

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

