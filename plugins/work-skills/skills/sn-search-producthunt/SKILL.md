---
name: sn-search-producthunt
description: 搜索 Product Hunt 产品数据：产品发现、竞品/替代品查找、产品档案（评分/评论/融资）、分类榜单与分类列表。当任务涉及产品发现、竞品分析、市场调研、融资数据时触发；供 deep-research product 通道按 source_type=product 分派调用。
user-invocable: false
---

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
| `search "<query>"` | `search_launches` | `--limit N`（默认 10，上游上限 8） |
| `semantic "<query>"` | `semantic_product_search` | `--limit N`（默认 10，上游上限 8） |
| `alternatives` | `find_alternatives` | `--name <产品名>`（如 `"Notion"`，注意是产品名不是 slug） |
| `profile` | `get_product_profile` | `--name <产品名>`（上游参数 product_name） |
| `category` | `get_products` | `--category-slug <分类slug>`、`--limit N`（默认 10，上游上限 8） |
| `leaderboard` | `get_leaderboard` | `--date YYYY-MM-DD`（必填，查该日榜单）、`--limit N`（默认 10，上游上限 8） |
| `categories` | `get_categories` | 无 |

```bash
python scripts/producthunt_search.py semantic "ai note taking app" --limit 5
python scripts/producthunt_search.py search "note taking" --limit 8
python scripts/producthunt_search.py alternatives --name "Evernote"
python scripts/producthunt_search.py profile --name "Notion"
python scripts/producthunt_search.py category --category-slug ai-tools --limit 8
python scripts/producthunt_search.py leaderboard --date 2026-11-09
python scripts/producthunt_search.py categories
```

输出为标准 JSON 包络（成功时含 `items`；失败时省略 `items`，脚本退出码 1）：

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

本脚本是 deep-research 的 **product 通道入口**（`source_type: product`），调用方式与其他 sn-search-* 通道一致：

```bash
PYTHONIOENCODING=utf-8 python ../sn-search-producthunt/scripts/producthunt_search.py semantic "{query}" --limit {N}
```

Product Hunt 数据由 maker 自报，关键事实（融资额、评分、用户规模）需与 web / academic 通道交叉验证，不宜单独作为结论依据。
