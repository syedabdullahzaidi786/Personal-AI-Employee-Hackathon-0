# Personal AI Employee - Obsidian Vault

## Overview
Production-grade knowledge management system for autonomous AI agents, MCP integrations, and business intelligence.

## Vault Structure

```
obsidian-vault/
├── 00-INDEX/                    # Central navigation and MOCs
├── 10-KNOWLEDGE/                # Domain knowledge and learning
├── 20-PROCESSES/                # Workflows and procedures
├── 30-INTEGRATIONS/             # MCP servers and external systems
├── 40-SECURITY/                 # Access control and compliance
├── 50-BUSINESS/                 # Business logic and intelligence
├── 60-PROMPTS/                  # Prompt library and templates
├── 70-LOGS/                     # Activity logs and traces
├── 80-MEMORY/                   # Long-term agent memory
├── 90-TEMPLATES/                # Markdown templates
└── .obsidian/                   # Obsidian configuration
```

## Quick Start

1. **Navigation**: Start at `00-INDEX/000-HOME.md`
2. **New Agent**: Use template `90-TEMPLATES/agent-profile.md`
3. **New Workflow**: Use template `90-TEMPLATES/process-sop.md`
4. **Daily Operations**: Check `70-LOGS/daily/YYYY-MM-DD.md`

## Naming Conventions

### Files
- **Format**: `NNN-descriptor-name.md`
- **NNN**: 3-digit sequence number (000-999)
- **descriptor**: lowercase-with-hyphens
- **Examples**:
  - `001-customer-analysis-agent.md`
  - `042-email-automation-workflow.md`
  - `101-stripe-mcp-integration.md`

### Folders
- **Format**: `NN-CATEGORY/`
- **NN**: 2-digit prefix (00-99)
- **CATEGORY**: UPPERCASE-WITH-HYPHENS
- **Examples**:
  - `10-KNOWLEDGE/`
  - `30-INTEGRATIONS/`

### Tags
- `#agent/<name>` - Agent identifier
- `#skill/<name>` - Agent capability
- `#mcp/<server>` - MCP integration
- `#status/<state>` - Operational status
- `#priority/<level>` - Task priority
- `#domain/<area>` - Business domain

## Key Concepts

### Autonomous Agents
Each agent has:
- Profile document in `10-KNOWLEDGE/agents/`
- Memory store in `80-MEMORY/agents/<name>/`
- Execution logs in `70-LOGS/agents/<name>/`
- Custom prompts in `60-PROMPTS/agents/<name>/`

### MCP Integrations
Each integration includes:
- Configuration in `30-INTEGRATIONS/<server>/config.md`
- API documentation in `30-INTEGRATIONS/<server>/api.md`
- Usage examples in `30-INTEGRATIONS/<server>/examples.md`

### Human-in-the-Loop
Workflow checkpoints defined in:
- `20-PROCESSES/hitl/approval-gates.md`
- `20-PROCESSES/hitl/escalation-rules.md`
- `20-PROCESSES/hitl/decision-logs.md`

## Maintenance

- **Daily**: Review `70-LOGS/daily/` for anomalies
- **Weekly**: Update `80-MEMORY/weekly-review.md`
- **Monthly**: Audit `40-SECURITY/access-log.md`
- **Quarterly**: Refactor knowledge graphs in `10-KNOWLEDGE/graphs/`

## Version
v1.0.0 - Initial production release

---
*Last Updated: 2026-02-16*
*Maintained by: Personal AI Employee*
