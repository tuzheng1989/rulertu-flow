# Long-Text 导入模式使用示例

## 示例 1: 导入 PDF 文档

### 用户输入

```
导入这个 PDF 文档: ~/Documents/technical-report.pdf
```

### 系统处理流程

**Step 1: 解析 PDF**
```bash
python scripts/parse-pdf.py \
    ~/Documents/technical-report.pdf \
    --output .longText/technical-report/raw-content.md
```

**Step 2: 分析文档结构**
```
调用 analyzer subagent
  输入: raw-content.md
  输出: structure_analysis.json

分析结果:
  - 文档标题: 微服务架构技术报告
  - 文档类型: 技术报告
  - 章节数: 6
  - 字数: 8,500
  - 语气: 正式
  - 人称: 第三人称
```

**Step 3: 创建工作区**
```bash
mkdir -p .longText/microservices-architecture/references/{raw,indexed}
```

**Step 4: 生成 Long-Text 文件**
```
00-structure.md
00-style-guide.md
00-source-info.md
```

**Step 5: 转换章节**
```
调用 converter subagent
  输入: raw-content.md + structure_analysis
  输出: chapter-01.md, chapter-02.md, ...
```

**Step 6: 处理参考资料**
```
保存原始内容到: references/raw/original-content.md
创建索引到: references/index.md
```

**Step 7: 整合文档**（可选）
```bash
python scripts/merge.py \
    --workspace .longText/microservices-architecture/
```

### 导入完成报告

```
✅ PDF 导入完成

**工作区**: .longText/microservices-architecture/

**生成文件**:
  ✓ 00-structure.md (章节大纲)
  ✓ 00-style-guide.md (风格指南)
  ✓ 00-source-info.md (源信息)
  ✓ chapter-01.md (引言, 1200字)
  ✓ chapter-02.md (架构设计, 1800字)
  ✓ chapter-03.md (服务通信, 1500字)
  ✓ chapter-04.md (数据一致性, 1400字)
  ✓ chapter-05.md (部署方案, 1600字)
  ✓ chapter-06.md (总结, 1000字)

**转换统计**:
  - 代码块: 8 个
  - 表格: 3 个
  - 外部链接: 12 个

**接下来可以**:
  1. 编辑特定章节
  2. 审查文档质量
  3. 添加新章节
  4. 重新整合文档
```

---

## 示例 2: 导入网页文章

### 用户输入

```
导入这篇网页文章: https://example.com/machine-learning-guide
```

### 系统处理流程

**Step 1: 获取网页内容**
```yaml
调用 meta-web:
  url: https://example.com/machine-learning-guide
  保存到: .longText/ml-guide/raw-content.md
```

**Step 2-7: 与 PDF 导入相同**

### 导入完成报告

```
✅ 网页导入完成

**源 URL**: https://example.com/machine-learning-guide
**工作区**: .longText/machine-learning-guide/

**生成文件**:
  (同上)

**特殊处理**:
  - 图片链接已保留
  - 外部链接已添加来源注释
  - 原始网页保存在 references/raw/
```

---

## 示例 3: 导入后编辑

### 场景

用户导入文档后，发现第3章内容不足，需要扩展。

### 用户输入

```
编辑第3章，添加更多关于服务通信的示例
```

### 系统处理（编辑模式）

**Step 1: 定位目标章节**
```
读取 00-structure.md
目标: chapter-03.md (服务通信)
```

**Step 2: 调用 writer subagent**
```
修改 chapter-03.md
要求: 添加更多服务通信示例
遵循: 00-style-guide.md
```

**Step 3: 可选审查**
```
调用 reviewer subagent
审查: chapter-03.md
检查: 风格一致性、格式规范
```

**Step 4: 更新结构大纲**
```markdown
00-structure.md 更新:
| 03 | 服务通信 | 添加更多示例 | 2100 | completed |
```

**Step 5: 重新整合**
```bash
python scripts/long-text/scripts/merge.py \
    --workspace .longText/microservices-architecture/
```

---

## 示例 4: 导入后添加新章节

### 场景

用户导入文档后，想添加"未来展望"章节。

### 用户输入

```
在文档末尾添加一个关于未来展望的章节
```

### 系统处理（编辑模式）

**Step 1: 确定章节序号**
```
当前最大序号: 06
新章节序号: 07
```

**Step 2: 调用 writer subagent**
```
创建 chapter-07.md
标题: 未来展望
要求: 遵循 00-style-guide.md
内容: 预测微服务架构的发展方向
```

**Step 3: 更新结构大纲**
```markdown
00-structure.md 添加:
| 07 | 未来展望 | 预测架构发展方向 | 800 | completed |
```

**Step 4: 审查新章节**
```
调用 reviewer subagent
审查: chapter-07.md
```

**Step 5: 重新整合文档**

---

## 示例 5: 导入后调整风格

### 场景

用户导入的技术文档语气过于正式，希望改为更易懂的风格。

### 用户输入

```
把文档风格调整得更通俗易懂一些，面向初学者
```

### 系统处理

**Step 1: 修改风格指南**
```markdown
00-style-guide.md 更新:

语气与口吻:
- 整体语气: 半正式 (从正式改为半正式)

用词规范:
- 专业术语: 首次出现时需要解释: 是

句式结构:
- 句式长度: 简短 (从较长改为简短)
- 段落长度: 建议每段 2-3 句话 (从 4-5 句话减少)
```

**Step 2: 批量审查章节**
```
调用 reviewer subagent
审查: 所有章节 (chapter-01 到 chapter-06)
检查: 符合新的风格指南
```

**Step 3: 执行修改**
```
调用 writer subagent (批量修改)
根据 reviewer 建议，修改所有不符合新风格的段落
```

**Step 4: 重新整合文档**

---

## 输出示例

### 导入前的原始文档 (PDF)

```
[PDF 文件内容 - 非结构化]
```

### 导入后的结构

```
.longText/microservices-architecture/
├── 00-structure.md
├── 00-style-guide.md
├── 00-source-info.md
├── chapter-01.md
├── chapter-02.md
├── chapter-03.md
├── chapter-04.md
├── chapter-05.md
├── chapter-06.md
├── references/
│   ├── index.md
│   └── raw/
│       └── original-content.md
└── final-output.md
```

### 00-structure.md 示例

```markdown
# 文档结构大纲

## 文档元信息
- **文档标题**: 微服务架构技术报告
- **创建时间**: 2024-04-01
- **来源**: local file - ~/Documents/technical-report.pdf
- **文档类型**: 技术报告

## 章节结构

| 序号 | 章节标题 | 内容概述 | 预估字数 | 状态 |
|-----|---------|---------|---------|------|
| 01 | 引言 | 介绍微服务架构的背景和优势 | 1200 | imported |
| 02 | 架构设计 | 详细描述服务拆分和设计原则 | 1800 | imported |
| 03 | 服务通信 | 说明服务间通信方式 | 1500 | imported |
| 04 | 数据一致性 | 探讨分布式数据一致性方案 | 1400 | imported |
| 05 | 部署方案 | 介绍容器化和编排部署 | 1600 | imported |
| 06 | 总结 | 总结全文内容 | 1000 | imported |
```

### chapter-02.md 示例

```markdown
## 架构设计

微服务架构的核心在于将单一应用拆分为多个小型服务。

### 服务拆分原则

**单一职责原则**
每个服务应专注于单一业务功能。

**自治性原则**
服务应独立部署和扩展。

### 设计模式

**API 网关模式**
提供统一的入口点...

**服务发现模式**
实现服务的动态注册和发现...

```python
# 服务注册示例
class ServiceRegistry:
    def register(self, service):
        pass
```
```

---

## 常见使用场景

### 场景 1: 将现有技术文档转换为可编辑格式

```
用户: 导入这份技术手册 ~/manual.pdf

系统: 导入 PDF，生成结构化章节
用户: 编辑第5章，更新 API 文档
系统: 修改 chapter-05.md
用户: 重新整合
系统: 生成 final-output.md
```

### 场景 2: 将网页文章保存为长文档

```
用户: 保存这篇博客文章为 long-text 格式
      https://blog.example.com/series-part1

系统: 导入网页，生成章节
用户: 添加第二部分 https://blog.example.com/series-part2
系统: 合并两个导入结果
用户: 添加总结章节
系统: 创建最终文档
```

### 场景 3: 将 Word 文档转换为 Markdown 并二次创作

```
用户: 将这份报告转换为 long-text
      ~/reports/Q1-report.docx

系统: 导入 DOCX
用户: 调整风格，改为更正式的语气
系统: 修改风格指南并重新审查
用户: 添加Q2展望章节
系统: 创建新章节
用户: 导出最终 Markdown
系统: 整合为 final-output.md
```
