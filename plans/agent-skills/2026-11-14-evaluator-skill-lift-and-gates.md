# agent-evaluator：Skill Lift 配对评测与分层门禁显式化

- 日期：2026-11-14
- 插件：agent-skills（agent-evaluator，1.5.0 → 1.6.0）
- 方案来源：NVIDIA/SkillEvaluator（论文 *Evaluating Skills, Not Just Agents*）调研启示
- 状态：待评审

## 一、背景与目标

### 1.1 SkillEvaluator 的五个可借鉴机制

NVIDIA SkillEvaluator 是 skill 工件质量评测框架，三层递进（Tier 1 静态安全扫描硬门禁、Tier 2 去重、Tier 3 实测增益）。与本方案相关的五个机制：

1. **Skill Lift 配对试验**（Tier 3）：同一 agent 在 with-skill 与 without-skill 两种条件下跑同一评测集，差值即 skill 的行为增益。把「我觉得这个 skill 有用」变成可测量的因果论断。
2. **autopilot 缺省行为**：评测集不存在时自动生成 starter case 并跑通全流程，同时明确警告覆盖率有限。
3. **分层门禁语义**：Tier 1 硬门禁，Tier 2 默认 gate 可放宽为建议，Tier 3 默认建议可收紧为门禁。每层「有没有一票否决权」显式声明。
4. **负例缺省缺席警示**：评测集模板默认不含负例，作者必须在评测定义中显式写。把「负例容易忘」做成机制提醒。
5. **doctor 就绪检查**：依赖外部环境的方式入口先自检，避免跑到一半发现环境缺失。

### 1.2 agent-evaluator 现状空白

| 空白 | 现状 | 后果 |
|------|------|------|
| 无 Skill 配对评测 | 「边缘情况 > 用户要求对比两个 Agent」只有 A/B 对比（两个不同 Agent 各跑一遍） | 「某 skill / 某工具 / 某段提示词对 Agent 的贡献」无法量化 |
| 快速通道仍需逐阶段确认 | 阶段流程每步有确认门禁，快速通道只是精简指标 | 轻量场景「帮我快速看看」摩擦大 |
| 门禁属性隐式 | 判定漏斗（expect → L1 → L2 → L3）只解决短路省 token；Safety 一票否决明确，但 L2 综合分、L3 抽检是建议还是否决未声明 | 报告读者不知道哪些数字有否决权 |
| 负例输入无占比要求 | dataset-schema「分布均衡」一句话带过；「Negative case（拦截验证）」节是 Harness 元测试，不是负例输入 | 评测集默认偏正例，拒答、澄清、承认局限的能力测不出 |
| deepeval 无环境自检 | deepeval-bridge.md 开头直接进决策树 | 方式 B 跑到一半才发现 Python 环境缺失 |

### 1.3 目标与边界

五项改动全部落在 agent-evaluator 技能内，纯 prompt 工件改动，不引入代码、不引入依赖、不改五阶段编号。配套完成双 manifest 升版与 CHANGELOG。

## 二、改动清单

### 改动一：Skill Lift 配对评测（核心）

**动机**：阶段 4 只测「装了某组件的 Agent 表现如何」，从未回答「这个组件的贡献是多少」。rulertu-flow 自身的 agent-skills 体系（evaluator、jev-agent-design、deepagents 等）质量取舍都需要这个测量。

**概念区分**（需写进 SKILL.md，避免与既有 A/B 对比混淆）：

| | A/B 对比（既有） | Skill Lift（新增） |
|---|---|---|
| 比什么 | 两个不同 Agent（agent-v1 vs agent-v2） | 同一个 Agent 的两种配置 |
| 配置差异来源 | Agent 本体不同 | 装或不装某 skill、开或关某工具、加或不加某段提示词 |
| 回答的问题 | 哪个 Agent 更好 | 这个组件值不值得存在 |

**设计决策：复用 variant 字段，不新增 schema 字段。**

- `variant` 已支持任意字符串标识（dataset-schema.md:47）。配对评测约定 variant 取值 `with-{组件名}` 与 `without-{组件名}`。
- 同一评测集（同 case id 集合）在两条件下各跑一遍，原始结果分目录存放（`raw-with-X/`、`raw-without-X/`）。
- 取舍：新增 `condition` 字段语义更精确，但多一个概念且与 variant 功能重叠；复用 variant 零 schema 结构改动，文档说清约定即可。选后者。

**落点与具体改法**：

1. **SKILL.md「边缘情况」**：「用户要求对比两个 Agent」一条扩展为「用户要求对比评测」两条：A/B 对比保持原文；新增「用户要求评测某组件（skill/工具/提示词段）的贡献」，给出配对流程（同一评测集、两条件、同判定漏斗、同 k 值）。
2. **SKILL.md 阶段 4**：方式 A 末尾加「配对执行」小段。两条件必须用同一评测集与同一判定漏斗，唯一变量是被测组件的开关；建议 k 值一致（默认 k=3），否则 lift 被运行次数差异污染。
3. **SKILL.md 阶段 5 报告模板**：新增 Skill Lift 板块：

```markdown
## Skill Lift（仅配对评测时输出）

| 指标 | with-{X} 均分 | without-{X} 均分 | Lift | 判读 |
|------|--------------|-----------------|------|------|
| Correctness | x.xx | x.xx | +x.xx | 有效/无感/有害 |
| ... | ... | ... | ... | ... |

- 组件贡献结论: {一句话，明确「装/不装」建议}
- 置信说明: {评测集条数、k 值、噪声提示}
```

**Lift 计算口径**（写进 SKILL.md 阶段 5）：

- 指标级：lift = with 条件指标均分 − without 条件指标均分。
- 通过率级：lift = with 条件通过率 − without 条件通过率。
- 一致性场景：pass@k 与 pass^k 在两条件下分别计算后作差。
- 判读基准：lift 显著为正，组件有效；lift 接近 0，组件无感，建议移除省 token 与维护成本；lift 为负，组件有害，必须人工复查原因。
- 置信警示：本 skill 推荐 20-55 条的小评测集上，绝对值 0.2 以内的 lift 不宜下强结论，报告必须标注置信有限。

### 改动二：autopilot 最小起跑

**动机**：SkillEvaluator 在评测集缺席时自动造 starter case 跑通全流程，且明确警告覆盖局限。agent-evaluator 的快速通道仍要求用户走完阶段确认，轻量场景摩擦大。

**设计决策：显式授权才生效，不废除确认门禁。**

- 触发条件：用户明确说「自动跑」「别问我」「autopilot」「直接给我结果」时生效。未授权时维持现有确认流程。
- 行为：自动推导评测维度（L1 四指标加 1-2 个最相关 L2 指标），自动生成 3-5 条 starter case，内联跑通，出精简报告。
- 双保险：报告顶部固定标注「starter case 由 AI 自动生成，覆盖率有限，不可作为上线门禁依据」；评测维度与全部用例在报告中完整列出，供人工复核后决定是否转正为正式评测集。

**落点**：

1. SKILL.md「快速通道」加第 0 步「自动起跑（须用户显式授权）」，写明触发词、行为与报告标注义务。
2. SKILL.md NEVER 首条加豁免句：「NEVER 在没有确认评测方案的情况下直接开始评测。用户显式授权自动起跑时除外，此时评测维度自动推导，并须在报告中完整声明。」

**不做**：不模仿 SkillEvaluator 自动建 Docker 沙箱跑 provider 原生 agent。autopilot 的终点是精简报告，执行方式仍是阶段 4 方式 A 的内联/subagent 跑法。

### 改动三：门禁属性显式化（gate / advisory）

**动机**：判定漏斗解决了「前置层失败短路省 token」，没解决「谁有一票否决权」。Safety 已是一票否决，但 L2 综合分、L3 人工抽检在流程中的门禁属性未声明，报告读者无法判断哪些数字能拦住发布。

**设计：两值属性，逐层声明，默认值加可调规则。**

| 层 | 默认属性 | 语义 | 调整规则 |
|----|---------|------|---------|
| Safety | gate（固定） | 任一 case 不通过，整场评测标红，报告醒目列出 | 不可调 |
| expect 门槛 | gate | 失败即短路记 FAIL | 由数据集作者逐 case 定义 |
| L1 | gate | 结构性错误即 FAIL | 可在评测方案中降为 advisory（如格式瑕疵只扣分不否决） |
| L2 综合分 | advisory | 只进报告排序与结论，不作否决 | 可升格 gate：评测方案声明阈值（示例：综合加权分 ≥4.0 且任一指标不低于 3） |
| L3 抽检 | advisory | 抽检意见写入报告供参考 | 争议 case 可声明人工裁决为最终判定（升格 gate） |

- gate：一票否决，失败即判 FAIL 或阻断发布结论。
- advisory：记分进报告、写进结论建议，无否决权。

**落点**：

1. evaluation-methodology.md「判定漏斗」执行顺序表加「门禁属性」列；表后加「门禁属性声明」小节：两值定义、逐层默认值、升格与降格规则、声明位置（Evaluation Plan 的「门禁声明」行）。
2. SKILL.md 阶段 1 Evaluation Plan 模板「评测约束」加一行「门禁声明」。
3. SKILL.md 阶段 4 判定漏斗引言加一句：每层门禁属性见 `references/evaluation-methodology.md`，默认 L2 与 L3 为 advisory，可在评测方案中升格。

### 改动四：负例输入占比建议

**动机**：SkillEvaluator 把「负例容易忘」做成机制提醒。agent-evaluator 的 `must_not_include` 与 expect 管的是输出侧约束，评测集本身缺「应拒绝、应澄清、应承认做不到」的负例输入，Agent 的判断力测不出。

**概念区分**（写进 dataset-schema.md，消除与既有「Negative case（拦截验证）」节的混淆）：

| | 负例输入（新增建议） | Negative case 拦截验证（既有） |
|---|---|---|
| 测的对象 | 被测 Agent | 评测 Harness 自身 |
| 是什么 | 应被拒绝、应澄清、应承认局限的输入请求 | 预填 actual_output 的元测试，验证 expect 门槛真能拦截 |
| 存放位置 | 正常 cases 列表中，category 或 tags 标注 | 独立的 negative 拦截验证条目 |

两者对象不同，互不替代，都应保留。

**落点**：

1. SKILL.md 阶段 2 构建策略加第 6 条「负例输入覆盖」：建议占比不低于 20%，类型含超出能力边界的请求、缺关键参数的模糊请求、越权或危险操作请求、依赖不存在资源的请求。
2. dataset-schema.md「设计最佳实践」表「分布均衡」行的说明补具体比例；「Negative case」节开头加一句与负例输入的区分，并指向阶段 2 构建策略。

### 改动五：doctor 环境自检

**动机**：方式 B 依赖 Python 环境与 deepeval 包，当前 deepeval-bridge.md 无入口自检，跑到一半才发现环境缺失。

**落点**：

1. deepeval-bridge.md 开头（决策树之前）加「环境自检」小节：
   - `python --version`（版本要求随 deepeval 官方说明）
   - `python -c "import deepeval; print(deepeval.__version__)"`
   - 任一失败时的安装指引（`pip install deepeval`）与「改用方式 A」的降级提示。
2. SKILL.md 阶段 4 方式 B 处加一句：使用前先跑 `references/deepeval-bridge.md` 的环境自检。

## 三、不做的事

- **Docker 沙箱、provider 原生 agent 编排、CI dashboard**：SkillEvaluator Tier 3 的重型工程路线，与 agent-evaluator「Prompt-as-Code、零部署」核心理念冲突，不引入。
- **Skill 静态准入扫描**（Tier 1 风格的 frontmatter 规范、触发词冲突、危险模式检查）：属独立的 skill 准入需求，不塞进 agent-evaluator，将来单独立项。
- **新增 schema 结构字段**：Skill Lift 复用 variant，负例输入用现有 category 与 tags 承载，均不加字段。
- **报告模板大改**：仅加 Skill Lift 板块，其余板块不动。

## 四、配套变更

1. 双 manifest 同步升版：`plugins/agent-skills/.claude-plugin/plugin.json` 与 `plugins/agent-skills/.codex-plugin/plugin.json`，1.5.0 → 1.6.0。manifest 描述文字不动（「评测 Harness 构建」已覆盖新能力）。
2. 仓库根 CHANGELOG.md Unreleased 加条目，按仓库惯例详述五项改动与落点。
3. README.md 技能清单行不动。

## 五、实施顺序与验证

**实施顺序**：改动三（methodology 漏斗表，其他改动引用它）→ 改动一（SKILL.md 对比节与阶段 4/5）→ 改动二（快速通道与 NEVER）→ 改动四（阶段 2 与 schema 最佳实践）→ 改动五（deepeval-bridge）→ 配套升版与 CHANGELOG。

**验证方式**（prompt 工件，无单元测试可跑）：

1. 交叉引用自检：grep 核对新增文字引用的文件名与章节名（`references/*.md`、模板编号、「Negative case」节名）真实存在。
2. 一致性核对：五阶段编号与各阶段门禁文字未漂移；NEVER 豁免句与快速通道授权条件互洽；schema 的 variant 说明与 SKILL.md 配对口径一致；「Negative case」区分句与阶段 2 构建策略口径一致。
3. 冒烟实测（建议，实施后进行）：任选一个小 skill 作被测组件，按新流程跑一次最小 Skill Lift 配对（3-5 条 case，两条件，k=3），确认报告 Skill Lift 板块可产出且置信说明生效。

## 六、风险与不确定点

1. **autopilot 与确认门禁的张力**：已设计为显式授权加报告声明双保险。若实际使用中仍嫌越界，可降级为半自动形态（自动生成 starter case 草稿，确认后再跑）。
2. **Skill Lift 统计功效有限**：20-55 条小评测集上的 lift 噪声大。方案以「绝对值 0.2 以内不下强结论」为经验值，无硬统计标准，待真实跑批数据积累后校准。
3. **门禁升格阈值是示例值**：L2 升格的「综合加权分 ≥4.0」为默认示例，不同业务需在评测方案中自行声明，文档将写明示例属性，避免被当作规定。
