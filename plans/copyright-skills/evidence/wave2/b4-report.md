# B4 回报摘要

执行人：Executor（B4/T2），日期 2026-09-03。
方案：plugins/copyright-skills/plans/2026-09-03-review-rectification.md 的 B4 批次。

## 一、改动文件清单

1. build_manual_docx.py（修改）
2. render_check.py（新增）
3. manual.md（修改）
4. test_build_manual_docx.py（翻转 1 个用例）
5. test_render_check.py（新增）

## 二、锚点改前改后

### build_manual_docx.py

- EXAMPLE（原 :19-33）：evidence 字段保留，语义不变；加注释说明它不进正文、只进旁路 audit JSON。
- 原 :133-136：删除正文"材料复核依据"段落写入。改后正文无该段落。
- 原 :142-151：audit dict 新增 page_evidence。键为内容页序号（1 起、字符串），值为该页 evidence 列表；无 evidence 的页省略。

### render_check.py（新增）

路径：scripts/render_check.py（software-copyright-cn 技能 scripts 目录，与两个构建器同目录）。

- `count_pdf_lines(pdf_path, min_lines)`：fitz 逐页提取文本，按换行拆分后非空行计数；报告含 render_checked、total_pages、pages、under_pages、min_lines、line_definition。
- `convert_to_pdf(docx, soffice, out_dir)`：调 soffice --headless --convert-to pdf 输出到临时目录；失败抛 RuntimeError。本函数是可替换接缝（测试注入假转换器验证）。
- soffice 不可用：非零退出（2），stderr 提示"无法渲染校验，需人工在 Word/PDF 中逐页核对"，不产出任何报告。
- 输出已存在：拒绝覆盖（refusing to overwrite output，全局红线 1）。
- 临时转换目录：TemporaryDirectory，用后自动清理（测试断言目录已不存在）。

### manual.md（修改）

- 构建命令段：追加 render_check 步骤（--min-lines 30 --output render-report.json）。
- 新增页数口径段：官方要求不足 60 页全部提交、每页不少于 30 行；"至少 10 页"是内部下限（核对记录：官网申请须知 2026-09-03，URL 待人工补充）。
- 新增 render_check 使用说明：soffice 缺失时脚本不伪造通过，转人工核对项。
- 完成标准：新增"渲染实测每页 ≥30 行，不足页整改后复测"；新增 evidence 只进旁路 audit JSON 的说明。

### test_build_manual_docx.py（翻转）

- 用例由 `test_evidence_written_to_body_and_audit` 翻转为 `test_evidence_kept_out_of_body_and_written_to_audit`：断言正文无"材料复核依据"字样、不含任何 evidence 路径；audit JSON 的 page_evidence 与 spec 一致（无 evidence 页省略）；evidence_references 计数保留断言。
- 文件头锚点注释同步更新。

### test_render_check.py（新增，8 用例）

3 个函数级（count_pdf_lines：逐页行数、不足页清单、口径字段、全达标、空行不计）+ 5 个 CLI 级（soffice 缺失非零退出、--soffice 无效路径、拒绝覆盖、docx 不存在拒绝、注入假转换器全流程含临时目录清理断言）。

## 三、验证命令与退出码

| 命令 | pytest 退出码 | 结果 |
|---|---|---|
| 改动前基线 `python -m pytest plugins/copyright-skills/tests -q` | 0 | 29 passed |
| 切片 1 红 `pytest test_build_manual_docx.py -q` | 1 | 1 failed（test_evidence_kept_out_of_body_and_written_to_audit）+ 3 passed |
| 切片 1 绿 同上 | 0 | 4 passed |
| 切片 2 红 `pytest test_render_check.py -q` | 1 | 2 failed + 1 error（模块未创建） |
| 切片 2 绿 同上 | 0 | 3 passed |
| 切片 3 红 同上 | 1 | 5 failed + 3 passed（CLI 用例，main 未实现） |
| 切片 3 绿 同上 | 0 | 8 passed |
| 收尾 `python -m pytest plugins/copyright-skills/tests -q` | 0 | 44 passed，日志落盘 plans/evidence/wave2/b4-pytest.log |
| 收尾 Grep `材料复核依据` 于 build_manual_docx.py | — | 0 命中，断言通过 |

## 四、TDD 红绿证据（先失败用例名，后通过）

- 切片 1：红 test_evidence_kept_out_of_body_and_written_to_audit（正文含"材料复核依据"断言失败）→ 绿 4 passed。
- 切片 2：红 test_count_pdf_lines_reports_per_page_and_under_list 等 3 个（模块不存在）→ 绿 3 passed。
- 切片 3：红 test_cli_soffice_missing_fails_loudly 等 5 个（main 未实现）→ 中途修正（注入用例需传占位 --soffice；Path/str 断言类型修正）→ 绿 8 passed。

## 五、偏差与风险

1. test_render_check.py 不能改 conftest.py（禁改），改为文件内定义被测脚本路径，复用 conftest 的 run_cli、load_module fixtures。接缝等价，未改共享设施。
2. page_evidence 语义定为：键 = 内容页序号（1 起、字符串），无 evidence 的页省略。后续消费方（B6 check_submission 等）需按此读取。
3. render_check.py 的 main 先 reconfigure stdout/stderr 为 utf-8：Windows 管道默认 GBK，中文降级提示需 utf-8 才能被 subprocess utf-8 捕获（委派单未禁止，属必要辅助）。
4. 本机无 soffice，soffice 存在时的真实转换路径未在本机验证，仅有注入假转换器的等价验证（委派单第三切片明确以此替代）。
5. 全量测试触发依据：委派单收尾验证第 1 条明确要求全量 pytest 并落盘，非 executor 自行扩大。
6. 未提交未推送。git status 中 SKILL.md、registration-form.md、ownership.md、check_submission.py、plans/ 等其他改动属并行批次（B1/B2/B6/B3），本任务未触碰。
