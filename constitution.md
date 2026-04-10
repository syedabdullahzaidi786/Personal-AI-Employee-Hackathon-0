# Personal AI Employee System - Constitution

**Version**: 1.0.0 | **Tier**: Bronze (Hackathon 0) | **Ratified**: 2026-02-16

---

## 1. System Purpose

### Mission
Build a **local-first, autonomous Personal AI Employee** that operates transparently with human oversight, maintains persistent memory, and executes real-world actions through controlled integrations.

### Design Philosophy
- **Local-First**: Obsidian vault as source of truth, no cloud dependency
- **Human-in-the-Loop**: AI proposes, human approves high-risk actions
- **Transparent**: All reasoning, decisions, and actions are logged and auditable
- **Persistent**: Ralph Wiggum loop ensures continuous operation and memory
- **Composable**: MCP servers as action primitives, skills as capabilities

### Success Criteria
- **Bronze Tier (Current)**: Core loop running, basic skills, HITL gates functional
- **Silver Tier (Next)**: Multi-agent coordination, advanced integrations, learning loops
- **Gold Tier (Future)**: Fully autonomous for approved domains, predictive intelligence

---

## 2. Core Operating Principles

### I. Local-First Sovereignty
**Rule**: The Obsidian vault is the single source of truth. All state lives in markdown.

**Requirements**:
- Every decision, memory, and artifact must be written to the vault
- No critical state in ephemeral memory or external databases
- Vault structure follows `obsidian-vault/` conventions (see NAMING-CONVENTIONS.md)
- Git tracks all changes for rollback and audit

**Rationale**: Ensures data sovereignty, auditability, and resilience against service failures.

### II. Explicit Over Implicit
**Rule**: AI must declare intent before action. No silent operations.

**Requirements**:
- Log all reasoning to `70-LOGS/` before execution
- Use structured logging (timestamp, agent, action, context)
- Declare assumptions explicitly in decision logs
- No "magic" - every automation must be discoverable

**Rationale**: Builds trust, enables debugging, prevents runaway automation.

### III. Human-in-the-Loop (HITL) by Default
**Rule**: High-risk actions require human approval. Start restrictive, loosen with trust.

**Requirements**:
- All external actions (email, payments, API writes) require approval initially
- Approval gates defined in `20-PROCESSES/hitl/`
- SLA-based escalation if approval not received
- Gradual autonomy: track success rate to reduce gates over time

**Rationale**: Safety first. Automation is earned, not assumed.

### IV. Composability Through Standards
**Rule**: Every capability is a skill. Every integration is an MCP server.

**Requirements**:
- Skills live in `.claude/commands/` with clear signatures
- MCP servers documented in `30-INTEGRATIONS/mcp-servers/`
- Skills are atomic: one clear purpose, testable independently
- No monolithic agents - compose small capabilities

**Rationale**: Enables reuse, testing, and incremental improvement.

### V. Memory as Knowledge
**Rule**: Learn from every interaction. Build institutional memory.

**Requirements**:
- Store episodic memory (events) in `80-MEMORY/episodic/`
- Store semantic memory (facts) in `80-MEMORY/semantic/`
- Store procedural memory (how-tos) in `80-MEMORY/procedural/`
- Weekly reviews to consolidate learnings into knowledge base

**Rationale**: The AI employee gets smarter over time, not just more data.

### VI. Fail Safe, Fail Visible
**Rule**: Errors must be logged, contained, and never silent.

**Requirements**:
- All errors logged to `70-LOGS/errors/` with full context
- Circuit breakers on external integrations (max retries, cooldowns)
- Rollback mechanisms for file operations
- Health checks every loop iteration

**Rationale**: Systems fail. The question is: do we know when and why?

---

## 3. Human-in-the-Loop Governance Model

### Approval Tiers

| Tier | Risk Level | Examples | Default Action | Approval SLA |
|------|-----------|----------|----------------|--------------|
| **Tier 0** | Read-only | File reads, searches, queries | Auto-approve | None |
| **Tier 1** | Low-risk writes | Vault writes, log entries, memory updates | Auto-approve | None |
| **Tier 2** | Medium-risk | Email drafts, calendar events, code commits | Require approval | 4 hours |
| **Tier 3** | High-risk | Payments, deletions, external API writes | Require approval | 1 hour |
| **Tier 4** | Critical | Security changes, credential updates | Require approval + 2FA | Immediate |

### Approval Workflow
1. **Request**: AI logs intent to `70-LOGS/hitl/pending/`
2. **Notification**: Watcher alerts human (desktop notification, email)
3. **Review**: Human reviews context, logs, and rationale
4. **Decision**: Approve, deny, or defer
5. **Execution**: If approved, action proceeds with full logging
6. **Audit**: All decisions logged to `70-LOGS/hitl/completed/`

### Escalation Rules
- If no response within SLA: escalate notification
- After 2 escalations: pause workflow, log as blocked
- Critical actions (Tier 4): no timeout, must be explicit

### Trust Score System (Future: Silver Tier)
- Track success rate per skill per tier
- After 50 successful operations at 98%+ success: propose auto-approval
- Human can accept, reject, or set conditions
- Auto-approval can be revoked at any time

---

## 4. Safety & Risk Boundaries

### Hard Limits (Non-Negotiable)
- **No credential exposure**: Secrets never in vault plaintext
- **No destructive auto-actions**: Deletions, payments always require approval
- **No silent failures**: Every error must be logged
- **No unbounded operations**: Rate limits on all external calls
- **No production access without testing**: Bronze tier is sandbox only

### Operational Boundaries

#### Bronze Tier (Current)
- **Scope**: Personal productivity (notes, tasks, emails, calendar)
- **Integrations**: Read-only APIs, local tools only
- **Autonomy**: HITL required for all Tier 2+ actions
- **Risk Budget**: Can break personal workflows, cannot affect others

#### Silver Tier (Future)
- **Scope**: Small team coordination (shared calendars, light CRM)
- **Integrations**: Write-enabled APIs with rate limits
- **Autonomy**: Tier 2 actions auto-approved for trusted skills
- **Risk Budget**: Can disrupt team workflows, no financial impact

#### Gold Tier (Future)
- **Scope**: Business operations (customer interactions, payments)
- **Integrations**: Full API access with circuit breakers
- **Autonomy**: Tier 3 actions auto-approved for proven skills
- **Risk Budget**: Financial exposure with caps and monitoring

### Circuit Breakers
- **API Rate Limits**: Respect external service quotas minus 20% buffer
- **Error Thresholds**: Pause skill after 3 consecutive failures
- **Retry Logic**: Exponential backoff, max 3 retries
- **Cooldown Periods**: 5 min after error threshold hit

---

## 5. Vault & File Governance Rules

### Folder Structure (Immutable)
The vault structure defined in `obsidian-vault/README.md` is canonical:
```
00-INDEX/       # Navigation and dashboards
10-KNOWLEDGE/   # Domain knowledge and agent skills
20-PROCESSES/   # Workflows and SOPs
30-INTEGRATIONS/# MCP servers and API configs
40-SECURITY/    # Policies and access control
50-BUSINESS/    # KPIs and business logic
60-PROMPTS/     # AI prompt library
70-LOGS/        # All activity logs
80-MEMORY/      # Long-term agent memory
90-TEMPLATES/   # Markdown templates
```

### Naming Conventions (Strict)
- **Folders**: `NN-CATEGORY/` (00-99 prefix, UPPERCASE)
- **Files**: `NNN-descriptor-name.md` (000-999 prefix, lowercase-with-hyphens)
- **Dates**: ISO 8601 (`YYYY-MM-DD`)
- **IDs**: Type-prefixed (`WF-001`, `MCP-042`, `TPL-023`)

See `NAMING-CONVENTIONS.md` for complete rules.

### Write Operations
- **Atomic Writes**: Create temp file → verify → rename
- **Backups**: Git commit before bulk operations
- **Validation**: Check frontmatter, tags, and links before save
- **Conflict Resolution**: Human decides on merge conflicts

### Read Operations
- **Caching**: Agent can cache file contents for 5 minutes
- **Indexing**: Maintain file index for fast searches
- **No Assumptions**: Always verify file exists before read

### Prohibited Operations
- ❌ Writes outside `obsidian-vault/` or `.claude/`
- ❌ Binary files in vault (except images in `attachments/`)
- ❌ Vault structure changes without constitution amendment
- ❌ Circular links that break Obsidian graph

---

## 6. MCP & External Action Control

### MCP Server Standards

#### Registration Requirements
Every MCP server must have:
1. **Config File**: `30-INTEGRATIONS/mcp-servers/MCP-NNN-name.md`
2. **Capabilities List**: What actions it exposes
3. **Authentication**: How credentials are managed
4. **Rate Limits**: Documented quotas and throttling
5. **Error Handling**: What to do on failures
6. **Health Check**: Endpoint or method to verify status

#### Approved MCP Servers (Bronze Tier)
- **Filesystem**: Local file operations (read-only initially)
- **GitHub**: Repository queries (read-only)
- **Obsidian**: Vault operations (write-enabled)
- **Custom Python**: Watcher scripts (controlled execution)

#### Adding New MCP Servers
1. Document in `30-INTEGRATIONS/mcp-servers/`
2. Test in isolation with mock data
3. Define HITL gates for write operations
4. Add to health check rotation
5. Update this constitution's approved list

### External API Guidelines

#### Before Integration
- [ ] API has rate limits we can respect
- [ ] Authentication can be secured (env vars, vault)
- [ ] Error responses are documented
- [ ] Billing/cost implications understood
- [ ] Retry logic designed

#### During Integration
- [ ] Wrapper in `30-INTEGRATIONS/apis/API-NNN-name.md`
- [ ] Test with sandbox/test credentials first
- [ ] Implement circuit breakers
- [ ] Log all requests/responses to `70-LOGS/integrations/`
- [ ] Monitor quota usage

#### After Integration
- [ ] Document common errors and fixes
- [ ] Set up alerts for failures or quota exhaustion
- [ ] Review logs weekly for optimization opportunities

### Action Approval Matrix

| Action Type | Approval Required | Logging | Circuit Breaker |
|-------------|------------------|---------|-----------------|
| Read files | No | Standard | N/A |
| Write vault | No | Detailed | After 10 errors |
| Read API | No | Standard | After 5 errors |
| Write API | Yes (Tier 2+) | Comprehensive | After 3 errors |
| External tool | Yes (Tier 3) | Comprehensive | After 1 error |
| Payment | Yes (Tier 4) | Immutable audit log | N/A |

---

## 7. Logging & Audit Requirements

### Log Levels

| Level | Purpose | Retention | Location |
|-------|---------|-----------|----------|
| **DEBUG** | Development troubleshooting | 7 days | `70-LOGS/debug/` |
| **INFO** | Normal operations | 90 days | `70-LOGS/daily/` |
| **WARN** | Recoverable issues | 180 days | `70-LOGS/warnings/` |
| **ERROR** | Failures requiring attention | 365 days | `70-LOGS/errors/` |
| **CRITICAL** | System integrity issues | Permanent | `70-LOGS/critical/` |

### Required Log Fields
Every log entry must include:
```yaml
timestamp: 2026-02-16T23:45:00.123Z
level: INFO | WARN | ERROR | CRITICAL
agent: agent-identifier
action: what-was-attempted
context:
  key: value
result: success | failure | partial
duration_ms: 1234
```

### Daily Operations Log
- **File**: `70-LOGS/daily/YYYY-MM-DD.md`
- **Contents**:
  - Summary of agents active
  - Count of actions by tier
  - HITL approvals/denials
  - Errors encountered
  - System health metrics
  - Performance stats

### Agent-Specific Logs
- **Location**: `70-LOGS/agents/{agent-name}/`
- **Purpose**: Track individual agent behavior
- **Includes**: Actions, decisions, learnings, errors

### Audit Trail (Immutable)
- **Location**: `70-LOGS/audit/`
- **Purpose**: Regulatory compliance, security investigations
- **Coverage**:
  - All Tier 3+ actions
  - All credential access
  - All security policy changes
  - All data exports/deletions

### Log Rotation & Archival
- **Daily logs**: Compress after 30 days
- **Error logs**: Archive after 90 days
- **Audit logs**: Never delete, compress after 365 days
- **Debug logs**: Purge after 7 days

---

## 8. Security & Credential Handling

### Credential Storage

#### Environment Variables (Preferred)
- All secrets in `.env` file (gitignored)
- Load at runtime only
- Never log credential values
- Rotate quarterly

#### Vault Encryption (Future: Silver Tier)
- Use encrypted vault for non-runtime secrets
- Decrypt on-demand with user authentication
- Re-encrypt immediately after use

#### Prohibited Storage
- ❌ Plaintext in vault markdown files
- ❌ Hardcoded in skill files
- ❌ In log files (even hashed)
- ❌ In git history

### Access Control

#### File Permissions
- Vault: Owner read/write only (`chmod 600` on sensitive files)
- Logs: Owner read/write, group read (`chmod 640`)
- Configs: Owner read/write only
- Scripts: Owner execute only for watchers

#### Agent Permissions
Each agent profile must declare:
- What files it can read
- What files it can write
- What MCP servers it can access
- What APIs it can call

### Security Incidents

#### Definition
- Unauthorized access to credentials
- Unintended external action execution
- Data exfiltration or exposure
- Privilege escalation attempt

#### Response
1. **Immediate**: Pause all agents, rotate affected credentials
2. **Investigate**: Review audit logs, identify root cause
3. **Document**: Write incident report to `40-SECURITY/incidents/`
4. **Remediate**: Fix vulnerability, update policies
5. **Review**: Update constitution if governance gap found

### Security Principles
1. **Least Privilege**: Agents get minimum necessary permissions
2. **Zero Trust**: Verify every action, even from trusted agents
3. **Defense in Depth**: Multiple layers (HITL, logging, circuit breakers)
4. **Assume Breach**: Design for graceful degradation and recovery

---

## 9. Skill Design Rules

### Skill Anatomy
Every skill must have:
```markdown
skill_name: descriptive-action-name
description: One-line summary of what it does
inputs:
  - name: input_name
    type: string | number | boolean | object
    required: true | false
    description: What this input means
outputs:
  - success: What's returned on success
  - failure: What's returned on failure
tier: 0 | 1 | 2 | 3 | 4 (approval requirement)
dependencies:
  - mcp_server: server-name
  - api: api-name
examples:
  - input: Example input
    output: Expected output
```

### Design Principles

#### I. Single Responsibility
- One skill = one clear purpose
- If description has "and", split into two skills
- Composability over complexity

#### II. Idempotent When Possible
- Running twice with same input should be safe
- For non-idempotent: document side effects clearly
- Use transaction-like patterns for multi-step operations

#### III. Fail Fast, Fail Clear
- Validate inputs before execution
- Return structured errors: `{error: "message", code: "ERROR_TYPE"}`
- No silent failures or partial success without clear indication

#### IV. Observable
- Log entry point and exit point
- Log decision branches taken
- Include timing information
- Context should enable replay/debugging

#### V. Testable
- Provide mock/test mode that doesn't execute real actions
- Include at least 3 examples: success, failure, edge case
- Document how to validate behavior

### Skill Lifecycle

#### Development
1. Define in `.claude/commands/skill-name.md`
2. Specify tier and approval requirements
3. Write test cases before implementation
4. Implement with logging and error handling

#### Testing
1. Test in isolation with mocks
2. Test with real integrations in sandbox
3. Test error paths and edge cases
4. Test HITL approval flow

#### Deployment
1. Document in `10-KNOWLEDGE/skills/`
2. Add to agent profiles that need it
3. Monitor logs for first 10 uses
4. Tune approval tier based on success rate

#### Maintenance
1. Review quarterly: still needed?
2. Update for API changes
3. Optimize based on usage patterns
4. Deprecate if unused for 90 days

### Skill Registry
Maintain index at `10-KNOWLEDGE/skills/README.md` with:
- Skill name and purpose
- Tier level
- Owner/maintainer
- Usage frequency
- Success rate
- Last updated date

---

## 10. Evolution Path: Bronze → Silver → Gold

### Current: Bronze Tier (Hackathon 0)

**Goal**: Prove the core loop works

**Capabilities**:
- ✅ Obsidian vault as memory
- ✅ Claude Code as reasoning engine
- ✅ Python watchers for persistence
- ✅ Basic MCP integrations (read-only)
- ✅ HITL gates for all Tier 2+ actions
- ✅ Comprehensive logging

**Limitations**:
- Single-agent only
- Manual approval for most actions
- Limited integrations
- No learning loops yet
- Personal use only (no team features)

**Success Metrics**:
- [ ] 7 consecutive days of uptime
- [ ] 50+ successful HITL approvals
- [ ] 3+ useful skills operational
- [ ] Zero security incidents
- [ ] Full audit trail maintained

### Next: Silver Tier

**Goal**: Multi-agent coordination and learning

**New Capabilities**:
- Multi-agent system with specialization
- Automated learning loops (weekly reviews)
- Advanced integrations (write-enabled APIs)
- Trust score system (gradual auto-approval)
- Team collaboration features

**New Requirements**:
- Agent coordination protocols
- Conflict resolution between agents
- Shared memory architecture
- Performance monitoring dashboard
- Cost tracking and optimization

**Prerequisites to Advance**:
- [ ] All Bronze success metrics met
- [ ] Constitution amendments documented
- [ ] Security audit passed
- [ ] Backup and recovery tested
- [ ] Human operator trained on Silver features

### Future: Gold Tier

**Goal**: Fully autonomous for approved domains

**New Capabilities**:
- Autonomous operation for trusted workflows
- Predictive intelligence (anticipate needs)
- Business process automation
- Customer-facing interactions
- Financial transaction handling

**New Requirements**:
- Comprehensive testing suite
- Real-time anomaly detection
- Regulatory compliance (GDPR, SOC2)
- Insurance/risk management
- 24/7 monitoring and alerting

**Prerequisites to Advance**:
- [ ] All Silver success metrics met
- [ ] 6 months of stable Silver operation
- [ ] External security audit passed
- [ ] Business continuity plan documented
- [ ] Legal review completed

---

## Governance & Amendments

### Constitutional Authority
This constitution supersedes all other documentation when conflicts arise. When in doubt, default to more restrictive interpretation.

### Amendment Process
1. **Proposal**: Document proposed change in `history/prompts/constitution/`
2. **Impact Analysis**: Assess effects on skills, agents, workflows
3. **Testing**: Validate changes in isolated environment
4. **Approval**: Human operator must explicitly approve
5. **Migration**: Update dependent files and templates
6. **Ratification**: Increment version, update this document

### Version Semantics
- **MAJOR (X.0.0)**: Breaking changes to core principles
- **MINOR (0.X.0)**: New sections or material expansions
- **PATCH (0.0.X)**: Clarifications, typo fixes, non-semantic changes

### Review Schedule
- **Weekly**: Operational review (are we following this?)
- **Monthly**: Effectiveness review (is this working?)
- **Quarterly**: Strategic review (what needs to change?)
- **Annually**: Major revision consideration

### Enforcement
- All skills must validate compliance before execution
- Agents log constitutional violations as CRITICAL errors
- Human operator reviews violations weekly
- Repeat violations trigger skill suspension

### Exceptions
No exceptions to:
- Credential handling rules
- Audit logging requirements
- HITL Tier 4 approvals

Temporary exceptions allowed (with documentation):
- File structure modifications during migration
- Experimental skills in isolated sandbox
- Performance optimizations that trade safety for speed

---

## Compliance Checklist

Before deploying any new capability, verify:

- [ ] Is the Obsidian vault still the source of truth?
- [ ] Are all actions logged comprehensively?
- [ ] Are appropriate HITL gates in place?
- [ ] Are credentials secured properly?
- [ ] Are error paths handled and tested?
- [ ] Is the skill documented with examples?
- [ ] Are circuit breakers configured?
- [ ] Is rollback/recovery possible?
- [ ] Have I updated relevant READMEs?
- [ ] Is this change captured in version history?

---

## Closing Principles

### Start Restrictive, Loosen Deliberately
Better to annoy a human with approvals than to automate a catastrophe. Trust is earned through repeated success.

### Transparency Builds Trust
Every decision, every action, every error must be visible. If you can't explain why the AI did something, it shouldn't have done it.

### Simplicity is Governance
Complex systems fail in complex ways. Simple, composable skills are easier to understand, test, and trust.

### The Human is the Owner
The AI employee is a tool, not a decision-maker. When in doubt, ask. When critical, require approval. Always.

---

**Ratified**: 2026-02-16
**Version**: 1.0.0
**Tier**: Bronze (Hackathon 0)
**Next Review**: 2026-03-16

*This constitution is a living document. Improve it as you learn.*
