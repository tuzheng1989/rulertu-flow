#!/usr/bin/env python3
# gen_gallery.py —— 从 awesome-agents.json 生成 ai-agent-design-examples 分类参考库
#
# 零第三方依赖，仅用 Python 标准库（遵循"优先原生方法"准则）。
# 输入：../_data/awesome-agents.json + ../snapshot.meta.json
# 输出：../categories/<slug>.md（每分类一文件）+ ../index.md + ../overview.md
#
# 用法：python gen_gallery.py
# 更新数据后重跑即可刷新全部 markdown。

import json
import re
import pathlib

BASE = pathlib.Path(__file__).resolve().parents[1]  # references/
DATA = BASE / "_data" / "awesome-agents.json"
META = BASE / "snapshot.meta.json"
CAT_DIR = BASE / "categories"


def slugify(name):
    """分类名 -> 文件名 slug：小写，非 [a-z0-9] 替为连字符，首尾不留连字符。"""
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def load():
    d = json.loads(DATA.read_text(encoding="utf-8"))
    agents = d.get("agents", [])
    categories = d.get("categories", [])
    meta = {}
    if META.exists():
        meta = json.loads(META.read_text(encoding="utf-8"))
    return agents, categories, meta


def group_by_category(agents, categories):
    """category name -> [agent, ...]；一个 agent 属多分类时在每个分类都出现。"""
    buckets = {c["category"]: [] for c in categories}
    for a in agents:
        for cat in a.get("categories", []):
            if cat in buckets:
                buckets[cat].append(a)
    return buckets


def github_top_stars(agent):
    """取该 agent 所有 github 源中的最高 stars；无则 0。用于排序。"""
    top = 0
    for s in agent.get("sources", []):
        if (s.get("source") or "").lower() == "github" and s.get("stars") is not None:
            top = max(top, s["stars"])
    return top


def sort_agents(agents):
    return sorted(agents, key=lambda a: (-github_top_stars(a), (a.get("project") or "").lower()))


def fmt_links(sources):
    """渲染所有 source 为 [label](url)；github 源附 (★ N)。无 url 者跳过。"""
    parts = []
    for s in sources or []:
        url = s.get("source_url")
        if not url:
            continue
        label = (s.get("source") or "link").strip()
        if (s.get("source") or "").lower() == "github" and s.get("stars") is not None:
            label = f"github (★ {s['stars']:,})"
        parts.append(f"[{label}]({url})")
    return " · ".join(parts)


def oss_mark(agent):
    v = agent.get("project_is_open_source")
    if v is True:
        return "✅ 开源"
    if v is False:
        return "❌ 闭源/商业"
    return "— 未知"


def render_category(cat_obj, agents):
    name = cat_obj.get("category", "")
    desc = cat_obj.get("category_description", "")
    emoji = cat_obj.get("emoji", "")
    title = f"# {emoji} {name}".strip()
    agents = sort_agents(agents)
    lines = [title, ""]
    if desc:
        lines += [f"> {desc}", ""]
    lines.append(f"共 {len(agents)} 个项目（按 GitHub Stars 降序，无 stars 者按名称）。")
    lines.append("")
    for a in agents:
        proj = a.get("project", "")
        pdesc = (a.get("project_description") or "").strip()
        lines.append(f"### {proj}")
        if pdesc:
            lines.append(f"- 描述：{pdesc}")
        lines.append(f"- 开源：{oss_mark(a)}")
        links = fmt_links(a.get("sources", []))
        if links:
            lines.append(f"- 链接：{links}")
        # 该 agent 同时所属的其他分类（便于跨分类跳转）
        other = [c for c in a.get("categories", []) if c != name]
        if other:
            lines.append("- 另见分类：" + "、".join(other))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_index(categories, buckets):
    lines = [
        "# ai-agent-design-examples · 索引",
        "",
        "> 外部参考库（来自 slavakurilyak/awesome-ai-agents 静态快照，**非本书内容**）。",
        "> 先在此命中分类，再读 `categories/<分类slug>.md` 看项目清单。",
        "",
        "## 35 分类总表",
        "",
        "| 分类 | 项目数 | 文件 |",
        "|---|---:|---|",
    ]
    for c in categories:
        name = c.get("category", "")
        emoji = c.get("emoji", "")
        cnt = len(buckets.get(name, []))
        slug = slugify(name)
        lines.append(f"| {emoji} {name} | {cnt} | [`{slug}.md`](categories/{slug}.md) |")
    lines += [
        "",
        "> 注：项目可属多分类，会在多个文件出现；故各分类项目数之和大于项目总数。",
        "",
    ]
    return "\n".join(lines) + "\n"


def render_overview(agents, categories, buckets, meta):
    commit = meta.get("source_commit", "N/A")
    short = commit[:7] if commit != "N/A" else "N/A"
    snap = meta.get("snapshot_date", "N/A")
    stars_upd = meta.get("stars_last_updated", "N/A")
    lines = [
        "# ai-agent-design-examples · 概览",
        "",
        "## 定位（身份声明）",
        "",
        "本组件是 ai-agent-design-pack 的**外部现实参考层**：收录现成 AI Agent 项目清单，",
        "供设计 agent 时查看「某类 agent 已有哪些现实实现」「某项能力有哪些框架/服务可选」「竞品参考」「技术选型」。",
        "",
        "⚠️ **硬约束**：数据来自外部仓库 `slavakurilyak/awesome-ai-agents` 静态快照，**非李博杰本书内容**。",
        "本组件只回答「有什么实现」，**不回答**「为何这么设计」——后者归 knowledge / source / methods 三组件。",
        "",
        "## 数据来源",
        "",
        f"- 上游仓库：[{meta.get('source_repo','slavakurilyak/awesome-ai-agents')}]({meta.get('source_url','')})",
        f"- 快照日期：{snap}",
        f"- 来源 commit：`{short}`（{commit}）",
        f"- 规模：{len(agents)} 个项目 / {len(categories)} 个分类",
        f"- GitHub Stars 数据截止：{stars_upd}（由上游 `02-update-github-stars.py` 写入，非本次快照实时值）",
        f"- 许可：{meta.get('license','见上游仓库 LICENSE')}",
        "",
        "## 如何使用（按需渐进加载）",
        "",
        "1. 读 [`index.md`](index.md) → 按分类名命中目标。",
        "2. 读 `categories/<分类slug>.md` → 看该分类下项目清单（含描述、开源标记、链接、stars）。",
        "3. 需要跨分类对比或理解定位时回到本概览。",
        "",
        "## 质量与边界",
        "",
        "- 清单含商业服务、SDK、框架、模型，**质量参差**，仅作参考实现，**非推荐**。",
        "- 每条仅有「一句话描述 + 链接」，**无设计推理**；要深挖请顺链接去上游项目自行调研。",
        "- 项目可属多分类，会在多个分类文件出现。",
        "- 静态快照会随时间过时；如需更新见下节。",
        "",
        "## 数据更新",
        "",
        "重新拉取 `awesome-agents.json` 到 `_data/`、更新 `snapshot.meta.json` 后，重跑：",
        "",
        "```bash",
        "python _scripts/gen_gallery.py",
        "```",
        "",
    ]
    return "\n".join(lines) + "\n"


def main():
    agents, categories, meta = load()
    buckets = group_by_category(agents, categories)

    # slug 唯一性校验
    seen = {}
    for c in categories:
        slug = slugify(c["category"])
        if slug in seen:
            raise SystemExit(f"slug 冲突：{seen[slug]} 与 {c['category']} 都得到 {slug}")
        seen[slug] = c["category"]

    CAT_DIR.mkdir(parents=True, exist_ok=True)
    for c in categories:
        name = c["category"]
        md = render_category(c, buckets.get(name, []))
        (CAT_DIR / f"{slugify(name)}.md").write_text(md, encoding="utf-8")

    (BASE / "index.md").write_text(render_index(categories, buckets), encoding="utf-8")
    (BASE / "overview.md").write_text(render_overview(agents, categories, buckets, meta), encoding="utf-8")

    nfiles = len(list(CAT_DIR.glob("*.md")))
    print(f"OK: {nfiles} category files + index.md + overview.md")


if __name__ == "__main__":
    main()
