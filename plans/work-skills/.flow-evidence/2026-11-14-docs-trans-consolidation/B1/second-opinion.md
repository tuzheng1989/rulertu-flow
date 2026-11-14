# B1 独立第二意见评审（冷启动可用性）

说明：第二意见代理只读契约未落盘，本报告由主控原样落盘（全文无增删）。总体判断：**修后可用**。3 高项与部分中低项已由主控当日修复（见 master-remediation-B1.md）。

# docs-trans 第二意见评审（只读核验）

**独立验证证据**：重跑全量路径断言（python os.path，从 modes/ 与技能根双基准解析四份 mode 文档 + SKILL.md 全部脚本引用）——26 处唯一引用全部存在，Executor"42 处 exists 通过"结论成立（42 为出现次数，26 为去重数）。抽查了 6 个脚本的 argparse/CLI 实参、url 树 3 个环境变量实现、requirements.txt/package.json 与文档三方对账、evals.json 可解析。**但 flag 级契约缺陷是 exists 断言盲区，以下高危项均属此类。**

## 高（3 项）

1. **merge.py 合并后删除用户输入文件**。scripts/htmlpdf/merge.py:106 CLI 入口硬编码 delete_temp=True，合并成功后 os.unlink 全部输入 PDF。而 modes/html-to-pdf.md:47 明文推广"仅合并已有 PDF（不经 Chrome）"，SKILL.md description 与触发词表还把"合并这些 PDF"路由进来——冷启动照文档执行即毁用户存量 PDF。浅层根因：delete_temp 语义是给 convert.py 临时单页用的，merge.py 独立入口未暴露开关。
2. **md-to-pdf.md 文档命令必失败**：--output-dir（67、76 两行）与 --header --footer --page-numbers（87 行）在 md_to_pdf.py argparse 中不存在（仅 -o/--output，页眉页脚无任何实现），照抄执行报 unrecognized arguments。
3. **SKILL.md:16 "页眉页脚"能力宣称**随上条处空——入口文档对 md-to-pdf 的能力描述与引擎实际不符（列为高因它出现在路由表，误导面最大；实质是问题 2 的入口级传播）。

## 中（5 项）

4. **路由方向缺口未声明**：四 mode 覆盖 文档→MD / URL→MD / MD→PDF / HTML→PDF。"md 转 docx"（非公文）、docx→pdf、html→md 等方向无任何"不支持/去向"声明，路由表也无 fallback 行。建议补一行"未列方向默认不支持，公文 docx 例外归 gongwen-trans"。
5. **Mermaid 预渲染的网络依赖未披露**：diagram_renderer.py:43 从 jsdelivr CDN import mermaid，文档只声明 PlantUML 需网络；离线环境 Mermaid 全挂且故障排除节无此提示。
6. **config.json 使用方式缺失**：md-to-pdf.md 160 行"配置文件"只展示字段，未说明须经 --config 传入（脚本实际仅此一途）。
7. **宿主项目旧语境残留**：anydoc-to-md.md B 节"遵守 CLAUDE.md「素材处理」规则"、/llm-wiki、workspace/fuliang-ocr/merge_book.py 参照实现，html-to-pdf.md:102"本仓库默认输出 output/exports/（见项目 CLAUDE.md）"——本仓及任意新项目的 CLAUDE.md 均无这些定义（已 grep 证伪），与计划决策 5"删旧语境"部分相违。B 节标注"可选"故不阻断主路径。
8. **相邻技能反向链接断裂（B3 待办）**：data-analysis SKILL.md:23/43 仍指 anydoc-to-md、write-report references 3 处仍指 url-to-md。属计划内 B3 联动批未执行，非 B1 缺陷，但当前冷启动会把用户指向已不存在的旧技能名——B3 必须收口，勿漏。

## 低（4 项）

9. OCR 路由三级优先级未显式声明：≤8 页古籍同时命中"<70→DeepSeek"与"≤8→Claude 视觉"两行，冲突时谁优先靠猜；"≤8 页→Claude 视觉"路径的 pages 渲染无命令。
10. "打印这个文档"触发词映射 md-to-pdf，若输入为 docx/html 则方向不匹配。
11. 模糊请求（"帮我处理这个文件"无目标格式）无询问规则。
12. references/mermaid-syntax.md 仅 SKILL.md:45 提及，md-to-pdf.md mode 文档零引用，自包含契约下参考资产半孤儿。

## 达标项

D1 触发词/方向/互斥三件套齐全，四正例路由正确；D2 url-to-md 契约最完整（BUN_X 解析、bun install 首检、7 脚本全存在、3 环境变量均有实现）；D3 依赖三方一致（pip 三件套=requirements.txt=mode 文档；anydoc OCR 的 pypdf/pillow=实际 import；bun 依赖=package.json+bun.lock）；D4 gongwen-trans↔docs-trans 双向互指一致；D5 win32-arm64 限制与 npx 回退、bun 回退、playwright 安装指引均如实披露。

## 总体判断：**修后可用**

阻断项仅 3 个高问题（merge.py 数据丢失为最急；md-to-pdf 删两处假参数与页眉页脚宣称即恢复契约）。中低项可随后续小批处理。B1 的路径迁移质量本身过硬，缺陷集中在**文档命令与脚本 CLI 的逐字对账**——正是上批死指针教训的另一面：只验"文件存在"不验"参数存在"。
