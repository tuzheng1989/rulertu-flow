#!/usr/bin/env python3
"""producthunt_search.py 的离线单元测试。

测试替身边界 = monkeypatch HTTP（producthunt_search._http_post_json），绝不真联网。
fixture 取自 2026-11-10 真实上游响应（截断版），保持与线上形状一致。
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))

import producthunt_search as ph


# ---------------------------------------------------------------------------
# fixtures（形状取自真实上游响应）
# ---------------------------------------------------------------------------

FIXTURE_PRODUCT = {
    "slug": "evernote-for-ios",
    "name": "Evernote for iOS",
    "tagline": "The most popular note-taking app, reengineered.",
    "description": "The new Evernote for iOS app features a redesigned UI and navigation.",
    "url": "https://www.producthunt.com/products/evernote-for-ios?ref=mcp",
    "thumbnail_url": "https://ph-files.imgix.net/xxx.png",
    "reviews_rating": 4.5,
    "reviews_count": 4,
    "categories": [{"name": "Note and writing apps", "slug": "notes-documents"}],
    "makers": [{"name": "Rob Nichols"}, {"name": "Sahand Hajizadeh"}],
    "funding": {"total_raised_usd": 0.0, "is_bootstrapped": True},
    "relevance_score": 0.692,
}


def _rpc_payload(products: list[dict]) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [{"type": "text", "text": "Products matching ..."}],
            "isError": False,
            "structuredContent": {"status": "ok", "data": {"products": products}},
        },
    }


FIXTURE_BODY_PLAIN = json.dumps(_rpc_payload([FIXTURE_PRODUCT]), ensure_ascii=False)
# SSE 形态：同一负载包在 data: 行里
FIXTURE_BODY_SSE = "event: message\r\ndata: " + FIXTURE_BODY_PLAIN + "\r\n\r\n"

FIXTURE_BODY_RPC_ERROR = json.dumps({
    "jsonrpc": "2.0",
    "id": 1,
    "error": {"code": -32000, "message": "tool not found"},
}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 切片 1：响应解析（纯函数层）
# ---------------------------------------------------------------------------

class TestParseResponseBody(unittest.TestCase):

    def test_plain_json(self):
        body = '{"jsonrpc": "2.0", "id": 1, "result": {"ok": true}}'
        self.assertEqual(ph._parse_response_body(body), {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}})

    def test_sse_data_line(self):
        body = 'event: message\r\ndata: {"jsonrpc": "2.0", "result": {"ok": 1}}\r\n\r\n'
        self.assertEqual(ph._parse_response_body(body), {"jsonrpc": "2.0", "result": {"ok": 1}})

    def test_sse_skips_done_and_comment_lines(self):
        body = (
            ": keepalive\n"
            "data: [DONE]\n"
            'data: {"jsonrpc": "2.0", "result": {"ok": 2}}\n'
            'data: not-json\n'
        )
        self.assertEqual(ph._parse_response_body(body), {"jsonrpc": "2.0", "result": {"ok": 2}})

    def test_unparseable_raises(self):
        with self.assertRaises(ValueError):
            ph._parse_response_body("<html>gateway error</html>")


class TestExtractItemList(unittest.TestCase):

    def test_structured_content_wrapped_in_data_products(self):
        payload = {"status": "ok", "data": {"query": "q", "products": [FIXTURE_PRODUCT]}}
        self.assertEqual(ph._extract_item_list(payload), [FIXTURE_PRODUCT])

    def test_payload_is_bare_list(self):
        self.assertEqual(ph._extract_item_list([FIXTURE_PRODUCT]), [FIXTURE_PRODUCT])

    def test_unknown_payload_shape_raises(self):
        # 静默空成功会让 deep-research 降级规则失效，未知形状必须显式失败
        with self.assertRaises(ValueError):
            ph._extract_item_list({"status": "ok"})


# ---------------------------------------------------------------------------
# 切片 2：items 归一化（纯函数层）
# ---------------------------------------------------------------------------

class TestNormalizeItem(unittest.TestCase):

    def test_full_item_maps_contract_fields(self):
        item = ph._normalize_item(FIXTURE_PRODUCT)
        self.assertEqual(item["title"], "Evernote for iOS")
        self.assertEqual(item["url"], "https://www.producthunt.com/products/evernote-for-ios?ref=mcp")
        self.assertEqual(item["slug"], "evernote-for-ios")
        self.assertEqual(item["rating"], 4.5)
        self.assertEqual(item["reviews_count"], 4)
        self.assertEqual(item["categories"], ["Note and writing apps"])
        self.assertEqual(item["makers"], ["Rob Nichols", "Sahand Hajizadeh"])
        self.assertEqual(item["funding"], {"total_raised_usd": 0.0, "is_bootstrapped": True})
        self.assertEqual(item["source_type"], "product")

    def test_snippet_joins_tagline_and_description(self):
        item = ph._normalize_item(FIXTURE_PRODUCT)
        self.assertEqual(item["snippet"], FIXTURE_PRODUCT["tagline"] + " — " + FIXTURE_PRODUCT["description"])

    def test_missing_fields_omit_keys(self):
        item = ph._normalize_item({"name": "NoteIt", "slug": "noteit"})
        self.assertEqual(item, {"source_type": "product", "title": "NoteIt", "slug": "noteit"})
        self.assertNotIn("url", item)
        self.assertNotIn("rating", item)
        self.assertNotIn("snippet", item)
        self.assertNotIn("funding", item)

    def test_snippet_truncated_by_chars_no_mojibake(self):
        # 150 个中文字符 × 3 字节/字符 = 450 字节 > 300；按字符截断不得产生乱码
        raw = {
            "name": "中文产品",
            "slug": "cn-product",
            "tagline": "简短标语",
            "description": "深" * 400,
        }
        item = ph._normalize_item(raw)
        self.assertLessEqual(len(item["snippet"]), 300)
        self.assertTrue(item["snippet"].isprintable())
        item["snippet"].encode("utf-8").decode("utf-8")  # 乱码会在此时报错

    def test_non_dict_input_filtered(self):
        self.assertEqual(ph._normalize_item("junk"), {})
        self.assertEqual(ph._normalize_item(None), {})


# ---------------------------------------------------------------------------
# 切片 3+4：CLI 包络（公开接缝 1）、子命令分发、参数校验、错误路径
# ---------------------------------------------------------------------------

class CliTestBase(unittest.TestCase):
    """运行 ph.main() 并捕获 stdout JSON 与退出码；HTTP 层一律打桩。"""

    def run_cli(self, argv: list[str], *, body: str = "", status: int = 200,
                side_effect: Exception | None = None) -> tuple[dict, int | None]:
        stub = mock.Mock(return_value=(status, body)) if side_effect is None else mock.Mock(side_effect=side_effect)
        out = io.StringIO()
        with mock.patch.object(ph, "_http_post_json", stub), \
                contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                ph.main(argv)
        code = ctx.exception.code
        exit_code: int | None = None
        if isinstance(code, int):
            exit_code = code
        return json.loads(out.getvalue()), exit_code

    def assert_failure(self, envelope: dict, code: int | None, needle: str) -> None:
        self.assertFalse(envelope["success"])
        self.assertIn(needle, envelope["error"])
        self.assertNotIn("items", envelope)
        self.assertEqual(code, 1)


class TestCliSuccessEnvelope(CliTestBase):

    def test_plain_json_fixture(self):
        envelope, code = self.run_cli(["semantic", "ai note taking app", "--limit", "2"],
                                      body=FIXTURE_BODY_PLAIN, status=200)
        self.assertTrue(envelope["success"])
        self.assertEqual(code, 0)
        item = envelope["items"][0]
        for key in ("title", "url", "snippet", "slug", "source_type"):
            self.assertIn(key, item)
        self.assertEqual(item["source_type"], "product")

    def test_sse_fixture(self):
        envelope, code = self.run_cli(["search", "note taking", "--limit", "5"],
                                      body=FIXTURE_BODY_SSE, status=200)
        self.assertTrue(envelope["success"])
        self.assertEqual(code, 0)
        self.assertEqual(envelope["items"][0]["slug"], "evernote-for-ios")

    def test_rpc_payload_is_tools_call(self):
        stub = mock.Mock(return_value=(200, FIXTURE_BODY_PLAIN))
        with mock.patch.object(ph, "_http_post_json", stub), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                ph.main(["semantic", "ai note taking app", "--limit", "2"])
        request = stub.call_args.args[1]
        self.assertEqual(request["jsonrpc"], "2.0")
        self.assertEqual(request["method"], "tools/call")
        self.assertEqual(request["params"]["name"], "semantic_product_search")
        self.assertEqual(request["params"]["arguments"], {"query": "ai note taking app", "limit": 2})

    def test_leaderboard_tool_args(self):
        parser = ph.build_parser()
        args = parser.parse_args(["leaderboard", "--date", "2026-11-09"])
        self.assertEqual(ph.resolve_tool_call(args), ("get_leaderboard", {"date": "2026-11-09", "limit": 8}))

    def test_leaderboard_limit_clamped_to_8(self):
        # 上游 inputSchema 声明 limit minimum:1 / maximum:8，运行时同样强制（实测超限被拒）
        parser = ph.build_parser()
        args = parser.parse_args(["leaderboard", "--date", "2026-11-09", "--limit", "20"])
        self.assertEqual(ph.resolve_tool_call(args)[1]["limit"], 8)

    def test_limit_clamped_to_minimum_1(self):
        # 上游 inputSchema 声明 minimum:1，0/负数在本地 clamp 到 1，避免晦涩的上游报错
        parser = ph.build_parser()
        args = parser.parse_args(["search", "ai", "--limit", "0"])
        self.assertEqual(ph.resolve_tool_call(args)[1]["limit"], 1)

    def test_search_limit_clamped_to_8(self):
        # 省略 --limit 时本地默认 8（schema maximum：search_launches default 8）
        parser = ph.build_parser()
        args = parser.parse_args(["search", "note taking app"])
        self.assertEqual(ph.resolve_tool_call(args)[1]["limit"], 8)

    def test_schema_driven_tool_args(self):
        # 参数键名以上游 inputSchema 为准（mcp-tools-schema.json，2026-11-10 tools/list 实测）
        parser = ph.build_parser()
        args = parser.parse_args(["alternatives", "--name", "Notion"])
        self.assertEqual(ph.resolve_tool_call(args), ("find_alternatives", {"product_name": "Notion"}))
        args = parser.parse_args(["profile", "--name", "Notion"])
        self.assertEqual(ph.resolve_tool_call(args), ("get_product_profile", {"product_name": "Notion"}))
        args = parser.parse_args(["category", "--category-slug", "ai", "--limit", "5"])
        self.assertEqual(ph.resolve_tool_call(args), ("get_products", {"category_slug": "ai", "limit": 5}))
        args = parser.parse_args(["categories"])
        self.assertEqual(ph.resolve_tool_call(args), ("get_categories", {}))

    def test_categories_subcommand(self):
        body = json.dumps({"jsonrpc": "2.0", "id": 1,
                           "result": {"structuredContent": {"categories": [
                               {"name": "Artificial Intelligence", "slug": "artificial-intelligence"}]}}})
        envelope, code = self.run_cli(["categories"], body=body, status=200)
        self.assertTrue(envelope["success"])
        self.assertEqual(code, 0)
        self.assertEqual(envelope["items"][0]["slug"], "artificial-intelligence")


class TestCliArgumentValidation(CliTestBase):

    def test_alternatives_requires_name(self):
        with mock.patch.object(ph, "_http_post_json"), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                ph.build_parser().parse_args(["alternatives"])
        self.assertEqual(ctx.exception.code, 2)

    def test_profile_requires_name(self):
        with mock.patch.object(ph, "_http_post_json"), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                ph.build_parser().parse_args(["profile"])
        self.assertEqual(ctx.exception.code, 2)

    def test_leaderboard_requires_date(self):
        # 上游 inputSchema（tools/list 实测）：date 必填，无 period 参数
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                ph.build_parser().parse_args(["leaderboard"])
        self.assertEqual(ctx.exception.code, 2)

    def test_leaderboard_rejects_period(self):
        # --period 已按 schema 移除，传入应为未知参数错误
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                ph.build_parser().parse_args(["leaderboard", "--period", "week", "--date", "2026-11-09"])
        self.assertEqual(ctx.exception.code, 2)

    def test_no_subcommand_exits(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                ph.build_parser().parse_args([])
        self.assertEqual(ctx.exception.code, 2)


class TestCliErrorPaths(CliTestBase):

    def test_rpc_error_maps_to_failure(self):
        envelope, code = self.run_cli(["search", "x"], body=FIXTURE_BODY_RPC_ERROR, status=200)
        self.assert_failure(envelope, code, "tool not found")

    def test_http_429_maps_to_failure(self):
        envelope, code = self.run_cli(["search", "x"], body="rate limited", status=429)
        self.assert_failure(envelope, code, "429")

    def test_http_500_maps_to_failure(self):
        envelope, code = self.run_cli(["search", "x"], body="boom", status=500)
        self.assert_failure(envelope, code, "500")

    def test_network_error_maps_to_failure(self):
        import urllib.error
        envelope, code = self.run_cli(["search", "x"],
                                      side_effect=urllib.error.URLError("connection refused"))
        self.assert_failure(envelope, code, "connection refused")

    def test_unparseable_body_maps_to_failure(self):
        envelope, code = self.run_cli(["search", "x"], body="<html>proxy</html>", status=200)
        self.assert_failure(envelope, code, "JSON")

    def test_text_only_result_maps_to_failure(self):
        # 实测（2026-11-10）：get_leaderboard 返回纯文本榜单（无 structuredContent、text 非 JSON），
        # 按保守契约映射为 success:false，由下游通道降级兜底。
        body = json.dumps({"jsonrpc": "2.0", "id": 1,
                           "result": {"content": [{"type": "text",
                                                   "text": "1. ProductA - 350 upvotes\n2. ProductB - 300 upvotes"}],
                                      "isError": False}})
        envelope, code = self.run_cli(["leaderboard", "--date", "2026-11-09"],
                                      body=body, status=200)
        self.assert_failure(envelope, code, "JSON")

    def test_is_error_result_surfaces_upstream_message(self):
        # 实测（2026-11-10）：上游以 result.isError + content 文本表达业务错误（缺必填参数等），
        # 必须透出原始错误信息而非含糊的解析失败。
        body = json.dumps({"jsonrpc": "2.0", "id": 1,
                           "result": {"content": [{"type": "text", "text": "Missing required arguments: date"}],
                                      "isError": True}})
        envelope, code = self.run_cli(["leaderboard", "--date", "2026-11-09"],
                                      body=body, status=200)
        self.assert_failure(envelope, code, "Missing required arguments: date")

    def test_empty_items_is_success(self):
        body = json.dumps({"jsonrpc": "2.0", "id": 1,
                           "result": {"structuredContent": {"status": "ok", "data": {"products": []}}}})
        envelope, code = self.run_cli(["search", "zzz-no-hit"], body=body, status=200)
        self.assertTrue(envelope["success"])
        self.assertEqual(envelope["items"], [])
        self.assertEqual(code, 0)

    def test_unknown_shape_maps_to_failure(self):
        # 未知包裹形状显式失败（success:false + 退出码 1），由 deep-research 降级规则兜底，不静默
        body = json.dumps({"jsonrpc": "2.0", "id": 1,
                           "result": {"structuredContent": {"status": "ok", "records": [FIXTURE_PRODUCT]}}})
        envelope, code = self.run_cli(["search", "x"], body=body, status=200)
        self.assert_failure(envelope, code, "未知形状")


if __name__ == "__main__":
    unittest.main()
