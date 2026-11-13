# Serper.dev API 定价与免费额度调研报告

> 研究主题：Serper.dev API 的定价和免费额度
> 日期：2026-11-13 ｜ 研究轮次：1（快速调研） ｜ 搜索区域：us ｜ 通道：web（MCP web-search-prime）

## 核心结论

| 项目 | 结论 | 置信度 |
|------|------|--------|
| 免费额度 | 注册即送 **2,500 次免费查询**（一次性 credit，非按月），无需信用卡 | 高（6 个独立来源交叉一致） |
| 起步付费 | 预付费 credit 包：**$50 / 50,000 次**（$1.00/1K） | 高（3 个来源一致） |
| 最大档 | **$3,750 / 1,250 万次**（$0.30/1K），即量大最低单价约 **$0.30/1,000 次** | 高（2 个来源一致） |
| 计费模式 | credit 制，1 credit 约等于 1 次请求；credits 有效期约 6 个月 | 中高（第三方来源，官方页未核验） |
| 订阅月费档位 | 第三方提及 Starter $25/mo/1,000 次、Developer $75/mo/5,000 次、Production $150/mo 等 | 低（仅 2 个第三方来源，可能过时或与 SerpApi 混淆，未核验） |

## 分段详述

### 1. 定价方案与计费单位

Serper.dev 采用**预付费 credit 包**模式（prepaid credits），无强制月费订阅：起步 **$50 购 50,000 credits**（合 $1.00/千次）[1][3][8]，随购买量阶梯降价，最大档约 **$3,750 购 1,250 万 credits**（合 **$0.30/千次**）[1][4][6]。计费粒度简单：按请求次数计 credit，无按结果数的乘数 [10]。第三方评测将 Serper 与 SerpApi 对比时，普遍把 "$0.30-$1.00/1K" 作为 Serper 的价格区间，显著低于 SerpApi 的 "$3.75-$25/1K" [2][7]。

另有第三方来源提及 Serper 存在订阅制月费档位（Starter $25/mo 含 1,000 次、Developer $75/mo 含 5,000 次、Production $150/mo）[9][11]，但该组数字同时出现在 SerpApi 的定价页结构中（SerpApi 亦为 $25 起步/1,000 次/月）[12]，存在信息混淆或过时的可能。**本报告未能直读 serper.dev/pricing 官方页核验（本次调研约束不做深度阅读），订阅档位信息请以官方页为准。**

### 2. 免费额度

新账号注册即获 **2,500 次免费查询 credit**，**无需绑定信用卡** [1][3][5][6][8][11]。该额度为**一次性赠送**（signup credit，用完即止），而非按月刷新 [5][11]。一个第三方来源称其为"每月 2,500 次" [13]，与主流"一次性"说法冲突，采信多数来源；另有竞品对比页称"5,000 免费 credit、1 credit = 10 results" [10] 的口径与其他来源均不符，疑为竞品自有口径的误植，不予采信。credits 自充值起有效期约 **6 个月** [14]。

### 3. 配额与超额规则

免费 credit 用尽后需购买预付费包继续使用 [1][5]。搜索深度可能影响消耗：有第三方分析指出更深的搜索结果（如 depth 加大）会消耗更多 credit [14]。Serper 覆盖 Google 搜索、Google News、图片搜索等端点，均按同一 credit 模型计费 [13]。与竞品相比，Serper 定位为"Google 专属、低价、低延迟"的搜索 API [2][7]。

## 冲突与不确定点（如实记录）

1. **免费额度是否按月刷新**：多数来源说一次性（采信），codewords.ai 说每月 [13] —— 未核验官方页，存疑。
2. **订阅月费档位是否存在**：fastcrw [9] 与 apiserpent [11] 提及 $25/$75/$150 档位，但与 SerpApi 定价结构雷同 [12]，可能是混淆或 Serper 旧版定价。
3. **官方定价页未直读**：受"快速调研、不做深度阅读"约束，以上均为第三方来源转述，正式采购决策前建议直读 https://serper.dev/pricing 核验。

## 来源列表

1. <a id="ref-1"></a>[Serper API Key: Get One Free, Pricing and Examples (2026) — keirolabs.cloud](https://keirolabs.cloud/blog/serper-api-guide-2026)
2. <a id="ref-2"></a>[Serper API Key Guide（Serper vs SerpAPI 价格区间对比）— keirolabs.cloud](https://keirolabs.cloud/blog/serper-api-guide-2026)
3. <a id="ref-3"></a>[crawl and search for cheapest prices — crawleo.dev](https://www.crawleo.dev/blog/serperdev-vs-crawleodev-features-pricing-pros-and-cons-2026)
4. <a id="ref-4"></a>[Serper API — Docs, OpenAPI & Kin Score — apis.io](https://apis.io/providers/serper)
5. <a id="ref-5"></a>[web-researcher-mcp API_SETUP.md — github.com/zoharbabin](https://github.com/zoharbabin/web-researcher-mcp/blob/main/docs/API_SETUP.md)
6. <a id="ref-6"></a>[Serper API — apis.io（$0.30/1K 佐证）](https://apis.io/providers/serper)
7. <a id="ref-7"></a>[Best SERP APIs in 2026 — octoparse.com](https://www.octoparse.com/blog/best-serp-api)
8. <a id="ref-8"></a>[10 Best Free SERP APIs in 2026 — brightdata.com](https://brightdata.com/blog/web-data/best-free-serp-apis)
9. <a id="ref-9"></a>[Cheapest & Fastest vs Broadest Google Search API — fastcrw.com](https://fastcrw.com/alternatives/serper-vs-serpapi)
10. <a id="ref-10"></a>[Serper.dev Alternative & Pricing — serpscraper.dev](https://serpscraper.dev/vs/serper-dev)
11. <a id="ref-11"></a>[SerpApi vs Serper.dev: 500 Queries Through Both, Tested — apiserpent.com](https://apiserpent.com/blog/serpapi-vs-serper-benchmark)
12. <a id="ref-12"></a>[Plans and Pricing — serpapi.com](https://serpapi.com/pricing)
13. <a id="ref-13"></a>[How to use Serper.dev API for Google search automation — codewords.ai](https://www.codewords.ai/blog/serper-dev)
14. <a id="ref-14"></a>[Serper Pricing 2026: Credits, 6-Month Expiry — apiserpent.com](https://apiserpent.com/blog/serper-pricing-credits-explained)

> 注：来源 1/2、4/6、9/11 等为同域名不同信息点，报告中按信息点分别引用。所有来源均为第三方转述，官方定价页（serper.dev/pricing）未在本次调研中直读核验。
