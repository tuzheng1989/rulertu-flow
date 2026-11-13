# B1 委派单：搜索通道收编（deep-research）

- 方案：plans/work-skills/2026-11-13-skill-consolidation.md（详案第 2 节 B1）
- 证据目录：plans/work-skills/.flow-evidence/2026-11-13-skill-consolidation/B1/
- 仓库：C:\Users\tuzhe\runspace\rulertu-flow（Windows Git Bash）
- 纪律：**不 git commit**（主控收口时统一提交）；用 `git mv` 保持 rename 追踪；只动边界内文件

## 目标

把 work-skills/skills/ 顶层 5 个 `sn-search-*` 技能目录收编进 `deep-research/scripts/channels/`，消灭 SKILL.md 里的跨目录相对路径（`../sn-search-*`）与 config.json 里的旧前缀残留（`.claude/skills/sn-search-*`），并新增 image 通道接线。

## 目录移动映射（git mv）

| 源（plugins/work-skills/skills/） | 目标（plugins/work-skills/skills/deep-research/scripts/channels/） | 目录内改名 |
|---|---|---|
| sn-search-code/ | code/ | SKILL.md → CHANNEL.md |
| sn-search-social-cn/ | social_cn/ | SKILL.md → CHANNEL.md |
| sn-search-social-en/ | social_en/ | SKILL.md → CHANNEL.md |
| sn-search-producthunt/ | product/ | SKILL.md → CHANNEL.md |
| sn-search-image/ | image/ | SKILL.md → CHANNEL.md |

- `scripts/`、`requirements.txt` 原样随迁。
- sn-search-producthunt/scripts/`__pycache__/`（.pyc）不迁移，直接删除。
- CHANNEL.md 头部处理：删除原 SKILL.md 的 YAML frontmatter（`name:`/`user-invocable:`/`metadata:`——收编后不再是顶层 skill，frontmatter 失效）；正文最前面加一行说明：`> 本文件为 <通道键> 通道契约文档（原 sn-search-<原名> skill，2026-11-13 收编进 deep-research）。`正文其余内容不动。

## 改动锚点（行号为当前磁盘状态，改动后自然偏移）

### A1. deep-research/SKILL.md

- **143-146 行**（搜索通道映射表 4 行）：调用路径 `../sn-search-<X>/scripts/` → `scripts/channels/<key>/scripts/`（调用工作目录视角：相对 deep-research 技能根）；通道名 `sn-search-<X> 脚本` → `<key> 通道脚本`。
- **新增 image 行**（跟在 146 行 product 之后）：
  `| image | Serper 图搜脚本 | Bash：PYTHONIOENCODING=utf-8 python scripts/channels/image/scripts/serper_image_search.py "{query}" --num {N} --json |`
- **149-153 行**（子工具选择区）：`product` 行内 `../sn-search-producthunt/SKILL.md` → `scripts/channels/product/CHANNEL.md`；新增 `image` 条目：配图/视觉证据按需调用，`--num` 控制数量，`--gl`/`--hl` 国家与语言偏好。
- **158-162 行**（输出包络映射区）：160-161 行 `sn-search-*`/`sn-search-producthunt` 名称改为通道名；新增 image 映射行：
  `image：{title, url: imageUrl, pageUrl, source_domain, source_type:"image"}（imageUrl 为主产物，pageUrl 保留溯源）`
- **156 行**：`sn 脚本` 措辞可顺手改为 `通道脚本`（仅此一词，不扩改）。
- **394-397 行**（参数速查表）：通道名同步更新；新增 image 行：`| image | Serper 图搜脚本 | Google 图搜（Serper.dev） | --num（需 SERPER_API_KEY，缺失降级 web） |`
- **420 行**：`分派到 6 个通道` → `分派到 6 个通道 + 按需 image 增强通道`（image 不入 source_type 分派体系，见设计决策）。
- **427-428 行**（架构描述）：名称同步；新增一行 image 通道描述：`- **image 通道（Serper 图搜脚本）** - Google 图搜，web 通道的配图/视觉证据增强，secondary 来源；SERPER_API_KEY 缺失时降级 web。`

### A2. deep-research/config.json

- **54/59/64/70 行** 4 处 `entry`：`.claude/skills/sn-search-<X>/scripts/...` → `scripts/channels/<key>/scripts/...`（保持既有 `{a|b|c}` 花括号枚举写法）。
- **search_channels 新增 image 条目**（product 之后）：
  ```json
  "image": {
    "type": "script",
    "entry": "PYTHONIOENCODING=utf-8 python scripts/channels/image/scripts/serper_image_search.py \"{query}\" --num {N} --json",
    "fallback": "web",
    "note": "Google 图搜（Serper.dev），web 通道配图/视觉证据增强，source_tier: secondary；SERPER_API_KEY 缺失时降级 web"
  }
  ```
- **不动**：`version`（0.7.0，B3 统一升版）。

### A3. deep-research/agents/research-node-query.md

- **81 行**：`（走 sn-search-producthunt 脚本）` → `（走 product 通道 channels/product）`。仅此一处，分派表不新增 image。

### A4. deep-research/docs/SEARCH_MIGRATION.md

- **83 行**活引用：调用路径与 `sn-search-producthunt/SKILL.md` → 新路径 `scripts/channels/product/scripts/producthunt_search.py` 与 `scripts/channels/product/CHANNEL.md`。
- **47-49、81 行**表格通道名同步（`sn-search-X 脚本` → `<key> 通道`）。
- **55 行**历史决策记录（为何选 deepxiv 而非 sn-search-academic）**保留原文不改**——历史事实。
- **文件末尾补一节**：`## 2026-11-13 五通道物理收编 + image 通道上线`——收编动机（消灭跨目录相对路径）、新布局（channels/ 目录树）、目录名映射表（同上）、image 通道上线记录（Serper.dev、SERPER_API_KEY、fallback web、source_tier secondary）、顶层 sn-search-* 目录清零记录。

### A5. 顶层目录清零

- 5 个 sn-search-* 目录经 git mv 后 skills/ 顶层无残留（含 __pycache__ 清理）。

## 设计决策（主控已定夺，照执行）

1. **image 不扩 source_type 分派体系**：source_type 保持 6 类（web/academic/code/social_cn/social_en/product）。image 是按需调用的增强通道（配图/视觉证据），方案定位"web 通道的配图/视觉证据增强，source_tier: secondary"。
2. **版本号不动**（0.7.0，B3 统一升版）。
3. **SKILL.md frontmatter description 不动**（B3 补 image 一句）。

## TDD 边界

- 本批是**文件搬迁 + 文档接线**，无新业务逻辑，**不写新单元测试**（无接缝可测新行为）。
- 回归接缝两条：
  1. 搬迁后 product 通道既有测试在新位置可跑：`python scripts/channels/product/scripts/test_producthunt_search.py`（或该文件的既定运行方式，见文件头部说明）。
  2. deep-research 自带 `scripts/test_state_manager.py` 跑一次，证明搬迁未破坏 deep-research 自身。
- 冒烟测试是真实外部调用，**不 mock**（验收要求）。

## 定向测试映射（锚点 → 命令）

| 锚点 | 定向验证 |
|---|---|
| 目录搬迁 + 顶层清零 | `ls plugins/work-skills/skills/ \| grep sn-search` 零输出；`find deep-research/scripts/channels -name "*.py" \| head -20` 文件齐全 |
| 路径接线（SKILL.md/config.json/query.md/MIGRATION.md） | `grep -rn "\.\./sn-search-" deep-research/` 零命中；`grep -rn "\.claude/skills/" deep-research/ --include="*.json" --include="*.md" \| grep -v INSTALL.md \| grep -v README.md` 零命中 |
| product 测试随迁 | 在新位置跑通既有测试 |
| state_manager 回归 | `python deep-research/scripts/test_state_manager.py` 通过 |
| 通道可用性冒烟 | 见下方冒烟清单 |

## 冒烟清单（cwd = deep-research/ 目录）

先探测 `echo ${SERPER_API_KEY:+set}` 判断 key 存在性（不要打印 key 值）。

| 通道 | 命令 | 判定 |
|---|---|---|
| code | `PYTHONIOENCODING=utf-8 python scripts/channels/code/scripts/github_search.py "claude code" --limit 3` | 匿名真调，success:true 且 items 非空 |
| product | `PYTHONIOENCODING=utf-8 python scripts/channels/product/scripts/producthunt_search.py search "notebook" --limit 3` | 匿名真调，输出标准 JSON |
| social_cn | `PYTHONIOENCODING=utf-8 python scripts/channels/social_cn/scripts/zhihu_search.py "Claude Code" --limit 3` | 脚本加载成功、参数校验通过即算 B1 通过；外部服务限流/风控属环境因素，如实记录 |
| social_en | `PYTHONIOENCODING=utf-8 python scripts/channels/social_en/scripts/youtube_search.py "Claude Code" --limit 3` | 同上 |
| image | 有 key：`... serper_image_search.py "paper leaderboard" --num 3 --json` 真调；无 key：同命令运行，判定**友好报错退出**（明确提示缺 SERPER_API_KEY，非栈崩溃） | 脚本找到并正常启动 |

判定原则：冒烟验证的是**搬迁后脚本可被发现、加载、正确启动**。外部 API 失败（限流/网络/key 缺失且已有友好报错）不算 B1 失败，但必须在报告里区分"路径断裂"与"环境因素"两种失败形态。

## 验收标准（方案原文 + 主控修正）

1. 五通道冒烟（见上表；方案原文："四个脚本通道各跑一次冒烟（code 通道 GitHub 搜索匿名可用；image 无 key 时验证参数校验报错路径而非栈崩溃）"）。
2. `grep -r "\.\./sn-search-" deep-research/` 零命中；`grep -r "\.claude/skills/" deep-research/` 零命中。**主控修正**：INSTALL.md 与 README.md 中的 `~/.claude/skills/deep-research/` 是安装目标路径（合法内容），grep 时排除这两个文件。
3. `ls plugins/work-skills/skills/ | grep sn-search` 零命中。

## 回报要求

- 每条命令回报：命令、退出码、通过/失败、关键输出摘录；完整日志写 `evidence/B1/executor-log.md`。
- 实际改动文件清单（含 git mv 的 rename 记录）。
- 冒烟失败时明确归因（路径断裂 vs 环境因素）。
- 发现方案与事实冲突时**停下上报主控**，不自行扩改。
