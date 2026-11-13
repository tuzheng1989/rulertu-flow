> 本文件为 product 通道契约文档（原 sn-search-producthunt skill，2026-11-13 收编进 deep-research）。

# sn-search-producthunt - Product Hunt 搜索

调用 Product Hunt 官方 MCP 端点（`https://mcp.producthunt.com/mcp`）的搜索脚本。匿名 JSON-RPC，无需 OAuth、无需 API key。

## 依赖

无需 API key，无需 requirements.txt（仅 Python 3 标准库）。

## 可用脚本

| 脚本 | 数据源 | 用途 | API key |
|------|--------|------|---------|
| `producthunt_search.py` | Product Hunt | 产品搜索、语义搜索、替代品、产品档案、分类与榜单 | 无需 |

## 参数说明

```bash
python scripts/producthunt_search.py <子命令> [参数]
```

7 个子命令对应上游 7 个只读工具（参数键名以上游 inputSchema 为准，见 `plans/work-skills/.flow-evidence/B1/mcp-tools-schema.json`）：

| 子命令 | 上游工具 | 参数 |
|--------|----------|------|
| `search "<query>"` | `search_launches` | `--limit N`（默认 8，上游 schema 限 1–8） |
| `semantic "<query>"` | `semantic_product_search` | `--limit N`（默认 8，上游 schema 限 1–8） |
| `alternatives` | `find_alternatives` | `--name <产品名>`（如 `"Notion"`，注意是产品名不是 slug） |
| `profile` | `get_product_profile` | `--name <产品名>`（上游参数 product_name） |
| `category` | `get_products` | `--category-slug <分类slug>`、`--limit N`（默认 8，上游 schema 限 1–8） |
| `leaderboard` | `get_leaderboard` | `--date <周期>`（必填，四种格式：`YYYY-MM-DD` 日榜 / `YYYY-Www` 周榜 / `YYYY-MM` 月榜 / `YYYY` 年榜）、`--limit N`（默认 8，上游 schema 限 1–8） |
| `categories` | `get_categories` | 无 |

```bash
python scripts/producthunt_search.py semantic "ai note taking app" --limit 5
python scripts/producthunt_search.py search "note taking" --limit 8
python scripts/producthunt_search.py alternatives --name "Evernote"
python scripts/producthunt_search.py profile --name "Notion"
python scripts/producthunt_search.py category --category-slug ai-tools --limit 8
python scripts/producthunt_search.py leaderboard --date 2026-11-09        # 日榜
python scripts/producthunt_search.py leaderboard --date 2026-11          # 月榜
python scripts/producthunt_search.py categories
```

输出为标准 JSON 包络（成功时含 `items`；失败时省略 `items`，脚本退出码 1）。**用法错误**（缺必填参数、未知 flag）由 argparse 在包络之前拦截：退出码 2、stdout 无 JSON——按退出码判失败的调用方两种码都算失败。成功包络示例：

```json
{
  "success": true,
  "items": [
    {"title": "...", "url": "...", "snippet": "...", "slug": "...", "rating": 4.5,
     "reviews_count": 12, "categories": ["..."], "makers": ["..."],
     "funding": {"total_raised_usd": 0.0, "is_bootstrapped": true},
     "source_type": "product"}
  ]
}
```

`snippet` 为 tagline + description 拼接（按字符截断约 300 字符）；`items` 内字段在上游缺失时省略键，不填 null。

**注意**：`search`（search_launches）面向产品**发布流**，通用描述性查询词可能合法返回空列表（`success:true` + `items:[]`，非失败）——此时换更具体的产品词，或改用 `semantic` 语义搜索。

## 与 deep-research 的关系

本脚本是 deep-research 的 **product 通道入口**（`source_type: product`），调用方式与其他脚本通道一致（cwd = deep-research 技能根）：

```bash
PYTHONIOENCODING=utf-8 python scripts/channels/product/scripts/producthunt_search.py semantic "{query}" --limit {N}
```

Product Hunt 数据由 maker 自报，关键事实（融资额、评分、用户规模）需与 web / academic 通道交叉验证，不宜单独作为结论依据。
