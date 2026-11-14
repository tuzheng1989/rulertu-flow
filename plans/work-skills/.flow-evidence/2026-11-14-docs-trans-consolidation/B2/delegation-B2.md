# B2 委派单：gongwen-trans 升级（新增公文 PDF 输出）

- 方案：plans/work-skills/2026-11-14-docs-trans-consolidation.md（详案第 2 节 B2，含设计决策 1-4 与改动清单 1-4——**先通读方案全文再动工**）
- 证据目录：plans/work-skills/.flow-evidence/2026-11-14-docs-trans-consolidation/B2/
- 仓库：C:\Users\tuzhe\runspace\rulertu-flow（Windows Git Bash）
- 纪律：**不 git commit**；git mv 保 rename 追踪；只动 gongwen-docx/（改名后 gongwen-trans/）边界

## 执行要点

1. **git mv gongwen-docx gongwen-trans**（references/ 与 gongwen-to-docx.py 随迁零改动）。
2. **新写 scripts/gongwen-to-pdf.py**：
   - argparse：`docx_path` 位置参数；`--keep-docx`（默认转换后删中间 docx——仅当 docx 是本脚本链式产出时删，外部传入的 docx 不删）；`--output`（pdf 输出路径，默认与 docx 同名）。
   - Word 可用性前置检测：win32com 探测 Word.Application，不可用时 print 明确提示"公文 PDF 转换需要 Microsoft Word（docx2pdf 依赖 Word COM）"并 sys.exit(1)，非栈崩溃。
   - 转换：docx2pdf.convert(docx, pdf)；完成 print 输出路径与文件大小。
   - 错误处理：docx 被占用/不存在 → 友好报错；转换后确认 pdf 存在。
   - **Word 进程生命周期**：docx2pdf 内部管理 Word 实例，不额外手工 Quit（避免干扰库自身的 COM 生命周期）。
   - **依赖**：docx2pdf 本机未安装——委派单授权 `pip install docx2pdf`（写入用户 site-packages，为运行依赖非项目依赖）。
3. **SKILL.md 改写**：
   - frontmatter name: gongwen-trans；description 扩展"生成符合 GB/T 9704-2012 标准的公文 DOCX 或 PDF 文件" + 触发词补"生成公文 pdf / 公文转 pdf / 红头文件 pdf"。
   - 新增「输出格式」小节：默认 docx；用户明确要 pdf（或 `--pdf`）时走 gongwen-to-pdf.py——内部先按既有流程产 docx，再 docx2pdf 转 pdf；pdf 输出需本机 Microsoft Word。
   - 依赖节：python-docx 既有 + docx2pdf 新增（注明仅 pdf 输出需要）。
   - 脚本引用与正文中"gongwen-to-docx.py"名称不变（随迁零改动）。
4. **requirements 处理**：技能目录无 requirements 文件（方案已确认），依赖声明写在 SKILL.md 依赖节即可。

## 冒烟执行（方案 L2）

- 造小 md 公文样稿（含标题 + 主送机关 + 正文两段 + 落款，frontmatter 带公文字类型）→ gongwen-to-docx.py 产 docx → gongwen-to-pdf.py 产 pdf。
- 断言：docx 存在；pdf 存在且大小 > 0；页数 ≥ 1（python 读 pdf 元数据或 pypdf 若可用，否则文件头 %PDF 判定）；--keep-docx 与默认删除两种模式各跑一次。
- 产物落证据目录 smoke-gongwen/（docx + pdf + 样稿 md）。
- 路由推演 3 条（方案 L3）落 raw-routing.md：subagent 只读 gongwen-trans/SKILL.md 输出路由决策。

## 定向验证映射

| 锚点 | 验证 |
|---|---|
| 改名 | git porcelain rename 追踪；references/gbt9704-reference.md 与 gongwen-to-docx.py 零内容改动 |
| 新脚本 | --help 正常；Word 检测逻辑在位；真跑产 pdf |
| SKILL.md | name: gongwen-trans；输出格式路由 + 触发词扩展；依赖节含 docx2pdf |
| 路由推演 | 3/3（docx / pdf / 普通 pdf 指 docs-trans） |
| 顶层清零 | skills/ 顶层 gongwen-docx 无残留 |

## 回报要求

- 完整日志写 `evidence/B2/executor-log.md`：改动清单、gongwen-to-pdf.py 设计说明、每条验收命令与退出码、冒烟产物与断言、路由推演结果。
- 发现现状与方案锚点不符时停下上报，不自行扩改。
