# Naming Conventions & Guidelines

**Version**: 1.0.0
**Last Updated**: 2026-02-16
**Status**: Active

---

## Overview

This document defines the naming conventions, tagging standards, and organizational guidelines for the Personal AI Employee Obsidian Vault. Consistent naming enables AI agents to efficiently navigate, search, and maintain the knowledge base.

## Core Principles

1. **Predictability**: Names should clearly indicate content and location
2. **Consistency**: Follow established patterns across all sections
3. **Searchability**: Names should contain relevant keywords
4. **Scalability**: Conventions should work at any vault size
5. **Machine-Readable**: Easy for AI agents to parse and understand
6. **Human-Friendly**: Clear and intuitive for human users

---

## Folder Naming

### Format
```
NN-CATEGORY-NAME/
```

### Rules
- **NN**: Two-digit prefix (00-99) for sorting
- **CATEGORY**: UPPERCASE with hyphens for multi-word
- Use descriptive, plural nouns
- No special characters except hyphens
- Maximum 25 characters (excluding prefix)

### Examples
✅ Good:
- `10-KNOWLEDGE/`
- `30-INTEGRATIONS/`
- `50-BUSINESS/`

❌ Bad:
- `knowledge/` (no prefix, lowercase)
- `10_KNOWLEDGE/` (underscore instead of hyphen)
- `10-Know/` (abbreviation, not descriptive)

### Hierarchy
```
NN-CATEGORY/              # Top level (00-99)
  ├── subcategory/        # No prefix, lowercase
  │   └── detail/         # No prefix, lowercase
  └── topic/
```

---

## File Naming

### General Files
```
NNN-descriptor-name.md
```

### Rules
- **NNN**: Three-digit sequence number (000-999)
- **descriptor**: lowercase-with-hyphens
- Use descriptive, specific names
- Include type/category when helpful
- Maximum 50 characters total
- Always use `.md` extension

### Examples
✅ Good:
- `001-customer-service-agent.md`
- `042-email-automation-workflow.md`
- `101-stripe-payment-integration.md`

❌ Bad:
- `customer.md` (no number, not specific)
- `001_Customer_Agent.md` (underscores, caps)
- `1-csa.md` (abbreviation, not descriptive)

### Special File Types

#### Process SOPs
```
SOP-NNN-procedure-name.md
```
Example: `SOP-001-refund-processing.md`

#### Workflows
```
WF-NNN-workflow-name.md
```
Example: `WF-042-customer-onboarding.md`

#### Business Rules
```
BR-NNN-rule-name.md
```
Example: `BR-015-volume-discount-pricing.md`

#### MCP Integrations
```
MCP-NNN-server-name.md
```
Example: `MCP-001-github-integration.md`

#### API Integrations
```
API-NNN-service-name.md
```
Example: `API-023-stripe-payments.md`

#### Templates
```
template-name.md
```
Example: `agent-profile.md` (no number for templates)

#### Prompts
```
TPL-NNN-prompt-name.md
```
Example: `TPL-001-customer-support-response.md`

#### Logs
```
YYYY-MM-DD.md               # Daily logs
AGENT-NAME-YYYY-MM-DD.md    # Agent logs
ERROR-YYYYMMDD-HHMMSS-type.md  # Error logs
```

#### Memory Entries
```
EP-YYYYMMDD-event-description.md  # Episodic
SM-NNN-concept-name.md             # Semantic
PR-NNN-skill-name.md               # Procedural
CTX-entity-type-entity-id.md       # Context
```

---

## Naming by Section

### 00-INDEX
```
NNN-name.md
000-HOME.md                  # Main entry point
001-agent-directory.md
002-integration-dashboard.md
```

### 10-KNOWLEDGE
```
NNN-topic-name.md
001-customer-segmentation.md
023-pricing-strategies.md
045-compliance-requirements.md
```

### 20-PROCESSES
```
WF-NNN-workflow-name.md      # Workflows
SOP-NNN-procedure-name.md    # SOPs
HITL-NNN-gate-name.md        # HITL gates
PB-NNN-playbook-name.md      # Playbooks
```

### 30-INTEGRATIONS
```
MCP-NNN-server-name.md       # MCP servers
API-NNN-service-name.md      # APIs
WH-NNN-webhook-handler.md    # Webhooks
CONFIG-server-name.yaml      # Configurations
```

### 40-SECURITY
```
POL-NNN-policy-name.md       # Policies
ROLE-NNN-role-name.md        # Roles
AUDIT-YYYY-MM-DD-type.md     # Audit logs
COMP-framework-topic.md      # Compliance
```

### 50-BUSINESS
```
BM-NNN-model-name.md         # Business models
AN-NNN-analysis-name.md      # Analytics
BR-NNN-rule-name.md          # Business rules
RPT-YYYY-MM-report-name.md   # Reports
```

### 60-PROMPTS
```
TPL-NNN-template-name.md     # Prompt templates
CHN-NNN-chain-name.md        # Prompt chains
EX-NNN-example-name.md       # Examples
EVAL-YYYY-MM-DD-prompt-id.md # Evaluations
```

### 70-LOGS
```
YYYY-MM-DD.md                # Daily logs
AGENT-NAME-YYYY-MM-DD.md     # Agent logs
ERROR-YYYYMMDD-HHMMSS.md     # Error logs
WF-workflow-id-exec-id.md    # Workflow logs
```

### 80-MEMORY
```
EP-YYYYMMDD-event.md         # Episodic memory
SM-NNN-concept.md            # Semantic memory
PR-NNN-procedure.md          # Procedural memory
CTX-type-id.md               # Context
```

### 90-TEMPLATES
```
template-name.md             # No number prefix
agent-profile.md
process-sop.md
mcp-integration.md
```

---

## Tagging System

### Tag Format
```
#category/subcategory
```

### Rules
- Use lowercase
- Use hyphens for multi-word tags
- Hierarchical structure with forward slashes
- Maximum 3 levels deep
- Be specific but not overly granular

### Standard Tag Categories

#### Agent Tags
```
#agent/<agent-name>
#agent/customer-service
#agent/sales
#agent/analytics
```

#### Skill Tags
```
#skill/<skill-name>
#skill/customer-support
#skill/data-analysis
#skill/report-generation
```

#### Domain Tags
```
#domain/<area>
#domain/customer
#domain/finance
#domain/operations
```

#### Knowledge Tags
```
#knowledge/<category>
#knowledge/product
#knowledge/policy
#knowledge/technical
```

#### Process Tags
```
#process/<type>
#process/workflow
#process/sop
#process/automation
```

#### Integration Tags
```
#mcp/<server>
#api/<service>
#integration/<type>
```

#### Status Tags
```
#status/<state>
#status/active
#status/deprecated
#status/draft
#status/review
```

#### Priority Tags
```
#priority/<level>
#priority/critical
#priority/high
#priority/medium
#priority/low
```

#### Classification Tags
```
#classification/<level>
#classification/public
#classification/internal
#classification/confidential
#classification/restricted
```

#### Compliance Tags
```
#compliance/<framework>
#compliance/gdpr
#compliance/soc2
#compliance/hipaa
```

#### Memory Tags
```
#memory/<type>
#memory/episodic
#memory/semantic
#memory/procedural
```

### Tag Examples

#### Multi-Tag Document
```yaml
---
tags:
  - agent/customer-service
  - skill/ticket-resolution
  - domain/customer
  - status/active
  - priority/high
---
```

---

## ID Systems

### Agent IDs
```
Format: lowercase-with-hyphens
Examples:
  - customer-service-agent
  - sales-automation-agent
  - data-analytics-agent
```

### Workflow IDs
```
Format: WF-NNN
Examples:
  - WF-001 (Customer onboarding)
  - WF-042 (Payment processing)
  - WF-089 (Report generation)
```

### Customer/Entity IDs
```
Format: PREFIX-NNNNN
Examples:
  - CUST-12345 (Customer)
  - PROJ-67890 (Project)
  - CONT-11111 (Contract)
```

### Execution IDs
```
Format: EXEC-NNN
Examples:
  - EXEC-001 (Workflow execution instance)
  - EXEC-456 (Process run)
```

### Correlation IDs
```
Format: UUID v4
Example: 7c8a9f2e-4d1b-4e6f-9c3d-5a7b8e9f0a1b
Use: Track related events across systems
```

---

## Cross-Referencing

### Internal Links
```markdown
[[relative/path/to/file|Display Text]]
[[file-name|Display Text]]
[[#heading|Section Link]]
```

### Examples
```markdown
See [[../10-KNOWLEDGE/agents/001-customer-agent|Customer Agent Profile]]
Reference [[policy-name|Security Policy]]
Jump to [[#prerequisites|Prerequisites section]]
```

### Best Practices
- Use descriptive link text
- Prefer relative paths for portability
- Link to specific sections when possible
- Avoid broken links (verify periodically)

---

## Version Numbering

### Semantic Versioning
```
MAJOR.MINOR.PATCH
```

- **MAJOR**: Breaking changes, incompatible updates
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, small corrections

### Examples
```
1.0.0 → Initial release
1.1.0 → Added new features
1.1.1 → Fixed bugs
2.0.0 → Major rewrite (breaking changes)
```

### Document Versions
```yaml
---
version: 1.2.3
---
```

---

## Date Formats

### Standard Format
```
YYYY-MM-DD (ISO 8601)
```

### Examples
```
2026-02-16 ✅
02/16/2026 ❌
16-02-2026 ❌
2026.02.16 ❌
```

### Timestamps
```
YYYY-MM-DDTHH:MM:SS.sssZ
2026-02-16T23:30:45.123Z ✅
```

---

## YAML Front Matter

### Standard Structure
```yaml
---
id: unique-identifier
name: Human Readable Name
type: document-type
status: active | draft | deprecated
version: 1.0.0
created: 2026-02-16
updated: 2026-02-16
owner: Person/Team Name
tags: [tag1, tag2, tag3]
---
```

### Required Fields (Minimum)
```yaml
---
id: document-id
name: Document Name
type: document-type
tags: [relevant-tags]
---
```

### Optional Common Fields
```yaml
author: Author Name
category: Category
priority: high | medium | low
classification: public | internal | confidential
compliance: [gdpr, soc2, hipaa]
related: [link1, link2]
```

---

## README Files

### Structure
Every major folder should have `README.md`:

```markdown
# NN-SECTION-NAME: Description

## Purpose
[What this section contains]

## Structure
[Folder organization]

## Key Files
[Important documents]

## Usage by AI Agents
[How agents interact]

## Naming Conventions
[Section-specific rules]

## Maintenance
[Update schedule]

## Templates
[Available templates]

## Integration
[Links to related sections]
```

---

## Best Practices

### DO ✅
- Follow naming conventions consistently
- Use descriptive, searchable names
- Include proper metadata in front matter
- Tag documents appropriately
- Keep names concise but clear
- Use standard date formats (ISO 8601)
- Link related documents
- Update modification dates
- Include version numbers
- Write clear README files

### DON'T ❌
- Use spaces in file/folder names
- Use special characters (except hyphens)
- Create overly long names (>50 chars)
- Use abbreviations unless standard
- Mix naming styles in same section
- Create duplicate IDs
- Leave front matter incomplete
- Use inconsistent tag formats
- Break existing naming patterns
- Forget to update version history

---

## Validation Checklist

### New Document
- [ ] Follows naming convention for section
- [ ] Includes complete front matter
- [ ] Has appropriate tags
- [ ] Uses correct date format
- [ ] Links to related documents
- [ ] Follows template structure (if applicable)
- [ ] Has unique ID
- [ ] Includes version number

### Updated Document
- [ ] Updated date changed
- [ ] Version number incremented
- [ ] Version history updated
- [ ] Changes documented
- [ ] Links still valid
- [ ] Tags still relevant

---

## Tools & Automation

### Obsidian Plugins (Recommended)
- **Templater**: Advanced template features
- **Dataview**: Query and organize notes
- **Tag Wrangler**: Manage tags
- **Obsidian Linter**: Enforce formatting
- **Various Complements**: Auto-complete

### Validation Scripts
Location: `.obsidian/scripts/validation/`

- `check-naming.js` - Validate file names
- `check-tags.js` - Validate tag format
- `check-links.js` - Find broken links
- `check-metadata.js` - Validate front matter

---

## Common Patterns

### Agent Documentation Set
```
10-KNOWLEDGE/agents/
  ├── 001-customer-service-agent.md (Profile)
60-PROMPTS/agents/customer-service/
  ├── TPL-001-ticket-response.md
  └── TPL-002-escalation.md
70-LOGS/agents/customer-service/
  └── 2026-02-16.md
80-MEMORY/agents/customer-service/
  ├── EP-20260216-interaction.md
  └── SM-001-procedures.md
```

### Workflow Documentation Set
```
20-PROCESSES/workflows/
  └── WF-001-customer-onboarding.md (Definition)
70-LOGS/workflows/
  └── WF-001-EXEC-123.md (Execution log)
80-MEMORY/context/
  └── CTX-workflow-WF-001.md (Learnings)
```

### Integration Documentation Set
```
30-INTEGRATIONS/mcp-servers/
  ├── MCP-001-github.md (Main doc)
  └── CONFIG-github.yaml (Config)
30-INTEGRATIONS/mcp-servers/github/
  ├── api.md (API docs)
  └── examples.md (Usage examples)
```

---

## Maintenance

### Weekly
- [ ] Check for naming violations
- [ ] Validate new tags
- [ ] Update indexes
- [ ] Fix broken links

### Monthly
- [ ] Comprehensive naming audit
- [ ] Update this document if patterns change
- [ ] Review tag taxonomy
- [ ] Archive deprecated content

### Quarterly
- [ ] Refactor if needed
- [ ] Update automation scripts
- [ ] Training on conventions
- [ ] Document improvements

---

## Questions & Support

### For Naming Questions
1. Check this document first
2. Search for similar examples in vault
3. Check section-specific README
4. Consult vault maintainer
5. Propose new convention if needed

### Proposing Changes
1. Document the need
2. Show examples of current issue
3. Propose specific solution
4. Consider backward compatibility
5. Update this document
6. Communicate to all users

---

**Document Owner**: Vault Administrator
**Last Review**: 2026-02-16
**Next Review**: 2026-03-16
**Version**: 1.0.0

*This is a living document. Suggest improvements as patterns emerge.*
