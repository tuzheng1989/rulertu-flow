---
name: ai-agent-design-knowledge
description: 《深入理解 AI Agent：设计原理与工程实践》（李博杰）知识压缩百科。当需要理解 Agent 设计原理、查询概念 / 框架 / 术语、对比设计选型（SFT vs RL、工作流 vs Agent、单 vs 多 Agent）、或做架构决策时使用。触发词：Agent 设计原理、上下文工程、Harness、ReAct、proposer-reviewer、MCP、SFT/RL、评估方法论、多 Agent 协作、agent 百科。
---

# ai-agent-design-knowledge · Agent 设计百科

《深入理解 AI Agent：设计原理与工程实践》（李博杰 / Pine AI 首席科学家）的知识压缩层。围绕核心公式 **Agent = LLM + 上下文 + 工具**，把 10 章 + 引言 + 后记压缩为可检索百科。本文为衍生解释；逐字核对用 `ai-agent-design-source`，执行具体方法用 methods 层 skill。

## 知识边界
只覆盖这本书的内容，不补写书外知识。书未覆盖的明确说明，不脑补。

## 如何使用（按需渐进加载）
- **理解全貌** → [overview.md](references/overview.md)（全书骨架 + 6 条核心判断 + 章节地图）
- **查术语** → [glossary.md](references/glossary.md)（含 reasoning / inference 区分）
- **对比选型** → [patterns.md](references/patterns.md)（11 个对比 / 因果 / 权衡模式）
- **做决策** → [cheatsheet.md](references/cheatsheet.md)（决策规则速查）
- **某章深入** → 按 [index.md](references/index.md) 主题索引读 references/chapters/ 对应文件

不确定时：overview 定位 → 读对应章 → glossary 校准术语。

## 核心公式与 6 条核心判断（最高密度）
**Agent = LLM + 上下文 + 工具**（大脑 + 眼睛 + 手脚；眼睛是决定性因素；学术层 = Policy + Observation + Action）。
1. 好的设计原则穿越模型迭代周期。
2. 实践在前，命名在后。
3. Harness 是竞争力（模型商品化时代的差异）。
4. 没有评估就没有进步。
5. 数据和环境比算法更重要。
6. 循环的瓶颈在验证器（proposer-reviewer）。

## 主题索引（→ 章）
核心公式 / Harness / 编排 → 引言 / ch1 / 后记 · KV Cache / 压缩 / Skills → ch2 · 记忆 / RAG / 双层架构 → ch3 · MCP / 工具五分类 / 异步 → ch4 · 代码 / 元能力 → ch5 · 评估 / LLM-as-a-Judge → ch6 · SFT / RL / RLVP → ch7 · 自我进化 / 工具创造 → ch8 · 语音 / Computer Use / VLA → ch9 · 多 Agent / 验证器 / Agent 社会 → ch10 · 模型吃掉 Harness / 两朵乌云 → 后记

## 不确定时的回答方式
结论标注出处章；跨章对比分别给出各章位置；区分作者原文（用 source 层）与本层衍生解释。

## 支持文件
overview / glossary / patterns / cheatsheet / index 均在 `references/`。
