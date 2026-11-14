# B1 Auditor 审计报告（契约审计）

说明：Auditor 只读契约未落盘，本报告由主控原样落盘（全文无增删）。

## 结论：通过（无 P0/P1；1 项 P2 建议并入 B3 顺手修复）

分级统计：P0=0，P1=0，P2=1，P3=5。六条验收标准全部成立（冒烟项按委派单前置声明的"环境性失败归因不算失败"原则判定）。

## 逐条审计要点

### 1. mode 文档脚本路径断言（最高风险项）——通过，自报计数完全复核一致
- 复跑证据目录 path-assert.py：断言 42 处，PASS 41 + FAIL 1（唯一 FAIL = ../scripts/url/node_modules，文档语义"若不存在则 bun install"，运行时产物，豁免成立），退出码 1。Executor 自报计数逐项吻合（anydoc 8 + url 11 + mdpdf 16 + htmlpdf 7 = 42）。
- 独立完整性扫描（七类形态：.claude/baseDir/skills/盘符/裸 scripts/裸 assets/裸脚本名）：四份 mode 文档内无任何漏断言的可解析路径指针。残留命中均为合法（~/.cache 用户家目录、assets/files/ B 节约定、位置描述 prose）。
- 结论：上一批 13 处死指针类风险在本批 mode 文档层面零复发。

### 2. rename 保真——通过（最严阈值复核）
- git diff 9dfadac^ 9dfadac -M100%：B1 部分恰好 33 条 R100 + 2 条 D，无任何 RM/内容改动条目。
- blob 哈希抽查：url vendor src/index.ts 迁移前后哈希同为 0be48c3d9de2d2e262ad5e8cc352e189de5954be。
- 工作区 4 份 RM diff 全文通读：改写面全部可归因（anydoc 29 行、url 36、mdpdf 35、htmlpdf 20 行），无夹带。

### 3. EvoCenter 旧语境清理——通过
- grep -rn "EvoCenter" plugins/work-skills/skills/ → 零命中（exit 1）。
- B 节 inbox/llm-wiki 表述保留与主控最小改动裁定一致（不含 EvoCenter 字样）。

### 4. 新 SKILL.md——通过
- 54 行 ≤ 200；frontmatter 四组触发词 + 互斥边界三外部技能齐全；路由表 4 行与 modes/ 实际一一对应；scripts 索引与实际树一致；依赖速查逐 mode 比对全部一致。

### 5. 计数守恒——通过
- 基线 git ls-tree -r 9dfadac^（四源目录）= 35 个追踪文件 = 33 随迁 + 2 README 删除，逐一对账闭合；基线中不存在 caption.py，无漏迁文件。
- docs-trans 现树 = 33 追踪 + 1 未追踪 SKILL.md；__pycache__ 补删与 url 冒烟 node_modules 清理均确认；两 README 删除后无残留引用方。

### 6. 边界纪律——通过
- 工作区 work-skills 改动仅 4 份 mode 文档 + 未追踪 SKILL.md；CHANGELOG.md 改动属其他任务在制品零命中；B1 与 B2 文件集零交集；用户在制品零触碰。

### 7. 验收命令复跑 + 冒烟与路由真实性——成立
- L1 三条 + path-assert.py + route_ocr.py --help 复跑全部一致。
- 冒烟产物字节数与自报精确一致；mdpdf-run.log 实读 traceback 首行即新路径 line 26 import（路径断裂排除成立）；anydoc 已知限制在 mode 文档 95-96 行预先记载（非事后编造）；raw-routing.md 8 条判定引述逐字存在。
- 方案"冒烟 4/4"被委派单执行前显式修订为"环境性失败归因不算失败"——非事后弱化契约，采信。

## 问题清单

**P2-1（唯一实质缺陷，建议并入 B3）**：references/mermaid-syntax.md:297 残留旧命令 `python scripts/md_to_pdf.py input.md --timeout 120000`——随搬迁断裂；方案 L1 grep（连字符词表）与 B3 计划 grep 均不会命中它（此处为下划线 md_to_pdf），若不主动修复将永久静默残留。建议 B3 顺手改这一行并在提交说明注明偏离决策 4 零改动约定，且 B3 兜底 grep 词表补充下划线形态。

**P3-1**：executor-log §2 自报"失败 0，退出码 0"与"1 条件路径"矛盾（脚本任一 FAIL 即 exit 1）——推测断言跑在 url 冒烟 bun install 之后、清理之前。计数 42/41/1 本身复核无误，仅退出码记录不实。
**P3-2**：master-spot-check 记"39/40"计数与脚本实跑 42 不符（结论同）。证据记录数字瑕疵。
**P3-3**：anydoc-to-md.md:12 表格内 winocr.ps1 已改全路径而相邻 ocr_pdf.py 仍裸名——描述性提及非解析指针，纯风格不一致。
**P3-4**：scripts/mdpdf/package.json 的 npm scripts 随层级失效（无文档指路）；executor-log §1 表格注"见第 4 节归因"但 §4 未展开——交叉引用悬空。
**P3-5**：install.py:45 parent.parent/requirements.txt 新布局断裂——Executor 留痕准确，维持移交。

## 总评

完成度：B1 全部改动清单 1-5 落地，六条验收成立。证据真实性：产物字节数、traceback、断言计数、路由引述逐项吻合；仅两处记录数字瑕疵。契约对齐：设计决策 1-6 逐条兑现；现场处置均有记录；无未申报越界。

建议下一步：B1 剩余部分（4 mode 改写 + SKILL.md）可提交收口；P2-1 并入 B3 改动清单；B3 全仓兜底 grep 词表补充下划线形态 md_to_pdf。
