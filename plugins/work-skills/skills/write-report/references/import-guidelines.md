# Long-Text Import 指南

## 概述

本文档提供 long-text 技能导入模式的使用指南，包括各种输入类型的处理方法和最佳实践。

---

## 支持的输入类型

### 1. PDF 文档

**特点**：
- 保持原有格式
- 保留字体和布局信息
- 支持中英文混合内容

**依赖安装**：
```bash
pip install PyMuPDF
```

**使用示例**：
```bash
python scripts/parse-pdf.py document.pdf --output .longText/document/raw-content.md
```

**注意事项**：
- 复杂布局可能需要人工调整
- 扫描版 PDF 识别准确度较低
- 表格转换可能不完美

### 2. DOCX 文档

**特点**：
- 精准提取段落和样式
- 保留标题层级
- 支持表格和图片

**依赖安装**：
```bash
pip install python-docx
```

**使用示例**：
```bash
python scripts/parse-docx.py document.docx --output .longText/document/raw-content.md
```

**注意事项**：
- 复杂的嵌套表格可能需要手动调整
- 图片链接会被转换为引用格式

### 3. Markdown 文档

**特点**：
- 直接读取，无需转换
- 完整保留格式
- 最佳兼容性

**使用方法**：
- 直接提供文件路径
- 系统自动读取并分析

### 4. TXT 文档

**特点**：
- 简单文本内容
- 无格式信息
- 结构由内容决定

**使用方法**：
- 直接提供文件路径
- 系统尝试识别章节结构

### 5. 网页 URL

**特点**：
- 使用 meta-web 技能获取
- 支持动态网页
- 自动过滤广告和导航

**使用方法**：
```
导入这个网页: https://example.com/article
```

**注意事项**：
- 需要 meta-web 技能可用
- 登录后内容无法获取
- JavaScript 渲染内容可能有延迟

---

## 导入流程详解

### 阶段 1: 内容获取

| 输入类型 | 获取方法 | 处理工具 |
|---------|---------|---------|
| PDF | 解析 PDF 文件 | parse-pdf.py |
| DOCX | 解析 Word 文档 | parse-docx.py |
| MD/TXT | 直接读取 | Read 工具 |
| 网页 | 获取网页内容 | meta-web 技能 |

### 阶段 2: 结构分析

**Analyzer Subagent** 执行以下分析：

1. **元信息提取**
   - 文档标题
   - 作者、日期（如有）
   - 文档类型

2. **章节结构识别**
   - 识别标题层级 (H1-H6)
   - 确定章节划分
   - 生成章节概述

3. **内容特征检测**
   - 代码块及其语言
   - 表格结构
   - 图片引用
   - 外部链接

4. **风格分析**
   - 语气（正式/半正式/非正式）
   - 人称使用
   - 主要语言

### 阶段 3: 内容转换

**Converter Subagent** 执行以下转换：

1. **章节划分**
   - 根据结构分析分割内容
   - 生成独立 chapter-*.md 文件
   - 使用两位数字序号命名

2. **格式规范化**
   - 标题层级调整
   - 代码块保留
   - 表格转换为 Markdown
   - 图片引用标准化

3. **引用处理**
   - 保留超链接
   - 添加来源注释
   - 创建参考资料索引

---

## 工作区结构

导入完成后，工作区目录结构：

```
.longText/{title_slug}/
├── 00-structure.md          # 章节结构大纲（从文档导入）
├── 00-style-guide.md        # 语言风格指南（根据分析生成）
├── 00-source-info.md        # 原始文档信息
├── chapter-01.md            # 第1章（转换后）
├── chapter-02.md            # 第2章（转换后）
├── ...                      # 更多章节
├── references/              # 参考资料
│   ├── index.md             # 参考资料索引
│   └── raw/                # 原始内容
│       └── original-content.md
└── final-output.md          # 最终整合文档（可选）
```

### 文件说明

#### 00-structure.md
- 章节结构大纲
- 从原始文档提取的章节信息
- 包含章节标题、概述、字数估计

#### 00-style-guide.md
- 语言风格指南
- 根据文档分析自动生成
- 包含语气、人称、语言等风格特征

#### 00-source-info.md
- 原始文档信息
- 记录来源路径、转换时间
- 包含文档元信息和转换说明

#### chapter-*.md
- 各章节的 Markdown 文件
- 格式规范化的内容
- 保留代码块、表格、引用

#### references/index.md
- 参考资料索引
- 列出所有外部链接
- 指向原始文档位置

#### references/raw/original-content.md
- 原始文档的完整内容
- 用于对比和参考

---

## 导入后的编辑

### 1. 编辑特定章节

进入编辑模式，修改指定章节：

```
编辑第3章，补充更多示例
```

### 2. 添加新章节

使用 writer subagent 添加新章节：

```
添加一个章节关于未来展望
```

### 3. 审查文档质量

使用 reviewer subagent 检查一致性：

```
审查所有章节
```

### 4. 更新风格指南

根据需要调整风格：

```
将语气改为更正式
```

修改 `00-style-guide.md`，然后重新审查章节。

### 5. 重新整合文档

完成编辑后重新生成最终文档：

```bash
python scripts/merge.py --workspace .longText/{title}/
```

---

## 最佳实践

### 1. 文档准备

**PDF 文档**：
- 选择可复制文本的 PDF（非扫描版）
- 确保文档结构清晰
- 避免过多复杂布局

**DOCX 文档**：
- 使用标准标题样式
- 保持层级一致
- 避免嵌套表格

**网页**：
- 选择文章页而非首页
- 避免登录后内容
- 选择结构完整的页面

### 2. 导入后验证

**检查清单**：
- [ ] 章节划分合理
- [ ] 内容完整无丢失
- [ ] 代码块格式正确
- [ ] 表格结构完整
- [ ] 外部链接可访问
- [ ] 风格指南准确反映原文风格

### 3. 编辑建议

**保持一致性**：
- 遵循 `00-style-guide.md` 的风格
- 新增内容与原文保持语气一致
- 使用相同的人称和语言风格

**逐步验证**：
- 每修改 2-3 章节后重新整合
- 检查章节间过渡是否自然
- 确保逻辑连贯

**版本管理**：
- 使用 Git 管理工作区
- 定期提交重要修改
- 保留原始导入版本

---

## 常见问题

### Q1: 导入后章节划分不正确怎么办？

**A**: 手动编辑 `00-structure.md`，调整章节划分。然后重新调用 converter subagent 重新生成章节文件。

### Q2: 代码块语言标识错误？

**A**: 直接编辑 `chapter-*.md` 中的代码块，修正语言标识：
```markdown
```python
# 替换为正确的语言
```

### Q3: 表格格式混乱？

**A**: 手动调整表格格式，确保使用正确的 Markdown 表格语法：
```markdown
| 列1 | 列2 |
|-----|-----|
| 值1 | 值2 |
```

### Q4: 想要更改文档风格？

**A**: 编辑 `00-style-guide.md`，调整语气、人称等参数。然后调用 reviewer subagent 根据新指南审查章节。

### Q5: 如何将多个文档合并？

**A**:
1. 分别导入每个文档到不同工作区
2. 手动合并 `00-structure.md`
3. 复制所有章节文件到同一目录
4. 重新编号章节文件
5. 运行 merge.py 整合

---

## 高级用法

### 自定义解析规则

修改 `scripts/parse-pdf.py` 或 `scripts/parse-docx.py`：

```python
# 自定义标题识别
def _is_heading(self, block):
    # 添加自定义规则
    if "Chapter" in block:
        return True
    return self._is_heading(block)

# 自定义代码语言检测
def _detect_code_language(self, text):
    # 添加自定义模式
    patterns['rust'] = [r'\bfn\b', r'\blet\b', r'\bimpl\b']
```

### 批量导入

创建批量导入脚本：

```bash
#!/bin/bash
for file in docs/*.pdf; do
    filename=$(basename "$file" .pdf)
    python scripts/parse-pdf.py "$file" \
        --output ".longText/$filename/raw-content.md"
done
```

---

## 版本历史

| 版本 | 日期 | 更新内容 |
|-----|------|---------|
| 1.0 | 2024-04-01 | 初始版本，支持导入模式 |
