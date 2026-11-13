# B2 主控修复裁定与处置记录（双重验证后）

日期：2026-11-13。主控综合 Auditor（契约审计：通过，P0/P1/P2=0）与第二意见（冷启动可用性：修后可用，2 高 5 中）的报告，裁定如下。

## 分歧实质与裁定

Auditor 从委派单契约字面验收判"工作区无需修正"；第二意见从真实执行推演发现 evoCenter 时代残留语义使 compose 主路径在本仓必死。裁定：**契约实质缺陷（验收 3"自包含"的违反）属 B2 范围，本批修复；纯随迁资产保持 rename 可审计，其内容缺陷与打磨项记 B3。**

## 本批修复清单（主控直接实施，8 处）

| # | 修复 | 文件:位置 | 对应问题 |
|---|---|---|---|
| A | 输入入口统一：三件套为主入口（补语义对应），旧工作流四件套降为兼容条款（标注来源与读法）；无材料时加路标（创作型→引擎创建模式；研究报告→引导 deep-research） | modes/compose.md 输入入口节 + 适用模式节 | 问题2 + 问题1 |
| B | AI 配图条件化：能力存在性前置判断（如 agnes-image / sn-image-base 或同类），删除死路径命令块 `python3 /scripts/sn_agent_runner.py`，调用方式改为按所选技能接口适配 | modes/compose.md AI 配图节 | 必修① |
| C | visual_plan 落点定义：终稿生成 `{report_dir}/visual_plan.md`；写作修改与输出文稿同目录 | modes/compose.md 视觉计划文件节 | 问题3 |
| D1 | 引擎创建模式触发词消歧：去"写个报告"，改"手册/教程/书稿"+注记报告类优先 mode 路由 | SKILL.md frontmatter | 问题1 |
| D2 | 裁决句补泛化"写个报告"三分支（研究报告→deep-research 引导；创作型→引擎；不明→询问） | SKILL.md 与引擎的分流段 | 问题1 |
| D3 | 判断流程导入分支消歧："从...开始"→"从<某份文档>开始"、"基于..."→"基于<现有文档>"（与"从零开始"解冲突） | SKILL.md 模式判断流程图 | 场景5【中】 |
| E | report_shape 通用化："嵌入 deep research：为 plan.json.report_shape…"→"嵌入上游工作流：…（以其实际约定的载体为准）" | modes/format.md 双重定位 | 问题2 |
| F | meta-web 依赖注记：本仓优先 url-to-md 技能或 MCP web-reader，meta-web 为旧环境依赖 | references/engine/import-mode.md 2.2 节 | 问题4 |
| G | Long-Text 术语说明行：引擎文件中 Long-Text 范式/系统字样同义注记 | SKILL.md Subagent 架构段尾 | 问题5（低成本消解） |

修复后复跑验收：互引 grep 零命中 ✓；死路径（sn_agent_runner）零残留 ✓；SKILL.md 122 行 ≤ 200 ✓；sn-image-base 仅存于条件化举例（非死依赖）✓。

## 记 B3 待办（追加，源自双重验证）

- import-guidelines.md（纯随迁资产）:79/:89/:104 的 meta-web 引用更新
- 引擎层 long-text 术语清扫：.claude/agents 四文件自称、merge.py docstring、import-mode.md 残留字样（现已有 SKILL.md 同义注记兜底，不阻断）
- examples/import-example/README.md:178 旧布局命令路径 `scripts/long-text/scripts/merge.py` → `scripts/merge.py`
- audit.md :11/:34 默认路径 `workspace/reports/` 加"deep-research 产物根"注记；:84 "项目记忆偏好"表述本地化
- Subagent 启动机制统一：import-mode.md 的 general-purpose+内联提示词 vs .claude/agents 定义，二选一收敛
- 引擎工作区根路径两套并存（`workspace/{project-name}` 与导入模式根）在 SKILL.md 工作区概念节显式化
- Auditor P3-1（workspace-and-files.md 缺空行）、P3-2（映射表补"创建 vs 编辑"小表去向标注）随手修

## 未采纳 / 记档

- 第二意见场景 4（"基于这份报告改写"误入导入模式）：已有 :51 事后裁决可恢复，D1/D3 已降低误触发概率；不做更深重构。
- Auditor P3-4（sn-image-base 引用）：已由本批修复 B 直接解决（条件化+删死路径），B3 无需再处理。
- CRLF/LF 混合（P3-5）：git 提交规范化，不处理。
