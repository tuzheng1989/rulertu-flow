# deep-research 新增 product 通道（Product Hunt 数据源）

- **日期**：2026-11-10
- **状态**：待评审（handoff 自 evoCenter 调研会话）
- **目标插件**：work-skills（deep-research 0.6.1 → 0.7.0；插件 2.3.2 → 2.4.0）

---

## 0. 调研结论（已实测，执行代理免复测）

2026-11-10 对官方端点 `https://mcp.producthunt.com/mcp` 的探测结果：

1. **匿名可用**：无 OAuth、无 API key，直接 POST JSON-RPC `tools/list` 与 `tools/call` 均返回 200 与真实数据（该 server 当前为无状态模式，单次 `tools/call` 无需先 `initialize`，实测三次独立 curl 皆成功）。
2. **限流**：响应头 `x-rate-limit-limit: 250` / 900 秒窗口。单轮研究最多 4 条 product 查询，远低于上限。
3. **工具清单（17 个）**，按用途分两类：
   - **只读调研类（7 个，本方案封装）**：`search_launches`、`semantic_product_search`（向量语义搜索）、`find_alternatives`、`get_product_profile`、`get_products`（分类榜单）、`get_leaderboard`（日/周/月/年榜）、`get_categories`。
   - **账号与写操作类（10 个，本方案排除）**：`get_my_account`、`get_launch_context`、`list_my_launches`、`get_launch`、`start_launch`、`update_launch`、`submit_launch`、`prepare_launch_asset`、`submit_feedback`，以及需登录的 `find_investable_startups`。
4. **返回结构化程度高**：以 `semantic_product_search "AI agent framework"` 实测为例，每条含 slug、name、tagline、description、url、`reviews_rating`、`reviews_count`、categories、makers、**funding（轮次/金额/日期/投资人）**、relevance_score。融资数据是通用网页搜索难以稳定拿到的增量价值。
5. **调用方式**：`POST` + 头 `Accept: application/json, text/event-stream`，响应为纯 JSON（解析器兜底处理 SSE `data:` 行）。超时 20 秒。

### 集成方式裁决：Bash 包装脚本，不注册 MCP server

- **为何不注册 MCP server**（`claude mcp add ... producthunt`）：会把全部 17 个工具 schema 常驻注入每个会话（含 `submit_launch` 等写工具，研究会话里是误操作面），上下文负载约数千 token，且无法按工具过滤。
- **为何走脚本**：与 deep-research v0.5.0 现行五通道架构同构（academic=deepxiv CLI、code/social=sn-search-* 脚本均为 Bash 直调）；只封装 7 个只读工具；无凭据、无会话污染；子代理经 Bash 可达。上游仍是官方 MCP 端点（匿名 JSON-RPC），不碰需 developer token 的 GraphQL API。
- **本仓库网络规则兼容性**：「禁止内置 WebSearch/WebFetch、web 搜索走 MCP」针对通用网页搜索与抓取；dedicated API 直调已有 deepxiv 先例，product 通道同性质。

### 数据定位与使用边界（写入 query 节点选择指南）

- Product Hunt 数据由 maker 自报，默认 `source_tier: secondary`，关键事实需与 web/academic 通道交叉验证，不作 primary。
- 覆盖偏英文市场、独立开发者与 VC 产品；中文市场产品覆盖弱，不适用于国内产品调研的主要来源。
- 榜单（leaderboard）只反映编辑推荐位与互动信号排名，不等于市场份额或竞品全集——竞品发现应 `find_alternatives` + 语义搜索并用，不只看榜。

> **实施期勘误（2026-11-10，B1 批）**：B1 执行时经 `tools/list` 实测上游 inputSchema，与上文「已实测」结论存在三处出入，已按真实 schema 定稿（证据：`plans/work-skills/.flow-evidence/B1/mcp-tools-schema.json`）：① `find_alternatives`/`get_product_profile` 必填参数为 **product_name**（产品名，非 slug）；② `get_leaderboard` 仅必填 `date`，**无 period 参数**，另有可选 `limit`；③ 全部带 limit 的工具上游限制为 **1–8**（inputSchema 声明 `minimum:1` / `maximum:8`，运行时同样强制，脚本本地双端 clamp）；`get_leaderboard` 的 `date` 接受四种周期格式（`YYYY-MM-DD` 日 / `YYYY-Www` 周 / `YYYY-MM` 月 / `YYYY` 年），日/周/月/年榜均可查。另 `search_launches` 面向产品发布流，通用描述词可能合法返回空列表（非失败）。

---

## 1. 路线图

### 优先级矩阵（价值 × 成本）

| 批次 | 内容 | 价值 | 成本 | 级 |
|---|---|---|---|---|
| B1 | sn-search-producthunt 通道脚本 + 测试 | 高（通道本体，无它一切免谈） | 低（纯新增文件，不碰既有契约） | T1 |
| B2 | deep-research 接线（通道映射 / query 节点 / 降级 / 文档 / 版本） | 高（研究循环真正受益） | 中（动技能契约文件，需审计） | T2 |

### 波次依赖图

```
B1 通道脚本 ──▶ B2 deep-research 接线    （单波次：B1 → B2 顺序执行）
```

- B2 依赖 B1 的脚本契约（输出 JSON 包络与子命令），且 B2 的 L3 验收直接调 B1 产物，必须先 B1 后 B2。
- 无并行批次；无纯验证批（各批验证由本批验收与波次收口承担）。

---

## 2. 详案

### B1：sn-search-producthunt 通道脚本（T1）

**如何改**（纯新增，无既有文件改动）：

1. 新建 `plugins/work-skills/skills/sn-search-producthunt/SKILL.md`
   - frontmatter 仿 `sn-search-code/SKILL.md:1-5`：`name`、`description`（面向模型：产品发现/竞品替代/产品档案/分类榜单/融资数据；供 deep-research product 通道与模型按需调用）、`user-invocable: false`。
   - 正文四节：依赖（无需 API key，无需 requirements.txt——仅标准库）、可用脚本表、参数说明、与 deep-research 的关系（product 通道入口，`source_type: product`）。
2. 新建 `plugins/work-skills/skills/sn-search-producthunt/scripts/producthunt_search.py`
   - Python 3 标准库实现（`urllib.request`，与全局依赖准则一致；Windows 下调用方加 `PYTHONIOENCODING=utf-8` 前缀，脚本内 `sys.stdout` 用 utf-8 重配）。
   - 上游调用：`POST https://mcp.producthunt.com/mcp`，JSON-RPC `tools/call`（跳过 `initialize`，实测无状态可用）；响应先按纯 JSON 解析，失败则提取 SSE `data:` 行再解析。
   - 子命令映射（每个子命令对应一个只读工具）：

   | 子命令 | 上游工具 | 参数 |
   |---|---|---|
   | `search "<query>"` | `search_launches` | `--limit N`（默认 10，上游上限 8，脚本自动 clamp） |
   | `semantic "<query>"` | `semantic_product_search` | `--limit N`（默认 10，上游上限 8，脚本自动 clamp） |
   | `alternatives` | `find_alternatives` | `--name <产品名>`（上游参数 product_name，非 slug） |
   | `profile` | `get_product_profile` | `--name <产品名>`（上游参数 product_name，非 slug） |
   | `category` | `get_products` | `--category-slug <分类slug>`、`--limit N` |
   | `leaderboard` | `get_leaderboard` | `--date YYYY-MM-DD`（必填，上游无 period 参数）、`--limit N`（可选） |
   | `categories` | `get_categories` | 无 |

   - **输出包络（本方案契约唯一出处，B2 引用不复制）**：
     ```json
     {"success": true|false, "error": "<仅失败时>",
      "items": [{"title", "url", "snippet", "slug", "rating",
                 "reviews_count", "categories", "makers",
                 "funding", "source_type": "product"}]}
     ```
     `snippet` 取 tagline + description 截断；`items` 字段在上游缺失时省略键（不填 null）；失败（网络错误、JSON-RPC error、限流 429、非 2xx）一律 `success:false` + `error` 说明并退出码 1——deep-research 降级规则以 `success:false` 为触发信号。
3. 新建 `plugins/work-skills/skills/sn-search-producthunt/scripts/test_producthunt_search.py`
   - `unittest` 标准库框架。注意：基线 `deep-research/scripts/test_state_manager.py` 实为自定义函数骨架（`def test_*(results)` + `run_all_tests`，无 `import unittest`），本脚本不模仿该自定义 runner，选标准库框架并保持离线可跑；HTTP 层 monkeypatch 注入 fixture。

**如何验证**：

- L1（离线）：纯 JSON 与 SSE 两种响应解析；`items` 归一化形状；子命令参数校验；JSON-RPC error / 非 2xx / 429 各映射为 `success:false`。命令：`PYTHONIOENCODING=utf-8 python scripts/test_producthunt_search.py`。
- L3（在线冒烟，共 ≤4 次调用）：`semantic "ai note taking app"`、`search "note taking"`、`leaderboard --date 2026-11-09` 各实调一次，断言 `success:true`、`items` 非空、至少一条含 `slug` 与 `title`。（原 `--period week` 为勘误前旧契约，见下注）

**验收标准**：

1. 给定 fixture（纯 JSON）→ `success:true` 且 `items[0]` 含 `title/url/snippet/slug/source_type`；给 SSE fixture → 同结果。PASS/FAIL 逐例留证。
2. 给定 JSON-RPC error fixture → `success:false`、退出码 1、`error` 非空。
3. 离线测试套件全绿（不联网也能全跑）。
4. 在线冒烟三子命令各返回 `success:true` 且 `items` 非空。
5. `git status` 显示本批仅新增上述三个文件，零既有文件改动。

**代码评审节点**：退出码与 `success` 字段的一致性（降级规则的触发契约）；`snippet` 截断不破坏 UTF-8；无密钥、无写操作路径混入。

**分级与验证流程**：T1——纯新增、加法式改动、不邻近任何契约（输出包络是本方案新定义、尚未被消费的契约）、无外部状态变更（只读 API）。定级依据见 optimization-plan 风险分级表；执行侧流程（Executor 实施 + 主控机械验证）以 implement-plan 为准。

### B2：deep-research 接线（T2）

**如何改**（四处既有文件 + 版本，均以当前 0.6.1 行号为锚）：

1. `plugins/work-skills/skills/deep-research/SKILL.md`
   - **L137-145 搜索通道映射表**：新增一行 `product` 通道：Bash `PYTHONIOENCODING=utf-8 python ../sn-search-producthunt/scripts/producthunt_search.py {子命令}`（参数按 query 语义选子命令，契约见 B1 输出包络，此处只写调用方式不复制包络定义）。
   - **L153-159 统一调用约定**：normalize 映射补一条：`sn-search-producthunt` 输出已含 `source_type:"product"`，`items[]` 直接入 `search_results`。
   - **L161-173 降级规则**：pseudocode 与文字中「专门通道」清单补入 product（该规则本身是通用的，只需在枚举处带上）。
   - **L383-393「搜索通道与工具」表 + L404 降级注 + L414-429「搜索与抓取（多源）」prose**：同步补 product 行（这三处是同一信息的三个呈现位，改动为加行，语义以映射表为单一出处）。
   - **L3-4 frontmatter**：`version: 0.6.1 → 0.7.0`；description 末尾追加一句 `v0.7.0 新增 product 通道（Product Hunt 产品/竞品/融资数据，Bash 脚本直调官方 MCP 端点，匿名可用，失败降级 web）。`
2. `plugins/work-skills/skills/deep-research/agents/research-node-query.md`
   - **L25 与 L38**：`source_type` 枚举 `academic|code|social_cn|social_en|web` → 增补 `|product`（两处是 schema 与字段说明，同改）。
   - **L71-86 source_type 选择指南**：表加一行「竞品分析、产品发现、替代品对比、融资信息、发布榜单 → `product`」；选择原则补两句：PH 数据 maker 自报默认 `source_tier: secondary`；榜单≠竞品全集，竞品发现优先 `alternatives`/语义搜索。**不改**首轮固定三角度与后续轮策略（L43-69）——首轮仍至少 1 条 web，product 按主题性质自然入选。
   - **L156 注意事项 5**：source_type 多样性清单含义已覆盖，无需改文，仅确认。
   - **不改 summary/reflect/finalize 三个节点**：`source_type` 是透传标注字段，summary 节点按值标注来源层次，新枚举值自动流转。
3. `plugins/work-skills/skills/deep-research/docs/SEARCH_MIGRATION.md`
   - 文件末尾（v0.5.0 节之后）追加 `## v0.7.0：product 通道（Product Hunt）` 一节：背景、通道架构表加行、数据定位与使用边界（自报数据 secondary、榜单偏置、匿名访问是观测行为可能收紧）。该文件是搜索层的活文档（ARCHITECTURE.md 等已标注滞后，不动）。
4. 版本收口：
   - 根 `CHANGELOG.md` Unreleased 段顶部新增 `work-skills 2.4.0` 条目（风格仿既有条目：一段话讲清动机、改动、双 manifest 同步升版）。
   - `plugins/work-skills/.claude-plugin/plugin.json` 与 `.codex-plugin` 侧 manifest：`2.3.2 → 2.4.0`（双 manifest 同步升版为仓库既定约定）。

**如何验证**：

- L1（机械化一致性）：`product` 枚举在三处声明位（映射表、query 节点 schema、query 节点选择指南）与降级规则枚举处一致出现；`grep -n "product" SKILL.md agents/research-node-query.md` 输出人工核对无遗漏声明位、无重复定义包络。
- L2：既有基线回归——`PYTHONIOENCODING=utf-8 python scripts/test_state_manager.py` 保持 31/31（本批不碰该模块，作红线回归）。
- L3（链路演练，非完整研究循环）：主控按映射表对一条 product query 实际执行「分派 → 脚本调用 → normalize」，断言结果含 `source_type:"product"`；再以错误子命令参数人为触发 `success:false`，断言按降级规则回退 MCP web-search-prime 并留 log。

**验收标准**：

1. 给定查询「AI notetaker 竞品对比」→ query 节点指南含 product 适用行，主控演练该 query 走脚本通道返回 `source_type:"product"` 条目 ≥3 条。PASS/FAIL 留证。
2. 给定脚本失败（错误参数）→ 降级到 web-search-prime 的路径按既有规则触发并有 log，不静默。
3. `test_state_manager.py` 31/31 通过。
4. 五个文档位（映射表/调用约定/降级/实现说明表/prose）对 product 通道的表述无矛盾，包络定义只在 B1 一处。
5. CHANGELOG 条目、双 manifest、deep-research frontmatter 版本号三者一致（2.4.0 / 2.4.0 / 0.7.0）。

**代码评审节点**：包络契约单一出处（B2 各处引用而非复制）；query 节点枚举两处同步；source_tier 默认 secondary 写入选择指南；文档三呈现位语义一致。

**分级与验证流程**：T2——多文件修改、改动 deep-research 的运行时契约文件（source_type 枚举与通道映射被 query/summary/主控分派链路消费）、有既有测试基线（31 用例）。定级边界：本批为加法式扩展，不改既有枚举值、不改既有五通道语义，未触碰仓库红线契约本体，故 T2 而非 T3。执行侧流程（Executor 实施 + Auditor 证据包审计）以 implement-plan 为准。

---

## 3. 风险与不确定点

1. **匿名访问是观测行为**：PH 未承诺匿名额度长期可用；若收紧，脚本返回 `success:false`，既有降级规则兜底到 web 通道，研究不中断。届时可加 OAuth 或作罢，不必预先兼容（极简原则）。
2. **上游是 MCP 端点而非官方 GraphQL API**：工具 schema 非稳定契约，PH 改版可能破坏脚本；B1 的 L1 fixture 化测试 + L3 冒烟会最先暴露，修复面限于单脚本。
3. **数据偏置**：英文市场/独立开发者/VC 产品偏重，中文产品覆盖弱；已在 query 节点选择指南写入使用边界，query 生成器自会避坑。
4. **find_investable_startups 明确排除**：需登录且是投资建议性质数据，超出调研通道范围；用户个人如需，自行注册 MCP server 使用官方安装指引，与本方案无关。

## 4. Handoff 说明

- 执行宿主：rulertu-flow 仓库会话；开工按 implement-plan 开工检查点复述批次。
- 本方案调研证据（端点探测、工具清单、实测响应）在第 0 节，执行代理免复测；若距方案日期超过 30 天，建议先重跑 L3 冒烟确认匿名访问仍可用。
- 方案含 T2 批次，建议定稿前走一轮 auditor 硬伤自审（结果见 `.plan-iterate/` 同名审计记录）。
