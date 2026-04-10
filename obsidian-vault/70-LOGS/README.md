# 70-LOGS: Activity Logs & Traces

## Purpose
Comprehensive logging system for tracking all agent activities, system events, integrations, errors, and operational metrics for debugging, auditing, and optimization.

## Structure

```
70-LOGS/
├── daily/               # Daily activity logs
│   └── YYYY-MM-DD.md    # Date-based logs
├── agents/              # Agent-specific logs
│   ├── customer-service/
│   ├── sales/
│   └── analytics/
├── integrations/        # Integration call logs
│   ├── mcp-servers/
│   ├── apis/
│   └── webhooks/
├── workflows/           # Workflow execution logs
│   ├── success/
│   ├── failed/
│   └── pending/
├── errors/              # Error logs and stack traces
│   ├── critical/
│   ├── warnings/
│   └── info/
├── performance/         # Performance metrics
│   ├── latency/
│   ├── throughput/
│   └── resource-usage/
├── alerts/              # System alerts
│   ├── active/
│   ├── resolved/
│   └── historical/
└── audit/               # Audit trails
    ├── security/
    ├── compliance/
    └── changes/
```

## Key Files

- **[[daily/2026-02-16|Today's Activity Log]]** - Current day operations
- **[[agents/activity-summary|Agent Activity Summary]]** - Agent performance overview
- **[[errors/error-dashboard|Error Dashboard]]** - Error tracking and analysis
- **[[performance/metrics-dashboard|Performance Dashboard]]** - System metrics

## Log Levels

| Level | Icon | Purpose | Retention |
|-------|------|---------|-----------|
| DEBUG | 🔍 | Detailed diagnostic information | 7 days |
| INFO | ℹ️ | General informational messages | 30 days |
| WARN | ⚠️ | Warning messages for potential issues | 90 days |
| ERROR | ❌ | Error events that need attention | 180 days |
| CRITICAL | 🚨 | Critical failures requiring immediate action | 365 days |

## Usage by AI Agents

### Writing Logs
```python
# Agent writes structured log entry
agent.log(
    level="INFO",
    category="workflow",
    action="customer_onboarding",
    context={
        "customer_id": "CUST-12345",
        "workflow_id": "WF-789",
        "status": "completed",
        "duration_ms": 2340,
        "steps_completed": 8
    }
)
```

### Querying Logs
```python
# Agent queries logs for analysis
results = agent.query_logs(
    time_range="last_24_hours",
    filters={
        "agent_id": "customer-service-agent",
        "level": ["ERROR", "CRITICAL"],
        "category": "integration"
    }
)
```

### Error Tracking
```python
# Agent logs error with context
agent.log_error(
    error_type="APIConnectionError",
    error_message="Failed to connect to Stripe API",
    stack_trace=traceback,
    context={
        "integration": "stripe",
        "endpoint": "/v1/customers",
        "retry_count": 3,
        "last_attempt": "2026-02-16T23:30:00Z"
    }
)
```

## Naming Conventions

### Files
- **Daily Logs**: `YYYY-MM-DD.md`
- **Agent Logs**: `AGENT-NAME-YYYY-MM-DD.md`
- **Error Logs**: `ERROR-YYYYMMDD-HHMMSS-error-type.md`
- **Workflow Logs**: `WF-workflow-id-execution-id.md`

### Tags
- `#log/<level>` - Log level
- `#agent/<name>` - Agent identifier
- `#category/<type>` - Log category
- `#integration/<name>` - Integration name
- `#workflow/<id>` - Workflow identifier
- `#incident/<id>` - Incident reference

## Log Entry Structure

### Standard Log Format
```yaml
---
timestamp: 2026-02-16T23:30:45.123Z
level: INFO
category: workflow
agent_id: customer-service-agent
correlation_id: 7c8a9f2e-4d1b-4e6f-9c3d-5a7b8e9f0a1b
---

# Log Entry

## Event
Workflow execution completed successfully

## Context
- Workflow: customer-onboarding
- Customer ID: CUST-12345
- Execution ID: EXEC-789
- Started: 2026-02-16T23:28:03.000Z
- Duration: 2.34 seconds

## Details
Completed all 8 steps of customer onboarding workflow:
1. ✅ Validate customer data (0.15s)
2. ✅ Create CRM record (0.42s)
3. ✅ Send welcome email (0.38s)
4. ✅ Generate API credentials (0.21s)
5. ✅ Assign account manager (0.18s)
6. ✅ Schedule onboarding call (0.29s)
7. ✅ Update billing system (0.35s)
8. ✅ Log completion event (0.12s)

## Metrics
- Total steps: 8
- Success rate: 100%
- Average step duration: 0.29s
- API calls: 12
- Database queries: 6

## Related Logs
- [[workflows/customer/onboarding/EXEC-789|Full Execution Log]]
- [[agents/customer-service/2026-02-16#EXEC-789|Agent Activity]]
```

## Daily Log Template

```markdown
---
date: 2026-02-16
day_of_week: Sunday
status: 🟢 Operational
---

# Daily Activity Log - 2026-02-16

## Summary
- **Total Events**: 1,247
- **Agents Active**: 8
- **Workflows Executed**: 53
- **Errors**: 3 (2 resolved, 1 investigating)
- **API Calls**: 8,456
- **Uptime**: 99.99%

## Key Metrics
| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Response Time | 1.2s | < 2s | 🟢 |
| Success Rate | 98.7% | > 98% | 🟢 |
| Error Rate | 0.24% | < 1% | 🟢 |
| CPU Usage | 42% | < 80% | 🟢 |
| Memory Usage | 68% | < 85% | 🟢 |

## Agent Activity

### Customer Service Agent
- Sessions: 127
- Tickets Resolved: 94
- Avg Response Time: 1.8s
- CSAT: 4.6/5
- Status: 🟢 Healthy

### Sales Agent
- Leads Processed: 43
- Meetings Scheduled: 12
- Proposals Sent: 5
- Conversion Rate: 28%
- Status: 🟢 Healthy

### Analytics Agent
- Reports Generated: 8
- Data Points Analyzed: 145,234
- Insights Generated: 23
- Recommendations: 7
- Status: 🟢 Healthy

## Workflows

### Completed (53)
- customer-onboarding: 8 executions
- payment-processing: 31 executions
- report-generation: 14 executions

### Failed (2)
- [[workflows/failed/WF-EMAIL-423|Email delivery failure]] (resolved)
- [[workflows/failed/WF-INTEGRATION-891|API timeout]] (resolved)

### Pending (1)
- [[workflows/pending/WF-APPROVAL-234|High-value contract approval]]

## Integration Activity

### API Calls by Service
| Service | Calls | Success | Errors | Avg Latency |
|---------|-------|---------|--------|-------------|
| Stripe | 2,341 | 2,339 | 2 | 245ms |
| SendGrid | 187 | 187 | 0 | 123ms |
| GitHub | 456 | 455 | 1 | 389ms |
| PostgreSQL | 5,472 | 5,472 | 0 | 12ms |

### Rate Limit Status
- Stripe: 28% utilization
- SendGrid: 0.5% utilization
- GitHub: 9% utilization

## Errors & Incidents

### ERROR-001: Stripe API Timeout
- **Time**: 14:23:45
- **Agent**: payment-processing-agent
- **Resolution**: Automatic retry successful
- **Status**: ✅ Resolved

### ERROR-002: Email Delivery Failure
- **Time**: 18:15:32
- **Agent**: customer-service-agent
- **Resolution**: Switched to backup SMTP
- **Status**: ✅ Resolved

### ERROR-003: Database Connection Slowdown
- **Time**: 22:47:19
- **Agent**: analytics-agent
- **Resolution**: 🔍 Investigating
- **Status**: ⚠️ Monitoring

## Security Events
- Failed login attempts: 0
- Unauthorized access attempts: 0
- Suspicious activity: 0
- Status: 🟢 Secure

## Performance Insights
- Peak traffic: 14:00-16:00 (324 req/min)
- Slowest endpoint: /api/v1/analytics/report (3.2s avg)
- Most called endpoint: /api/v1/customers (2,341 calls)
- Cache hit rate: 87%

## Action Items
- [ ] Investigate database slowdown (ERROR-003)
- [ ] Optimize analytics report endpoint
- [ ] Review peak traffic capacity planning

## Notes
- Successfully handled 2.3x normal load during marketing campaign
- All systems performed within SLA
- No security incidents

---
**Generated by**: System Logger
**Last Updated**: 2026-02-16 23:59:59
```

## Error Log Structure

```markdown
---
error_id: ERROR-20260216-233045-stripe-timeout
timestamp: 2026-02-16T23:30:45.123Z
severity: ERROR
category: integration
status: resolved
---

# Error: Stripe API Connection Timeout

## Overview
- **Error Type**: APIConnectionError
- **Integration**: Stripe Payment API
- **Endpoint**: /v1/customers
- **Agent**: payment-processing-agent
- **Workflow**: payment-capture (WF-789)

## Timeline
- **First Occurrence**: 2026-02-16T23:30:45.123Z
- **Last Occurrence**: 2026-02-16T23:30:47.456Z
- **Occurrence Count**: 1
- **Resolution Time**: 2.3 seconds

## Error Details
```
APIConnectionError: Connection timeout after 10000ms
  at StripeClient.request (stripe-client.js:234)
  at PaymentProcessor.capturePayment (payment-processor.js:89)
  at WorkflowExecutor.executeStep (workflow.js:156)
```

## Context
```json
{
  "customer_id": "CUST-12345",
  "payment_intent": "pi_abc123",
  "amount": 4999,
  "currency": "usd",
  "retry_count": 1,
  "timeout_ms": 10000
}
```

## Root Cause
Temporary network latency spike to Stripe infrastructure

## Resolution
- **Action**: Automatic retry with exponential backoff
- **Retry Attempt**: 2
- **Success**: ✅ Yes
- **Total Time**: 2.3s

## Impact
- **Affected Workflows**: 1
- **Affected Customers**: 1
- **Revenue Impact**: $0 (recovered)
- **User Experience**: Minimal (within SLA)

## Prevention
- Circuit breaker prevented cascade
- Retry strategy successful
- No code changes required

## Related Logs
- [[integrations/stripe/2026-02-16#233045|Stripe API Log]]
- [[workflows/payment-processing/WF-789|Workflow Execution]]
- [[agents/payment-processor/2026-02-16#233045|Agent Activity]]

## Follow-up Actions
- [x] Monitor Stripe API for continued issues
- [ ] Review timeout configuration
- [ ] Update alerting thresholds
```

## Performance Log Structure

```markdown
---
date: 2026-02-16
metric_type: latency
aggregation: hourly
---

# Performance Metrics - Latency (Hourly)

## Summary
- **Period**: 2026-02-16 00:00 - 23:59
- **Total Requests**: 145,234
- **Avg Latency**: 1.2s
- **P50**: 0.8s
- **P95**: 2.1s
- **P99**: 3.4s

## Latency by Hour

| Hour | Requests | Avg | P50 | P95 | P99 | Status |
|------|----------|-----|-----|-----|-----|--------|
| 00:00 | 2,341 | 0.9s | 0.7s | 1.5s | 2.1s | 🟢 |
| 01:00 | 1,987 | 0.8s | 0.6s | 1.4s | 1.9s | 🟢 |
| 02:00 | 1,456 | 0.8s | 0.6s | 1.3s | 1.8s | 🟢 |
| ... | ... | ... | ... | ... | ... | ... |
| 14:00 | 9,234 | 1.8s | 1.2s | 3.1s | 4.2s | ⚠️ |
| 15:00 | 8,765 | 1.7s | 1.1s | 2.9s | 4.0s | ⚠️ |
| ... | ... | ... | ... | ... | ... | ... |
| 23:00 | 3,124 | 1.0s | 0.8s | 1.7s | 2.3s | 🟢 |

## Latency by Endpoint

| Endpoint | Requests | Avg Latency | P95 | Trend |
|----------|----------|-------------|-----|-------|
| /api/v1/customers | 45,234 | 0.8s | 1.5s | → |
| /api/v1/analytics/report | 1,234 | 3.2s | 5.1s | ↑ |
| /api/v1/workflows/execute | 8,765 | 1.5s | 2.8s | → |
| /api/v1/integrations/call | 12,456 | 1.1s | 2.2s | ↓ |

## Insights
- Peak traffic period (14:00-16:00) shows elevated latency
- Analytics endpoint needs optimization (3.2s avg)
- Overall performance within SLA (< 2s avg)

## Recommendations
- [ ] Optimize analytics report query
- [ ] Consider caching for customer endpoint
- [ ] Review peak traffic capacity
```

## Maintenance

### Daily
- [ ] Review daily activity log
- [ ] Investigate critical/error level logs
- [ ] Monitor performance trends
- [ ] Clear debug logs older than 7 days

### Weekly
- [ ] Analyze error patterns
- [ ] Generate weekly summary report
- [ ] Review log storage utilization
- [ ] Optimize slow queries/endpoints

### Monthly
- [ ] Comprehensive log analysis
- [ ] Update log retention policies
- [ ] Archive old logs
- [ ] Performance optimization review

## Templates

- [[../90-TEMPLATES/log-entry|Standard Log Entry]]
- [[../90-TEMPLATES/error-report|Error Report]]
- [[../90-TEMPLATES/daily-summary|Daily Summary]]

## Integration with Other Sections

- **10-KNOWLEDGE**: Logs inform knowledge updates
- **20-PROCESSES**: Process execution logged
- **30-INTEGRATIONS**: Integration calls logged
- **40-SECURITY**: Security events logged
- **50-BUSINESS**: Business events logged
- **60-PROMPTS**: Prompt executions logged
- **80-MEMORY**: Logs feed long-term memory

## Log Analysis & Insights

### Common Queries

```python
# Find all errors in last 24 hours
agent.query_logs(
    time_range="last_24_hours",
    level=["ERROR", "CRITICAL"]
)

# Analyze agent performance
agent.analyze_logs(
    agent_id="customer-service-agent",
    metrics=["response_time", "success_rate", "csat"],
    time_range="last_7_days"
)

# Track workflow success rate
agent.query_logs(
    category="workflow",
    workflow_id="customer-onboarding",
    time_range="last_30_days",
    aggregate="success_rate"
)
```

---

**Owned by**: Logging & Monitoring Agent
**Last Review**: 2026-02-16
**Next Review**: 2026-03-16
**Retention Policy**: See [[audit/retention-policy|Retention Policy]]
