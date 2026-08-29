#!/usr/bin/env python3
"""从 LangChain 官方 llms.txt 提取 DeepAgents 相关 URL。

用法:
    python extract_deepagents_urls.py [--prefix URL_PREFIX] [--output PATH]

输出 JSON 数组，每个元素是一个 URL 字符串。
"""

import argparse
import json
import re
import sys
import urllib.request

# 默认配置
DEFAULT_INDEX_URL = "https://docs.langchain.com/llms.txt"
DEFAULT_PREFIX = "https://docs.langchain.com/oss/python/deepagents/"


def fetch_llms_txt(url: str, timeout: int = 30) -> str:
    """下载 llms.txt 纯文本内容。"""
    req = urllib.request.Request(url, headers={"User-Agent": "deepagents-update/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def extract_urls(text: str, prefix: str) -> list[str]:
    """从文本中提取指定前缀的 URL，去重并排序。"""
    # 匹配 https://... 形式的 URL（到空格或行尾）
    all_urls = re.findall(r"https?://[^\s)\]]+", text)
    matched = sorted({u for u in all_urls if u.startswith(prefix)})
    return matched


def main():
    parser = argparse.ArgumentParser(description="提取 DeepAgents 文档 URL")
    parser.add_argument(
        "--prefix",
        default=DEFAULT_PREFIX,
        help=f"URL 前缀过滤 (默认: {DEFAULT_PREFIX})",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="输出文件路径 (默认: stdout)",
    )
    args = parser.parse_args()

    try:
        text = fetch_llms_txt(DEFAULT_INDEX_URL)
    except Exception as e:
        print(f"ERROR: 无法下载 {DEFAULT_INDEX_URL}: {e}", file=sys.stderr)
        print("提示: 可使用 webReader MCP 工具作为 fallback", file=sys.stderr)
        sys.exit(1)

    urls = extract_urls(text, args.prefix)

    if not urls:
        print(
            f"WARNING: 未找到前缀为 {args.prefix} 的 URL",
            file=sys.stderr,
        )

    result = json.dumps(urls, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"已写入 {args.output} ({len(urls)} 个 URL)", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    main()
