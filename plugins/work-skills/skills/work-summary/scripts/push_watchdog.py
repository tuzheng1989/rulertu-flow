# -*- coding: utf-8 -*-
"""push_watchdog.py — 重点关注仓库每日推送守护（2026-11-12 用户定）

机制：每天定时检查 FOCUS_REPOS 是否存在「已提交但未推送」（ahead），存在则推送。
  - 未提交的工作区更改一律忽略（可能是中间产物，绝不自动 add/commit）
  - push 双通道 fallback：默认配置 → 代理（127.0.0.1:7890）→ 直连，一条失败换另一条
  - push 被拒（non-fast-forward，远端有新提交）：不自动 merge，只报告，由会话/人工处理
  - 静默约定：全部仓库干净时 stdout 输出为空（配合 cron no_agent 模式不发消息）

用法：
  python push_watchdog.py            # 检查并推送，stdout 输出人类可读报告（干净时为空）
  python push_watchdog.py --json out.json   # 结果另存 JSON（stderr 输出过程日志）

清单来源：复用 pull_repos.py 的 FOCUS_REPOS（同一份重点清单，随 rulertu-flow 双机同步）。
"""

import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pull_repos import FOCUS_REPOS, RUNSPACE, PROXY, run_git


def push_with_fallback(repo_path: str, timeout: int) -> tuple:
    """单仓 push：默认 → 代理 → 直连，两轮。返回 (成功?, 详情)。"""
    channels = [False, True, False, True]  # (默认配置, 代理) × 2 轮
    attempts = []
    for i, use_proxy in enumerate(channels):
        ok, out = run_git(repo_path, ["push"], timeout, use_proxy)
        label = "proxy" if use_proxy else "default"
        if ok:
            return (True, f"ok ({label})")
        tail = out.strip().splitlines()[-1] if out.strip() else "empty"
        if "rejected" in out or "non-fast-forward" in out.lower():
            return (False, f"rejected（远端有新提交，需 fetch+merge 后再推）: {tail}")
        attempts.append(f"{i + 1}/{label}: {tail}")
    return (False, " | ".join(attempts))


def check_one(repo: str, timeout: int) -> dict:
    """检查单仓：有 ahead 则推送。未提交更改不感知、不处理。"""
    repo_path = os.path.join(RUNSPACE, repo)
    result = {"repo": repo, "status": "clean", "detail": ""}
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        result["status"] = "no_git"
        return result

    ok, out = run_git(repo_path, ["status", "-sb"], timeout, False)
    if not ok:
        result["status"] = "failed"
        result["detail"] = f"status failed: {out.strip()}"
        return result
    first = out.splitlines()[0] if out.strip() else ""
    if "..." not in first:
        # 无 upstream 是项目自身状态（如纯本地仓），不是「已提交未推送」，不进报告防噪音
        result["status"] = "no_upstream"
        result["detail"] = f"分支无 upstream，跳过（{first.strip('# ').strip()}）"
        return result
    ahead = re.search(r"ahead (\d+)", first)
    if not ahead:
        return result  # clean

    n = ahead.group(1)
    ok, detail = push_with_fallback(repo_path, timeout)
    if ok:
        result["status"] = "pushed"
        result["detail"] = f"已推送 {n} 个提交"
    else:
        result["status"] = "push_failed"
        result["detail"] = f"领先 {n} 但推送失败: {detail}"
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=40, help="单仓 push 超时秒数（默认 40）")
    ap.add_argument("--json", default="", help="结果 JSON 另存路径")
    args = ap.parse_args()

    t0 = time.time()
    results = []
    for repo in FOCUS_REPOS:
        r = check_one(repo, args.timeout)
        results.append(r)
        print(f"[{r['status']:>11}] {repo}: {r['detail'] or '干净'}", file=sys.stderr)

    acted = [r for r in results if r["status"] in ("pushed", "push_failed")]
    abnormal = [r for r in results if r["status"] in ("push_failed", "failed")]
    summary = {
        "focus_repos": FOCUS_REPOS,
        "pushed": [r for r in results if r["status"] == "pushed"],
        "push_failed": [r for r in results if r["status"] == "push_failed"],
        "failed": [r for r in results if r["status"] == "failed"],
        "no_upstream": [r for r in results if r["status"] == "no_upstream"],
        "elapsed_sec": round(time.time() - t0, 1),
    }

    # 人类可读报告：无动作且无异常 → 空 stdout（cron no_agent 静默）
    if not acted and not abnormal:
        if args.json:
            with open(args.json, "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
        sys.exit(0)
    lines = []
    for r in acted:
        mark = "✅" if r["status"] == "pushed" else "❌"
        lines.append(f"{mark} {r['repo']}：{r['detail']}")
    for r in abnormal:
        if r not in acted:
            lines.append(f"⚠️ {r['repo']}：{r['detail']}")
    lines.append(f"\n（推送守护 {summary['elapsed_sec']}s，其余重点关注仓库干净；未提交的工作区更改未处理）")
    out = "\n".join(lines)

    print(out)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
    sys.exit(1 if summary["push_failed"] or summary["failed"] else 0)


if __name__ == "__main__":
    main()
