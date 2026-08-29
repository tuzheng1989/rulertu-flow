# ai-agent-design-examples · 概览

## 定位（身份声明）

本组件是 ai-agent-design-pack 的**外部现实参考层**：收录现成 AI Agent 项目清单，
供设计 agent 时查看「某类 agent 已有哪些现实实现」「某项能力有哪些框架/服务可选」「竞品参考」「技术选型」。

⚠️ **硬约束**：数据来自外部仓库 `slavakurilyak/awesome-ai-agents` 静态快照，**非李博杰本书内容**。
本组件只回答「有什么实现」，**不回答**「为何这么设计」——后者归 knowledge / source / methods 三组件。

## 数据来源

- 上游仓库：[slavakurilyak/awesome-ai-agents](https://github.com/slavakurilyak/awesome-ai-agents)
- 快照日期：2026-07-27
- 来源 commit：`0da290a`（0da290a403c216507422576b2752c2ab81b97e7c）
- 规模：239 个项目 / 35 个分类
- GitHub Stars 数据截止：2025-07-30（由上游 `02-update-github-stars.py` 写入，非本次快照实时值）
- 许可：上游仓库 LICENSE（见 source_url）

## 如何使用（按需渐进加载）

1. 读 [`index.md`](index.md) → 按分类名命中目标。
2. 读 `categories/<分类slug>.md` → 看该分类下项目清单（含描述、开源标记、链接、stars）。
3. 需要跨分类对比或理解定位时回到本概览。

## 质量与边界

- 清单含商业服务、SDK、框架、模型，**质量参差**，仅作参考实现，**非推荐**。
- 每条仅有「一句话描述 + 链接」，**无设计推理**；要深挖请顺链接去上游项目自行调研。
- 项目可属多分类，会在多个分类文件出现。
- 静态快照会随时间过时；如需更新见下节。

## 数据更新

重新拉取 `awesome-agents.json` 到 `_data/`、更新 `snapshot.meta.json` 后，重跑：

```bash
python _scripts/gen_gallery.py
```

