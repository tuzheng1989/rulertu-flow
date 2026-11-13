# 被测 C 原始输出：DR-E06 deep-research 轻量真跑

说明：被测 subagent（general-purpose，冷启动模拟）原始回报，主控落盘供评估 subagent 评分。产物目录 outputs/DR-E06/（report.md / research-process.md / sources.json）。

---

# DR-E06 执行报告：Serper.dev API 定价与免费额度（deep-research v0.8.0，max_loops=1）

## 一、产物文件清单

目录：`outputs/DR-E06/`

| 文件 | 大小 | 说明 |
|------|------|------|
| report.md | 5,729 B | 主报告，按 v0.4.1 要求引用锚链化（来源条目含 `<a id="ref-n">` 锚点），含核心结论表 / 三维度分段 / 冲突与不确定点 / 14 条来源 |
| research-process.md | 3,262 B | 过程记录：节点执行表、通道与降级记录、与文档的偏离点 |
| sources.json | 4,792 B | 14 条来源结构化列表（含 key_facts 标注），`python json.load` 校验通过 |

## 二、通道使用记录

仅 1 轮循环，2 条 query，`source_type` 均为 `web`：
1. `Serper.dev API pricing plans per 1000 queries` → MCP `web-search-prime`（content_size=high, location=us, recency=oneYear）— 成功，9 条结果
2. `Serper.dev free credits signup 2500 queries` → MCP `web-search-prime`（同参数）— 成功，9 条结果

两调用在一条消息内并行发起，符合文档 3.2 的"查询级并行"约定。未触及 academic/code/social/product/image 专门通道。

## 三、降级记录

**降级次数：0**。web 通道两次调用均成功，无任何失败/限流，降级规则未被触发。如实记录，无虚构。

## 四、流程符合度自评

**符合项**：第 1 步解析、clarify 豁免判定（主题具体，符合"能推断则不问"）、brief 生成并作为 query/summary/reflect/finalize 的统一锚点（文档注意事项第 7 条维度一致性）、3.2 真实 MCP 搜索 + 并行、3.3c 按文档规则首轮不压缩、reflect→max_loops=1 自然结束、finalize 文件集齐全（report/process/sources 三件套）、落盘方式即文档第 5 步规定的 Bash 写文件。

**偏离项（已在 research-process.md 如实记录）**：
1. **节点未走独立 subagent**：文档注意事项第 1 条推荐每节点独立 subagent；本次单轮 2 query 的快速场景下，brief/query/summary/reflect/finalize 五个 LLM 节点由主控内联执行以控制开销，各节点按 agents/research-node-*.md 的输入输出契约执行。这是为"快速"约束做的适配，属有意偏离而非遗漏。
2. **产物路径**：按调用方约束（DR-E06 目录）覆盖文档默认 `workspace/reports/{date}-{topic}-{hex4}/`。
3. **3.2b 深读跳过**：调用方约束"不做深度阅读"，代价是官方定价页未直读核验，报告中已将订阅档位等信息标注"低置信、未核验"。

## 五、研究核心发现（速览）

- **免费额度**：注册送 2,500 次查询，一次性 credit、无需信用卡——6 个独立来源交叉一致（置信度高）；个别来源称"每月"或"5,000 次"与主流冲突，报告中标注未采信。
- **定价**：预付费 credit 包制，$50/50,000 次（$1.00/1K）起步，阶梯降至最大档约 $3,750/1,250 万次（**$0.30/1K**）；credits 有效期约 6 个月。
- **存疑点**：第三方提及的订阅月费档位（$25/$75/$150 per mo）与 SerpApi 定价结构雷同，可能是混淆或旧版信息；正式采购决策前建议直读 serper.dev/pricing 核验。
