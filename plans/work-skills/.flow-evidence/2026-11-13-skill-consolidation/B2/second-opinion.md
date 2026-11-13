# B2 独立第二意见评审（冷启动可用性）

说明：第二意见代理只读契约未落盘，本报告由主控原样落盘（全文无增删）。总体判断：**修后可用**，必修 2 项 + 建议 5 项已于当日由主控处置（见 master-remediation.md）。

# write-report 冷启动第二意见评审（只读）

评审对象：plugins/work-skills/skills/write-report/。以下行号均为当前工作区文件实测。

## 维度1 入口分流正确性

场景推演（6 例）：
1. 「帮我调研X并写成长报告」（无材料）→ SKILL.md:20-21 正确导向 deep-research，通过。
2. 「这份报告的引用靠谱吗」→ audit，通过。
3. 「帮我写个报告」（无材料、非调研型）→ **冲突**，见问题1。
4. 「基于这份报告改写压缩一下」→ SKILL.md:15 导入模式触发词「基于...改写」正面命中，而 :51 又裁定报告改写走 compose；误走导入会拉起 Analyzer/Converter 全套工作区转换。有 :51 事后裁决，可恢复。【中】
5. 「从零开始写个教程」→ frontmatter:14「从零开始」→创建模式，但 SKILL.md:62 判断流程「从...开始」→导入模式，"从零开始"字面命中导入分支，同一文件内两处相反。【中】
6. 模糊表述「这报告不行，弄好点」→ 判断流程末端询问意图，可恢复，通过。

**问题1【高】**「写个报告」被双重认领：SKILL.md:9 与 :45（路由表）把「写…报告」判给 compose，:14 又把"写个报告"（无现成材料）列为引擎创建模式触发词。若进 compose，compose.md:22「两者都缺：先要求输入文稿或研究材料，不要硬写」即死胡同，且 compose.md 全文无任何指回引擎创建模式的路标——冷启动会话会卡在索要材料。三层结构（frontmatter 分流/路由表/引擎判断）对同一短语给出相反答案，是文档内真实矛盾，非表达歧义。SKILL.md:51 的裁决句只覆盖"研究/分析/调研报告 vs 手册/教程/书稿"，未覆盖泛化"报告"。

## 维度2 mode 契约自包含性

**问题2【中】** compose.md:20 终稿生成模式检测 `{report_dir}/synthesis.md`、`plan.json`、`sub_reports/*.md`，这些产物在 deep-research 全目录（md/py/json）grep 零命中——本仓无任何生产者；compose.md:11 宣称的 deep-research 产物（report.md+research-process.md+sources.json）与 :20 检测的文件集自相矛盾。结果是：现仓库 deep-research 产物永远落到写作修改模式，终稿生成主路径在本仓不可达，冷启动无法得知 synthesis.md 从何而来。同源悬空：format.md:9/:232-240 与 SKILL.md:47 的 `plan.json.report_shape`，deep-research 亦无此概念（B3 加指引也补不上）。
**问题3【中】** compose.md:66/:115/:306-309 强制 visual_plan.md 与 images/ 落在 `{report_dir}`，但写作修改模式的输入是"任意文稿路径或贴入文本"（:270-276），`{report_dir}` 未定义，质量门槛条款无法执行。
- audit.md 自包含良好；:11/:34 默认路径 `workspace/reports/` 未注明是 deep-research 产物根（格式与 deep-research SKILL.md:318 一致，可对上）【低】；:84「项目记忆偏好」引用读者不可见的项目记忆【低】。
- format.md 自包含最好，唯一问题是上述 report_shape 悬空。

## 维度3 引擎细节可用性

四文件头部均有「入口见 SKILL.md」指引，模板引用（structure-from-doc / source-info / structure / style-guide）经核对全部存在，merge.py 的 --workspace/--output 签名与文档一致。问题：
**问题4【中】** import-mode.md:82-88 与 import-guidelines.md:79/:89/:104 依赖 `meta-web` 技能，本仓 skills/ 无此技能（有 url-to-md 可替代但未提及，也未给 fallback），URL 导入路径冷启动受阻。
- 【低】启动机制不一致：import-mode.md:96/:224 用 `subagent_type: general-purpose`+内联提示词，SKILL.md:97 与 create-edit-modes.md 却说调用随技能分发的 .claude/agents 定义（后者未给启动机制）。两条路都能走通。
- 【低】创建模式工作区根 `workspace/{project-name}` 仅出现在 create-edit-modes.md:166/:225 与 workspace-and-files.md:6，SKILL.md 工作区概念（:101）未给根路径，且与导入模式 `.longText/` 两套根并存；merge.py 接受任意路径，可运行。
- 【低】examples/import-example/README.md:178 命令路径 `scripts/long-text/scripts/merge.py` 为旧布局失效路径（实际 scripts/merge.py），照抄必失败。

## 维度4 合并残留

**问题5【中】** 旧技能名贯穿引擎层未统一：import-mode.md:5/:32/:227「long-text 范式 / Long-Text 文件」、import-guidelines.md:5 自称"long-text 技能"（该技能已不存在）、.claude/agents 四文件自称「Long-Text 系统 / Long-Text v1.1.0」（analyzer.md:12、converter.md:3、reviewer.md:9/:390、writer.md:9/:247）、merge.py:2 docstring、examples README。SKILL.md 统一叫"长文档引擎/引擎工作区"，冷启动读到「Long-Text 范式」无定义可查。B2 验收 grep 只查了三个 sn-* 名，漏了 long-text。三 mode 之间术语（报告/研究材料）无冲突，mode 文档头部路标清晰，未发现误导性"本 skill"自指（仅 import-guidelines.md:5 一处）。

## 维度5 与 deep-research 衔接

SKILL.md:18-21 分工表述与 deep-research 现状（finalize 自产 report.md，deep-research SKILL.md:318）不矛盾，write-report 侧自洽。唯一衔接缺口即问题2的 synthesis/plan.json 悬空假设（源自 evoCenter 时代工作流）。deep-research 无反向指引属 B3，不计。

## 总体判断：修后可用

必修两项（高）：① compose.md:245 调用命令 `python3 /scripts/sn_agent_runner.py` 为本仓不存在的绝对路径，且 `sn-image-base` 技能未随插件分发（全仓 grep 仅 compose.md 自身提及）——AI 配图主路径照抄必失败（:230 有 fallback 条款，但文档给出的"调用命令"本身即错）；② 问题1「写个报告」双重认领。建议同批处理：synthesis/plan.json 来源说明或显式降级（问题2）、visual_plan 在写作修改模式的落点（问题3）、meta-web 替换为 url-to-md（问题4）、「基于...改写」「从零开始」触发词与 :51/:62 去冲突、long-text 术语清扫（问题5）。低级项可随 B3 顺带。
