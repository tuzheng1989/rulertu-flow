---
name: ai-agent-design-source
description: 《深入理解 AI Agent：设计原理与工程实践》（李博杰）原书全文可检索来源。当需要逐字核对 Agent 设计原话、精确依据（MCP 协议细节、API 消息结构、SFT/RL 算法、评估指标定义、ReAct / proposer-reviewer 原始表述），或确认 ai-agent-design-knowledge / methods 层结论的出处时使用。触发词：原文、出处、逐字、精确引用、书上怎么说、第 N 章。
---

# ai-agent-design-source · 原书全文来源

《深入理解 AI Agent：设计原理与工程实践》——李博杰（Pine AI 首席科学家）。
原书 10 章 + 引言 + 后记，按章 + `##` 子节切分，共 **92 个子节**。此 skill 只保留来源文本，不做摘要、不补写书外知识。

## 知识边界

只收录这一本书的内容。问题超出本书范围时，明确说明"本书未覆盖"并追问，不凭记忆补写。

## 检索顺序（从粗到细，渐进定位）

1. 先读 [references/index.md](references/index.md) —— 全书 12 章地图，每章标注子节数。
2. 选定章后读章主文件 `references/<NN>-<title>/<NN>-<title>.md` —— 含章首概述 + 「子章节」索引。
3. 按子章节索引进入最具体子节 `references/<NN>-<title>/<NN>.<MM>-<section>.md`。
4. 在子节文件内用关键词定位原文；图片在 `references/images/`。

## 关键章节速查（主题 → 章）

- 核心公式 Agent = LLM + 上下文 + 工具、Harness 工程：00-引言、01-AI Agent 入门
- KV Cache、上下文压缩、Skills 按需加载、状态栏：02-上下文工程
- 用户记忆、RAG、知识图谱、Agentic RAG：03-用户记忆和知识库
- MCP 协议、工具五分类、执行工具安全、异步 Agent：04-工具
- Coding Agent、OpenClaw 架构、代码生成元工具：05-Coding Agent 与代码生成
- 评估环境、指标、LLM-as-a-Judge、统计显著性：06-Agent 的评估
- 预训练/SFT/RL 三阶段、奖励信号设计：07-模型后训练
- 三种学习范式、经验学习、工具创造、MCP-Zero：08-Agent 的自我进化
- 语音三范式、Computer Use、机器人 VLA、Sim2Real：09-多模态与实时交互
- 多 Agent 协作分类（上下文共享/独立 × 对等/管理者/去中心化）：10-多 Agent 协作

## 术语约定（作者专门区分，核对时务必注意）

- **reasoning →「思考」**：思维链、思考模型（o 系列、DeepSeek-R1）、思考过程
- **inference →「推理」**：模型运行、推理时、推理成本、推理时扩展
- 例外复合词仍用「推理」：逻辑推理、多跳推理、空间推理、时序推理（指演绎推断，非 inference）

## 冲突与覆盖顺序

本书非规则手册，冲突较少；遇表述差异时：① 更深层子节优先于章首概述；② 后记对全书的总结性论断可作为作者最终立场的参照。

## 交付前检查

- 引用原文标注章节号（如 ch7 7.3）。
- 区分作者原文与读者推断；此 skill 只交付作者原文。
- 跨章节对比时，分别给出各章原文位置，不混写。
