# -*- coding: utf-8 -*-
"""pull_repos.py — 自研项目批量拉取脚本（周报步骤 0 固化版）

设计目标（2026-11-06 试跑后固化，用户确认方案一）：
  1. 单仓独立超时：一个仓库网络挂起不拖死整批（试跑实测 9/18 首轮失败、总耗时 25 分钟的教训）
  2. 失败自动重试一轮 + 双通道 fallback：代理（127.0.0.1:7890）失败自动切直连
  3. 失败透明化：输出 JSON（updated/unchanged/failed/local_ahead），失败仓库供周报如实标注
  4. 只拉不推：ff-only 合并（分叉显式报错，本地领先原样保留，绝不产生合并提交）

用法：
  python pull_repos.py                     # 从 evoCenter《研发项目简介.md》读自研项目清单
  python pull_repos.py --list-only         # 只打印清单不执行
  python pull_repos.py --timeout 40        # 单仓 fetch 超时秒数（默认 40）
  python pull_repos.py --json out.json     # 结果同时写 JSON 文件

清单权威来源：D:/runspace/evoCenter/研发项目简介.md 的「自研项目」表格（参考仓库分组一律不拉）。
解析方式：抓取「## 自研项目」到下一个「## 」之间的表格行，取每行第一列目录名。

重点关注机制（2026-11-12 用户定）：
  FOCUS_REPOS 是重点仓库清单（本文件内置，随 rulertu-flow 仓库双机同步）：
    - 重点仓库：fetch + ff-only 合并（原有行为）
    - 非重点仓库：只 fetch 汇报是否有更新（behind 数），不合并到本地
  --focus-only 可只处理重点仓库。
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

RUNSPACE = "D:/runspace"
EVOCENTER = os.path.join(RUNSPACE, "evoCenter")
INTRO_DOC = os.path.join(EVOCENTER, "研发项目简介.md")
PROXY = "http://127.0.0.1:7890"

# 重点关注仓库（2026-11-12 用户定）：周报主动拉代码；其余自研仓只 fetch 汇报是否有更新。
# 目录名与 D:/runspace 下实际目录一致，比较时用 casefold 容错大小写。
FOCUS_REPOS = [
    "evoCenter",
    "peirasim",
    "smartAfsim",
    "evochat",
    "smart-plotting",
    "rhetra-harness",
    "agent-retrieval",
    "kyros-gardener",
    "kyros-sentinel",
    "SkillEvolve",
    "rulertu-flow",
]


def is_focus(repo: str) -> bool:
    return repo.casefold() in {r.casefold() for r in FOCUS_REPOS}


def read_repo_list() -> list:
    """从《研发项目简介.md》解析自研项目目录清单（自研项目两个分组 + evoCenter 自身）。

    说明列含「纯本地仓」的仓库跳过（2026-11-06 用户指示：xd 移出待更新清单）。
    """
    with open(INTRO_DOC, encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"## 自研项目(.*?)(?=\n## )", text, re.S)
    if not m:
        raise SystemExit(f"未能在 {INTRO_DOC} 中找到「## 自研项目」分组")
    section = m.group(1)
    repos = []
    for line in section.splitlines():
        line = line.strip()
        # 表格行形如 | `EvoSim/` | EvoSim | ... 或 | `evoCenter/` | ...
        mm = re.match(r"^\|\s*`([^`|]+?)/?`\s*\|", line)
        if mm:
            repo = mm.group(1).strip()
            if "纯本地仓" in line:  # 远端失效/无远端，不参与批量拉取
                print(f"[  local_only] {repo}: 简介文档标注纯本地仓，跳过", file=sys.stderr)
                continue
            repos.append(repo)
    repos.append("evoCenter")
    return sorted(set(repos))


def run_git(repo_path: str, args: list, timeout: int, use_proxy: bool) -> tuple:
    """执行一条 git 命令，返回 (成功?, stdout+stderr)。代理通道失败时由调用方切直连重试。"""
    cmd = ["git", "-C", repo_path] + args
    if use_proxy:
        cmd = ["git", "-C", repo_path, "-c", f"http.proxy={PROXY}", "-c", f"https.proxy={PROXY}"] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        return (r.returncode == 0, (r.stdout or "") + (r.stderr or ""))
    except subprocess.TimeoutExpired:
        return (False, f"TIMEOUT after {timeout}s: {' '.join(args)}")
    except Exception as e:
        return (False, f"{type(e).__name__}: {e}")


def fetch_with_fallback(repo_path: str, timeout: int) -> tuple:
    """单仓 fetch：代理 → 失败切直连 → 都失败再各试一轮。返回 (成功?, 详情)。"""
    attempts = []
    for round_no in (1, 2):  # 两轮，每轮代理+直连各一次
        for use_proxy in (True, False):
            ok, out = run_git(repo_path, ["fetch", "--quiet"], timeout, use_proxy)
            channel = "proxy" if use_proxy else "direct"
            if ok:
                return (True, f"ok ({channel}, round {round_no})")
            attempts.append(f"r{round_no}/{channel}: {out.strip().splitlines()[-1] if out.strip() else 'empty'}")
    return (False, " | ".join(attempts))


def pull_one(repo: str, timeout: int, merge: bool = True) -> dict:
    """处理单个仓库：fetch → status 判断 →（重点仓）ff-only 合并。返回结果 dict。

    merge=False（非重点仓库）：fetch 后只汇报 behind 数，不合并到本地。
    """
    repo_path = os.path.join(RUNSPACE, repo)
    result = {"repo": repo, "status": "unknown", "detail": ""}
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        result["status"] = "no_git"
        result["detail"] = "目录不存在或不是 git 仓库"
        return result

    ok, detail = fetch_with_fallback(repo_path, timeout)
    if not ok:
        result["status"] = "failed"
        result["detail"] = detail
        return result

    # status -sb 判断 ahead/behind
    ok, out = run_git(repo_path, ["status", "-sb"], timeout, False)
    if not ok:
        result["status"] = "failed"
        result["detail"] = f"fetch ok but status failed: {out}"
        return result
    first = out.splitlines()[0] if out.strip() else ""
    branch = first.split("...")[0].strip("## ").strip()
    behind = re.search(r"behind (\d+)", first)
    ahead = re.search(r"ahead (\d+)", first)

    if ahead and not behind:
        result["status"] = "local_ahead"
        result["detail"] = f"本地领先 {ahead.group(1)}，未推送（只拉不推）"
        return result
    if not behind:
        result["status"] = "unchanged"
        result["detail"] = "已是最新"
        return result

    # 非重点仓库：只汇报落后，不合并（2026-11-12 用户定）
    if not merge:
        result["status"] = "behind_unmerged"
        result["detail"] = f"远端有 {behind.group(1)} 个新提交（非重点关注，仅汇报未拉取）"
        return result

    # 落后 → ff-only 合并
    n = behind.group(1)
    ok, out = run_git(repo_path, ["merge", "--ff-only", f"origin/{branch.split('/')[-1]}"], timeout, False)
    if ok:
        result["status"] = "updated"
        result["detail"] = f"ff-only 合并 {n} 个提交"
        return result
    # ff-only 失败 = 分叉（本地和远端各有提交）——显式暴露，不自动处理
    result["status"] = "diverged"
    result["detail"] = f"本地与远端分叉（落后 {n}），ff-only 拒绝合并，需人工决策: {out.strip().splitlines()[-1] if out.strip() else ''}"
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=40, help="单仓 fetch 超时秒数（默认 40）")
    ap.add_argument("--json", default="", help="结果 JSON 另存路径（stdout 始终输出 JSON）")
    ap.add_argument("--list-only", action="store_true", help="只打印仓库清单不执行")
    ap.add_argument("--force", action="store_true", help="忽略缓存，全部仓库重新 fetch")
    ap.add_argument("--cache-hours", type=float, default=24, help="缓存有效期小时数（默认 24）")
    ap.add_argument("--focus-only", action="store_true", help="只处理重点关注仓库（跳过非重点仓）")
    args = ap.parse_args()

    all_repos = read_repo_list()
    repos = [r for r in all_repos if is_focus(r)] if args.focus_only else all_repos
    if args.list_only:
        focus_mark = lambda r: "*" if is_focus(r) else " "  # noqa: E731
        print("\n".join(f"{focus_mark(r)} {r}" for r in all_repos))
        print("(标 * 为重点关注仓库)", file=sys.stderr)
        return

    # 跳过缓存：上一次运行记录（<24h 内 unchanged/no_git/local_ahead 的仓库不重复 fetch，
    # 除非 --force。updated/failed/diverged 不缓存——每次都要重试）
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".pull_repos_cache.json")
    cache = {}
    if os.path.isfile(cache_path) and not args.force:
        try:
            with open(cache_path, encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {}
    now = time.time()
    fresh = {k: v for k, v in cache.items() if now - v.get("ts", 0) < args.cache_hours * 3600
             and v.get("status") in ("unchanged", "local_ahead", "no_git")}

    t0 = time.time()
    results = []
    for repo in repos:
        if repo in fresh and not args.force:
            r = {"repo": repo, "status": fresh[repo]["status"], "detail": fresh[repo]["detail"] + "（缓存）"}
            results.append(r)
            print(f"[{r['status']:>12}] {repo}: {r['detail']}", file=sys.stderr)
            continue
        r = pull_one(repo, args.timeout, merge=is_focus(repo))
        results.append(r)
        print(f"[{r['status']:>12}] {repo}: {r['detail']}", file=sys.stderr)
        # 写缓存（仅可缓存状态）
        if r["status"] in ("unchanged", "local_ahead", "no_git"):
            cache[repo] = {"status": r["status"], "detail": r["detail"], "ts": now}
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    summary = {
        "total": len(results),
        "focus_repos": FOCUS_REPOS,
        "updated": [r["repo"] for r in results if r["status"] == "updated"],
        "unchanged": [r["repo"] for r in results if r["status"] == "unchanged"],
        "behind_unmerged": [r for r in results if r["status"] == "behind_unmerged"],
        "local_ahead": [{"repo": r["repo"], "detail": r["detail"]} for r in results if r["status"] == "local_ahead"],
        "diverged": [r for r in results if r["status"] == "diverged"],
        "failed": [r for r in results if r["status"] == "failed"],
        "skipped_no_git": [r["repo"] for r in results if r["status"] == "no_git"],
        "elapsed_sec": round(time.time() - t0, 1),
    }
    out = json.dumps(summary, ensure_ascii=False, indent=2)
    print(out)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            f.write(out)
    # 有失败时分叉/失败仓库的退出码非零，便于调用方感知
    sys.exit(1 if (summary["failed"] or summary["diverged"]) else 0)


if __name__ == "__main__":
    main()
