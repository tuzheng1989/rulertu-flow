# -*- coding: utf-8 -*-
"""dual-listen.py 单元测试。

全部经由 CLI 子进程观察（subprocess.run 跑 dual-listen.py），或直接读
state.json / 磁盘工件，不 mock 脚本内部函数。外部 codex 用 tmp_path 下
动态生成的假 codex 脚本替换（--codex-bin "python <fake路径>"），行为由
FAKE_MODE 等环境变量驱动（经 dual-listen 的子进程环境继承）。
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "plugins" / "work-skills" / "scripts" / "dual-listen.py"

# 假 codex：记录 argv 与 .listen-tmp 快照到 FAKE_LOG，再按 FAKE_MODE 演出各种行为
FAKE_CODEX_SRC = '''# -*- coding: utf-8 -*-
import json, os, subprocess, sys, time

argv = sys.argv
log_entry = {
    "argv": argv,
    "prompt": argv[-1],
    "listen_tmp": sorted(os.listdir(os.path.join(os.environ["FAKE_WORKDIR"], ".listen-tmp"))),
}
with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as f:
    f.write(json.dumps(log_entry, ensure_ascii=False) + "\\n")

mode = os.environ.get("FAKE_MODE", "ok")
out = argv[argv.index("-o") + 1]


def emit_ok():
    with open(out, "w", encoding="utf-8") as f:
        f.write("- 兼听分支一：换一种资源约束重述问题\\n- 兼听分支二：把时间维度反转\\n")
    ev = {"type": "thread.started", "thread_id": os.environ.get("FAKE_THREAD_ID", "th-default")}
    if "-m" in argv:
        ev["model"] = argv[argv.index("-m") + 1]
    for a in argv:
        if a.startswith("model_reasoning_effort="):
            ev["model_reasoning_effort"] = a.split("=", 1)[1].strip('"')
    print(json.dumps(ev))
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 120, "output_tokens": 48}}))


if mode == "crash":
    sys.stdout.flush()
    os._exit(1)  # 硬崩：不写输出、退出码 1
if mode == "crash_once":
    flag = os.environ["FAKE_CRASH_FLAG"]
    if os.path.exists(flag):
        os.remove(flag)
        os._exit(1)
    emit_ok()
elif mode == "hang":
    # 模拟真实 codex 挂死：再孵化一个孙进程持有 stdout/stderr 句柄后一起长眠，
    # 用于复现"只 kill 直接子进程、PIPE 句柄被孙进程扣住导致超时失效"的场景
    subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])
    time.sleep(float(os.environ.get("FAKE_HANG_SECONDS", "300")))
elif mode == "read_stdin":
    data = sys.stdin.read()  # stdin=DEVNULL 时立即 EOF 返回 ""；否则阻塞等待
    if data == "":
        emit_ok()
    else:
        sys.exit(3)
elif mode == "silent_ok":
    with open(out, "w", encoding="utf-8") as f:
        f.write("- 只有输出文件，事件流里没有 thread/model/usage 字段\\n")
elif mode == "model_not_found":
    m = argv[argv.index("-m") + 1] if "-m" in argv else "gpt-6.1-sol"
    print("ERROR: model %s not found" % m, file=sys.stderr)
    sys.exit(1)
elif mode in ("effort_unsupported", "effort_always"):
    if mode == "effort_unsupported" and 'model_reasoning_effort="high"' in argv:
        emit_ok()
    else:
        print("error: unknown config key model_reasoning_effort", file=sys.stderr)
        sys.exit(1)
elif mode == "resume_fail":
    if "resume" in argv:
        print("ERROR: resume failed: thread not found", file=sys.stderr)
        sys.exit(1)
    emit_ok()
elif mode == "no_output":
    sys.exit(0)  # 退出 0 但不写输出文件
elif mode == "bad_output":
    with open(out, "w", encoding="utf-8") as f:
        f.write("这不是列表输出，没有以 - 开头的行。")
    sys.exit(0)
else:
    emit_ok()
'''


@pytest.fixture()
def env(tmp_path):
    """每个测试一套独立的快照 / workdir / 假 codex / 日志。"""
    snapshot = tmp_path / "snapshot.md"
    snapshot.write_text("# 快照\n- 已有分支 A\n", encoding="utf-8")
    workdir = tmp_path / "work"
    workdir.mkdir()
    fake = tmp_path / "fake_codex.py"
    fake.write_text(FAKE_CODEX_SRC, encoding="utf-8")
    return {
        "tmp": tmp_path,
        "snapshot": snapshot,
        "workdir": workdir,
        "fake": fake,
        "log": tmp_path / "fake_log.jsonl",
    }


def run_listen(env, mode="diverge", task="t1", budget=3, extra=(), fake_env=None,
               codex_bin=None, stdin_pipe=False, proc_timeout=None):
    """跑 dual-listen.py，返回 CompletedProcess。假 codex 行为经环境变量注入。"""
    if proc_timeout is not None:
        extra = ["--proc-timeout", str(proc_timeout), *extra]
    cmd = [
        sys.executable, str(SCRIPT),
        "--mode", mode,
        "--snapshot", str(env["snapshot"]),
        "--workdir", str(env["workdir"]),
        "--task-id", task,
        "--budget-limit", str(budget),
        "--codex-bin", codex_bin if codex_bin is not None else "python " + env["fake"].as_posix(),
        *extra,
    ]
    e = {**os.environ, "FAKE_LOG": str(env["log"]), "FAKE_WORKDIR": str(env["workdir"])}
    e.update(fake_env or {})
    # stdin_pipe=True：给 dual-listen 一个永不关闭的管道作 stdin，
    # 用于验证脚本给 codex 传 stdin=DEVNULL（若未隔离，子进程会阻塞读输入）
    return subprocess.run(cmd, capture_output=True, text=True, env=e,
                          stdin=subprocess.PIPE if stdin_pipe else None)


def result_of(proc):
    """断言 stdout 是单个 JSON 并解析返回。"""
    return json.loads(proc.stdout)


def read_state(env, task="t1"):
    return json.loads((env["workdir"] / ".listen" / "state.json").read_text(encoding="utf-8"))["tasks"][task]


def read_fake_log(env):
    text = env["log"].read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def assert_no_tmp_residue(env):
    """断言 .listen-tmp 无本次残留（目录可能从未创建）。"""
    tmp_root = env["workdir"] / ".listen-tmp"
    assert not tmp_root.exists() or os.listdir(tmp_root) == []


def write_state(env, task, fields):
    """测试直接预置 state.json（磁盘状态是公开契约）。"""
    p = env["workdir"] / ".listen" / "state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    state = {"tasks": {task: {
        "used": 0, "disabled": False, "thread_id": None, "model_effective": None,
        "model_verified": False, "usage_log": [],
    }}}
    if p.exists():
        state = json.loads(p.read_text(encoding="utf-8"))
    state["tasks"].setdefault(task, {}).update(fields)
    p.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------- 切片 1：正常路径 / 输入校验 / 预算 / 事件字段


def test_ok_path_contract(env):
    """正常路径：退出 0，结果 JSON 契约字段齐全，state 与磁盘工件落盘，tmp 目录清理。"""
    p = run_listen(env, mode="diverge", budget=3, fake_env={"FAKE_THREAD_ID": "th-ok-1"})
    assert p.returncode == 0, p.stderr
    r = result_of(p)
    assert r["ok"] is True
    assert r["failure"] is None
    assert r["model_effective"] == "gpt-6.1-sol"
    assert r["model_verified"] is True
    assert r["usage"] == {"input_tokens": 120, "output_tokens": 48}
    assert r["budget_remaining"] == 2
    assert r["disabled"] is False
    # 输出被转移到 .listen/outputs/（尝试目录已清理，output_path 仍可读）
    out_path = Path(r["output_path"])
    assert out_path.exists()
    assert ".listen-tmp" not in str(out_path)
    assert out_path.read_text(encoding="utf-8").startswith("- ")
    # state：扣次、thread_id、模型验证结果、用量日志
    t = read_state(env)
    assert t["used"] == 1
    assert t["thread_id"] == "th-ok-1"
    assert t["model_effective"] == "gpt-6.1-sol"
    assert t["model_verified"] is True
    assert len(t["usage_log"]) == 1 and t["usage_log"][0]["outcome"] == "ok"
    # 清理：.listen-tmp 下无本次残留
    assert_no_tmp_residue(env)


def test_invalid_inputs_exit_2(env):
    """输入检查：mode 非法 / 快照不存在 → 退出码 2，不扣次。"""
    p1 = run_listen(env, mode="nonsense")
    assert p1.returncode == 2
    assert result_of(p1)["ok"] is False
    p2 = subprocess.run(
        [sys.executable, str(SCRIPT), "--mode", "diverge",
         "--snapshot", str(env["tmp"] / "missing.md"),
         "--workdir", str(env["workdir"]), "--task-id", "t1",
         "--budget-limit", "3", "--codex-bin", "python " + env["fake"].as_posix()],
        capture_output=True, text=True,
        env={**os.environ, "FAKE_LOG": str(env["log"]), "FAKE_WORKDIR": str(env["workdir"])},
    )
    assert p2.returncode == 2
    assert result_of(p2)["ok"] is False
    # 两次都未产生扣次（未走到状态初始化则 state.json 不存在）
    sp = env["workdir"] / ".listen" / "state.json"
    assert not sp.exists() or read_state(env)["used"] == 0


def test_budget_exhausted(env):
    """预算耗尽：limit=1 第一次成功后，第二次不启动、退出 3、used 不变。"""
    p1 = run_listen(env, budget=1)
    assert p1.returncode == 0
    p2 = run_listen(env, budget=1)
    assert p2.returncode == 3
    r = result_of(p2)
    assert r["ok"] is False
    assert r["failure"] == "budget_exhausted"
    assert r["budget_remaining"] == 0
    assert r["disabled"] is False
    assert read_state(env)["used"] == 1
    # 第二次没有再启动进程
    assert len(read_fake_log(env)) == 1
    assert_no_tmp_residue(env)


def test_event_fields_missing(env):
    """事件流无 thread/model/usage 字段：不判失败，如实标注未验证。"""
    p = run_listen(env, fake_env={"FAKE_MODE": "silent_ok"})
    assert p.returncode == 0, p.stderr
    r = result_of(p)
    assert r["ok"] is True
    assert r["model_effective"] == "gpt-6.1-sol"  # 回落请求值
    assert r["model_verified"] is False
    assert r["usage"] is None
    t = read_state(env)
    assert t["thread_id"] is None
    assert t["model_verified"] is False
    assert t["usage_log"][0]["usage"] is None


# ---------------------------------------------------------------- 切片 2：失败分类 / 预留不返还 / 目录排他与清理


def test_l1_cli_unavailable(env):
    """L1：codex_bin 的 argv[0] 无法解析 → 不启动、不扣次、disabled=true、退出 3。"""
    p = run_listen(env, extra=["--codex-bin", "no-such-codex-binary-xyz"])
    assert p.returncode == 3
    r = result_of(p)
    assert r["ok"] is False
    assert r["failure"] == "cli_unavailable"
    assert r["disabled"] is True
    t = read_state(env)
    assert t["used"] == 0
    assert t["disabled"] is True
    assert not env["log"].exists()  # 进程从未启动
    assert_no_tmp_residue(env)


def test_l2_model_unavailable_no_retry(env):
    """L2：stderr 含模型名+not found → 不重试、禁用、退出 3，只扣 1 次。"""
    p = run_listen(env, fake_env={"FAKE_MODE": "model_not_found"})
    assert p.returncode == 3
    r = result_of(p)
    assert r["failure"] == "model_unavailable"
    assert r["disabled"] is True
    t = read_state(env)
    assert t["used"] == 1  # 只扣一次：未重试
    assert t["disabled"] is True
    assert len(read_fake_log(env)) == 1
    assert_no_tmp_residue(env)


def test_l3_effort_fallback_to_high(env):
    """L3：max 不支持 → 回落 high 重试一次成功；argv 先 max 后 high，各扣一次。"""
    p = run_listen(env, fake_env={"FAKE_MODE": "effort_unsupported", "FAKE_THREAD_ID": "th-l3"})
    assert p.returncode == 0, p.stderr
    r = result_of(p)
    assert r["ok"] is True
    assert r["budget_remaining"] == 1  # 3 - 2：回落重试也扣次
    entries = read_fake_log(env)
    assert len(entries) == 2
    assert 'model_reasoning_effort="max"' in entries[0]["argv"]
    assert 'model_reasoning_effort="high"' in entries[1]["argv"]
    assert read_state(env)["used"] == 2


def test_l3_fallback_still_fails(env):
    """L3：回落 high 仍失败 → 禁用、退出 3，共扣 2 次。"""
    p = run_listen(env, fake_env={"FAKE_MODE": "effort_always"})
    assert p.returncode == 3
    r = result_of(p)
    assert r["failure"] == "effort_unsupported"
    assert r["disabled"] is True
    assert read_state(env)["used"] == 2


def test_l4_charge_not_refunded_and_disabled(env):
    """L4：硬崩（os._exit(1)）→ 重试一次再崩 → 连续 2 次禁用；扣次不返还。"""
    p = run_listen(env, fake_env={"FAKE_MODE": "crash"})
    assert p.returncode == 3
    r = result_of(p)
    assert r["failure"] == "process_failed"
    assert r["disabled"] is True
    t = read_state(env)
    assert t["used"] == 2  # 两次启动都扣次，中断不返还
    assert t["disabled"] is True
    assert len(read_fake_log(env)) == 2
    # 任何结局后尝试目录都被清理
    assert_no_tmp_residue(env)


def test_l4_crash_once_retry_succeeds(env):
    """L4：第一次崩、重试成功 → 退出 0 但 used=2（预留后中断不返还）。"""
    flag = env["tmp"] / "crash.flag"
    flag.write_text("", encoding="utf-8")
    p = run_listen(env, fake_env={"FAKE_MODE": "crash_once", "FAKE_CRASH_FLAG": str(flag)})
    assert p.returncode == 0, p.stderr
    r = result_of(p)
    assert r["ok"] is True
    assert r["failure"] is None
    assert r["budget_remaining"] == 1  # 3 - 2
    t = read_state(env)
    assert t["used"] == 2
    assert t["disabled"] is False
    entries = read_fake_log(env)
    assert len(entries) == 2
    # 目录排他的可观察面：进程运行期间 .listen-tmp 里只有本次一个尝试目录
    assert all(len(e["listen_tmp"]) == 1 for e in entries)
    assert_no_tmp_residue(env)


def test_l4_consecutive_across_invocations(env):
    """L4 连败跨调用累计：上一次崩 1 次未禁用，本次再崩 1 次即达 2 次禁用。"""
    p1 = run_listen(env, task="t1", budget=5,
                    fake_env={"FAKE_MODE": "crash_once",
                              "FAKE_CRASH_FLAG": str(env["tmp"] / "f1.flag")})
    # 上面那套是"崩一次后成功"；这里直接预置 consec=1 再崩一次
    write_state(env, "t2", {"consec_proc_fail": 1})
    flag2 = env["tmp"] / "f2.flag"
    flag2.write_text("", encoding="utf-8")  # 让本次第一次尝试硬崩
    p2 = run_listen(env, task="t2", budget=5, fake_env={"FAKE_MODE": "crash_once",
                    "FAKE_CRASH_FLAG": str(flag2)})
    assert p1.returncode == 0
    assert p2.returncode == 3
    t2 = read_state(env, task="t2")
    assert t2["disabled"] is True
    assert t2["used"] == 1  # 本次只启动一次：连败计数已到 2，不再重试


def test_l5_parse_fail_no_output(env):
    """L5：退出 0 但没有输出文件 → 不重试不禁用，退出 4。"""
    p = run_listen(env, fake_env={"FAKE_MODE": "no_output"})
    assert p.returncode == 4
    r = result_of(p)
    assert r["ok"] is False
    assert r["failure"] == "parse_failed"
    assert r["output_path"] is None
    t = read_state(env)
    assert t["used"] == 1
    assert t["disabled"] is False
    assert len(read_fake_log(env)) == 1
    assert_no_tmp_residue(env)


def test_l5_parse_fail_no_list_item(env):
    """L5：退出 0、输出非空但无 "- " 列表项 → 退出 4。"""
    p = run_listen(env, fake_env={"FAKE_MODE": "bad_output"})
    assert p.returncode == 4
    assert result_of(p)["failure"] == "parse_failed"
    assert read_state(env)["disabled"] is False


# ---------------------------------------------------------------- 切片 3：会话策略


def test_diverge_blindspot_always_fresh(env):
    """diverge/blindspot 恒 fresh：即使 state 里留有 thread_id 也不 resume。"""
    p1 = run_listen(env, mode="diverge", fake_env={"FAKE_THREAD_ID": "th-d1"})
    assert p1.returncode == 0
    # state 已有 thread_id，第二次 diverge 仍应 fresh
    p2 = run_listen(env, mode="diverge", fake_env={"FAKE_THREAD_ID": "th-d2"})
    assert p2.returncode == 0, p2.stderr
    entries = read_fake_log(env)
    assert all("resume" not in e["argv"] for e in entries)
    assert all("-m" in e["argv"] and "-C" in e["argv"] and "-c" in e["argv"] for e in entries)
    assert read_state(env)["used"] == 2
    # blindspot 同理（新 workdir 由 fixture 隔离，直接再跑一次验证不含 resume）
    p3 = run_listen(env, mode="blindspot", task="t-b", fake_env={"FAKE_THREAD_ID": "th-b1"})
    assert p3.returncode == 0
    assert "resume" not in read_fake_log(env)[2]["argv"]


def test_attack_second_run_auto_resume_with_delta_prompt(env):
    """attack 第 2 次自动 resume：argv 含 thread_id、不含 -m，提示词为 --prompt-file 全文。"""
    p1 = run_listen(env, mode="attack", fake_env={"FAKE_THREAD_ID": "th-a1"})
    assert p1.returncode == 0, p1.stderr
    delta = env["tmp"] / "delta.md"
    delta.write_text("新增进展：结论 2 已被实验推翻。只针对增量继续攻击。", encoding="utf-8")
    p2 = run_listen(env, mode="attack", extra=["--prompt-file", str(delta)],
                    fake_env={"FAKE_THREAD_ID": "th-a2"})
    assert p2.returncode == 0, p2.stderr
    entries = read_fake_log(env)
    # 第 1 次 fresh：含 -m/-c/-C，无 resume；第 2 次 resume：含 thread_id，不含 -m
    assert "resume" not in entries[0]["argv"]
    assert "-m" in entries[0]["argv"] and "-c" in entries[0]["argv"] and "-C" in entries[0]["argv"]
    argv2 = entries[1]["argv"]
    assert "resume" in argv2 and "th-a1" in argv2
    assert "-m" not in argv2 and "-c" not in argv2
    assert entries[1]["prompt"] == delta.read_text(encoding="utf-8")
    t = read_state(env)
    assert t["used"] == 2
    assert t["thread_id"] == "th-a2"  # 成功后更新为最新会话


def test_attack_resume_without_prompt_file_exit_2(env):
    """attack 已有 thread_id 但缺 --prompt-file → 退出码 2，不启动。"""
    write_state(env, "t1", {"thread_id": "th-x"})
    p = run_listen(env, mode="attack")
    assert p.returncode == 2
    assert result_of(p)["failure"] == "resume_requires_prompt_file"
    assert not env["log"].exists()
    assert read_state(env)["used"] == 0


def test_attack_resume_fail_falls_back_to_fresh(env):
    """resume 调用非零 → 清 thread_id、按 fresh 重来一次：不按 L4 计连败，failure 记降级。"""
    p1 = run_listen(env, mode="attack", fake_env={"FAKE_THREAD_ID": "th-a1"})
    assert p1.returncode == 0
    delta = env["tmp"] / "delta.md"
    delta.write_text("delta 提示词", encoding="utf-8")
    p2 = run_listen(env, mode="attack", extra=["--prompt-file", str(delta)],
                    fake_env={"FAKE_MODE": "resume_fail", "FAKE_THREAD_ID": "th-a2"})
    assert p2.returncode == 0, p2.stderr
    r = result_of(p2)
    assert r["ok"] is True
    assert r["failure"] == "resume_failed_fallback_fresh"
    entries = read_fake_log(env)
    assert len(entries) == 3
    assert "resume" in entries[1]["argv"]          # 第 2 次：resume 尝试（失败）
    assert "resume" not in entries[2]["argv"]      # 降级 fresh
    assert "-m" in entries[2]["argv"]
    t = read_state(env)
    assert t["used"] == 3              # 两次调用：fresh 1 次 + resume 尝试 1 次 + 降级 fresh 1 次（各扣一次）
    assert t["disabled"] is False      # 不按 L4 计连续失败
    assert t["thread_id"] == "th-a2"   # 新 fresh 会话的 thread_id
    assert t["consec_proc_fail"] == 0


# ---------------------------------------------------------------- 切片 4：stdin 隔离 / 硬超时 / 裸命令名解析


def test_stdin_isolated_devnull(env):
    """stdin 隔离：codex 的 stdin 必须是 DEVNULL。

    假 codex 在 read_stdin 模式下 sys.stdin.read()：stdin=DEVNULL → 立即 EOF
    返回 "" → 正常输出；若继承父进程的未关闭管道 → 阻塞读直到 proc-timeout。
    测试给 dual-listen 一个永不关闭的 stdin 管道，复现未隔离时的挂死。
    """
    p = run_listen(env, stdin_pipe=True, proc_timeout=8,
                   fake_env={"FAKE_MODE": "read_stdin"})
    assert p.returncode == 0, "codex 的 stdin 未隔离为 DEVNULL，阻塞到超时：%s" % p.stderr[-500:]
    assert result_of(p)["ok"] is True
    assert len(read_fake_log(env)) == 1  # fake 正常跑完而非被超时击杀


def test_hang_process_tree_hard_killed(env):
    """硬超时：挂死（含持有句柄的孙进程）在 proc-timeout 后被杀整棵进程树。

    分类为 L4：重试再挂 → 连续 2 次 → 禁用、退出 3；扣次不返还；
    stdout/stderr 落文件（非 PIPE）故清理不被句柄阻塞，尝试目录无残留。
    """
    t0 = time.monotonic()
    p = run_listen(env, proc_timeout=2, fake_env={"FAKE_MODE": "hang"})
    elapsed = time.monotonic() - t0
    assert p.returncode == 3
    r = result_of(p)
    assert r["failure"] == "process_failed"
    assert r["disabled"] is True
    assert r["budget_remaining"] == 1  # 两次启动各扣一次，不返还
    t = read_state(env)
    assert t["used"] == 2
    assert t["disabled"] is True
    assert elapsed < 40, "硬超时失效：整个调用耗时 %.1fs（应约 2 次 proc-timeout）" % elapsed
    assert_no_tmp_residue(env)


def test_bare_codex_name_resolves_via_cmd_and_js(env):
    """裸命令名解析策略：优先 .exe/.com；否则借 .cmd 同目录的 codex.js 以 [node, js] 启动，
    避免落到 npm .cmd 包装层。PATH 里只放 .cmd 包装（它被写成必败脚本）：
    修复前 which("codex") 直接命中包装层 → 进程失败；修复后走 js 分支 → 正常。"""
    bin_dir = env["tmp"] / "bin"
    (bin_dir / "node_modules" / "@openai" / "codex" / "bin").mkdir(parents=True)
    codex_js = bin_dir / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
    codex_js.write_text("// fake js 入口\n", encoding="utf-8")
    (bin_dir / "codex.cmd").write_text("@exit /B 1\r\n", encoding="utf-8")  # 包装层必败
    fake_node_py = env["tmp"] / "fake_node.py"
    fake_node_py.write_text(FAKE_CODEX_SRC, encoding="utf-8")
    (bin_dir / "node.cmd").write_text(
        '@"%s" "%s" %%*\r\n' % (sys.executable, fake_node_py), encoding="utf-8")
    p = run_listen(
        env, codex_bin="codex",
        fake_env={"FAKE_THREAD_ID": "th-js",
                  "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"]})
    assert p.returncode == 0, "未走 .cmd→codex.js 分支：%s" % p.stderr[-500:]
    r = result_of(p)
    assert r["ok"] is True
    entries = read_fake_log(env)
    assert str(codex_js) in entries[0]["argv"]  # 以 [node, codex.js] 前缀启动
    assert "exec" in entries[0]["argv"]
