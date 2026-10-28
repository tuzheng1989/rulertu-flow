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
import glob
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
CODEX_PROJECTS = Path.home() / ".codex" / "sessions"
DEFAULT_REPOS_ROOT = Path("D:/runspace")

CONTENT_MAX_CHARS = 300   # 会话输入截断长度，足够 Agent 理解意图
COMMIT_MSG_MAX = 200

# 工作台型项目：每个会话对应独立一件事，按会话拆分输出（按需增删）
WORKBENCH_PROJECTS = {"evoCenter"}
TITLE_MAX_CHARS = 80       # 工作台会话标题：首条有效输入截断

# --summarize 深度摘要的预算（每会话，字符）
DEEP_HEAD_CHARS = 400     # T1 首条 assistant 复述（天然 recap）
DEEP_TAIL_CHARS = 800     # T1 尾部成果（最终交付陈述）
DEEP_TAIL_COUNT = 3       # 尾部取最后 N 条 assistant 文本，避开"Q1 请定夺"式追问
DEEP_MID_COUNT = 3        # T2 中段里程碑锚点数
DEEP_MID_CHARS = 300      # T2 每条锚点截断
# 成果关键词：中段只采样含里程碑信号的 assistant 块
OUTCOME_KEYWORDS = ("完成", "交付", "通过", "达标", "定稿", "实现", "修复", "验证",
                    "FAIL", "PASS", "全过", "上线", "合入", "迁移", "重构", "发布")

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
    by_project_sessions = {}  # 项目 -> {sessionId: 会话内输入条数}

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
                pname = Path(proj).name
                entry = {
                    "date": dt.strftime("%Y-%m-%d"),
                    "time": dt.strftime("%H:%M"),
                    "content": display[:CONTENT_MAX_CHARS],
                }
                sid = data.get("sessionId")
                if pname in WORKBENCH_PROJECTS and sid:
                    # 工作台项目：每会话一件事，按会话拆分，保留会话边界
                    by_project.setdefault(pname, {}).setdefault(sid, []).append(entry)
                else:
                    by_project.setdefault(pname, []).append(entry)
                if sid:
                    by_project_sessions.setdefault(pname, {}).setdefault(sid, 0)
                    by_project_sessions[pname][sid] += 1
            except Exception:
                continue
    return by_project, by_project_sessions


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
    full_sids = set()

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
                if sid:
                    full_sids.add(sid)
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
    return result, full_sids


# ============================================================
# 深度摘要：从会话全量文件抽取 recap + 结尾成果 + 中段锚点
# ============================================================

def _first_longest(texts, n, min_len=100):
    """尾部取法：最后 n 条里选最长的一条作为成果陈述。

    会话结尾不一定是成果（可能是"Q1 请定夺"式追问），
    尾部若干条中最长的通常就是交付摘要。
    """
    tail = [t for t in texts[-n:] if t.strip()]
    if not tail:
        return None
    best = max(tail, key=len)
    return best if len(best) >= min_len else tail[-1]


def _pick_midstones(texts, count):
    """中段采样：优先含成果关键词的 assistant 块，不足则等距补齐。"""
    candidates = []
    for i, t in enumerate(texts):
        if any(k in t for k in OUTCOME_KEYWORDS):
            candidates.append((i, t))
    if len(candidates) > count:
        # 关键词命中过多时等距抽 count 条，避免全挤在前半段
        step = len(candidates) / count
        candidates = [candidates[int(i * step)] for i in range(count)]
    picked = {i: t[:DEEP_MID_CHARS] for i, t in candidates[:count]}
    # 等距补齐到 count 条
    if len(picked) < count and texts:
        rest = [(i, t) for i, t in enumerate(texts) if i not in picked]
        need = count - len(picked)
        if rest:
            step = len(rest) / need
            for j in range(need):
                i, t = rest[int(j * step)]
                picked[i] = t[:DEEP_MID_CHARS]
    return [picked[i] for i in sorted(picked)]


def _make_summary(head, tail, midstones, extra=None):
    """组装深度摘要对象。head/tail/midstones 均为纯文本或 None。"""
    out = {}
    if head:
        out["recap"] = head[:DEEP_HEAD_CHARS]   # 会话开头的任务复述（天然 recap）
    if midstones:
        out["milestones"] = midstones           # 中段里程碑锚点
    if tail:
        out["outcome"] = tail[:DEEP_TAIL_CHARS] # 会话结尾的最终成果陈述
    if extra:
        out.update(extra)
    return out


def summarize_claude_session(session_id):
    """读 ~/.claude/projects/*/<sessionId>.jsonl，抽取 assistant 纯文本块。

    只提取 type:"text" 块——工具调用 JSON、附件、api-request 等体积大头
    全部天然排除，这是控制上下文规模的关键。
    """
    pattern = str(Path.home() / ".claude" / "projects" / "*" / f"{session_id}.jsonl")
    matches = glob.glob(pattern)
    if not matches:
        return None
    texts = []
    try:
        with open(matches[0], encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("type") != "assistant":
                    continue
                content = d.get("message", {}).get("content", [])
                if isinstance(content, list):
                    for blk in content:
                        if isinstance(blk, dict) and blk.get("type") == "text":
                            t = (blk.get("text") or "").strip()
                            if t:
                                texts.append(t)
    except Exception as e:
        log(f"读取 Claude 会话 {session_id[:8]} 失败: {e}")
        return None
    if not texts:
        return None
    return _make_summary(texts[0], _first_longest(texts, DEEP_TAIL_COUNT),
                         _pick_midstones(texts, DEEP_MID_COUNT))


def summarize_codex_session(session_id):
    """读 ~/.codex/sessions/**/rollout-*.jsonl（文件名含 session_id）。

    同一 session 的 rollout 文件可能跨多天存在（会话恢复），全部合并处理。
    顺带汇总 token_usage_record 作为工作量指标。
    """
    pattern = str(CODEX_PROJECTS / "**" / f"rollout-*{session_id}*.jsonl")
    matches = sorted(glob.glob(pattern, recursive=True))
    if not matches:
        return None
    texts, total_tokens, turn_count = [], 0, 0
    for path in matches:
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    try:
                        d = json.loads(line)
                    except Exception:
                        continue
                    p = d.get("payload", {})
                    ptype = p.get("type")
                    if d.get("type") == "event_msg" and ptype == "agent_message":
                        t = (p.get("message") or "").strip()
                        if t:
                            texts.append(t)
                    elif (d.get("type") == "response_item" and ptype == "message"
                          and p.get("role") == "assistant"):
                        # 部分版本 rollout 不写 event_msg/agent_message，正文在此
                        for c in p.get("content", []):
                            if isinstance(c, dict) and c.get("text"):
                                t = (c["text"] or "").strip()
                                if t:
                                    texts.append(t)
                    elif d.get("type") == "token_usage_record":
                        usage = p.get("usage") or {}
                        total_tokens += (usage.get("input_tokens", 0)
                                         + usage.get("output_tokens", 0))
                        turn_count += 1
        except Exception as e:
            log(f"读取 Codex 会话 {session_id[:8]} 失败: {e}")
            continue
    if not texts:
        return None
    extra = {"total_tokens": total_tokens, "turns": turn_count} if turn_count else None
    return _make_summary(texts[0], _first_longest(texts, DEEP_TAIL_COUNT),
                         _pick_midstones(texts, DEEP_MID_COUNT), extra)


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


def attach_deep_summaries(claude, claude_sessions, codex, codex_full_sids):
    """--summarize 模式：按 sessionId join 到全量会话文件，挂载深度摘要。

    未匹配到全量文件的会话保持现状（轻量层），不报错。
    """
    for pname, sids in claude_sessions.items():
        proj = claude.get(pname)
        if isinstance(proj, dict) and "items" in proj:
            # 已是摘要结构，摘要补充进 session_summaries
            summaries = proj.setdefault("session_summaries", {})
            for sid in sids:
                if sid[:8] not in summaries:
                    s = summarize_claude_session(sid)
                    if s:
                        summaries[sid[:8]] = s
            continue
        summaries = {}
        for sid in sids:
            s = summarize_claude_session(sid)
            if s:
                summaries[sid[:8]] = s
        if summaries:
            if isinstance(proj, list):
                # 普通项目：条目列表 + 摘要
                claude[pname] = {"items": proj, "session_summaries": summaries}
            elif isinstance(proj, dict):
                # 工作台项目：{完整sid: [entries]} 摘要挂进对应会话组（键长不同，前缀匹配）
                for sid in sids:
                    s = summaries.get(sid[:8])
                    if s and sid in proj:
                        proj[sid] = {"items": proj[sid], "summary": s}
            elif proj is None:
                claude[pname] = {"items": [], "session_summaries": summaries}

    # Codex：摘要挂到会话组级
    for sid in codex_full_sids:
        key = sid[:8]
        if key not in codex:
            continue
        s = summarize_codex_session(sid)
        if s:
            codex[key] = {"items": codex[key], "summary": s}


def main():
    parser = argparse.ArgumentParser(description="周报数据采集")
    parser.add_argument("--repos", type=Path, default=DEFAULT_REPOS_ROOT,
                        help="Git 仓库根目录（默认 D:/runspace）")
    parser.add_argument("--days", type=int, default=None,
                        help="最近 N 天（自然日窗口）；不指定则用默认周窗口")
    parser.add_argument("--summarize", action="store_true",
                        help="深度摘要：按 sessionId 关联全量会话文件，抽取 recap/成果/里程碑（默认关闭）")
    parser.add_argument("-o", "--output-file", type=Path, default=None,
                        help="写入文件（默认输出到 stdout）")
    args = parser.parse_args()

    if args.days:
        start_dt, end_dt = days_range(args.days)
    else:
        start_dt, end_dt = week_range()
    report_date = end_dt.strftime("%Y-%m-%d")

    log(f"周期: {start_dt:%Y-%m-%d %H:%M} — {end_dt:%Y-%m-%d %H:%M}")

    claude, claude_sessions = collect_claude(start_dt, end_dt)
    codex, codex_full_sids = collect_codex(start_dt, end_dt)
    git = collect_git(start_dt, end_dt, args.repos)

    if args.summarize:
        attach_deep_summaries(claude, claude_sessions, codex, codex_full_sids)

    # 摘要/工作台模式下组结构变为 dict，统一计条数
    def group_len(v):
        if isinstance(v, dict):
            if "items" in v:
                return len(v["items"])
            # 工作台 {sid: entries 或 {items, summary}}
            return sum(len(x["items"]) if isinstance(x, dict) else len(x)
                       for x in v.values())
        return len(v)

    total_claude = sum(group_len(v) for v in claude.values())
    total_codex = sum(group_len(v) for v in codex.values())
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
