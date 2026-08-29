---
name: ai-agent-design
description: 《深入理解 AI Agent：设计原理与工程实践》（李博杰）统一入口——AI Agent 设计百科、原文来源与可执行方法库。当用户涉及 Agent 设计、上下文工程、Harness、ReAct、proposer-reviewer、工具 / MCP、Agent 评估、SFT / RL、多 Agent 协作、自我进化、Coding Agent 等任何 agent 主题时使用。本 skill 是路由器：先判断用户意图，再索引到 pack 内 knowledge（百科）/ source（原文）/ methods（可执行方法）/ examples（现实项目参考）/ practices（书外工程实践）五个组件。触发词：agent 设计、agent 原理、上下文工程、harness、react、mcp、agent 评估、sft rl、多 agent、agent 百科、proposer-reviewer、kv cache、agent 工具、agent 选型、竞品 agent、有哪些 agent、现实实现、agent 示例、awesome ai agents、协调结构、生成器验证器、协调器子代理、代理团队、消息总线、共享状态、agent coordination pattern、有哪些 agent 工程模式。
---

# ai-agent-design · Agent 设计统一入口

《深入理解 AI Agent：设计原理与工程实践》（李博杰 / Pine AI 首席科学家）的顶层路由 skill。本书核心公式：**Agent = LLM + 上下文 + 工具**。

本 skill **不重复内容，只做分发**——先判断用户意图，再索引到 `ai-agent-design-pack` 内五个组件。knowledge / source / methods 三个组件所有内容仅来自这一本书，不补写书外知识；examples 为外部现实项目参考（来自 `slavakurilyak/awesome-ai-agents`），practices 为外部工程实践层（书外 agent 协调模式等），二者皆不纳入本书知识体系。

## 路由决策（先判断意图，再按路径读取）

### 意图 1：查询 / 理解 / 对比 / 决策（最常见）
特征：「X 是什么」「怎么选」「对比 A 和 B」「Agent 如何做 Y」「书上讲没讲 X」。
→ 读 **knowledge 百科层**（`pack/skills/ai-agent-design-knowledge/references/`）：
- 全貌：`overview.md`（骨架 + 6 条核心判断 + 章节地图）
- 术语：`glossary.md`（含 reasoning=思考 / inference=推理 区分）
- 对比：`patterns.md`（11 个对比 / 因果 / 权衡框架）
- 决策：`cheatsheet.md`（决策规则速查）
- 某章：`chapters/chXX-*.md`（按 `index.md` 主题索引定位）

### 意图 2：逐字核对原文 / 精确引用
特征：「书上怎么说」「原文」「出处」「第 N 章」「精确依据」「作者原话」。
→ 读 **source 原文层**（`pack/skills/ai-agent-design-source/references/`）：
- 从 `index.md` → 章主文件 → 子节（12 章 / 92 子节，渐进定位）。原书插图未随插件分发，仅有文字内容。

> ⚠️ **原文引用纪律（硬约束）**：凡用引号引用、或声明「原话 / 原文 / 书上原话」，**必须实际打开 source 层对应子节文件，逐字照抄**；绝不可凭记忆改写，更不可用 knowledge 层的衍生压缩表述包装为原文。knowledge 是衍生解释、source 才是逐字原文，身份不同，引用时不得混用。不确定就如实说明「未逐字核对」，绝不伪造引文。

### 意图 3：执行 / 实现 / 动手做
特征：「怎么写 / 实现 / 构建 / 设计」某具体东西。
→ 读对应 **method 方法 skill**（`pack/skills/methods/skills/<method>/SKILL.md`）：

| 要做的事 | 读这个 method |
|---|---|
| 构建 Agent 主循环 | `ai-agent-design-react-loop` |
| 判定任务完成 / 防假成功 / 过早放弃 | `ai-agent-design-proposer-reviewer` |
| 优化上下文 / 提示词膨胀 / KV Cache | `ai-agent-design-context-engineering` |
| 评估 Agent / 选型 / 判断改动真伪 | `ai-agent-design-eval-driven-iteration` |
| 设计工具 / MCP / 异步事件驱动 | `ai-agent-design-tool-design` |
| SFT vs RL 选型 / 奖励信号设计 | `ai-agent-design-sft-vs-rl-selection` |
| 用代码思考 / 创造工具 / Agent 自举 | `ai-agent-design-coding-as-meta-tool` |

每个 method 含触发条件、执行步骤、完成 / 判停标准、边界、证据链。

### 意图 4：现实参考 / 竞品 / 选型
特征：「有哪些现成的 X agent」「某类 agent 已有实现」「技术选型」「竞品」「已有项目怎么做的」。
→ 读 **examples 现实参考层**（`pack/skills/ai-agent-design-examples/references/`）：
- 先 `index.md` 命中 35 分类之一，再读 `categories/<分类>.md` 看项目清单（描述 / 开源 / 链接 / stars）。

> ⚠️ **外部参考，非本书内容**：examples 数据来自 `slavakurilyak/awesome-ai-agents` 静态快照，只回答「有什么实现」，不回答「为何这么设计」。设计原理仍查 knowledge / source / methods。

### 意图 5：工程模式选型 / 书外实践
特征：「选哪种多 agent 协调结构」「工程上别人怎么搭 multi-agent」「有没有现成的 agent 协调模式」「生成器-验证器 / 协调器-子代理怎么选」。
→ 读 **practices 书外工程实践层**（`pack/skills/ai-agent-design-practices/references/`）：
- 先 `index.md` 命中五种协调模式之一，再读对应模式文件（架构图 / 适用场景 / 设计考虑 / deepagents 落地示例）。

> ⚠️ **书外工程实践，非本书内容**：practices 收纳工程社区模式，回答「有哪些做法、选哪种、怎么落地」，不回答原理（为何这么做仍查 knowledge / source / methods）。

## 五步使用法（不确定时）
1. **不知道是什么** → knowledge `overview.md` 建立全局认知。
2. **要精确引用** → source 按章 / 子节定位原文。
3. **要动手实现** → 选 method，按其 `E` 节步骤执行。
4. **要看现实实现 / 选型** → examples `index.md` 命中分类，读对应项目清单。
5. **要选协调结构 / 工程模式** → practices `index.md` 命中五种模式，读对应模式文件。

## 6 条核心判断（全书最高密度，可直接给出）
1. 好的设计原则穿越模型迭代周期。
2. 实践在前，命名在后。
3. Harness 是竞争力（模型商品化时代的差异）。
4. 没有评估就没有进步。
5. 数据和环境比算法更重要。
6. 循环的瓶颈在验证器（proposer-reviewer）。

## 主题速查（→ 组件 / 章）
核心公式 / Harness / 编排 → knowledge ch00 / ch01 / 后记 · KV Cache / 压缩 / Skills → ch02 · 记忆 / RAG → ch03 · MCP / 工具五分类 / 异步 → ch04 · 代码 / 元能力 → ch05 · 评估 / LLM-as-a-Judge → ch06 · SFT / RL / RLVP → ch07 · 自我进化 → ch08 · 语音 / Computer Use / VLA → ch09 · 多 Agent / 验证器 → ch10（原理）；协调模式选型 / 工程落地 → practices 层 · 模型吃掉 Harness / 两朵乌云 → 后记

## 术语快查
**reasoning = 思考**（思维链 / 思考模型），**inference = 推理**（模型运行 / 推理成本），勿混。详见 knowledge `glossary.md`。

## 边界
本 skill 是路由器；具体内容由五组件承载。用户要现实实现 / 选型参考时转 examples（外部数据），要协调结构 / 工程模式选型时转 practices（书外工程实践）；其余超出本书范围的需求，明确说明「本书未覆盖」并追问，不凭记忆补写。
