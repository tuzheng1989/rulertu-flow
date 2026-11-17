#!/usr/bin/env python3
"""verify_plugins.py — plugin-release 技能的验证器。

在 `zcode plugins update` 之后运行，对 rulertu-flow 市场插件做四项检查并输出汇总：

1. 仓库门禁    ：scripts/validate_repo.py 除 4 条存量 ERROR（family-skills/secret-skills
                 本地未上架目录所致）外零新增；
2. 版本一致    ：`zcode plugins list --json` 中各插件 version == 仓库 manifest version；
3. 内容一致    ：以 `git ls-files` 为基准（未追踪文件不参与），仓库工作区与
                 插件缓存目录逐文件比对；仅行尾（CRLF/LF）差异记 WARN 不判 FAIL；
4. CLI 结构校验：`zcode plugins validate <插件目录>` 逐个通过。

用法：
    python verify_plugins.py                # 验证本机已安装的全部 rulertu-flow 市场插件
    python verify_plugins.py flow-deck      # 只验证指定插件（可多个）

退出码：存在 FAIL 项为 1，否则 0。WARN 不影响退出码。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Windows 控制台默认 GBK，统一转 UTF-8 避免中文输出乱码
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[4]
PLUGINS = ROOT / "plugins"
VALIDATE = ROOT / "scripts" / "validate_repo.py"
CACHE = Path.home() / ".zcode" / "cli" / "plugins" / "cache" / "rulertu-flow"
MARKET = "rulertu-flow"

# validate_repo.py 的存量基线（family-skills / secret-skills 本地目录未登记
# marketplace 所致，长期存在且与本技能无关；见 memory 与 CHANGELOG 2.10.1 条目）。
# 两目录为 .gitignore 本地目录、不随 git 同步：主工作站仍在，4 条报错为存量；
# 2026-11-17 另一机器删目录后曾清空基线（6cb29bf），致主工作站把存量误判为
# 新增，现恢复。目录已删的机器会得到"基线报错消失"WARN，属预期而非 FAIL。
GATE_BASELINE: set[str] = {
    "ERROR: Claude marketplace entries and plugin dirs differ",
    "ERROR: Codex marketplace entries and plugin dirs differ",
    "ERROR: manifest missing: family-skills",
    "ERROR: manifest missing: secret-skills",
}

FAILS: list[str] = []
WARNS: list[str] = []


def fail(msg: str) -> None:
    FAILS.append(msg)
    print(f"  ❌ {msg}")


def warn(msg: str) -> None:
    WARNS.append(msg)
    print(f"  ⚠️  {msg}")


def ok(msg: str) -> None:
    print(f"  ✅ {msg}")


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=ROOT, **kw)


# ---------- zcode CLI 解析（同 update 技能口径：PATH 优先，降级已知安装位） ----------

def resolve_zcode() -> list[str] | None:
    if shutil.which("zcode"):
        return ["zcode"]
    local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    for cand in (
        Path(r"C:\Program Files (x86)\ZCode\resources\glm\zcode.cjs"),
        Path(r"C:\Program Files\ZCode\resources\glm\zcode.cjs"),
        Path(local) / "Programs" / "ZCode" / "resources" / "glm" / "zcode.cjs",
    ):
        if cand.is_file():
            return ["node", str(cand)]
    return None


# ---------- 1. 仓库门禁 ----------

def check_gate() -> None:
    print("\n[1/4] 仓库门禁 validate_repo.py（存量外零新增）")
    if not VALIDATE.is_file():
        fail(f"门禁脚本不存在: {VALIDATE}")
        return
    p = run([sys.executable, str(VALIDATE)])
    lines = {ln.strip() for ln in (p.stderr + p.stdout).splitlines() if ln.strip().startswith("ERROR:")}
    new = sorted(lines - GATE_BASELINE)
    gone = sorted(GATE_BASELINE - lines)
    if p.returncode != 0 and not lines:
        fail(f"门禁异常退出（exit={p.returncode}）且未解析到 ERROR 行：\n{p.stderr.strip()[:500]}")
        return
    if new:
        for ln in new:
            fail(f"门禁新增报错: {ln}")
    else:
        ok("门禁零报错" if not GATE_BASELINE else f"存量 {len(lines)} 条基线报错之外零新增")
    if gone:
        warn(f"基线报错消失（基线可能过时，考虑更新 GATE_BASELINE）: {gone}")


# ---------- 已安装清单 ----------

def installed_rulertu_plugins(zcode: list[str]) -> dict[str, dict]:
    """返回 {插件名: list --json 条目}，仅 rulertu-flow 市场且已安装的。"""
    p = run(zcode + ["plugins", "list", "--json"])
    if p.returncode != 0:
        fail(f"zcode plugins list --json 失败：{p.stderr.strip()[:300]}")
        return {}
    try:
        entries = json.loads(p.stdout)
    except json.JSONDecodeError as e:
        fail(f"plugins list --json 输出解析失败：{e}")
        return {}
    return {e["name"]: e for e in entries if e.get("marketplace") == MARKET}


def manifest_version(name: str) -> str:
    m = PLUGINS / name / ".claude-plugin" / "plugin.json"
    return json.loads(m.read_text(encoding="utf-8"))["version"]


# ---------- 2. 版本一致 ----------

def check_versions(names: list[str], installed: dict[str, dict]) -> None:
    print("\n[2/4] 版本一致（仓库 manifest vs 本机缓存）")
    for name in names:
        repo_v = manifest_version(name)
        entry = installed.get(name)
        if entry is None:
            fail(f"{name}: 本机未安装（仓库 {repo_v}）")
            continue
        cache_v = entry.get("version", "")
        if cache_v == repo_v:
            ok(f"{name}: {repo_v}")
        else:
            fail(f"{name}: 仓库 {repo_v} ≠ 缓存 {cache_v}（plugins update 未生效？）")


# ---------- 3. 内容一致 ----------

def normalize(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def check_contents(names: list[str], installed: dict[str, dict]) -> None:
    print("\n[3/4] 内容一致（git 追踪文件 vs 缓存，行尾归一后比对）")
    for name in names:
        entry = installed.get(name)
        if entry is None:
            continue  # 未安装已在版本检查报过
        # list --json 的缓存路径字段是 rootPath（installed_plugins.json 里才叫 installPath）
        raw = entry.get("rootPath", "")
        cache_dir = Path(raw) if raw else None
        if cache_dir is None or not cache_dir.is_dir():
            fail(f"{name}: 缓存目录不存在: {raw or '(list --json 无 rootPath)'}")
            continue
        # -z：NUL 分隔且不做 quotePath 转义——中文文件名按原样输出
        p = subprocess.run(["git", "ls-files", "-z", "--", f"plugins/{name}"],
                           capture_output=True, cwd=ROOT)
        tracked = [ln for ln in p.stdout.decode("utf-8", errors="replace").split("\0") if ln.strip()]
        if not tracked:
            fail(f"{name}: git ls-files 无追踪文件（插件名有误？）")
            continue
        missing, differ, eol_only, checked = [], [], [], 0
        for rel in tracked:
            prefix = f"plugins/{name}/"
            rel_inside = rel[len(prefix):]
            repo_f = ROOT / rel
            cache_f = cache_dir / rel_inside
            if not cache_f.is_file():
                missing.append(rel_inside)
                continue
            a = repo_f.read_bytes()
            b = cache_f.read_bytes()
            checked += 1
            if a == b:
                continue
            if b"\0" in a or b"\0" in b:
                differ.append(rel_inside)  # 二进制真差异，不做行尾归一
            elif normalize(a) == normalize(b):
                eol_only.append(rel_inside)
            else:
                differ.append(rel_inside)
        if missing:
            fail(f"{name}: 缓存缺 {len(missing)} 个追踪文件，如 {missing[:3]}")
        if differ:
            fail(f"{name}: 缓存 {len(differ)} 个文件内容不一致，如 {differ[:3]}")
        if eol_only:
            warn(f"{name}: {len(eol_only)} 个文件仅行尾差异（CRLF/LF），判定通过")
        if not missing and not differ:
            ok(f"{name}: {checked} 个追踪文件逐字节/行尾归一一致")


# ---------- 4. CLI 结构校验 ----------

def check_validate(names: list[str], zcode: list[str]) -> None:
    print("\n[4/4] CLI 结构校验 zcode plugins validate")
    for name in names:
        d = PLUGINS / name
        p = run(zcode + ["plugins", "validate", str(d)])
        if p.returncode == 0:
            ok(f"{name}")
        else:
            fail(f"{name}: validate 失败\n{(p.stderr or p.stdout).strip()[:500]}")


# ---------- 汇总 ----------

def main() -> int:
    ap = argparse.ArgumentParser(description="rulertu-flow 插件发布后验证")
    ap.add_argument("plugins", nargs="*", help="要验证的插件名；缺省 = 本机已安装的全部 rulertu-flow 市场插件")
    args = ap.parse_args()

    zcode = resolve_zcode()
    if zcode is None:
        print("❌ 未找到 zcode CLI（PATH 与已知安装位置均无）")
        return 1

    installed = installed_rulertu_plugins(zcode)
    if not installed and not args.plugins:
        print("❌ 本机未安装任何 rulertu-flow 市场插件，且未指定插件名")
        return 1
    names = args.plugins or sorted(installed)

    # 指定的插件必须是仓库里的真实插件
    bad = [n for n in names if not (PLUGINS / n / ".claude-plugin" / "plugin.json").is_file()]
    for n in bad:
        fail(f"未知插件: {n}（plugins/ 下无对应 manifest）")
    if bad:
        return 1

    print(f"验证对象: {', '.join(names)}")
    check_gate()
    check_versions(names, installed)
    check_contents(names, installed)
    check_validate(names, zcode)

    print("\n==================== 汇总 ====================")
    if FAILS:
        for f in FAILS:
            print(f"  ❌ {f.splitlines()[0]}")
        print(f"\n结果: FAIL（{len(FAILS)} 项失败, {len(WARNS)} 项警告）")
        return 1
    print(f"  全部通过（{len(WARNS)} 项警告）" if WARNS else "  全部通过，零警告")
    print("\n提示: 插件更新需重启 ZCode 会话后才在会话内生效。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
