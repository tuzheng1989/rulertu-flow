# 被测 A 原始输出：deep-research 路由推演（DR-E01~E05、E07）

说明：被测 subagent（general-purpose，冷启动模拟）原始回报，主控落盘供评估 subagent 评分。

---

以下为 6 条独立请求的路由决策与行动计划。判定依据均引自 plugins/work-skills/skills/deep-research/SKILL.md（v0.8.0），下文以「§」加小节名引用。

━━━ case DR-E01（2026 AI 编程助手市场格局）━━━
【路由决策】完整走 deep-research 主流程（澄清→简报→3 轮循环→finalize），以 web 通道为主。
【依据】命中「触发条件」的"深度调研 XX"；§第 1 步 解析（max_loops 默认 3，search_location 自动）；§3.2 映射表——市场格局/玩家/趋势属通用网页情报（分析师报告、厂商公告、新闻），source_type=web → MCP web-search-prime；§3.2 web 参数 `content_size: "high"`，`search_recency_filter` 按 brief 时效要求（主题锚定 2026，需近一年过滤）；§第 1 步 允许多区域并行：英文资料 `us` 为主、中文市场视角 `cn` 并行。
【行动计划】
1. Step 1.5：Agent(general-purpose) 按 agents/research-node-clarify.md 判定——主题中等宽泛，预计触发 1 轮澄清（受众/深度），选项可枚举则走 AskUserQuestion（§1.5 规则：最多 1 轮）。
2. Step 1.8：Agent 按 research-node-brief.md 生成简报，维度清单定为：市场规模/主要玩家与份额/技术趋势/商业模式与定价/融资格局。
3. Step 2：初始化 ResearchState（scripts/state_manager.py）。
4. Step 3 循环 ×3：§3.1 query 节点首轮固定 3 条（核心概念/应用场景/最新进展）；§3.2 一条消息内并行调 `mcp__web-search-prime__web_search_prime`（us+cn）；后续轮按 knowledge_gaps 定向（上限 4 条），可补 social_en 通道（hackernews/twitter 脚本）抓开发者口碑、product 通道 `profile` 查 AI 编程工具融资。
5. 每轮 §3.3a/b/c summary→merge→compress（超阈值且 loop>1 才压缩）→§3.4 reflect（brief 维度评分，<7 继续、≥8 结束）。
6. Step 4/5：Agent 按 research-node-finalize.md 出报告，自动落盘 `workspace/reports/{日期}-{主题}-{hex4}/report.md`（含 research-process.md、sources.json）。

━━━ case DR-E02（React vs Vue 生态对比选型）━━━
【路由决策】完整主流程，多通道并行：code + social_cn + social_en + web。
【依据】命中"深度研究"触发条件；§第 1.5 步 + 「注意事项 #5」澄清单轮约束"能推断则不问"——用户已给定目的（技术选型）与侧重点（GitHub 活跃度、社区讨论），预计 need_clarification=false；§3.2「子工具选择」：仓库→`github_search.py`，技术讨论→`hackernews_search.py`，讨论→`twitter_search.py`；中文社区深度讨论→`zhihu_search.py`（social_cn）；综述类（State of JS、官方 roadmap、对比评测）→web 通道。
【行动计划】
1. Step 1.5 clarifier 判定（预计免澄清）；Step 1.8 brief：受众=技术选型团队，维度=GitHub 活跃度指标（stars/commits/releases）/社区讨论热度（HN/Twitter/知乎）/生态与工具链/学习成本与招聘/重大版本动向。
2. Step 3 循环 ×3，§3.2 一条消息内并行多通道 Bash 调用，统一加 `PYTHONIOENCODING=utf-8` 前缀：
   - `python scripts/channels/code/scripts/github_search.py "react" / "vue" --limit N` 取仓库与活跃元数据；数值细节（commit 频次、release 节奏）可经 §3.2b web-reader 深读 GitHub 仓库页补充；
   - `hackernews_search.py` + `twitter_search.py`（social_en）、`zhihu_search.py`（social_cn）抓社区讨论；
   - web 通道并行搜对比报告与年度生态调查。
3. 任一脚本 `success:false`/报错 → 按 §3.2 降级规则立即回退 `mcp__web-search-prime` 重试一次并 log。
4. reflect 的 gaps 预计指向量化数据缺口，第 2-3 轮定向补数；交叉验证关键数字（§3.2b：≥2 独立来源）。
5. finalize：对比表格型正式报告，自动落盘；如需润色可后接 write-report compose（§产物后处理，须用户确认）。

━━━ case DR-E03（Rulertu Flow 开源项目调研 + 正式报告）━━━
【路由决策】完整主流程，但澄清环节预计跳过（用户已指定"直接写完整报告、正式一点"）；code + web 通道为主，深读层权重高。
【依据】命中"调研"触发条件；§第 1.5 步 clarify 语义——用户用"直接写"预先封死了澄清回路，且交付物与语气已明确，符合「注意事项 #5」能推断则不问；"正式一点"写入 brief 的受众/输出格式字段，由 finalize 执行（§第 1.8 步"finalize 据其输出格式与受众决定报告结构"）。
【行动计划】
1. clarifier 判定输出 need_clarification=false（记录用户已预先给定范围）；brief：正式研究报告格式，维度=项目定位与功能/GitHub 数据与活跃度/技术架构/社区与生态/竞品对照。
2. §3.1 query（首轮 3 条：项目概况/仓库与社区数据/评价与使用案例）。
3. §3.2 并行：`python scripts/channels/code/scripts/github_search.py "Rulertu Flow" --limit N`（仓库发现与元数据）+ `mcp__web-search-prime__web_search_prime`（官方文档、发布公告、第三方提及）。
4. §3.2b 深读：非 arxiv 来源走 `mcp__web-reader__webReader` 抓 README/官方文档站全文——单项目调研的重心在深读而非广搜。
5. 判断备注：当前工作目录即 rulertu-flow 仓库本体，可把本地 README/docs 作为一手材料直接并入深读层（等效 3.2b 深读），但按技能流程仍以通道检索公开信息为主线，本地材料作补充。
6. 循环预计 2 轮即可达 reflect ≥8（单一对象、范围窄）；finalize 出正式语气完整报告并自动落盘。

━━━ case DR-E04（Product Hunt 热门 AI 笔记应用 + 融资）━━━
【路由决策】完整主流程但高度收窄，主打 v0.7.0 product 通道，预计 1-2 轮循环，交付物为清单/表格而非长文报告。
【依据】§v0.7.0 版本注记 + §3.2 映射表——"Product Hunt 产品/竞品/融资数据"与请求精确对口，source_type=product；§3.2「子工具选择」：产品发现→`search`/`semantic`，产品档案（评分/融资）→`profile --name "<产品名>"`，榜单→`leaderboard --date YYYY-MM-DD`；SKILL.md 明示子命令契约"详见 scripts/channels/product/CHANNEL.md，不在此复制"，故动线第一步须先读该 CHANNEL.md；范围窄（列产品名+融资）不需 3 轮，按 §3.4 reflect 提前达标即 break。
【行动计划】
1. clarifier 预计免澄清（范围/字段/时效均已明确）；brief：输出格式=产品清单表（名称/一句话/评分/融资），时效=最近热门。
2. 读 `scripts/channels/product/CHANNEL.md` 确认子命令参数契约。
3. §3.2 Bash（加 PYTHONIOENCODING=utf-8）：`python scripts/channels/product/scripts/producthunt_search.py search "AI note app" --limit 8`（或 semantic）发现产品；必要时 `leaderboard --date 2026-11-12` 取近期热度；再对入选产品逐个 `profile --name "<产品名>"` 取融资数据。
4. product 通道失败/限流 → §3.2 降级规则回退 `mcp__web-search-prime` 重试一次并 log。
5. summary 汇总后 reflect 评分（清单完整性为主维度）；finalize 出表格型短报告，自动落盘。

━━━ case DR-E05（找 transformer 架构示意图）━━━
【路由决策】不启动完整研究管线。这是取图任务而非研究任务——不命中「触发条件」（深入研究/研究一下/调研/全面分析/研究报告均无），用户也未要报告。仅轻量复用 v0.8.0 image 通道脚本单发执行。
【依据】§触发条件 不匹配，故 clarify/brief/循环/reflect/finalize 全部不适用；§3.2 映射表 image 行：`PYTHONIOENCODING=utf-8 python scripts/channels/image/scripts/serper_image_search.py "{query}" --num {N} --json`，`--gl`/`--hl` 指定国家语言；§实现说明"image 通道（Serper 图搜脚本）——SERPER_API_KEY 缺失时降级 web"；输出映射：`{title, url: imageUrl, pageUrl, source_domain, source_type:"image"}`（imageUrl 主产物、pageUrl 溯源）。
【行动计划】
1. 检查 SERPER_API_KEY 是否可用。
2. 可用 → Bash 单发：`PYTHONIOENCODING=utf-8 python scripts/channels/image/scripts/serper_image_search.py "transformer neural network architecture diagram" --num 6 --json`，可加 `--gl us --hl en`。
3. 缺失/失败 → 按降级规则走 web：`mcp__web-search-prime__web_search_prime` 搜图源页面（论文图、官方博客、开放图库），再 `mcp__web-reader__webReader` 打开页面提取图片直链（全程严禁内置 WebSearch/WebFetch，§注意事项）。
4. 向用户返回候选图清单（imageUrl + pageUrl + 来源域名），提示幻灯片使用前自查图片授权/署名；用页 URL 保留溯源。不产出 report.md。

━━━ case DR-E07（查证 GPT-5 SWE-bench 74.3%）━━━
【路由决策】以压缩形态触发本技能：单轮事实查核，只使用搜索层 + §3.2b 原始核验与交叉验证规则，不走 3 轮完整报告管线，产出查证结论而非完整报告。
【依据】"查证"不在 §触发条件 字面清单，但 §3.2b 明文覆盖此场景——"关键数字/时间/结论/高风险判断，优先回到原始来源确认；至少用 2 个独立来源交叉确认，冲突无法解决时记录冲突并在 summary 标注"；本技能无独立 fact-check 模式（对比：academic-research-skills:deep-research 有显式 fact-check 模式，可作跨技能备选，一行提及即可）；主张具体、无需澄清（§注意事项 #5）。
【行动计划】
1. 迷你 brief：查核对象=『GPT-5 在 SWE-bench 拿到 74.3%』，产出=结论（可靠/不可靠/存疑）+ 证据链 [n]；先厘清查核维度——74.3% 必须对应到具体 variant（SWE-bench Full/Verified/Lite）与时间点，variant 错配即不可靠。
2. §3.1 生成 2-3 条查询（单轮）：如 "GPT-5 SWE-bench 74.3%"、"SWE-bench Verified leaderboard GPT-5 score"，全部 source_type=web。
3. §3.2 并行调 `mcp__web-search-prime__web_search_prime`（content_size high，recency 覆盖 GPT-5 发布至今）。
4. §3.2b 深读原始来源：`mcp__web-reader__webReader` 抓 SWE-bench 官方排行榜页 + OpenAI 官方公告/模型页；优先一手来源，若主张仅见于二手聚合文章则降置信。
5. 交叉验证：≥2 个独立来源确认数值与 variant 归属；冲突无法解决 → 按 §3.2b 规则记录冲突、结论标"存疑"，不强行裁断。
6. 输出简短查证结论（判定 + 依据来源 [n] + variant/时间限定说明），可选落盘一份短 md；不执行 write-report 后处理。
