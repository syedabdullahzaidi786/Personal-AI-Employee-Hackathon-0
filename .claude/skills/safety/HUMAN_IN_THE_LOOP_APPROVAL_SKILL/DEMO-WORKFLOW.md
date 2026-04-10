# HUMAN_IN_THE_LOOP_APPROVAL_SKILL - Demo Workflow

**Status**: ✅ Specification Complete - Ready for Implementation
**Version**: 1.0.0
**Category**: Safety Skill
**Tier**: 0 (Read-only, provides approval for others)
**Priority**: CRITICAL (Foundation for all Tier 2+ skills)

---

## Purpose

This document provides 5 practical demonstrations of the Human-in-the-Loop Approval System. Each demo includes:
- Step-by-step instructions
- Expected outputs
- Verification steps
- Common issues and solutions

These demos are designed to be copy-pasted and executed in sequence to validate the skill's core functionality.

---

## Prerequisites

Before running demos, ensure:
- [ ] HITL skill is implemented and installed
- [ ] CLI interface is accessible (`hitl --version` works)
- [ ] Notification channels are configured (at least desktop)
- [ ] Logging directory exists: `obsidian-vault/70-LOGS/approvals/`
- [ ] Test agent is available for generating approval requests

---

## Demo Environment Setup

```bash
# Navigate to project root
cd "C:\Users\Computer Technology\OneDrive\Desktop\Hackathon_GIAIC\Hackathon_0"

# Verify HITL CLI is available
hitl --version
# Expected: HITL Approval System v1.0.0

# Verify logging directory exists
ls obsidian-vault/70-LOGS/approvals/
# Expected: Directory exists (may be empty initially)

# Check configuration
hitl config show
# Expected: Display current HITL configuration (tiers, SLAs, notifications)
```

---

## Demo 1: Single Approval Request (Tier 2 - Medium Risk)

**Objective**: Submit a Tier 2 approval request, review it, and approve it via CLI.

**Scenario**: An agent wants to send a business email to a client.

### Step 1: Submit Approval Request

```bash
# Simulate agent submitting approval request
hitl submit \
  --agent-id "email-sender-agent" \
  --operation "send_email" \
  --tier 2 \
  --action "Send business proposal email to client" \
  --reason "Client requested proposal after demo call" \
  --details '{
    "recipient": "client@example.com",
    "subject": "Q1 2026 Proposal - AI Employee System",
    "body_preview": "Dear Client,\n\nThank you for the productive demo...",
    "attachments": ["proposal-Q1-2026.pdf"],
    "estimated_cost": "$0.01"
  }' \
  --blast-radius "Single email to one recipient" \
  --reversibility "Cannot recall email after send" \
  --data-exposure "Business proposal (internal use)"
```

**Expected Output**:
```
✅ Approval request submitted successfully
Request ID: REQ-a1b2c3d4-e5f6-7890-abcd-ef1234567890
Tier: 2 (Medium Risk)
SLA: 4 hours (expires at 2026-02-16 16:30:00)
Status: PENDING
Notifications sent: Desktop, Email

View details: hitl view REQ-a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Verification**:
```bash
# Check desktop notification appeared
# Expected: Desktop notification with request summary

# Check email notification sent
# Expected: Email to configured address with full request details

# Verify request appears in pending queue
hitl list --status pending
# Expected: Shows REQ-a1b2c3d4... in pending queue

# Verify log entry created
ls obsidian-vault/70-LOGS/approvals/2026-02-16/
# Expected: File REQ-a1b2c3d4-*.approval.log exists
```

### Step 2: Review Request Details

```bash
# View full request details
hitl view REQ-a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Expected Output**:
```yaml
Request ID: REQ-a1b2c3d4-e5f6-7890-abcd-ef1234567890
Status: PENDING
Agent: email-sender-agent
Operation: send_email (Tier 2)
Submitted: 2026-02-16 12:30:00

Context:
  Action: Send business proposal email to client
  Reason: Client requested proposal after demo call
  Triggered By: Scheduled workflow: weekly-proposal-sender
  Timestamp: 2026-02-16T12:30:00Z

Details:
  Recipient: client@example.com
  Subject: Q1 2026 Proposal - AI Employee System
  Body Preview: Dear Client,\n\nThank you for the productive demo...
  Attachments: ["proposal-Q1-2026.pdf"]
  Estimated Cost: $0.01

Risk Assessment:
  Tier: 2 (Medium Risk)
  Blast Radius: Single email to one recipient
  Reversibility: Cannot recall email after send
  Data Exposure: Business proposal (internal use)
  Cost Impact: Negligible ($0.01)

SLA:
  Required By: 2026-02-16 16:30:00 (3h 59m remaining)
  Escalation At: 2026-02-16 15:30:00 (2h 59m remaining)
  Timeout Action: deny (default for Tier 2)

Options:
  [A] Approve - Execute send_email operation
  [D] Deny - Block operation and notify agent
  [F] Defer - Request 1-hour extension
  [M] Modify - Change parameters (recipient, subject, body)
```

### Step 3: Approve Request

```bash
# Approve the request
hitl approve REQ-a1b2c3d4-e5f6-7890-abcd-ef1234567890 \
  --comment "Proposal reviewed and approved. Client relationship established."
```

**Expected Output**:
```
✅ Request approved successfully
Request ID: REQ-a1b2c3d4-e5f6-7890-abcd-ef1234567890
Decision: APPROVED
Decided By: human-operator-001
Decided At: 2026-02-16 12:35:00
Comment: Proposal reviewed and approved. Client relationship established.

Agent "email-sender-agent" has been notified and may now execute send_email.
```

**Verification**:
```bash
# Verify request status changed
hitl view REQ-a1b2c3d4-e5f6-7890-abcd-ef1234567890 | grep "Status:"
# Expected: Status: APPROVED

# Verify decision logged
cat obsidian-vault/70-LOGS/approvals/2026-02-16/REQ-a1b2c3d4-*.approval.log | grep "DECISION"
# Expected: Contains APPROVED decision with timestamp, operator, comment

# Verify request no longer in pending queue
hitl list --status pending
# Expected: Request removed from pending queue

# Verify agent can retrieve decision
hitl get-decision REQ-a1b2c3d4-e5f6-7890-abcd-ef1234567890
# Expected: Returns APPROVED status with full decision details
```

### Step 4: Verify Execution Log

```bash
# Check that operation execution was logged (simulated)
cat obsidian-vault/70-LOGS/approvals/2026-02-16/REQ-a1b2c3d4-*.approval.log
```

**Expected Log Contents**:
```log
[2026-02-16 12:30:00] REQUEST_SUBMITTED: REQ-a1b2c3d4-e5f6-7890-abcd-ef1234567890
  Agent: email-sender-agent
  Operation: send_email (Tier 2)
  SLA: 4 hours (expires 2026-02-16 16:30:00)
  Checksum: sha256:abc123...

[2026-02-16 12:30:01] NOTIFICATION_SENT: Desktop notification delivered
[2026-02-16 12:30:02] NOTIFICATION_SENT: Email notification delivered to operator@example.com

[2026-02-16 12:35:00] DECISION_RECORDED: APPROVED
  Decided By: human-operator-001
  Comment: Proposal reviewed and approved. Client relationship established.
  Decision Time: 5 minutes (within SLA)
  Checksum: sha256:def456...

[2026-02-16 12:35:01] AGENT_NOTIFIED: email-sender-agent notified of approval
[2026-02-16 12:35:05] OPERATION_EXECUTED: send_email completed successfully
  Result: Email sent to client@example.com
  Message ID: msg-xyz789
```

**Success Criteria**:
- ✅ Request submitted successfully with valid ID
- ✅ Desktop and email notifications received
- ✅ Request visible in pending queue
- ✅ Request details viewable via CLI
- ✅ Approval recorded with operator and comment
- ✅ Agent notified of decision
- ✅ Full audit trail logged immutably

---

## Demo 2: Batch Approval (Multiple Tier 1 Operations)

**Objective**: Submit multiple low-risk operations and approve them in batch.

**Scenario**: Agent wants to organize 5 files in the vault.

### Step 1: Submit Multiple Tier 1 Requests

```bash
# Submit 5 file organization requests (Tier 1 - auto-approve candidate)
for i in {1..5}; do
  hitl submit \
    --agent-id "filesystem-automation" \
    --operation "organize_file" \
    --tier 1 \
    --action "Move and rename Meeting_Notes_$i.md" \
    --reason "Enforce naming conventions and folder structure" \
    --details "{
      \"source\": \"vault/Meeting_Notes_$i.md\",
      \"destination\": \"vault/80-MEMORY/episodic/EP-20260216-meeting-notes-$i.md\",
      \"changes\": [\"rename\", \"move\", \"add_frontmatter\"]
    }" \
    --blast-radius "Single file (no links)" \
    --reversibility "Fully reversible (can restore)" \
    --data-exposure "Internal meeting notes"
done
```

**Expected Output** (for each request):
```
✅ Approval request submitted successfully
Request ID: REQ-[unique-id-1]
Tier: 1 (Low Risk - Auto-Approve Candidate)
Status: PENDING
Auto-approve eligibility: YES (Tier 1, low blast radius, reversible)

5 requests submitted. View batch: hitl list --agent filesystem-automation
```

### Step 2: Review Batch

```bash
# List all pending requests from filesystem agent
hitl list --agent filesystem-automation --status pending
```

**Expected Output**:
```
Pending Requests (5):

ID                                      Agent                  Operation        Tier  Age   SLA Remaining
REQ-11111111-1111-1111-1111-111111111111  filesystem-automation  organize_file    1     1m    N/A (auto-approve)
REQ-22222222-2222-2222-2222-222222222222  filesystem-automation  organize_file    1     1m    N/A (auto-approve)
REQ-33333333-3333-3333-3333-333333333333  filesystem-automation  organize_file    1     1m    N/A (auto-approve)
REQ-44444444-4444-4444-4444-444444444444  filesystem-automation  organize_file    1     1m    N/A (auto-approve)
REQ-55555555-5555-5555-5555-555555555555  filesystem-automation  organize_file    1     1m    N/A (auto-approve)

Use 'hitl batch-approve --agent filesystem-automation' to approve all eligible requests.
```

### Step 3: Batch Approve

```bash
# Approve all Tier 1 requests in batch
hitl batch-approve \
  --agent filesystem-automation \
  --tier 1 \
  --comment "Batch approval: Standard file organization operations"
```

**Expected Output**:
```
Processing batch approval...

✅ REQ-11111111-1111-1111-1111-111111111111: APPROVED
✅ REQ-22222222-2222-2222-2222-222222222222: APPROVED
✅ REQ-33333333-3333-3333-3333-333333333333: APPROVED
✅ REQ-44444444-4444-4444-4444-444444444444: APPROVED
✅ REQ-55555555-5555-5555-5555-555555555555: APPROVED

Batch Summary:
  Total Requests: 5
  Approved: 5
  Denied: 0
  Skipped: 0

Decided By: human-operator-001
Decided At: 2026-02-16 12:45:00
Batch Comment: Batch approval: Standard file organization operations

Agent "filesystem-automation" has been notified. Operations may now execute.
```

**Verification**:
```bash
# Verify all requests approved
hitl list --agent filesystem-automation --status approved | wc -l
# Expected: 5 approved requests

# Verify batch operation logged
cat obsidian-vault/70-LOGS/approvals/2026-02-16/BATCH-*.approval.log
# Expected: Contains batch decision record with all 5 request IDs
```

**Success Criteria**:
- ✅ Multiple Tier 1 requests submitted successfully
- ✅ Batch command identifies eligible requests
- ✅ All requests approved in single operation
- ✅ Batch decision logged with shared comment
- ✅ Agent notified once with all approvals

---

## Demo 3: Request Denial (Tier 3 - High Risk)

**Objective**: Deny a high-risk operation and verify agent is blocked.

**Scenario**: Agent attempts to delete production database records.

### Step 1: Submit High-Risk Request

```bash
# Submit Tier 3 deletion request
hitl submit \
  --agent-id "database-maintenance" \
  --operation "delete_records" \
  --tier 3 \
  --action "Delete 150 customer records older than 7 years" \
  --reason "GDPR compliance: Data retention policy enforcement" \
  --details '{
    "database": "production",
    "table": "customers",
    "filter": "last_activity < 2019-02-16",
    "estimated_count": 150,
    "backup_available": true
  }' \
  --blast-radius "150 customer records (potentially active)" \
  --reversibility "Reversible from backup (24h restore window)" \
  --data-exposure "PII deletion (GDPR-regulated)"
```

**Expected Output**:
```
✅ Approval request submitted successfully
Request ID: REQ-danger-1111-2222-3333-444444444444
Tier: 3 (High Risk)
SLA: 1 hour (expires at 2026-02-16 13:45:00)
Status: PENDING
Notifications sent: Desktop, Email, SMS

⚠️  HIGH RISK OPERATION - Immediate attention required
View details: hitl view REQ-danger-1111-2222-3333-444444444444
```

**Verification**:
```bash
# Check all notification channels fired
# Expected: Desktop notification, Email, SMS message received

# Verify SLA is 1 hour (Tier 3)
hitl view REQ-danger-1111-2222-3333-444444444444 | grep "SLA:"
# Expected: SLA: 1 hour
```

### Step 2: Review and Deny

```bash
# View full request details
hitl view REQ-danger-1111-2222-3333-444444444444

# Deny the request with detailed reason
hitl deny REQ-danger-1111-2222-3333-444444444444 \
  --reason "REJECTED: Customer records appear to have recent activity. Manual audit required before deletion." \
  --require-manual-review
```

**Expected Output**:
```
✅ Request denied successfully
Request ID: REQ-danger-1111-2222-3333-444444444444
Decision: DENIED
Decided By: human-operator-001
Decided At: 2026-02-16 12:50:00
Reason: REJECTED: Customer records appear to have recent activity. Manual audit required before deletion.
Manual Review Required: YES

Agent "database-maintenance" has been notified and operation is BLOCKED.
Escalation flag set: Manual audit required.
```

### Step 3: Verify Agent is Blocked

```bash
# Simulate agent checking decision
hitl get-decision REQ-danger-1111-2222-3333-444444444444
```

**Expected Output**:
```yaml
Request ID: REQ-danger-1111-2222-3333-444444444444
Status: DENIED
Decision: DENIED
Decided By: human-operator-001
Decided At: 2026-02-16 12:50:00
Reason: REJECTED: Customer records appear to have recent activity. Manual audit required before deletion.
Manual Review Required: YES
Operation Blocked: YES

Agent Action Required:
  Do NOT execute delete_records operation.
  Escalate to human operator for manual audit.
  Review customer activity data and resubmit request if appropriate.
```

**Verification**:
```bash
# Verify denial logged with full context
cat obsidian-vault/70-LOGS/approvals/2026-02-16/REQ-danger-*.approval.log | grep "DENIED"
# Expected: Contains DENIED decision with reason and escalation flag

# Verify request moved to denied queue
hitl list --status denied
# Expected: Shows REQ-danger-... in denied queue

# Verify no execution occurred
cat obsidian-vault/70-LOGS/approvals/2026-02-16/REQ-danger-*.approval.log | grep "OPERATION_EXECUTED"
# Expected: No execution record (operation blocked)
```

**Success Criteria**:
- ✅ Tier 3 request triggers all notification channels (Desktop, Email, SMS)
- ✅ 1-hour SLA enforced
- ✅ Request denied with detailed reason
- ✅ Agent receives BLOCKED status
- ✅ Manual review flag set
- ✅ No operation execution occurred
- ✅ Full audit trail with denial reason

---

## Demo 4: SLA Timeout and Escalation

**Objective**: Demonstrate SLA timeout behavior and escalation.

**Scenario**: Tier 2 request expires without decision (simulated by fast-forwarding time).

### Step 1: Submit Request with Short SLA

```bash
# Submit Tier 2 request with custom short SLA for demo purposes
hitl submit \
  --agent-id "social-media-poster" \
  --operation "post_tweet" \
  --tier 2 \
  --action "Post company update to Twitter" \
  --reason "Announce new product launch" \
  --details '{
    "platform": "twitter",
    "content": "Excited to announce our new AI Employee platform! 🚀",
    "visibility": "public"
  }' \
  --blast-radius "Public social media post (permanent)" \
  --reversibility "Can delete post but may be screenshot/cached" \
  --data-exposure "Public company announcement" \
  --sla-override 300
  # SLA override: 5 minutes (300 seconds) for demo purposes
```

**Expected Output**:
```
✅ Approval request submitted successfully
Request ID: REQ-timeout-1111-2222-3333-444444444444
Tier: 2 (Medium Risk)
SLA: 5 minutes (expires at 2026-02-16 12:55:00)
Escalation: 3 minutes (2026-02-16 12:53:00)
Status: PENDING

⏰ Short SLA: This request will timeout in 5 minutes
View details: hitl view REQ-timeout-1111-2222-3333-444444444444
```

### Step 2: Wait for Escalation

```bash
# Wait 3 minutes (or simulate time passage)
sleep 180

# Check request status
hitl view REQ-timeout-1111-2222-3333-444444444444
```

**Expected Output**:
```yaml
Request ID: REQ-timeout-1111-2222-3333-444444444444
Status: PENDING (ESCALATED)
⚠️  ESCALATION: SLA escalation point reached (2 minutes remaining)

Escalation Actions Taken:
  - Additional desktop notification sent
  - Escalation email sent to supervisor
  - SMS reminder sent
  - Request priority increased

Original SLA: 5 minutes (expires at 2026-02-16 12:55:00)
Time Remaining: 2 minutes
Timeout Action: deny (default for Tier 2)
```

### Step 3: Wait for Timeout

```bash
# Wait additional 2 minutes for timeout
sleep 120

# Check request status after timeout
hitl view REQ-timeout-1111-2222-3333-444444444444
```

**Expected Output**:
```yaml
Request ID: REQ-timeout-1111-2222-3333-444444444444
Status: DENIED (TIMEOUT)
Decision: DENIED
Decided By: SYSTEM (timeout)
Decided At: 2026-02-16 12:55:00
Reason: SLA timeout - No decision received within 5 minutes. Default action: deny

Agent "social-media-poster" has been notified and operation is BLOCKED.
```

**Verification**:
```bash
# Verify timeout logged with system decision
cat obsidian-vault/70-LOGS/approvals/2026-02-16/REQ-timeout-*.approval.log
```

**Expected Log Contents**:
```log
[2026-02-16 12:50:00] REQUEST_SUBMITTED: REQ-timeout-1111-2222-3333-444444444444
  SLA: 5 minutes (custom override)
  Escalation: 3 minutes
  Timeout Action: deny

[2026-02-16 12:53:00] ESCALATION_TRIGGERED: SLA escalation point reached
  Time Remaining: 2 minutes
  Actions: Additional notifications sent

[2026-02-16 12:55:00] SLA_TIMEOUT: No decision received
  Decision: DENIED (system timeout)
  Decided By: SYSTEM
  Reason: SLA timeout - No decision received within 5 minutes. Default action: deny

[2026-02-16 12:55:01] AGENT_NOTIFIED: social-media-poster notified of timeout denial
```

**Success Criteria**:
- ✅ SLA countdown accurate
- ✅ Escalation triggered at specified time (3 minutes)
- ✅ Additional notifications sent during escalation
- ✅ Timeout occurs exactly at SLA expiration
- ✅ System automatically denies request (fail-safe)
- ✅ Agent notified of timeout denial
- ✅ Full escalation and timeout logged

---

## Demo 5: Request Modification (Tier 2)

**Objective**: Modify request parameters before approval.

**Scenario**: Approve email request but change recipient to reduce blast radius.

### Step 1: Submit Request with Broad Recipient List

```bash
# Submit email request with multiple recipients
hitl submit \
  --agent-id "email-sender-agent" \
  --operation "send_email" \
  --tier 2 \
  --action "Send product announcement to all customers" \
  --reason "Quarterly product update newsletter" \
  --details '{
    "recipients": ["all-customers@company.com"],
    "subject": "Q1 2026 Product Updates",
    "body_preview": "Dear Valued Customer...",
    "estimated_reach": 10000
  }' \
  --blast-radius "10,000 customer emails" \
  --reversibility "Cannot recall mass email" \
  --data-exposure "Product information (public)"
```

**Expected Output**:
```
✅ Approval request submitted successfully
Request ID: REQ-modify-1111-2222-3333-444444444444
Tier: 2 (Medium Risk)
Blast Radius: 10,000 customer emails (HIGH)
Status: PENDING

⚠️  Large blast radius detected - Review carefully
View details: hitl view REQ-modify-1111-2222-3333-444444444444
```

### Step 2: Review and Decide to Modify

```bash
# View request
hitl view REQ-modify-1111-2222-3333-444444444444

# Modify request to reduce blast radius
hitl modify REQ-modify-1111-2222-3333-444444444444 \
  --modify-field "recipients" \
  --new-value '["beta-customers@company.com"]' \
  --modify-field "estimated_reach" \
  --new-value "500" \
  --reason "Reducing blast radius: Send to beta customers first, then broader rollout if successful" \
  --approve-after-modify
```

**Expected Output**:
```
✅ Request modified successfully
Request ID: REQ-modify-1111-2222-3333-444444444444

Modifications Applied:
  recipients: ["all-customers@company.com"] → ["beta-customers@company.com"]
  estimated_reach: 10000 → 500

Blast Radius: 10,000 customer emails → 500 beta customer emails (REDUCED)

Decision: APPROVED (with modifications)
Decided By: human-operator-001
Decided At: 2026-02-16 13:00:00
Reason: Reducing blast radius: Send to beta customers first, then broader rollout if successful

Agent "email-sender-agent" has been notified with modified parameters.
```

### Step 3: Agent Retrieves Modified Parameters

```bash
# Simulate agent retrieving decision with modifications
hitl get-decision REQ-modify-1111-2222-3333-444444444444
```

**Expected Output**:
```yaml
Request ID: REQ-modify-1111-2222-3333-444444444444
Status: APPROVED (MODIFIED)
Decision: APPROVED
Decided By: human-operator-001
Decided At: 2026-02-16 13:00:00

⚠️  PARAMETERS MODIFIED - Use modified values below

Original Parameters:
  recipients: ["all-customers@company.com"]
  estimated_reach: 10000

Modified Parameters (USE THESE):
  recipients: ["beta-customers@company.com"]
  estimated_reach: 500

Modification Reason:
  Reducing blast radius: Send to beta customers first, then broader rollout if successful

Agent Action Required:
  Execute send_email operation with MODIFIED parameters.
  Do NOT use original parameters.
  Modified parameters are binding.
```

**Verification**:
```bash
# Verify modification logged with before/after parameters
cat obsidian-vault/70-LOGS/approvals/2026-02-16/REQ-modify-*.approval.log | grep -A 10 "MODIFICATION"
```

**Expected Log Contents**:
```log
[2026-02-16 13:00:00] MODIFICATION_APPLIED: REQ-modify-1111-2222-3333-444444444444
  Decided By: human-operator-001

  Original Parameters:
    recipients: ["all-customers@company.com"]
    estimated_reach: 10000
    blast_radius: "10,000 customer emails"

  Modified Parameters:
    recipients: ["beta-customers@company.com"]
    estimated_reach: 500
    blast_radius: "500 beta customer emails"

  Modification Reason: Reducing blast radius: Send to beta customers first, then broader rollout if successful

  Blast Radius Change: HIGH → MEDIUM (reduced)

[2026-02-16 13:00:01] DECISION_RECORDED: APPROVED (with modifications)
[2026-02-16 13:00:02] AGENT_NOTIFIED: email-sender-agent notified with modified parameters
```

**Success Criteria**:
- ✅ Request modified before approval
- ✅ Blast radius reduced (10,000 → 500)
- ✅ Agent receives modified parameters
- ✅ Original and modified parameters logged
- ✅ Modification reason documented
- ✅ Agent enforces use of modified parameters

---

## Demo 6: Delegation and Multi-Operator Workflow

**Objective**: Delegate approval to another operator and track decision chain.

**Scenario**: Primary operator is unavailable; request is delegated to backup operator.

### Step 1: Submit Tier 3 Request Requiring Expertise

```bash
# Submit request that needs domain expertise
hitl submit \
  --agent-id "legal-document-signer" \
  --operation "sign_contract" \
  --tier 3 \
  --action "Electronically sign vendor contract" \
  --reason "New cloud infrastructure vendor onboarding" \
  --details '{
    "vendor": "CloudProvider Inc.",
    "contract_type": "Master Services Agreement",
    "contract_value": "$120,000/year",
    "term": "3 years",
    "requires_legal_review": true
  }' \
  --blast-radius "Legal and financial commitment" \
  --reversibility "Contract cancellation subject to penalties" \
  --data-exposure "Company financial information"
```

**Expected Output**:
```
✅ Approval request submitted successfully
Request ID: REQ-delegate-1111-2222-3333-444444444444
Tier: 3 (High Risk)
SLA: 1 hour
Status: PENDING
Requires Expertise: Legal review

Suggested Delegates: legal-team-lead, cfo
View details: hitl view REQ-delegate-1111-2222-3333-444444444444
```

### Step 2: Delegate to Legal Expert

```bash
# Current operator delegates to legal expert
hitl delegate REQ-delegate-1111-2222-3333-444444444444 \
  --to "legal-team-lead" \
  --reason "Requires legal expertise for contract review" \
  --notify-methods "email,sms"
```

**Expected Output**:
```
✅ Request delegated successfully
Request ID: REQ-delegate-1111-2222-3333-444444444444
Delegated From: human-operator-001
Delegated To: legal-team-lead
Delegated At: 2026-02-16 13:10:00
Reason: Requires legal expertise for contract review

Notifications sent to legal-team-lead: Email, SMS
SLA remains: 1 hour (unchanged)
Status: PENDING (DELEGATED)

Delegation tracked in audit log.
```

### Step 3: Delegated Operator Reviews and Approves

```bash
# Simulate legal team lead logging in and viewing request
# (This would be done by the delegated operator)

# Legal team lead views request
hitl view REQ-delegate-1111-2222-3333-444444444444 --as legal-team-lead
```

**Expected Output**:
```yaml
Request ID: REQ-delegate-1111-2222-3333-444444444444
Status: PENDING (DELEGATED TO YOU)
Delegated From: human-operator-001
Delegated At: 2026-02-16 13:10:00
Delegation Reason: Requires legal expertise for contract review

[... full request details ...]

Your Action Required:
  Review contract details and approve/deny as legal expert.
```

```bash
# Legal team lead approves after review
hitl approve REQ-delegate-1111-2222-3333-444444444444 \
  --as legal-team-lead \
  --comment "Contract reviewed. Terms acceptable. MSA standard clauses verified. Approved for signature."
```

**Expected Output**:
```
✅ Request approved successfully
Request ID: REQ-delegate-1111-2222-3333-444444444444
Decision: APPROVED
Decided By: legal-team-lead (delegated from human-operator-001)
Decided At: 2026-02-16 13:25:00
Comment: Contract reviewed. Terms acceptable. MSA standard clauses verified. Approved for signature.

Delegation Chain:
  1. human-operator-001 (delegated to legal-team-lead)
  2. legal-team-lead (final decision: APPROVED)

Agent "legal-document-signer" has been notified and may proceed with signature.
```

**Verification**:
```bash
# Verify delegation chain logged
cat obsidian-vault/70-LOGS/approvals/2026-02-16/REQ-delegate-*.approval.log
```

**Expected Log Contents**:
```log
[2026-02-16 13:05:00] REQUEST_SUBMITTED: REQ-delegate-1111-2222-3333-444444444444
  Agent: legal-document-signer
  Operation: sign_contract (Tier 3)

[2026-02-16 13:10:00] DELEGATION_INITIATED: human-operator-001 → legal-team-lead
  Reason: Requires legal expertise for contract review
  Notifications: Email, SMS sent to legal-team-lead
  SLA: Unchanged (1 hour from submission)

[2026-02-16 13:25:00] DECISION_RECORDED: APPROVED
  Decided By: legal-team-lead (delegated authority)
  Original Operator: human-operator-001
  Delegation Chain: human-operator-001 → legal-team-lead
  Comment: Contract reviewed. Terms acceptable. MSA standard clauses verified. Approved for signature.

[2026-02-16 13:25:01] AGENT_NOTIFIED: legal-document-signer notified of approval
```

**Success Criteria**:
- ✅ Request delegated to expert operator
- ✅ Delegated operator notified via email and SMS
- ✅ SLA countdown continues during delegation
- ✅ Delegated operator can view and act on request
- ✅ Final decision attributed to delegated operator
- ✅ Full delegation chain logged
- ✅ Original operator informed of final decision

---

## Demo 7: Emergency Tier 4 (Critical) Approval

**Objective**: Handle critical operation requiring immediate attention and 2FA.

**Scenario**: Production system failure requires emergency database rollback.

### Step 1: Submit Tier 4 Critical Request

```bash
# Submit emergency Tier 4 request
hitl submit \
  --agent-id "incident-response-bot" \
  --operation "database_rollback" \
  --tier 4 \
  --action "Rollback production database to 2026-02-16 10:00:00" \
  --reason "INCIDENT #1234: Database corruption detected after failed migration" \
  --details '{
    "database": "production",
    "rollback_point": "2026-02-16T10:00:00Z",
    "data_loss_window": "3 hours",
    "affected_users": "all",
    "downtime_estimate": "15 minutes"
  }' \
  --blast-radius "CRITICAL: All production users (downtime, data loss)" \
  --reversibility "Cannot reverse rollback (forward-only recovery)" \
  --data-exposure "3 hours of production data will be lost"
```

**Expected Output**:
```
🚨 CRITICAL TIER 4 REQUEST SUBMITTED 🚨
Request ID: REQ-critical-1111-2222-3333-444444444444
Tier: 4 (CRITICAL)
SLA: IMMEDIATE (no timeout)
Status: PENDING
2FA Required: YES

⚠️  ALL NOTIFICATION CHANNELS ACTIVATED ⚠️
  - Desktop: URGENT notification displayed
  - Email: HIGH PRIORITY email sent
  - SMS: Emergency SMS sent
  - Phone: Automated call initiated (if configured)
  - Slack/Teams: @here mention in #incidents channel

🔐 TWO-FACTOR AUTHENTICATION REQUIRED
Enter 2FA code to proceed: _
```

### Step 2: Authenticate with 2FA

```bash
# Enter 2FA code from authenticator app
hitl view REQ-critical-1111-2222-3333-444444444444 --2fa 123456
```

**Expected Output**:
```
✅ 2FA authentication successful
Authenticated: human-operator-001

Request ID: REQ-critical-1111-2222-3333-444444444444
Status: PENDING (CRITICAL - IMMEDIATE ACTION REQUIRED)
Tier: 4 (CRITICAL)

🚨 EMERGENCY DATABASE ROLLBACK 🚨

Context:
  Incident: #1234
  Issue: Database corruption detected after failed migration
  Severity: CRITICAL
  Affected Users: ALL production users

Operation: database_rollback
  Database: production
  Rollback Point: 2026-02-16 10:00:00 (3 hours ago)
  Data Loss Window: 3 hours of production data
  Downtime Estimate: 15 minutes
  Reversibility: Cannot reverse rollback (forward-only recovery)

Risk Assessment:
  Blast Radius: CRITICAL - All production users (downtime, data loss)
  Data Loss: 3 hours of production data will be lost
  User Impact: All users will experience 15-minute downtime

⚠️  CRITICAL DECISION REQUIRED ⚠️
Options:
  [A] Approve - Execute emergency rollback (data loss, downtime)
  [D] Deny - Continue with corrupted database (investigate alternative solutions)

Decision must be made IMMEDIATELY (Tier 4 has no timeout).
```

### Step 3: Approve Critical Operation

```bash
# Approve emergency rollback with detailed justification
hitl approve REQ-critical-1111-2222-3333-444444444444 \
  --2fa 123456 \
  --comment "APPROVED: Database corruption confirmed by DBA team. Rollback is only viable option. Customer support notified. Status page updated. Incident commander: operator-001. GO FOR ROLLBACK."
```

**Expected Output**:
```
✅ 2FA verification successful
✅ CRITICAL REQUEST APPROVED

Request ID: REQ-critical-1111-2222-3333-444444444444
Decision: APPROVED
Decided By: human-operator-001 (2FA verified)
Decided At: 2026-02-16 13:35:00
Comment: APPROVED: Database corruption confirmed by DBA team. Rollback is only viable option. Customer support notified. Status page updated. Incident commander: operator-001. GO FOR ROLLBACK.

🚨 CRITICAL OPERATION AUTHORIZED 🚨
Agent "incident-response-bot" has been notified and may execute database_rollback IMMEDIATELY.

All stakeholders notified:
  - Incident team: Notified via Slack #incidents
  - Executive team: SMS sent
  - Customer support: Email sent
  - Engineering team: PagerDuty alert sent
```

### Step 4: Monitor Execution

```bash
# Monitor operation execution status
hitl monitor REQ-critical-1111-2222-3333-444444444444 --follow
```

**Expected Output** (live streaming):
```
Monitoring execution: REQ-critical-1111-2222-3333-444444444444

[13:35:05] Operation started: database_rollback
[13:35:06] Pre-flight checks: PASSED
[13:35:10] Backup created: backup-emergency-20260216-133510.sql
[13:35:15] Stopping application servers...
[13:35:20] Application servers stopped (5 servers)
[13:35:25] Beginning database rollback to 2026-02-16 10:00:00...
[13:40:30] Rollback complete (5m 5s)
[13:40:35] Verifying database integrity...
[13:40:45] Integrity check: PASSED
[13:40:50] Restarting application servers...
[13:45:00] Application servers online (5/5 healthy)
[13:45:05] Smoke tests: PASSED
[13:45:10] Operation complete: database_rollback

✅ CRITICAL OPERATION SUCCESSFUL
Total Duration: 10 minutes 5 seconds
Downtime: 9 minutes 40 seconds
Status: COMPLETE
```

**Verification**:
```bash
# Verify complete audit trail with 2FA verification
cat obsidian-vault/70-LOGS/approvals/2026-02-16/REQ-critical-*.approval.log
```

**Expected Log Contents**:
```log
[2026-02-16 13:30:00] REQUEST_SUBMITTED: REQ-critical-1111-2222-3333-444444444444
  Tier: 4 (CRITICAL)
  Agent: incident-response-bot
  Operation: database_rollback
  Incident: #1234 - Database corruption

[2026-02-16 13:30:01] NOTIFICATION_SENT: All channels activated
  - Desktop: URGENT notification
  - Email: HIGH PRIORITY
  - SMS: Emergency alert
  - Phone: Automated call
  - Slack: @here mention in #incidents
  - PagerDuty: P1 incident created

[2026-02-16 13:32:00] 2FA_VERIFICATION: human-operator-001
  Method: Authenticator app
  Status: SUCCESS
  IP: 192.168.1.100

[2026-02-16 13:35:00] DECISION_RECORDED: APPROVED
  Decided By: human-operator-001 (2FA verified)
  Comment: APPROVED: Database corruption confirmed by DBA team. Rollback is only viable option.
  2FA Timestamp: 2026-02-16 13:35:00
  Authorization Level: CRITICAL (Tier 4)

[2026-02-16 13:35:05] OPERATION_STARTED: database_rollback
[2026-02-16 13:45:10] OPERATION_COMPLETED: database_rollback
  Status: SUCCESS
  Duration: 10 minutes 5 seconds
  Downtime: 9 minutes 40 seconds
  Data Loss: 3 hours (as expected)

[2026-02-16 13:45:15] INCIDENT_RESOLVED: #1234
  Resolution: Database rolled back to stable state
  Post-mortem: Scheduled for 2026-02-17
```

**Success Criteria**:
- ✅ Tier 4 request triggers all notification channels immediately
- ✅ 2FA required for viewing and approving
- ✅ No SLA timeout (immediate decision required)
- ✅ Full stakeholder notification on approval
- ✅ Real-time operation monitoring available
- ✅ Complete audit trail with 2FA verification logs
- ✅ Incident resolution tracked end-to-end

---

## Troubleshooting

### Issue: "CLI command not found"
**Cause**: HITL skill not installed or not in PATH
**Fix**:
```bash
# Verify installation
which hitl
# If not found, reinstall or add to PATH
export PATH=$PATH:/path/to/hitl/bin
```

### Issue: "Request not found"
**Cause**: Invalid request ID or request expired
**Fix**:
```bash
# Verify request ID is correct
hitl list --all | grep REQ-<partial-id>

# Check expired requests
hitl list --status expired
```

### Issue: "Permission denied"
**Cause**: Operator not authorized for tier or operation
**Fix**:
```bash
# Check operator permissions
hitl config show-permissions

# Request admin to grant permissions
# (See SKILL.md Section 7.3: Authorization)
```

### Issue: "SLA timeout too soon"
**Cause**: SLA misconfigured or insufficient time for review
**Fix**:
```bash
# Request SLA extension (before timeout)
hitl defer REQ-xxx --extend 3600 --reason "Need additional review time"

# Or configure default SLAs in config
hitl config set sla.tier2 7200  # Extend Tier 2 to 2 hours
```

### Issue: "Notifications not received"
**Cause**: Notification channels misconfigured
**Fix**:
```bash
# Test notification channels
hitl test-notifications --desktop --email --sms

# Check configuration
hitl config show-notifications

# Update notification settings
hitl config set notifications.email "operator@example.com"
```

### Issue: "2FA verification failed"
**Cause**: Incorrect code or expired OTP
**Fix**:
```bash
# Verify authenticator app time is synced
# Request new 2FA code (refreshes every 30 seconds)

# If persistent issues, reset 2FA
hitl reset-2fa --operator human-operator-001
# (Requires admin authorization)
```

---

## Success Criteria Summary

After completing all demos, verify:

### Functional Requirements
- ✅ Tier 0-4 requests can be submitted
- ✅ Approval, denial, defer, modify decisions work
- ✅ Batch approval processes multiple requests
- ✅ SLA timeout and escalation function correctly
- ✅ Delegation passes authority to other operators
- ✅ 2FA required for Tier 4 operations
- ✅ Agents receive decisions and modified parameters

### Non-Functional Requirements
- ✅ Notification channels deliver alerts (Desktop, Email, SMS)
- ✅ SLA countdowns accurate to the second
- ✅ CLI interface responsive (< 1 second for list/view)
- ✅ Audit logs complete and immutable
- ✅ No data loss on any operation
- ✅ System fails safe (deny on error/timeout)

### Constitution Compliance
- ✅ Principle II: All operations explicit and logged
- ✅ Principle III: HITL enforced for Tier 2+
- ✅ Principle IV: Skill composable (agents can integrate)
- ✅ Principle V: Decisions stored in vault memory
- ✅ Principle VI: Fail safe defaults (deny) work correctly

---

## Next Steps

1. **Run All Demos**: Execute demos 1-7 sequentially to validate functionality
2. **Review Logs**: Examine audit logs to verify completeness
3. **Test Edge Cases**: Run TEST-PLAN.md edge case scenarios
4. **Performance Test**: Submit 100+ requests to test batch processing
5. **Security Audit**: Verify 2FA, authorization, and fail-safe mechanisms
6. **User Training**: Share demos with operators for onboarding

---

**Last Updated**: 2026-02-16
**Version**: 1.0.0
**Status**: Ready for Testing

*For full specification, see SKILL.md. For comprehensive test plan, see TEST-PLAN.md.*
