# B3 委派单：联动收尾（版本 / 描述 / 衔接段 / evoCenter 收敛 / B1+B2 移交打磨）

- 方案：plans/work-skills/2026-11-13-skill-consolidation.md（详案第 2 节 B3 + B1/B2 收口移交待办，T1）
- 证据目录：plans/work-skills/.flow-evidence/2026-11-13-skill-consolidation/B3/
- 仓库：本仓 C:\Users\tuzhe\runspace\rulertu-flow + evoCenter 仓 C:\Users\tuzhe\runspace\evoCenter（仅 CLAUDE.md）
- 纪律：**两仓均不 git commit**（主控收口统一处理）；只动边界内文件

## A1. 本仓插件 manifest

- `plugins/work-skills/.claude-plugin/plugin.json`：`version: 2.5.0 → 2.6.0`；`description` 改为：
  `工作型技能合集：文章导读、深度研究、数据分析、报告成稿与审计、战略分析、写作改稿、文档转换、工作总结与思维工具`
- 根 `.claude-plugin/marketplace.json` 的 work-skills 条目 `description` 同步为同一句（当前两处措辞不一致，本次统一）。

## A2. deep-research 升版与衔接段

- `SKILL.md` frontmatter：`version: 0.7.0 → 0.8.0`；`description` 末尾追加一句（保持版本演进句式）：
  `v0.8.0 五个搜索通道收编进 scripts/channels/ 内部布局并新增 image 通道（Serper.dev 图搜，web 通道的配图/视觉证据增强，SERPER_API_KEY 缺失时降级 web）。`
- `config.json`：`version: 0.7.0 → 0.8.0`。
- `SKILL.md` 末尾新增「产物后处理」段（指引而非自动执行，2-4 行）：

```markdown
## 产物后处理

finalize 产出 report.md 后，可选接同插件 write-report 技能做后处理（不自动执行，经用户确认）：
- 需要改稿 / 润色 / 重组结构 → write-report compose mode（产物目录即本技能 finalize 输出）
- 需要核查引用 / 怀疑幻觉 → write-report audit mode
```

## A3. evoCenter CLAUDE.md（跨仓）

文件：C:\Users\tuzhe\runspace\evoCenter\CLAUDE.md

- **79-81 行**三行收敛为一行（放原位置）：
  `| 报告成稿后处理：生成最终报告、改写 / 润色 / 压缩 / 扩写文稿、核验引用与参考文献、研究报告结构规范 | write-report（compose / audit / format mode） |`
- **85 行**`/sn-report-audit` 同步：`推荐调用 /sn-report-audit` → `推荐调用 write-report 的 audit mode`（该行其余语义保留，"skill 不自动改报告"边界表述保留）。
- 先通读 75-90 行上下文再改，保持表格格式与周边行风格一致；全文件 grep 确认无其他 sn-* 三件套残留。

## A4. B1 移交（channels/ 旧布局清理）

- 三个 CHANNEL.md 的依赖安装指引：`deep-research/scripts/channels/{code,social_cn,social_en}/CHANNEL.md` 中 `skills/sn-search-<X>/requirements.txt` → `deep-research/scripts/channels/<key>/requirements.txt`（按各文件上下文调整措辞，指引语义不变）。
- 三个 search_utils.py 第 21 行缺 httpx 报错指引：`python -m pip install -r skills/sn-search-<X>/requirements.txt` → `python -m pip install -r deep-research/scripts/channels/<key>/requirements.txt`（只改路径字符串，不动报错逻辑）。
- `docs/SEARCH_MIGRATION.md` 收编节代码围栏排版：两行说明文字（「每个通道目录内：CHANNEL.md…」与「+ scripts/…」）移出 ``` 围栏，恢复为正文。
- `channels/product/scripts/producthunt_search.py` 第 44 行 User-Agent：`sn-search-producthunt/1.0` → `deep-research-product/1.0`（主控定夺，脚本内仅此一处）。

## A5. B2 移交（write-report 打磨）

1. `references/import-guidelines.md`：:79/:89/:104 附近 meta-web 引用 → 与 import-mode.md 2.2 节同样的替代注记口径（url-to-md 技能或 MCP web-reader 优先，meta-web 为旧环境依赖）。先读上下文，最小改动。
2. 引擎层自称清扫（最小化，保留一次历史名提及）：`.claude/agents/{analyzer,converter,reviewer,writer}.md` 头部自称「Long-Text 系统 / Long-Text v1.1.0」→「write-report 长文档引擎」；`scripts/merge.py` 第 2 行 docstring 同步。SKILL.md 末尾已有的 Long-Text 同义注记保留不动。
3. `examples/import-example/README.md` :178 命令路径 `scripts/long-text/scripts/merge.py` → `scripts/merge.py`（对照 write-report 实际布局）。
4. `modes/audit.md`：:11/:34 附近默认路径 `workspace/reports/` 加一句注记「（deep-research 产物根目录）」；:84「项目记忆偏好」→ 改为读者可见的表述（如「用户此前明确的偏好约定」）。
5. `references/engine/import-mode.md` :96/:224 附近 Subagent 启动：加一句注记「优先调用随技能分发的 .claude/agents 定义（插件 agent 形式）；宿主不支持时用 general-purpose + 本文提示词作替身」，原文流程保留。
6. `SKILL.md` 工作区概念段：补一句工作区根路径说明——创建模式工作区通常为 `workspace/{project-name}/`，导入模式工作区路径按导入时的 workspace 参数（两种根并存是引擎既有设计）。
7. `references/engine/workspace-and-files.md`：L52-53 间补回缺失空行（对照源排版）。

## 设计定夺（主控已裁）

- UA 更名值：`deep-research-product/1.0`。
- 描述统一以 A1 的新句为准（覆盖"数据分析"= sn-da 四件套、"报告成稿与审计"= write-report）。
- agents 自称清扫保留一次"Long-Text"历史名（与 SKILL.md 注记呼应），不做全文同义替换。
- evoCenter 仓只改 CLAUDE.md，不碰其他；两仓均不提交。

## 定向验证映射

| 锚点 | 验证 |
|---|---|
| A1 | `grep '"version"'` 两处 = 2.6.0；两 description 逐字一致 |
| A2 | deep-research 双处 0.8.0；SKILL.md 有「产物后处理」段且含 write-report 指引 |
| A3 | evoCenter CLAUDE.md `grep "sn-research-report\|sn-report-audit\|sn-report-format-discovery"` 零命中；write-report 行在位 |
| A4 | `grep -rn "skills/sn-search-" deep-research/` 零命中；`grep -rn "sn-search-producthunt/1.0" channels/` 零命中；SEARCH_MIGRATION.md 围栏渲染正确（目测 diff） |
| A5 | `grep -rn "meta-web" write-report/references/` 仅存于"旧环境依赖"注记口径；`grep -rn "Long-Text" write-report/.claude/agents/ write-report/scripts/merge.py` 清扫后符合口径；README 路径指向存在文件 |
| 红线 | B1 验收两条 grep 仍零命中；`grep -rn "sn-research-report\|sn-report-audit\|sn-report-format-discovery" write-report/` 仍零命中 |

## 回报要求

- 日志写 `evidence/B3/executor-log.md`：改动清单、每条验证命令与退出码、两仓 diff 概览。
- 发现现状与委派单锚点不符时停下上报，不自行扩改。
