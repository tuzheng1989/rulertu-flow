# B2 执行证据 · 权属材料决策表 + 主 SKILL 口径修正

批次：B2（方案 `plugins/copyright-skills/plans/2026-09-03-review-rectification.md`，分级 T1）
执行：Executor，2026-09-03，main @ 16fe209（工作树含并行批次 B1 对 copyright-code-review/SKILL.md 的改动，非本任务产出）

## 改动回报

### 改动 1：新增 references/ownership.md（决策表 + schema）

位置：`plugins/copyright-skills/skills/software-copyright-cn/references/ownership.md`（新增文件）

结构摘要：

1. 文档头：官方口径声明（官网申请须知要求按申请情形提交权属证明文件）+ 核对记录"官网申请须知核对于 2026-09-03（URL 待人工补充）"。
2. "情形 → 必需文件决策表"：6 种情形 × 必需文件，附情形标识（schema 用）：`independent` / `cooperative` / `commissioned` / `employment` / `derivative` / `transferred`。跨情形补充口径：涉外主体外文材料附中文翻译件（形式要求标注"以官网现行要求为准"）；不虚构额外文件。
3. "文件三态"：`provided` / `pending` / `na` 判定规则表；判 `na` 必须写理由。
4. "权属文件清单 JSON schema"：字段与委派单给定结构逐字段一致（`scenario` / `items[].file|type|status|note`）。声明本节为该格式唯一出处，`check_submission.py` 按此消费。消费规则两条：`status=pending` 的项必须进 `review-needed.md`；提交前校验存在 `pending` 按阻断处理（内部暂停提交）。另定义清单无效判定（scenario 六选一之外、status 三态之外）。

### 改动 2：SKILL.md frontmatter description（锚点 :3）

- 改前关键内容：`a 10+ page illustrated Word manual`
- 改后关键内容：`an illustrated Word manual (documents under 60 pages are submitted in full, with at least 30 lines per page; the internal page floor lives in manual.md)`
- 保持英文一句式；触发词 软著、软件著作权、登记表、操作手册、源代码文档 均保留未动。

### 改动 3：SKILL.md 工作流第 2 步（锚点 :13-15 区段，Verita 小节之前新增一条子弹）

- 改前：该位置无此条（第 2 步只有事实表主条 + 设计要点条 + Verita 条）。
- 改后新增："开发方式与权属情形必须经用户确认；确认后按 [references/ownership.md](references/ownership.md) 建立权属文件清单。情形无法确认时，不进入材料构建。完成标准：清单中每一项都有 `provided`、`pending` 或 `na` 状态，`pending` 项不补齐就不提交。"
- 句式与现有步骤一致（"必须经用户确认""完成标准""不…就不…"）。

### 边界核对

SKILL.md 其余工作流步骤与总体约束未改动（`git diff --stat` 显示该文件仅 3 行变更：description 1 行改写 + 新增 1 条子弹）。

## 验证回报

| 验证项 | 结论 |
|---|---|
| 决策表覆盖 6 种情形 | PASS。逐一核对：独立开发（independent，主体资格证明）、合作开发（cooperative，+合作开发合同）、委托开发（commissioned，+委托开发合同或任务书）、职务作品/法人作品（employment，+职务创作/法人归属材料，标注"以官网现行要求为准"）、二次开发或修改他人软件（derivative，+原著作权人许可证明）、受让取得（transferred，+转让合同）；涉外翻译件为跨情形补充口径。每种情形均含主体资格证明，未虚构额外文件。 |
| JSON schema 与 pending → review-needed.md 规则可断言文本 | PASS。`Grep 'independent|cooperative|commissioned|employment|derivative|transferred|review-needed|status=pending'` 命中 8 行。schema 逐字段与委派单给定结构一致；"status=pending 的项必须进 review-needed.md"与"按阻断处理"两处可断言文本存在。 |
| SKILL.md 新增链接指向文件存在 | PASS。`test -f .../references/ownership.md` → LINK_OK（退出码 0）。 |
| 两文件无 `必被驳回\|官方.{0,4}查重\|征信` 命中 | PASS。Grep 扫描整个 software-copyright-cn 目录，No matches found。 |

## 假设与剩余问题

- "URL 待人工补充"按委派单原文保留在 ownership.md 文档头，与方案"执行说明"中"本方案写作环境禁用联网检索"一致。
- 职务作品情形的"任务书、劳动合同或单位证明"在决策表说明列标注"以官网现行要求为准"；涉外翻译件的形式要求同此口径。
- schema 的 `type` 枚举（identity/contract/license/translation）在委派单中以"..."示意开放枚举，本文件按四个具名值 + "等"表述落定；B6 实现 `check_submission.py` 时若需收紧为闭枚举，应在 B6 评审节点确认。
- 工作区中 `copyright-code-review/SKILL.md` 的未提交改动属并行批次 B1，本任务未触碰。
