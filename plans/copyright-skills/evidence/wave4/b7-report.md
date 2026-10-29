# B7 回报摘要（回归收口 + 三波审计移交 P2 项）

执行人：Executor（批次 B7 / T1）
日期：2026-09-03
测试基线：全量 52 passed（委派单预期 ≥53，偏差说明见"偏差"第 1 条）；全绿，无回归。

## 一、逐任务回报

### A. SKILL.md 工作流对齐（方案 B7）

- A1（SKILL.md 第 4 步，改前 :18）
  - 改前：`4. 生成用户要求的产物。登记表读 [references/registration-form.md]…只加载当前产物需要的参考文件。`
  - 改后：指代用户提供 xlsx 的"登记表"改为"在线填报工作底稿"；产物清单加入 render-report（`scripts/render_check.py` 渲染实测说明书/源代码 `.docx` 每页行数）、submission-check（`scripts/check_submission.py` 提交前校验）、权属文件清单。
- A2（SKILL.md 第 7 步，改前 :21）
  - 改前：交付清单为原模板副本、说明书/源代码 `.docx`、代码清单 JSON、事实表、`review-needed.md`。
  - 改后：交付清单加入权属文件清单、render-report、submission-check；新增"官网申请须知的核对 URL 为待人工补齐项，交付时列入 `review-needed.md` 防遗忘"。
  - 第 4、7 步之外未改动任何工作流步骤（`git diff` 核对：本批仅这两行变动；diff 中 description 与第 2 步新增行是 Wave 1–3 的未提交遗留，非本批产物）。

### B. P2 加固项

- B1（test_render_check.py `test_cli_soffice_missing_fails_loudly` 环境耦合）
  - 改前：依赖"本机 PATH 无 soffice"的真实环境，装了 LibreOffice 的机器上用例会因 soffice 查找成功而失败。
  - 改后：委派单提供了两个方向（改为显式 `--soffice` 或加 skipif 保留）。选择加 `@pytest.mark.skipif(shutil.which("soffice") is not None, reason=…)` 保留原用例：理由是该用例覆盖的是 `shutil.which` 返回 None 的 PATH 查找分支，与 :111 用例（显式坏路径）覆盖的代码路径不同；若按主方向改成显式 `--soffice <不存在路径>`，它与 :111 用例完全重复。加 skipif 后：无 soffice 机器上两用例都跑；有 soffice 机器上本用例跳过、失败分支仍由 :111 用例确定性覆盖。`import shutil` 已加。前提已写入 skipif reason。
  - 偏差说明：委派单主方向是"改为显式 --soffice"，我选了委派单明示的备选方向，理由如上。改动文件：`plugins/copyright-skills/tests/test_render_check.py`。
- B2（test_render_check.py 空行不计用例名不符实）
  - 改前：`test_count_pdf_lines_counts_nonempty_text_rows` 实际只写 5 行非空文本，无任何空白行，用例名"空行不计"不符实。
  - fitz 行为探测：`insert_text` 写仅含空格的行（`"   "`），`get_text()` 会原样返回该空白行（实测输出 `'only 0\n   \n'`）；写空字符串则不产生行。
  - 改后：重写为 `test_count_pdf_lines_ignores_blank_rows`——4 非空行 + 1 行仅空格文本，样本自检断言 `get_text()` 确实返回空白行（防止样本构造失效时用例自证），再断言计数为 4 而非 5。
- B3（test_build_source_docx.py 追加 1 用例）
  - 新增 `test_first_flag_applied_after_selection_over_3000`：main.py 3001 行 + app.py 2000 行（清单序 app 在前），`--first main.py`，断言 `total_physical_lines==5001`、`selection=="first-1500-and-last-1500"`、`reordered_first==["main.py"]`、`selected_line_count==3000`、`first/head_end/tail_start/last` 为独立真值（main:1/1500 + app:501/2000），锁死"selection 在 reorder 之后"。仅追加，既有用例未动。
- B4（check_submission.py 畸形 JSON）
  - 改前：`load_ownership` 直接 `json.loads`，非法 JSON 抛 traceback。
  - 改后：`json.loads` 包 `try/except json.JSONDecodeError`，`raise SystemExit(f"ownership checklist is not valid JSON: {path} ({exc})")`，报错含清单路径。
  - 配套在 test_check_submission.py 新增 `test_malformed_ownership_json_rejected`：断言非零退出、stderr 含 `ownership.json` 与 `not valid JSON`、`"Traceback" not in stderr`、不写输出。
- B5（test_check_submission.py 措辞断言）
  - 沿现有断言风格追加 `assert "官方" not in text`（紧邻既有 `assert "可提交" not in text`），注明红线 2。
- B6（registration-form.md 示例文件名加注）
  - `:12` inspect 命令与 `:35` fill 命令中 `"登记表.xlsx"` 后加 PowerShell 行内注释 `# "登记表.xlsx" 为示例文件名，以实际文件名为准`（选"加注"方案，最小改动，未改示例名本身）。

### C. 版本与变更记录

- C7：`.claude-plugin/plugin.json` 与 `.codex-plugin/plugin.json` version 1.0.0 → 1.1.0，Python 读取断言两文件一致（exit 0）。
- C8：CHANGELOG.md Unreleased 段新增 1 条 copyright-skills 1.1.0 条目（表述治理、权属决策表、在线填报工作底稿 + check_submission、构建器整改、pytest 基建）。未重排旧条目；期间两次手误改动旧 work-skills 条目文字，均已即时回滚，`git diff CHANGELOG.md` 确认净变更仅 +1 行。
- C9：明确不做三项，重申为交付后人工待办：
  1. 官网 URL 补录（本环境禁网，文档保持"URL 待人工补充"占位；SKILL.md 第 7 步已要求列入 review-needed.md）。
  2. soffice 端到端渲染实测（本机无 LibreOffice，渲染链路仅接缝级测试覆盖）。
  3. pyc 清理（`__pycache__/` 未入库，根 .gitignore 已覆盖，git status 无未跟踪 pyc，无需处理）。

## 二、验证命令与结果

| 命令 | 退出码 | 结果 |
|---|---|---|
| `python -m pytest plugins/copyright-skills/tests -q` | 0 | 52 passed, 5 warnings（基线 50 + 新增 2） |
| `rg -n --glob '!plans/**' --glob '!**/__pycache__/**' '2026\.3\.15\|官方.{0,4}查重\|必被驳回\|直接驳回\|征信' .`（copyright-skills 目录内） | 1（无匹配） | 0 命中 |
| 两份 plugin.json version 读取断言（== "1.1.0" 且一致） | 0 | claude: 1.1.0 / codex: 1.1.0 |
| `git status --porcelain` | — | 无未跟踪 pyc；本批改动均在委派单允许清单内 |

- 5 个 warning 均为 PyMuPDF 的既有 DeprecationWarning（与 B5 回报一致，非本次引入）。
- 全量 pytest 完整输出：`plugins/copyright-skills/plans/evidence/wave4/b7-pytest.log`。

## 三、偏差与剩余问题

1. 用例数 52 而非委派单预期 ≥53：本批净新增 2 个用例（B3 +1、B4 +1）。委派单 B2 项是原地重写既有用例（用例总数不变），B1 项加 skipif 不增用例，52 是委派单各项算术之和；"≥53"疑为主控把 B2 重写计入为净新增。未为凑数额外加用例。
2. B1 项选了委派单明示的备选方向（skipif 保留原用例）而非主方向（改显式 --soffice），理由：避免与 :111 用例完全重复，同时保留 PATH 查找分支的覆盖。
3. registration-form.md 的 :12/:35 加注采用 PowerShell 行内 `#` 注释，非正文加注——如主控要求正文加注可再调整。
4. 官网 URL 补录、soffice 端到端实测、pyc 清理三项为交付后人工待办（见 C9）。
