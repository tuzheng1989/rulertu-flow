# data-analysis excel mode 冒烟测试结果（B1 / smoke-sales.xlsx）

- 测试日期：2026-11-13
- 被测文档：`plugins/work-skills/skills/data-analysis/SKILL.md`（路由入口）+ `modes/excel.md`（Workflow）
- 待分析文件：`plans/work-skills/.flow-evidence/2026-11-13-data-analysis-consolidation/B1/smoke-sales.xlsx`
- 用户请求（模拟）："分析这份销售数据：各区域的订单数与总金额，以及哪个产品销售额最高。"
- Python：`C:\Users\tuzhe\AppData\Local\Temp\B1-smoke\.venv\Scripts\python.exe`（pandas 3.1.1，一律 `-I` 隔离模式）
- 脚本目录：`C:\Users\tuzhe\AppData\Local\Temp\B1-smoke\scripts\`（smoke_excel_step1~6）

## 路由（SKILL.md）

输入为 `.xlsx` → 查路由表 → 进入 `modes/excel.md` 常规六步编排。命中。

## 执行步骤记录（对照 excel.md Step 1-6）

### Step 1 — 行数统计（lightweight, no full load）
- 按文档代码用 openpyxl `read_only=True, data_only=True` 逐 Sheet 以 `iter_rows(min_row=2, values_only=True)` 计数，未用 `pd.read_excel()` 数行数（文档明令禁止）。
- 实际输出：
  ```
  Sheet '销售数据': 20 rows
  Sheet '汇总表': 4 rows
  总行数=24
  ```

### Step 2 — 大文件门判定
- total_rows=24 < 10k → 走 **Direct read** 分支：`df = pd.read_excel(file_path, sheet_name=target_sheet)`，target_sheet 取明细表"销售数据"。
- 未触发 Parquet 缓存（10k–100k）与 large-file-engine 档（≥100k）。
- 实际输出：`direct read OK, df shape = (20, 5)`

### Step 3 — schema 检查
- 按文档 `nrows=20` 预览，打印 Columns / Dtypes / head(10)。
- 实际输出：
  ```
  Columns: ['订单ID', '区域', '产品', '数量', '金额']
  Dtypes: 订单ID int64 / 区域 str / 产品 str / 数量 int64 / 金额 int64
  ```

### Step 4 — 数据清洗
- 缺失值：按文档 `df[col].isna().sum()` 逐列检查 → 全列 0。
- 文本清洗：按文档 `clean_text`（`re.findall(r"[\u4e00-\u9fff]", ...)` 只保留中文）应用于"区域""产品"两列 → 0 处变化（原数据干净，清洗为幂等空操作）。
- 附加确认：订单ID 无重复；清洗后 shape 仍为 (20, 5)。
- 大文件 apply 禁令不触发（24 行 < 100k）。

### Step 5 — 筛选/统计
- 按区域分组聚合订单数与总金额；按产品聚合销售额并降序。
- 说明：excel.md Step 5 代码块只给了条件筛选与 headerless 布局示例，分组聚合需按其"按需加载 capability 子技能"机制取 group-by-analysis 模式；本次受测试约束（只读两个文档）以 pandas 常规 groupby 完成，见"文档问题"第 3 条。
- 真实运行输出：
  ```
  === 各区域订单数与总金额 ===
      订单数    总金额
  区域            
  华东    6  23670
  华北    5  15080
  西南    4  14260
  华南    5  14220
  合计: 订单数=20, 总金额=67230

  === 各产品销售额（降序） ===
  产品
  显示器    42000
  打印机    15300
  鼠标      5130
  键盘      4800
  销售额最高产品: 显示器（42000 元）
  ```

### Step 6 — 导出
- 按文档 `to_excel(output_path, index=False)` 模式导出统计结果；文档的 `/mnt/data/result.xlsx` 与 `[Download](sandbox:...)` 为沙箱写法，按语境等效调整为本机 Temp 路径。
- 导出路径：**`C:\Users\tuzhe\AppData\Local\Temp\B1-smoke\data\result.xlsx`**（两个 Sheet：区域统计、产品销售额；已确认落盘 5658 字节）

## 大文件门判定结果

- 总行数 24（销售数据 20 + 汇总表 4），门限分支：< 10k → Direct read（`pd.read_excel` 直读明细表）。

## 分析数值结论

- 各区域：华东 6 单 / 23,670 元（第一）；华北 5 单 / 15,080 元；西南 4 单 / 14,260 元；华南 5 单 / 14,220 元；合计 20 单 / 67,230 元。
- 产品销售额：显示器 42,000 元最高（占总销售额 62.5%），其后为打印机 15,300、鼠标 5,130、键盘 4,800。

## 执行中发现的文档问题

1. **Step 6 沙箱路径本机不可用**：`/mnt/data/result.xlsx` 与 `[Download](sandbox:...)` 是 Claude 沙箱约定，Windows 本机路径不存在；本次按任务约束等效调整为 Temp 目录。建议文档加一句"非沙箱环境改为本机可写目录"的提示。
2. **CJK Font Setup 全部 Linux 路径**：`_FONT_PATHS` 五个候选均为 `/mnt/...`、`~/.fonts`、`/usr/share/fonts`，Windows 上全部 miss，静默回退后中文图表会出方块。本次未画图未触发，但对 Windows 用户是隐患（无报错、只有乱码症状）。
3. **Step 5 代码块覆盖不了分组统计**：主文档 Step 5 只给条件筛选与 headerless 示例，"各区域订单数与总金额"这类 groupby 聚合在主文档无代码模板，须依赖其"按需加载子技能"机制跳到 capability；仅凭主文档自身无法完成本测试的分析请求（本次以 pandas 常规 groupby 补齐）。
4. 小瑕疵：Step 1 代码 `import openpyxl, gc` 中 `gc` 未使用，无害。

整体：六步可照做，无报错，顺序与分支判定清晰；问题集中在沙箱/环境假设（1、2）与 Step 5 模板缺口（3）。
