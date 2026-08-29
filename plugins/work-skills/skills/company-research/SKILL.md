---
name: company-research
description: |
  Automated company research using Playwright browser automation. Extracts comprehensive company information from official websites, generates sitemaps (2-3 layers deep), persists structured JSON data for future reference, and generates professional research reports in DOCX format. Supports four research scenarios: competitive analysis (竞品分析), investment research (投资调研), customer research (客户调研), and job applicant research (应聘调研). Auto-detects previously researched companies and supports incremental updates. Use when user requests company analysis with commands like "/company-research [公司名称]" or "调研一下[公司名]" or mentions any company name that may have been researched before.
---

# Company Research Skill

Automated company information collection, sitemap generation, and research report generation using Playwright browser automation with persistent JSON storage.

## Data Storage Structure

**Directory layout:**
```
./company-research/
├── data/                           # Persistent JSON data (for Claude reference)
│   ├── index.json                 # Master index of all researched companies
│   └── {company_slug}/            # Company-specific data
│       ├── basic_info.json        # Company basic information
│       ├── sitemap.json           # Complete website sitemap (2-3 layers)
│       ├── pages_data/            # Extracted data from each page
│       │   ├── homepage.json
│       │   ├── about.json
│       │   └── products.json
│       └── metadata.json          # Research metadata (timestamp, scenario, etc.)
├── reports/                        # Human-readable reports
│   ├── {公司名}_{场景}_20250210_143022.md
│   └── {公司名}_{场景}_20250210_143022.docx
└── .company-research-ignore        # Git ignore patterns (optional)
```

**index.json structure:**
```json
{
  "companies": [
    {
      "slug": "bytedance",
      "names": ["字节跳动", "ByteDance", "抖音"],
      "website": "https://www.bytedance.com",
      "last_researched": "2025-02-10T14:30:22Z",
      "scenarios": ["竞品分析", "投资调研"],
      "data_quality": 85
    }
  ],
  "last_updated": "2025-02-10T14:30:22Z"
}
```

### 0. Auto-Detect Historical Data

**Before starting new research:**

1. **Check for existing data:**
   ```bash
   # Check if ./company-research/data/index.json exists
   # Search for company name aliases and website URL
   ```

2. **If found, ask user:**
   ```
   📚 发现已存在的数据：
   - 公司：字节跳动
   - 上次研究：2025-02-10
   - 场景：竞品分析
   - 数据质量：85/100

   选择操作：
   [1] 加载历史数据（快速查看）
   [2] 增量更新（重新爬取最新数据）
   [3] 全新研究（覆盖旧数据）
   [4] 取消
   ```

3. **Company name normalization:**
   - Remove spaces, special characters
   - Convert to lowercase
   - Use pinyin for Chinese companies
   - Example: "字节跳动" → "bytedance", "OpenAI" → "openai"

## Core Workflow

### 1. User Input and Auto-Detect Historical Data

**Step 1: Parse user input**

Extract from user command:
- **Company name** (required)
- **Research scenario** (optional, will ask if not specified)

**Supported scenarios:**
- 竞争对手分析 (Competitive Analysis)
- 投资调研 (Investment Research)
- 客户调研 (Customer Research)
- 应聘调研 (Job Applicant Research)

**Command examples:**
- `/company-research 字节跳动 竞品分析`
- `帮我调研一下OpenAI的投资价值`
- `分析腾讯的应聘情况`
- `字节跳动怎么样？` (auto-detect intent)

**Step 2: Check for existing data**

```bash
# Check if ./company-research/data/index.json exists
if [ -f "./company-research/data/index.json" ]; then
  # Search for company name in index
  # Match by: name, aliases, or website
fi
```

**Step 3: If found, present options to user**

```
📚 发现已存在的研究数据：

公司名称：字节跳动 (ByteDance)
官网：https://www.bytedance.com
上次研究：2025-02-10 (3天前)
研究场景：竞品分析
数据质量：85/100
网站页面：25 个已发现，8 个已访问

选择操作：
[1] 📖 加载历史数据 - 快速查看之前的研究结果
[2] 🔄 增量更新 - 重新爬取最新数据，保留历史对比
[3] ✨ 全新研究 - 覆盖旧数据，从头开始
[4] ❌ 取消 - 放弃本次操作
```

**Step 4: Handle user choice**

**Option 1: Load historical data**
1. Read JSON files from `./company-research/data/{company_slug}/`
2. Display key information in chat
3. Offer to generate full report from stored data
4. No browser automation needed

**Option 2: Incremental update**
1. Read old metadata.json
2. Compare dates (if > 7 days old, suggest full refresh)
3. Re-run sitemap generation
4. Compare with old sitemap (highlight new pages)
5. Extract new/updated data
6. Preserve old data for comparison
7. Generate comparison report

**Option 3: Fresh research**
1. Archive old data (add timestamp suffix)
2. Proceed with standard workflow
3. Generate new research

**Company name matching logic:**

```javascript
// Normalize company name for matching
function normalizeCompanyName(name) {
  return name
    .toLowerCase()
    .replace(/[\s\-_]/g, '')  // Remove spaces, hyphens, underscores
    .replace(/[^\w\u4e00-\u9fa5]/g, '');  // Keep alphanumeric and Chinese
}

// Generate search variants
function generateSearchVariants(name) {
  const normalized = normalizeCompanyName(name);
  return [
    normalized,
    // Pinyin for Chinese (basic approximation)
    // Common aliases
    // Partial matches
  ];
}

// Match in index
function findCompanyInIndex(index, variants) {
  for (const company of index.companies) {
    for (const variant of variants) {
      if (company.slug.includes(variant) ||
          company.names.some(n => normalizeCompanyName(n).includes(variant))) {
        return company;
      }
    }
  }
  return null;
}
```

### 2. Target Website Navigation

**If URL provided:** Navigate directly
**If not provided:** Search for official website first

### 3. Three-Layer Navigation Strategy + Sitemap Generation

```
Layer 1: Homepage Exploration & Sitemap Root
  ├─ browser_navigate(url)
  ├─ browser_wait_for("networkidle") - CRITICAL
  ├─ browser_snapshot() - Get page structure
  ├─ Identify ALL navigation links (not just key pages)
  └─ Build sitemap root node with all discovered links

Layer 2: Key Pages Access (Priority Order)
  Priority 1 (Must): About Us, Products
  Priority 2 (Important): Solutions, News, Cases
  Priority 3 (Optional): Careers, Investors
  ├─ Visit each page sequentially
  ├─ Wait for networkidle
  ├─ Extract page data
  └─ Discover child links (for sitemap layer 2)

Layer 3: Sitemap Expansion (2-3 Layers Total)
  ├─ For each Priority 1-2 page:
  │   ├─ Extract all internal links
  │   ├─ Filter out duplicates and external links
  │   ├─ Categorize by page type
  │   └─ Add to sitemap structure
  ├─ Target: 10-50 total pages
  └─ Save sitemap.json

Layer 4: Deep Information Extraction
  ├─ Use browser_evaluate() for JavaScript extraction
  ├─ Apply scenario-specific extraction templates
  └─ Validate and clean data
```

### Sitemap Generation Algorithm

**Step 1: Extract all navigation links from homepage**

```javascript
// Run via browser_evaluate()
function extractNavigationLinks() {
  const selectors = [
    'nav a', '[role="navigation"] a',
    '[class*="nav"] a', '[class*="menu"] a',
    'header a', 'footer a'
  ];

  const links = new Set();

  for (const selector of selectors) {
    document.querySelectorAll(selector).forEach(a => {
      const href = a.href;
      const text = a.textContent.trim();

      // Filter: internal links only, non-empty text
      if (href &&
          text &&
          text.length > 0 &&
          text.length < 100 &&
          (href.startsWith('/') || href.includes(window.location.hostname))) {
        links.add(JSON.stringify({
          url: href.startsWith('http') ? href : window.location.origin + href,
          text: text,
          source: 'homepage-nav'
        }));
      }
    });
  }

  return Array.from(links).map(s => JSON.parse(s));
}
```

**Step 2: Categorize and prioritize links**

```javascript
function categorizeLinks(links) {
  const categories = {
    about: [],
    product: [],
    news: [],
    contact: [],
    careers: [],
    investors: [],
    other: []
  };

  const patterns = {
    about: /about|company|who-we-are|profile|关于/i,
    product: /product|service|solution|offering|产品|服务/i,
    news: /news|blog|press|media|article|新闻|动态/i,
    contact: /contact|reach-us|联系/i,
    careers: /career|job|hiring|join|招聘/i,
    investors: /investor|ir|stock|shareholder/i
  };

  links.forEach(link => {
    let categorized = false;

    for (const [category, pattern] of Object.entries(patterns)) {
      if (pattern.test(link.url) || pattern.test(link.text)) {
        categories[category].push(link);
        categorized = true;
        break;
      }
    }

    if (!categorized) {
      categories.other.push(link);
    }
  });

  return categories;
}
```

**Step 3: Visit and extract child links (Layer 2)**

For each category page (except 'other'):
1. Navigate to page
2. Wait for networkidle
3. Extract internal links from this page
4. Add to sitemap as children

**Step 4: Build sitemap structure**

```javascript
// Final sitemap.json structure
{
  "url": "https://example.com",
  "title": "Company Homepage",
  "type": "homepage",
  "children": [
    {
      "url": "https://example.com/about",
      "title": "About Us",
      "type": "about",
      "visited": true,
      "extracted_at": "2025-02-10T14:30:22Z",
      "children": [
        {
          "url": "https://example.com/about/team",
          "title": "Our Team",
          "type": "about",
          "visited": false,
          "discovered_from": "about"
        }
      ]
    }
  ],
  "metadata": {
    "total_pages": 25,
    "visited_pages": 8,
    "depth": 3,
    "generated_at": "2025-02-10T14:30:22Z"
  }
}
```

**Sitemap generation rules:**
- **Max depth**: 3 layers (homepage → category pages → child pages)
- **Max pages**: 50 total (stop when reached)
- **Deduplication**: Use URL as unique key
- **External links**: Exclude
- **Social media**: Keep separate, don't follow
- **File types**: Exclude (.pdf, .jpg, .png, etc.)

### 4. Page Type Identification

**URL Pattern Matching:**
- `/about`, `about`, 关于我们 → About page
- `/product`, `products`, 产品中心 → Product page
- `/news`, `blog`, 新闻动态 → News page
- `/contact`, 联系我们 → Contact page

**Content-based Fallback:**
- Check page title and content text for keywords
- Handle multi-language sites (Chinese/English)
- Support SPA applications (wait for route changes)

### 5. Scenario-Specific Research Framework

**CRITICAL - READ ENTIRE FILE**: Before proceeding, you MUST read
[`research-framework.md`](references/research-framework.md) completely.
This contains the standard 9-chapter report template, scenario weight tables,
and typical logic for each research scenario.

**Do NOT load** `data-extraction.md` or `sitemap-generation.md` for report generation tasks.

Each scenario has dedicated research focus and structure priorities:

#### Scenario Identification & Weight Matrix

| Scenario | Core Question | Focus Chapters | Key Priorities |
|----------|---------------|----------------|----------------|
| **Competitive Analysis** | What are they better at? | Products, Competition, Market | Product features, tech capabilities, market share, differentiation |
| **Investment Research** | What is this company worth? | Industry, Business Model, Finance | Market size (TAM/SAM/SOM), revenue streams, growth logic, moats |
| **Customer Research** | Should we partner with them? | Products (Highest), Customer Cases | Product capabilities, use cases, delivery capacity, integration |
| **Job Applicant Research** | Is this company right for me? | Company Overview, Team, Culture | Leadership, tech stack, benefits, career path, work-life balance |

**Chapter Weight Table** (Use to adjust report structure):

| Chapter | Competitive | Investment | Customer | Applicant |
|---------|-------------|------------|----------|-----------|
| 0. Executive Summary | High | High | High | High |
| 1. Company Overview | Medium | Medium | Low | High |
| 2. Products & Business | High | High | **Highest** | Medium |
| 3. Market & Customer | High | High | Medium | Low |
| 4. Industry Analysis | Medium | **Highest** | Low | Low |
| 5. Competition | **Highest** | High | Medium | Low |
| 6. Business Model & Finance | Low | **Highest** | Low | Low |
| 7. Strategy & Future | High | High | Medium | Medium |
| 8. Risk Analysis | Medium | High | Medium | Low |
| 9. Conclusion | High | High | High | Medium |

**Legend**: **Highest** > High > Medium > Low

#### Scenario Decision Tree

```
Step 1: Identify Scenario (from user input or auto-detection)
        │
        ├─ "竞品分析" / "competitor" / "对比XX公司" → Competitive Analysis
        ├─ "投资" / "估值" / "值得投" → Investment Research
        ├─ "合作" / "供应商" / "评估" → Customer Research
        └─ "工作" / "应聘" / "公司文化" → Job Applicant Research

Step 2: Select Priority Chapters (based on weight table)
        │
        ├─ **Highest** chapters → Put first, detailed analysis
        ├─ High chapters → Complete coverage
        ├─ Medium chapters → Brief introduction, key points only
        └─ Low chapters → Merge or omit

Step 3: Adjust Report Structure (reorder chapters by priority)
        │
        └─ Most important chapters come first (after Executive Summary)

Step 4: Fill Scenario-Specific Content
        │
        └─ Reference "Typical Logic" in research-framework.md

Step 5: Write Executive Summary LAST (summarize entire report)
```

#### Typical Logic by Scenario

**Competitive Analysis** (竞对分析):
- **Focus**: Product + Technology + Market
- **Structure**: Overview → Products → Competition → Market → Strategy → Threats
- **Key Questions**: What are their core products? What's their tech advantage? Who are their customers? What's their market share?
- **Output**: Product comparison, tech assessment, threat level, response recommendations

**Investment Research** (投资调研):
- **Focus**: Industry + Finance + Growth
- **Structure**: Overview → Industry → Business Model → Finance → Growth → Risks → Investment Logic
- **Key Questions**: How big is the market? What's the revenue model? What are growth drivers? What's the moat? What are the risks?
- **Output**: Investment thesis, growth potential, valuation, risk assessment, recommendation

**Customer Research** (客户调研):
- **Focus**: Product Capabilities + Customer Cases
- **Structure**: Overview → Products → Use Cases → Customer Cases → Integration → Capabilities → Risks
- **Key Questions**: Can they solve our pain points? Is their tech reliable? What customer cases exist? How's their service?
- **Output**: Suitability assessment, product analysis, case validation, implementation advice

**Job Applicant Research** (应聘调研):
- **Focus**: Team + Culture + Development
- **Structure**: Overview → Team → Culture → Tech Stack → Benefits → Career Path → Match Analysis
- **Key Questions**: What's the company stage? Who are the leaders? What's the culture? What's the tech stack? What are benefits? How's the growth?
- **Output**: Recommendation index, culture match, tech match, opportunities, concerns, interview prep

#### Common Base Info (All Scenarios)

Extract for all scenarios:
- Company name, website URL, founded year
- Headquarters location, company description
- Core business, target audience
- Contact info (email, phone, address)

### 6. JavaScript Extraction Templates

Use `browser_evaluate()` with these patterns:

```javascript
// Extract company description
const description = [
  document.querySelector('meta[name="description"]')?.content,
  ...Array.from(document.querySelectorAll('h1, h2'))
    .map(h => h.textContent)
].filter(Boolean).join(' | ');

// Extract contact information
const emailPattern = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
const phonePattern = /(\+\d{1,3}[- ]?)?\d{10,}/g;
const emails = text.match(emailPattern) || [];
const phones = text.match(phonePattern) || [];

// Extract product list
const products = Array.from(document.querySelectorAll('[class*="product"]'))
  .map(el => ({
    name: el.querySelector('h3, h4')?.textContent,
    description: el.querySelector('p')?.textContent
  }))
  .filter(p => p.name);
```

**See:** [data-extraction.md](references/data-extraction.md) for complete templates

### 7. Report Generation

**CRITICAL: Final report MUST be generated as DOCX format**

**MANDATORY - READ ENTIRE FILES**: Before generating any report, you MUST read the following files completely:

1. [`research-framework.md`](references/research-framework.md) (~400 lines) - **Standard 9-chapter template, Executive Summary framework, scenario weight tables, and typical logic for each scenario**
2. [`report-templates.md`](references/report-templates.md) (~700 lines) - **Four complete report templates with section structures and quality checklists**

**NEVER set range limits when reading these files. Read them entirely.**

**Do NOT load** `data-extraction.md`, `page-navigation.md`, or `sitemap-generation.md` for report generation tasks.

### Report Generation Workflow

**Step 1: Identify Scenario**
- Determine which of the 4 scenarios (Competitive/Investment/Customer/Applicant)
- Reference the weight table in research-framework.md

**Step 2: Select Report Structure**
- Use the weight table to determine chapter priorities
- **Highest** chapters → detailed analysis, put first
- **High** chapters → complete coverage
- **Medium** chapters → brief, key points only
- **Low** chapters → merge or omit

**Step 3: Generate Markdown Report**
- Use the appropriate template from report-templates.md
- Adjust chapter order based on scenario priorities
- Fill in extracted data from JSON files

**Step 4: Write Executive Summary LAST**
- Although it appears first, write it last
- Include: company positioning, core advantages, key risks, future outlook, overall assessment
- Reference framework in research-framework.md section 0

**Step 5: Convert to DOCX**
- Invoke `/docx` skill to convert Markdown to DOCX
- Save both formats (MD and DOCX)

**Markdown report template (intermediate format):**

```markdown
# {Company Name} {Scenario} Report

## 📊 Key Findings
[Overall score, key conclusions]

## 🏢 Company Overview
- Basic info, history, ownership

## 📌 [Scenario-Specific Sections]
[Customized content based on scenario]

## ⚠️ Risk Notes
[Potential risks and considerations]

## 📚 Data Sources
- Official website: {url}
- Pages visited: {list}
- Extraction timestamp: {time}
```

**DOCX conversion using /docx skill:**

```bash
# After generating Markdown report, invoke:
/docx create --input {markdown_file} --output {docx_file}

# Example:
/docx create --input ./company-research/字节跳动_竞品分析_20250210.md --output ./company-research/字节跳动_竞品分析_20250210.docx
```

**See:** [report-templates.md](references/report-templates.md) for complete templates

### 7.5. Save Persistent JSON Data (NEW!)

**CRITICAL: Must save JSON data before generating reports**

**Step 1: Create/update company directory**

```bash
# Create directory structure
mkdir -p ./company-research/data/{company_slug}/pages_data
```

**Step 2: Save basic_info.json**

```json
{
  "name": "字节跳动",
  "slug": "bytedance",
  "website": "https://www.bytedance.com",
  "founded_year": "2012",
  "headquarters": "北京",
  "description": "全球领先的科技公司",
  "core_business": ["短视频", "人工智能", "内容分发"],
  "contact": {
    "email": ["contact@bytedance.com"],
    "phone": [],
    "address": "北京市海淀区"
  },
  "aliases": ["ByteDance", "抖音", "TikTok母公司"],
  "last_updated": "2025-02-10T14:30:22Z"
}
```

**Step 3: Save sitemap.json**

See sitemap structure in section 7.5 above.

**Step 4: Save pages_data/{page_type}.json**

For each visited page, save extracted data:

```json
{
  "url": "https://www.bytedance.com/about",
  "type": "about",
  "title": "关于我们",
  "visited_at": "2025-02-10T14:30:22Z",
  "extracted_data": {
    "company_history": "2012年成立...",
    "mission": "激发创造，丰富生活",
    "values": ["用户至上", "追求极致", "终身学习"],
    "team_size": "150000+"
  },
  "snapshot": "page_html_or_text_for_reference"
}
```

**Step 5: Save metadata.json**

```json
{
  "company_slug": "bytedance",
  "research_scenario": "竞品分析",
  "researched_at": "2025-02-10T14:30:22Z",
  "research_duration_seconds": 180,
  "pages_visited": 8,
  "total_pages_discovered": 25,
  "data_quality_score": 85,
  "extraction_methods": ["browser_evaluate", "regex_fallback"],
  "tool_version": "company-research v2.0"
}
```

**Step 6: Update index.json**

```bash
# Read existing index.json or create new
# Add or update company entry
# Save back to ./company-research/data/index.json
```

**JSON storage benefits:**
- ✅ Claude can quickly read with Read tool
- ✅ Searchable with Grep tool
- ✅ Version control friendly
- ✅ Reusable across sessions
- ✅ Easy to update incrementally

### 8. Save Report

**CRITICAL: Generate both Markdown and DOCX formats**

**File structure:**
```
./company-research/
├── {公司名}_{场景}_20250210_143022.md       # Markdown report (intermediate)
├── {公司名}_{场景}_20250210_143022.docx      # DOCX report (final output)
└── {公司名}_{场景}_20250210_143022/         # Reference data
    ├── homepage_snapshot.txt
    ├── about_page_snapshot.txt
    └── ...
```

**File naming:** `{company}_{scenario}_{timestamp}.md` and `{company}_{scenario}_{timestamp}.docx`

**Required steps:**
1. Generate Markdown report using scenario template
2. Invoke `/docx` skill to convert Markdown to DOCX
3. Save both files to ./company-research/ directory
4. Provide user with both file paths

## Error Handling & Degradation

**Level 1: Website inaccessible**
- Try both HTTP and HTTPS
- Provide friendly error message
- Suggest checking URL or providing alternative

**Level 2: Key pages return 404**
- Infer information from available pages
- Mark as "Information missing"
- Continue with partial data

**Level 3: JavaScript extraction fails**
- Degrade to regex extraction
- Mark data quality as "low"
- Note extraction method used

**Level 4: Insufficient data**
- Expand search scope
- Generate partial report
- Note data limitations

**Principle:** Degradation preferred over failure - partial report is better than no report.

## Progress Updates

Keep user informed during extraction:

```
🔍 正在调研{公司名称}...

📊 数据收集中...
✓ 已访问首页: {url}
✓ 正在访问关键页面...
  ✓ 关于我们
  ⏳ 产品中心
  ○ 新闻动态

⏳ 预计还需 {time}...

📝 正在生成报告...
✅ 报告已生成!
```

## Performance Targets

- **Total time**: 3-5 minutes (depending on site complexity)
- **Pages visited**: 8-15 key pages (for data extraction)
- **Sitemap size**: 10-50 total pages discovered
- **Sitemap depth**: 2-3 layers maximum
- **Data quality**: Aim for 80%+ extraction accuracy
- **JSON storage**: All data saved before report generation

## Auto-Detection Examples

**Example 1: Direct company mention**

User: "字节跳动最近怎么样？"

Claude:
1. Detects "字节跳动" in message
2. Checks ./company-research/data/index.json
3. Finds match: slug="bytedance", last_researched="2025-02-10"
4. Prompts: "发现已有字节跳动的研究数据（3天前），是否加载？"

**Example 2: Contextual reference**

User: "我想做短视频竞品分析"

Claude:
1. Asks: "目标竞争对手是哪家公司？"
2. User: "抖音"
3. Checks for "抖音" → finds "bytedance" with alias "抖音"
4. Loads historical data or offers to research

**Example 3: No existing data**

User: "帮我研究一下 Anthropic"

Claude:
1. Checks index.json → no match
2. Proceeds with fresh research
3. Creates new entry in index.json
4. Saves to ./company-research/data/anthropic/

## Loading Historical Data Workflow

When user selects "Load historical data":

```bash
# Read all JSON files
./company-research/data/{company_slug}/basic_info.json     # Basic company info
./company-research/data/{company_slug}/sitemap.json        # Website structure
./company-research/data/{company_slug}/pages_data/*.json  # Page-specific data
./company-research/data/{company_slug}/metadata.json      # Research metadata

# Display key findings in chat
📊 字节跳动 - 研究摘要（2025-02-10）

公司定位：全球领先的科技公司
核心业务：短视频、人工智能、内容分发
团队规模：150,000+ 人
竞品威胁：⚠️ 高 - 市场份额领先，产品迭代快

💡 可用操作：
- 查看完整报告：./company-research/reports/字节跳动_竞品分析_20250210.md
- 查看网站地图：./company-research/data/bytedance/sitemap.json
- 增量更新：重新爬取最新数据
```

## Data Update Strategy

**Incremental update benefits:**
- Faster than full research (only new/changed pages)
- Maintains historical comparison
- Tracks company evolution over time

**Update workflow:**
1. Compare sitemap versions (old vs new)
2. Highlight new pages (🆕) and removed pages (❌)
3. Re-extract data from priority pages
4. Generate comparison report:

```markdown
## 🔄 数据更新对比

### 新增页面 (🆕)
- /ai-lab - AI实验室页面 (2025-02-09)
- /careers/remote - 远程工作职位 (2025-02-08)

### 移除页面 (❌)
- /product/legacy-app - 已下线产品

### 数据变化 (📈)
- 团队规模：100,000 → 150,000 (+50%)
- 新增产品：AI创作工具
```

## References

### references/research-framework.md (NEW!)

**MANDATORY - READ BEFORE GENERATING REPORTS**

Complete company research methodology including:
- **Standard 9-chapter report template** (Executive Summary, Company Overview, Products, Market, Industry, Competition, Business Model, Strategy, Risk, Conclusion)
- **Scenario weight tables** - How to adjust chapter priorities for each scenario (Competitive/Investment/Customer/Applicant)
- **Typical logic for each scenario** - Core questions, structure priorities, key outputs
- **Executive Summary framework** - Company positioning, core advantages, key risks, future outlook
- **Data quality assessment standards** - Completeness, accuracy, timeliness metrics

**Read when:** Generating reports for any scenario, or when determining how to structure research for different use cases.

### references/sitemap-generation.md

Complete guide for:
- Website sitemap generation (2-3 layers)
- Link discovery and categorization
- Prioritized page visiting
- Building sitemap structure
- JSON data persistence
- Auto-detection logic

**Read when:** Implementing sitemap generation or data persistence for the first time.

### references/data-extraction.md

Complete JavaScript extraction templates for:
- Company基本信息
- Products and services
- Contact information
- Team and culture
- Financial indicators

**Read when:** Implementing data extraction for new page types or debugging extraction failures.

### references/page-navigation.md

Page navigation strategies including:
- URL pattern matching rules
- Text content recognition
- Multi-language handling
- SPA application support

**Read when:** Troubleshooting navigation issues or adapting to new website structures.

### references/report-templates.md

Four complete report templates (one per scenario) with:
- Section structure
- Content guidelines
- Formatting standards
- Quality checklists

**Read when:** Generating reports for specific scenarios or customizing report format.

## Output Format

**CRITICAL: Final output MUST be DOCX format**

**Required output workflow:**
1. Generate Markdown report (intermediate format)
2. Convert to DOCX using `/docx` skill
3. Save both formats (user gets DOCX, MD kept for reference)

**All reports MUST be in Chinese (中文)**

**Final output requirements:**
- **Primary format**: DOCX file (using `/docx` skill)
- **Intermediate format**: Markdown (for reference and version control)
- Well-structured with clear section hierarchy
- Practical details included
- Sources clearly marked
- Saved to `./company-research/` directory

**DOCX conversion command:**
```bash
/docx create --input {markdown_file} --output {docx_file}
```

**Display to user:**
- Show brief summary in chat
- Provide both file paths (MD and DOCX)
- Emphasize DOCX as the final deliverable
- Offer refinement options

## Key Design Principles

1. **Adaptive navigation** - Intelligently recognize different website structures
2. **Scenario differentiation** - Different focus for each research scenario
3. **Quality assurance** - Data validation, source attribution, completeness checks
4. **Graceful degradation** - Attempt fallback strategies before failing completely
5. **Persistent storage** - JSON-based structured data for future reference (NEW!)
6. **Auto-detection** - Check historical data before starting new research (NEW!)
7. **Sitemap generation** - Systematic website structure mapping (NEW!)
8. **Incremental updates** - Support efficient data refresh without full re-crawl (NEW!)

## Quick Reference

**New in v2.0:**
- ✅ Automatic sitemap generation (2-3 layers, 10-50 pages)
- ✅ JSON persistent storage for Claude reference
- ✅ Auto-detection of previously researched companies
- ✅ Incremental update support with comparison
- ✅ Company name normalization and alias matching

**File locations:**
- Research data: `./company-research/data/{company_slug}/`
- Human reports: `./company-research/reports/`
- Master index: `./company-research/data/index.json`

**When to use:**
- User explicitly requests company research
- User mentions a company name that may have been researched before
- User asks about competitors, investment targets, or business partners
- User needs quick company information (load from JSON)
