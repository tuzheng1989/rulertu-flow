# 被测 A 原始输出：data-analysis 路由推演（DA-E01~E08）

说明：被测 subagent（general-purpose，冷启动模拟）原始回报，主控落盘供评估 subagent 评分。

---

依据文档：入口 SKILL.md、modes/excel.md、modes/document.md、modes/image.md、references/large-file-engine.md（均已完整阅读）。

### [DA-E01] 分析销售数据 Excel，看各区域表现
**路由决策**：excel mode（modes/excel.md），不预触发大文件引擎档（行数未知，待探查后由大文件门决定）。
**依据**：SKILL.md「输入类型路由表」第 1 行：.xlsx → modes/excel.md；触发词①命中；路由规则 1：按扩展名查表路由。
**下一步动作序列**（按 excel.md Workflow 六步）：
1. Step 1 行数探查——openpyxl read_only 逐 Sheet 计数，禁止 pd.read_excel() 计数（Step 1 警告：全量加载致 OOM）；
2. Step 2 大文件门——<10k 直接读；10k–100k 转 Parquet；≥100k 停下读 references/large-file-engine.md；
3. Step 3 schema 检查——nrows=20 采样（Key rules：列名可能含空格，精确字符串索引）；
4. Step 4 清洗（挂 excel-data-cleaning 子技能）；
5. Step 5 按「区域」分组统计（挂 group-by-analysis 或 grouped-statistics）；图表挂 bar-chart-visualization，绘图前原样复制 CJK Font Setup 字体块；
6. Step 6 导出 result.xlsx（excel-result-export/single-sheet-export）。
加载纪律：只加载当前步骤所需子技能。

### [DA-E02] 扫描版 PDF 发票批量提取金额与发票号
**路由决策**：document mode → 加载 doc-capability/pdf-analysis/SKILL.md；扫描件走会话视觉直读（提取指引见 image.md）。
**依据**：路由表第 2 行 .pdf → modes/document.md；触发词②含「发票提取」；document.md Workflow Step 1 格式表：.pdf → doc-capability/pdf-analysis（只加载这一个）；document.md「Universal Rules — MUST DO」：「For scanned PDFs: detect empty text → render pages to PNG → visual reading」；「NEVER DO」禁止 pytesseract/easyocr 主 OCR、禁止 PIL 像素分析推图表值；「Image Content via Visual Reading」节：渲染 PNG 后 Read 直读，无外部 API。
**下一步动作序列**：
1. Step 0 识别输入范围；「这批」多文件命中 Critical rule：逐个文件处理并聚合，不停在第一个；
2. 加载 pdf-analysis 做文字型/扫描型判别；
3. 扫描页判定空文本 → 渲染 PNG → Read 视觉直读，逐张提取发票号与金额（金额带单位）；
4. Step 3 回答前校验——抽查 3-5 张核对，打印总张数；
5. 输出结构化清单，可按需落 Excel。

### [DA-E03] 软件界面截图表格提取转 Excel
**路由决策**：image mode，会话视觉直读，无外部 API、无外部 OCR。
**依据**：路由表第 3 行 .png/.jpg + 数据提取 → modes/image.md；触发词③「表格识别 / 图片转表格 / 截图分析」命中；属数据提取非图片编辑；image.md「视觉提取指引」表格截图行：保持原行列结构逐格提取，数值不四舍五入；合并单元格如实注明。
**下一步动作序列**：
1. Read 直读（>5MB 先压缩）；
2. 按表格截图要点提取为 Markdown 表格；过大分两次提取再合并；
3. parse_markdown_table() 解析为 DataFrame；
4. 解析后校验（求和/百分比/行数）；
5. Export to Excel 节导出带表头样式 result.xlsx。

### [DA-E04] 200 万行 Excel 分组统计，8G 内存
**路由决策**：excel mode → Step 2 大文件门 → large-file-engine 引擎档。
**依据**：触发词④「大文件 / 百万行 / 内存不足 / OOM」命中；excel.md Step 2：≥100k STOP 读 references/large-file-engine.md，禁止 pd.read_excel()；large-file-engine「Mandatory Rules」：>1M 行 streaming + multi-sheet split（单 Sheet 上限 1,048,576）；「Memory Estimation」：200 万行 20 列含文本约 1.9GB，必须防 OOM。
**下一步动作序列**：
1. Core Method 1 inspect_excel() 流式探查；
2. Core Method 2 stream_excel_to_parquet() 50k 块流式写 Parquet（全列转字符串防 schema 不一致）；单 Sheet 超 104.8 万行拆分；
3. pd.read_parquet(columns=[...]) 只读所需列 + Core Method 4 optimize_dtypes()（省 50-80% 内存）；
4. 向量化分组 df.groupby().agg()（禁 apply/iterrows）；
5. Core Method 5 write_large_excel()（>1M 行改 CSV，>50k 单元格 write_only）；
6. del + gc.collect()。
补充：聚合结果行数小可直接出 Excel；导出明细才走大文件写出规则。

### [DA-E05] 销售 Excel 统计 + 架构截图提取（混合输入）
**路由决策**：双路并行——Excel 走 excel mode，截图走 image mode，各自完成后汇总交付。
**依据**：路由规则 1：「多种文件混合 → 各自路由后汇总」；截图内容是架构图，命中 image.md「视觉提取指引」流程图/架构图行（节点与连接关系 A→B，分支条件标注）。
**下一步动作序列**：Excel 路同 E01（分组维度换产品线）；截图路 Read 直读 → 架构图要点提取 → 整理选型清单；两路结果独立呈现。

### [DA-E06] 照片裁剪加滤镜
**路由决策**：拒绝进入本技能，转指外部技能 agnes-image。
**依据**：description 排除项「图片编辑（裁剪、滤镜、缩放）与图片生成」；路由规则 3 互斥边界明文。
**下一步动作**：说明 data-analysis 只管图片理解与数据提取；裁剪滤镜由 agnes-image 处理（其描述覆盖修改现有图片、风格转换）。

### [DA-E07] PDF 报告转 Markdown
**路由决策**：不进本技能任何 mode，指给 anydoc-to-md。
**依据**：description 排除项「文档格式转换（那归 anydoc-to-md）」；路由规则 3 原话；document mode 职责是解析提取回答问题，不是产出 Markdown 文件。
**下一步动作**：调用 anydoc-to-md（文本型直转，扫描版该技能内部路由 OCR）。

### [DA-E08] 分析报告结论润色
**路由决策**：不进本技能任何 mode，指给 write-report。
**依据**：description 排除项「报告成稿与改写（那归 write-report）」；路由规则 3。
**下一步动作**：路由给 write-report。备注（会话观察）：当前会话技能清单未见 write-report 挂载，实际可用近似技能为 work-skills:writing-for-human；若 write-report 不可用应以 writing-for-human 兜底并说明。

**评测小结**：8 条中 5 条进入本技能——E01/E04→excel mode（E04 经大文件门入引擎档），E02→document mode，E03/E05→image mode（E05 混合双路）；3 条命中互斥边界拒入转出——E06→agnes-image，E07→anydoc-to-md，E08→write-report。路由依据全部可溯源。
