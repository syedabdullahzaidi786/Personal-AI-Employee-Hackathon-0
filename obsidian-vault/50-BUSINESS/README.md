# 50-BUSINESS: Business Intelligence & Logic

## Purpose
Business models, analytics, KPIs, decision frameworks, and business logic that guide AI agent decision-making and operations.

## Structure

```
50-BUSINESS/
├── models/              # Business models and frameworks
│   ├── revenue/         # Revenue models
│   ├── customer/        # Customer lifecycle models
│   ├── pricing/         # Pricing strategies
│   └── operations/      # Operational models
├── analytics/           # Business analytics and reports
│   ├── dashboards/      # BI dashboards
│   ├── reports/         # Standard reports
│   ├── metrics/         # KPI definitions
│   └── forecasts/       # Predictive analytics
├── rules/               # Business rules engine
│   ├── pricing-rules/   # Dynamic pricing
│   ├── eligibility/     # Qualification rules
│   ├── automation/      # Business automation
│   └── validation/      # Business validation
├── strategies/          # Strategic frameworks
├── optimization/        # Business optimization
└── intelligence/        # Market and competitive intel
```

## Key Files

- **[[models/business-model-canvas|Business Model Canvas]]** - Core business model
- **[[analytics/kpi-dashboard|KPI Dashboard]]** - Key performance indicators
- **[[rules/master-rules-engine|Master Rules Engine]]** - Business logic repository
- **[[strategies/strategic-priorities|Strategic Priorities]]** - Company objectives

## Business Models

### Revenue Model
```yaml
model_type: recurring_revenue
streams:
  - subscription_saas:
      tiers: [starter, professional, enterprise]
      billing: monthly | annual
      mrr_target: $100,000
  - usage_based:
      unit: api_calls
      pricing: tiered_volume
      revenue_target: $25,000/month
  - professional_services:
      type: consulting
      hourly_rate: $200
      utilization_target: 70%
```

### Customer Lifecycle Model
```yaml
stages:
  awareness:
    duration: 0-7 days
    conversion_rate: 5%
    key_metrics: [traffic, leads]

  consideration:
    duration: 7-30 days
    conversion_rate: 20%
    key_metrics: [demo_requests, trial_signups]

  decision:
    duration: 30-60 days
    conversion_rate: 30%
    key_metrics: [proposals, negotiations]

  purchase:
    duration: 60-90 days
    conversion_rate: 70%
    key_metrics: [closed_deals, contract_value]

  retention:
    duration: ongoing
    target_rate: 95%
    key_metrics: [churn, nrr, usage]

  advocacy:
    duration: 12+ months
    target_rate: 30%
    key_metrics: [referrals, reviews, case_studies]
```

## Usage by AI Agents

### Business Rule Evaluation
```python
# Agent evaluates pricing rule
result = agent.evaluate_rule(
    rule="dynamic-pricing",
    context={
        "customer_tier": "enterprise",
        "volume": 1000000,
        "contract_term": "annual"
    }
)
# Returns: {"price_per_unit": 0.08, "discount": 0.15}
```

### KPI Calculation
```python
# Agent calculates business metrics
metrics = agent.calculate_kpis(
    period="2026-02",
    kpis=["mrr", "arr", "churn_rate", "cac", "ltv"]
)
```

### Decision Framework
```python
# Agent applies decision framework
decision = agent.apply_framework(
    framework="customer-acquisition",
    inputs={
        "lead_score": 85,
        "deal_size": 50000,
        "sales_cycle": 45
    }
)
# Returns: {"priority": "high", "recommended_action": "fast_track"}
```

## Naming Conventions

### Files
- **Models**: `BM-NNN-model-name.md`
- **Analytics**: `AN-NNN-analysis-name.md`
- **Rules**: `BR-NNN-rule-name.md`
- **Reports**: `RPT-YYYY-MM-report-name.md`

### Tags
- `#business/<category>` - Business category
- `#model/<type>` - Business model type
- `#kpi/<metric>` - Key performance indicator
- `#rule/<name>` - Business rule
- `#strategic` - Strategic importance
- `#financial` - Financial impact

## Key Performance Indicators (KPIs)

### Revenue Metrics
| KPI | Definition | Target | Current | Trend |
|-----|------------|--------|---------|-------|
| MRR | Monthly Recurring Revenue | $100k | - | - |
| ARR | Annual Recurring Revenue | $1.2M | - | - |
| Growth Rate | Month-over-month growth | 10% | - | - |
| NRR | Net Revenue Retention | 110% | - | - |

### Customer Metrics
| KPI | Definition | Target | Current | Trend |
|-----|------------|--------|---------|-------|
| CAC | Customer Acquisition Cost | $500 | - | - |
| LTV | Customer Lifetime Value | $5,000 | - | - |
| LTV:CAC | Ratio of LTV to CAC | 10:1 | - | - |
| Churn Rate | Monthly customer churn | < 2% | - | - |

### Operational Metrics
| KPI | Definition | Target | Current | Trend |
|-----|------------|--------|---------|-------|
| Conversion Rate | Lead to customer | 3% | - | - |
| Sales Cycle | Days to close | 60 days | - | - |
| CSAT | Customer Satisfaction | > 4.5/5 | - | - |
| NPS | Net Promoter Score | > 50 | - | - |

### Efficiency Metrics
| KPI | Definition | Target | Current | Trend |
|-----|------------|--------|---------|-------|
| Gross Margin | Revenue - COGS | 80% | - | - |
| Burn Rate | Monthly cash burn | $50k | - | - |
| Runway | Months until cash out | 18 mo | - | - |
| Magic Number | Sales efficiency | > 1.0 | - | - |

## Business Rules Engine

### Rule Categories

#### Pricing Rules
```yaml
rule_id: BR-001-volume-discount
type: pricing
conditions:
  - monthly_volume > 100000: discount = 0.10
  - monthly_volume > 500000: discount = 0.20
  - monthly_volume > 1000000: discount = 0.30
override: requires_approval_if_discount > 0.25
```

#### Eligibility Rules
```yaml
rule_id: BR-002-enterprise-tier
type: eligibility
conditions:
  - annual_contract_value >= 50000
  - OR company_size >= 500
  - AND credit_check_passed = true
actions:
  - assign_tier: enterprise
  - assign_account_manager: true
  - enable_features: [sso, api_access, premium_support]
```

#### Automation Rules
```yaml
rule_id: BR-003-auto-renewal
type: automation
conditions:
  - contract_expires_in_days <= 30
  - customer_status = active
  - payment_method_valid = true
  - no_cancellation_request = true
actions:
  - send_renewal_notice: 30_days_before
  - auto_renew: true
  - notify_account_manager: 7_days_before
```

#### Validation Rules
```yaml
rule_id: BR-004-transaction-validation
type: validation
conditions:
  - transaction_amount <= daily_limit
  - customer_kyc_verified = true
  - no_fraud_flags = true
actions:
  - approve: auto
  - log: standard
escalation:
  - if_amount > 10000: require_manual_approval
  - if_fraud_score > 0.7: block_and_investigate
```

## Decision Frameworks

### Strategic Priorities (2026)
1. **Revenue Growth**: Scale MRR to $500k
2. **Market Expansion**: Enter 3 new verticals
3. **Product Innovation**: Launch AI-powered features
4. **Operational Excellence**: 99.9% uptime, < 2% churn
5. **Team Building**: Hire 10 key positions

### Investment Criteria
```yaml
framework: investment-decision
must_have:
  - roi > 25%
  - payback_period < 24 months
  - aligns_with_strategic_priorities
  - technical_feasibility = high

nice_to_have:
  - competitive_advantage
  - scalability
  - customer_requested

decision_matrix:
  high_roi_high_alignment: immediate_approval
  high_roi_low_alignment: further_review
  low_roi_high_alignment: strategic_investment
  low_roi_low_alignment: reject
```

### Customer Segmentation
```yaml
segments:
  enterprise:
    criteria:
      - annual_revenue > 50000
      - employees > 500
    strategy: white_glove_service
    ownership: dedicated_account_manager

  mid_market:
    criteria:
      - annual_revenue: 10000-50000
      - employees: 50-500
    strategy: scaled_support
    ownership: pooled_account_managers

  smb:
    criteria:
      - annual_revenue < 10000
      - employees < 50
    strategy: self_service
    ownership: customer_success_team
```

## Analytics & Reporting

### Standard Reports

#### Monthly Business Review (MBR)
```yaml
report: monthly-business-review
frequency: monthly
recipients: [executives, board]
sections:
  - revenue_performance
  - customer_metrics
  - product_usage
  - operational_efficiency
  - strategic_initiatives
  - risks_and_opportunities
```

#### Weekly Operations Report
```yaml
report: weekly-operations
frequency: weekly
recipients: [operations_team, managers]
sections:
  - key_metrics_snapshot
  - completed_initiatives
  - upcoming_milestones
  - blockers_and_issues
  - resource_allocation
```

#### Daily Dashboard
```yaml
report: daily-dashboard
frequency: daily
recipients: [all_stakeholders]
metrics:
  - mrr
  - active_users
  - new_signups
  - churn_events
  - support_tickets
  - system_health
```

## Forecasting & Projections

### Revenue Forecast Model
```yaml
model: revenue-forecast
methodology: time_series + regression
inputs:
  - historical_mrr: 12 months
  - seasonal_factors: true
  - growth_initiatives: planned
  - market_trends: industry_data
outputs:
  - monthly_forecast: 12 months
  - confidence_interval: 80%
  - scenario_analysis: [conservative, base, optimistic]
```

### Customer Churn Prediction
```yaml
model: churn-prediction
methodology: machine_learning
features:
  - usage_frequency
  - feature_adoption
  - support_tickets
  - payment_issues
  - engagement_score
output:
  - churn_probability: 0-1
  - risk_level: [low, medium, high]
  - recommended_actions: retention_playbook
```

## Maintenance

### Daily
- [ ] Update KPI dashboard
- [ ] Review business alerts
- [ ] Monitor revenue metrics
- [ ] Check forecast accuracy

### Weekly
- [ ] Generate operations report
- [ ] Review business rules effectiveness
- [ ] Analyze customer cohorts
- [ ] Update strategic initiatives

### Monthly
- [ ] Comprehensive business review
- [ ] Financial close and reporting
- [ ] Forecast revision
- [ ] Strategic planning session

### Quarterly
- [ ] Board reporting
- [ ] Strategic review and planning
- [ ] Budget vs. actuals analysis
- [ ] Market analysis update

## Templates

- [[../90-TEMPLATES/business-model|Business Model]]
- [[../90-TEMPLATES/kpi-definition|KPI Definition]]
- [[../90-TEMPLATES/business-rule|Business Rule]]
- [[../90-TEMPLATES/analytics-report|Analytics Report]]

## Integration with Other Sections

- **10-KNOWLEDGE**: Business models inform agent knowledge
- **20-PROCESSES**: Business rules drive workflow decisions
- **30-INTEGRATIONS**: Business data from external systems
- **60-PROMPTS**: Business context in prompts
- **70-LOGS**: Business events tracked
- **80-MEMORY**: Business intelligence stored

## AI Agent Applications

### Intelligent Pricing
Agents use pricing models and rules to:
- Calculate dynamic pricing
- Apply volume discounts
- Negotiate within guardrails
- Optimize for revenue

### Customer Intelligence
Agents analyze customer data to:
- Predict churn risk
- Identify upsell opportunities
- Personalize engagement
- Optimize lifetime value

### Operational Optimization
Agents optimize operations by:
- Resource allocation
- Capacity planning
- Process efficiency
- Cost reduction

### Strategic Insights
Agents provide insights on:
- Market trends
- Competitive positioning
- Growth opportunities
- Risk assessment

---

**Owned by**: Business Intelligence Agent
**Last Review**: 2026-02-16
**Next Review**: 2026-03-16
**Classification**: Confidential
