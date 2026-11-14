# B1 执行日志：docs-trans 组建（四转换技能四合一）

- 执行者：Executor（B1 委派单）
- 日期：2026-11-14
- 契约：plans/work-skills/2026-11-14-docs-trans-consolidation.md（方案 B1 节）+ delegation-B1.md
- 工作目录：plugins/work-skills/skills/（Windows Git Bash）

## 1. 改动清单（rename 记录）

基线：四技能 git ls-files 共 35 个追踪文件。收口：33 随迁（全部 R100 rename）+ 2 README 删除 + SKILL.md 新写（未追踪）。

### 树搬迁（git mv，全部 R100 零内容改动）

| 源 | 目标 | 说明 |
|---|---|---|
| anydoc-to-md/scripts/（4 脚本） | docs-trans/scripts/anydoc/ | 整树 rename；随迁的未追踪 __pycache__（3 .pyc）在 L1-1 验证时暴露后删除（见第 5 节注记） |
| url-to-md/scripts/（13 文件含 vendor/ 2 文件、bun.lock、package.json） | docs-trans/scripts/url/ | 整树零内容改动 |
| md-to-pdf/scripts/（3 py） | docs-trans/scripts/mdpdf/ | git mv scripts→mdpdf 目录整体改名，3 py 平铺 |
| md-to-pdf/assets/（3 文件） | docs-trans/scripts/mdpdf/assets/ | 含 custom.css、example.md、md-to-pdf.config.json |
| md-to-pdf/package.json | docs-trans/scripts/mdpdf/package.json | 零内容改动（其中 npm scripts 的相对路径随层级失效，见第 4 节归因） |
| md-to-pdf/requirements.txt | docs-trans/scripts/mdpdf/requirements.txt | 零内容改动 |
| html-to-pdf/scripts/（convert.py、merge.py） | docs-trans/scripts/htmlpdf/ | 整树 rename |
| md-to-pdf/references/mermaid-syntax.md | docs-trans/references/mermaid-syntax.md | 零内容改动 |
| html-to-pdf/evals/（evals.json） | docs-trans/evals/evals.json | 首次 mv 因目标父目录已存在产生嵌套 docs-trans/evals/evals/evals.json，已二次 mv 上提修正为方案布局 |
| 四份 SKILL.md | docs-trans/modes/{anydoc-to-md,url-to-md,md-to-pdf,html-to-pdf}.md | rename 后内容改写（见第 2 节） |

### 删除

- git rm：md-to-pdf/README.md（213 行）、html-to-pdf/README.md（86 行）
- 删未追踪：anydoc-to-md/scripts/__pycache__/ 3 个 .pyc——注意：git mv 把未追踪 __pycache__ 一并带到 docs-trans/scripts/anydoc/，首次 rm 删的是已不存在的旧路径（rm -rf 静默成功）；L1-1 grep 命中 .pyc 内嵌旧路径字符串后在新位置补删
- 源目录清零：anydoc-to-md/、url-to-md/、md-to-pdf/、html-to-pdf/ 全部移除（含空目录 rmdir）

### 新写

- docs-trans/SKILL.md（54 行）：frontmatter（name: docs-trans，description 含四组触发词 + 互斥边界）+ 转换方向路由表 + 触发词分流 + 互斥边界 + scripts 四子目录索引 + 依赖速查

## 2. mode 文档改写明细（含路径断言）

四份 mode 文档统一形态：删 frontmatter → 正文最前加前缀行 `> 本文件为 docs-trans 的 <原名> mode（2026-11-14 组建）。执行入口与 mode 路由见 SKILL.md。脚本路径相对本文件所在目录（modes/）解析。` → 脚本引用改为 `../scripts/<引擎子目录>/...`（从 modes/ 出发可解析，断言即按此基准）。

### anydoc-to-md.md（7 处命令引用 + 1 处表格引用）

| 原路径 | 新路径 | 处数 | 断言 |
|---|---|---|---|
| .claude/skills/anydoc-to-md/scripts/route_ocr.py | ../scripts/anydoc/route_ocr.py | 3（14/105/112 行） | PASS |
| .claude/skills/anydoc-to-md/scripts/ocr_pdf.py | ../scripts/anydoc/ocr_pdf.py | 2（152/160 行） | PASS |
| .claude/skills/anydoc-to-md/scripts/clean_hallucinations.py | ../scripts/anydoc/clean_hallucinations.py | 2（197/198 行） | PASS |
| winocr.ps1（引擎表格裸名） | ../scripts/anydoc/winocr.ps1 | 1（11 行） | PASS |

另：标题"（EvoCenter 专用）"改为"（任意文档 → Markdown）"；description 随 frontmatter 删除（"EvoCenter 专用"旧语境消除）。B 节 inbox 导入型与边界节的 /llm-wiki 表述按最小改动原则保留（方案未点名，回报中说明此判断）。

### url-to-md.md（{baseDir} 变量机制 → 直接相对路径）

| 原形态 | 新形态 | 处数 | 断言 |
|---|---|---|---|
| ${BUN_X} {baseDir}/scripts/main.ts | ${BUN_X} ../scripts/url/main.ts | 1（10 行） | PASS |
| {baseDir}/scripts/node_modules | ../scripts/url/node_modules | 1（18 行） | COND（条件路径：文档语义"若不存在则 bun install"，未安装状态为本然，不计失败） |
| {baseDir}/scripts（bun install cwd） | ../scripts/url | 1（18 行） | PASS |
| 表格 scripts/*.ts 7 行 | ../scripts/url/*.ts | 7（25-31 行） | 全 PASS |

Agent 执行步骤改写为"本文档位于 modes/ 子目录，脚本树位于技能根 scripts/url/"的相对表述，去除 {baseDir} 变量替换步骤（保留 ${BUN_X} 解析）。

### md-to-pdf.md（15 处）

| 原形态 | 新形态 | 处数 | 断言 |
|---|---|---|---|
| scripts/md_to_pdf.py | ../scripts/mdpdf/md_to_pdf.py | 12（54-91 行命令 + 202 行） | 全 PASS |
| ./assets/custom.css | ../scripts/mdpdf/assets/custom.css | 2（70/204 行） | PASS |
| scripts/diagram_renderer.py | ../scripts/mdpdf/diagram_renderer.py | 1（203 行） | PASS |
| assets/md-to-pdf.config.json | ../scripts/mdpdf/assets/md-to-pdf.config.json | 1（205 行） | PASS |

### html-to-pdf.md（7 处）

| 原形态 | 新形态 | 处数 | 断言 |
|---|---|---|---|
| scripts/convert.py | ../scripts/htmlpdf/convert.py | 6（16-46 行） | 全 PASS |
| scripts/merge.py | ../scripts/htmlpdf/merge.py | 1（47 行） | PASS |

### 断言汇总

断言脚本：本目录 path-assert.py（python os.path.exists，从 modes/ 目录出发解析）。最终结果：**断言总数 42，PASS 41，条件路径 1（node_modules，预期缺失语义），失败 0，退出码 0**。

## 3. 验收命令与退出码

| # | 验收项 | 命令 | 结果 |
|---|---|---|---|
| L1-1 | 旧路径引用清零 | `grep -rn "skills/anydoc-to-md\|skills/url-to-md\|skills/md-to-pdf\|skills/html-to-pdf\|\.\./anydoc-to-md\|\.\./url-to-md\|\.\./md-to-pdf\|\.\./html-to-pdf" .`（cwd=docs-trans/） | 退出码 1，零命中 PASS |
| L1-2 | 旧 frontmatter 清零 | `grep -n "^name:" modes/*.md` | 退出码 1，零命中 PASS |
| L1-3 | SKILL.md 行数 | `wc -l SKILL.md` | 54 ≤ 200 PASS |
| L1-4 | 脚本树守恒 | `git ls-files` 对账 + `git diff --cached -M --name-status` | 33 随迁全 R100 rename + 2 D（README 预期删除）= 基线 35；工作树逐文件 exists 全部存在 PASS |
| L1-5 | 顶层清零 | `ls \| grep -E "anydoc\|url-to-md\|md-to-pdf\|html-to-pdf"`（cwd=skills/） | 退出码 1，零输出 PASS |
| L2 | 冒烟 4 项 | 见第 4 节 | 见第 4 节 |
| L3 | 路由推演 8 条 | subagent 只读 SKILL.md | 见第 5 节 |

rename 相似度核验：`git diff --cached -M --name-status` 范围内非 R100 条目仅 2 个 README 的 D（预期），无 RM——mode 文档改写发生在 rename staged 之后（工作区未 staged），staged 视角保持纯 rename。

## 4. 冒烟结果与归因

产物目录：本目录下 smoke-anydoc/、smoke-mdpdf/、smoke-htmlpdf/、smoke-url/。

### 4.1 anydoc（环境性失败·结构性，非 B1 失败）

- 输入：smoke-anydoc/sample.xlsx（openpyxl 3.1.5 造）
- 执行：`npx -y @firecrawl/anydoc sample.xlsx -o sample.md`（anydoc CLI 本机未装，走 mode 文档回退路径）→ 退出码非 0
- 归因：**环境性失败，且为结构性不可用，与搬迁无关**。anydoc 0.2.4 的 optionalDependencies 平台清单只有 darwin/linux/win32-x64，无 win32-arm64；`@firecrawl/anydoc-wasm32-wasi` registry 404（wasm fallback 不存在）；本机 Node 为 ARM64（报 win32-arm64-msvc 绑定缺失）。这正是 mode 文档预见并记载的已知限制（"无 win32-arm64 构建，此时 anydoc 不可用，走 OCR 管线或其他工具"）。
- 搬迁质量证据：`python route_ocr.py --help`（cwd=scripts/anydoc）退出码 0，usage 正常输出——anydoc 脚本树搬迁后可发现、可加载、可启动。
- 临时目录 fresh install 复核：npm i @firecrawl/anydoc 仅装入 1 包（optional deps 仍被跳过，npm bug 4828 复现），手动补装 wasm 报 404——确认非网络/缓存偶发。临时安装目录已清理。

### 4.2 md-to-pdf（环境性失败·依赖缺失，非 B1 失败）

- 输入：smoke-mdpdf/sample.md（含 mermaid flowchart 块）
- 执行：`python <skills>/docs-trans/scripts/mdpdf/md_to_pdf.py sample.md -o sample.pdf` → 退出码 1，报错 `ModuleNotFoundError: No module named 'playwright'`（md_to_pdf.py:26）
- 归因：**环境性失败（playwright 未安装；markdown2 亦未装，pygments 已装）**。关键证据：Traceback 首行路径即新路径 `docs-trans\scripts\mdpdf\md_to_pdf.py`——脚本从搬迁后位置被正确发现并加载，执行至第三方依赖 import 处停止，符合委派单"区分环境因素与路径断裂"的后者排除标准。未安装 playwright（方案未授权改环境；完整验证待依赖就绪后由后续批次或人工补跑）。

### 4.3 html-to-pdf（真跑成功）

- 输入：smoke-htmlpdf/sample.html（固定 body 1280x720，16:9 幻灯片样式）
- 执行：`python <skills>/docs-trans/scripts/htmlpdf/convert.py sample.html sample.pdf` → **退出码 0**
- 产物：sample.pdf（21,671 字节）；尺寸验证（pymupdf）：`首页尺寸: 960.0 x 540.0 pt (13.33 x 7.50 in), 比例 1.7778`——16:9 比例精确保留，Chrome CDP→headless 打印链路在新位置完整工作。

### 4.4 url-to-md（真跑成功）

- 输入：https://example.com
- 执行：先 `npx -y bun install`（cwd=scripts/url，bun 本机未装走 npx 回退）→ **93 packages installed（6.16s）**；再 `npx -y bun main.ts https://example.com -o <EV>/smoke-url/example.md` → **退出码 0**
- 产物：example.md（1,472 字节，frontmatter 完整：url/title/language/captured_at，defuddle 管道转换）+ example-captured.html 快照
- 归因：无失败。验证点：bun.lock/package.json 随迁后安装指引可执行（方案代码评审节点确认项）✓；Chrome CDP 渲染链路正常 ✓。冒烟产生的 node_modules 已清理（恢复零未追踪产物状态；.gitignore 旧规则路径修正归 B3）。

### 冒烟判定

4 项中 2 项真跑成功（htmlpdf/url），2 项环境性失败且均验证到"可发现、可加载"层面（anydoc 脚本树 --help 通过；mdpdf 脚本加载至依赖 import）。无一项失败源于路径断裂。符合委派单判定原则（环境性失败不算 B1 失败但归因记录）。

## 5. 路由推演（L3）

独立只读 subagent 仅读取 docs-trans/SKILL.md，对 8 条消息逐一判定（要求完全基于文档文本，禁止常识补全）：**8/8 与预期一致**——4 正例（1 anydoc / 2 url / 3 mdpdf / 4 htmlpdf）+ 4 边界（5 data-analysis / 6 gongwen-trans / 7 write-report / 8 anydoc OCR 路由）全部命中，每条均能在触发词分流表、路由表或互斥边界节找到唯一依据。完整判定与依据引述见本目录 raw-routing.md。

## 6. 边界与并行说明

- **【现场事件】B1 staged 内容被 B2 提交卷入**：B1 搬迁完成后、mode 文档改写期间，另一执行者的 B2 提交 `9dfadac`（"feat(work-skills): gongwen-docx 升级 gongwen-trans——新增公文 PDF 输出"）把当时暂存区全部内容一并提交，其中包含 B1 的 33 个 R100 rename + 2 个 README 删除（提交统计 52 files changed，R+D 39 条）。本执行者**未执行任何 commit**（纪律遵守）；rename 追踪在该提交中完好（`git show 9dfadac -M` 35 条 R100）。但该提交 message 只描述 B2、未提 docs-trans——提交内容与 message 不符属并行批次协调问题，**是否拆分、补 message 或接受现状由主控裁决**，本批次不动历史。B1 尚未提交的剩余内容：4 份 mode 文档改写（工作区 M）+ SKILL.md 新写（未追踪）。
- B2 已完成并提交（含 gongwen-to-pdf.py 新增），后续 B3 兜底 grep 时 gongwen-docx 旧路径在历史提交中属正常形态（CHANGELOG 历史记录同类豁免逻辑）。
- **超出方案锚点的现场处置**（2 处，均已修正并有记录）：evals 首次 mv 嵌套（已上提修正）；__pycache__ 随 git mv 带入新树（已补删，见第 1 节注记）。
- **遗留归 B3**：.gitignore:4 的 url-to-md node_modules 旧规则（现指死路径，新路径规则待 B3 改写）；write-report/data-analysis 6 处跨技能引用；根 README；plugin.json 升版。
- install.py:45 `parent.parent/requirements.txt` 在新布局下解析为 docs-trans/scripts/requirements.txt（断裂）——install.py 仅被 package.json npm scripts 与已删 README 引用，mode 文档安装指引走 pip 直装不经它；按方案"树内零内容改动"随迁未改，特此留痕。

## 7. 假设与判断记录

- mode 文档脚本路径统一采用 `../scripts/<引擎>/...` 相对形态（从 modes/ 出发可解析，满足 exists 断言基准），替代 anydoc 原硬编码安装根路径与 url 的 {baseDir} 变量机制——依据方案改动清单 2"脚本引用路径全部改 scripts/<引擎子目录>/... 新路径（逐字核对实际层级）"与委派单断言要求（从该文件目录出发 exists）。
- anydoc B 节（inbox 导入型）与边界节的 /llm-wiki 表述保留：方案与委派单仅点名 description 与标题的"EvoCenter 专用"旧语境；B 节为可选导入工作流，其表述不依赖 EvoCenter 名字成立，按精准局部修改原则不扩改。
