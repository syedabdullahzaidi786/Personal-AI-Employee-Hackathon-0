# 30-INTEGRATIONS: MCP Servers & External Systems

## Purpose
Configuration, documentation, and management of Model Context Protocol (MCP) servers and external system integrations used by AI agents.

## Structure

```
30-INTEGRATIONS/
├── mcp-servers/         # MCP server configurations
│   ├── filesystem/      # File system operations
│   ├── github/          # GitHub integration
│   ├── database/        # Database connections
│   ├── api-gateway/     # API management
│   └── custom/          # Custom MCP servers
├── apis/                # External API integrations
│   ├── crm/             # CRM systems
│   ├── payment/         # Payment processors
│   ├── communication/   # Email, SMS, chat
│   └── analytics/       # Analytics platforms
├── webhooks/            # Incoming webhook handlers
├── oauth/               # OAuth configurations
├── credentials/         # Credential management (encrypted)
└── monitoring/          # Integration health monitoring
```

## Key Files

- **[[mcp-servers/registry|MCP Server Registry]]** - All configured MCP servers
- **[[apis/api-catalog|API Catalog]]** - External API directory
- **[[webhooks/webhook-routes|Webhook Routes]]** - Inbound webhook mappings
- **[[monitoring/health-dashboard|Health Dashboard]]** - Integration status

## MCP Server Configuration

### Standard MCP Server Template
```yaml
server_name: github-mcp
type: mcp
version: 1.0.0
endpoint: npx -y @modelcontextprotocol/server-github
capabilities:
  - repository_access
  - issue_management
  - pull_request_operations
authentication:
  method: token
  token_env: GITHUB_TOKEN
rate_limits:
  requests_per_minute: 5000
  burst: 100
status: active
owner: integration-agent
documentation: [[mcp-servers/github/README|GitHub MCP Docs]]
```

## Usage by AI Agents

### MCP Server Invocation
```python
# Agent requests GitHub data via MCP
agent.mcp_call(
    server="github-mcp",
    tool="list_repositories",
    params={"org": "company"}
)
```

### API Integration
```python
# Agent calls external API
agent.api_call(
    integration="stripe-api",
    endpoint="/v1/customers",
    method="POST",
    data={"email": "customer@example.com"}
)
```

### Webhook Processing
```python
# Incoming webhook triggers agent workflow
webhook_event = {
    "source": "stripe",
    "event": "payment.succeeded",
    "handler": "20-PROCESSES/workflows/payment/success.md"
}
```

## Naming Conventions

### Files
- **MCP Servers**: `MCP-NNN-server-name.md`
- **APIs**: `API-NNN-service-name.md`
- **Webhooks**: `WH-NNN-event-handler.md`
- **Configs**: `CONFIG-server-name.yaml`

### Tags
- `#mcp/<server>` - MCP server identifier
- `#api/<service>` - External API service
- `#integration/<type>` - Integration category
- `#status/<state>` - Operational status
- `#auth/<method>` - Authentication method
- `#rate-limit` - Has rate limiting

## Integration Status

| Server/API | Type | Status | Uptime | Last Check |
|------------|------|--------|--------|------------|
| GitHub | MCP | 🟢 Active | 99.9% | 2026-02-16 23:30 |
| Stripe | API | 🟢 Active | 99.99% | 2026-02-16 23:29 |
| SendGrid | API | 🟢 Active | 99.8% | 2026-02-16 23:28 |
| PostgreSQL | MCP | 🟢 Active | 100% | 2026-02-16 23:27 |

## Security & Credentials

### Credential Management
- **Storage**: Environment variables + encrypted vault
- **Rotation**: Automated 90-day rotation
- **Audit**: All access logged to `70-LOGS/integrations/access.md`
- **Policies**: See `40-SECURITY/policies/credential-management.md`

### Authentication Methods
- **API Keys**: Short-lived, scoped tokens
- **OAuth 2.0**: Standard authorization flows
- **JWT**: For service-to-service auth
- **mTLS**: For high-security integrations

## Rate Limiting & Quotas

| Integration | Limit | Current Usage | Alert Threshold |
|-------------|-------|---------------|-----------------|
| GitHub API | 5000/hr | 234/hr | 80% (4000/hr) |
| Stripe API | 100/sec | 12/sec | 80% (80/sec) |
| SendGrid | 100k/day | 5.2k/day | 80% (80k/day) |
| OpenAI API | 10k RPM | 450 RPM | 75% (7.5k RPM) |

## Error Handling

### Retry Strategy
```yaml
default_retry_policy:
  max_attempts: 3
  backoff: exponential
  initial_delay: 1s
  max_delay: 30s
  retry_on:
    - connection_timeout
    - rate_limit_exceeded
    - server_error_5xx
  no_retry_on:
    - authentication_error
    - authorization_error
    - bad_request_4xx
```

### Circuit Breaker
```yaml
circuit_breaker:
  failure_threshold: 5
  timeout: 60s
  half_open_requests: 3
  reset_timeout: 300s
```

## Maintenance

### Daily
- [ ] Monitor integration health
- [ ] Review rate limit usage
- [ ] Check error rates
- [ ] Verify credential validity

### Weekly
- [ ] Audit API usage patterns
- [ ] Update documentation
- [ ] Test fallback mechanisms
- [ ] Review webhook handlers

### Monthly
- [ ] Comprehensive security audit
- [ ] Performance optimization
- [ ] Deprecate unused integrations
- [ ] Update MCP server versions

## Templates

- [[../90-TEMPLATES/mcp-integration|MCP Server Integration]]
- [[../90-TEMPLATES/api-integration|API Integration]]
- [[../90-TEMPLATES/webhook-handler|Webhook Handler]]
- [[../90-TEMPLATES/oauth-config|OAuth Configuration]]

## Integration with Other Sections

- **10-KNOWLEDGE**: Integration capabilities inform agent skills
- **20-PROCESSES**: Workflows trigger integration calls
- **40-SECURITY**: Security policies govern access
- **70-LOGS**: All integration calls are logged
- **80-MEMORY**: Integration state stored in memory

## MCP Server Examples

### Filesystem MCP
```yaml
Purpose: Local file operations
Capabilities:
  - read_file
  - write_file
  - list_directory
  - search_files
Use Cases:
  - Document processing
  - Log analysis
  - Configuration management
```

### GitHub MCP
```yaml
Purpose: GitHub repository operations
Capabilities:
  - repository_management
  - issue_tracking
  - pull_request_operations
  - code_search
Use Cases:
  - Automated PR reviews
  - Issue triage
  - Release management
```

### Database MCP
```yaml
Purpose: Database query and management
Capabilities:
  - query_execution
  - schema_inspection
  - data_migration
  - backup_management
Use Cases:
  - Business intelligence
  - Data analysis
  - Automated reporting
```

---

**Owned by**: Integration Management Agent
**Last Review**: 2026-02-16
**Next Review**: 2026-03-16
