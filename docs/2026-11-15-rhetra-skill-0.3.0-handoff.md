# rhetra 技能 0.2.0 → 0.3.0 对齐 handoff

状态：交接文档（2026-11-15）。本文件是给执行技能更新的会话的完整交接——变更调研已做完，含逐文件修改点、一个待拍板的决策点与验收清单。技能更新落地后本文件退为记录，无需维护。

## 背景

rhetra 技能（`plugins/agent-skills/skills/rhetra/`）版本锚点是 rhetra 0.2.0（2026-11），而 rhetra-harness 仓库（`tuzheng1989/rhetra-harness`）已发布 **v0.3.0**（tag 指向 f0cd669）。技能的规矩是"若包行为与本文档冲突，以源码为准并更新本技能"，本次更新即履行该条款。

调研结论：顶层 `__all__` 27 符号在 v0.2.0 与 v0.3.0 **完全一致**（0.x 兼容承诺未动），技能主干仍准确；失真集中在安装锚点、`run_flow` 签名两处硬伤，外加 0.3.0 主体新特性 skillref 子系统的覆盖决策。

## 锚点纪律

- 技能对齐 **v0.3.0 tag（f0cd669）**，不要对齐 master。master 上 tag 之后还有 3 个未发版提交，**均不进本次更新**（描述了 pip 装不到的行为）：
  - e1f829b `run_flow` task 形态新增 `hints` 透传参数——留给下一版
  - ab09651 planner 契约预检进草案环——留给下一版
  - c686013 `__version__` 改为动态读分发元数据——技能不描述 `__version__` 行为细节，无需动作
- 安装命令统一锁 `@v0.3.0`，wheel 文件名 `rhetra-0.3.0-py3-none-any.whl`。

## 变更对照（v0.2.0 → v0.3.0）

### 不变项（更新时勿动）

- 顶层 `__all__` 27 符号：两版本逐一比对一致，`python-api.md` 的符号清单与"27 符号"表述保留。
- 三类 Step、五类 transition、context 块、冻结契约、证据 Bundle 结构、verify 三态、离线替身与三层断言纪律——均未变。

### 硬失真（必须改）

| 位置 | 问题 | 改法 |
|---|---|---|
| `SKILL.md:12` | 锚点行"基于 rhetra 0.2.0" | 改 0.3.0 |
| `references/quickstart.md:3` | 锚点行 0.2.0 | 改 0.3.0 |
| `references/quickstart.md:27` | 安装命令 `@v0.2.0` | 改 `@v0.3.0` |
| `references/quickstart.md:30` | wheel 路径 `rhetra-0.2.0-py3-none-any.whl` | 改 0.3.0 |
| `references/quickstart.md:47` | "锁定 tag（如 v0.2.0）"示例 | 随手改 v0.3.0 |
| `references/python-api.md:7` | `run_flow` 签名缺 `transforms` | 见下"transforms 参数要点" |

### transforms 参数要点（票 #9，python-api.md 补写依据）

源码出处：`rhetra/api.py` 的 `run_flow` docstring（v0.3.0）。写入技能时压缩为与现有条目同密度：

- 形态：`transforms: dict[str, Callable[[dict], dict]] | None`，键为快照 implementation 键，值为 `(dict) -> dict` 函数。
- 语义：mode 装配产出后逐键注册进 TransformRegistry；**注入键覆盖包内同名键**（消费方显式意图优先）。
- 冻结无关性：transform 函数不进冻结体，`frozen_execution_hash` 与注入无关——这是"证据账本不含函数体"纪律的自然延伸，值得写明。
- 校验：非 dict / 键非 str / 值不可调用，在装配前拦截（异常外显）。

### 新特性零覆盖（见决策点）

- **skillref 子系统**（0.3.0 主体，`rhetra/skillref/` 新增六模块）：manifest 解析（`SkillManifest` / `build_manifest` / `load_manifest`，目录准入校验 + 链接逃逸检查）、组级/叶级候选投影、Jev 判定与弃权收敛循环（`TypeSafeJudger` 真实通道 / `ScriptedJudger` 离线替身）、`SkillRefLoaderTool`（tool 步协议同构）、双 lane 注册表（实现前缀 `skillref/`；auto lane 走 typesafe，offline lane 仅 scripted）。
- **viewer**：白名单放行 `artifacts/<hex>` + 新增 spill 产物审查卡（`evidence.md` Viewer 段）。
- **planner**：skillref 三段式编排范式进 prompt 骨架示例与准入校验（`planner.md`）。

## 决策点：skillref 覆盖粒度

skillref 不在顶层 `__all__` 承诺内，消费入口分散在 flow.yaml（tool 步实现前缀 `skillref/...`）与 planner 范式两处。三选一：

- **A. 本次不进技能**——等消费面成熟。代价：用户在 0.3.0 上写 `skillref/` 前缀的 flow 时技能无指引。
- **B. 轻量挂载（建议）**——`flow-definition.md` tool 步段落加一小节（实现前缀 `skillref/` 的含义、offline lane 只有 scripted 替身的事实）；`planner.md` 提一句三段式编排范式。不新增场景、不新增参考文档。
- **C. 完整覆盖**——新增第六场景 + `references/skillref.md`（manifest 结构、判定阈值、双 lane）。代价：技能膨胀约一倍，且 skillref 公开面尚未做兼容承诺，下版变动风险高。

建议 B 的依据：技能五场景按**用户意图**划分（接入/写 flow/planner/证据/测试），用户带着 skillref 需求进来时的意图就是"写 flow"或"planner 编排"，挂在这两处即可命中；等 skillref 公开面稳定（进 `__all__` 或有外部消费方）再升 C。

## 验收清单

1. `grep -rn "0\.2\.0" plugins/agent-skills/skills/rhetra/` 零命中（历史对照除外）。
2. 技能内 `run_flow` 签名与 `git -C <rhetra-harness> show v0.3.0:rhetra/api.py` 的 `def run_flow` 一致：**有 `transforms`、无 `hints`**。
3. `python-api.md` 符号清单与 `git show v0.3.0:rhetra/__init__.py` 的 `__all__` 逐一对应（27 个）。
4. 若采纳决策点 B：`flow-definition.md` 含 `skillref/` 前缀说明，`planner.md` 含三段式提及。

## 附：落地通道

- 只改本仓库（marketplace 源）；`~/.claude/plugins/cache/rulertu-flow/agent-skills/1.6.0/` 是安装副本，不手改，经插件更新机制刷新（技能内容更新是否伴随插件版本 bump，按本仓库 agent-skills 的发版惯例定）。
- 更新完成提交时，commit message 走本仓库 `rulertu-flow:commit` 技能起草。
