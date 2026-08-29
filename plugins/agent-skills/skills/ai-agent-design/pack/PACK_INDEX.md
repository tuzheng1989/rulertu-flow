# ai-agent-design-pack · Skill Pack 索引

《深入理解 AI Agent：设计原理与工程实践》（李博杰 / Pine AI 首席科学家）的 hybrid skill-pack。
来源：[bojieli/ai-agent-book](https://github.com/bojieli/ai-agent-book)（Apache-2.0）。
核心公式：**Agent = LLM + 上下文 + 工具**。

> Pack 根目录仅用于交付与审计，**不是一个可安装 skill**。安装时复制 `skills/` 下的叶子目录到宿主 skills 目录（如 `.claude/skills/`）。

## 顶层入口（推荐日常使用）
`ai-agent-design`（位于 `.claude/skills/ai-agent-design/SKILL.md`）是统一路由 skill，已被 Claude Code 自动发现。它按用户意图（查询理解 / 核对原文 / 执行方法 / 现实参考）索引到下方四组件，**日常直接用这个入口即可**，无需手动定位 pack 内文件。

## 四组件

| 组件 | 叶子 skill | 用途 |
|---|---|---|
| **faithful** 原文层 | `ai-agent-design-source` | 原书全文（12 章 92 子节）可检索，逐字核对 |
| **knowledge** 百科层 | `ai-agent-design-knowledge` | 知识压缩：骨架 + 术语 + 对比框架 + 决策速查 + 12 章压缩 |
| **methods** 方法层 | 7 个可执行方法（见下） | 蒸馏出的独立、可触发、可执行方法 |
| **examples** 现实参考层 | `ai-agent-design-examples` | 外部 agent 项目清单（35 分类 / 239 项目，来自 awesome-ai-agents），现实实现参考 / 选型 / 竞品 |

## methods 叶子 skill（7 个）

| Skill | 解决问题 | 触发场景 |
|---|---|---|
| `ai-agent-design-react-loop` | Agent 推进循环 | 构建 Agent 主循环 |
| `ai-agent-design-proposer-reviewer` | 任务完成判定 | 防假成功 / 过早放弃 |
| `ai-agent-design-context-engineering` | 上下文管理 | KV Cache / 压缩 / Skills / 状态栏 |
| `ai-agent-design-eval-driven-iteration` | 科学评估闭环 | 判断改动真伪 / 选型 |
| `ai-agent-design-tool-design` | 工具与异步架构 | 设计工具 / 安全审查 / 事件驱动 |
| `ai-agent-design-sft-vs-rl-selection` | 后训练选型 | SFT vs RL / 奖励设计 |
| `ai-agent-design-coding-as-meta-tool` | 代码元能力 | 用代码思考 / 创造工具 / 自举 |

## 推荐组合
- **查询与理解** → `ai-agent-design-knowledge`
- **核对原文出处** → `ai-agent-design-source`
- **执行具体设计** → 对应 methods skill（按 methods/INDEX.md 选用决策）
- **现实参考 / 选型 / 竞品** → `ai-agent-design-examples`（外部数据，非本书内容）
- 完整主干：`react-loop` + `proposer-reviewer` + `context-engineering`

## 未生成 / 降级内容（透明声明）
- `agentic-rag`：仅 ch3 单一章节证据，未通过多语境验证，**降级为 knowledge 条目**（ch03 + glossary），不做独立 method skill。
- methods 压力测试：每个 skill 已生成 `test-prompts.json`（3 should_trigger / 2 should_not_trigger / 1 edge_case / 1 decoy）；**完整盲测未执行**，留作部署后校验。
- faithful 层原书无章节编号，pipeline.py 不兼容，按章 + `##` 子节语义切分（详见 source 的 `.book2skill-generated.json`）。

## 内容边界
knowledge / source / methods 三组件全部内容仅来自这一本书，不包含书外知识。**例外**：`ai-agent-design-examples` 为外部参考数据（来自 `slavakurilyak/awesome-ai-agents` 静态快照，2026-07-27），仅作现实实现参考，已在组件内强力标注身份，不纳入本书知识体系。模型 / 产品能力数字截至 2026 年中，原则部分稳定。

## 安装
```bash
# 复制叶子 skill 到项目 skills 目录
cp -r skills/ai-agent-design-source     .claude/skills/
cp -r skills/ai-agent-design-knowledge  .claude/skills/
cp -r skills/methods/skills/ai-agent-design-*  .claude/skills/
cp -r skills/ai-agent-design-examples   .claude/skills/
```
