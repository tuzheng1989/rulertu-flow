---
name: ai-agent-design-examples
description: 《深入理解 AI Agent》pack 的外部现实参考层——精选 AI Agent 项目清单（来自 slavakurilyak/awesome-ai-agents，35 分类 / 239 项目静态快照）。当需要查看某类 agent 已有哪些现实实现、做技术选型、竞品参考、"已有项目怎么做的"、有哪些多 agent 框架 / 记忆 / 语音 / coding agent 项目时使用。触发词：agent 示例、agent 参考库、现实实现、竞品 agent、agent 选型、awesome ai agents、agent 项目清单、有哪些 agent、agent 实现、语音 agent 框架、记忆 agent、coding agent 项目、多 agent 框架、agent 案例、agent gallery。
---

# ai-agent-design-examples · 现实项目参考库

本书 pack 的**第四组件**，定位为外部现实参考层。本书公式：**Agent = LLM + 上下文 + 工具**。

本组件**不讲原理**，只提供「现实世界里有哪些现成 agent 实现可参考」。原理归 knowledge / source / methods 三组件，本组件补充三组件覆盖不到的「现实实现清单」。

## 身份与边界（硬约束）

- ⚠️ 本组件数据来自**外部仓库** `slavakurilyak/awesome-ai-agents` 静态快照，**非李博杰本书内容**。
- **只回答**：「某类 agent 有哪些实现」「某项能力有哪些框架/服务可选」「竞品参考」「技术选型」。
- **不回答**：「为何这么设计」「原理是什么」「该怎么实现」——这些归 knowledge / source / methods。
- 引用本组件内容时，必须标注「来自 awesome-ai-agents 外部参考」，**不得**包装为本书观点或设计原理。
- 数据是「项目名 + 一句话描述 + 链接 + stars」级别的清单，**无设计推理**；要深挖请顺链接去上游项目自行调研。

## 如何使用（按需渐进加载）

1. 读 [index.md](references/index.md) → 按分类名命中目标（35 分类总表：emoji / 名称 / 项目数 / 文件链接）。
2. 读对应 `references/categories/<分类slug>.md` → 看该分类下项目清单（按 GitHub Stars 降序，含描述、开源标记、链接、stars）。
3. 需要理解定位、数据来源或更新方式时读 [overview.md](references/overview.md)。

### 常见命中（场景 → 分类）

| 用户场景 | 命中分类 |
|---|---|
| 带长期记忆的 agent | Long-Term Memory |
| 语音 / 电话 agent | Voice Providers、Phone Calling、TTS Models、Transcriber Providers |
| 多 agent 协作 / 开发框架 | Development Frameworks、AI Agents |
| Coding / 浏览器 / OS 控制 agent | Operating System (OS)、Web Browsing Frameworks、Terminal-Friendly |
| 工具调用 / 结构化输出 | Tool Calling (Function Calling)、Structured Outputs |
| 评估 / 可观测 | Evaluation Frameworks、Observability Frameworks |
| 个人助手 | Personal Assistants、Assistants API |

分类完整清单见 [index.md](references/index.md)。

## 数据说明

- **规模**：239 个项目 / 35 个分类（详见 [snapshot.meta.json](references/snapshot.meta.json)）。
- **静态快照**：截至快照日期，非实时；GitHub Stars 数据截止上游 `02-update-github-stars` 脚本的上次运行时间。
- **质量参差**：清单含商业服务、SDK、框架、模型，**仅作参考实现，非推荐**。
- **多分类归属**：一个项目可属多分类，会在多个分类文件出现。
- 部分分类当前为 0 项目（上游已定义分类但暂无项目归入），文件保留以维持分类完整性。

## 数据更新

重新拉取 `awesome-agents.json` 到 `references/_data/`、更新 `references/snapshot.meta.json` 后，重跑：

```bash
python references/_scripts/gen_gallery.py
```

脚本零第三方依赖，仅用 Python 标准库 `json`。

## 来源

- 上游仓库：[slavakurilyak/awesome-ai-agents](https://github.com/slavakurilyak/awesome-ai-agents)（LICENSE 见仓库）
- 本组件为衍生索引，保留每条项目的原始 source 链接以溯上游。

## 边界

本组件是外部参考层；具体项目清单由 `references/` 承载。若用户需求是「agent 设计原理 / 怎么实现」，转 knowledge / source / methods，**不**用本组件充数。
