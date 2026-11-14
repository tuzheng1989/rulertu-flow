---
name: url-to-md
description: URL 转 Markdown 技能。抓取网页内容并转换为干净的 Markdown，使用 Chrome CDP 渲染页面，支持 Defuddle 和 Legacy 双管道转换，支持 YouTube 字幕提取。工具型技能，输出位置由调用方（项目指令）决定。当用户提供链接并要求转为 Markdown / 保存网页内容时使用。
version: 1.1.0
metadata:
  openclaw:
    requires:
      anyBins:
        - bun
        - npx
---

# URL to Markdown

抓取网页内容，转换为 Markdown。工具型技能：输出路径通过 `-o` / `--output-dir` 传入，由调用方（项目指令）决定保存位置。

## 用法

```
${BUN_X} {baseDir}/scripts/main.ts <url> -o <输出路径>.md
```

### Agent 执行步骤

1. 确定 SKILL.md 文件所在目录为 `{baseDir}`
2. 脚本路径 = `{baseDir}/scripts/<script-name>.ts`
3. 解析 `${BUN_X}`：已安装 `bun` → `bun`；否则 `npx -y bun`
4. 首次使用时：若 `{baseDir}/scripts/node_modules` 不存在，先在 `{baseDir}/scripts` 目录执行 `bun install` 安装依赖（依赖清单见 `package.json` 与 `bun.lock`）
5. 将文档中所有 `{baseDir}` 和 `${BUN_X}` 替换为实际值

### 脚本参考

| 脚本 | 用途 |
|------|------|
| `scripts/main.ts` | CLI 入口，抓取 URL |
| `scripts/html-to-markdown.ts` | Markdown 转换协调 |
| `scripts/defuddle-converter.ts` | Defuddle 转换 |
| `scripts/legacy-converter.ts` | Legacy 回退提取和转换 |
| `scripts/markdown-conversion-shared.ts` | 共享元数据解析和文档工具 |
| `scripts/media-localizer.ts` | 媒体下载和本地化 |
| `scripts/cdp.ts` | Chrome CDP 连接管理 |

## 功能

- Chrome CDP 全 JavaScript 渲染
- 双转换管道：Defuddle 优先，自动回退到 Legacy
- Shadow DOM 内容物化
- YouTube 字幕提取
- 本地抓取失败时回退到 `defuddle.md` API
- HTML 快照保存（`*-captured.html`）

## 选项

| 选项 | 说明 |
|------|------|
| `<url>` | 要抓取的 URL |
| `-o <path>` | 输出文件路径 |
| `--output-dir <dir>` | 输出目录（自动生成文件名） |
| `--wait` | 等待用户信号后抓取（用于需要登录的页面） |
| `--timeout <ms>` | 页面加载超时（默认 30000） |
| `--download-media` | 下载图片/视频到本地 |

## 环境变量

| 变量 | 说明 |
|------|------|
| `URL_CHROME_PATH` | 自定义 Chrome 路径 |
| `URL_DATA_DIR` | 自定义数据目录 |
| `URL_CHROME_PROFILE_DIR` | 自定义 Chrome 配置文件目录 |
