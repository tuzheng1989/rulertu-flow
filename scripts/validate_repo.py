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
    require(codex_manifest["name"] == claude_manifest["name"] == "rulertu-flow", "manifest names differ", errors)
    require(codex_manifest["version"] == claude_manifest["version"] == "2.0.0", "manifest versions differ", errors)
    require(codex_market["plugins"][0]["source"]["path"] == "./plugins/rulertu-flow", "Codex marketplace path differs", errors)
    require(claude_market["plugins"][0]["source"] == "./plugins/rulertu-flow", "Claude marketplace path differs", errors)
    require(codex_market["plugins"][0]["name"] == claude_market["plugins"][0]["name"] == "rulertu-flow", "marketplace names differ", errors)
    require((PLUGIN / codex_manifest["skills"].removeprefix("./")).is_dir(), "skills path is missing", errors)
    require(set(review_schema["required"]) == {"overall_quality", "score", "issues", "suggestions"}, "review schema fields differ", errors)

    for skill in (PLUGIN / "skills").glob("*/SKILL.md"):
        text = skill.read_text(encoding="utf-8")
        front = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        require(bool(front), f"missing frontmatter: {skill}", errors)
        if front:
            require("name:" in front.group(1) and "description:" in front.group(1), f"incomplete frontmatter: {skill}", errors)

    for role in ("executor", "auditor", "advisor"):
        wrapper = (PLUGIN / "agents" / f"{role}.md").read_text(encoding="utf-8")
        require("model: inherit" in wrapper, f"{role} wrapper model must inherit", errors)
        require(f"references/roles/{role}.md" in wrapper, f"{role} wrapper lacks role pointer", errors)
        require(len(wrapper.splitlines()) <= 10, f"{role} wrapper is not thin", errors)
        require((PLUGIN / "references" / "roles" / f"{role}.md").is_file(), f"{role} body missing", errors)

    executor = (PLUGIN / "references" / "roles" / "executor.md").read_text(encoding="utf-8")
    implement = (PLUGIN / "skills" / "implement-plan" / "SKILL.md").read_text(encoding="utf-8")
    require("普通子任务不扩大为全仓测试" in executor, "Executor directed-test policy missing", errors)
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
