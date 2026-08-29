# 文档结构大纲

## 文档元信息
- **文档标题**: {{TITLE}}
- **创建时间**: {{DATE}}
- **来源**: {{SOURCE_TYPE}} - {{SOURCE_PATH}}
- **文档类型**: {{DOC_TYPE}}

## 章节结构

| 序号 | 章节标题 | 内容概述 | 预估字数 | 状态 |
|-----|---------|---------|---------|------|
{{CHAPTERS}}

**状态说明**：
- `imported` - 已从原始文档导入
- `pending` - 待创建
- `in_progress` - 创建中
- `completed` - 已完成
- `reviewed` - 已审阅

## 原始文档特征

根据文档分析，原始文档具有以下特征：

### 内容特征
- **代码块**: {{HAS_CODE_BLOCKS}}
- **表格**: {{HAS_TABLES}}
- **图片**: {{HAS_IMAGES}}
- **外部引用**: {{HAS_REFERENCES}}

### 语言风格
- **语气**: {{TONE}}
- **人称**: {{PERSON}}
- **主要语言**: {{LANGUAGE}}

## 编辑建议

本文档为从原始文档导入的 Long-Text 范式。编辑时请注意：

1. **保持一致性**
   - 新增章节请遵循现有的语言风格
   - 参考 `00-style-guide.md` 保持语气和人称统一

2. **结构扩展**
   - 新增章节请更新本大纲表格
   - 确保章节序号连续

3. **内容审查**
   - 建议导入后使用 reviewer subagent 检查一致性
   - 可根据需要调整 `00-style-guide.md`

4. **参考资料**
   - 原始文档保存在 `references/raw/original-content.md`
   - 外部链接索引见 `references/index.md`
