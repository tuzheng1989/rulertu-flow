# Hybrid 模式

## 目标

对内容性质不同的章节选择性组合 faithful、knowledge、methods。Hybrid 不是默认生成三份全书，而是先确定每个组件的范围和用途，只产出能够增加价值的部分。

## 必须先确认计划

执行前读取 `references/mode-selection.md`，基于 `assets/build-plan.template.json` 生成计划并展示给用户。计划必须说明：

- 选中了哪些组件。
- 每个组件处理哪些章节或主题。
- 每个组件解决什么任务。
- 为什么排除其他组件或章节。
- 预计生成哪些独立 Skill。

用户确认后把计划视为契约；范围变化时重新确认。

## 产物

```text
<book-slug>-skill-pack/
├── PACK_INDEX.md
├── build-plan.json
└── skills/
    ├── <book-slug>-source/        # 仅选 faithful 时
    │   ├── SKILL.md
    │   └── references/
    ├── <book-slug>-knowledge/     # 仅选 knowledge 时
    │   ├── SKILL.md
    │   └── references/
    └── methods/                   # 仅选 methods 时
        ├── <method-a>/
        └── <method-b>/
```

Pack 根目录用于交付和审计，不作为一个可安装 Skill。每个叶子 Skill 必须可以独立复制到宿主 skills 目录。

## 组合规则

### Faithful + Knowledge

适合技术教材、复杂专著或既要精确依据又要快速理解的内容。

- faithful 保存完整或明确选定的权威章节。
- knowledge 只压缩解释密集、适合概念导航的章节。
- knowledge 结论需要核对时，指示用户使用 source Skill；不要依赖安装后可能失效的相对跨目录链接。

### Faithful + Methods

适合规则书、专业手册和含明确操作流程的标准。

- faithful 保存规则、阈值、例外和上下文。
- methods 只提炼真正可执行的流程、检查表或决策程序。
- 方法 Skill 不得简化会改变执行结果的规则；`references/evidence.md` 自包含必要证据和来源位置。

### Knowledge + Methods

适合方法型非虚构、课程和访谈。

- knowledge 提供全书知识地图。
- methods 只交付通过验证的可执行单元。
- 不把每个章节摘要再次复制到每个方法 Skill。

### 三种组合

仅在三类需求都明确且分工清晰时使用。例如专业教材既含权威公式、解释性理论，又含稳定求解流程。逐章节指定范围；不能用“可能有用”作为全量生成理由。

## 内容隔离

- faithful references：来源内容。
- knowledge references：模型生成的解释和压缩。
- method Skills：模型生成的触发器和执行程序。

三层必须在标题和说明中明确身份。模型衍生内容永远不进入 faithful references。

## 去重和独立性

- 同一来源片段可以作为不同层的依据，但不要复制相同的长篇文字。
- Knowledge Skill 负责解释“是什么和为什么”；Method Skill 负责“何时用和怎么做”。
- Method Skill 必须自包含运行所需内容，不能假设 Source 或 Knowledge Skill 一定安装。
- `PACK_INDEX.md` 列出每个叶子 Skill 的用途、安装路径、推荐组合和未生成内容。

## 执行顺序

1. 统一提取一次，所有组件共享规范化语料。
2. 若包含 faithful，先生成并验证来源层。
3. 生成 knowledge 组件。
4. 生成 methods 组件并压力测试。
5. 对照 `build-plan.json` 检查计划覆盖、计划外产物和重复内容。
6. 生成 `PACK_INDEX.md`，只列通过验证的叶子 Skill。

