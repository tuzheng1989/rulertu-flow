# Report Templates

Complete report templates for the four research scenarios.

## Template 1: 竞争对手分析 (Competitive Analysis)

```markdown
# {公司名称} 竞品分析报告

> 📅 生成时间：{timestamp}
> 🔗 官网：{website_url}
> 📊 数据来源：公司官网

---

## 📊 综合评估

**市场定位评分**: ★★★★☆
**产品竞争力**: ★★★★☆
**差异化程度**: ★★★☆☆

**核心定位**: {一句话概括公司的核心定位和目标市场}

---

## 🏢 公司概况

### 基本信息
- **成立时间**: {founded_year || "未知"}
- **总部地址**: {headquarters || "未知"}
- **公司规模**: {team_size || "未知"}
- **发展阶段**: {stage || "未知"}

### 公司简介
{company_description}

### 核心业务
{core_business_list}

---

## 🛠️ 产品与服务

### 主要产品

{#each products}
**{name}**
- 描述：{description}
- 链接：{link || "无"}
{/each}

### 产品功能特点

{product_features_summary}

### 定价策略

{pricing_info || "未公开定价信息"}

---

## 🎯 市场定位

### 目标客户

{target_audience || "未知"}

### 市场细分

{market_segments}

### 竞争优势

{#each advantages}
- {advantage}
{/each}

---

## ⚔️ 差异化分析

### 与竞争对手的差异

{differentiation_points}

### 独特价值主张

{unique_value_proposition || "未明确说明"}

---

## 📈 市场表现

### 市场份额

{market_share_estimate || "未知"}

### 增长态势

{growth_indicators || "未知"}

### 客户案例

{#if customer_cases}
{#each customer_cases}
- **{company}** ({industry}): {description}
{/each}
{/if}
{#unless customer_cases}
暂无公开客户案例
{/unless}

---

## 🚀 发展方向

### 产品路线图

{product_roadmap || "未公开"}

### 战略重点

{strategic_focus || "未知"}

---

## ⚠️ 竞争威胁

对我们产品的潜在威胁：
- {threat_1}
- {threat_2}

应对建议：
- {response_1}
- {response_2}

---

## 📚 数据来源

- **官网主页**: {homepage_url}
- **访问页面**: {pages_visited_list}
- **提取时间**: {extraction_timestamp}
- **数据质量**: {data_quality_score}/100
```

## Template 2: 投资调研 (Investment Research)

```markdown
# {公司名称} 投资调研报告

> 📅 生成时间：{timestamp}
> 🔗 官网：{website_url}
> 📊 数据来源：公司官网

---

## 📊 投资建议

**综合评分**: ★★★★☆
**投资建议**: [买入/持有/卖出/观望]

**核心结论**:
{investment_summary}

---

## 🏢 公司概况

### 基本信息
- **成立时间**: {founded_year}
- **总部地址**: {headquarters}
- **公司规模**: {team_size}
- **所属行业**: {industry || "未知"}

### 公司简介
{company_description}

### 发展历程
{company_history || "未知"}

### 股权结构
{ownership_structure || "未公开"}

---

## 💼 商业模式

### 商业模式概述
{business_model_description}

### 收入来源

{#each revenue_streams}
- **{source}**: {description}
{/each}

### 客户类型
{customer_types || "未知"}

---

## 🎯 市场地位

### 市场规模
{market_size || "未知"}

### 市场份额
{market_share || "未知"}

### 行业排名
{industry_ranking || "未知"}

---

## ⚡ 核心竞争力

{#each competitive_advantages}
- **{name}**: {description}
{/each}

### 护城河分析
{moat_analysis || "未知"}

---

## 📈 增长潜力

### 增长驱动因素
{growth_drivers || "未知"}

### 未来机会
{opportunities || "未知"}

### 扩张计划
{expansion_plans || "未公开"}

---

## ⚠️ 风险评估

### 市场风险
- {market_risk_1}
- {market_risk_2}

### 运营风险
- {operational_risk_1}
- {operational_risk_2}

### 财务风险
{financial_risks || "未知"}

### 合规风险
{compliance_risks || "未知"}

---

## 💰 财务健康度

> ⚠️ 注：以下信息基于公开数据，如需详细财务数据请查阅财报

**盈利能力**: {profitability || "未知"}
**增长趋势**: {revenue_growth || "未知"}
**融资情况**: {funding_info || "未公开"}

---

## 👥 团队分析

### 核心团队
{core_team || "未知"}

### 组织架构
{organization_structure || "未知"}

### 企业文化
{company_culture || "未知"}

---

## 🎯 投资逻辑

### 看点
{investment_bull_case || "未知"}

### 风险点
{investment_bear_case || "未知"}

---

## 📚 数据来源与免责声明

**数据来源**:
- 官网：{website_url}
- 访问页面：{pages_visited}
- 提取时间：{timestamp}

**免责声明**: 本报告基于公开信息生成，不构成任何投资建议。投资者应独立判断并自行承担投资风险。

**数据质量**: {data_quality_score}/100
**完整度**: {completeness_score}%
```

## Template 3: 客户调研 (Customer Research)

```markdown
# {公司名称} 客户调研报告

> 📅 生成时间：{timestamp}
> 🔗 官网：{website_url}
> 📊 数据来源：公司官网

---

## 📊 适用性评估

**推荐指数**: ★★★★☆

**适用场景**:
{use_cases_summary}

---

## 🏢 公司概况

### 基本信息
- **成立时间**: {founded_year}
- **总部地址**: {headquarters}
- **公司规模**: {team_size}

### 公司定位
{company_positioning}

---

## 💡 解决的核心痛点

{#each pain_points}
- **{pain_point}**
  - 解决方案：{solution}
  - 目标用户：{target_users}
{/each}

### 痛点覆盖度
{pain_points_coverage}

---

## 🎯 典型使用场景

{#each use_cases}
### {scenario_name}
- **适用对象**: {target_audience}
- **使用场景**: {description}
- **价值点**: {value_proposition}
{/each}

---

## 📚 客户案例

{#if customer_cases}
{#each customer_cases}
### {company} ({industry})

**背景**: {background}

**挑战**: {challenge}

**解决方案**: {solution}

**成果**: {results}

**链接**: {case_study_link || "无"}

{/each}
{else}
暂无公开客户案例
{/if}

---

## 🔗 集成能力

### 技术集成
{tech_integration || "未知"}

### 数据集成
{data_integration || "未知"}

### API 支持
{api_support || "未知"}

---

## 🎁 定价与方案

### 定价模式
{pricing_model || "未公开"}

### 方案类型
{offering_types}

---

## 🏆 产品优势

{#each advantages}
- {advantage}
{/each}

---

## ⚠️ 局限性

{#each limitations}
- {limitation}
{/each}

---

## 🔍 评估维度

| 维度 | 评分 | 说明 |
|-----|------|------|
| 功能完整性 | ★★★☆☆ | {feature_completeness_note} |
| 易用性 | ★★★★☆ | {usability_note} |
| 集成便利性 | ★★★☆☆ | {integration_note} |
| 性价比 | ★★★★☆ | {value_note} |
| 服务支持 | ★★★☆☆ | {support_note} |

---

## 💡 建议

### 适用建议
{recommendation_for_qualified}

### 不适用场景
{not_recommended_scenarios}

### 实施建议
{implementation_advice}

---

## 📚 数据来源

- 官网：{website_url}
- 客户案例：{case_studies_pages}
- 提取时间：{timestamp}

**数据质量**: {data_quality_score}/100
```

## Template 4: 应聘调研 (Job Applicant Research)

```markdown
# {公司名称} 应聘调研报告

> 📅 生成时间：{timestamp}
> 🔗 官网：{website_url}
> 📊 数据来源：公司官网

---

## 📊 推荐指数

**综合评分**: ★★★★☆

**推荐理由**: {recommendation_reason}

---

## 🏢 公司概况

### 基本信息
- **成立时间**: {founded_year}
- **总部地址**: {headquarters}
- **公司规模**: {team_size}
- **所属行业**: {industry}

### 公司简介
{company_description}

### 发展阶段
{development_stage}

---

## 🏛️ 公司文化

### 文化关键词
{culture_keywords}

### 文化描述
{company_culture_description}

### 价值观
{#each values}
- **{value}**: {description}
{/each}

### 工作风格
{work_style || "未知"}

---

## 👥 团队情况

### 团队规模
{team_size_detail}

### 团队构成
{team_composition || "未知"}

### 核心团队
{core_team_background || "未公开"}

---

## 💻 技术栈

### 后端技术
{backend_tech_stack}

### 前端技术
{frontend_tech_stack}

### 基础设施
{infrastructure_stack}

### 开发工具
{dev_tools}

### 技术亮点
{tech_highlights || "未知"}

---

## 🎁 薪酬福利

### 薪酬范围
{salary_range || "未公开"}

### 福利待遇

{#each benefits}
- {benefit}
{/each}

### 工作时间
{work_hours || "未知"}

### 远程工作
{remote_work_policy || "不支持"}

---

## 📈 职业发展

### 晋升路径
{career_path || "未知"}

### 培训体系
{training_program || "未知"}

### 发展机会
{growth_opportunities || "未知"}

### 内部转岗
{internal_transfer || "未知"}

---

## 🚀 招聘职位

### 当前热招职位
{#each open_positions}
- **{title}** ({department})
  - 要求：{requirements}
  - 职责：{responsibilities}
  - 链接：{link}
{/each}

### 人才需求特点
{talent_demand_summary}

---

## 🏆 优势

{#each advantages}
- {advantage}
{/each}

---

## ⚠️ 注意事项

{#each concerns}
- {concern}
{/each}

---

## 🔍 匹配度分析

### 技能匹配
{skills_match_score}

### 经验匹配
{experience_match_score}

### 文化匹配
{culture_match_score}

### 综合建议
{overall_recommendation}

---

## 📝 面试准备建议

### 技术准备
{technical_prep_advice}

### 行为面试准备
{behavioral_prep_advice}

### 公司了解重点
{company_research_focus}

---

## 📚 数据来源

- 官网：{website_url}
- 招聘页面：{careers_pages}
- 提取时间：{timestamp}

**数据质量**: {data_quality_score}/100
**信息完整度**: {completeness_score}%
```

## Report Generation Guidelines

### Section Completeness

**Critical sections** (must include):
- 公司概况
- 场景特定核心内容
- 数据来源
- 时间戳

**Optional sections** (include if data available):
- 财务数据
- 客户案例
- 团队详情
- 定价信息

### Data Quality Indicators

Add badges to indicate data quality:
- ✅ **官网确认** - Data from official website
- ⚠️ **需验证** - Data needs verification
- ❓ **推测** - Reasoned inference
- ❌ **未获取** - Data not available

### Formatting Standards

1. **Use consistent emoji** for each section type
2. **Maintain hierarchy** with proper heading levels
3. **Include metadata** at the top (date, source, quality)
4. **Add tables** for structured comparisons
5. **Use lists** for easy scanning
6. **Bold key terms** for emphasis
7. **Link to sources** when available

### Customization

Each scenario should customize:
1. **Section order** - Most important info first
2. **Section emphasis** - Expand on relevant sections
3. **Data priorities** - What to extract first
4. **Tone and style** - Match user expectations
5. **Action items** - Specific recommendations

### Quality Checklist

Before finalizing report:
- [ ] All critical sections present
- [ ] Data sources clearly marked
- [ ] Timestamp included
- [ ] Proper Chinese formatting
- [ ] No placeholder text (use "未知" or "未公开")
- [ ] Consistent emoji usage
- [ ] Proper heading hierarchy
- [ ] Links formatted correctly
- [ ] Quality score indicated
