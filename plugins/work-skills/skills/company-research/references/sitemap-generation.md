# Sitemap Generation & Data Persistence

Complete guide for generating website sitemaps and persisting research data in JSON format.

## Sitemap Generation Workflow

### Phase 1: Homepage Link Discovery

**Goal**: Extract all navigation links from homepage

```javascript
// Run via browser_evaluate() on homepage
function discoverHomepageLinks() {
  const result = {
    internal_links: [],
    external_links: [],
    social_links: []
  };

  const domainsToSkip = [
    'facebook.com', 'twitter.com', 'linkedin.com',
    'instagram.com', 'youtube.com', 'weibo.com'
  ];

  // Comprehensive selector list
  const selectors = [
    'nav a', '[role="navigation"] a',
    '[class*="nav"] a', '[class*="menu"] a',
    'header a', 'footer a',
    '.sidebar a', '.sidebar-menu a'
  ];

  for (const selector of selectors) {
    const elements = document.querySelectorAll(selector);

    elements.forEach(el => {
      try {
        const href = el.href;
        const text = el.textContent.trim();

        // Validation filters
        if (!href || !text || text.length < 1 || text.length > 100) {
          return;
        }

        // Skip anchors, javascript, mailto
        if (href.startsWith('#') ||
            href.startsWith('javascript:') ||
            href.startsWith('mailto:')) {
          return;
        }

        // Skip file downloads
        if (href.match(/\.(pdf|jpg|jpeg|png|gif|svg|zip|exe)$/i)) {
          return;
        }

        const currentDomain = window.location.hostname;
        const linkDomain = new URL(href).hostname;

        // Categorize link
        if (domainsToSkip.some(d => linkDomain.includes(d))) {
          result.social_links.push({ url: href, text });
        } else if (linkDomain === currentDomain) {
          // Convert relative URLs to absolute
          const absoluteUrl = href.startsWith('http')
            ? href
            : new URL(href, window.location.origin).href;

          result.internal_links.push({
            url: absoluteUrl,
            text,
            source_selector: selector
          });
        } else {
          result.external_links.push({ url: href, text });
        }
      } catch (e) {
        // Invalid URL, skip
      }
    });
  }

  // Deduplicate
  result.internal_links = dedupeByUrl(result.internal_links);
  result.external_links = dedupeByUrl(result.external_links);
  result.social_links = dedupeByUrl(result.social_links);

  return result;
}

function dedupeByUrl(links) {
  const seen = new Set();
  return links.filter(link => {
    if (seen.has(link.url)) {
      return false;
    }
    seen.add(link.url);
    return true;
  });
}
```

### Phase 2: Link Categorization

```javascript
function categorizeLinks(links) {
  const categories = {
    about: [],
    product: [],
    solution: [],
    service: [],
    news: [],
    blog: [],
    contact: [],
    careers: [],
    investors: [],
    pricing: [],
    cases: [],
    help: [],
    other: []
  };

  const patterns = {
    about: {
      url: /about|company|who-we-are|profile|overview|story|team/i,
      text: /关于|公司|团队|介绍|我们/i
    },
    product: {
      url: /product|offering/i,
      text: /产品|商品/i
    },
    solution: {
      url: /solution/i,
      text: /解决方案/i
    },
    service: {
      url: /service/i,
      text: /服务/i
    },
    news: {
      url: /news|press|media|article/i,
      text: /新闻|资讯|动态|媒体报道/i
    },
    blog: {
      url: /blog/i,
      text: /博客|日志/i
    },
    contact: {
      url: /contact|reach-us|get-in-touch/i,
      text: /联系|联络/i
    },
    careers: {
      url: /career|job|hiring|join-us|work-with-us|vacancy/i,
      text: /招聘|职位|加入我们|诚聘/i
    },
    investors: {
      url: /investor|ir|stock|shareholder|annual-report/i,
      text: /投资者|股票|年报/i
    },
    pricing: {
      url: /pricing|price|plan/i,
      text: /价格|收费标准|套餐/i
    },
    cases: {
      url: /case|customer|client|testimonial|success-story/i,
      text: /案例|客户|成功故事/i
    },
    help: {
      url: /help|support|doc|faq/i,
      text: /帮助|支持|文档|常见问题/i
    }
  };

  links.forEach(link => {
    let categorized = false;

    for (const [category, pattern] of Object.entries(patterns)) {
      if ((pattern.url && pattern.url.test(link.url)) ||
          (pattern.text && pattern.text.test(link.text))) {
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

### Phase 3: Prioritized Page Visiting

**Visit order (for sitemap expansion):**

1. **Priority 1 (Must visit, sequential):**
   - about (最多5个)
   - product (最多10个)
   - solution (最多5个)

2. **Priority 2 (Important, parallel batches):**
   - news (1-2个)
   - cases (1-2个)
   - contact (1个)

3. **Priority 3 (Optional, if time permits):**
   - careers (1个)
   - investors (1个)
   - pricing (1个)

**For each visited page:**

```javascript
async function visitAndExtractPage(link, parentUrl) {
  // Navigate
  await browser_navigate(link.url);
  await browser_wait_for('networkidle');

  // Extract page data
  const pageData = await browser_evaluate(function() {
    return {
      title: document.title,
      meta_description: document.querySelector('meta[name="description"]')?.content,
      h1: document.querySelector('h1')?.textContent,
      headings: Array.from(document.querySelectorAll('h2, h3')).map(h => h.textContent),
      internal_links: discoverPageLinks()  // Similar to homepage discovery
    };
  });

  // Return structured data
  return {
    url: link.url,
    title: pageData.title,
    type: inferPageType(link.url, pageData),
    parent_url: parentUrl,
    visited: true,
    visited_at: new Date().toISOString(),
    data: pageData,
    child_links: pageData.internal_links.map(l => l.url)
  };
}

function inferPageType(url, pageData) {
  const lowerUrl = url.toLowerCase();
  const lowerTitle = (pageData.title || '').toLowerCase();

  if (lowerUrl.includes('about') || lowerTitle.includes('about')) return 'about';
  if (lowerUrl.includes('product')) return 'product';
  if (lowerUrl.includes('pricing')) return 'pricing';
  // ... more patterns

  return 'unknown';
}
```

### Phase 4: Build Sitemap Structure

```javascript
function buildSitemap(homepageData, categorizedLinks, visitedPages) {
  const sitemap = {
    url: homepageData.url,
    title: homepageData.title,
    type: 'homepage',
    visited: true,
    visited_at: homepageData.visited_at,
    children: []
  };

  // Add categorized pages as children
  for (const [category, links] of Object.entries(categorizedLinks)) {
    links.forEach(link => {
      // Check if this page was visited
      const visited = visitedPages.find(p => p.url === link.url);

      const node = {
        url: link.url,
        text: link.text,
        type: category,
        visited: !!visited,
        visited_at: visited?.visited_at || null,
        children: []
      };

      // If visited, add its child links
      if (visited && visited.child_links) {
        visited.child_links.forEach(childUrl => {
          node.children.push({
            url: childUrl,
            type: 'discovered',
            visited: false,
            discovered_from: link.url
          });
        });
      }

      sitemap.children.push(node);
    });
  }

  // Add metadata
  sitemap.metadata = {
    total_pages: countTotalPages(sitemap),
    visited_pages: countVisitedPages(sitemap),
    max_depth: calculateMaxDepth(sitemap),
    generated_at: new Date().toISOString(),
    categories: Object.keys(categorizedLinks)
  };

  return sitemap;
}

function countTotalPages(node, count = 0) {
  count += 1;
  if (node.children) {
    node.children.forEach(child => {
      count = countTotalPages(child, count);
    });
  }
  return count;
}

function countVisitedPages(node, count = 0) {
  if (node.visited) count += 1;
  if (node.children) {
    node.children.forEach(child => {
      count = countVisitedPages(child, count);
    });
  }
  return count;
}

function calculateMaxDepth(node, currentDepth = 0) {
  if (!node.children || node.children.length === 0) {
    return currentDepth;
  }

  const childDepths = node.children.map(child =>
    calculateMaxDepth(child, currentDepth + 1)
  );

  return Math.max(...childDepths);
}
```

## Data Persistence Workflow

### File Structure Creation

```bash
# Create directory structure
COMPANY_SLUG="bytedance"  # Normalized company name
BASE_DIR="./company-research/data/${COMPANY_SLUG}"

mkdir -p "${BASE_DIR}/pages_data"
```

### Saving JSON Data

**basic_info.json**

```javascript
async function saveBasicInfo(companyData, slug) {
  const basicInfo = {
    // Identity
    name: companyData.name,
    slug: slug,
    aliases: companyData.aliases || [],
    website: companyData.website,

    // Basic details
    founded_year: companyData.founded_year || null,
    headquarters: companyData.headquarters || null,
    description: companyData.description || null,

    // Business info
    core_business: companyData.core_business || [],
    industry: companyData.industry || null,
    target_audience: companyData.target_audience || null,

    // Contact
    contact: {
      email: companyData.emails || [],
      phone: companyData.phones || [],
      address: companyData.address || null
    },

    // Metadata
    last_updated: new Date().toISOString(),
    data_source: 'official_website',
    confidence_score: calculateConfidence(companyData)
  };

  await fs.writeFile(
    `${BASE_DIR}/basic_info.json`,
    JSON.stringify(basicInfo, null, 2),
    'utf8'
  );
}
```

**sitemap.json**

```javascript
async function saveSitemap(sitemap) {
  await fs.writeFile(
    `${BASE_DIR}/sitemap.json`,
    JSON.stringify(sitemap, null, 2),
    'utf8'
  );
}
```

**pages_data/{page_type}.json**

```javascript
async function savePageData(pageType, pageData) {
  // Sanitize filename
  const safeType = pageType.replace(/[^a-z0-9_]/gi, '_');
  const filename = `${BASE_DIR}/pages_data/${safeType}.json`;

  const fileData = {
    url: pageData.url,
    type: pageType,
    title: pageData.title,
    visited_at: pageData.visited_at,

    // Extracted content
    extracted_data: {
      headings: pageData.headings,
      meta_description: pageData.meta_description,
      content_summary: pageData.content_summary,
      key_points: pageData.key_points
    },

    // Raw data for reference
    raw_snapshot: {
      title: pageData.title,
      h1: pageData.h1,
      h2s: pageData.h2s,
      text_preview: pageData.text_preview?.substring(0, 1000)
    }
  };

  await fs.writeFile(
    filename,
    JSON.stringify(fileData, null, 2),
    'utf8'
  );
}
```

**metadata.json**

```javascript
async function saveMetadata(metadata) {
  const metadataJson = {
    company_slug: metadata.slug,
    company_name: metadata.name,

    // Research details
    research_scenario: metadata.scenario,
    researched_at: new Date().toISOString(),
    research_duration_seconds: metadata.duration,

    // Sitemap stats
    sitemap: {
      total_pages: metadata.total_pages,
      visited_pages: metadata.visited_pages,
      max_depth: metadata.max_depth
    },

    // Quality indicators
    data_quality_score: metadata.quality_score,
    extraction_methods: metadata.extraction_methods,
    completeness_ratio: metadata.completeness_ratio,

    // Technical details
    tool_version: 'company-research v2.0',
    user_session: metadata.session_id
  };

  await fs.writeFile(
    `${BASE_DIR}/metadata.json`,
    JSON.stringify(metadataJson, null, 2),
    'utf8'
  );
}
```

### Updating Master Index

**index.json**

```javascript
async function updateIndex(companyData) {
  const indexPath = './company-research/data/index.json';

  let index = { companies: [], last_updated: null };

  // Read existing index
  if (fs.existsSync(indexPath)) {
    const content = await fs.readFile(indexPath, 'utf8');
    index = JSON.parse(content);
  }

  // Find existing entry or create new
  const existingIndex = index.companies.findIndex(
    c => c.slug === companyData.slug
  );

  const entry = {
    slug: companyData.slug,
    names: [companyData.name, ...(companyData.aliases || [])],
    website: companyData.website,
    last_researched: new Date().toISOString(),
    scenarios: existingIndex >= 0
      ? [...new Set([...index.companies[existingIndex].scenarios, companyData.scenario])]
      : [companyData.scenario],
    data_quality: companyData.quality_score,
    sitemap_pages: companyData.total_pages
  };

  if (existingIndex >= 0) {
    index.companies[existingIndex] = entry;
  } else {
    index.companies.push(entry);
  }

  index.last_updated = new Date().toISOString();

  // Sort by last_researched (newest first)
  index.companies.sort((a, b) =>
    new Date(b.last_researched) - new Date(a.last_researched)
  );

  await fs.writeFile(
    indexPath,
    JSON.stringify(index, null, 2),
    'utf8'
  );
}
```

## Auto-Detection Logic

### Company Name Matching

```javascript
function normalizeCompanyName(name) {
  return name
    .toLowerCase()
    .trim()
    // Remove spaces, hyphens, underscores
    .replace(/[\s\-_]+/g, '')
    // Remove special characters (keep Chinese, alphanumeric)
    .replace(/[^\w\u4e00-\u9fa5]/g, '');
}

function generateSearchVariants(name) {
  const variants = new Set();

  // Direct normalization
  variants.add(normalizeCompanyName(name));

  // English translations for common companies
  const translations = {
    '字节跳动': ['bytedance', 'douyin', 'tiktok'],
    '腾讯': ['tencent'],
    '阿里巴巴': ['alibaba', 'alibabacloud'],
    '百度': ['baidu']
  };

  if (translations[name]) {
    translations[name].forEach(t => variants.add(t));
  }

  // Partial matches (first few chars)
  const normalized = normalizeCompanyName(name);
  for (let i = 3; i <= normalized.length; i++) {
    variants.add(normalized.substring(0, i));
  }

  return Array.from(variants);
}

function findCompanyInIndex(index, companyName) {
  const variants = generateSearchVariants(companyName);

  for (const company of index.companies) {
    // Check slug
    for (const variant of variants) {
      if (company.slug.includes(variant)) {
        return company;
      }
    }

    // Check names and aliases
    for (const name of company.names) {
      for (const variant of variants) {
        if (normalizeCompanyName(name).includes(variant)) {
          return company;
        }
      }
    }
  }

  return null;
}
```

## Best Practices

1. **Always save JSON before generating reports** - Ensures data persistence even if report generation fails
2. **Validate JSON structure** - Use JSON Schema if possible
3. **Handle concurrent access** - Use file locking if multiple research sessions run in parallel
4. **Compress old data** - Archive data older than 30 days
5. **Index performance** - Keep index.json under 1000 entries for fast searching
6. **Error recovery** - If JSON save fails, log error but continue with report generation
7. **Data quality scoring** - Track quality over time to identify reliable sources
