# B1 主控抽查记录

日期：2026-11-14。抽查人：主控。

## 现场事件裁决

**9dfadac 卷入 B1 staged rename**：B2 提交时暂存区含 B1 已完成的 33 个 R100 rename + 2 README 删除（git mv 自动暂存），被一起带入。主控裁决：**接受现状不拆分**——夹带部分为 B1 已稳定完成的纯搬迁骨架（R100 零内容改动，B2 Auditor 顺带核验），拆分需 reset 会干扰当时仍在运行的 B1 Executor 的 git 观察环境；B1 剩余部分（4 份 mode 改写 + 新 SKILL.md）验证收口后补提交，提交信息注明骨架先行入库。教训记档：提交前必须全量审查暂存区（git diff --cached --stat），不能只 grep 目标批次。

## 抽查项与结果

| 抽查项 | 结果 |
|---|---|
| L1 旧路径 grep 8 模式（复跑） | 零命中 ✓ 可采信 |
| L1 frontmatter ^name:（复跑） | 零命中 ✓ |
| L1 SKILL.md 行数（复跑） | 54 ≤ 200 ✓ |
| L1 顶层清零（复跑） | 零输出 ✓ |
| 脚本路径断言（复验） | 39/40 解析成功；唯一 FAIL 为 `../scripts/url/node_modules` 条件路径（"若不存在则 bun install"，未安装状态本然，Executor 已声明，非死指针）✓ |
| rename/树守恒 | 33 R100 + git rm 2 README + __pycache__ 3 .pyc 清理，54 源文件对账闭合（Executor 报告）✓ |
| 新 SKILL.md 质量核验（全文通读） | 四组触发词 + 互斥边界（三外部技能分流）、转换方向路由表、scripts 索引（关键脚本 + bun install 指引）、依赖速查（含回退方案）齐全 ✓ |
| 冒烟产物 | smoke-*/ 四目录在位；url 冒烟附 bun install 93 包可执行验证 ✓ |

## 冒烟归因复核

Executor 归因：htmlpdf/url 真跑成功；anydoc/mdpdf 环境性失败（anydoc CLI 无 win32-arm64 构建——原文档已知限制，route_ocr.py --help 可加载可启动；playwright 未装，md_to_pdf.py 从新路径正确加载至 import 停止）。**复验采纳**：两项环境性失败均已证明"脚本可发现、可加载、正确启动"（路径断裂排除），符合委派单判定原则。

## 移交 B3/后续的已知项（Executor 边界内遗留）

- install.py:45 parent.parent/requirements.txt 新布局断裂（仅已删 README 引用它；按树内零改动随迁留痕，后续维护处理）。
- anydoc mode B 节 inbox/llm-wiki 表述保留（方案仅点名 description 与标题旧语境，最小改动正确）。
- .gitignore:4 旧规则、write-report/data-analysis 6 处引用、根 README、升版 2.8.0 归 B3。

## 结论

Executor 关键验收项经复跑全部成立，冒烟归因合理，标注可采信。B1 执行阶段通过，移交双重独立验证。
