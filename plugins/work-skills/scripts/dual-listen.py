#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dual-listen.py — 跨模型兼听（Codex CLI）共用执行脚本。

brainstorm（diverge）与 inspiration-pacemaker（attack / blindspot）复用本脚本。
确定性机制（预算扣次、排他目录、进程启动、五级失败分类、用量提取、清理）
全部下沉到这里，宿主模型只做判断性工作：触发、撰写快照、读取结果 JSON 并合并。
规格唯一出处：plans/work-skills/2026-10-29-dual-model-listening.md §2.8。

仅依赖 Python 标准库。退出码：0 成功 / 2 输入错误 / 3 进程失败（含 L1-L4 与
预算耗尽）/ 4 解析失败。stdout 恒打印单个结果 JSON。
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

MODES = ("diverge", "attack", "blindspot")
DEFAULT_MODEL = "gpt-6.1-sol"
DEFAULT_EFFORT = "max"

# L2：stderr 含模型名且含以下模式之一 → 模型名不可用
L2_PATTERNS = ("not found", "invalid", "unknown", "no access", "permission")
# L3：stderr 含以下之一 → 强度不支持，回落 high
L3_PATTERNS = ("model_reasoning_effort", "reasoning effort")

# 各模式默认提示词，{in_path} 替换为尝试目录内 in.md 的绝对路径
DEFAULT_PROMPTS = {
    "diverge": (
        "阅读 {in_path}（可能性地图快照）。只输出地图上不存在的新分支：最多 8 条，"
        "每条 ≤40 字，各标注适用的发散透镜（SCAMPER/类比跨界/逆向假设/随机刺激/绿帽）。"
        "只发散，不评估。输出为 markdown 列表。"
    ),
    "attack": (
        "阅读 {in_path}（钻探计划与洞察清单）。攻击这些结论，最多 3 个攻击点，"
        "每个 ≤80 字，指出反例或证据缺口。输出为 markdown 列表。"
    ),
    "blindspot": (
        "阅读 {in_path}。独立下钻此问题，输出最多 5 条你自己的洞察，输出为 markdown 列表。"
    ),
}

TASK_DEFAULTS = {
    "used": 0,
    "disabled": False,
    "thread_id": None,
    "model_effective": None,
    "model_verified": False,
    "usage_log": [],       # 每次尝试的摘要（含清理失败记录）
    "consec_proc_fail": 0, # 连续 L4 进程失败计数（成功清零，达 2 禁用）
}


# ---------------------------------------------------------------- 状态真源（.listen/state.json，原子写）

def state_path(workdir: str) -> str:
    return os.path.join(workdir, ".listen", "state.json")


def load_state(workdir: str) -> dict:
    p = state_path(workdir)
    if not os.path.exists(p):
        return {"tasks": {}}
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {"tasks": {}}
    return data if isinstance(data, dict) and "tasks" in data else {"tasks": {}}


def save_state(workdir: str, state: dict) -> None:
    """原子写：临时文件 + os.replace，避免中断留下半截状态。"""
    d = os.path.dirname(state_path(workdir))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".state-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, state_path(workdir))
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def get_task(state: dict, task_id: str) -> dict:
    tasks = state.setdefault("tasks", {})
    task = tasks.setdefault(task_id, {})
    for key, val in TASK_DEFAULTS.items():
        task.setdefault(key, [] if isinstance(val, list) else val)
    return task


def log_usage(workdir: str, task_id: str, **fields) -> None:
    """向 usage_log 追加一条摘要（自动带时间戳）。"""
    state = load_state(workdir)
    task = get_task(state, task_id)
    entry = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    entry.update(fields)
    task["usage_log"].append(entry)
    save_state(workdir, state)


# ---------------------------------------------------------------- 输入与进程准备

def _resolve_bare_command(name: str):
    """裸命令名（无路径分隔符）的解析策略，对齐 plan-iterate resolve_cli：
    依次找 <name>.exe / <name>.com（原生可执行优先，避免落到 npm .cmd 包装层）；
    都没有则找 <name>.cmd，并检查其同目录的 node_modules/@openai/codex/bin/codex.js，
    存在则以 [node, codex.js] 前缀启动；再不行退回 which(<name>)；全空 → None。"""
    for cand in (name + ".exe", name + ".com"):
        hit = shutil.which(cand)
        if hit:
            return [hit]
    cmd = shutil.which(name + ".cmd")
    if cmd:
        js = os.path.join(os.path.dirname(cmd),
                          "node_modules", "@openai", "codex", "bin", "codex.js")
        if os.path.isfile(js):
            node = shutil.which("node")
            if node:
                return [node, js]
    fallback = shutil.which(name)
    return [fallback] if fallback else None


def resolve_codex(codex_bin: str):
    """L1：启动前解析 codex_bin。支持 "codex" 或 "python x.py" 形式（后者检查 argv[0]）。

    返回 (argv[0]..., argv[1:])；解析失败返回 (None, None)。
    注意路径请用正斜杠（shlex 语义）。
    """
    try:
        parts = shlex.split(codex_bin)
    except ValueError:
        return None, None
    if not parts:
        return None, None
    exe = parts[0]
    if len(parts) == 1 and "/" not in exe and "\\" not in exe and os.sep not in exe:
        # 裸命令名：走原生可执行优先 / .cmd→codex.js 的解析策略
        bare = _resolve_bare_command(exe)
        if bare is None:
            return None, None
        return (bare[0], bare[1:]) if len(bare) > 1 else (bare[0], [])
    resolved = shutil.which(exe)
    if resolved is None and ("/" in exe or os.sep in exe) and os.path.isfile(exe):
        resolved = os.path.abspath(exe)
    if resolved is None:
        return None, None
    return resolved, parts[1:]


def make_attempt_dir(workdir: str, snapshot: str):
    """排他创建 <workdir>/.listen-tmp/<6位随机hex>/，并把快照复制为目录内 in.md。

    已存在（撞 ID）则换 ID 重试，至多 5 次。返回 (目录, in.md 路径) 或 (None, None)。
    """
    tmp_root = os.path.join(workdir, ".listen-tmp")
    os.makedirs(tmp_root, exist_ok=True)
    for _ in range(5):
        dir_id = "".join(random.choice("0123456789abcdef") for _ in range(6))
        attempt_dir = os.path.join(tmp_root, dir_id)
        try:
            os.mkdir(attempt_dir)  # 排他：已存在即抛 FileExistsError
        except FileExistsError:
            continue
        in_md = os.path.join(attempt_dir, "in.md")
        shutil.copyfile(snapshot, in_md)
        return attempt_dir, in_md
    return None, None


def cleanup_dir(attempt_dir: str):
    """进程结束（任何结局）后清理本次尝试目录。失败返回错误摘要（不判失败）。"""
    try:
        shutil.rmtree(attempt_dir)
        return None
    except OSError as exc:
        return f"cleanup_failed: {exc}"


def _kill_process_tree(proc) -> None:
    """超时后强杀整棵进程树：Windows 用 taskkill /F /T，POSIX 用进程组 SIGKILL。"""
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, timeout=15)
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        pass  # 进程可能已自行退出
    try:
        proc.kill()
    except OSError:
        pass


# ---------------------------------------------------------------- 事件流解析（宽松，字段缺失不算失败）

def parse_events(events_path: str) -> list:
    if not os.path.exists(events_path):
        return []
    events = []
    with open(events_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except ValueError:
                continue  # 非事件行，跳过
    return events


def _walk(obj):
    """递归产出嵌套结构里的 (key, value)，供宽松字段提取。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k, v
            yield from _walk(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk(item)


def extract_thread_id(events: list):
    for ev in events:
        if isinstance(ev, dict) and ev.get("type") == "thread.started" and ev.get("thread_id"):
            return ev["thread_id"]
    for ev in events:  # 宽松回退：任意事件里的 thread_id 字段
        for k, v in _walk(ev):
            if k == "thread_id" and isinstance(v, str) and v:
                return v
    return None


def extract_model_effort(events: list):
    """宽松提取实际模型/强度；事件流没给就返回 (None, None)，调用方标注"未验证"。"""
    model = effort = None
    for ev in events:
        for k, v in _walk(ev):
            if model is None and k == "model" and isinstance(v, str) and v:
                model = v
            if effort is None and k in ("model_reasoning_effort", "reasoning_effort", "effort") \
                    and isinstance(v, str) and v:
                effort = v
    return model, effort


def extract_usage(events: list):
    """含 token/usage 字样的事件，数值字段可得则记；不可得返回 None（"不可验证"）。"""
    usage = {}
    for ev in events:
        for k, v in _walk(ev):
            kl = str(k).lower()
            if "token" in kl and isinstance(v, (int, float)) and not isinstance(v, bool):
                usage[str(k)] = v
    return usage or None


def read_list_output(out_path: str):
    """读取并校验输出：文件存在、非空、含 ≥1 行以 "- " 开头的列表项；否则返回 None。"""
    if not os.path.exists(out_path):
        return None
    try:
        with open(out_path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return None
    if not text.strip():
        return None
    if not any(line.lstrip().startswith("- ") for line in text.splitlines()):
        return None
    return text


# ---------------------------------------------------------------- 结果 JSON

def build_result(ok, failure, output_path, model_effective, model_verified,
                 usage, budget_remaining, disabled) -> dict:
    return {
        "ok": ok,
        "output_path": output_path,
        "failure": failure,
        "model_effective": model_effective,
        "model_verified": model_verified,
        "usage": usage,
        "budget_remaining": budget_remaining,
        "disabled": disabled,
    }


def emit(result: dict, code: int) -> int:
    sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    return code


# ---------------------------------------------------------------- 主流程

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="跨模型兼听（Codex CLI）执行脚本")
    parser.add_argument("--mode", required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--task-id", required=True, dest="task_id")
    parser.add_argument("--budget-limit", required=True, type=int, dest="budget_limit")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--effort", default=DEFAULT_EFFORT, choices=["max", "high"])
    parser.add_argument("--prompt-file", dest="prompt_file", default=None)
    parser.add_argument("--codex-bin", dest="codex_bin", default="codex")
    parser.add_argument("--proc-timeout", dest="proc_timeout", type=float, default=120.0,
                        help="单次进程硬超时（秒，浮点）；超时后强杀整棵进程树")
    args = parser.parse_args(argv)

    def early_exit(code, failure, workdir=None):
        """启动前的失败：不扣次，输出契约字段默认值。"""
        used, disabled = 0, False
        if workdir is not None:
            task = get_task(load_state(workdir), args.task_id)
            used, disabled = task["used"], task["disabled"]
        return emit(build_result(
            False, failure, None, args.model, False, None,
            args.budget_limit - used, disabled), code)

    # 1. 输入检查
    if args.mode not in MODES:
        return early_exit(2, "invalid_mode")
    if not os.path.isfile(args.snapshot):
        return early_exit(2, "snapshot_not_found")
    if args.prompt_file is not None and not os.path.isfile(args.prompt_file):
        return early_exit(2, "prompt_file_not_found")

    workdir = os.path.abspath(args.workdir)
    os.makedirs(workdir, exist_ok=True)

    # 状态初始化落盘（首次调用建立该 task 的条目）
    state = load_state(workdir)
    task = get_task(state, args.task_id)
    save_state(workdir, state)

    # L1：CLI 不可用 → 不启动、不扣次、禁用
    resolved = resolve_codex(args.codex_bin)
    if resolved[0] is None:
        state = load_state(workdir)
        task = get_task(state, args.task_id)
        task["disabled"] = True
        save_state(workdir, state)
        log_usage(workdir, args.task_id, outcome="l1_cli_unavailable")
        return emit(build_result(
            False, "cli_unavailable", None, args.model, False, None,
            args.budget_limit - task["used"], True), 3)

    # 入口检查：已禁用 / 预算耗尽 → 不启动，退出 3
    if task["disabled"]:
        return early_exit(3, "disabled", workdir)
    if task["used"] >= args.budget_limit:
        return early_exit(3, "budget_exhausted", workdir)

    # 3. 会话策略：diverge/blindspot 恒 fresh；attack 有 thread_id 则 resume（提示词为 delta）
    resume_thread = task["thread_id"] if args.mode == "attack" else None
    if resume_thread and args.prompt_file is None:
        # resume 的提示词必须由调用方给 delta（--prompt-file），缺失属输入错误
        return early_exit(2, "resume_requires_prompt_file", workdir)
    if args.prompt_file is not None:
        with open(args.prompt_file, encoding="utf-8") as f:
            prompt_text = f.read()
    else:
        prompt_text = DEFAULT_PROMPTS[args.mode]

    codex_prefix = [resolved[0], *resolved[1]]
    outputs_dir = os.path.join(workdir, ".listen", "outputs")

    def reserve():
        """每次实际启动前预留扣次：先查余额并落盘，才启动；中断不返还。"""
        st = load_state(workdir)
        t = get_task(st, args.task_id)
        if t["disabled"]:
            return "disabled"
        if t["used"] >= args.budget_limit:
            return "budget_exhausted"
        t["used"] += 1
        save_state(workdir, st)
        return None

    def do_attempt(prompt_src: str, effort: str, resume_thread_id=None) -> dict:
        """单次尝试：预留 → 建排他目录 → 启动进程 → 读结果 → 清理 → 失败分类。

        返回 {"kind": ok/l2/l3/l4/l5/resume_failed/no_budget/disabled/attempt_dir_failed, ...}。
        """
        err = reserve()
        if err:
            return {"kind": err}
        attempt_dir, in_md = make_attempt_dir(workdir, args.snapshot)
        if attempt_dir is None:
            log_usage(workdir, args.task_id, outcome="attempt_dir_failed")
            return {"kind": "attempt_dir_failed"}
        out_path = os.path.join(attempt_dir, "out.md")
        events_path = os.path.join(attempt_dir, "events.jsonl")
        # 提示词引用尝试目录内 in.md 的绝对路径（保证引用文件随目录一起清理）
        prompt = prompt_src.replace("{in_path}", os.path.abspath(in_md))

        if resume_thread_id is not None:
            cmd = [*codex_prefix, "exec", "resume", resume_thread_id,
                   "--json", "-o", out_path, prompt]
        else:
            cmd = [*codex_prefix, "exec", "--json", "--skip-git-repo-check",
                   "-s", "read-only", "-C", workdir, "-m", args.model,
                   "-c", 'model_reasoning_effort="%s"' % effort,
                   "-o", out_path, prompt]

        timed_out = False
        rc = None
        stderr_path = os.path.join(attempt_dir, "stderr.log")
        try:
            # stdin 隔离为 DEVNULL：codex 检测到 stdin 未闭合会阻塞等待输入（挂死）。
            # stdout/stderr 都落尝试目录内的文件：不用 PIPE，杜绝孙进程扣住
            # 管道句柄导致 Windows 上 communicate() 无限阻塞、超时形同虚设。
            with open(events_path, "w", encoding="utf-8") as ef, \
                    open(stderr_path, "w", encoding="utf-8") as sf:
                proc = subprocess.Popen(
                    cmd, stdin=subprocess.DEVNULL, stdout=ef, stderr=sf,
                    cwd=workdir, start_new_session=(os.name == "posix"))
                try:
                    rc = proc.wait(timeout=args.proc_timeout)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    _kill_process_tree(proc)
                    rc = proc.wait(timeout=30)
        except OSError:
            rc = None  # 进程未能创建，按 L4 处理
        with open(stderr_path, encoding="utf-8", errors="replace") as sf:
            stderr = sf.read()

        # 进程结束：先读事件流与输出内容（目录清理前），再清理
        events = parse_events(events_path)
        out_text = read_list_output(out_path) if (rc == 0 and not timed_out) else None
        cleanup_err = cleanup_dir(attempt_dir)
        if cleanup_err:
            log_usage(workdir, args.task_id, outcome="cleanup", detail=cleanup_err)

        # 失败分类（互斥，按优先级）
        if timed_out or rc != 0:
            if resume_thread_id is not None:
                kind = "resume_failed"  # 交由调用方降级 fresh，不计入 L4 连败
            elif _is_l2(stderr):
                kind = "l2"
            elif _is_l3(stderr):
                kind = "l3"
            else:
                kind = "l4"
        elif out_text is None:
            kind = "l5"
        else:
            kind = "ok"
        return {"kind": kind, "rc": rc, "stderr": stderr, "events": events,
                "out_text": out_text, "cleanup_err": cleanup_err, "timed_out": timed_out}

    def _is_l2(stderr: str) -> bool:
        low = stderr.lower()
        return bool(args.model and args.model.lower() in low
                    and any(p in low for p in L2_PATTERNS))

    def _is_l3(stderr: str) -> bool:
        low = stderr.lower()
        return any(p in low for p in L3_PATTERNS)

    def set_disabled(failure: str):
        state = load_state(workdir)
        t = get_task(state, args.task_id)
        t["disabled"] = True
        log_usage(workdir, args.task_id, outcome="disabled", failure=failure)
        save_state(workdir, state)

    def note_l4() -> bool:
        """计入一次 L4 进程失败；连续 2 次则禁用。返回禁用后的状态。"""
        state = load_state(workdir)
        t = get_task(state, args.task_id)
        t["consec_proc_fail"] = t.get("consec_proc_fail", 0) + 1
        if t["consec_proc_fail"] >= 2:
            t["disabled"] = True
        save_state(workdir, state)
        return t["disabled"]

    def finish_ok(oc: dict, failure=None) -> int:
        """成功路径：提取事件流字段、转移输出、state 落盘、退出 0。"""
        thread_id = extract_thread_id(oc["events"])
        ev_model, _ev_effort = extract_model_effort(oc["events"])
        usage = extract_usage(oc["events"])
        model_effective = ev_model or args.model
        model_verified = ev_model is not None

        # 尝试目录已被清理，把输出转移到 .listen/outputs/ 使 output_path 长期可读
        output_path = None
        try:
            os.makedirs(outputs_dir, exist_ok=True)
            safe_task = re.sub(r"[^0-9A-Za-z_-]+", "_", args.task_id) or "task"
            name = "%s_%s_%s.md" % (
                datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"), safe_task, args.mode)
            dest = os.path.join(outputs_dir, name)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(oc["out_text"])
            output_path = dest
        except OSError:
            output_path = None  # 转移失败不判失败，仅 output_path 为 null

        state = load_state(workdir)
        t = get_task(state, args.task_id)
        t["thread_id"] = thread_id
        t["model_effective"] = model_effective
        t["model_verified"] = model_verified
        t["consec_proc_fail"] = 0
        t["usage_log"].append({
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "outcome": "ok",
            "failure": failure,
            "usage": usage,
            "cleanup": oc["cleanup_err"] or "ok",
            "output_path": output_path,
        })
        save_state(workdir, state)
        return emit(build_result(True, failure, output_path, model_effective,
                                 model_verified, usage,
                                 args.budget_limit - t["used"], t["disabled"]), 0)

    # ---- 尝试编排 ----
    oc = do_attempt(prompt_text, args.effort, resume_thread)
    kind = oc["kind"]

    if kind == "ok":
        return finish_ok(oc)
    if kind == "l5":
        return emit(build_result(
            False, "parse_failed", None, args.model, False, None,
            args.budget_limit - get_task(load_state(workdir), args.task_id)["used"],
            get_task(load_state(workdir), args.task_id)["disabled"]), 4)
    if kind in ("no_budget", "disabled", "attempt_dir_failed"):
        return emit(build_result(
            False, kind, None, args.model, False, None,
            args.budget_limit - get_task(load_state(workdir), args.task_id)["used"], True), 3)

    if kind == "resume_failed":
        # resume 调用非零退出 → 降级：清 thread_id，按 fresh 重来一次（正常预留，不计 L4 连败）
        state = load_state(workdir)
        t = get_task(state, args.task_id)
        t["thread_id"] = None
        save_state(workdir, state)
        log_usage(workdir, args.task_id, outcome="resume_failed", detail="fallback_to_fresh")
        oc = do_attempt(prompt_text, args.effort, None)  # 单次 fresh，不再级联重试
        if oc["kind"] == "ok":
            return finish_ok(oc, failure="resume_failed_fallback_fresh")
        if oc["kind"] == "l5":
            return emit(build_result(
                False, "parse_failed", None, args.model, False, None,
                args.budget_limit - get_task(load_state(workdir), args.task_id)["used"], False), 4)
        # fresh 回落仍失败 → 禁用退出 3
        set_disabled("fallback_" + oc["kind"])
        return emit(build_result(
            False, "resume_fallback_failed", None, args.model, False, None,
            args.budget_limit - get_task(load_state(workdir), args.task_id)["used"], True), 3)

    if kind == "l2":
        # 模型名不可用：不重试、禁用
        set_disabled("l2_model_unavailable")
        return emit(build_result(
            False, "model_unavailable", None, args.model, False, None,
            args.budget_limit - get_task(load_state(workdir), args.task_id)["used"], True), 3)

    if kind == "l3":
        # 强度不支持：回落 high 重试一次（重试前再走预留流程）
        oc2 = do_attempt(prompt_text, "high", None)
        if oc2["kind"] == "ok":
            return finish_ok(oc2)
        if oc2["kind"] == "l5":
            return emit(build_result(
                False, "parse_failed", None, args.model, False, None,
                args.budget_limit - get_task(load_state(workdir), args.task_id)["used"], False), 4)
        set_disabled("l3_effort_unsupported")
        return emit(build_result(
            False, "effort_unsupported", None, args.model, False, None,
            args.budget_limit - get_task(load_state(workdir), args.task_id)["used"], True), 3)

    # L4：进程失败（超时或其他非零退出）→ 计连败；未达 2 次且余额允许则重试一次
    if note_l4():
        return emit(build_result(
            False, "process_failed", None, args.model, False, None,
            args.budget_limit - get_task(load_state(workdir), args.task_id)["used"], True), 3)
    oc2 = do_attempt(prompt_text, args.effort, None)
    kind2 = oc2["kind"]
    if kind2 == "ok":
        return finish_ok(oc2)
    if kind2 == "l5":
        return emit(build_result(
            False, "parse_failed", None, args.model, False, None,
            args.budget_limit - get_task(load_state(workdir), args.task_id)["used"], False), 4)
    if kind2 in ("no_budget", "disabled", "attempt_dir_failed"):
        return emit(build_result(
            False, "process_failed" if kind2 == "attempt_dir_failed" else kind2,
            None, args.model, False, None,
            args.budget_limit - get_task(load_state(workdir), args.task_id)["used"],
            kind2 == "disabled"), 3)
    if kind2 == "l2":
        set_disabled("l2_model_unavailable")
        return emit(build_result(
            False, "model_unavailable", None, args.model, False, None,
            args.budget_limit - get_task(load_state(workdir), args.task_id)["used"], True), 3)
    if kind2 == "l3":
        set_disabled("l3_effort_unsupported")
        return emit(build_result(
            False, "effort_unsupported", None, args.model, False, None,
            args.budget_limit - get_task(load_state(workdir), args.task_id)["used"], True), 3)
    # 重试仍是 L4：连续第 2 次 → 禁用
    note_l4()
    return emit(build_result(
        False, "process_failed", None, args.model, False, None,
        args.budget_limit - get_task(load_state(workdir), args.task_id)["used"], True), 3)


if __name__ == "__main__":
    sys.exit(main())
