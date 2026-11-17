# 发布：Bundle 打包、安装与插件市场

> 精编自官方 `docs/user/develop/basic/publish.md`、`docs/user/guide/plugin-market.md`（v0.2.2-rc.3）。前置：完成 [[plugin-basics.md]]。

## bundle 包结构

bundle = npm 包 + `dsh.bundle` 清单。三件套：

```text
hello-plugin/
├── package.json       # 声明 dsh.bundle
├── cordis.patch.yml   # 该 bundle 被列出时应用的层
└── index.js           # patch 行引用的插件模块
```

`package.json`：

```json
{
  "name": "dsh-hello-plugin",
  "version": "0.1.0",
  "type": "module",
  "main": "index.js",
  "files": ["index.js", "cordis.patch.yml"],
  "dsh": { "bundle": { "patch": "./cordis.patch.yml" } }
}
```

`index.js`：

```js
export const name = 'hello-plugin'
export function apply() {
  console.log('[hello-plugin] plugin loaded!')
}
```

`cordis.patch.yml`——与 `--patch` 覆盖层同构，但插件行**按包名引用**（Node 解析找到已安装代码），不再写相对源路径：

```yaml
- insert:
    - id: hello
      name: dsh-hello-plugin
```

规则与变体：

- `patch` 接受有序文件列表（如 `["./base.patch.yml", "./web.patch.yml"]`），按序作为一层应用；每文件内的相对插件路径解析到该文件旁边。
- 没有 `dsh.bundle` 声明的包仍可安装，但只是普通依赖：`dsh plugin` 打警告、不激活层。给「被插件包 import 的库」用这种形态。
- **版本兼容声明**：`"engines": { "dsh": ">=0.2.0 <0.3.0" }`；安装与 profile 启动都会校验，不满足拒绝。未声明则回退检查 `@deepseek-ai/dsh*` peer 依赖范围。

## 安装进 profile

```sh
dsh plugin --profile demo add ./hello-plugin     # 本地 checkout
dsh plugin --profile demo add github:you/hello-plugin   # Git 直装（见下）
dsh plugin --profile demo add ./hello-plugin-0.1.0.tgz  # tarball
dsh plugin --profile demo add your-package       # npm
dsh plugin --profile demo remove dsh-hello-plugin
```

首次使用初始化 profile（`@deepseek-ai/dsh-base` 为首层 bundle）→ pnpm 链接 → `dsh` 把 bundle 追加进 `dsh.profile.bundles`。验证与启动：

```sh
dsh --profile demo --dump-config   # 应出现 "# == dsh-hello-plugin" 层
dsh --profile demo
```

**依赖声明纪律**（linked checkout 保持自己的 node_modules）：

- 需要与宿主**共享实例**的 dsh 包 → 同时写进 `peerDependencies` + `devDependencies`（peer 供运行时安装解析，dev 供你的类型检查与独立测试）。
- 独立版本的三方依赖、无状态 dsh 工具 → `dependencies`。

## 加载顺序对 bundle 作者的意义

有效配置 = bundles 依序 → profile patch → home patch → `--patch`（后层按 id 整行覆盖前层，**不深合并**）。推论：

1. 你的 patch 可按 `id` 覆盖早层行（`dsh-web-app` 就这么覆盖 `dsh-base`）——但必须**复述该行需要的每个键**，不能只写改动键。
2. 用户可在自己的 profile patch 里覆盖你的行、不动你的包——所以把默认值做成用户大概率保留的值，其余进 schema。
3. 内置 bundle 名永远从 dsh 安装解析；你的 bundle 可以放心依赖 `@deepseek-ai/dsh-base` 存在且最新。

## 给 surface bundle 配自己的命令行

可运行 app 的 bundle 挂一个普通 provider 插件：`inject = ['cmdlineArgs']`，用 `@deepseek-ai/dsh-cmdline` 的 `parseCmdline` 解析自己的 commander program，从 program action 提供 app-owned 服务。launcher 把 launcher 旗标后的全部参数以不可变快照交给每个插件——app 专属旗标无需改 launcher，多插件可解析同一快照。消费行经 `!!js` 读该服务并以部署值兜底：

```yaml
- id: hello-startup
  name: 'dsh-hello-plugin/startup'

- id: my-app
  name: '@example/my-app'
  inject: [myAppStartup]
  config:
    port: !!js ctx.myAppStartup.port ?? 8080
```

`--help` 时 provider 不发布服务 → 这些行不激活。

## GitHub 直装的 build-script 坑

Git 安装拉的是**源码不是制品**：没人跑你的 build 脚本，TypeScript 包没有 `lib/` 就加载失败。两侧各做一件事：

- **作者**：提供自包含 `prepare` 脚本（pnpm 在 git 安装后执行），从源码产出发布入口；不得假设 monorepo 兄弟目录等开发环境（可用独立 tsdown config 转译 `src/`，不做 project references 与类型检查）。
- **用户**：pnpm ≥10 默认拒绝跑 git 依赖的 `prepare`，首次 `add` 会失败；把 pnpm 打印的包键抄进 profile 的 `pnpm-workspace.yaml` 再重装：

```yaml
allowBuilds:
  dsh-hello-plugin: true
```

这条 allowance = **允许该包的代码在你机器上、在 agent 沙箱之外的安装期执行**。只放行可信来源，并钉住 commit（`github:you/hello-plugin#<sha>`）防后续 push 静默换代码。

不想让用户放行构建 → 分发制品：npm 发布（`pnpm publish` 时已构建）或 `pnpm pack` 产 tarball。两者都无需构建权限。

## 插件市场（Plugin Index）

插件索引 = 一个 JSON 文件，列出可安装 bundle（标题/图标/作者/版本）。dsh 不自带索引源。

**浏览安装**：Plugins 页开 **Custom plugin indexes**（实验插件）→ 出现 **Discover** 页签与 Creator 模式只读 `plugin_market` 工具 → Add index source 填索引 URL（必须 http/https、无凭据无 fragment；不受信网络用 https）→ 搜索/筛选/排序 → 确认后走正常安装流程（含兼容性与注册表校验）。推荐版本 = 与当前 dsh 兼容的最高非预发布版本。

**发布索引**：UTF-8 JSON（默认上限 128 MiB），任意静态主机（GitHub Pages 等）。图标可内联 data URL（≤32 KiB）或相对/绝对 URL（相对相对索引 URL 解析；跨源绝对必须 https）。最小示例：

```json
{
  "format": 1,
  "title": { "en": "Team plugins", "zh": "团队插件" },
  "plugins": [
    {
      "name": "dsh-plugin-foo",
      "title": "Foo",
      "description": "Adds the foo tool",
      "icon": "icons/foo.svg",
      "author": "Jane Doe",
      "homepage": "https://github.com/jane/dsh-plugin-foo#readme",
      "repository": { "url": "https://github.com/jane/dsh-plugin-foo" },
      "versions": [
        { "version": "1.1.0", "publishTimestamp": 1790476800,
          "source": { "type": "npm" }, "engines": { "dsh": ">=0.2.0-rc.2" } }
      ]
    }
  ]
}
```

字段要点：`format: 1` 必填；文本字段可 `LocalizedText`（对象须含 `en`）；`versions[].source` = `{type:"npm", registry?}` 或 `{type:"git", url(https), commit(40-hex), path?}`；`engines.dsh` 可选。任何规则违反 = 整个索引被拒并给出 JSON path。官方参考生成器：`apps/plugin-market-generator`（输入每行一个 npm 名或 https git URL，只读不执行包代码）。

给插件仓库加 GitHub topic [`dsh-plugin`](https://github.com/topics/dsh-plugin) 提升可发现性。
