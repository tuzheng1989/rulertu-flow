---
name: html-to-pdf
description: 将HTML文件（单个或多个、含幻灯片演示文稿）转换为PDF。自动从HTML的设计尺寸推断纸张比例，保持原始布局与背景色，多文件自动按序合并。每当用户需要将HTML导出为PDF、把幻灯片/HTML演示文稿转成PDF、合并多个PDF，或提到"HTML转PDF""生成PDF""打印PDF""slides转PDF"时，使用此技能。
compatibility: 需要 Chrome 浏览器、Python 3.x；合并需 PyPDF2（pip install PyPDF2）
---

# HTML to PDF 技能

把 HTML 转成 PDF。核心是**在渲染时就使用正确纸张尺寸**，而非事后缩放。

## 依赖

- **Chrome / Chromium**（headless 打印引擎）—— 可设环境变量 `CHROME_PATH`
- **Python 3.x**
- **PyPDF2** —— 仅批量合并时需要：`pip install PyPDF2`
- **PyMuPDF**（可选）—— 仅用于转换后打印页面尺寸验证：`pip install pymupdf`

## 快速使用

唯一主脚本 `scripts/convert.py`，三种输入皆可：

```bash
# 单文件
python scripts/convert.py page.html out.pdf

# 目录（自动识别 slides/ 子目录并按序合并）
python scripts/convert.py slides/ presentation.pdf

# 通配符
python scripts/convert.py "drafts/ch*.html" out.pdf
```

**默认即可正确工作**：脚本会自动从 HTML 的 `body{width;height}` 读出像素尺寸，
换算为英寸（÷96 DPI）注入 `@page`，从而保持原始比例与布局。

## 关键参数

| 参数 | 作用 |
|------|------|
| `--page-size SIZE` | 强制纸张（`A4` / `Letter` / `8.5in 11in`），**同时关闭自动推断** |
| `--no-auto-size` | 关闭尺寸自动推断，用 Chrome 默认纸张 |
| `--margin M` | 页边距，默认 `0`（演示文稿无边距）；文档可设 `15mm` |
| `--keep-temp` | 保留中间单页 PDF，便于排查 |

## 场景对照

| 场景 | 命令 |
|------|------|
| 幻灯片演示文稿（16:9 设计） | `python scripts/convert.py slides/ out.pdf`（自动推断，无需指定比例）|
| 普通文档转 A4 | `python scripts/convert.py report.html out.pdf --page-size A4` |
| 仅合并已有 PDF（不经 Chrome） | `python scripts/merge.py out.pdf a.pdf b.pdf c.pdf` |

## 工作原理

对每个 HTML：

1. **检测设计尺寸** —— 正则提取 `body` 的 `width`/`height`（像素）。
2. **注入打印 CSS** —— `@media print { @page { size: <W>in <H>in; margin:0 } … }`，
   并锁定 `html,body` 像素尺寸 + `print-color-adjust:exact`（保背景色/渐变）。
   写入临时 HTML 文件。
3. **Chrome headless 渲染** —— `--print-to-pdf`（输出用**绝对路径**），
   配合 `--virtual-time-budget=10000`（避免外部字体/资源加载超时）与
   `--window-size`（匹配设计尺寸）。
4. 多文件则用 PyPDF2 合并，清理临时文件。

## 踩坑记录（务必遵守）

这些是实战中踩过的坑，已内置修复，**改脚本时不要破坏**：

1. **输出路径必须绝对** —— Chrome headless 无法解析相对输出路径，
   报错 `0x3 系统找不到指定的路径`。脚本内部已用 `os.path.abspath()`。
2. **@page size 单位必须用 in/cm/mm，不能用 px** —— `@page { size: 1920px 1080px }`
   在 Chrome headless 下**无效**；必须 `@page { size: 20in 11.25in }`。
3. **必须 `print-color-adjust: exact`** —— 否则背景色、渐变在打印时被丢弃，
   导致 PDF 与 HTML 内容明显不同（深色背景变白等）。
4. **必须 `--virtual-time-budget`** —— HTML 若引用 Google Fonts 等外部资源，
   headless 会阻塞等待，导致转换超时。
5. **禁止"先转再缩放"** —— 不要先用 Chrome 默认纸张渲染再用 PyMuPDF 缩放页面。
   那会让内容先被压进 Letter、再被拉伸，布局必然错乱。**正确做法是渲染前注入正确 @page。**
6. **控制台编码** —— 脚本已 `sys.stdout.reconfigure(encoding='utf-8')` 且日志用
   纯 ASCII 标记（`[OK]`/`[FAIL]`），避免 Windows GBK 控制台对 `✓`/`✗` 崩溃。
7. **排除临时文件** —— 自动忽略 `slides/` 下 `temp_` 开头的 HTML。

## 验证

转换后脚本会读取首页尺寸并打印（需 PyMuPDF），形如：
```
首页尺寸: 1440.0 x 810.0 pt (20.00 x 11.25 in), 比例 1.7778
```
若比例与原 HTML 不符，检查：HTML 的 `body` 是否有固定像素 `width`/`height`
（文档流型 HTML 无固定尺寸，需用 `--page-size` 显式指定纸张）。

## 故障排除

| 现象 | 原因 / 解决 |
|------|------------|
| `未找到 Chrome` | 安装 Chrome，或设 `CHROME_PATH` 指向其可执行文件 |
| `Chrome 退出码 N: ... write file` | 输出路径不可写或目录不存在（脚本已自动建目录，仍失败请检查权限）|
| `超时` | 外部资源加载超时；`--virtual-time-budget` 已默认 10s，仍慢可检查网络 |
| `PyPDF2 未安装` | `pip install PyPDF2` |
| PDF 背景变白 | 缺 `print-color-adjust:exact`（脚本已注入，除非 HTML 自身用更高优先级覆盖）|
| 比例不对 | HTML 无固定 body 尺寸 → 加 `--page-size`；或检查是否被 `--no-auto-size` 关闭 |

## 输出位置

遵循所在项目约定。本仓库默认输出到 `output/exports/`（见项目 CLAUDE.md）。
