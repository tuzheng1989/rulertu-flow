# Page Navigation Strategies

Strategies for intelligently navigating corporate websites and identifying key pages.

## URL Pattern Matching

Priority-based URL pattern recognition:

```javascript
const urlPatterns = {
  about: ['about', 'company', 'who-we-are', 'about-us', 'profile'],
  product: ['product', 'service', 'solution', 'offerings', 'products', 'services'],
  news: ['news', 'blog', 'press', 'media', 'updates', 'article'],
  contact: ['contact', 'contact-us', 'reach-us', 'get-in-touch'],
  careers: ['career', 'job', 'join-us', 'hiring', 'work-with-us'],
  investors: ['investor', 'ir', 'stock', 'shareholder']
};

function identifyPageType(url) {
  const lowerUrl = url.toLowerCase();

  for (const [type, patterns] of Object.entries(urlPatterns)) {
    for (const pattern of patterns) {
      if (lowerUrl.includes(pattern)) {
        return type;
      }
    }
  }

  return 'unknown';
}
```

## Text Content Recognition

When URL patterns are insufficient, use text content analysis:

```javascript
function identifyPageByContent(snapshot) {
  const title = snapshot.title?.toLowerCase() || '';
  const text = snapshot.textContent?.toLowerCase().substring(0, 1000) || '';

  const contentKeywords = {
    about: ['关于我们', '公司简介', 'about us', 'our story', 'who we are'],
    product: ['产品', '服务', 'product', 'service', 'solution'],
    news: ['新闻', '动态', 'news', 'blog', 'press'],
    contact: ['联系', 'contact', 'reach us'],
    careers: ['招聘', '职业', 'career', 'join', 'hiring']
  };

  for (const [type, keywords] of Object.entries(contentKeywords)) {
    for (const keyword of keywords) {
      if (title.includes(keyword) || text.includes(keyword)) {
        return type;
      }
    }
  }

  return 'unknown';
}
```

## Multi-Language Handling

Support both Chinese and English websites:

```javascript
const bilingualKeywords = {
  about: {
    zh: ['关于', '公司', '简介', '介绍'],
    en: ['about', 'company', 'profile', 'overview']
  },
  product: {
    zh: ['产品', '服务', '解决方案'],
    en: ['product', 'service', 'solution']
  },
  news: {
    zh: ['新闻', '动态', '资讯'],
    en: ['news', 'blog', 'press', 'media']
  },
  contact: {
    zh: ['联系', '我们'],
    en: ['contact', 'reach']
  }
};

function detectLanguage(text) {
  const chineseCharRatio = (text.match(/[\u4e00-\u9fa5]/g) || []).length / text.length;
  return chineseCharRatio > 0.3 ? 'zh' : 'en';
}
```

## SPA (Single Page Application) Handling

For modern SPA websites using React/Vue/Angular:

### Strategy 1: Wait for Route Changes

```javascript
// After clicking a navigation link
await browser_wait_for('networkidle'); // Wait for initial load

// Additional wait for SPA route updates
await page.waitForTimeout(1000); // Give time for client-side routing

// Or wait for specific URL change
await page.waitForURL(/\/about/);
```

### Strategy 2: Wait for Content Update

```javascript
// Take snapshot before navigation
const beforeSnapshot = await browser_snapshot();

// Click navigation link
await browser_click(ref);

// Wait for new content to appear
await browser_wait_for({textGone: beforeSnapshot.title});
```

### Strategy 3: Scroll for Lazy Loading

```javascript
// Scroll to trigger lazy-loaded content
await page.evaluate(() => {
  window.scrollTo(0, document.body.scrollHeight);
});

// Wait for new content to load
await page.waitForTimeout(2000);
```

## Navigation Priority System

### Priority 1: Must Visit (Required)

**Pages to visit:**
- About Us / Company Profile
- Products / Services / Solutions

**Rationale:**
- About page: Company background, history, team, culture
- Product page: Core offerings, features, pricing

### Priority 2: Important (High Value)

**Pages to visit if available:**
- News / Blog / Press
- Case Studies / Customers
- Contact (for contact info)

**Rationale:**
- News: Recent developments, company updates
- Cases: Proof points, success stories
- Contact: Direct communication channels

### Priority 3: Optional (Scenario-Specific)

**Visit based on scenario:**

| Scenario | Optional Pages |
|----------|--------------|
| Competitive Analysis | Pricing, Partners |
| Investment Research | Investors, Financial Reports |
| Customer Research | Case Studies, Testimonials |
| Job Applicant | Careers, Team, Culture |

## Link Discovery Strategy

### Method 1: Navigation Menu Analysis

```javascript
function extractNavigationLinks(snapshot) {
  const navSelectors = [
    'nav',
    '[role="navigation"]',
    '[class*="nav"]',
    '[class*="menu"]',
    'header ul',
    '[class*="header"] ul'
  ];

  for (const selector of navSelectors) {
    const links = Array.from(document.querySelectorAll(selector + ' a'))
      .map(a => ({
        text: a.textContent.trim(),
        url: a.href,
        ref: a // For later clicking
      }))
      .filter(link => link.text.length > 0 && link.text.length < 50);

    if (links.length > 0) {
      return links;
    }
  }

  return [];
}
```

### Method 2: Footer Links

```javascript
function extractFooterLinks(snapshot) {
  const footerSelectors = [
    'footer',
    '[class*="footer"]',
    '[class*="bottom"]'
  ];

  for (const selector of footerSelectors) {
    const links = Array.from(document.querySelectorAll(selector + ' a'))
      .map(a => ({
        text: a.textContent.trim(),
        url: a.href
      }))
      .filter(link => link.url); // Footer links often just text

    if (links.length > 3) {
      return links;
    }
  }

  return [];
}
```

## Smart Page Prioritization

Rank pages by relevance before visiting:

```javascript
function prioritizePages(links, scenario) {
  const scores = links.map(link => {
    let score = 0;

    // Priority 1 boost
    if (link.url.includes('/about') || link.text.includes('关于')) score += 100;
    if (link.url.includes('/product') || link.text.includes('产品')) score += 90;

    // Priority 2 boost
    if (link.url.includes('/news') || link.text.includes('新闻')) score += 70;
    if (link.url.includes('/case') || link.text.includes('案例')) score += 60;

    // Scenario-specific boost
    if (scenario === 'investment' && link.url.includes('investor')) score += 80;
    if (scenario === 'job' && link.url.includes('career')) score += 80;

    return { ...link, score };
  });

  // Sort by score descending
  return scores.sort((a, b) => b.score - a.score);
}
```

## Parallel vs Sequential Navigation

### Parallel (for independent pages)

```javascript
// Priority 2 pages can be visited in parallel
const parallelPages = priority2Pages.slice(0, 3);

await Promise.all([
  visitPage(parallelPages[0]),
  visitPage(parallelPages[1]),
  visitPage(parallelPages[2])
]);
```

### Sequential (for dependent or critical pages)

```javascript
// Priority 1 pages should be visited sequentially
for (const page of priority1Pages) {
  await visitPage(page);
  // Process data before next page
}
```

## Error Recovery

### Page Not Found (404)

```javascript
if (pageStatus === 404) {
  // Try alternative URL patterns
  const alternatives = generateAlternativeUrls(originalUrl);
  for (const altUrl of alternatives) {
    try {
      await browser_navigate(altUrl);
      if (pageStatus === 200) break;
    } catch (e) {
      continue;
    }
  }

  // If all fail, mark as missing and continue
  missingPages.push(originalUrl);
}
```

### Navigation Timeout

```javascript
try {
  await browser_navigate(url, { timeout: 30000 });
} catch (error) {
  if (error.name === 'TimeoutError') {
    // Try with longer timeout
    await browser_navigate(url, { timeout: 60000 });
  } else {
    // Log error and continue
    console.error(`Failed to navigate to ${url}:`, error);
  }
}
```

### JavaScript Execution Errors

```javascript
try {
  const data = await browser_evaluate(function() {
    // Extraction logic
  });
} catch (error) {
  // Fallback to text extraction
  const snapshot = await browser_snapshot();
  const text = snapshot.textContent;
  // Use regex patterns for extraction
}
```

## Navigation Workflow Example

```javascript
async function navigateCompanyWebsite(url, scenario) {
  // Step 1: Homepage
  await browser_navigate(url);
  await browser_wait_for('networkidle');
  const homepageSnapshot = await browser_snapshot();

  // Step 2: Discover links
  const links = extractNavigationLinks(homepageSnapshot);
  const prioritizedLinks = prioritizePages(links, scenario);

  // Step 3: Visit Priority 1 pages (sequential)
  const priority1Links = prioritizedLinks.filter(l => l.score >= 90);
  for (const link of priority1Links) {
    await browser_navigate(link.url);
    await browser_wait_for('networkidle');
    // Extract data
  }

  // Step 4: Visit Priority 2 pages (parallel)
  const priority2Links = prioritizedLinks.filter(l => l.score >= 60 && l.score < 90);
  const batch1 = priority2Links.slice(0, 2);
  await Promise.all(batch1.map(link => visitAndExtract(link)));

  // Step 5: Visit scenario-specific pages
  if (scenario === 'investment') {
    const investorPage = prioritizedLinks.find(l => l.score === 80);
    if (investorPage) {
      await browser_navigate(investorPage.url);
      await browser_wait_for('networkidle');
    }
  }

  return collectedData;
}
```

## Best Practices

1. **Always wait for networkidle** before extracting data
2. **Use snapshot to discover links** before clicking
3. **Prioritize pages** to visit most important first
4. **Handle SPA routing** with additional waits
5. **Implement graceful degradation** for failed pages
6. **Validate page content** after navigation
7. **Save snapshots** for debugging and reference
8. **Respect rate limits** - add delays between requests
9. **Track visited URLs** to avoid duplicates
10. **Log navigation progress** for user feedback
