#!/usr/bin/env python3
"""对比官方文档 URL 列表与本地 references/ 目录，输出差异报告。

用法:
    python compare_docs.py --urls URLS_JSON --refs REFS_DIR [--output PATH]

URL 到文件名的映射规则:
    去掉前缀 .../deepagents/，剩余路径段对应 references/ 下的 .md 文件。
    例: .../deepagents/code/overview → references/code/overview.md

输出 JSON:
    {
      "new_pages": [{"url": "...", "ref_path": "references/xxx.md"}],
      "existing_pages": [{"url": "...", "ref_path": "references/xxx.md"}],
      "removed_pages": ["references/xxx.md"]
    }
"""

import argparse
import json
import os
import sys

# URL 前缀，用于提取相对路径
DEEPAGENTS_PREFIX = "https://docs.langchain.com/oss/python/deepagents/"


def url_to_ref_path(url: str) -> str:
    """将官方 URL 转为本地 references/ 下的相对路径。"""
    if not url.startswith(DEEPAGENTS_PREFIX):
        return None
    relative = url[len(DEEPAGENTS_PREFIX) :]
    # 去掉尾部斜杠和可能的 .md / .html 后缀
    relative = relative.rstrip("/")
    for suffix in (".html", ".md"):
        if relative.endswith(suffix):
            relative = relative[: -len(suffix)]
            break
    # 统一用正斜杠，与 scan_local_refs 的归一化保持一致
    return "references/" + relative + ".md"


def scan_local_refs(refs_dir: str) -> set[str]:
    """递归扫描 references/ 目录下所有 .md 文件，返回相对路径集合。"""
    local = set()
    for root, _, files in os.walk(refs_dir):
        for f in files:
            if f.endswith(".md"):
                full = os.path.join(root, f)
                # 转为相对于 refs_dir 父目录的路径
                rel = os.path.relpath(full, os.path.dirname(refs_dir))
                # 统一用正斜杠
                local.add(rel.replace(os.sep, "/"))
    return local


def main():
    parser = argparse.ArgumentParser(description="对比官方文档与本地文件")
    parser.add_argument(
        "--urls",
        required=True,
        help="步骤 2 输出的 URL JSON 文件路径",
    )
    parser.add_argument(
        "--refs",
        required=True,
        help="本地 references/ 目录路径",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="输出文件路径 (默认: stdout)",
    )
    args = parser.parse_args()

    # 归一化路径，避免尾部斜杠导致 dirname 求出 references 自身
    args.refs = os.path.normpath(args.refs)

    # 读取 URL 列表
    with open(args.urls, encoding="utf-8") as f:
        urls = json.load(f)

    # 扫描本地文件
    local_files = scan_local_refs(args.refs)

    # 对比
    new_pages = []
    existing_pages = []
    matched_locals = set()

    for url in urls:
        ref_path = url_to_ref_path(url)
        if ref_path is None:
            continue
        if ref_path in local_files:
            existing_pages.append({"url": url, "ref_path": ref_path})
            matched_locals.add(ref_path)
        else:
            new_pages.append({"url": url, "ref_path": ref_path})

    removed_pages = sorted(local_files - matched_locals)

    result = {
        "new_pages": new_pages,
        "existing_pages": existing_pages,
        "removed_pages": removed_pages,
    }

    # 输出到 stderr 方便查看
    print(f"  新增: {len(new_pages)} 个", file=sys.stderr)
    print(f"  已有: {len(existing_pages)} 个", file=sys.stderr)
    print(f"  已移除: {len(removed_pages)} 个", file=sys.stderr)

    output = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"已写入 {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
