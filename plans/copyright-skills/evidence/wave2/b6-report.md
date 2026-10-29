# B6 收尾报告（登记表重定位 + 提交前校验）

日期：2026-09-03 ｜ 执行者：Executor（T2 子任务）｜ 方案：`plugins/copyright-skills/plans/2026-09-03-review-rectification.md` B6

## 改动文件清单

| 文件 | 改动 |
|---|---|
| `skills/software-copyright-cn/references/registration-form.md` | 重写定位为"在线填报工作底稿"，新增"流程口径"与"在线填报映射"节 |
| `skills/software-copyright-cn/scripts/registration_form.py` | 仅 :2 docstring 措辞（行为零改动） |
| `skills/software-copyright-cn/scripts/check_submission.py` | 新增提交前机检脚本 |
| `tests/test_check_submission.py` | 新增 7 用例 |
| `tests/test_registration_form.py` | 未追加（见"偏差与决策"） |

未触碰 build_*.py、manual.md、source-code.md（B4/B5 并行批次文件）。

## 锚点改前 / 改后

- `registration-form.md:1-11` → 改后 `:1-11`："# 登记表" → "# 在线填报工作底稿"；新增"流程口径"节（在线填报 / 在线打印签章页 / 签章后上传 PDF / 不得擅自改变签章页格式和打印比例；核对记录 2026-09-03，URL 待人工补充）；`.xlsx` 定位改为工作底稿，"不是正式登记表交付物"。
- `registration-form.md:40`（"合计控制在 500–1,300 字"）→ 改后 `:64`："内部字数预算 500–1,300 字，唯一权威出处见 copyright-code-review SKILL.md F 项，本文件不重复展开为硬性要求"。
- 新增"在线填报映射"节（改后 `:41-55`）：11 行底稿字段 → 在线表单栏目对照，勾选列 `filled/pending`，注明与事实表 `user_confirmed` 联动（未确认不得标 `filled`）。
- `registration_form.py:2`：`"""Inspect or safely fill a copied Excel registration template."""` → `"""Inspect or safely fill a copied Excel worksheet for the online registration form."""`
- `registration_form.py:71` audit warning：实读为英文打开验证提示（"Open the output in Excel or LibreOffice to verify…"），不含"登记表"措辞，按委派单不改。

## TDD 红绿证据

1. 红：先写 `test_check_submission.py` 7 用例 → `7 failed`（脚本不存在）。
2. 中间红：实现后 1 failed（`test_invalid_status_rejected`）——根因：SystemExit 消息含中文条目名，Windows 子进程 stderr 按 cp936 编码写出，父进程 utf-8 解码失败 → `stderr=None`。修复：脚本 `main()` 内 `sys.stderr.reconfigure(encoding="utf-8", errors="replace")`。
3. 绿：`test_check_submission.py` → 7 passed。

## 验证命令与结果

| 命令 | 退出码 | 结果 |
|---|---|---|
| `python -m pytest plugins/copyright-skills/tests/test_check_submission.py plugins/copyright-skills/tests/test_registration_form.py -q` | 0 | 11 passed（7 新 + 4 既有回归） |
| `python -m pytest plugins/copyright-skills/tests -q` | 0 | 44 passed，无回归（完整输出：`b6-pytest.log`） |
| Grep registration-form.md | — | 含"在线填报工作底稿"（:1,:9）、"签章"（:5）、"URL 待人工补充"（:5）；:64 含 `500–1,300` 且同句含"唯一权威出处" |

注：全量 44 = 基线 29 + 本批 7（check_submission）+ 并行批次 B4/B5 已落盘的 8（test_render_check.py）与 test_build_source_docx +2。全量绿不能单独归因 B6，但确认与并行改动互不回归。

## schema 消费与 ownership.md 逐字段一致性核对

schema 唯一出处：`references/ownership.md:39-60`（B2 产物，本批只消费）。

| ownership.md 定义 | check_submission.py 消费 | 一致 |
|---|---|---|
| `scenario` 六选一（:41,:50） | `SCENARIOS` 六元组逐一对应，越界 → SystemExit 不写输出（:60 消费规则） | 是 |
| `items[].status` 三态（:43,:53） | `STATUSES = ("provided","pending","na")`，越界 → 清单无效报错退出（:60） | 是 |
| `items[].file/type/note`（:43,:51-54） | `pending` 项透传 file/type/note 进 `blocked_items` | 是 |
| `pending` → 内部暂停提交（:59） | `blocked_items` 非空 → 退出码 1，报告不结论 | 是 |

## 供评审节点决策：`type` 是否收闭枚举

建议**维持开放**。ownership.md:52 现文为 `identity|contract|license|translation 等`，"等"是有意开放（官网口径更新时可增列）；check_submission.py 对 `type` 仅透传不校验，收闭与否不影响脚本行为。若评审决定收闭，应只改 ownership.md 一处并在其中列出封闭值，脚本无需同步改动（透传设计下不破坏兼容）。

## 偏差与决策记录

1. `test_registration_form.py` 未追加用例：委派单允许"仅追加行为类（现有行为）用例，没有就不加"。registration_form.py 仅 docstring 变化、无行为变化，:71 warning 明确不改；无新行为可锁定，追加措辞测试被明确禁止。既有 4 用例作为回归护航。
2. `conftest.py` 不在允许改动清单内，无法给 `scripts` fixture 增加 check_submission 路径；`test_check_submission.py` 内自持脚本路径常量，`run_cli` 等 fixture 照常复用。
3. `check_submission.py` 增加 `sys.stderr.reconfigure(encoding="utf-8")`（一行）：Windows 管道下中文文件名消息会被按 utf-8 读取的调用方解码失败（本批用例实测复现）。属新脚本自身可用性修复，非行为扩张。
4. registration-form.md :35 输出文件名示例由"软件著作权登记表-待确认.xlsx"顺改为"在线填报工作底稿-待确认.xlsx"（指代 xlsx 副本）；:12 `"登记表.xlsx"` 为用户磁盘文件名字面量，保留。完成标准新增两条（映射表 pending 收口、上传前跑 check_submission），属新定位的自然延伸。
5. 方案执行说明要求官网口径"重新核对并记录 URL"，本环境禁用联网检索，按方案既定缺口处理：写"URL 待人工补充"，与 B1/B2 同口径。

## 产物

- 测试日志：`plugins/copyright-skills/plans/evidence/wave2/b6-pytest.log`
- 本报告：`plugins/copyright-skills/plans/evidence/wave2/b6-report.md`
