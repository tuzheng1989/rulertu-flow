# B2 Auditor 审计报告（契约审计）

说明：Auditor 只读契约未落盘，本报告由主控原样落盘（全文无增删）。

## 结论：通过

全部 7 项审计要点核验成立，主控修复（临时名防覆盖）经代码通读 + 真跑复现双重实证有效。分级统计：P0=0，P1=0，P2=0，P3=2（均为记录性，不阻断）。

## 一、逐条核验结果

### 1. 随迁零改动 — PASS（双视角）
- `git diff --cached -M --name-status | grep gongwen`：references/gbt9704-reference.md 与 scripts/gongwen-to-docx.py 均 R100（暂存视角）。
- `git diff HEAD -M --name-status -- '*gongwen*'`：两文件相对 HEAD 仍 R100（暂存+工作区联合视角零内容差异）；SKILL.md 为 R070（预期内改写）。

### 2. 新脚本质量（gongwen-to-pdf.py，148 行全文通读）— PASS
- Word 检测：check_word_available()（L26-41）Dispatch 探测实例在 finally 中 Quit（仅非 None 时，自身负责清理）；pywin32 ImportError 单独友好提示；不可用时 stderr 提示并 exit 1，无栈崩。
- 双模式分流：输入按扩展名分流——.md 链式（subprocess 以 sys.executable 调同目录 gongwen-to-docx.py，check 退出码 + 产物存在性，失败透传子进程 stderr）；.docx 直转永不删除。
- 临时名自洽：docx_path 单点赋值（L124 链式临时名 stem + ".gongwen-tmp.docx" / L128 外部输入本体），生成（L126）、转换（L130）、删除（L135 unlink）、--keep-docx 判断（L133）四处引用同一变量，天然一致；临时名与 stem + ".docx" 不同名。
- 错误路径全覆盖（6 处 sys.exit(1)：L59/75/79/102/107/113）：文件不存在 / 类型不支持 / Word 不可用（含缺 pywin32）/ 中间 docx 生成失败 / 转换异常（附占用提示）/ pdf 未落盘或空；中间 docx 删除失败降级警告不阻断。实测"文件不存在"路径 exit 1 + 友好提示。
- argparse 契约与 SKILL.md 一致：用法行 L26 与脚本参数逐字对应；--help 实跑正常。

### 3. SKILL.md 改写 — PASS
（156 行）L2 name: gongwen-trans；L4 description 双格式逐字对应方案决策 3；输出格式节 L38-44 默认 docx / pdf 路由 / 中间 docx 生命周期 / 需本机 Microsoft Word / 与 docs-trans 互斥边界；依赖节 L46-49 四项；触发词 L8 三词齐；旧名 gongwen-docx 零残留；常见问题表新增 Word 依赖行。version 1.2.0 自加项经主控明示接受，复核认可。

### 4. 主控修复复验 — PASS（逻辑 + 真跑双重复核）
- 逻辑确认：临时名四处引用同一变量分析。
- 真跑复现（mktemp 临时目录，3.11-arm64，样稿取自冒烟证据，同目录预置哨兵外部 audit.docx）：链式转换 exit 0 → 外部 audit.docx 哨兵内容原样保留（未被覆盖/删除）→ audit.gongwen-tmp.docx 已清理 → audit.pdf 产出（%PDF 头）。数据丢失风险修复实证有效。转换结束数分钟后 tasklist 查 WINWORD.EXE 零残留。

### 5. 边界纪律 — PASS
B2 git 改动全集四条全部落在 gongwen 边界内；B1（docs-trans）与 B2 文件集零交集；冒烟产物未污染技能目录；pip install 写用户 site-packages 系委派单明示授权。

### 6. 验收复核
8 项命令复跑全部与 Executor 声明一致（详见第三节原表）。

### 7. 冒烟真实性 — PASS（1 处时间线注记，见 P3-2）
产物五件齐全；sample-notice2.docx 不存在（默认删除语义）；三个 pdf 文件头 %PDF、pypdf 页数 1/1/1、均 176,362 B 与日志一致。COM 断连 flaky 如实记录、定向复跑通过、未隐瞒。路由推演 raw-routing.md 3/3 可对到当前 SKILL.md 实文。

## 二、问题清单

**P3-1（记录误差）**：executor-log 载 "sys.exit(1)" 4 处，实际 6 处——少记非多记（错误路径实际更全），不影响契约；建议日志类计数以 grep -c 原样誊抄。

**P3-2（证据留痕建议）**：冒烟 run 2 的 sample-notice2.pdf 时间戳晚于 executor 三 run，系主控修复验证时重跑覆盖（内容同源同字节数，断言在当前产物上仍成立）。建议后续主控复跑产物用独立文件名（如 *-master.pdf）避免覆盖 executor 原件——**主控采纳此流程改进**。

## 三、审计过程说明

全程只读；复现实验在 mktemp 临时目录进行，结束后已清理；Word COM 真跑一次 + 错误路径一次，均无仓库侧副作用。

**最终结论：B2 执行阶段通过，主控标注可采信成立，可进入 B3 联动收尾。**
