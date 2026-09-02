---
name: software-copyright-cn
description: "Generate Chinese computer-software copyright application materials from a code repository: an evidence-backed registration workbook, a 10+ page illustrated Word manual, and a Word source-code excerpt containing the first and last 1,500 lines (or all code when the total is at most 3,000 lines). Use for 软著、软件著作权、登记表、操作手册或源代码文档 requests."
---

# 中国软件著作权材料

把仓库事实整理为一套可复核、可提交的材料。源代码与测试是功能事实的首要证据；产品文档用于补充名称和业务口径。用户提供的主体、日期和权利信息优先于仓库推断。

## 工作流

1. 读取仓库内的 `AGENTS.md`、入口文档、包清单、主要运行入口、用户界面和相关测试。先运行 `scripts/inventory_repo.py`，生成代码清单和物理行数统计。完成标准：每个纳入或排除的代码文件都有理由，且秘密、依赖、生成物、测试夹具和压缩 vendor 文件未进入申报代码。
2. 建立一份事实表，逐项记录 `value`、`source` 和 `status`（`verified`、`user_confirmed`、`unknown`）。软件名称、版本、完成日期、发表状态、开发方式、权利范围、著作权人证件信息等无法由仓库可靠证明的字段保持 `unknown`，集中向用户确认。不要用“看起来合理”的值填空。
   - 事实表同时收集设计要点：核心模块的架构决策、业务规则来源、特殊输入与失败模式，由用户口述，记为 `user_confirmed`。这些要点供登记表“开发目的/技术特点”、说明书技术实现段和流程图使用，是申报材料中人类创造性投入的直接证据；用户讲不清的模块如实记录，不代拟。
   - 仓库由 `README.md` 中的 Verita 标题和 `poc/prototype/server.py` 共同识别为 Verita 项目时，读取 [references/verita-profile.md](references/verita-profile.md)。先刷新其中的 Git 状态和代码清单；profile 中的建议在用户确认前仍按 `unknown` 记入事实表。
3. **代码合规前置。** 构建材料前，用同插件 `copyright-code-review` 的 `scripts/scan_source.py` 对纳入申报的代码跑静态扫描（占位符、乱码、连续空行、第三方版权头、空桩行）；用户能提供疑似来源（所用脚手架、模板、教程仓库的本地 clone）时，另跑同目录 `similarity_check.py` 做本地查重比对。命中项整理成修复建议清单，经用户逐条审批后由 AI 实施、重跑扫描确认消除，再进入材料生成；阻断级问题未处理完不构建 Word。完整预审（链路完整性、开源权属、材料联动）需要人工读代码，建议用户直接运行该 skill。
4. 生成用户要求的产物。登记表读 [references/registration-form.md](references/registration-form.md)；操作手册读 [references/manual.md](references/manual.md)；源代码文档读 [references/source-code.md](references/source-code.md)。只加载当前产物需要的参考文件。
5. 对登记表中的“开发目的、面向行业、主要功能、技术特点”和操作手册正文调用 `$humanizer` 的改稿模式，做最小有效编辑。它来自 `work-skills` 插件，实际名称是 `humanizer`。代码、命令、路径、字段值、日期、版本、计量结果和截图文字不进入改稿。若当前会话未暴露 `$humanizer`，按 [references/human-writing-fallback.md](references/human-writing-fallback.md) 完成同等审校，并在交付说明中记录降级。
6. Humanizer 后逐句回查事实表：专名、数字、状态、功能边界和限制必须与证据一致；被 humanizer 新增而无来源的事实全部撤回。完成标准：每段申报文字均能指向仓库文件、界面截图或用户确认。
7. 在独立输出目录交付原模板副本、说明书 `.docx`、源代码 `.docx`、代码清单 JSON、事实表和 `review-needed.md`。保留原模板和原截图，不覆盖用户文件。

## 总体约束

- 当前工作树可能有未提交改动。材料按用户指定的代码状态生成，并在清单中记录 Git 提交号、分支和工作树是否干净；不要为了“统一版本”改动或清理仓库。
- 说明书只写已实现、能从界面或代码验证的功能。计划、路线图和测试设想不可写成现有能力。
- 截图使用真实运行界面并遮蔽密钥、令牌、个人信息、内网地址和调试数据。不能运行界面时，可用仓库已有图示或明确标注为“流程示意图”的图，不伪造产品截图。
- 任何产物都不得包含 `.env`、真实凭据、内部令牌、个人隐私或受限数据。
- Word 文档生成后至少检查：可打开、中文字体正常、图片未越界、页眉页脚连续、页数达标、代码抽取边界准确。环境有 LibreOffice 或 Word 时优先导出 PDF 做肉眼复核；PDF 仅作校样，不替代用户要求的 Word 文件。
