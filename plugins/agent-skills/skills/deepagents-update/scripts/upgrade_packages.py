#!/usr/bin/env python3
"""升级 Python 包并记录版本变化。

用法:
    python upgrade_packages.py [--packages pkg1 pkg2 ...] [--output PATH]

输出 JSON:
    {
      "packages": {
        "deepagents": {"old": "0.1.0", "new": "0.2.0"},
        ...
      }
    }
"""

import argparse
import json
import subprocess
import sys


def get_version(package: str) -> str | None:
    """获取已安装包的版本号，未安装返回 None。"""
    try:
        result = subprocess.run(
            ["pip", "show", package],
            capture_output=True,
            text=True,
            timeout=30,
        )
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return None


def upgrade_package(package: str) -> str | None:
    """升级包并返回新版本号。"""
    try:
        subprocess.run(
            ["pip", "install", "--upgrade", package],
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"WARNING: 升级 {package} 失败: {e.stderr}", file=sys.stderr)
        return None
    return get_version(package)


def main():
    parser = argparse.ArgumentParser(description="升级包并记录版本变化")
    parser.add_argument(
        "--packages",
        nargs="+",
        default=["deepagents", "langchain", "langgraph"],
        help="要升级的包列表",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="输出文件路径 (默认: stdout)",
    )
    args = parser.parse_args()

    results = {}
    for pkg in args.packages:
        old = get_version(pkg)
        new = upgrade_package(pkg) if old is not None else get_version(pkg)
        results[pkg] = {"old": old, "new": new}

        status = f"{old or '(未安装)'} → {new or '(未安装)'}"
        print(f"  {pkg}: {status}", file=sys.stderr)

    output = json.dumps({"packages": results}, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"已写入 {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
