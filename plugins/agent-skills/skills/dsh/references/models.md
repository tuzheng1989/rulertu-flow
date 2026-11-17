# 模型接入与配置

> 精编自官方 `docs/user/guide/providers.md`（v0.2.2-rc.3）。模型改动在下次请求即生效，无需重启服务。

## DeepSeek 官方直连

Web UI：**Settings → Models** → DeepSeek 卡片填 API key（[platform.deepseek.com](https://platform.deepseek.com/)）→ 保存。

- key 只写不读：保存后页面只见脱敏描述，实际存于 `$DSH_HOME/.credentials.yaml`，设置里只留凭据引用。
- 默认端点下模型列表跟随 DeepSeek API 发布（按需加载，使用中约每 10 分钟后台刷新，失败回退内置列表）。
- 直连路由自带推理档位 `off/low/high/max`，默认档位可用 `llm-deepseek.reasoningEffort` 配置：

```yaml
- id: llm-deepseek
  config:
    reasoningEffort: max
```

## 第三方内置 provider

**Settings → Models** → **Add model provider** → **Third-party model provider**：选择内置 provider（`anthropic`、`openai`、`moonshotai`（Kimi）、`zai`（GLM）等），填 key 保存。端点、协议、模型列表由已装目录提供。

- key 留空则回退已存凭据或环境变量（绿色提示 = 检测到环境变量；黄色 = 未检测到）。
- 走自建网关的内置 provider 模型目录仍来自内置目录；要看网关真实供给，需建自定义 provider 再抓取。

## 自定义模型 API（OpenAI 兼容网关/中转/自托管）

**Add model provider** → **Custom model API**，填写：

| 字段 | 说明 |
|------|------|
| Provider ID | 小写、**永久**（请求、会话、默认模型、凭据引用都用它；改名 = 新建 + 删除旧的） |
| Base URL | 网关地址；Gemini 协议需含版本段（如 `https://gateway.example/v1beta`） |
| API protocol | 四选一：`openai-completions` / `openai-responses` / `anthropic-messages` / `google-generative-ai`（一个 provider 只讲一种协议；网关双协议 = 建两个 provider） |
| 凭据 + 至少一个模型 | — |

配置写入当前 profile 的 `cordis.patch.yml`，等价 YAML（pi-ai 形态）：

```yaml
- id: llm-pi-ai
  config:
    providers:
      my-gateway:
        apiKeyEnv: GATEWAY_API_KEY      # 或 apiKey
        api: openai-completions
        baseURL: https://gateway.example/v1
        models:
          - id: my-model
```

**模型发现**：**Model catalog → Fetch available models** 用表单当前端点/协议/key 调 OpenAI 兼容 `GET /models`；失败或不识别格式时手工添加模型 id 即可。

## 网关兼容开关（compat）——最常见故障源

网关地址可达、key 正确但**每个请求都被拒**，多半是请求形状与 OpenAI 不一致。两大高频问题与修法（写在路由或模型上，模型级逐字段优先）：

```yaml
- id: llm-pi-ai
  config:
    providers:
      my-gateway:
        api: openai-completions
        baseURL: https://gateway.example/v1
        compat:
          supportsDeveloperRole: false   # 推理模型的系统提示走 developer 角色，多数网关直接拒
          maxTokensField: max_tokens     # 只认 max_tokens 的服务器拒 max_completion_tokens
        models:
          - id: my-model
```

其他常用 compat：

| 开关 | 用途 |
|------|------|
| `thinkingFormat: deepseek` | 「默认就在思考」的模型（如经 OpenAI 兼容网关的 DeepSeek V4）：`off` 档改发 `thinking: {type: disabled}`，其他档发 `enabled` + effort |
| 开关留空（如 `supportsDeveloperRole:`） | **报错不忽略**——空值会抹掉目录已知值却什么都没说 |
| 协议不认识的开关 | 报错并列出该协议可用的开关 |

compat 是「声明你的端点如何表现」，不做探测验证；设了网关实际不需要的开关只是发出不同请求。

## 推理档位（reasoningEfforts）

手工添加的模型默认无档位声明（Effort 菜单不出现，是否思考由端点默认决定）。自定义 provider 可在 UI **Model options → Reasoning levels** 或 YAML 声明：

```yaml
        models:
          - id: my-reasoner
            reasoningEfforts:
              off:            # off 留空 = 不发 reasoning 字段
              high: high
              max: xhigh      # 值 = 线上 reasoning_effort 的实际拼写
```

- 路由级 `reasoning: <档位>` 是会话未选档位时的默认；在 picker 里选档会与模型一起存为新会话默认。
- 内置 provider 的模型用 `modelOverrides` 移除档位：`reasoningEfforts: false`。

## 图像输入

模型默认纯文本。启用图像：UI **Model options → Input types → Image**，或 YAML：

```yaml
        models:
          - id: vision-preview
            input: [text, image]        # pi-ai 字段；省略则继承目录/defaultInput（默认 [text]）
        defaultInput: [text, image]     # 路由级兜底，模型级 input 优先
```

- DeepSeek 直连路由用 `inputModalities`（省略 = 纯文本，空列表被拒）；账号模型用 `modelOverrides` 微调单模型（如 `contextWindow`/`maxTokens`）。
- 声明图像而端点不真的支持 → 请求被 provider 拒；从 `input`/`defaultInput` 移除 `image` 并**开新会话**（旧会话日志里附着的图会重复触发）。

## 选模型

- 已配 provider 出现在模型 picker；**选中即成为新会话默认**；已发过请求的会话沿用自己日志里记录的模型。
- 调整 provider 内模型顺序：**Customized settings** 拖拽三线柄（或聚焦后上下箭头）→ Apply。
- 已存默认指向已删 provider → 输入框锁死为 **Select model**，必须另选。

## 排障速查

| 症状 | 处置 |
|------|------|
| `MISSING_CREDENTIAL` | Models 页存 key 或提供所引用的环境变量 |
| `UNKNOWN_MODEL` | 选已配置模型，或把缺的模型加进自定义 provider |
| 抓模型列表 401 | 查 key；不提供 `GET /models` 的端点手工添加 |
| key/URL 都对但全被拒 | 加 `compat.supportsDeveloperRole: false` + `compat.maxTokensField: max_tokens` |
| 只有推理模型失败 | `compat.supportsDeveloperRole: false`（developer 角色被拒） |
| `off` 档停不下思考 | `compat.thinkingFormat: deepseek` |
| 手工模型无 Effort 菜单 | 补 `reasoningEfforts` 声明 |

## 编程接线（给插件作者）

自定义网关走 UI/YAML 即可；要接**全新协议**的 provider 才写 LLM adapter，见 [[llm-adapters.md]]。全部插件配置字段与默认值查生成目录 `docs/config-catalog.md`（源自源码，不会滞后）。
