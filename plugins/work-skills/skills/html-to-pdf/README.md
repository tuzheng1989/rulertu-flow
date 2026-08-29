# HTML to PDF 技能

将 HTML（单个 / 多个 / 幻灯片演示文稿）转换为 PDF，保持原始布局、比例与背景色。

## 功能特性

- 单个 HTML 直接转换
- 多个 HTML 批量转换并按序合并
- 智能识别 `slides/` 演示文稿结构
- **自动从 HTML 设计尺寸推断纸张比例**（16:9 等），无需手动指定
- 保留背景色 / 渐变（`print-color-adjust: exact`）
- 自动清理临时文件；转换后验证页面尺寸

## 依赖

| 依赖 | 用途 | 安装 |
|------|------|------|
| Chrome / Chromium | headless 打印引擎 | 可设 `CHROME_PATH` |
| Python 3.x | 运行脚本 | — |
| PyPDF2 | 批量合并 | `pip install PyPDF2` |
| PyMuPDF（可选）| 转换后尺寸验证 | `pip install pymupdf` |

## 脚本

### convert.py —— 主脚本（推荐）

单文件 / 目录 / 通配符统一入口，自动推断尺寸：

```bash
# 幻灯片演示文稿（自动推断 16:9 等比例，按序合并）
python scripts/convert.py slides/ presentation.pdf

# 单文件
python scripts/convert.py page.html out.pdf

# 普通文档转 A4（关闭自动推断）
python scripts/convert.py report.html out.pdf --page-size A4

# 文档型 HTML，加页边距
python scripts/convert.py doc.html out.pdf --page-size A4 --margin 15mm
```

**参数：**

- `--page-size SIZE`：强制纸张（`A4` / `Letter` / `8.5in 11in`），同时关闭自动推断
- `--no-auto-size`：关闭自动推断，用 Chrome 默认纸张
- `--margin M`：页边距，默认 `0`
- `--keep-temp`：保留中间单页 PDF

### merge.py —— 仅合并已有 PDF

不经 Chrome，直接把多个 PDF 合并：

```bash
python scripts/merge.py out.pdf a.pdf b.pdf c.pdf
```

## 工作原理

1. 检测 HTML `body{width;height}`（像素），换算英寸（÷96 DPI）。
2. 注入 `@media print` CSS：`@page { size: <W>in <H>in; margin:0 }` +
   body 尺寸锁定 + `print-color-adjust:exact`。
3. Chrome headless `--print-to-pdf`（绝对路径输出）+ `--virtual-time-budget`（防外部资源超时）+
   `--window-size`（匹配设计尺寸）。
4. 多文件用 PyPDF2 合并，清理临时文件。

## 踩坑记录

> 改脚本时务必遵守，详见 `SKILL.md`。

1. **输出路径必须绝对** —— 相对路径会让 Chrome 报错 `0x3`。
2. **@page size 用 in/cm/mm，不能用 px** —— `1920px 1080px` 无效，要 `20in 11.25in`。
3. **必须 `print-color-adjust: exact`** —— 否则背景色丢失，PDF 与 HTML 内容不一致。
4. **必须 `--virtual-time-budget`** —— 否则 Google Fonts 等外部资源导致超时。
5. **禁止"先转再缩放"** —— 事后用 PyMuPDF 缩放会破坏布局；必须在渲染前注入正确 @page。
6. **控制台编码** —— stdout 强制 UTF-8，日志用 ASCII 标记，避免 GBK 崩溃。

## 故障排除

| 现象 | 解决 |
|------|------|
| 未找到 Chrome | 安装 Chrome 或设 `CHROME_PATH` |
| 超时 | 检查外部资源；`--virtual-time-budget` 已默认 10s |
| 比例不对 | HTML 无固定 body 尺寸 → 用 `--page-size` 指定 |
| 背景变白 | 确认未用 `--no-auto-size` 且 CSS 已注入 |
| PyPDF2 未安装 | `pip install PyPDF2` |
