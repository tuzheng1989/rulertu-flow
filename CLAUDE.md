# rulertu-flow 仓库约定

## 目录约定（重要）

本仓库是插件集合。**插件/技能目录只放技能运行所需文件**（SKILL.md、references/、scripts/、evals/ 等）——技能目录会被使用它的智能体检索到，任何会话产物（方案、评审记录、测试报告、临时文件）写入其中就是污染。

| 内容 | 位置 |
|------|------|
| 方案文档 + plan-iterate 评审留痕（`.plan-iterate/`） | `plans/<插件名>/` |
| 仓库级文档（跨插件、面向维护者） | `docs/` |
| 仓库级测试 | `tests/` |

历史归档已统一迁移：`plugins/copyright-skills/plans/` → `plans/copyright-skills/`（2026-10-29，内部引用已同步改写）。
