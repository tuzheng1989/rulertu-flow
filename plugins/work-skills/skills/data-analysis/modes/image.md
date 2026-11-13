# Image Analysis — Visual Reading & Data Extraction

> 本文件为 data-analysis 的 image mode（原图片理解与数据提取 skill，2026-11-13 组建）。入口与路由见 SKILL.md。

## Overview

Analyze, extract data from, or understand image files (.png, .jpg, .jpeg, .gif, .webp, .bmp). The core workflow:

1. **Read the image directly with the Read tool** — 会话原生视觉直读，无外部 API、无需任何 API Key
2. Follow the 视觉提取指引 below to output structured content (Markdown 表格等)
3. Parse the structured text into a DataFrame
4. Analyze, visualize, or export

## 视觉提取指引（Visual Extraction Guide）

用 Read 工具直接读图片文件（会话原生视觉理解）。不同图片类型的提取要点：

| 图片类型 | 场景 | 提取要点 |
|---------|------|---------|
| 数据图表 | 柱状图/折线图/饼图 | 先读图表标题与坐标轴标签，再逐系列提取每个数据点的数值与图例，输出 Markdown 表格 |
| 表格截图 | 表格/报表截图 | 保持原行列结构逐格提取，数值不四舍五入；合并单元格如实注明原始结构 |
| UI 截图 | 界面截图 | 以前端开发者视角记录：整体布局、组件层级、文字内容、颜色 |
| 流程图/架构图 | 流程图/架构图 | 列出所有节点与连接关系（A→B），标注分支条件 |
| 一般图片 | 照片、其他图片 | 描述主体内容与可见文字；不含数据时如实说明，不编造数值 |

- **大图（>5MB）先压缩再读**，避免超出读取限制
- **超大表格分两次提取**：第一次提取前半部分，第二次提取后半部分，最后按行列合并

## Parsing Visual Reading Results

视觉直读通常输出 Markdown 表格，解析为 DataFrame：

```python
import pandas as pd

def parse_markdown_table(text):
    lines = text.strip().split('\n')
    table_lines = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        if '|' in stripped:
            in_table = True
            table_lines.append(stripped)
        elif in_table:
            break

    data_lines = []
    for l in table_lines:
        cells = [c.strip() for c in l.split('|') if c.strip()]
        if cells and not all(set(c) <= set('-: ') for c in cells):
            data_lines.append(cells)

    if len(data_lines) < 2:
        return None

    header = data_lines[0]
    rows = [r for r in data_lines[1:] if len(r) == len(header)]
    df = pd.DataFrame(rows, columns=header)

    # Auto numeric conversion
    for col in df.columns:
        try:
            cleaned = df[col].str.replace(',', '').str.strip()
            if cleaned.str.endswith('%').any():
                df[col] = pd.to_numeric(cleaned.str.rstrip('%'), errors='coerce')
            else:
                converted = pd.to_numeric(cleaned, errors='coerce')
                if converted.notna().sum() > len(df) * 0.5:
                    df[col] = converted
        except Exception:
            pass
    return df
```

## Visualization

### Chinese Font Setup (MANDATORY)

```python
import matplotlib.pyplot as plt
import matplotlib
import matplotlib.font_manager as fm
import os

for font_path in ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf', '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc']:
    if os.path.exists(font_path):
        matplotlib.rcParams['font.family'] = fm.FontProperties(fname=font_path).get_name()
        break
matplotlib.rcParams['axes.unicode_minus'] = False
```

### Color Palette

```python
COLORS = ['#4C72B0', '#55A868', '#C44E52', '#8172B2', '#CCB974', '#64B5CD']
```

### Save & Display

```python
plt.savefig('chart.png', dpi=150, bbox_inches='tight')  # 写到当前工作目录
plt.show()
print("图表已保存: chart.png")
```

## Export to Excel

```python
from openpyxl.styles import Font, PatternFill, Alignment

output_path = "result.xlsx"  # 写到当前工作目录（或用户指定路径）
with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    df.to_excel(writer, index=False, sheet_name='提取数据')
    ws = writer.sheets['提取数据']
    fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    for cell in ws[1]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = fill
        cell.alignment = Alignment(horizontal='center')
    for i, col in enumerate(df.columns, 1):
        w = max(df[col].astype(str).str.len().max(), len(str(col))) + 2
        ws.column_dimensions[chr(64 + i)].width = min(w * 1.2, 40)

print(f"[下载](sandbox:{output_path})")
```

## Multi-Image Processing

多张图片场景：逐张用 Read 工具视觉直读，按视觉提取指引输出 Markdown 表格，再逐一解析合并。

```python
import glob

image_files = sorted(glob.glob("*.png"))  # 或用户指定的图片目录
all_dfs = []

# 对每张图片：Read 直读 → 按提取指引得到 Markdown 表格文本 → 解析
for img in image_files:
    table_text = read_image_and_extract(img)  # 会话视觉直读该图，返回 Markdown 表格文本
    df = parse_markdown_table(table_text)
    if df is not None:
        all_dfs.append(df)

combined = pd.concat(all_dfs, ignore_index=True) if all_dfs else None
```

## Common Pitfalls

- **Always read the image first** — don't guess image content from filenames
- **Verify extracted data** — check sums, percentages, row counts after parsing
- **Chinese font** — must set before any matplotlib call, or output is garbled
- **Large tables truncate** — 分两次直读（先提取前半部分，再提取后半部分）后合并
- **大图（>5MB）先压缩再读**，避免读取失败或截断
