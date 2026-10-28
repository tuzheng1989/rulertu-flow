#!/usr/bin/env python3
"""
周报数据采集脚本 —— 采集原始数据，输出结构化 JSON 到 stdout。
合并、去重、改写、成稿由 Agent（weekly-report 技能）完成。

数据来源：
  1. Claude Code 会话记录 (~/.claude/history.jsonl)
  2. Codex 会话记录 (~/.codex/history.jsonl + session_index.jsonl)
  3. Git 提交记录 (--repos 指定的目录树，默认 D:/runspace)
  4. 统计信息（条数、项目列表）

Hermes 会话（session_search）无法脚本化，由 Agent 侧补充。

用法：
  python collect.py                          # 默认周期（上周一12:00~本周一12:00），默认 D:/runspace
  python collect.py --repos D:/work          # 指定仓库根目录
  python collect.py --days 7                 # 最近 7 天（自然日，替代默认周窗口）
  python collect.py -o report-data.json      # 写文件而非 stdout

输出：JSON 到 stdout（--output-file 指定时写文件），日志到 stderr。
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================
# 配置
# ============================================================

CLAUDE_HISTORY = Path.home() / ".claude" / "history.jsonl"
CODEX_HISTORY = Path.home() / ".codex" / "history.jsonl"
CODEX_SESSION_INDEX = Path.home() / ".codex" / "session_index.jsonl"
DEFAULT_REPOS_ROOT = Path("D:/runspace")

CONTENT_MAX_CHARS = 300   # 会话输入截断长度，足够 Agent 理解意图
COMMIT_MSG_MAX = 200

# 无意义的会话输入，过滤掉
TRIVIAL_INPUTS = {
    "可以", "请继续", "继续", "好的", "嗯", "ok", "OK", "Ok",
    "1", "2", "3", "y", "Y", "yes", "Yes", "对", "是",
    "继续吧", "没问题", "行", "好",
}


# ============================================================
# 时间范围
# ============================================================

def week_range():
    """上周一 12:00 — 本周一 12:00。"""
    today = datetime.now()
    weekday = today.weekday()
    last_monday = today - timedelta(days=7 if weekday == 0 else weekday + 7)
    this_monday = last_monday + timedelta(days=7)
    return (
        last_monday.replace(hour=12, minute=0, second=0, microsecond=0),
        this_monday.replace(hour=12, minute=0, second=0, microsecond=0),
    )


def days_range(days: int):
    """最近 N 天：N 天前同时刻 — 现在。"""
    now = datetime.now()
    return now - timedelta(days=days), now


# ============================================================
# 数据源 1：Claude Code 会话
# ============================================================

def collect_claude(start_dt, end_dt):
    """~/.claude/history.jsonl：timestamp(毫秒)/project/display，按项目分组。"""
    if not CLAUDE_HISTORY.exists():
        log(f"Claude Code 历史不存在: {CLAUDE_HISTORY}")
        return {}

    start_ts, end_ts = start_dt.timestamp(), end_dt.timestamp()
    by_project = {}

    with open(CLAUDE_HISTORY, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                if "timestamp" not in data:
                    continue
                ts = data["timestamp"] / 1000
                if not (start_ts <= ts <= end_ts):
                    continue
                proj = data.get("project", "")
                if not proj:
                    continue
                display = (data.get("display") or "").strip()
                if len(display) <= 5 or display in TRIVIAL_INPUTS:
                    continue
                dt = datetime.fromtimestamp(ts)
                by_project.setdefault(Path(proj).name, []).append({
                    "date": dt.strftime("%Y-%m-%d"),
                    "time": dt.strftime("%H:%M"),
                    "content": display[:CONTENT_MAX_CHARS],
                })
            except Exception:
                continue
    return by_project


# ============================================================
# 数据源 2：Codex 会话
# ============================================================

def collect_codex(start_dt, end_dt):
    """~/.codex/history.jsonl(ts 秒) + session_index.jsonl(thread_name)。

    返回 {项目名|session前8位: [{date, time, content, title}]}。
    Codex history 无项目路径，项目归属由 Agent 结合内容判断或深挖 sessions/。
    """
    if not CODEX_HISTORY.exists():
        log(f"Codex 历史不存在: {CODEX_HISTORY}")
        return {}

    # 标题索引：session_id -> thread_name
    titles = {}
    if CODEX_SESSION_INDEX.exists():
        with open(CODEX_SESSION_INDEX, encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    if d.get("id") and d.get("thread_name"):
                        titles[d["id"]] = d["thread_name"]
                except Exception:
                    continue

    start_ts, end_ts = start_dt.timestamp(), end_dt.timestamp()
    by_session = {}

    with open(CODEX_HISTORY, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                ts = data.get("ts")
                if ts is None or not (start_ts <= ts <= end_ts):
                    continue
                text = (data.get("text") or "").strip()
                if len(text) <= 5 or text in TRIVIAL_INPUTS:
                    continue
                sid = data.get("session_id", "")
                key = sid[:8] if sid else f"codex-{len(by_session)}"
                dt = datetime.fromtimestamp(ts)
                entry = {
                    "date": dt.strftime("%Y-%m-%d"),
                    "time": dt.strftime("%H:%M"),
                    "content": text[:CONTENT_MAX_CHARS],
                }
                title = titles.get(sid)
                if title:
                    entry["title"] = title
                # 同会话多条输入聚合到同一 key
                if key in by_session:
                    by_session[key]["items"].append(entry)
                else:
                    by_session[key] = {"items": [entry]}
            except Exception:
                continue

    # 展平为 {key: [entries]}，标题提升到组级
    result = {}
    for key, group in by_session.items():
        titles_in = [e.pop("title") for e in group["items"] if e.get("title")]
        result[key] = group["items"]
        if titles_in:
            result[key + "#meta"] = [{"title": titles_in[0]}]
    return result


# ============================================================
# 数据源 3：Git 提交
# ============================================================

def collect_git(start_dt, end_dt, repos_root):
    """遍历 repos_root 下的 git 仓库，按仓库收集提交。"""
    commits_by_project = {}
    if not repos_root.exists():
        log(f"仓库根目录不存在: {repos_root}")
        return commits_by_project

    since = start_dt.strftime("%Y-%m-%d %H:%M:%S")
    until = end_dt.strftime("%Y-%m-%d %H:%M:%S")

    for proj_dir in sorted(repos_root.iterdir()):
        if not proj_dir.is_dir() or not (proj_dir / ".git").exists():
            continue
        try:
            result = subprocess.run(
                ["git", "-C", str(proj_dir),
                 "log", "--since", since, "--until", until,
                 "--pretty=format:%h|%ad|%s",
                 "--date=format:%Y-%m-%d %H:%M"],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0 and result.stdout.strip():
                commits = []
                for line in result.stdout.strip().split("\n"):
                    parts = line.split("|", 2)
                    if len(parts) == 3:
                        commits.append({
                            "hash": parts[0],
                            "date": parts[1],
                            "message": parts[2][:COMMIT_MSG_MAX],
                        })
                if commits:
                    commits_by_project[proj_dir.name] = commits
        except Exception as e:
            log(f"提取 {proj_dir.name} 提交失败: {e}")
            continue
    return commits_by_project


# ============================================================
# 主流程
# ============================================================

def log(msg):
    print(msg, file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="周报数据采集")
    parser.add_argument("--repos", type=Path, default=DEFAULT_REPOS_ROOT,
                        help="Git 仓库根目录（默认 D:/runspace）")
    parser.add_argument("--days", type=int, default=None,
                        help="最近 N 天（自然日窗口）；不指定则用默认周窗口")
    parser.add_argument("-o", "--output-file", type=Path, default=None,
                        help="写入文件（默认输出到 stdout）")
    args = parser.parse_args()

    if args.days:
        start_dt, end_dt = days_range(args.days)
    else:
        start_dt, end_dt = week_range()
    report_date = end_dt.strftime("%Y-%m-%d")

    log(f"周期: {start_dt:%Y-%m-%d %H:%M} — {end_dt:%Y-%m-%d %H:%M}")

    claude = collect_claude(start_dt, end_dt)
    codex = collect_codex(start_dt, end_dt)
    git = collect_git(start_dt, end_dt, args.repos)

    total_claude = sum(len(v) for v in claude.values())
    total_codex = sum(len(v) for v in codex.values())
    total_git = sum(len(v) for v in git.values())
    all_projects = sorted(set(list(claude.keys()) + list(git.keys())))

    log(f"Claude Code 会话: {total_claude} 条 / {len(claude)} 项目")
    log(f"Codex 会话: {total_codex} 条")
    log(f"Git 提交: {total_git} 条 / {len(git)} 项目")

    output = {
        "week_range": {
            "start": start_dt.strftime("%Y-%m-%d %H:%M"),
            "end": end_dt.strftime("%Y-%m-%d %H:%M"),
            "report_date": report_date,
        },
        "stats": {
            "total_claude_sessions": total_claude,
            "total_codex_sessions": total_codex,
            "total_git_commits": total_git,
            "active_projects": all_projects,
        },
        "claude_code_sessions": claude,
        "codex_sessions": codex,
        "git_commits": git,
        "_notes": "hermes_sessions 需 Agent 用 session_search 补充；codex 项目归属需结合内容判断",
    }

    text = json.dumps(output, ensure_ascii=False, indent=2)
    if args.output_file:
        args.output_file.write_text(text, encoding="utf-8")
        log(f"已写入 {args.output_file}")
    else:
        print(text)


if __name__ == "__main__":
    main()
