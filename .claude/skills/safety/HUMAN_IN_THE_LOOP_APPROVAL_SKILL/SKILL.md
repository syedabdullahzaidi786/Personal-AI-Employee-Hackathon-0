# HUMAN_IN_THE_LOOP_APPROVAL_SKILL

**Status**: Specification Complete - Ready for Implementation
**Category**: Safety
**Tier**: 0 (Read-only - this skill provides approval for others)
**Version**: 1.0.0
**Owner**: Safety & Governance Team
**Last Updated**: 2026-02-17

---

## 1. Purpose

### Mission
Provide a reliable, auditable, and user-friendly human-in-the-loop approval system that enables AI agents to request human decision-making for high-risk or ambiguous operations.

### What It Does
- **Request Approval**: Agents submit operations requiring human decision
- **Present Context**: Show humans all relevant information to make informed decisions
- **Enforce Tiers**: Implement constitution's 5-tier approval system (Tier 0-4)
- **Track SLAs**: Monitor response times and escalate if needed
- **Log Decisions**: Create immutable audit trail of all approvals/denials
- **Enable Delegation**: Support approval delegation and role-based approval

### What It Doesn't Do
- ❌ Make decisions autonomously (always waits for human)
- ❌ Skip logging (every decision is recorded)
- ❌ Override denials (respects human decisions)
- ❌ Timeout without escalation (follows SLA rules)

### Why It Matters
This skill is the **safety foundation** of the entire AI Employee system:
- Prevents autonomous execution of risky operations
- Builds trust through transparency
- Enables gradual automation (start restrictive, loosen deliberately)
- Provides accountability through audit trails
- Allows humans to maintain control

---

## 2. Tier System

### Overview
Five tiers from 0 (auto-approve) to 4 (critical, immediate approval required).

### Tier 0: Read-Only (Auto-Approve)
```yaml
Risk Level: None
Examples:
  - File reads
  - Search operations
  - Query execution (no writes)
  - Report generation
  - Log viewing

Approval Required: No
SLA: N/A (immediate)
Escalation: N/A

Auto-Approve Conditions:
  - No state changes
  - No external calls with side effects
  - Fully logged
  - Reversible (or no action taken)
```

### Tier 1: Low-Risk Writes (Auto-Approve)
```yaml
Risk Level: Low
Examples:
  - Vault file organization
  - Metadata updates
  - Log entries
  - Memory storage
  - Tag additions

Approval Required: No (auto-approve with logging)
SLA: N/A (immediate)
Escalation: N/A

Auto-Approve Conditions:
  - Within vault boundaries
  - No content modification
  - Fully logged
  - Reversible
  - Validated before execution
```

### Tier 2: Medium-Risk (4 Hour SLA)
```yaml
Risk Level: Medium
Examples:
  - Email drafts (not sent)
  - Calendar event creation
  - Code commits (to feature branches)
  - Configuration changes (non-production)
  - Watcher creation

Approval Required: Yes
SLA: 4 hours
Escalation: After 2 failed notifications
Notification Methods: Desktop notification, email

Approval Conditions:
  - Clear preview of changes
  - Rationale provided
  - Risk assessment shown
  - Rollback plan available
```

### Tier 3: High-Risk (1 Hour SLA)
```yaml
Risk Level: High
Examples:
  - Email sending
  - External API writes
  - Payment initiation
  - Data deletion (soft delete)
  - Production deployments

Approval Required: Yes
SLA: 1 hour
Escalation: After 30 minutes if no response
Notification Methods: Desktop notification, email, SMS (if configured)

Approval Conditions:
  - Detailed impact analysis
  - Clear rationale and necessity
  - Risk mitigation plan
  - Rollback procedure documented
  - Blast radius defined
```

### Tier 4: Critical (Immediate, 2FA)
```yaml
Risk Level: Critical
Examples:
  - Security changes
  - Credential updates
  - Data deletion (permanent)
  - Production database changes
  - Financial transactions

Approval Required: Yes (with 2FA)
SLA: Immediate (no timeout)
Escalation: Continuous notifications until approved/denied
Notification Methods: All available (desktop, email, SMS, phone)

Approval Conditions:
  - Executive approval may be required
  - 2FA authentication mandatory
  - Cannot be delegated
  - Complete audit trail
  - Legal/compliance check may be needed
```

---

## 3. Capabilities

### 3.1 Approval Request Submission

#### Request Structure
```yaml
approval_request:
  # Request Identification
  request_id: "REQ-{UUID}"
  timestamp: "2026-02-17T10:30:00Z"

  # Requesting Agent
  agent_id: "email-sender-agent"
  agent_name: "Email Sending Agent"
  skill_name: "EMAIL_MCP_ACTION_SKILL"

  # Operation Details
  operation:
    name: "send_email"
    description: "Send welcome email to new customer"
    tier: 3  # High-risk

  # Context
  context:
    action: "Send email to customer@example.com"
    reason: "New customer onboarding workflow triggered"
    triggered_by: "WF-001-customer-onboarding"
    timestamp: "2026-02-17T10:28:45Z"

  # Preview/Details
  details:
    recipient: "customer@example.com"
    subject: "Welcome to Our Service"
    body_preview: "Dear Customer, Welcome to..."
    attachments: []
    estimated_delivery: "Immediate"

  # Risk Assessment
  risk:
    tier: 3
    blast_radius: "Single customer"
    reversibility: "Cannot unsend (email sent)"
    data_exposure: "Customer name, email visible"
    cost: "$0.001 (email API)"

  # Options
  options:
    - approve: "Send email now"
    - deny: "Do not send"
    - defer: "Decide later (hold for 1 hour)"
    - modify: "Edit email before sending"

  # SLA
  sla:
    required_by: "2026-02-17T11:30:00Z"  # 1 hour
    escalation_at: "2026-02-17T11:00:00Z"  # 30 min
    timeout_action: "deny"  # Default to safe option

  # Metadata
  metadata:
    workflow_id: "WF-001-customer-onboarding"
    customer_id: "CUST-12345"
    priority: "normal"
    tags: ["email", "onboarding", "customer"]
```

#### Submission API
```python
# Pseudo-code example
def request_approval(
    agent_id: str,
    operation: str,
    tier: int,
    context: dict,
    details: dict,
    options: list,
    sla_hours: float = None
) -> ApprovalRequest:
    """
    Submit an approval request to HITL system.

    Returns:
        ApprovalRequest object with request_id for tracking
    """
    # Validate tier
    if tier not in [0, 1, 2, 3, 4]:
        raise ValueError("Invalid tier")

    # Auto-approve Tier 0-1
    if tier in [0, 1]:
        return auto_approve(agent_id, operation, context)

    # Create request
    request = create_request(
        agent_id=agent_id,
        operation=operation,
        tier=tier,
        context=context,
        details=details,
        options=options
    )

    # Set SLA based on tier
    if sla_hours is None:
        sla_hours = TIER_SLA_MAP[tier]

    request.set_sla(hours=sla_hours)

    # Log request
    log_approval_request(request)

    # Notify human
    notify_human(request)

    # Return request object for tracking
    return request
```

### 3.2 Human Notification

#### Notification Methods

**Desktop Notification (Primary)**
```yaml
Method: Native OS notification
Platforms: Windows, macOS, Linux
Priority: High
Sound: Enabled for Tier 3+
Persistence: Until acknowledged

Notification Content:
  Title: "🔔 Approval Required (Tier {N})"
  Body: "{Agent} requests approval to {action}"
  Actions:
    - "Review" (opens approval UI)
    - "Deny" (immediately denies)
    - "Snooze" (10 min, Tier 2 only)

Example:
  Title: "🔔 Approval Required (Tier 3)"
  Body: "Email Agent requests approval to send email to customer@example.com"
  Actions: [Review] [Deny]
```

**Email Notification (Secondary)**
```yaml
Method: Email
Trigger: If desktop notification not acknowledged in 5 min
Subject: "[HITL] Approval Required (Tier {N}) - {Operation}"

Email Content:
  - Operation summary
  - Risk level and tier
  - Context and rationale
  - Direct approval link
  - Direct denial link
  - Time remaining (SLA)

Security:
  - Signed links (expire after SLA)
  - One-time use tokens
  - IP logging
```

**SMS Notification (Escalation)**
```yaml
Method: SMS (Tier 3-4 only)
Trigger: Escalation after SLA threshold

SMS Content:
  "HITL Approval Required (Tier {N}). {Agent} needs approval for {action}. Respond: CHECK {request_id}"

Security:
  - Only to verified phone numbers
  - Short codes for response
  - Rate limited
```

**Slack/Teams Integration (Optional)**
```yaml
Method: Chat app webhook
Trigger: Same as desktop notification
Platforms: Slack, Microsoft Teams, Discord

Message Format:
  "🔔 **Approval Required (Tier {N})**
   Agent: {agent_name}
   Action: {action}
   Tier: {tier}
   SLA: {time_remaining}

   [Approve] [Deny] [View Details]"
```

### 3.3 Approval Interface

#### CLI Interface (Primary)
```bash
# List pending approvals
$ hitl list

Pending Approvals (3):
  1. [Tier 3] Email Agent - Send email to customer@example.com
     Request ID: REQ-abc123
     SLA: 45 min remaining
     Status: Pending

  2. [Tier 2] Calendar Agent - Create meeting "Quarterly Review"
     Request ID: REQ-def456
     SLA: 3h 20min remaining
     Status: Pending

  3. [Tier 3] Payment Agent - Process refund $99.99
     Request ID: REQ-ghi789
     SLA: 25 min remaining
     Status: Escalated (⚠️ 5 min to timeout)

# View request details
$ hitl view REQ-abc123

┌─────────────────────────────────────────────────┐
│ Approval Request: REQ-abc123                    │
│ Tier 3 (High-Risk) - SLA: 45 min remaining      │
├─────────────────────────────────────────────────┤
│ Agent: Email Agent (email-sender-agent)         │
│ Operation: send_email                           │
│ Triggered: WF-001-customer-onboarding           │
│ Requested: 2026-02-17 10:30:00                  │
│                                                 │
│ Action:                                         │
│   Send welcome email to customer@example.com    │
│                                                 │
│ Details:                                        │
│   To: customer@example.com                      │
│   Subject: Welcome to Our Service               │
│   Body: (145 words)                             │
│   Attachments: None                             │
│                                                 │
│ Risk Assessment:                                │
│   Tier: 3 (High-Risk)                           │
│   Blast Radius: Single customer                 │
│   Reversibility: Cannot unsend                  │
│   Data Exposure: Customer name, email           │
│   Cost: $0.001                                  │
│                                                 │
│ Context:                                        │
│   Customer CUST-12345 signed up 2 min ago       │
│   Onboarding workflow requires welcome email    │
│   Email template: TEMPLATE-001-welcome          │
│   Previous sends: 487 (success rate: 99.8%)     │
│                                                 │
│ Options:                                        │
│   1. Approve - Send email now                   │
│   2. Deny - Do not send                         │
│   3. Defer - Decide later (hold 1 hour)         │
│   4. Modify - Edit before sending               │
│                                                 │
│ Decision? (1/2/3/4):                            │
└─────────────────────────────────────────────────┘

# Approve
$ hitl approve REQ-abc123 --reason "Standard onboarding, approved"

✅ Approval Granted
   Request: REQ-abc123
   Decision: Approved
   Reason: Standard onboarding, approved
   Time: 2026-02-17 10:32:15
   By: human-operator-john
   Logged: 70-LOGS/hitl/completed/REQ-abc123.md

   Email will be sent immediately.
   Agent has been notified.

# Deny
$ hitl deny REQ-abc123 --reason "Customer requested no marketing emails"

❌ Approval Denied
   Request: REQ-abc123
   Decision: Denied
   Reason: Customer requested no marketing emails
   Time: 2026-02-17 10:32:15
   By: human-operator-john
   Logged: 70-LOGS/hitl/completed/REQ-abc123.md

   Operation cancelled.
   Agent has been notified.
   Workflow will handle denial gracefully.

# Batch approve
$ hitl approve-batch --tier 2 --all

Batch Approval (Tier 2 only):
  ✅ REQ-def456 (Calendar Agent - Create meeting)
  ✅ REQ-jkl012 (Watcher Agent - Gmail watcher)

  2 requests approved
  0 requests denied
  Logged to: 70-LOGS/hitl/batch-2026-02-17T103000.md
```

#### Web UI (Optional - Future)
```yaml
Features:
  - Dashboard of pending approvals
  - Filterable by tier, agent, time
  - One-click approve/deny
  - Batch operations
  - Historical view
  - Analytics and trends

Technology Stack:
  - Backend: FastAPI (Python)
  - Frontend: React or Vue.js
  - Real-time: WebSocket updates
  - Authentication: SSO or local
```

### 3.4 Decision Processing

#### Approval Flow
```yaml
1. Human Approves:
   - Log decision immediately
   - Notify requesting agent
   - Agent proceeds with operation
   - Agent logs execution
   - Operation links to approval log

2. Human Denies:
   - Log decision with reason
   - Notify requesting agent
   - Agent handles denial gracefully
   - Workflow continues with alternative
   - No operation executed

3. Human Defers:
   - Log deferral with new deadline
   - Request remains pending
   - SLA extended (if allowed)
   - Re-notify at new time
   - Same process repeats

4. Human Modifies:
   - Log modification request
   - Return modified parameters to agent
   - Agent re-submits with changes
   - New approval request created
   - Original request marked "superseded"

5. Timeout (No Response):
   - Log timeout event
   - Execute default action (usually deny)
   - Notify human of auto-decision
   - Escalate to supervisor log
   - Review in weekly audit
```

#### Denial Handling
```python
# Pseudo-code
def handle_denial(request_id: str, reason: str):
    """Process approval denial"""

    # Log denial
    log_decision(
        request_id=request_id,
        decision="denied",
        reason=reason,
        timestamp=now(),
        decided_by=current_user()
    )

    # Notify requesting agent
    notify_agent(
        agent_id=request.agent_id,
        message={
            "request_id": request_id,
            "decision": "denied",
            "reason": reason,
            "timestamp": now()
        }
    )

    # Agent-specific denial handling
    agent_response = agent.handle_denial(
        operation=request.operation,
        reason=reason
    )

    # Log agent's response
    log_agent_response(request_id, agent_response)

    # Update workflow if applicable
    if request.workflow_id:
        update_workflow_status(
            workflow_id=request.workflow_id,
            step_id=request.step_id,
            status="blocked",
            reason=reason
        )
```

### 3.5 SLA Management

#### SLA Tracking
```yaml
Per-Request Tracking:
  - Creation timestamp
  - Required decision by (deadline)
  - Time remaining (real-time)
  - Escalation thresholds
  - Notification history

Global Tracking:
  - Average response time by tier
  - SLA violation rate
  - Escalation rate
  - Timeout rate
  - Approval/denial ratio
```

#### Escalation Rules
```yaml
Tier 2 (4 hour SLA):
  - Notify at: 0 min (immediate)
  - Reminder at: 2 hours
  - Escalate at: 3 hours 30 min
  - Timeout at: 4 hours (deny by default)

Tier 3 (1 hour SLA):
  - Notify at: 0 min (immediate)
  - Reminder at: 20 min
  - Escalate at: 30 min
  - Urgent reminder at: 50 min
  - Timeout at: 1 hour (deny by default)

Tier 4 (Immediate):
  - Notify: Immediately (all channels)
  - Reminder: Every 5 minutes
  - Escalate: Continuously
  - Timeout: Never (must be decided)
  - Fallback: Auto-deny only if critical system issue
```

#### Escalation Actions
```yaml
Level 1 (Initial Notification):
  - Desktop notification
  - Log to pending queue

Level 2 (Reminder):
  - Repeat desktop notification (with sound)
  - Send email
  - Log reminder

Level 3 (Escalation):
  - All Level 2 actions
  - SMS (if configured)
  - Notify supervisor (if defined)
  - Log escalation event
  - Increase notification frequency

Level 4 (Critical):
  - All Level 3 actions
  - Phone call (if configured)
  - Slack/Teams mention
  - Alert dashboard
  - Consider emergency contacts
```

### 3.6 Audit Logging

#### Log Structure
```yaml
# Every approval decision creates detailed log

log_entry:
  # Request Information
  request_id: "REQ-abc123"
  request_timestamp: "2026-02-17T10:30:00Z"

  # Agent Information
  agent_id: "email-sender-agent"
  skill_name: "EMAIL_MCP_ACTION_SKILL"
  operation: "send_email"

  # Decision Information
  decision: "approved"  # approved | denied | deferred | timeout
  decision_timestamp: "2026-02-17T10:32:15Z"
  decided_by: "human-operator-john"
  decision_reason: "Standard onboarding, approved"

  # Timing Information
  response_time_seconds: 135
  sla_hours: 1.0
  sla_met: true
  time_to_decision: "2 min 15 sec"

  # Context
  tier: 3
  risk_level: "high"
  operation_details: {...}
  context: {...}

  # Outcome
  agent_notified_at: "2026-02-17T10:32:16Z"
  operation_executed_at: "2026-02-17T10:32:20Z"
  operation_result: "success"

  # Audit Trail
  log_location: "70-LOGS/hitl/completed/REQ-abc123.md"
  immutable: true
  checksum: "sha256:abc123..."
```

#### Log Locations
```yaml
Pending Requests:
  Location: 70-LOGS/hitl/pending/
  Format: {request_id}.md
  Contains: Full request details
  Updated: Real-time

Completed Requests:
  Location: 70-LOGS/hitl/completed/
  Format: {request_id}.md
  Contains: Request + decision + outcome
  Immutable: Yes (append-only)

Daily Summary:
  Location: 70-LOGS/hitl/daily/{YYYY-MM-DD}.md
  Contains: All requests for that day
  Metrics: Response times, approval rates, etc.

Weekly Summary:
  Location: 70-LOGS/hitl/weekly/{YYYY-Www}.md
  Contains: Aggregated weekly metrics
  Trends: Approval patterns, SLA compliance

Monthly Summary:
  Location: 70-LOGS/hitl/monthly/{YYYY-MM}.md
  Contains: Monthly analytics
  Insights: Optimization opportunities
```

---

## 4. Integration Points

### 4.1 Agent Integration

#### How Agents Use This Skill
```python
# Agent wants to perform Tier 3 operation
from skills.safety import request_approval

# Step 1: Check if approval needed
tier = determine_tier(operation="send_email")

if tier >= 2:
    # Step 2: Prepare approval request
    request = request_approval(
        agent_id="email-sender-agent",
        operation="send_email",
        tier=3,
        context={
            "action": "Send welcome email",
            "recipient": "customer@example.com",
            "workflow": "WF-001-customer-onboarding"
        },
        details={
            "to": "customer@example.com",
            "subject": "Welcome to Our Service",
            "body": email_body,
            "template": "TEMPLATE-001-welcome"
        },
        options=[
            {"id": "approve", "label": "Send now"},
            {"id": "deny", "label": "Do not send"},
            {"id": "defer", "label": "Decide later"}
        ]
    )

    # Step 3: Wait for decision (blocking or async)
    decision = request.wait_for_decision(timeout=3600)  # 1 hour

    # Step 4: Handle decision
    if decision.approved:
        # Proceed with operation
        send_email(recipient, subject, body)
        log_success(request.id)

    elif decision.denied:
        # Handle denial gracefully
        log_denial(request.id, decision.reason)
        notify_workflow_blocked(reason=decision.reason)

    elif decision.timeout:
        # SLA exceeded, default action
        log_timeout(request.id)
        # Usually: do not proceed (safe default)
```

#### Async Pattern
```python
# Non-blocking pattern for workflows

async def execute_with_approval(operation, tier, context):
    """Execute operation with approval if needed"""

    if tier < 2:
        # Auto-approve
        return await execute(operation)

    # Request approval (non-blocking)
    request = await request_approval_async(
        operation=operation,
        tier=tier,
        context=context
    )

    # Register callback
    request.on_decision(callback=handle_decision)

    # Return immediately
    return {"status": "pending_approval", "request_id": request.id}

async def handle_decision(request_id, decision):
    """Called when human makes decision"""

    if decision.approved:
        await execute(operation)
    else:
        await handle_denial(decision.reason)
```

### 4.2 Workflow Integration

#### Workflow Pause Points
```yaml
# workflows/WF-001-customer-onboarding.md

steps:
  1. validate_customer_data:
      tier: 0
      approval: auto

  2. create_crm_record:
      tier: 1
      approval: auto

  3. send_welcome_email:
      tier: 3
      approval: required  # ← Workflow pauses here
      sla: 1 hour
      on_denial: skip_to_step_5

  4. schedule_onboarding_call:
      tier: 2
      approval: required
      sla: 4 hours
      on_denial: continue

  5. activate_account:
      tier: 1
      approval: auto
```

#### Workflow State Management
```python
class Workflow:
    def execute_step(self, step):
        """Execute workflow step with HITL support"""

        # Check if approval needed
        if step.tier >= 2:
            # Pause workflow
            self.state = "paused"
            self.paused_at = step.id
            self.save_state()

            # Request approval
            request = request_approval(
                operation=step.operation,
                tier=step.tier,
                context={
                    "workflow": self.id,
                    "step": step.id,
                    "step_name": step.name
                }
            )

            # Wait for decision
            decision = request.wait_for_decision(
                timeout=step.sla_seconds
            )

            # Resume or handle denial
            if decision.approved:
                self.state = "running"
                return self.execute(step)
            else:
                return self.handle_step_denial(step, decision)

        else:
            # Auto-approve, execute immediately
            return self.execute(step)
```

---

## 5. Configuration

### 5.1 System Configuration

```yaml
# config/hitl.yaml

hitl_config:
  # Notification Settings
  notifications:
    desktop:
      enabled: true
      sound: true
      persistence: true

    email:
      enabled: true
      delay_seconds: 300  # 5 min after desktop
      smtp_server: "smtp.example.com"
      from_address: "ai-employee@example.com"
      to_address: "operator@example.com"

    sms:
      enabled: false  # Optional
      provider: "twilio"
      to_number: "+1234567890"
      tier_threshold: 3  # Only Tier 3+

    slack:
      enabled: false  # Optional
      webhook_url: "https://hooks.slack.com/..."
      channel: "#ai-approvals"
      tier_threshold: 2

  # SLA Configuration
  sla:
    tier_2: 14400  # 4 hours in seconds
    tier_3: 3600   # 1 hour
    tier_4: 0      # Immediate

    escalation:
      tier_2:
        reminder_at: 7200    # 2 hours
        escalate_at: 12600   # 3.5 hours

      tier_3:
        reminder_at: 1200    # 20 min
        escalate_at: 1800    # 30 min
        urgent_at: 3000      # 50 min

      tier_4:
        reminder_every: 300  # 5 min

    timeout_action: "deny"  # deny | approve | escalate

  # Approval Delegation
  delegation:
    enabled: true
    allowed_tiers: [2]  # Only Tier 2 can be delegated
    delegation_limit: 3  # Max delegation chain
    require_confirmation: true

  # Batch Approval
  batch:
    enabled: true
    max_batch_size: 10
    require_review: true  # Must review before batch approve
    allowed_tiers: [1, 2]  # No batch for Tier 3+

  # Trust Score (Future: Silver Tier)
  trust_score:
    enabled: false  # Bronze tier: all require approval
    threshold: 0.95  # 95% success rate
    min_samples: 50   # Min operations before auto-approve

  # Logging
  logging:
    location: "70-LOGS/hitl/"
    retention_days: 365
    immutable: true
    checksum: true

  # UI
  ui:
    cli_enabled: true
    web_enabled: false  # Future
    mobile_enabled: false  # Future
```

### 5.2 User Configuration

```yaml
# config/users.yaml

users:
  human-operator-john:
    email: "john@example.com"
    phone: "+1234567890"
    role: "primary_operator"
    permissions:
      - approve_tier_0
      - approve_tier_1
      - approve_tier_2
      - approve_tier_3
      - deny_any

    preferences:
      notification_methods: ["desktop", "email"]
      quiet_hours:
        enabled: true
        start: "22:00"
        end: "08:00"
        emergency_override: tier_4

    delegation:
      enabled: true
      delegates: ["human-operator-alice"]
      tiers: [2]

  human-operator-alice:
    email: "alice@example.com"
    role: "backup_operator"
    permissions:
      - approve_tier_0
      - approve_tier_1
      - approve_tier_2
      - deny_any

  supervisor-bob:
    email: "bob@example.com"
    phone: "+1234567891"
    role: "supervisor"
    permissions:
      - approve_tier_4
      - override_any
      - view_all_requests

    escalation:
      receives: tier_4
      always_cc: true
```

---

## 6. Security & Safety

### 6.1 Security Controls

#### Authentication
```yaml
Requirements:
  - Tier 0-2: User authentication required
  - Tier 3: User authentication + session verification
  - Tier 4: User authentication + 2FA mandatory

Methods:
  - CLI: SSH key or PAM authentication
  - Web: OAuth2, SSO, or local auth
  - API: Signed tokens with expiration

Session Management:
  - Max session length: 8 hours
  - Re-auth required: After 30 min idle (Tier 3+)
  - Concurrent sessions: 1 per user (configurable)
```

#### Authorization
```yaml
Role-Based Access:
  primary_operator:
    - Approve/deny Tier 0-3
    - View all requests
    - Batch approve Tier 1-2
    - Delegate Tier 2

  backup_operator:
    - Approve/deny Tier 0-2
    - View assigned requests
    - Batch approve Tier 1

  supervisor:
    - All operator permissions
    - Approve/deny Tier 4
    - Override decisions (logged)
    - View analytics

  auditor:
    - View all logs (read-only)
    - Generate reports
    - No approval permissions
```

#### Audit Trail Security
```yaml
Immutability:
  - All logs are append-only
  - No modification allowed
  - No deletion allowed (except per retention policy)
  - Checksums for integrity

Encryption:
  - Logs encrypted at rest (optional)
  - Sensitive data redacted
  - API tokens never logged
  - Passwords never logged

Access Logging:
  - All log access is logged
  - Who, when, what viewed
  - Unauthorized access attempts logged
  - Regular audit log reviews
```

### 6.2 Safety Mechanisms

#### Fail-Safe Defaults
```yaml
If uncertain: Deny
If timeout: Deny (for Tier 2-3)
If error: Deny
If system unavailable: Queue for later, block operation

Exception:
  - Tier 4: Never auto-deny, must wait for human
  - Emergency override: Requires supervisor
```

#### Request Validation
```python
def validate_request(request: ApprovalRequest) -> bool:
    """Validate approval request before processing"""

    # Required fields present
    if not all([request.agent_id, request.operation, request.tier]):
        raise ValidationError("Missing required fields")

    # Tier valid
    if request.tier not in [0, 1, 2, 3, 4]:
        raise ValidationError("Invalid tier")

    # Agent registered
    if not agent_exists(request.agent_id):
        raise ValidationError("Unknown agent")

    # Operation allowed for tier
    if not is_operation_allowed(request.operation, request.tier):
        raise ValidationError("Operation not allowed for tier")

    # Context sufficient
    if len(request.context) < 3:
        raise ValidationError("Insufficient context")

    # Risk assessment present for Tier 3+
    if request.tier >= 3 and not request.risk_assessment:
        raise ValidationError("Risk assessment required")

    return True
```

#### Anti-Abuse Measures
```yaml
Rate Limiting:
  - Max 10 requests per agent per minute
  - Max 100 pending requests per agent
  - Cooldown after 3 denials: 5 minutes

Request Deduplication:
  - Detect duplicate requests (same operation, context)
  - Prevent request spam
  - Log duplicate attempts

Suspicious Activity Detection:
  - Multiple rapid requests (>5/min)
  - All requests denied (>10 consecutive)
  - Unusual hours (outside business hours for non-urgent)
  - Alert supervisor if detected
```

---

## 7. Logging & Monitoring

### 7.1 Request Log Entry

```markdown
---
request_id: REQ-abc123
timestamp: 2026-02-17T10:30:00Z
status: completed
---

# Approval Request: REQ-abc123

## Request Information
- **ID**: REQ-abc123
- **Timestamp**: 2026-02-17 10:30:00 UTC
- **Tier**: 3 (High-Risk)
- **SLA**: 1 hour (by 11:30:00 UTC)
- **Status**: Completed

## Agent Information
- **Agent ID**: email-sender-agent
- **Agent Name**: Email Sending Agent
- **Skill**: EMAIL_MCP_ACTION_SKILL
- **Operation**: send_email

## Operation Details
### Action
Send welcome email to new customer

### Context
- Workflow: WF-001-customer-onboarding
- Customer: CUST-12345
- Trigger: Customer signup (2026-02-17 10:28:45)

### Details
```yaml
to: customer@example.com
subject: "Welcome to Our Service"
body_preview: "Dear Customer, Welcome to..."
template: TEMPLATE-001-welcome
attachments: []
```

### Risk Assessment
- **Tier**: 3 (High-Risk)
- **Blast Radius**: Single customer
- **Reversibility**: Cannot unsend email
- **Data Exposure**: Customer name, email address
- **Cost**: $0.001 (email API call)

## Decision Information
- **Decision**: ✅ Approved
- **Decided By**: human-operator-john
- **Decided At**: 2026-02-17 10:32:15 UTC
- **Response Time**: 2 min 15 sec
- **SLA Met**: Yes (57 min 45 sec remaining)
- **Reason**: "Standard onboarding email, customer just signed up, approved"

## Outcome
- **Agent Notified**: 2026-02-17 10:32:16 UTC
- **Operation Executed**: 2026-02-17 10:32:20 UTC
- **Operation Result**: Success
- **Email Sent**: Yes
- **Email ID**: MSG-xyz789
- **Delivery Status**: Delivered (2026-02-17 10:32:25 UTC)

## Audit Trail
- **Log Created**: 2026-02-17 10:30:00 UTC
- **Log Completed**: 2026-02-17 10:32:30 UTC
- **Immutable**: Yes
- **Checksum**: sha256:abc123def456...
- **Linked Logs**:
  - Workflow: 70-LOGS/workflows/WF-001-EXEC-789.md
  - Email: 70-LOGS/integrations/email/2026-02-17.md
  - Agent: 70-LOGS/agents/email-sender/2026-02-17.md

---
Generated by: HUMAN_IN_THE_LOOP_APPROVAL_SKILL v1.0.0
Constitution Compliant: ✅
```

### 7.2 Daily Summary

```markdown
# HITL Daily Summary - 2026-02-17

## Overview
- **Total Requests**: 24
- **Approved**: 18 (75%)
- **Denied**: 4 (17%)
- **Deferred**: 1 (4%)
- **Timeout**: 1 (4%)

## By Tier
| Tier | Count | Approved | Denied | Avg Response Time |
|------|-------|----------|--------|-------------------|
| 0    | 0     | 0        | 0      | N/A               |
| 1    | 0     | 0        | 0      | N/A               |
| 2    | 15    | 13       | 2      | 45 min            |
| 3    | 8     | 5        | 2      | 12 min            |
| 4    | 1     | 0        | 0      | Pending           |

## By Agent
| Agent | Requests | Approved | Denied | Success Rate |
|-------|----------|----------|--------|--------------|
| Email Agent | 8 | 6 | 2 | 75% |
| Calendar Agent | 10 | 9 | 1 | 90% |
| Payment Agent | 4 | 3 | 1 | 75% |
| Watcher Agent | 2 | 0 | 0 | Pending |

## SLA Compliance
- **Met**: 22 (92%)
- **Missed**: 1 (4%)
- **Pending**: 1 (4%)
- **Average Response Time**: 28 min
- **Fastest Response**: 2 min 15 sec
- **Slowest Response**: 3 hrs 45 min

## Escalations
- **Total**: 3
- **Tier 2**: 2 (both resolved)
- **Tier 3**: 1 (resolved)
- **Supervisor Involved**: 1

## Top Denial Reasons
1. "Customer preference - no emails" (2 times)
2. "Already scheduled" (1 time)
3. "Duplicate request" (1 time)

## Notable Events
- ⚠️ One Tier 2 request timed out (WF-023)
- ✅ All Tier 3 requests handled within SLA
- 🔔 First Tier 4 request received (security update)

## Recommendations
- Review email agent logic (2 denials for customer preferences)
- Consider auto-checking calendar before meeting requests
- Configure duplicate detection for faster denial

---
Generated: 2026-02-17 23:59:59
Next Review: 2026-02-24 (weekly)
```

---

## 8. Constitution Compliance

### ✅ Principle I: Local-First Sovereignty
**Requirement**: All state in vault
**Compliance**:
- All requests logged to `70-LOGS/hitl/`
- Decisions stored in markdown files
- No external database dependencies
- Configuration in local files

### ✅ Principle II: Explicit Over Implicit
**Requirement**: Declare intent before action
**Compliance**:
- All requests logged before notification
- Full context provided to humans
- Decisions explicitly recorded
- No silent approvals/denials

### ✅ Principle III: HITL by Default
**Requirement**: High-risk actions require approval
**Compliance**:
- This IS the HITL system
- Implements 5-tier approval model
- Enforces SLAs
- Enables human control

### ✅ Principle IV: Composability Through Standards
**Requirement**: Skills are atomic and composable
**Compliance**:
- Clear API for all agents
- Standard request format
- Reusable across all skills
- No business logic coupling

### ✅ Principle V: Memory as Knowledge
**Requirement**: Learn from interactions
**Compliance**:
- All decisions logged
- Patterns tracked (approval rates, common denials)
- Trust scores calculated (Silver tier)
- Historical trends analyzed

### ✅ Principle VI: Fail Safe, Fail Visible
**Requirement**: Errors logged, contained, never silent
**Compliance**:
- Default to deny on errors
- All errors logged
- Timeout handling explicit
- No silent failures

### ✅ Section 3: HITL Governance Model
**Requirement**: Implement constitution's HITL system
**Compliance**:
- Implements exact tier system from constitution
- Enforces SLAs as specified
- Escalation rules match constitution
- Audit trail as required

### ✅ Section 7: Logging Requirements
**Requirement**: Comprehensive logging
**Compliance**:
- Every request logged
- Every decision logged
- Immutable audit trail
- Daily/weekly/monthly summaries

---

## 9. Implementation Roadmap

### Phase 1: Core Approval System (Week 1)
```yaml
Deliverables:
  - [ ] Request submission API
  - [ ] Request validation
  - [ ] Pending queue management
  - [ ] Basic CLI interface (list, view, approve, deny)
  - [ ] Decision logging
  - [ ] Unit tests (80% coverage)

Success Criteria:
  - Can submit approval request
  - Can view pending requests
  - Can approve/deny
  - All decisions logged
  - Tests pass
```

### Phase 2: Notification System (Week 2)
```yaml
Deliverables:
  - [ ] Desktop notifications (cross-platform)
  - [ ] Email notifications
  - [ ] Notification delivery tracking
  - [ ] SLA timer implementation
  - [ ] Escalation logic
  - [ ] Integration tests

Success Criteria:
  - Notifications reach human
  - SLA tracking works
  - Escalations trigger correctly
  - Email delivery confirmed
```

### Phase 3: Agent Integration (Week 3)
```yaml
Deliverables:
  - [ ] Python SDK for agents
  - [ ] Async/await support
  - [ ] Workflow integration helpers
  - [ ] Timeout handling
  - [ ] Example integrations (filesystem skill)
  - [ ] Integration tests

Success Criteria:
  - Agents can request approval easily
  - Workflow pause/resume works
  - Timeouts handled gracefully
  - Documentation complete
```

### Phase 4: Polish & Production (Week 4)
```yaml
Deliverables:
  - [ ] Configuration system
  - [ ] User management
  - [ ] Daily/weekly/monthly reports
  - [ ] Performance optimization
  - [ ] Security hardening
  - [ ] User acceptance testing

Success Criteria:
  - Configuration flexible
  - Multi-user support
  - Reports accurate
  - Performance acceptable (<500ms per request)
  - Security reviewed
  - Ready for Bronze Tier
```

---

## 10. Testing Strategy

### Unit Tests
```python
# Test request validation
def test_validate_request_valid():
    request = create_test_request(tier=3)
    assert validate_request(request) == True

def test_validate_request_invalid_tier():
    request = create_test_request(tier=5)
    with pytest.raises(ValidationError):
        validate_request(request)

# Test decision processing
def test_approval_flow():
    request = submit_request(tier=2)
    decision = approve_request(request.id, "test reason")
    assert decision.approved == True
    assert log_exists(request.id)

# Test SLA calculation
def test_sla_tier_3():
    request = create_request(tier=3)
    assert request.sla_hours == 1.0
    assert request.deadline > now() + timedelta(minutes=59)
```

### Integration Tests
```python
# Test end-to-end approval flow
async def test_approval_workflow():
    # Agent submits request
    request = await agent.request_approval(
        operation="test_op",
        tier=3,
        context={"test": True}
    )

    # Human approves
    decision = await human_approve(request.id)

    # Agent receives notification
    notification = await agent.wait_for_notification()
    assert notification.approved == True

    # Logs created
    assert log_exists(f"hitl/completed/{request.id}.md")
```

### Acceptance Tests
```yaml
Test: Real approval workflow
Duration: 30 minutes
Scenario:
  1. Filesystem skill requests Tier 2 approval
  2. Desktop notification appears
  3. Human reviews in CLI
  4. Human approves
  5. Skill continues execution
  6. Logs created correctly

Success Criteria:
  - Notification appears within 5 sec
  - CLI shows all details
  - Approval processed immediately
  - Logs accurate and complete
  - Skill resumes correctly
```

---

## 11. Performance Targets

### Latency
- **Request Submission**: < 100ms
- **Notification Delivery**: < 5 seconds
- **Decision Processing**: < 500ms
- **Log Writing**: < 200ms

### Throughput
- **Concurrent Requests**: 100+
- **Requests per Minute**: 60
- **Pending Queue Size**: 1000+

### Reliability
- **Uptime**: 99.9%
- **Notification Delivery**: 99.5%
- **Log Integrity**: 100%

---

## 12. Future Enhancements (Silver/Gold Tier)

### Silver Tier
- Web UI for approvals
- Mobile app integration
- Trust score system (gradual automation)
- Batch approval with filtering
- Delegation workflows
- Analytics dashboard

### Gold Tier
- ML-powered risk assessment
- Predictive approval suggestions
- Smart escalation based on patterns
- Voice interface (Alexa, Google Home)
- Multi-tenant support
- Advanced audit analytics

---

## Approval & Sign-Off

**Specification Complete**: 2026-02-17
**Reviewed By**: [Human Operator Name]
**Approved For Implementation**: ⏳ Pending
**Target Completion**: Week 1-4 (Bronze Tier)

**Constitution Compliance**: ✅ All requirements met
**Security Review**: ✅ No vulnerabilities identified
**Critical Skill**: ✅ Foundation for all other Tier 2+ skills

---

**Ready for Implementation**: Yes
**Blockers**: None
**Next Step**: Begin Phase 1 development

**Priority**: CRITICAL - This skill must be implemented before any Tier 2+ skills
