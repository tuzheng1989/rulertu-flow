> 本文件为 write-report 引擎细节：工作区文件体系与输出清单。入口与引擎概览见 SKILL.md。

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
│   ├── analyzer.md     # Analyzer Subagent 配置（导入模式）
│   └── converter.md    # Converter Subagent 配置（导入模式）
```

### 模板文件

```
templates/
├── structure-template.md       # 创建模式：章节结构大纲模板
├── structure-from-doc.md      # 导入模式：从文档生成结构模板
├── style-guide-template.md    # 创建模式：风格指南模板
├── source-info-template.md    # 导入模式：源信息模板
└── chapter-template.md         # 单章节内容模板
```

### 解析脚本

```
scripts/
├── merge.py              # 章节整合脚本（所有模式）
├── parse-pdf.py          # PDF 文档解析（需要 pip install PyMuPDF）
└── parse-docx.py         # DOCX 文档解析（需要 pip install python-docx）
```

## 参考资料

- `references/writing-styles.md` - 写作风格参考库
- `references/document-structures.md` - 文档结构参考库
- `references/import-guidelines.md` - 导入模式使用指南
- `templates/style-guide-template.md` - 语言风格指南模板
- `templates/chapter-template.md` - 单章节内容模板
- `scripts/merge.py` - 章节整合脚本
