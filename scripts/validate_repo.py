"""Repository-local release gate for the dual-host plugin."""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "rulertu-flow"

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def market_entry(market: dict, name: str):
    for entry in market["plugins"]:
        if entry["name"] == name:
            return entry
    return None

def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)

def validate() -> list[str]:
    errors: list[str] = []
    codex_manifest = load(PLUGIN / ".codex-plugin" / "plugin.json")
    claude_manifest = load(PLUGIN / ".claude-plugin" / "plugin.json")
    codex_market = load(ROOT / ".agents" / "plugins" / "marketplace.json")
    claude_market = load(ROOT / ".claude-plugin" / "marketplace.json")
    review_schema = load(PLUGIN / "skills" / "plan-iterate" / "scripts" / "review-schema.json")
    plan_iterate = (PLUGIN / "skills" / "plan-iterate" / "SKILL.md").read_text(encoding="utf-8")
    require(codex_manifest["name"] == claude_manifest["name"] == "rulertu-flow", "manifest names differ", errors)
    require(codex_manifest["version"] == claude_manifest["version"], "manifest versions differ", errors)
    codex_flow = market_entry(codex_market, "rulertu-flow")
    claude_flow = market_entry(claude_market, "rulertu-flow")
    require(codex_flow is not None and claude_flow is not None, "rulertu-flow marketplace entry missing", errors)
    if codex_flow is not None and claude_flow is not None:
        require(codex_flow["source"]["path"] == "./plugins/rulertu-flow", "Codex marketplace path differs", errors)
        require(claude_flow["source"] == "./plugins/rulertu-flow", "Claude marketplace path differs", errors)
        require(codex_flow["name"] == claude_flow["name"] == "rulertu-flow", "marketplace names differ", errors)
    require((PLUGIN / codex_manifest["skills"].removeprefix("./")).is_dir(), "skills path is missing", errors)
    require(set(review_schema["required"]) == {"overall_quality", "score", "issues", "suggestions"}, "review schema fields differ", errors)
    review_scripts = PLUGIN / "skills" / "plan-iterate" / "scripts"
    for script in ("review_common.py", "codex_review.py", "claude_review.py", "codex-review.sh", "claude-review.sh"):
        require((review_scripts / script).is_file(), f"review backend file missing: {script}", errors)
    claude_backend = (review_scripts / "claude_review.py").read_text(encoding="utf-8")
    for fragment in ('"--model",\n        "opus"', '"--effort",\n        "high"', '"--permission-mode",\n        "plan"', '"Read,Glob,Grep"'):
        require(fragment in claude_backend, f"Claude read-only route differs: {fragment}", errors)
    require("shell=True" not in claude_backend, "Claude backend must not use a shell", errors)
    require("Codex 宿主：运行 `scripts/claude_review.py" in plan_iterate, "Codex host must route to Claude", errors)
    require("Claude Code 宿主：运行 `scripts/codex_review.py" in plan_iterate, "Claude host must route to Codex", errors)
    require("不回退为同宿主自评" in plan_iterate, "cross-model fallback guard missing", errors)

    for skill in (PLUGIN / "skills").glob("*/SKILL.md"):
        text = skill.read_text(encoding="utf-8")
        front = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        require(bool(front), f"missing frontmatter: {skill}", errors)
        if front:
            require("name:" in front.group(1) and "description:" in front.group(1), f"incomplete frontmatter: {skill}", errors)

    plugin_dirs = sorted(d for d in (ROOT / "plugins").iterdir() if d.is_dir())
    require({d.name for d in plugin_dirs} == {e["name"] for e in claude_market["plugins"]}, "Claude marketplace entries and plugin dirs differ", errors)
    require({d.name for d in plugin_dirs} == {e["name"] for e in codex_market["plugins"]}, "Codex marketplace entries and plugin dirs differ", errors)
    for plugin_dir in plugin_dirs:
        claude_manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
        codex_manifest_path = plugin_dir / ".codex-plugin" / "plugin.json"
        require(claude_manifest_path.is_file() and codex_manifest_path.is_file(), f"manifest missing: {plugin_dir.name}", errors)
        if not (claude_manifest_path.is_file() and codex_manifest_path.is_file()):
            continue
        plugin_claude = load(claude_manifest_path)
        plugin_codex = load(codex_manifest_path)
        require(plugin_claude["name"] == plugin_codex["name"] == plugin_dir.name, f"manifest names differ: {plugin_dir.name}", errors)
        require(plugin_claude["version"] == plugin_codex["version"], f"manifest versions differ: {plugin_dir.name}", errors)
        require((plugin_dir / "skills").is_dir(), f"skills path is missing: {plugin_dir.name}", errors)
        for skill in (plugin_dir / "skills").glob("*/SKILL.md"):
            text = skill.read_text(encoding="utf-8")
            front = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
            require(bool(front), f"missing frontmatter: {skill}", errors)
            if front:
                require("name:" in front.group(1) and "description:" in front.group(1), f"incomplete frontmatter: {skill}", errors)

    role_models = {"auditor": "opus", "advisor": "opus"}
    for role, model in role_models.items():
        wrapper = (PLUGIN / "agents" / f"{role}.md").read_text(encoding="utf-8")
        require(f"model: {model}" in wrapper, f"{role} wrapper model must be {model}", errors)
        require(f"references/roles/{role}.md" in wrapper, f"{role} wrapper lacks role pointer", errors)
        require(len(wrapper.splitlines()) <= 10, f"{role} wrapper is not thin", errors)
        require((PLUGIN / "references" / "roles" / f"{role}.md").is_file(), f"{role} body missing", errors)

    executor_wrapper = (PLUGIN / "agents" / "executor.md").read_text(encoding="utf-8")
    require("model:" not in executor_wrapper, "executor wrapper must not pin a model", errors)
    require("references/roles/executor.md" in executor_wrapper, "executor wrapper lacks role pointer", errors)
    require(len(executor_wrapper.splitlines()) <= 10, "executor wrapper is not thin", errors)
    require((PLUGIN / "references" / "roles" / "executor.md").is_file(), "executor role body missing", errors)

    executor = (PLUGIN / "references" / "roles" / "executor.md").read_text(encoding="utf-8")
    implement = (PLUGIN / "skills" / "implement-plan" / "SKILL.md").read_text(encoding="utf-8")
    codex_routes = (
        ("Executor", "gpt-5.6-terra", "medium", '"3"'),
        ("Auditor", "gpt-5.6-sol", "high", '"none"'),
        ("Advisor", "gpt-5.6-sol", "xhigh", '"none"'),
    )
    for role, model, effort, fork in codex_routes:
        require(
            f"| {role} | `{model}` | `{effort}` | `{fork}` |" in implement,
            f"Codex route differs for {role}",
            errors,
        )
    require('fork_turns="all"' in implement and "强制继承主控模型" in implement, "Codex full-fork guard missing", errors)
    require("普通子任务不扩大为全仓测试" in executor, "Executor directed-test policy missing", errors)
    require("需主控裁决" in executor, "Executor escalation marker missing", errors)
    require("直连" in implement, "Advisor direct-dispatch policy missing", errors)
    require("收尾时跑一次全量测试" not in executor + implement, "legacy full-suite rule remains", errors)
    require(implement.count("仅有以下情况运行全量测试") == 1, "full-suite exceptions must have one policy source", errors)
    for stale in (ROOT / "skills", ROOT / "agents", ROOT / ".codex-plugin"):
        require(not stale.exists(), f"stale root layout remains: {stale.name}", errors)
    return errors

if __name__ == "__main__":
    problems = validate()
    if problems:
        print("\n".join(f"ERROR: {item}" for item in problems), file=sys.stderr)
        raise SystemExit(1)
    print("repository validation passed")
