# B2 Executor 日志：gongwen-trans 升级（新增公文 PDF 输出）

- 日期：2026-11-14
- 执行者：Executor（rulertu-flow:executor）
- 契约：方案 `plans/work-skills/2026-11-14-docs-trans-consolidation.md` 第 2 节 B2 + 委派单 `delegation-B2.md`
- 纪律遵守：未 git commit；只动 gongwen-docx/（改名后 gongwen-trans/）边界；边界外文件零触碰

## 1. 改动清单

| # | 改动 | 状态 |
|---|---|---|
| 1 | `git mv plugins/work-skills/skills/gongwen-docx plugins/work-skills/skills/gongwen-trans` | 完成，rename 追踪 R100 |
| 2 | 新写 `scripts/gongwen-to-pdf.py`（~150 行） | 完成 |
| 3 | 改写 `SKILL.md`（136 → 156 行） | 完成 |
| 4 | requirements 处理：技能目录无 requirements 文件（与方案确认一致），依赖声明写入 SKILL.md 依赖节 | 完成 |

- `references/gbt9704-reference.md` 与 `scripts/gongwen-to-docx.py` 随迁零改动（`git diff --cached -M --name-status` 均为 R100）。
- SKILL.md 暂存视角为 `RM`（rename + 工作区改写）；`git diff HEAD` 因改写幅度大不再按 rename 展示（显示为 A+D 对），rename 追踪在暂存区（`git status --porcelain` RM / `git diff --cached -M` R100）持续成立。

## 2. gongwen-to-pdf.py 设计说明

- **接口**：argparse，位置参数 `input`（.md 或 .docx）；`--output`（pdf 路径，默认与输入同目录同名 .pdf）；`--keep-docx`。
- **--keep-docx 语义实现**：委派单要求"仅当 docx 是本脚本链式产出时删，外部传入的 docx 不删"。脚本自身要能判定"链式产出"，因此输入按扩展名分流——`.md` 为链式模式（内部 subprocess 调用同目录 gongwen-to-docx.py 产出中间 docx，pdf 成功后默认删除，`--keep-docx` 保留）；`.docx` 为外部传入模式（直接转换，永不删除，`--keep-docx` 无实际效果）。这是对委派单位置参数名 `docx_path` 的必要扩展（支持 .md 输入），动因是 --keep-docx 语义要求脚本自判链式产出，且方案决策 3 "内部先按既有流程产 docx" 指向同一设计。
- **Word 可用性前置检测**：`check_word_available()` 以 win32com Dispatch("Word.Application") 探测，探测实例在 finally 中 Quit（自己负责清理）；不可用（含 pywin32 缺失的 ImportError）时 stderr 提示"公文 PDF 转换需要 Microsoft Word（docx2pdf 依赖 Word COM）"并 sys.exit(1)，非栈崩溃。
- **转换**：`docx2pdf.convert(docx, pdf)`；完成后校验 pdf 存在且大小 > 0，print 输出路径与文件大小（KB）。
- **错误处理**：输入不存在 / 扩展名不支持 / 中间 docx 生成失败（子进程退出码非零或产物缺失）/ 转换异常（含文件占用提示）/ 转换后 pdf 缺失，均为友好 stderr 提示 + exit 1。实测"文件不存在"路径 exit 1 无栈崩。
- **Word 进程生命周期**：按委派单，docx2pdf 内部管理 Word 实例，脚本不额外手工 Quit；实测转换返回后 WINWORD.EXE 在数秒内自行退出（见冒烟观察），无真残留。
- **链式调用**：`subprocess.run([sys.executable, gongwen-to-docx.py, md, -o, docx])`，check 退出码与产物存在性；失败时透传子进程 stderr。
- **依赖安装**：`pip install docx2pdf`（0.1.8，委派单授权）。冒烟执行环境为 Python 3.11-arm64（`C:/Users/tuzhe/AppData/Local/Programs/Python/Python311-arm64/python.exe`）——默认 `python`（3.12-arm64）缺 python-docx/gongwen 既有依赖链，docx2pdf 已同装两环境；SKILL.md 依赖节已声明 python-docx、PyYAML（既有）与 docx2pdf+pywin32（仅 pdf 需要）。

## 3. 验收命令与退出码

| 锚点 | 命令 | 退出码 | 结果 |
|---|---|---|---|
| git mv | `git status --porcelain \| grep gongwen` | 0 | RM/R 状态见第 1 节 |
| 零内容改动 | `git diff --cached -M --name-status \| grep gongwen` | 0 | 三随迁文件 R100 |
| L1 docx2pdf | `python -c "import docx2pdf"` | 0 | OK |
| L1 新脚本 | `gongwen-to-pdf.py --help` | 0 | usage 正常 |
| SKILL.md name | `grep -n "^name:" SKILL.md` | 0 | L2 `name: gongwen-trans` |
| 触发词 | 逐词 grep "生成公文 pdf" / "公文转 pdf" / "红头文件 pdf" | 0×3 | 全在位 |
| 输出格式节/依赖节 | `grep -n "## 输出格式\|## 依赖\|docx2pdf\|Microsoft Word" SKILL.md` | 0 | L38 输出格式节、L46 依赖节、L49 docx2pdf 声明 |
| Word 检测在位 | `grep -n "check_word_available\|Word.Application\|sys.exit(1)" gongwen-to-pdf.py` | 0 | L26/35 + 4 处 exit(1) |
| 顶层清零 | `ls skills/ \| grep gongwen-docx` | 1（零命中） | 通过，仅存 gongwen-trans |
| 错误路径 | `gongwen-to-pdf.py not-exist.docx` | 1 | "错误: 文件不存在" 友好提示非栈崩 |

## 4. 冒烟（L2 真跑）

产物目录：`plans/work-skills/.flow-evidence/2026-11-14-docs-trans-consolidation/B2/smoke-gongwen/`

样稿：`sample-notice.md` / `sample-notice2.md`（同内容：frontmatter 带 doc_type: 通知 + 发文字号 + 主送机关 + 正文两段中文编号 + 特此通知 + 落款）。

| Run | 命令形态 | 退出码 | 断言 |
|---|---|---|---|
| 1 | `gongwen-to-pdf.py sample-notice.md --keep-docx` | 0 | sample-notice.docx 保留（37,918 B）；sample-notice.pdf 产出（172.2 KB） |
| 2 | `gongwen-to-pdf.py sample-notice2.md`（默认） | 0 | "[INFO] 已删除中间 docx"；sample-notice2.docx 不存在；sample-notice2.pdf 产出 |
| 3 | `gongwen-to-pdf.py sample-notice.docx --output sample-notice-from-docx.pdf` | 0（复跑后） | 外部 docx 未被删除；pdf 产出 |

文件断言：4 产物存在且非空 PASS；`sample-notice2.docx` 已删除 PASS；三个 pdf 文件头 `%PDF` PASS；pypdf 页数 1/1/1 页（≥1）PASS。

Word 进程观察：run 3 首跑遇 COM 断连（-2147417848 RPC_E_DISCONNECTED），检查无 WINWORD 残留后按 flaky 规则定向复跑一次即成功；复跑返回时 WINWORD.EXE 仍在收尾，等待 6 秒后复查已自行退出——docx2pdf 的 Quit 为异步，无真残留，与"不额外手工 Quit"设计一致。连续多次转换时 COM 断连为 docx2pdf 已知瞬时问题，复跑可过；已在脚本错误处理中给占用/失败提示，如后续高频使用可考虑加重试（超出本单边界，未做）。

## 5. 路由推演（L3）

3/3 通过，详见同目录 `raw-routing.md`（独立只读 subagent 仅凭 SKILL.md 决策）：
1. "转成公文 docx" → gongwen-to-docx.py（PASS）
2. "生成公文 pdf" → gongwen-to-pdf.py（PASS）
3. "普通文档转 pdf" → 指 docs-trans md-to-pdf mode，不进本技能（PASS）

## 6. 观察与剩余问题

- 暂存区存在 B1 批次（docs-trans 组建）rename——与方案"B1/B2 文件集互斥可并行"预期一致，两批次边界无交集，本单未触碰 docs-trans 相关文件。
- SKILL.md 依赖节除方案点名的 python-docx/docx2pdf 外，如实列入 PyYAML（gongwen-to-docx.py 既有 import，标注"既有依赖"），纯文档准确性补充，无行为变化。
- 技能 frontmatter version 1.1.0 → 1.2.0（新增 PDF 输出功能，minor 升级惯例；方案未点名，如需回退仅一行）。
