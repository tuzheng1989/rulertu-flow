---
name: data-analysis
description: |
  数据分析统一入口：按输入类型路由到三个 mode 与一个大文件引擎档——
  excel（Excel/CSV 多步分析编排，含 44 个 capability 子技能）、document（Word/PDF/PPT
  解析与数据提取，含 3 个 doc-capability 子技能）、image（图片视觉直读与数据提取）、
  large-file-engine（≥10k 行大文件 Parquet/流式引擎档，由 excel mode 的行数门触发）。
  **遇到以下任一情况就主动使用本 skill**：
  ①Excel 触发词：Excel 分析 / 表格分析 / 数据分析 / 数据清洗 / 数据统计 / 数据筛选 /
  数据可视化 / 数据导出 / 汇总统计 / 透视表 / 分组统计 / 交叉分析 / 趋势分析 / 对比分析 /
  异常值检测 / 去重 / 缺失值处理 / Excel 报告 / 生成报表 / analyze Excel / data analysis /
  data cleaning / pivot table；
  ②文档触发词：Word分析 / PDF解析 / PPT提取 / 文档分析 / 报告解析 / 幻灯片分析 /
  发票提取 / 合同分析 / 文档统计 / 错别字 / 语病 / 字号检查 / 简历分析 / 多文档对比；
  ③图片触发词：图片分析 / 图表提取 / 表格识别 / OCR / 图片描述 / 截图分析 / 图表数据 /
  提取图片中的数据 / 图片转表格 / 识别图片 / extract data from image / chart analysis /
  table OCR；
  ④大文件触发词：大文件 / 大数据量 / 性能优化 / 内存不足 / OOM / 百万行 / 十万行 /
  流式读取 / Parquet / 分块处理 / large file / big data / streaming read / chunked processing；
  ⑤用户上传或指定了 .xlsx / .xls / .csv / .docx / .doc / .pdf / .pptx / .ppt /
  .png / .jpg / .jpeg / .gif / .webp / .bmp 文件并要求分析、提取、统计或可视化。
  仅不用于：图片编辑（裁剪、滤镜、缩放）与图片生成；文档格式转换（那归
  anydoc-to-md——本技能管分析不管转换）；报告成稿与改写（那归 write-report）；
  不涉及表格数据的纯文本处理；单个公式计算的简单问答。
---

# Data Analysis — 数据分析统一入口

按**输入类型**路由：拿到文件先看扩展名，进对应 mode；mode 内部再按需加载子技能。

## 输入类型路由表

| 输入 | 路由 | 说明 |
|------|------|------|
| `.xlsx` / `.xls` / `.csv` | `modes/excel.md` | 常规编排六步；总行数 ≥10k 时由 excel.md Step 2 大文件门转入引擎档 |
| `.docx` / `.doc` / `.pdf` / `.pptx` / `.ppt` | `modes/document.md` | 按格式加载 doc-capability 子技能解析 |
| `.png` / `.jpg` / `.jpeg` / `.gif` / `.webp` / `.bmp` + 数据提取 | `modes/image.md` | 会话视觉直读（Read 工具），无外部 API |
| 大文件 / Parquet / 流式读取 / ≥10k 行 | excel mode → `references/large-file-engine.md` | 由 excel.md 的行数门按量级指路 |

路由规则：
1. 用户给了文件 → 按扩展名查表路由；多种文件混合 → 各自路由后汇总。
2. 用户没给文件只有触发词 → 按触发词组匹配 mode（Excel 组→excel，文档组→document，图片组→image，大文件组→excel 的引擎档）。
3. 互斥边界：图片编辑/生成请求**拒绝**并说明不归本技能；"把这个 PDF 转成 Markdown"类格式转换请求指给 **anydoc-to-md**；"帮我改写/成稿这份报告"类请求指给 **write-report**。

## Modes

- **`modes/excel.md`** — Excel/CSV 数据分析多步编排器：行数探查 → 大文件门 → schema 检查 → 清洗 → 筛选 → 导出六步，按步骤挂载 capability 子技能。
- **`modes/document.md`** — Word/PDF/PPT 解析：按格式加载子技能，全量扫描提取文本/表格/图表，扫描件走视觉直读。
- **`modes/image.md`** — 图片理解与数据提取：Read 工具视觉直读 → 结构化解析 → 可视化/Excel 导出。
- **`references/large-file-engine.md`** — ≥10k 行引擎档：流式读取、Parquet 转换、内存优化、大文件写入。不是独立入口，由 excel.md 的大文件门进入。

## capability 子技能索引（excel mode，44 个）

完整索引表（类别 × 功能）见 `modes/excel.md` 的 "Available capability sub-skills" 节。
加载路径：`<skills_root>/data-analysis/capability/{category}/{sub-skill}/SKILL.md`。

| 类别 | 子技能数 | 覆盖 |
|------|---------|------|
| excel-reading | 7 | 单/多/指定 Sheet、区域、大文件、多文件、结构化表头读取 |
| excel-data-cleaning | 6 | 缺失值、去重、无效数据、文本/数值格式标准化、异常值检测 |
| excel-data-filtering | 4 | 条件、分类、区间、阈值筛选 |
| excel-data-analysis | 6 | 对比、分组、KPI、透视表、时间序列、趋势分析 |
| excel-data-statistics | 4 | 基础/分类/分组统计、占比计算 |
| excel-data-visualization | 6 | 柱/直方/折线/饼/散点/堆叠图 |
| excel-cell-coloring | 5 | 分类/重复值/异常值/阈值/Top 值着色 |
| excel-conditional-formatting | 1 | 数据条格式 |
| excel-result-export | 4 | 单 Sheet/格式化/图表嵌入/报告生成导出 |
| excel-table-styling | 1 | 表格主题样式（大文件 Parquet 加速） |

加载纪律（与 excel.md 一致）：只加载当前步骤需要的子技能，不要一次性全读。

## doc-capability 子技能索引（document mode，3 个）

加载路径：`<skills_root>/data-analysis/doc-capability/{format}-analysis/SKILL.md`。

| 子技能 | 格式 |
|--------|------|
| `doc-capability/word-analysis/SKILL.md` | .docx / .doc（正文、表格、高亮/颜色格式、嵌入图片） |
| `doc-capability/pdf-analysis/SKILL.md` | .pdf（文字型/扫描型判别、表格、嵌入图表） |
| `doc-capability/ppt-analysis/SKILL.md` | .pptx / .ppt（slide 全量、表格、图表、纯图片 slide） |

## 图片与扫描件说明

图片理解统一由**会话视觉直读**完成（Read 工具直接读图片），全程无外部 API、
无需 API Key。文档 mode 遇到扫描页/图片页时渲染为 PNG 后同样走视觉直读，
提取指引见 `modes/image.md` 的视觉提取指引节。
