---
id: {{agent_id}}
name: {{agent_name}}
type: agent-profile
status: active
version: 1.0.0
created: {{YYYY-MM-DD}}
updated: {{YYYY-MM-DD}}
tags: [agent, {{domain}}, {{primary_skill}}]
---

# Agent Profile: {{agent_name}}

*Note: This template defines an AI agent's capabilities, configuration, and operational parameters. Fill all REQUIRED fields and delete instruction notes after completion.*

## Overview

**Agent Name**: {{agent_name}}
**Agent ID**: {{agent_id}}
**Role**: [REQUIRED: Primary role/purpose]
**Domain**: [REQUIRED: Business domain - e.g., customer-service, sales, analytics]
**Status**: [active | development | maintenance | deprecated]

**Description**:
[REQUIRED: 2-3 sentences describing what this agent does and its primary value]

## Capabilities

### Primary Skills
*Note: Skills this agent excels at*

1. [REQUIRED: Primary skill] - [[../10-KNOWLEDGE/skills/skill-name|Skill Definition]]
2. [REQUIRED: Secondary skill] - [[../10-KNOWLEDGE/skills/skill-name|Skill Definition]]
3. [OPTIONAL: Additional skill]

### Secondary Skills
*Note: Supporting capabilities*

- [Skill name]
- [Skill name]

### Limitations
*Note: What this agent cannot or should not do*

- [REQUIRED: Key limitation]
- [Limitation]

## Configuration

### Model Settings
```yaml
model:
  provider: anthropic | openai | custom
  model_id: [e.g., claude-sonnet-4-5]
  temperature: [0.0-1.0]
  max_tokens: [e.g., 4096]
  top_p: [0.0-1.0]
```

### Behavioral Parameters
```yaml
behavior:
  response_style: [formal | casual | professional | technical]
  verbosity: [concise | balanced | detailed]
  creativity: [low | medium | high]
  safety_level: [standard | strict | custom]
```

### Memory Configuration
```yaml
memory:
  enabled: [true | false]
  type: [short_term | long_term | hybrid]
  retention_days: [number]
  storage_limit_gb: [number]
  context_window: [number of previous interactions]
```

## Integrations

### MCP Servers
*Note: Which MCP servers this agent can access*

- [[../../30-INTEGRATIONS/mcp-servers/server-name|Server Name]] - Purpose
- [Server name] - Purpose

### APIs
*Note: External APIs this agent uses*

- [[../../30-INTEGRATIONS/apis/api-name|API Name]] - Use case
- [API name] - Use case

### Tools
*Note: Specific tools available to this agent*

```yaml
tools:
  - name: [tool_name]
    type: [mcp | api | function]
    purpose: [What this tool does]
    permission_level: [read | write | admin]
```

## Workflows

### Primary Workflows
*Note: Main workflows this agent executes*

1. **[[../../20-PROCESSES/workflows/workflow-name|Workflow Name]]**
   - Trigger: [What starts this workflow]
   - Frequency: [How often]
   - HITL Required: [Yes/No]

2. [Additional workflow]

### Decision Authority

| Decision Type | Authority Level | Approval Required |
|---------------|----------------|-------------------|
| [Decision type] | [autonomous | supervised | approval_required] | [Yes/No - Who] |
| Spend < $100 | autonomous | No |
| Spend $100-$1000 | supervised | Yes - Manager |
| Data deletion | approval_required | Yes - Security team |

## Prompts

### System Prompt
*Note: Core instruction that defines agent behavior*

```markdown
[REQUIRED: System prompt that defines agent's role, behavior, and constraints]

Example:
You are a customer service agent for Acme Corp. Your primary goals are:
1. Provide helpful, empathetic support to customers
2. Resolve issues efficiently within established policies
3. Escalate complex situations appropriately
4. Maintain professional, friendly communication

You have access to customer data, product knowledge, and company policies.
Always prioritize customer satisfaction while following company guidelines.
```

### Default Prompts
*Note: Standard prompts this agent uses*

- **Task Execution**: [[../../60-PROMPTS/agents/{{agent_id}}/task-execution|Link]]
- **Error Handling**: [[../../60-PROMPTS/agents/{{agent_id}}/error-handling|Link]]
- **Escalation**: [[../../60-PROMPTS/agents/{{agent_id}}/escalation|Link]]

## Knowledge Base

### Required Knowledge
*Note: Knowledge this agent must have access to*

- [[../../10-KNOWLEDGE/domains/{{domain}}/core-knowledge|Core Domain Knowledge]]
- [[../../10-KNOWLEDGE/domains/{{domain}}/policies|Policies]]
- [Additional knowledge]

### Learning Priorities
*Note: Areas where this agent should continuously learn*

1. [REQUIRED: Primary learning area]
2. [Learning area]

## Performance Metrics

### Success Metrics
*Note: How we measure this agent's performance*

| Metric | Target | Current | Tracking |
|--------|--------|---------|----------|
| [Metric name] | [Target value] | [Current value] | [[../../70-LOGS/agents/{{agent_id}}/metrics|Link]] |
| Task Success Rate | > 95% | - | Daily |
| Response Time | < 2s | - | Real-time |
| User Satisfaction | > 4.5/5 | - | After each interaction |

### Quality Indicators
- [REQUIRED: Key quality indicator]
- [Quality indicator]

## Security & Compliance

### Access Level
```yaml
access:
  data_classification: [public | internal | confidential | restricted]
  permissions:
    read: [List of readable resources]
    write: [List of writable resources]
    delete: [List of deletable resources - typically none]

  restrictions:
    - [REQUIRED: Key restriction]
    - [Additional restriction]
```

### Compliance Requirements
- [REQUIRED: Relevant compliance framework - e.g., GDPR, SOC 2]
- [Compliance requirement]

### Audit Trail
- **Logging Level**: [standard | detailed | comprehensive]
- **Log Retention**: [Days]
- **Log Location**: [[../../70-LOGS/agents/{{agent_id}}/|Agent Logs]]

## HITL (Human-in-the-Loop)

### Approval Gates
*Note: When human approval is required*

| Scenario | Approver | SLA | Escalation |
|----------|----------|-----|------------|
| [REQUIRED: Scenario requiring approval] | [Role/Person] | [Time] | [Who to escalate to] |
| High-value transaction (>$1000) | Finance Manager | 2 hours | CFO |

### Escalation Rules
```yaml
escalations:
  - condition: [REQUIRED: When to escalate]
    to: [Who to escalate to]
    sla: [Response time required]

  - condition: [Escalation trigger]
    to: [Escalation target]
    sla: [SLA]
```

## Operational Details

### Availability
```yaml
schedule:
  operational_hours: [24/7 | business_hours | custom]
  timezone: [Primary timezone]
  maintenance_window: [When maintenance occurs]
```

### Resource Requirements
```yaml
resources:
  cpu: [vCPU count or percentage]
  memory: [GB]
  storage: [GB]
  network: [Bandwidth requirements]
```

### Dependencies
*Note: Other systems/agents this agent depends on*

- [[agent-name|Agent Name]] - Purpose
- [[../../30-INTEGRATIONS/apis/api-name|API Name]] - Purpose

## Monitoring & Alerts

### Health Checks
```yaml
health_checks:
  - name: [Check name]
    frequency: [How often]
    endpoint: [What to check]
    threshold: [When to alert]
```

### Alerts
*Note: When to send alerts and to whom*

| Alert Type | Condition | Recipients | Channel |
|------------|-----------|------------|---------|
| Critical Error | Error rate > 5% | [Team/Person] | [Slack/Email/PagerDuty] |
| Performance Degradation | Response time > 5s | [Team] | [Channel] |

## Version History

### v1.0.0 - {{YYYY-MM-DD}}
- Initial agent profile created
- [Key change or feature]

### [OPTIONAL: Previous versions]
### v0.9.0 - {{YYYY-MM-DD}}
- [Change description]

## Related Documentation

- **Agent Logs**: [[../../70-LOGS/agents/{{agent_id}}/|View Logs]]
- **Agent Memory**: [[../../80-MEMORY/agents/{{agent_id}}/|View Memory]]
- **Performance Dashboard**: [[../../50-BUSINESS/analytics/agents/{{agent_id}}|View Analytics]]
- **Training Materials**: [[../../10-KNOWLEDGE/training/{{agent_id}}|View Training]]

## Contact & Ownership

**Owner**: [REQUIRED: Person/Team responsible]
**Created By**: [Person]
**Maintained By**: [Team/Person]
**Review Frequency**: [Monthly | Quarterly]
**Last Reviewed**: {{YYYY-MM-DD}}
**Next Review**: {{YYYY-MM-DD}}

---

*This profile is maintained in the Personal AI Employee knowledge base.*
*For updates or questions, contact the agent owner listed above.*
