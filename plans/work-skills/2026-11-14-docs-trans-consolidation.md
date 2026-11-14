# work-skills 文档转换整合：docs-trans 组建 + gongwen-trans 升级

- **日期**：2026-11-14
- **状态**：待评审（用户裁定：方案出来后跳过对抗评审，自审后直接开工；已确认本机有 Word）
- **目标插件**：work-skills（docs-trans 新增、gongwen-docx 升级为 gongwen-trans、插件 2.7.0 → 2.8.0）

---

## 0. 背景与调研结论（锚点已核实）

skills/ 顶层文档转换类技能 4 个（方向各异、引擎异构）+ 公文特化 1 个：

1. **anydoc-to-md**（249 行 + scripts/ 92K：clean_hallucinations.py、ocr_pdf.py、route_ocr.py、winocr.ps1）：任意文档 → Markdown。anydoc Rust 引擎亚 5ms；扫描版 PDF 三级 OCR 路由（Windows OCR / DeepSeek-OCR+llama.cpp / Claude 视觉）+ 幻觉清洗 + 断点续传。description 仍是"EvoCenter 专用"旧语境，随整合更新。
2. **url-to-md**（69 行 + scripts/ 127K TypeScript 整树：bun + Chrome CDP，Defuddle/Legacy 双管道、YouTube 字幕、媒体本地化、vendor/）：URL → Markdown。
3. **md-to-pdf**（208 行 + scripts/ 3 py + assets/（custom.css、example.md、config.json）+ package.json + requirements.txt + references/mermaid-syntax.md）：Markdown → PDF，核心能力图表预渲染（Mermaid/PlantUML/HTML 图表/SVG）+ 中文显示 + 锚链。
4. **html-to-pdf**（106 行 + scripts/convert.py、merge.py + evals/evals.json + README.md）：HTML → PDF，自动推断纸张比例、多文件合并。
5. **gongwen-docx**（136 行 + references/gbt9704-reference.md + scripts/gongwen-to-docx.py 818 行）：Markdown → GB/T 9704-2012 公文 DOCX。版式逻辑（parse/classify/setup_page/set_font 等）全在 DOCX 侧。

6. **本机 Word COM 可用**（powershell New-Object Word.Application 实测 OK）——公文 PDF 走 docx2pdf 路径（版式零重写，PDF 只是渲染）。
7. **跨技能引用**：data-analysis/SKILL.md 2 处指 anydoc-to-md（互斥边界，23/43 行）；write-report 4 处指 url-to-md（references/engine/import-mode.md:82、references/import-guidelines.md:79/89/104）——整合后改指 docs-trans（B3 联动）。另有根 README.md:78/82 技能清单与安装指引含四个旧名（B3 同步更新）；.gitignore:4 的 url-to-md node_modules 规则随整合成死规则（B3 清理）；CHANGELOG.md:94 为历史记录豁免。
8. **互斥与触发词**：OCR 归 anydoc（触发词含"扫描版 pdf 转文字/OCR 这本书"）；Mermaid 归 md-to-pdf；四技能触发词无交叉冲突；与 data-analysis 边界（转换 vs 分析）沿用其 SKILL.md 既有互斥表述。

## 1. 路线图

### 批次矩阵

| 批次 | 内容 | 价值 | 成本 | 级 |
|---|---|---|---|---|
| B1 | docs-trans 组建：四转换技能四合一 | 高（文档转换单入口，消灭"EvoCenter 专用"旧语境） | 高（异构引擎随迁 + 四文档改写） | T3 |
| B2 | gongwen-trans 升级：新增公文 PDF 输出（docx2pdf/Word COM） | 中高（公文 docx/pdf 双格式） | 中（新代码 + Word COM 真跑） | T3 |
| B3 | 联动收尾：跨技能 6 处引用同步 + 升版 2.8.0 + 兜底 | 中 | 低 | T1 |

### 波次依赖

```
B1 docs-trans 组建 ─┐
                     ├──▶ B3 联动收尾（B1 与 B2 文件集互斥可并行；B3 依赖两者）
B2 gongwen-trans 升级 ─┘
```

## 2. 详案

### B1：docs-trans 组建（T3）

**目标布局**：

```
skills/docs-trans/
├── SKILL.md                     # 新写，≤200 行：按转换方向路由 + 触发词分流
├── modes/
│   ├── anydoc-to-md.md          # ← anydoc-to-md/SKILL.md 改写（文件 → MD）
│   ├── url-to-md.md             # ← url-to-md/SKILL.md 改写（网页 → MD）
│   ├── md-to-pdf.md             # ← md-to-pdf/SKILL.md 改写（MD → PDF）
│   └── html-to-pdf.md           # ← html-to-pdf/SKILL.md 改写（HTML → PDF）
├── scripts/
│   ├── anydoc/                  # ← anydoc-to-md/scripts/ 4 脚本整树
│   ├── url/                     # ← url-to-md/scripts/ 整树（含 vendor/、package.json、bun.lock）
│   ├── mdpdf/                   # ← md-to-pdf/scripts/ + assets/ + package.json + requirements.txt
│   └── htmlpdf/                 # ← html-to-pdf/scripts/convert.py、merge.py
├── references/
│   └── mermaid-syntax.md        # ← md-to-pdf/references/
└── evals/
    └── evals.json               # ← html-to-pdf/evals/
```

**设计决策（主控已定夺）**：

1. **mode 文件名保留原技能名**（anydoc-to-md.md 等）——输入输出语义自释，路由表无歧义；因此验收 grep 用**路径形态**（`skills/<旧名>/`、`../<旧名>/`、frontmatter `name:`）而非裸名（裸名 = mode 文件名，合法存在）。
2. **scripts/ 按引擎分子目录**（anydoc/url/mdpdf/htmlpdf）——四技能脚本树互不冲突；各 mode 文档内的脚本引用路径同步更新（逐字核对实际层级）。
3. **README.md 两份删除**（md-to-pdf、html-to-pdf 的）——SKILL.md 已覆盖，README 面向外部仓库语境；assets/example.md 随 mdpdf 保留（测试样本）；assets/test_output 若存在不随迁。
4. **evals.json 与 mermaid-syntax.md 随迁**（评测资产与图表语法参考）。
5. **description 更新**：anydoc mode 的"EvoCenter 专用"旧语境删除，改为通用表述（本仓环境）。
6. **触发词分流**（SKILL.md description 四组合并 + 互斥边界）："转成 md/OCR/扫描版转文字/文档转 markdown" → anydoc-to-md；"URL 转markdown/网页转 md/抓取网页" → url-to-md；"转 pdf/markdown 转 pdf/Mermaid" → md-to-pdf；"HTML 转 pdf/幻灯片转 pdf" → html-to-pdf。互斥边界：文档**分析**归 data-analysis；公文生成归 gongwen-trans（B2 后）；报告成稿归 write-report。

**改动清单**：

1. 先建 `docs-trans/` 父目录；`git mv` 四棵 scripts 树（anydoc 4 脚本、url 整树、mdpdf scripts+assets+package.json+requirements.txt、htmlpdf 2 脚本）+ mermaid-syntax.md + evals.json → 目标位置（纯 rename 零内容改动）。
2. `git mv` 四份 SKILL.md → `modes/<原名>.md` 后改写：删 frontmatter（加前缀行，按 write-report 先例用描述性名避开 grep 冲突）、触发词与"EvoCenter 专用"等旧语境更新、**脚本引用路径全部改 `scripts/<引擎子目录>/...` 新路径（逐字核对实际层级，不得照抄模板）**。
3. `git rm` 两份 README.md；`git rm` md-to-pdf/assets/test_output（若存在）；**删除未追踪残留 anydoc-to-md/scripts/__pycache__/（3 个 .pyc，gitignore 覆盖、git mv 不触及，不删则顶层清零验收必失败）**。
4. 新写 `SKILL.md`（≤200 行）：frontmatter（name: docs-trans + 四组触发词 + 互斥边界）+ 转换方向路由表（输入格式 × 输出格式 → mode）+ 各 mode 一句话定位 + scripts 子目录索引。
5. 四个源目录清零（含第 3 条的未追踪残留）。

**如何验证**：

- L1 机械（cwd = skills/docs-trans/）：`grep -rn "skills/anydoc-to-md\|skills/url-to-md\|skills/md-to-pdf\|skills/html-to-pdf\|\.\./anydoc-to-md\|\.\./url-to-md\|\.\./md-to-pdf\|\.\./html-to-pdf" .` 零命中；`grep -n "^name:" modes/*.md` 零命中；SKILL.md `wc -l` ≤ 200；脚本树文件计数守恒；skills/ 顶层 `ls | grep -E "anydoc|url-to-md|md-to-pdf|html-to-pdf"` 零输出。
- L2 冒烟（真跑）：
  - anydoc：构造小 docx（openpyxl 造 xlsx 亦可），按 mode 文档转换出 md
  - md-to-pdf：小 md（含一段 Mermaid）转 PDF，PDF 可打开且页数合理
  - html-to-pdf：小 html 转 PDF
  - url-to-md：真转一个稳定网页（如 example.com）出 md
- L3 路由推演 8 条：4 正例（docx 转 md / 网页转 md / md 转 pdf / html 转 pdf）+ 4 边界（PDF 分析→data-analysis / 报告改写→write-report / 公文生成→gongwen-trans / 扫描版 PDF 转文字→anydoc OCR 路由）。

**验收标准**：

- [ ] 旧路径引用 grep 零命中；`^name:` 旧 frontmatter 零命中
- [ ] SKILL.md ≤ 200 行、四组触发词 + 互斥边界齐全
- [ ] 脚本树计数守恒（rename 追踪 + 除 mode 文档外零内容改动）
- [ ] 冒烟 4/4（四种转换各真跑一次成功）
- [ ] 路由推演 8/8（4 正例 + 4 边界）
- [ ] 顶层目录清零

**代码评审节点**：mode 文档脚本新路径逐字核对实际层级（决策 7 前车之鉴）；url 树随迁后 bun/package 依赖安装指引是否仍可执行；mdpdf 的 config.json 引用路径；两 README 删除无引用方残留。

**分级依据**：T3——四技能契约合并改写、异构引擎随迁、新路由无既有测试覆盖；同 write-report/data-analysis 先例。

### B2：gongwen-trans 升级（T3）

**目标布局**：

```
skills/gongwen-trans/                # ← git mv gongwen-docx gongwen-trans
├── SKILL.md                         # 改写：输出格式路由（docx / pdf）+ 公文字类型
├── references/gbt9704-reference.md  # 随迁零改动
└── scripts/
    ├── gongwen-to-docx.py           # 随迁零改动
    └── gongwen-to-pdf.py            # 新写：docx → pdf 封装（docx2pdf，Word COM）
```

**设计决策（主控已定夺）**：

1. **pdf 路径 = docx2pdf（Word COM）**：GB/T 9704 版式已在 docx 侧完整实现，PDF 只是渲染——零版式重写。本机 Word COM 实测可用（powershell 实证）。
2. **gongwen-to-pdf.py 设计**：输入 docx 路径（或 md 先链式调 gongwen-to-docx 产出 docx 再转 pdf）；docx2pdf.convert() 封装 + Word 可用性前置检测（win32com 探测 Word.Application，不可用时给明确提示"需要安装 Microsoft Word"）；支持 `--keep-docx`（pdf 生成后保留中间 docx，默认删除）。
3. **SKILL.md 改写**：name: gongwen-trans；description 扩展"生成符合 GB/T 9704-2012 标准的公文 DOCX 或 PDF"；新增「输出格式」小节（默认 docx；`--pdf` 或明确要求 pdf 时走 gongwen-to-pdf.py，内部先产 docx 再转换）；触发词补"生成公文 pdf / 公文转 pdf"。
4. **依赖声明**：requirements 新增 docx2pdf（python-docx 既有）；SKILL.md 依赖节写明"pdf 输出需本机安装 Microsoft Word"。

**改动清单**：

1. `git mv gongwen-docx gongwen-trans`。
2. 新写 `scripts/gongwen-to-pdf.py`：argparse（docx_path / --keep-docx / --output）；win32com Word 可用性检测；docx2pdf.convert()；错误处理（Word 不可用 / 文件占用）。
3. SKILL.md 改写（决策 3）。
4. requirements.txt 增补 docx2pdf（若无 requirements 文件则在 SKILL.md 依赖节声明）。

**如何验证**：

- L1 机械：`python -c "import docx2pdf"` 通过（委派单需先 `pip install docx2pdf`——本机当前未安装）；gongwen-to-pdf.py `--help` 正常。
- L2 真跑：小 md 公文样稿 → gongwen-to-docx.py 产 docx → gongwen-to-pdf.py 产 pdf；断言 pdf 存在、页数 ≥1、Word 进程退出无残留。
- L3：SKILL.md 路由推演 3 条（"转成公文 docx" → docx 路径；"生成公文 pdf" → pdf 路径；"普通文档转 pdf" → 指 docs-trans）。

**验收标准**：

- [ ] `git mv` rename 追踪；gbt9704-reference.md 与 gongwen-to-docx.py 零内容改动
- [ ] gongwen-to-pdf.py 真跑产 pdf 成功（本机 Word）
- [ ] SKILL.md 输出格式路由 + 触发词扩展齐全
- [ ] 路由推演 3/3
- [ ] 顶层 gongwen-docx 目录名清零（改名完成）

**代码评审节点**：Word COM 进程生命周期管理（转换后 Quit 防残留）；docx2pdf 异常路径（文件被占用时的提示）；SKILL.md 双格式路由不与 docs-trans 的通用 pdf 转换混淆（公文 pdf 走本技能，通用 pdf 走 docs-trans）。

**分级依据**：T3——新代码路径（pdf 转换封装）无既有测试覆盖 + 外部 COM 依赖；就高不就低。

### B3：联动收尾（T1）

**如何改**：

1. 跨技能引用同步 6 处：data-analysis/SKILL.md:23 与 :43 的 `anydoc-to-md` → `docs-trans`（措辞改为"格式转换归 docs-trans"）；write-report/references/engine/import-mode.md:82 与 references/import-guidelines.md:79/89/104 的 `url-to-md` → `docs-trans 的 url-to-md mode`。
2. 根 README.md:78/82 更新：技能清单四个旧名 → docs-trans；url-to-md 的 bun install、md-to-pdf requirements、html-to-pdf Chrome 依赖三条安装指引合并为 docs-trans 依赖指引。
3. `.gitignore:4` 的 url-to-md node_modules 死规则 → 改为 `plugins/work-skills/skills/docs-trans/scripts/url/node_modules/`。
4. `plugins/work-skills/.claude-plugin/plugin.json`：version 2.7.0 → 2.8.0（description 已含"文档转换"不动）；.claude-plugin/marketplace.json 无版本字段，description 已一致。
5. 全仓兜底：`grep -rn "anydoc-to-md\|url-to-md\|md-to-pdf\|html-to-pdf\|gongwen-docx"` 预期命中形态仅限——docs-trans/gongwen-trans 内部（mode 文件名、route_ocr.py argparse 字符串、url/scripts/package.json 与 bun.lock 的包名字符串等随迁零改动文件的必然命中）、方案与证据目录、CHANGELOG.md 历史记录、.scratch/；**skills/ 顶层目录名、两 manifest、根 README.md 零命中旧目录路径形态**。
6. 方案状态回写。

**如何验证**：版本核验 + 6 处引用逐处核验 + 全仓 grep 兜底（按第 5 条预期形态判定）+ 前序红线复查（deep-research 两条、write-report 互引、data-analysis 互引）。

**验收标准**：

- [ ] plugin.json version=2.8.0
- [ ] data-analysis/write-report 6 处引用全部改指 docs-trans 且逐处可解析
- [ ] 根 README.md 技能清单与安装指引已更新
- [ ] 全仓兜底 grep 符合第 5 条预期形态（skills/ 顶层与 manifest 零旧路径）
- [ ] 前序红线仍零命中

**代码评审节点**：引用同步后 data-analysis 互斥边界语义不变（"转换归 docs-trans"）；write-report 引擎指引链路可达；根 README.md 更新后与实际技能清单一致。

**分级依据**：T1——加法式版本与引用更新 + grep 兜底。

## 3. 风险与回滚

| 风险 | 缓解 | 回滚 |
|---|---|---|
| mode 文档脚本新路径错层级 | 决策 7 前车之鉴：委派单明令逐字核对 + 验收含路径解析 exists 检查 | git revert |
| url 树（bun/TS/vendor）随迁后安装执行语境变化 | 树内零内容改动 + 冒烟真转网页验证 | git revert |
| docx2pdf 与 Word COM 版本兼容 | 真跑断言 + Word 可用性前置检测给明确提示 | gongwen-to-pdf.py 单文件回退 |
| 两 README 删除后信息丢失 | SKILL.md 已覆盖全部操作语义；git 历史可溯 | git revert |
| 旧路径引用漏改 | 三条精确 grep（路径形态/frontmatter/顶层目录）+ B3 全仓兜底 | 补改 |

## 4. 范围外声明

- data-analysis、write-report 本体不动（仅 B3 引用同步）。
- anydoc Rust 引擎本体、url-to-md 的 vendor/ 第三方代码零改动随迁。
- OCR 三级路由的 DeepSeek-OCR 管线（llama.cpp）不做本机验证（重依赖，沿用文档既有指引）。
- 公文 PDF 仅 docx2pdf 路径；reportlab 直接排版不在本方案。
