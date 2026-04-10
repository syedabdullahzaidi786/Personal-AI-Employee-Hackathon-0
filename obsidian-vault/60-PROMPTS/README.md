# 60-PROMPTS: Prompt Library & Templates

## Purpose
Centralized repository of prompt templates, chains, and optimization strategies for AI agent interactions across all operational scenarios.

## Structure

```
60-PROMPTS/
├── templates/           # Reusable prompt templates
│   ├── system/          # System-level prompts
│   ├── task/            # Task-specific prompts
│   ├── analysis/        # Analysis prompts
│   └── generation/      # Content generation
├── chains/              # Multi-step prompt chains
│   ├── research/        # Research workflows
│   ├── decision/        # Decision-making chains
│   └── execution/       # Execution chains
├── agents/              # Agent-specific prompts
│   ├── customer-service/
│   ├── sales/
│   ├── operations/
│   └── analytics/
├── optimization/        # Prompt engineering best practices
├── examples/            # Successful prompt examples
└── evaluation/          # Prompt performance metrics
```

## Key Files

- **[[templates/master-template-library|Master Template Library]]** - All prompt templates
- **[[chains/chain-catalog|Chain Catalog]]** - Multi-step prompt sequences
- **[[optimization/prompt-engineering-guide|Prompt Engineering Guide]]** - Best practices
- **[[evaluation/performance-metrics|Performance Metrics]]** - Effectiveness tracking

## Prompt Engineering Principles

### Core Principles
1. **Clarity**: Explicit, unambiguous instructions
2. **Context**: Sufficient background information
3. **Constraints**: Clear boundaries and limitations
4. **Output Format**: Specific structure requirements
5. **Examples**: Few-shot learning where appropriate
6. **Verification**: Built-in validation criteria

### Optimization Strategies
- **Chain-of-Thought**: Step-by-step reasoning
- **Self-Consistency**: Multiple reasoning paths
- **Tree-of-Thoughts**: Parallel exploration
- **Iterative Refinement**: Progressive improvement
- **Meta-Prompting**: Prompts about prompts

## Usage by AI Agents

### Template Loading
```python
# Agent loads prompt template
prompt = agent.load_template(
    category="customer-service",
    template="ticket-response",
    variables={
        "customer_name": "John Doe",
        "issue": "billing error",
        "priority": "high"
    }
)
```

### Chain Execution
```python
# Agent executes prompt chain
result = agent.execute_chain(
    chain="customer-analysis",
    steps=[
        "data_collection",
        "sentiment_analysis",
        "recommendation_generation",
        "action_planning"
    ],
    context=customer_data
)
```

### Dynamic Prompt Generation
```python
# Agent generates context-aware prompt
prompt = agent.generate_prompt(
    task="sales_outreach",
    context={
        "prospect_industry": "fintech",
        "company_size": "mid-market",
        "pain_points": ["manual_processes", "scalability"]
    }
)
```

## Naming Conventions

### Files
- **Templates**: `TPL-NNN-template-name.md`
- **Chains**: `CHN-NNN-chain-name.md`
- **Examples**: `EX-NNN-example-name.md`
- **Evaluations**: `EVAL-YYYY-MM-DD-prompt-id.md`

### Tags
- `#prompt/<category>` - Prompt category
- `#agent/<name>` - Target agent
- `#task/<type>` - Task type
- `#chain` - Part of a chain
- `#tested` - Performance validated
- `#version/<n>` - Version number

## Prompt Template Structure

### Standard Template Format
```yaml
---
id: TPL-001
name: Customer Support Response
category: customer-service
version: 2.1.0
last_updated: 2026-02-16
performance_score: 0.92
tags: [customer-service, support, response]
---

# Template: Customer Support Response

## Purpose
Generate empathetic, accurate, and actionable responses to customer support tickets.

## Input Variables
- {{customer_name}}: Customer's name
- {{ticket_id}}: Support ticket number
- {{issue_category}}: Type of issue
- {{issue_description}}: Detailed description
- {{customer_history}}: Past interactions
- {{priority}}: Ticket priority level

## System Prompt
You are a customer support agent for [Company Name]. Your goal is to provide helpful, empathetic, and accurate responses that resolve customer issues quickly.

## Task Prompt
Respond to the following customer support ticket:

**Ticket #{{ticket_id}}**
**Customer**: {{customer_name}}
**Category**: {{issue_category}}
**Priority**: {{priority}}

**Issue Description**:
{{issue_description}}

**Customer History**:
{{customer_history}}

**Your Response Should**:
1. Acknowledge the customer's concern with empathy
2. Provide a clear explanation of the issue
3. Offer a specific solution or next steps
4. Set expectations for resolution timeline
5. Offer additional assistance

## Output Format
```
Subject: Re: [Original Subject]

Dear {{customer_name}},

[Empathetic acknowledgment]

[Explanation of issue]

[Proposed solution]

[Timeline and next steps]

[Offer for additional help]

Best regards,
[Agent Name]
Customer Support Team
```

## Validation Criteria
- [ ] Addresses customer by name
- [ ] Acknowledges specific issue
- [ ] Provides actionable solution
- [ ] Sets clear expectations
- [ ] Professional and empathetic tone
- [ ] No technical jargon (unless appropriate)
- [ ] Includes follow-up offer

## Performance Metrics
- CSAT Score: 4.6/5
- Resolution Rate: 87%
- Avg Response Time: 2.3 hours
- Follow-up Required: 13%

## Example Usage
See [[../examples/EX-001-support-response|Example 001]]
```

## Prompt Chains

### Research Chain
```yaml
chain: customer-research
purpose: Comprehensive customer analysis
steps:
  1_data_collection:
    prompt: TPL-050-data-collection
    inputs: [customer_id]
    outputs: [customer_profile, interaction_history, usage_data]

  2_sentiment_analysis:
    prompt: TPL-051-sentiment-analysis
    inputs: [interaction_history]
    outputs: [sentiment_score, key_themes, concerns]

  3_behavior_analysis:
    prompt: TPL-052-behavior-analysis
    inputs: [usage_data]
    outputs: [usage_patterns, feature_adoption, engagement_level]

  4_insight_generation:
    prompt: TPL-053-insight-generation
    inputs: [customer_profile, sentiment_score, usage_patterns]
    outputs: [insights, recommendations, risk_factors]

  5_action_planning:
    prompt: TPL-054-action-planning
    inputs: [insights, recommendations, risk_factors]
    outputs: [action_plan, priority_actions, expected_outcomes]
```

### Decision Chain
```yaml
chain: strategic-decision
purpose: Multi-criteria decision making
steps:
  1_problem_definition:
    prompt: TPL-100-problem-framing
    inputs: [situation_description]
    outputs: [problem_statement, objectives, constraints]

  2_option_generation:
    prompt: TPL-101-option-generation
    inputs: [problem_statement, constraints]
    outputs: [options_list, initial_assessment]

  3_criteria_definition:
    prompt: TPL-102-criteria-definition
    inputs: [objectives]
    outputs: [evaluation_criteria, weights]

  4_option_evaluation:
    prompt: TPL-103-option-evaluation
    inputs: [options_list, evaluation_criteria, weights]
    outputs: [scored_options, trade-off_analysis]

  5_recommendation:
    prompt: TPL-104-recommendation
    inputs: [scored_options, trade-off_analysis]
    outputs: [recommended_option, rationale, implementation_plan]

  6_risk_assessment:
    prompt: TPL-105-risk-assessment
    inputs: [recommended_option, implementation_plan]
    outputs: [risk_register, mitigation_strategies]
```

## Agent-Specific Prompts

### Customer Service Agent
```yaml
agent: customer-service-agent
primary_prompts:
  - TPL-001: Support ticket response
  - TPL-002: Escalation handling
  - TPL-003: Refund request evaluation
  - TPL-004: Product recommendation
  - TPL-005: Follow-up scheduling

secondary_prompts:
  - TPL-010: Complaint resolution
  - TPL-011: Feature request logging
  - TPL-012: Bug report triaging
```

### Sales Agent
```yaml
agent: sales-agent
primary_prompts:
  - TPL-020: Lead qualification
  - TPL-021: Outreach email generation
  - TPL-022: Proposal creation
  - TPL-023: Objection handling
  - TPL-024: Follow-up sequencing

secondary_prompts:
  - TPL-030: Competitive analysis
  - TPL-031: Pricing strategy
  - TPL-032: Deal review
```

### Analytics Agent
```yaml
agent: analytics-agent
primary_prompts:
  - TPL-040: Data analysis
  - TPL-041: Report generation
  - TPL-042: Insight extraction
  - TPL-043: Trend identification
  - TPL-044: Forecast creation

secondary_prompts:
  - TPL-050: Anomaly detection
  - TPL-051: Correlation analysis
  - TPL-052: Root cause analysis
```

## Prompt Optimization

### A/B Testing
```yaml
test_id: AB-001
variants:
  variant_a:
    template: TPL-001-v1
    description: Original template
    sample_size: 100
    performance:
      csat: 4.5
      resolution_rate: 85%
      avg_time: 2.5h

  variant_b:
    template: TPL-001-v2
    description: Added empathy framing
    sample_size: 100
    performance:
      csat: 4.7
      resolution_rate: 89%
      avg_time: 2.2h

winner: variant_b
improvement: +4.4% CSAT, +4.7% resolution
deployed: 2026-02-15
```

### Performance Tracking
```yaml
template: TPL-001
tracking_period: 2026-02-01 to 2026-02-16
metrics:
  usage_count: 487
  success_rate: 92%
  avg_csat: 4.6
  avg_tokens: 523
  avg_latency: 1.8s
  cost_per_execution: $0.03

trends:
  - success_rate: +3% vs previous period
  - csat: stable
  - token_efficiency: +8% (optimized)

recommendations:
  - Continue current version
  - Monitor edge cases
  - Consider adding examples for complex scenarios
```

## Best Practices

### Writing Effective Prompts

#### DO's ✅
- Be specific and explicit
- Provide relevant context
- Define clear output format
- Include validation criteria
- Use examples when helpful
- Version and track changes
- Test and iterate

#### DON'Ts ❌
- Use vague language
- Assume implicit context
- Overload with information
- Mix multiple unrelated tasks
- Skip error handling
- Forget to document
- Deploy without testing

### Prompt Versioning
```
TPL-001-v1.0.0 → Initial version
TPL-001-v1.1.0 → Minor improvements (backward compatible)
TPL-001-v2.0.0 → Major changes (breaking changes)
TPL-001-v2.0.1 → Bug fixes
```

## Maintenance

### Daily
- [ ] Monitor prompt performance
- [ ] Review failed executions
- [ ] Collect feedback
- [ ] Update usage statistics

### Weekly
- [ ] Analyze performance trends
- [ ] Identify optimization opportunities
- [ ] Review new prompt requests
- [ ] Update documentation

### Monthly
- [ ] Comprehensive prompt audit
- [ ] A/B test new variants
- [ ] Archive deprecated prompts
- [ ] Update best practices guide

## Templates

- [[../90-TEMPLATES/prompt-template|Prompt Template]]
- [[../90-TEMPLATES/chain-definition|Chain Definition]]
- [[../90-TEMPLATES/prompt-evaluation|Prompt Evaluation]]

## Integration with Other Sections

- **10-KNOWLEDGE**: Prompts reference knowledge base
- **20-PROCESSES**: Processes use prompt chains
- **30-INTEGRATIONS**: API calls embedded in prompts
- **50-BUSINESS**: Business rules inform prompts
- **70-LOGS**: Prompt executions logged
- **80-MEMORY**: Prompt context from memory

## Advanced Techniques

### Few-Shot Learning
```markdown
# Task: Classify customer sentiment

## Examples:
Input: "I love this product! Best purchase ever!"
Output: Positive (confidence: 0.95)

Input: "The product is okay, nothing special."
Output: Neutral (confidence: 0.78)

Input: "Terrible experience. Would not recommend."
Output: Negative (confidence: 0.92)

## Now classify:
Input: {{customer_feedback}}
Output:
```

### Chain-of-Thought
```markdown
# Task: Evaluate refund request

Let's think through this step by step:

1. Review the purchase details:
   - Product: {{product_name}}
   - Date: {{purchase_date}}
   - Amount: {{amount}}

2. Check refund policy eligibility:
   - Within 30-day window? {{days_since_purchase < 30}}
   - Product condition: {{condition}}
   - Return reason: {{reason}}

3. Assess special circumstances:
   - Customer history: {{customer_tier}}
   - Previous refunds: {{refund_count}}
   - Issue type: {{issue_type}}

4. Make recommendation:
   Based on the analysis above...
```

### Self-Consistency
```markdown
# Task: Recommend pricing tier

Generate 3 independent analyses:

## Analysis 1 (Revenue Focus):
[Consider revenue maximization...]

## Analysis 2 (Customer Value Focus):
[Consider lifetime value...]

## Analysis 3 (Competitive Focus):
[Consider market positioning...]

## Consensus Recommendation:
[Synthesize the three analyses...]
```

---

**Owned by**: Prompt Engineering Agent
**Last Review**: 2026-02-16
**Next Review**: 2026-03-16
**Classification**: Internal
