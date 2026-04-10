# 20-PROCESSES: Workflows & Procedures

## Purpose
Executable workflows, standard operating procedures (SOPs), and process automation logic for autonomous agents and human-in-the-loop operations.

## Structure

```
20-PROCESSES/
├── workflows/           # Automated workflows
│   ├── customer/        # Customer-facing workflows
│   ├── internal/        # Internal operations
│   └── integration/     # Cross-system workflows
├── hitl/                # Human-in-the-loop procedures
│   ├── approval-gates/  # Approval checkpoints
│   ├── escalation/      # Escalation rules
│   └── decision-points/ # Human decision requirements
├── sops/                # Standard Operating Procedures
│   ├── operational/     # Day-to-day operations
│   ├── emergency/       # Incident response
│   └── maintenance/     # System maintenance
├── automation/          # Automation scripts and rules
├── playbooks/           # Scenario-based playbooks
└── templates/           # Process templates
```

## Key Files

- **[[workflows/index|Workflow Index]]** - All automated workflows
- **[[hitl/master-gate-map|HITL Gate Map]]** - Human approval requirements
- **[[sops/index|SOP Library]]** - Complete procedure index
- **[[automation/rule-engine|Automation Rules]]** - Trigger-action mappings

## Usage by AI Agents

### Workflow Execution
```yaml
Process: customer-onboarding
Steps:
  1. Read: 20-PROCESSES/workflows/customer/onboarding.md
  2. Execute: Each step sequentially
  3. Log: Progress to 70-LOGS/workflows/
  4. Checkpoint: HITL gates as defined
```

### HITL Integration
```yaml
Checkpoint: high-value-transaction
Criteria:
  - Amount > $10,000
  - New customer (< 90 days)
Action:
  - Pause workflow
  - Notify: finance-approver
  - Log: 70-LOGS/hitl/pending.md
  - Resume: Upon approval
```

### Decision Trees
Agents navigate decision trees to:
- Handle exceptions
- Apply business rules
- Route to appropriate handlers
- Escalate when needed

## Naming Conventions

### Files
- **Workflows**: `WF-NNN-workflow-name.md`
- **SOPs**: `SOP-NNN-procedure-name.md`
- **HITL**: `HITL-NNN-gate-name.md`
- **Playbooks**: `PB-NNN-scenario-name.md`

### Tags
- `#process/<category>` - Process category
- `#workflow/<name>` - Workflow identifier
- `#hitl-required` - Requires human intervention
- `#automated` - Fully automated
- `#priority/<level>` - Execution priority
- `#frequency/<cadence>` - Execution frequency

## Process States

| State | Description | Icon |
|-------|-------------|------|
| Draft | Under development | 📝 |
| Review | Pending approval | 🔍 |
| Active | In production | ✅ |
| Paused | Temporarily disabled | ⏸️ |
| Deprecated | No longer used | ⚠️ |
| Archived | Historical reference | 📦 |

## HITL Approval Levels

| Level | Description | SLA | Escalation |
|-------|-------------|-----|------------|
| L1 | Routine approvals | 1 hour | L2 after 2 hours |
| L2 | Significant decisions | 4 hours | L3 after 8 hours |
| L3 | Strategic approvals | 24 hours | Executive after 48h |
| Executive | Major decisions | 72 hours | Board notification |

## Maintenance

### Daily
- [ ] Monitor active workflow executions
- [ ] Review HITL pending queue
- [ ] Clear completed process logs

### Weekly
- [ ] Audit automation rules
- [ ] Update SOP documentation
- [ ] Optimize slow workflows

### Monthly
- [ ] Comprehensive process review
- [ ] Identify bottlenecks
- [ ] Refactor inefficient workflows

## Templates

- [[../90-TEMPLATES/process-sop|Process SOP]]
- [[../90-TEMPLATES/workflow-definition|Workflow Definition]]
- [[../90-TEMPLATES/hitl-gate|HITL Gate]]
- [[../90-TEMPLATES/playbook|Scenario Playbook]]

## Integration with Other Sections

- **10-KNOWLEDGE**: Knowledge informs process decisions
- **30-INTEGRATIONS**: Processes trigger MCP integrations
- **50-BUSINESS**: Business rules govern processes
- **60-PROMPTS**: Processes use prompt templates
- **70-LOGS**: All executions are logged

## Automation Examples

### Simple Automation
```yaml
Trigger: New customer signup
Process: 20-PROCESSES/workflows/customer/onboarding.md
Actions:
  - Send welcome email
  - Create CRM record
  - Assign account manager
  - Schedule follow-up
```

### Complex HITL Workflow
```yaml
Trigger: Contract value > $50K
Process: 20-PROCESSES/workflows/customer/high-value-contract.md
Steps:
  1. Initial validation (automated)
  2. Risk assessment (automated)
  3. Legal review (HITL - Level 2)
  4. Pricing approval (HITL - Level 3)
  5. Contract generation (automated)
  6. Final signature (HITL - Level 3)
  7. Activation (automated)
```

---

**Owned by**: Process Automation Agent
**Last Review**: 2026-02-16
**Next Review**: 2026-03-16
