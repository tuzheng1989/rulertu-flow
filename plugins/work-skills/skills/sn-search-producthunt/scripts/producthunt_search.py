#!/usr/bin/env python3
"""Product Hunt 搜索。经官方 MCP 端点匿名调用（JSON-RPC 2.0 tools/call，无 OAuth、无 API key）。

端点实测（2026-11-10）：无状态，单次 tools/call 无需先 initialize；响应通常为纯 JSON，
解析失败时兜底提取 SSE data: 行再解析；限流 250 次/900 秒（本用途远达不到，429 按失败处理）。
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

MCP_URL = "https://mcp.producthunt.com/mcp"
TIMEOUT_SECONDS = 20
SNIPPET_MAX_CHARS = 300

# 从 payload 中找产品列表的实证键：semantic 实测 products；categories/launches/leaderboard
# 按工具语义一一对应。不做投机兜底——未知形状显式失败，让 deep-research 降级规则可触发。
_LIST_KEYS = ("products", "categories", "launches", "leaderboard")


def _configure_stdout() -> None:
    """Windows 控制台兼容：stdout/stderr 重配为 utf-8。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------------
# HTTP 层（测试替身边界：patch 本函数即可离线）
# ---------------------------------------------------------------------------

def _http_post_json(url: str, payload: dict) -> tuple[int, str]:
    """POST JSON-RPC 请求，返回 (HTTP 状态码, 响应体文本)。非 2xx 不在此抛错，由上层统一判定。"""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": "sn-search-producthunt/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:  # 429 / 5xx 等：读出响应体一并返回
        return error.code, error.read().decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# 响应解析与归一化（纯函数层）
# ---------------------------------------------------------------------------

def _parse_response_body(body: str) -> dict:
    """按纯 JSON 解析；失败则逐行提取 SSE data: 行的 JSON 负载再解析。"""
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        pass
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        text = line[len("data:"):].strip()
        if not text or text == "[DONE]":
            continue
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            continue
    raise ValueError("响应不是纯 JSON，SSE data 行中也无有效 JSON")


def _extract_tool_payload(rpc_result: object) -> object:
    """从 tools/call result 中取出结构化负载：structuredContent 优先，其次 content 的 JSON text 块。"""
    if not isinstance(rpc_result, dict):
        raise ValueError("tools/call result 形状不符合预期")
    structured = rpc_result.get("structuredContent")
    if isinstance(structured, (dict, list)):
        return structured
    content = rpc_result.get("content")
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "text":
                continue
            text = block.get("text")
            if not isinstance(text, str):
                continue
            stripped = text.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                return json.loads(stripped)
    raise ValueError("tools/call result 中找不到 structuredContent 或 JSON text 块")


def _extract_item_list(payload: object) -> list:
    """从结构化负载中定位产品列表；定位不到显式报错（静默空成功会让降级规则失效）。"""
    if isinstance(payload, list):
        return [entry for entry in payload if isinstance(entry, dict)]
    if isinstance(payload, dict):
        for key in _LIST_KEYS:
            value = payload.get(key)
            if isinstance(value, list):
                return [entry for entry in value if isinstance(entry, dict)]
        for value in payload.values():  # 实测包裹：{"status": "ok", "data": {"products": [...]}}
            if isinstance(value, dict):
                for key in _LIST_KEYS:
                    inner = value.get(key)
                    if isinstance(inner, list):
                        return [entry for entry in inner if isinstance(entry, dict)]
    raise ValueError("无法从上游负载定位产品列表（未知形状）")


def _stringify_names(value: object) -> list[str] | None:
    """把 [{name: ...}] / ["..."] 归一为字符串列表；不可归一或为空则返回 None（省键）。"""
    if not isinstance(value, list):
        return None
    names: list[str] = []
    for entry in value:
        if isinstance(entry, dict):
            name = entry.get("name") or entry.get("title") or entry.get("slug")
            if isinstance(name, str) and name:
                names.append(name)
        elif isinstance(entry, str) and entry:
            names.append(entry)
    return names or None


def _normalize_item(raw: object) -> dict:
    """上游产品 dict → 输出包络的 item。缺失字段省键；source_type 恒为 product。"""
    if not isinstance(raw, dict):
        return {}
    item: dict = {"source_type": "product"}
    title = raw.get("name") or raw.get("title")
    if isinstance(title, str) and title:
        item["title"] = title
    url = raw.get("url")
    if isinstance(url, str) and url:
        item["url"] = url
    tagline = raw.get("tagline")
    description = raw.get("description")
    if isinstance(tagline, str) or isinstance(description, str):
        snippet = " — ".join(part for part in (tagline, description) if isinstance(part, str) and part)
        if snippet:
            item["snippet"] = snippet[:SNIPPET_MAX_CHARS]
    slug = raw.get("slug")
    if isinstance(slug, str) and slug:
        item["slug"] = slug
    rating = raw.get("reviews_rating", raw.get("rating"))
    if isinstance(rating, (int, float)):
        item["rating"] = rating
    reviews_count = raw.get("reviews_count")
    if isinstance(reviews_count, int):
        item["reviews_count"] = reviews_count
    categories = _stringify_names(raw.get("categories"))
    if categories:
        item["categories"] = categories
    makers = _stringify_names(raw.get("makers"))
    if makers:
        item["makers"] = makers
    if isinstance(raw.get("funding"), dict):
        item["funding"] = raw["funding"]
    return item


# ---------------------------------------------------------------------------
# 子命令 → 上游工具映射
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="producthunt_search",
        description="Product Hunt 搜索：官方 MCP 端点匿名 JSON-RPC，无需 API key",
    )
    sub = parser.add_subparsers(dest="command", required=True,
                                metavar="{search|semantic|alternatives|profile|category|leaderboard|categories}")

    p = sub.add_parser("search", help="关键词搜索产品（上游工具 search_launches）")
    p.add_argument("query", help="搜索关键词")
    p.add_argument("--limit", type=int, default=8, help="返回数量（默认 8，上游上限 8）")

    p = sub.add_parser("semantic", help="语义搜索产品（上游工具 semantic_product_search）")
    p.add_argument("query", help="自然语言描述")
    p.add_argument("--limit", type=int, default=8, help="返回数量（默认 8，上游上限 8）")

    p = sub.add_parser("alternatives", help="查找某产品的替代品（上游工具 find_alternatives）")
    p.add_argument("--name", required=True, help="产品名（上游参数 product_name，如 Notion）")

    p = sub.add_parser("profile", help="产品档案（上游工具 get_product_profile）")
    p.add_argument("--name", required=True, help="产品名（上游参数 product_name）")

    p = sub.add_parser("category", help="分类下产品（上游工具 get_products）")
    p.add_argument("--category-slug", required=True, help="分类 slug（上游参数 category_slug，先 categories 查列表）")
    p.add_argument("--limit", type=int, default=8, help="返回数量（默认 8，上游上限 8）")

    p = sub.add_parser("leaderboard", help="榜单（上游工具 get_leaderboard）")
    p.add_argument("--date", required=True,
                   help="榜单周期：YYYY-MM-DD（日）/ YYYY-Www（周）/ YYYY-MM（月）/ YYYY（年）")
    p.add_argument("--limit", type=int, default=8, help="返回数量（默认 8，上游上限 8）")

    sub.add_parser("categories", help="分类列表（上游工具 get_categories）")
    return parser


LIMIT_UPPER = 8  # 上游 inputSchema 声明 limit minimum:1 / maximum:8（mcp-tools-schema.json），运行时同样强制（实测超限被拒）


def _clamp_limit(value: int) -> int:
    return max(1, min(value, LIMIT_UPPER))


def resolve_tool_call(args: argparse.Namespace) -> tuple[str, dict]:
    """argparse Namespace → (上游工具名, 工具参数)。键名以上游 inputSchema 为准（mcp-tools-schema.json）。"""
    if args.command == "search":
        return "search_launches", {"query": args.query, "limit": _clamp_limit(args.limit)}
    if args.command == "semantic":
        return "semantic_product_search", {"query": args.query, "limit": _clamp_limit(args.limit)}
    if args.command == "alternatives":
        return "find_alternatives", {"product_name": args.name}
    if args.command == "profile":
        return "get_product_profile", {"product_name": args.name}
    if args.command == "category":
        return "get_products", {"category_slug": args.category_slug, "limit": _clamp_limit(args.limit)}
    if args.command == "leaderboard":
        return "get_leaderboard", {"date": args.date, "limit": _clamp_limit(args.limit)}
    return "get_categories", {}


# ---------------------------------------------------------------------------
# CLI 主流程
# ---------------------------------------------------------------------------

def _call_upstream(tool_name: str, tool_arguments: dict) -> list[dict]:
    """调用上游并归一化为 items；任何失败以异常表达，由 main 统一转失败包络。"""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": tool_arguments},
    }
    status, body = _http_post_json(MCP_URL, request)
    if not 200 <= status < 300:
        hint = "（限流，250 次/900 秒）" if status == 429 else ""
        raise RuntimeError(f"上游 HTTP {status}{hint}")
    rpc_response = _parse_response_body(body)
    if not isinstance(rpc_response, dict):
        raise ValueError("JSON-RPC 响应不是对象")
    if rpc_response.get("error"):
        error = rpc_response["error"]
        raise RuntimeError(f"JSON-RPC 错误 {error.get('code')}: {error.get('message')}")
    result = rpc_response.get("result")
    if isinstance(result, dict) and result.get("isError"):
        # 上游以 result.isError + content 文本表达业务错误（如缺必填参数），透出原始信息
        raise RuntimeError(f"上游工具执行失败: {_first_text(result)}")
    payload = _extract_tool_payload(result)
    return [item for item in (_normalize_entry(entry) for entry in _extract_item_list(payload)) if item]


def _first_text(rpc_result: dict) -> str:
    content = rpc_result.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str) and block["text"].strip():
                return block["text"].strip()
    return "（无错误详情）"


def _normalize_entry(entry: object) -> dict:
    return _normalize_item(entry)


def main(argv: list[str] | None = None) -> None:
    _configure_stdout()
    args = build_parser().parse_args(argv)
    try:
        tool_name, tool_arguments = resolve_tool_call(args)
        items = _call_upstream(tool_name, tool_arguments)
        print(json.dumps({"success": True, "items": items}, ensure_ascii=False))
        sys.exit(0)
    except Exception as error:  # 网络/解析/JSON-RPC/限流等一律失败包络 + 退出码 1
        print(json.dumps({"success": False, "error": str(error)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
