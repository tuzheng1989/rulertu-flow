# Data Extraction Templates

JavaScript templates for extracting company information using `browser_evaluate()`.

## Basic Information Extraction

```javascript
// Extract company description from meta tags and headings
const description = [
  document.querySelector('meta[name="description"]')?.content,
  ...Array.from(document.querySelectorAll('h1, h2'))
    .map(h => h.textContent.trim())
    .filter(text => text.length > 10)
].filter(Boolean).join(' | ');

// Extract founding year from text
const yearPattern = /(?:成立于|founded|since|established).*?(\d{4})/i;
const yearMatch = document.body.innerText.match(yearPattern);
const foundedYear = yearMatch ? yearMatch[1] : null;

// Extract company location
const locationPatterns = [
  /(?:总部|headquarter|位于|located in)[:：\s]*([^,。\n]+)/i,
  /(?:地址|address)[:：\s]*([^。\n]+)/i
];
let location = null;
for (const pattern of locationPatterns) {
  const match = document.body.innerText.match(pattern);
  if (match) {
    location = match[1].trim();
    break;
  }
}
```

## Contact Information Extraction

```javascript
// Extract email addresses
const emailPattern = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
const text = document.body.innerText;
const emails = text.match(emailPattern) || [];

// Extract phone numbers (support multiple formats)
const phonePatterns = [
  /(\+\d{1,3}[- ]?)?\(?\d{3,4}\)?[- ]?\d{3,4}[- ]?\d{4,}/g,  // International
  /(\d{3,4}[- ]){2}\d{4}/g,  // Simple format
  /1[3-9]\d{9}/g  // Chinese mobile
];
const phones = [];
for (const pattern of phonePatterns) {
  const matches = text.match(pattern) || [];
  phones.push(...matches);
}

// Extract address
const addressSelectors = [
  'address',
  '[class*="address"]',
  '[class*="contact"]',
  '[itemtype*="PostalAddress"]'
];
let address = null;
for (const selector of addressSelectors) {
  const el = document.querySelector(selector);
  if (el) {
    address = el.textContent.trim();
    break;
  }
}
```

## Product/Service Extraction

```javascript
// Extract product cards
const products = Array.from(document.querySelectorAll([
  '[class*="product"]',
  '[class*="service"]',
  '[class*="solution"]'
].join(', ')))
  .filter(el => {
    // Filter out non-product containers
    const text = el.textContent.toLowerCase();
    return text.length > 20 && text.length < 500;
  })
  .map(el => {
    const titleEl = el.querySelector('h1, h2, h3, h4, [class*="title"]') || el;
    const descEl = el.querySelector('p, [class*="desc"], [class*="detail"]');
    const linkEl = el.querySelector('a');

    return {
      name: titleEl.textContent.trim(),
      description: descEl ? descEl.textContent.trim().substring(0, 200) : '',
      link: linkEl ? linkEl.href : null
    };
  })
  .filter(p => p.name && p.name.length > 2);

// Extract pricing information (if available)
const pricingPatterns = [
  /(?:￥|\$|USD|CNY)\s*(\d+(?:,\d{3})*(?:\.\d{2})?)/g,
  /\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:元|dollars?|USD)/gi
];
const extractPricing = (text) => {
  const prices = [];
  for (const pattern of pricingPatterns) {
    const matches = text.match(pattern) || [];
    prices.push(...matches);
  }
  return [...new Set(prices)]; // Deduplicate
};
```

## Team and Culture Extraction

```javascript
// Extract team size mentions
const teamSizePatterns = [
  /(?:团队|team).*?(\d+).*?(?:人|people|member)/i,
  /(?:员工|employees?).*?(\d+)/i,
  /(\d+).*?(?:人|people).*?(?:团队|team)/i
];
let teamSize = null;
for (const pattern of teamSizePatterns) {
  const match = document.body.innerText.match(pattern);
  if (match) {
    teamSize = match[1];
    break;
  }
}

// Extract tech stack from job postings or tech pages
const techKeywords = [
  'Python', 'JavaScript', 'Java', 'Go', 'Rust', 'C++',
  'React', 'Vue', 'Angular', 'Node.js',
  'TensorFlow', 'PyTorch', 'Keras',
  'AWS', 'Azure', 'GCP',
  'Docker', 'Kubernetes', 'Linux'
];
const extractTechStack = (text) => {
  const found = [];
  const lowerText = text.toLowerCase();
  for (const tech of techKeywords) {
    if (lowerText.includes(tech.toLowerCase())) {
      found.push(tech);
    }
  }
  return [...new Set(found)];
};

// Extract benefits/perks (for job applicant research)
const benefitKeywords = [
  '五险一金', '年终奖', '带薪年假', '弹性工作',
  'health insurance', 'bonus', 'remote work', 'stock options'
];
const extractBenefits = (text) => {
  const benefits = [];
  const sentences = text.split(/[。！.\!]/);
  for (const sentence of sentences) {
    for (const keyword of benefitKeywords) {
      if (sentence.toLowerCase().includes(keyword.toLowerCase())) {
        benefits.push(sentence.trim());
        break;
      }
    }
  }
  return [...new Set(benefits)];
};
```

## Business Model Extraction (Investment Research)

```javascript
// Extract revenue model indicators
const revenueIndicators = {
  subscription: ['订阅', 'subscription', 'SaaS', '会员'],
  transaction: ['交易', 'transaction', 'commission', '佣金'],
  advertising: ['广告', 'advertising', 'ads', '变现'],
  freemium: ['免费增值', 'freemium', 'basic.*pro'],
  enterprise: ['企业', 'enterprise', 'B2B']
};

const identifyRevenueModel = (text) => {
  const lowerText = text.toLowerCase();
  const models = [];

  for (const [model, keywords] of Object.entries(revenueIndicators)) {
    for (const keyword of keywords) {
      if (lowerText.includes(keyword.toLowerCase())) {
        models.push(model);
        break;
      }
    }
  }

  return models.length > 0 ? models : ['unclear'];
};

// Extract competitive advantages
const advantagePatterns = [
  /(?:优势|advantage|strength)[:：\s]*([^\n。]+)/gi,
  /(?:核心|core).*?(?:竞争力|competitiveness)[:：\s]*([^\n。]+)/gi
];
const extractAdvantages = (text) => {
  const advantages = [];
  for (const pattern of advantagePatterns) {
    let match;
    while ((match = pattern.exec(text)) !== null) {
      advantages.push(match[1].trim());
    }
  }
  return [...new Set(advantages)];
};
```

## Customer Case Extraction (Customer Research)

```javascript
// Extract customer case studies
const cases = Array.from(document.querySelectorAll([
  '[class*="case"]',
  '[class*="customer"]',
  '[class*="client"]',
  '[class*="story"]'
].join(', ')))
  .filter(el => {
    const text = el.textContent;
    return text.length > 50 && text.length < 1000;
  })
  .map(el => {
    const companyEl = el.querySelector('[class*="company"], [class*="name"], h3, h4');
    const industryEl = el.querySelector('[class*="industry"]');
    const descEl = el.querySelector('p, [class*="desc"]');

    return {
      company: companyEl ? companyEl.textContent.trim() : '',
      industry: industryEl ? industryEl.textContent.trim() : '',
      description: descEl ? descEl.textContent.trim().substring(0, 300) : ''
    };
  })
  .filter(c => c.company || c.description);

// Extract pain points addressed (from product descriptions)
const painPointIndicators = [
  '解决', 'solves?', 'addresses?',
  '痛点', 'pain point',
  '挑战', 'challenge',
  '帮助', 'helps?',
  '提升', 'improve'
];
const extractPainPoints = (text) => {
  const points = [];
  const sentences = text.split(/[。！.\!]/);

  for (const sentence of sentences) {
    for (const indicator of painPointIndicators) {
      if (sentence.toLowerCase().match(indicator)) {
        points.push(sentence.trim());
        break;
      }
    }
  }

  return [...new Set(points)];
};
```

## News and Updates Extraction

```javascript
// Extract news items
const newsItems = Array.from(document.querySelectorAll([
  '[class*="news"]',
  '[class*="article"]',
  '[class*="post"]',
  '[class*="update"]'
].join(', ')))
  .filter(el => {
    const text = el.textContent;
    return text.length > 30 && text.length < 500;
  })
  .map(el => {
    const titleEl = el.querySelector('h1, h2, h3, h4, [class*="title"]');
    const dateEl = el.querySelector('[class*="date"], [datetime], time');
    const linkEl = el.querySelector('a');

    return {
      title: titleEl ? titleEl.textContent.trim() : '',
      date: dateEl ? dateEl.getAttribute('datetime') || dateEl.textContent : '',
      link: linkEl ? linkEl.href : null
    };
  })
  .filter(n => n.title);

// Extract latest news date
const getLatestNewsDate = () => {
  const dates = newsItems
    .map(item => item.date ? new Date(item.date) : null)
    .filter(date => date && !isNaN(date));

  return dates.length > 0 ? new Date(Math.max(...dates)) : null;
};
```

## Data Validation

```javascript
// Validate extracted data
const validateData = (data) => {
  const validated = {};

  // Clean and validate email
  if (data.email) {
    const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    validated.email = emailPattern.test(data.email) ? data.email : null;
  }

  // Clean and validate URL
  if (data.website) {
    try {
      new URL(data.website);
      validated.website = data.website;
    } catch {
      validated.website = null;
    }
  }

  // Clean text fields
  for (const [key, value] of Object.entries(data)) {
    if (typeof value === 'string') {
      validated[key] = value.trim().substring(0, 500); // Limit length
    }
  }

  return validated;
};
```

## Usage Examples

```javascript
// Extract basic company info
const basicInfo = {
  name: document.querySelector('h1')?.textContent || document.title,
  description: extractDescription(),
  foundedYear: extractYear(),
  location: extractLocation(),
  email: extractEmail(),
  phone: extractPhone(),
  website: window.location.href
};

// Extract products
const products = extractProducts();

// Extract business model (for investment research)
const businessModel = {
  revenueModel: identifyRevenueModel(document.body.innerText),
  advantages: extractAdvantages(document.body.innerText)
};

// Validate all data
const validatedData = validateData({
  ...basicInfo,
  ...businessModel
});

// Return to Claude
return JSON.stringify(validatedData, null, 2);
```

## Best Practices

1. **Always validate data** before returning
2. **Use multiple selectors** for robustness
3. **Limit string lengths** to avoid excessive data
4. **Filter out noise** (too short/long content)
5. **Handle missing data** gracefully with null/default values
6. **Deduplicate results** to avoid redundancy
7. **Use regex patterns** cautiously - test with real data
8. **Return structured JSON** for easy parsing
