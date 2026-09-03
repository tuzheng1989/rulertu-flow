# B4 证据包审计报告（Auditor 回报归档，主控代写）

结论：PASS（5 条 P2，移交 B7 收口；无 P0/P1）

## 验收清单（5/5 PASS）
1. evidence 出正文 + page_evidence：正文构建路径"材料复核依据"0 命中；audit dict 新增 page_evidence（键=str 内容页序号 1 起、无 evidence 页省略），语义在代码注释/测试 docstring/Executor 回报三处一致
2. render_check.py：接口齐备（--docx/--min-lines 30 默认/--output/--soffice 注入）；失败路径逐行排查——所有失败分支（soffice 缺失 return 2、转换 RuntimeError→return 2、fitz 缺 SystemExit）均不触碰输出文件，不存在 render_checked:true 假成功路径；拒绝覆盖先于存在性检查；临时 PDF 经 TemporaryDirectory 三路径（成功/RuntimeError/SystemExit）均清理，测试断言 out_dir 不存在；行数口径 LINE_DEFINITION 写入报告
3. manual.md：render_check 步骤（--min-lines 30）、官方口径段+核对记录、完成标准渲染实测项与 evidence 旁路说明全落地
4. 既有行为无回归：min-pages/无图/拒绝覆盖三用例在且绿，拒绝分支 diff 零改动
5. 测试质量：翻转真实（新用例断言新行为非改名）；render 期望值为独立真值（fitz 造 PDF 35/10/0 等）；run_cli 为 subprocess 真进程非 mock

## 独立验证
- 定向重跑 test_render_check + test_build_manual_docx → 12 passed（soffice 缺失分支即真实环境分支）
- diff 范围 5 文件经 diff+mtime 双重核对未越界；conftest.py 未动

## 发现清单（均 P2，移交 B7）
1. [P2] manual.md:30 核对 URL 待补 —— 红线 2 wave 级已知缺口，B7 统一补录并写入 review-needed 防遗忘
2. [P2] test_render_check.py:96 soffice 缺失用例环境耦合 —— 装 LibreOffice 的机器会假失败；改显式 --soffice 不存在路径或加 skipif
3. [P2] test_render_check.py:71 "空行不计"用例未构造空行 —— 改 docstring 如实描述或构造含空白行样本
4. [P2] build_manual_docx.py:140 page_evidence 键为内容页序号、与 docx 物理页号恒差 2 —— 消费侧文档注明偏移防误读
5. [P2] render_check.py convert_to_pdf soffice 真实路径本机未实测（已披露） —— 有 soffice 的环境补端到端实测

（完整论证见会话内 Auditor 回报；本文件为主控按其全文要点归档。）
