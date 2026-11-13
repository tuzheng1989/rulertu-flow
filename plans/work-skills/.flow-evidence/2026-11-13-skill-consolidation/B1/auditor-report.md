# B1 审计报告（Auditor，只读核验）

仓库：C:\Users\tuzhe\runspace\rulertu-flow ｜ 日期：2026-11-13 ｜ 范围：deep-research 搜索通道收编（未提交工作区差异）
说明：Auditor 只读契约未落盘，本报告由主控原样落盘（全文见 Auditor 回报，无增删）。

## 结论：通过（B1 可收口）

分级统计：**P0=0，P1=0，P2=1，P3=4**。无契约违背、无路径断裂、无边界越界、无验收造假；Executor 与主控的全部可复跑声明经独立复跑均逐字复现。

## 一、逐项核验结果（对应审计要点 1-6）

**1. RM 文件正文完整性：通过。**
- 暂存区 `git diff --cached -M --stat`：25 个文件全部纯 rename（0 insertions/0 deletions），证明 git mv 时刻零内容夹带。
- 5 个 CHANNEL.md 未暂存差异逐个通读：code/image/social_cn/social_en 均为「删 YAML frontmatter（含 image 的 metadata 行）+ 加 1 行收编说明」，收编说明与委派单模板逐字一致，正文其余零改动；product 额外 1 处活引用修正（66-70 行 `../sn-search-producthunt/...` → `scripts/channels/product/...`、"其他 sn-search-* 通道"→"其他脚本通道"），与 Executor 声明的边界内补充 #1 完全一致。
- 所有 .py/requirements.txt 工作区零改动（porcelain 中均为纯 `R ` 状态），"原样随迁"成立。

**2. SKILL.md 语义漂移：无漂移，通过。** 全文 diff 仅 3 个 hunk，全部落在 A1 锚点区（映射表 143-146、子工具区/统一约定/包络映射 149-162、参数速查表 394-397、420 行、架构区 427-428）：4 行路径/通道名更新、image 行（映射表/速查表/包络/架构 4 处均与委派单原文逐字一致）、156 行"sn 脚本"→"通道脚本"、420 行"分派到 6 个通道 + 按需 image 增强通道"。降级规则区为纯上下文未触碰。主控修正（现 424 行 `product=channels/product 脚本`）已生效且在 diff 中可证。SKILL.md 残留 sn-search 仅第 3 行 frontmatter description（v0.5.0 历史版本记录，主控已裁定不改、B3 处理）。

**3. config.json：通过。** JSON 有效；version=0.7.0 未动；4 处 entry 改为 `scripts/channels/<key>/scripts/...` 且保留花括号枚举；channel_keys = web/academic/code/social_cn/social_en/product/image（image 在 product 后）；image 条目三字段与委派单原文逐字一致。**逐文件存在性核验**：11 个枚举脚本（code×4、social_cn×3、social_en×2、product×1、image×1）全部 EXISTS，5 个 requirements.txt 与 5 个 CHANNEL.md 亦齐。

**4. 边界纪律：通过。** 全量 `git status --porcelain` 与边界逐项对照：批内 = 4 个 M（SKILL.md/config.json/research-node-query.md/SEARCH_MIGRATION.md）+ 5 组 rename，其余 R 均为随迁成员（含 reddit_search.py.disabled）。A3 仅 1 行改动（81 行）、MIGRATION 55 行历史决策原文保留。Executor 2 处边界内补充均由验收标准 2（grep 硬性零命中）驱动且已披露；主控 1 处修正（424 行名称残留，活引用性质）合理且已披露。边界外 `.gitignore`（diff 仅新增 family-skills/secret-skills 两行，与本批无关）、gongwen-docx、steve-jobs-perspective、docs/2026-11-12-recurrence-backflow.md、plans/.flow-evidence/ 均为本批外的用户在制品/证据目录，本批零触碰。旧 `__pycache__` 未迁移（委派单要求满足；现存 pyc 为测试/冒烟运行后新生成，见 P3-2）。

**5. 验收复核（cwd=plugins/work-skills/skills/，全部实际复跑）：全部通过。** 详见第三节命令清单。

**6. 冒烟归因核验：成立，无路径断裂误判。** 三条证据链：
- image：源码 `_require_search_enabled()`（serper_image_search.py 51-55 行）缺 key 时 `SystemExit("Serper image search is unavailable in the current environment.")`，与日志引用逐字一致；我复跑输出同一单行消息、rc=1、无栈回溯。
- social_cn/social_en：zhihu_search.py:25、youtube_search.py:16 的凭据缺失报错文案与日志摘录逐字一致，属凭据前置条件，非路径问题。
- code/product 为匿名真调成功。Executor 的判定原则（可发现、可加载、正确启动 = B1 通过；外部凭据缺失 = 环境因素）执行正确。image 文案未字面写出 key 名的偏差已如实记录并经主控裁定接受。

## 二、问题清单

**P2-1（应修不阻断）：search_utils.py 运行时报错内嵌旧布局路径，未入 B3 待办。**
- 位置：deep-research/scripts/channels/{code,social_cn,social_en}/scripts/search_utils.py 第 21 行，缺 httpx 时报错指引 `python -m pip install -r skills/sn-search-<X>/requirements.txt`——该路径在收编后已失效（实际位于 deep-research/scripts/channels/<key>/）。
- 定性：与主控已裁定延后的"三个 CHANNEL.md 依赖指引旧路径"同类，Executor 按脚本"原样随迁"边界不改是对的；但 Executor 范围外发现仅列了 CHANNEL.md，此 3 处运行时报错未被报告，B3 待办（master-spot-check 末节）也未覆盖。**建议：将此 3 处 append 进 B3 待办（与 CHANNEL.md 指引一并更新或裁定接受）。**

**P3-1（记录）：SEARCH_MIGRATION.md 新节代码块围栏错位。** 「每个通道目录内：CHANNEL.md…」与「+ scripts/…+ requirements.txt…」两行说明文字被裹在 ``` 代码块内部，渲染为代码内容。信息无损失，纯排版瑕疵，B3 顺手可修。

**P3-2（记录）：channels/ 下现存 __pycache__/*.pyc。** 为 T1/冒烟复跑新生成（非迁移夹带——暂存区纯 rename 可证）；.gitignore 第 1 行 `__pycache__/` 已忽略，`git check-ignore` 验证命中，不会进入收口提交。无需处理。

**P3-3（记录）：producthunt_search.py:44 User-Agent 仍为 "sn-search-producthunt/1.0"。** 历史 UA 标识字符串，非路径引用，无功能影响；是否更名交 B3/后续定夺。

**P3-4（记录）：product/CHANNEL.md 修正附带了括注「（cwd = deep-research 技能根）」。** Executor 日志对该补充的描述将其写为调用约定说明，实际也落进了文档正文。属让相对路径可读的必要补充，方向正确，仅记录措辞精度。

## 三、实际复跑命令与退出码（cwd=plugins/work-skills/skills/，除注明外）

| 命令 | 退出码 | 结果 |
|---|---|---|
| `grep -rn "\.\./sn-search-" deep-research/` | 1 | 零命中 ✓ |
| `grep -rn "\.claude/skills/" deep-research/ --include="*.json" --include="*.md" \| grep -v INSTALL.md \| grep -v README.md` | 1 | 零命中 ✓（INSTALL.md 命中经查均为 `~/.claude/skills/deep-research/` 安装目标路径，主控排除裁定合法） |
| `ls \| grep sn-search` | 1 | 零输出 ✓ |
| `PYTHONIOENCODING=utf-8 python deep-research/scripts/test_state_manager.py` | 0 | 31/31 通过 ✓（复现 T2） |
| cwd=deep-research/：`python scripts/channels/product/scripts/test_producthunt_search.py` | 0 | Ran 35 tests, OK ✓（主控未抽查项，补查，复现 T1） |
| cwd=deep-research/：`python scripts/channels/code/scripts/github_search.py "claude code" --limit 3` | 0 | success:true，anthropics/claude-code stars 155519——与 Executor 日志摘录逐字一致 ✓（冒烟抽查 1/2） |
| cwd=deep-research/：`python scripts/channels/image/scripts/serper_image_search.py "paper leaderboard" --num 3 --json` | 1 | 单行 "Serper image search is unavailable in the current environment."，无栈回溯 ✓（冒烟抽查 2/2） |
| `git status --porcelain`（repo 根） | 0 | 边界比对基准 |
| `git diff --cached -M --stat -- plugins/work-skills/skills/` | 0 | 25 文件纯 rename，0 行内容变化 |
| `git diff -M`（5 个 CHANNEL.md + 4 个修改文件，全文通读） | 0 | 见第一节 |
| `python -c "import json; ..."`（config.json 校验 + entry 路径逐文件存在性） | 0 | json 有效、version 0.7.0、11 脚本全 EXISTS |
| `find deep-research/scripts/channels -name "*.py" \| sort` | 0 | 15 个 .py，与 Executor 清单一致 |
| `git check-ignore -v <channels 下 pyc>` | 0 | .gitignore:1 `__pycache__/` 命中 |

## 四、五维评估

- **完成度**：委派单 A1-A5 全部锚点落实，验收标准 1/2/3 全部满足，TDD 边界两条回归接缝全绿。
- **证据真实性**：Executor 日志全部可复跑声明经我独立复跑逐字复现（含 GitHub star 数、报错文案、测试计数）；无夸大、无造假迹象。
- **契约对齐**：无弱化、无语义漂移；2 处 Executor 边界内补充与 1 处主控修正均有硬性驱动（验收 grep / 活引用）且均已披露。
- **问题与建议下一步**：P2-1 append 进 B3 待办（master-spot-check「移交 B3 的待办」节）；P3-1 随 B3 顺手修；其余记录在案。B1 可收口，等待主控统一提交。
