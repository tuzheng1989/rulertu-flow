> 本文件为 docs-trans 的 url-to-md mode（2026-11-14 组建）。执行入口与 mode 路由见 SKILL.md。脚本路径相对本文件所在目录（modes/）解析。

# URL to Markdown

抓取网页内容，转换为 Markdown。工具型技能：输出路径通过 `-o` / `--output-dir` 传入，由调用方（项目指令）决定保存位置。

## 用法

```
${BUN_X} ../scripts/url/main.ts <url> -o <输出路径>.md
```

### Agent 执行步骤

1. 本文档位于 docs-trans 技能的 `modes/` 子目录，脚本树位于技能根的 `scripts/url/`
2. 脚本路径 = `../scripts/url/<script-name>.ts`（相对本文档所在目录解析）
3. 解析 `${BUN_X}`：已安装 `bun` → `bun`；否则 `npx -y bun`
4. 首次使用时：若 `../scripts/url/node_modules` 不存在，先在 `../scripts/url` 目录执行 `bun install` 安装依赖（依赖清单见该目录下的 `package.json` 与 `bun.lock`）
5. 将命令中的 `${BUN_X}` 替换为实际值后执行

### 脚本参考

| 脚本 | 用途 |
|------|------|
| `../scripts/url/main.ts` | CLI 入口，抓取 URL |
| `../scripts/url/html-to-markdown.ts` | Markdown 转换协调 |
| `../scripts/url/defuddle-converter.ts` | Defuddle 转换 |
| `../scripts/url/legacy-converter.ts` | Legacy 回退提取和转换 |
| `../scripts/url/markdown-conversion-shared.ts` | 共享元数据解析和文档工具 |
| `../scripts/url/media-localizer.ts` | 媒体下载和本地化 |
| `../scripts/url/cdp.ts` | Chrome CDP 连接管理 |

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
