# copyright-skills 整改方案（基于 2026-09-03 外部评审）

## 背景

外部评审结论：插件对整理软著材料有明显帮助，但不是"生成后即可提交"的可靠闭环。评审列出 6 类主要问题、7 条整改优先级建议。本方案把评审意见落成 7 个有依赖关系的实施批次，全部锚点已对照当前代码核实（2026-09-03，main @ 16fe209）。

## 官方口径声明（全方案唯一出处）

本方案涉及的官方要求，来源为评审者在 2026-09-03 对中国版权保护中心官网申请须知的核对，要点：

- 登记全程在线办理：在线填报申请表、在线打印申请确认签章页、签章后上传 PDF、不得擅自改变签章页格式和打印比例。
- 鉴别材料：程序和文档前、后各连续 30 页；不足 60 页提交全部。程序每页不少于 50 行，文档每页不少于 30 行。
- 按情形还需提交：主体身份证明、委托/合作开发合同、任务书、转让合同、修改他人软件的许可证明、特殊主体授权及外文翻译材料。

执行 B1/B2/B4/B5/B6 时，须以当时官网现行文本复核上述要点，并在文档中记录核对 URL 与日期；无法核对的表述一律降级为"内部口径"，不标注为官方规则。评审中提到的"2026.3.15 新版审查规则""官方 AI 查重系统""必驳回""征信影响"均无出处，按 B1 删除或降级。

## 评审问题 → 批次映射

| 评审问题 | 批次 |
|---|---|
| 1. 登记表流程落后于在线办理 | B6 |
| 2. 说明书漏检每页 30 行、前后各 30 页口径 | B4 |
| 3. "2026 新版规则 / 官方 AI 查重"无出处 | B1 |
| 4. 源码按路径字母序、无显式顺序与入口前置机制 | B5 |
| 5. 内部代码路径写入正式说明书 | B4 |
| 6. 权属材料无决策表 | B2 |
| 7. 核心脚本无自动化测试 | B3（前置）、B4/B5/B6（随改随测）、B7（回归收口） |

## 路线图

优先级：P0 = 直接影响补正/合规风险（B1、B4、B5）；P1 = 流程与权属适配（B2、B6）；P2 = 质量地基（B3，因是 B4/B5 前置故先行）；P3 = 收口（B7）。

```
Wave 1:  B1 ──────────────────────┐
         B2 ────────┐             │
         B3 ──┐     │             │
              │     │             │
Wave 2:       ├──▶ B4 ──┐        ├──▶ ...
              │         │        │
              │  B6 ◀───┼──┘(B2、B3) 
              │         │        │
Wave 3:       │         ├──▶ B5
              │         │
Wave 4:  B7 ◀─┴─────────┴── (B1..B6 全部)
```

- B1（copyright-code-review/SKILL.md）与 B2（software-copyright-cn/SKILL.md + references/ownership.md）与 B3（tests/**）文件集互不重叠，可并行。
- B4 交付共用脚本 `render_check.py`，B5 依赖它，故 B5 排在 B4 之后。
- B6 的提交校验脚本消费 B2 定义的权属文件清单格式。

## 全局红线（唯一出处，各批次引用不复制）

1. 所有脚本拒绝覆盖已存在的输出文件；新脚本遵循同一约定。
2. 凡写进交付文档的"官方要求"，必须附核对来源（URL + 日期）或显式标注"内部口径"；禁止使用"必被驳回""官方 XX 系统"等无出处表述。
3. 正式提交件（说明书、源代码 docx）正文不得包含内部文件路径、审计措辞；证据信息只进旁路 audit JSON。

## 详案

### B1 copyright-code-review 表述治理 [P0]

**如何改**（文件：`plugins/copyright-skills/skills/copyright-code-review/SKILL.md`，单文件）：

- 锚点 `SKILL.md:4`（description "按中国版权保护中心 2026 新版审查口径逐项核查"）：改为"按现行《计算机软件著作权登记办法》与中国版权保护中心官网申请须知口径自查；分级为内部风险控制口径"。
- 锚点 `SKILL.md:18`（`source: 中国版权保护中心 2026.3.15 新版软著登记申请审查规则`）：删除该 metadata 行，或改为 `source: 内部风控基线（非官方文件）`。
- 锚点 `SKILL.md:23`（"官方 AI 查重系统的比对结果无法本地复现"）：改为"登记机关审查中的比对结果无法本地复现"。
- 新增小节"口径声明"（放在"定位与边界"前后）：官方要求以官网现行文本为准并附核对记录；"阻断"定义为内部暂停提交信号，非官方必驳规则；列出本次核对记录（官网申请须知，2026-09-03）。
- 锚点 `SKILL.md:77`（"功能说明 500–1300 字"）：保留数值，标注"内部字数预算，非官方硬性要求"。此处为该数值的全方案唯一权威陈述，`registration-form.md` 在 B6 改为引用。
- 锚点 `SKILL.md:78`（"虚标功能直接驳回"）与 `SKILL.md:87`（"阻断：不改必被驳回…纯 AI 生成的核心逻辑"）：改为内部分级语义——"阻断：按内部口径暂停提交，虚标功能与未标注第三方代码是高概率补正/驳回风险"。
- 锚点 `SKILL.md:91`（"征信影响"与"官方查重比对结果"）：删除"征信影响"；"官方查重比对结果"改为"登记机关查重比对结果"。

**如何验证**：
- L1：`Grep` 断言文件中不再出现 `2026.3.15`、`官方.{0,4}查重`、`必被驳回`、`征信`、`直接驳回`；`500–1300` 出现且带"内部"标注。
- 红线回归：frontmatter 仍可解析（YAML 合法），allowed-tools 未变动。

**验收标准**：
- PASS：上列 7 处锚点（:4、:18、:23、:77、:78、:87、:91）逐一改毕，1 个新增小节（口径声明）落位，Grep 断言全绿。
- FAIL：任一无出处表述残留；或 frontmatter 解析失败。

**代码评审节点**：降级后语义是否仍能约束执行者（防止从"必驳回"降成"无所谓"）；"阻断"的新定义是否在全篇一致使用。

**分级 T1**：单文件文档措辞改动，无脚本、无契约邻近。主控亲自机械验证收口。

### B2 权属材料决策表 + 主 SKILL 口径修正 [P1]

**如何改**：

- 新增 `plugins/copyright-skills/skills/software-copyright-cn/references/ownership.md`：
  - 决策表：申请情形（独立开发 / 合作开发 / 委托开发 / 职务作品 / 二次开发或修改他人软件 / 受让取得）→ 必需文件（营业执照或身份证明、合作开发合同、委托开发合同、任务书、转让合同、原著作权人许可证明、外文翻译件等，按情形取交集）。
  - 每个文件三态：`provided` / `pending` / `na`，输出为权属文件清单 JSON（路径 + 状态 + 说明），`pending` 项必须进 `review-needed.md`。
  - 文档头注明：官网申请须知要求按情形提交权属文件，核对记录（URL + 日期）留在此文件，格式遵循全局红线 2。
- `plugins/copyright-skills/skills/software-copyright-cn/SKILL.md`：
  - 锚点 `SKILL.md:13-14`（事实表字段列举）附近：工作流第 2 步增加——开发方式与权属情形必须经用户确认，确认后按 `references/ownership.md` 建权属文件清单；情形无法确认时不进入构建。
  - 锚点 `SKILL.md:3`（description "10+ page illustrated Word manual"）：改为与官方口径一致的表述（文档不足 60 页全交、每页不少于 30 行；内部下限见 manual.md），避免在入口描述里固化无出处页数。

**如何验证**：
- L1：ownership.md 决策表覆盖上列 6 种情形，每种情形的必需文件与全局红线 2 的来源声明齐备；SKILL.md 链接可达（文件存在）。
- 红线回归：SKILL.md 其余工作流步骤未被改动（diff 范围核对）。

**验收标准**：
- PASS：6 情形 × 必需文件矩阵完整；`pending` → `review-needed.md` 的规则可断言（文本存在）；SKILL.md 新增步骤指明"未确认不构建"。
- FAIL：任何情形缺必需文件；或决策表使用了"必驳"类无出处表述（违全局红线 2）。

**代码评审节点**：清单 JSON 字段是否与 B6 的 `check_submission.py` 消费格式一致（schema 在本批定义，B6 引用）；是否误把"内部下限"写成官方要求。

**分级 T1**：加法式文档改动，不邻近脚本契约。主控亲自机械验证收口。

### B3 测试基建：现有脚本行为基线 [P2，前置]

**如何改**（新增 `plugins/copyright-skills/tests/`，pytest；不改任何生产文件）：

- fixtures（conftest.py）：临时目录构造迷你仓库——含入口文件（`main.py` 带 `if __name__ == "__main__"`）、恰好 3000 行与 3001 行的文本文件、无尾换行文件、空文件、CRLF 文件、含 TODO/MIT License 头/`pass` 桩/乱码样本的文件、`.env`、`node_modules/**`、`docs/**`、 GB18030 编码文件。
- `test_inventory_repo.py`：`physical_lines` 边界（空/无尾换行/CRLF）；DEFAULT_EXCLUDES 命中与理由字段；排序键（casefold）稳定；git 元数据在非 git 目录下为 None 不崩溃。
- `test_build_source_docx.py`：≤3000 全选；>3000 前后各 1500 不重叠（断言 manifest 的 `first/head_end/tail_start/last`）；入选文件 sha256 与清单不符时拒构建（`build_source_docx.py:74-75`）；`--lines-per-page` 非 positive 拒绝（`:61-62`）；输出已存在拒绝（`:63-65`）；manifest 的 `selected_sha256` 稳定。
- `test_build_manual_docx.py`：显式页数不足 `--min-pages` 拒绝（`build_manual_docx.py:64-69`）；无图片拒绝（`:70-72`）；输出已存在拒绝（`:60-61`）；**基线锁定**：当前 evidence 段写入正文段落（`:133-136`）——该用例在 B4 改为断言 evidence 只出现在 audit JSON。
- `test_registration_form.py`：`fill` 拒绝覆盖已存在输出（`registration_form.py:48-49`）；模板与输出同路径拒绝（`:50-51`）；changes.json 记录 before/after；inspect 输出含 merged_ranges。
- `test_scan_source.py`：占位符/license/stub/乱码命中；字符串内 TODO 的误报样本按现状记录（脚本目前会命中，预期行为锁定在测试注释里）。
- `test_similarity_check.py`：6 行窗口指纹在构造的两份相似文件上命中，无关文件不命中。
- dev 依赖声明：pytest 加入开发说明（README 或 tests/README），不进运行时依赖。

**如何验证**：`pytest plugins/copyright-skills/tests -q` 全绿，覆盖上列 6 个脚本模块。

**验收标准**：
- PASS：全量用例通过；每个用例对应上列锚点行为；失败用例不存在 skip 掩盖。
- FAIL：任一锚点行为未被用例覆盖；或测试依赖网络/外部 soffice（本批不测渲染）。

**代码评审节点**：fixtures 是否复用（一个 conftest，不在各测试文件复制仓库构造）；断言的是行为不是实现细节（JSON 字段名属于行为契约，允许断言）。

**分级 T1**：纯加法测试，不改生产文件，无外部状态。主控亲自机械验证收口。

### B4 说明书构建器：证据出正文 + 渲染后行数校验 [P0]

**如何改**（文件：`build_manual_docx.py`、新增 `scripts/render_check.py`、`references/manual.md`；依赖 B3）：

- 锚点 `build_manual_docx.py:133-136`：删除写入正文的"材料复核依据：…"段落；逐页 evidence 改写入 audit JSON 新增字段 `page_evidence`（`:142-151` 的 audit dict）。
- 新增 `scripts/render_check.py`（software-copyright-cn/scripts/ 下，与两个构建器同目录）：
  - 接口：`python scripts/render_check.py --docx <file> --min-lines 30 --output render-report.json`。
  - 实现：`soffice --headless --convert-to pdf` 转到临时目录（不污染输出目录），用 fitz（PyMuPDF）逐页提取文本统计行数；报告含总页数、每页行数、不足 `--min-lines` 的页列表。
  - soffice 不存在 → 非零退出并明确提示"无法渲染校验，需人工在 Word/PDF 中逐页核对"，不静默通过；输出文件已存在 → 拒绝（全局红线 1）。
  - 依赖说明：PyMuPDF 已是本仓库既有惯例（`work-skills/skills/long-text/scripts/parse-pdf.py:20` 同款），非新增引入；soffice 为可选外部工具，缺失时降级为人工核对项。
- `references/manual.md`：
  - 锚点 `manual.md:24`（构建命令）：命令后追加 render_check 步骤（`--min-lines 30`）。
  - 锚点 `manual.md:27`（"至少 10 页"段）：注明官方口径（文档不足 60 页全部提交；每页不少于 30 行），10 页为内部下限，全局红线 2。
  - 锚点 `manual.md:35-39`（完成标准）：新增"渲染实测每页 ≥30 行，不足页整改后复测"；删除/替换涉及正文 evidence 的隐含预期。
- `test_build_manual_docx.py`：基线用例翻转——断言正文无 evidence 段、audit JSON 含 `page_evidence`。

**如何验证**：
- L1：pytest（evidence 迁移、既有 min-pages/无图用例不回归）。
- L2：构造含 2 个内容页的 spec（`--min-pages 4`）→ 构建成功 → render_check 在无 soffice 环境返回明确不可用；有 soffice 环境（CI/本机）→ 报告 JSON 可断言。
- 红线回归：`--example` 输出同步更新（`build_manual_docx.py:30` 的 EXAMPLE 中 `evidence` 字段语义不变，但文档说明其在旁路文件）。

**验收标准**：
- 给定 evidence 非空的 spec → 必现：docx 正文无"材料复核依据"字样；audit JSON `page_evidence` 与 spec 一致。
- 给定 `--min-pages 10` 与 8 页 spec → 必现：拒绝构建。
- 给定 soffice 缺失环境 → 必现：render_check 非零退出 + 明确提示；必不现：报告 `render_checked: true` 的假成功。
- 给定每页文字量约 20 行的 spec（有 soffice）→ 必现：报告中该页列入不足清单。

**代码评审节点**：`page_evidence` 字段向后兼容（无 evidence 的页省略还是空数组，定一种并写入 audit 文档）；fitz 提取的"行"定义（按文本 line 对象计数）在报告中注明口径；临时 PDF 必须清理。

**分级 T2**：多文件、变更交付物（正式说明书正文内容）行为；有 B3 测试覆盖；不触外部状态（soffice 只读转换）。虽触及全局红线 3 的管辖对象，但红线本身由本批测试断言直接覆盖（正文无 evidence 段为必现断言），故不升 T3。

### B5 源代码构建器：显式顺序 + 入口前置 + 渲染实测 [P0]

**如何改**（文件：`build_source_docx.py`、`references/source-code.md`；依赖 B3、B4）：

- 锚点 `build_source_docx.py:54-60`（argparse）：新增 `--first` 参数（`action="append"`，值为清单内相对路径，可重复）：命中文件按给定顺序移到串接序列最前，其余保持清单相对顺序；路径不在 `included_files` → 报错退出并列出可用路径。
- 锚点 `build_source_docx.py:138-154`（manifest）：新增 `reordered_first` 字段记录本次前置调整（文件 + 顺序），对应 `source-code.md:18` "在清单中记录这一调整及理由"的机制落地。
- 锚点 `source-code.md:17-18`（抽取规则）：改写为——默认按清单顺序；入口文件未居前时用 `--first <入口相对路径>` 显式前置，manifest `reordered_first` 即为记录载体；不再要求手工改清单。
- 锚点 `source-code.md:30-33`（构建命令段）：命令后追加 `render_check.py --min-lines 50` 步骤；说明长行折行会导致某页实际渲染行数少于配置的每页记录数——报告列出不足页，整改（调小 `--lines-per-page` 或字号）由人工决策，构建器不自动改版式。
- `test_build_source_docx.py` 新增：`--first` 前置生效且其余顺序稳定；`--first` 未知路径拒绝；manifest `reordered_first` 内容正确；`--first` 不改变 `selected_line_count`；`selected_sha256` 因串接顺序变化而改变（设计取舍：sha256 按选中记录的 JSON 序列化计算，顺序即内容，manifest 如实记录新值，测试断言与实际一致而非与旧值一致）。

**如何验证**：
- L1：pytest（上列新用例 + B3 既有用例不回归）。
- L2：3001 行迷你仓库 → `--first main.py` → manifest 断言首记录为 main.py:1、`reordered_first` 正确。
- 红线回归：无 `--first` 时行为与 B3 基线逐字节一致（selected_sha256 相同）。

**验收标准**：
- 给定入口文件路径字母序不在最前的清单 → 必现：不带 `--first` 时入口不在文档前部（manifest `first.path` 非入口）；带 `--first` 后 manifest `first.path` 为入口文件。
- 给定 `--first not-in-list.py` → 必现：非零退出，错误信息列出清单内可选路径。
- 给定 50 行/页 × 折行样本（有 soffice）→ 必现：render 报告标出实际行数不足页。
- 必不现：无 `--first` 调用产生 `reordered_first` 非空。

**代码评审节点**：`--first` 多次传入的顺序语义（按传入顺序排列，非字母序）；文档前部"入口必须在前"的既有验收（`source-code.md:38`）与新参数表述一致。

**分级 T2**：同 B4——多文件、交付物行为变更、有测试覆盖、只读转换。

### B6 登记表重定位为在线填报工作底稿 + 提交前校验 [P1]

**如何改**（文件：`references/registration-form.md`、`scripts/registration_form.py`、新增 `scripts/check_submission.py`；依赖 B2 的清单格式、B3 的测试基建）：

- 锚点 `registration-form.md:1-11`：重写定位——按「官方口径声明」第一条要点（在线填报、签章页、不得改打印比例）写入流程描述并附核对记录（全局红线 2）；用户提供的 `.xlsx` 更名为"在线填报工作底稿"，仅用于收集字段，不是正式登记表交付物。
- 新增"在线填报映射"节：底稿字段 → 在线表单栏目对照表 + 完成勾选列（`filled` / `pending`），与事实表 `user_confirmed` 状态联动。
- 锚点 `registration-form.md:40`（"合计控制在 500–1,300 字"）：改为引用 B1 的唯一出处（"内部字数预算，见 copyright-code-review F 项"），不重复数值定义之外另立出处。
- `registration_form.py:2`（docstring，现文 "Excel registration template"）：语义改为"在线填报工作底稿"模板工具；行为不变。`:71` 的 audit warning（现文为英文打开验证提示）不含"登记表"措辞，确认无需改动。
- 新增 `scripts/check_submission.py`：
  - 输入：`--docs` 待上传文件清单（签章页 PDF、说明书、源代码文档，可重复）+ `--ownership` 权属文件清单 JSON（B2 schema）+ `--output submission-check.json`。
  - 检查：文件存在、可解析、页数（fitz）、大小非零；docx 类文件提示先经 render_check 实测；权属清单逐项核 `provided/pending`，pending 列为阻断内部提交项。
  - 机器不可判定项（签章清晰度、打印比例、在线表单与底稿一致性）在报告中列为 `manual` 项，不给出通过结论。
  - 遵循全局红线 1（拒绝覆盖输出）。
- `test_registration_form.py` 扩充 + 新增 `test_check_submission.py`：缺文件必现报告缺失项；pending 权属项必现阻断列表；manual 项必现；输出已存在拒绝。

**如何验证**：
- L1：pytest（上列新用例）。
- L2：用 fixtures 构造一份签章页 PDF（fitz 生成单页空 PDF）+ 含 pending 项的权属清单 → 报告断言。
- 红线回归：registration_form.py 现有 inspect/fill 行为（B3 用例）不回归。

**验收标准**：
- 给定缺失的 PDF 路径 → 必现：报告缺失条目，非零退出。
- 给定权属清单含 pending → 必现：报告阻断列表含该项；必不现：整体结论为"可提交"。
- 给定全部 provided + 文件齐全 → 必现：机检项通过，manual 项仍列出（必不现"官方通过"类结论措辞）。

**代码评审节点**：报告措辞不得暗示官方结果（红线 2）；`--ownership` schema 与 B2 ownership.md 定义逐字段一致。

**分级 T2**：新脚本 + 交付链路文档重定位；邻近"正式提交物"契约（红线 3 管辖域），但机检项与措辞约束由本批测试断言直接覆盖（pending 权属项必现阻断、报告无官方结论措辞为必现断言），故不升 T3；无外部状态变更。

### B7 回归收口 [P3]

**如何改**（依赖 B1–B6 全部）：

- 全量 `pytest plugins/copyright-skills/tests -q` 通过。
- `software-copyright-cn/SKILL.md:17-20`（工作流第 4、7 步）：与新脚本对齐——产物清单加入 render-report、submission-check、权属清单；交付描述中"登记表"措辞改"在线填报工作底稿"。
- 清理工作区未跟踪的 `skills/copyright-code-review/scripts/__pycache__/`（可选）。注：经核实，pyc 未入库，根 `.gitignore` 已含 `__pycache__/` 规则，无需改 `.gitignore`。
- `.claude-plugin/plugin.json` 与 `.codex-plugin/plugin.json` 版本 1.0.0 → 1.1.0；仓库 `CHANGELOG.md` 记录本次整改。

**如何验证**：全量测试 + 两份 plugin.json 版本一致 + `git status` 干净（含无未跟踪 pyc）。

**验收标准**：PASS = 全量用例绿、版本双文件一致、Grep 全插件无 `2026.3.15` / `官方 AI 查重` / `必被驳回` / `征信` 残留；FAIL = 任一残留或版本不一致。

**代码评审节点**：SKILL.md 描述与新行为无漂移；CHANGELOG 只记录本方案范围的改动。

**分级 T1**：文档与元数据收口，验证以机械核对为主。主控亲自机械验证收口。

## 执行说明

- 各批执行、派单、审计与波次收口流程见 `rulertu-flow:implement-plan`，本方案只定级不定流程。
- B4/B5 的渲染实测依赖本机 LibreOffice（soffice）；环境缺失时按脚本降级路径输出人工核对项，不阻断其他批次。
- B1/B2/B6 涉及官网口径的表述，执行时须重新核对官网现行文本并记录 URL + 日期；本方案写作环境禁用联网检索，未能预先附 URL，属已知缺口。
