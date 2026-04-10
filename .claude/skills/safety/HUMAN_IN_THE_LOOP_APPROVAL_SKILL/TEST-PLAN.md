# HUMAN_IN_THE_LOOP_APPROVAL_SKILL - Test Plan

**Status**: ✅ Specification Complete - Ready for Implementation
**Version**: 1.0.0
**Category**: Safety Skill
**Tier**: 0 (Read-only, provides approval for others)
**Priority**: CRITICAL (Foundation for all Tier 2+ skills)

---

## Purpose

This document defines a comprehensive testing strategy for the Human-in-the-Loop Approval System. Testing is organized into 6 levels with 100+ test cases covering functionality, integration, security, performance, and compliance.

**Testing Philosophy**: Since HITL is a CRITICAL safety foundation, testing must be exhaustive, automated where possible, and include failure injection to verify fail-safe behavior.

---

## Test Environment Setup

### Prerequisites

```bash
# 1. Install HITL skill (implementation required first)
pip install -e .claude/skills/safety/HUMAN_IN_THE_LOOP_APPROVAL_SKILL/

# 2. Set up test vault
cp -r obsidian-vault obsidian-vault-test
export VAULT_PATH="$(pwd)/obsidian-vault-test"

# 3. Configure test notification channels
cat > .hitl-test-config.yaml <<EOF
notifications:
  desktop:
    enabled: true
    test_mode: true  # Don't show real notifications
  email:
    enabled: true
    smtp_server: "smtp.test.local"
    test_mode: true  # Log instead of send
  sms:
    enabled: true
    provider: "test"
    test_mode: true  # Mock SMS delivery

logging:
  audit_path: "obsidian-vault-test/70-LOGS/approvals/"
  level: "DEBUG"
  test_mode: true

sla:
  tier0: 0        # Read-only, no SLA
  tier1: 0        # Low-risk, auto-approve
  tier2: 14400    # 4 hours (in test, use shorter times)
  tier3: 3600     # 1 hour
  tier4: 0        # Immediate
EOF

# 4. Verify test environment
hitl --config .hitl-test-config.yaml version
pytest --version
```

### Test Data Generation

```bash
# Create test dataset generator script
python .claude/skills/safety/HUMAN_IN_THE_LOOP_APPROVAL_SKILL/tests/generate_test_data.py

# Generates:
# - 20 valid requests (Tier 0-4)
# - 10 invalid requests (malformed, missing fields)
# - 5 edge case requests (boundary conditions)
# - 10 stress test requests (large payloads)
```

---

## Test Levels

### Level 1: Unit Tests (70+ tests)
**Scope**: Individual functions and components
**Duration**: ~15 minutes
**Coverage Target**: > 90%

### Level 2: Integration Tests (30+ tests)
**Scope**: Component interactions
**Duration**: ~30 minutes
**Coverage Target**: > 85%

### Level 3: System Tests (15+ tests)
**Scope**: End-to-end workflows
**Duration**: ~45 minutes
**Coverage Target**: All critical paths

### Level 4: Security Tests (10+ tests)
**Scope**: Authorization, authentication, fail-safe
**Duration**: ~30 minutes
**Coverage Target**: All security controls

### Level 5: Performance Tests (5+ tests)
**Scope**: Scalability, latency, resource usage
**Duration**: ~20 minutes
**Coverage Target**: All performance targets

### Level 6: Compliance Tests (5+ tests)
**Scope**: Constitution adherence, audit trail
**Duration**: ~15 minutes
**Coverage Target**: 100% (all principles)

---

## Level 1: Unit Tests

### 1.1 Request Validation (15 tests)

```python
# tests/unit/test_request_validation.py

def test_valid_tier0_request():
    """Valid Tier 0 read-only request"""
    request = {
        "agent_id": "test-agent",
        "operation": {"name": "read_file", "tier": 0},
        "context": {"action": "Read configuration", "reason": "Debug"},
        "details": {"file": "config.yaml"},
        "risk": {"tier": 0, "blast_radius": "none"}
    }
    assert validate_request(request) == True

def test_valid_tier4_critical_request():
    """Valid Tier 4 critical request with all required fields"""
    request = {
        "agent_id": "incident-bot",
        "operation": {"name": "database_rollback", "tier": 4},
        "context": {
            "action": "Emergency rollback",
            "reason": "Database corruption",
            "triggered_by": "incident-#1234",
            "timestamp": "2026-02-16T13:00:00Z"
        },
        "details": {
            "database": "production",
            "rollback_point": "2026-02-16T10:00:00Z"
        },
        "risk": {
            "tier": 4,
            "blast_radius": "CRITICAL - All users",
            "reversibility": "Cannot reverse",
            "data_exposure": "3 hours data loss",
            "cost": "High"
        }
    }
    assert validate_request(request) == True

def test_invalid_missing_agent_id():
    """Request missing required agent_id field"""
    request = {"operation": {"name": "test", "tier": 1}}
    with pytest.raises(ValidationError, match="agent_id is required"):
        validate_request(request)

def test_invalid_tier_out_of_range():
    """Request with invalid tier value"""
    request = {
        "agent_id": "test",
        "operation": {"name": "test", "tier": 5}  # Invalid: 0-4 only
    }
    with pytest.raises(ValidationError, match="tier must be 0-4"):
        validate_request(request)

def test_invalid_missing_risk_for_tier2():
    """Tier 2+ request missing required risk assessment"""
    request = {
        "agent_id": "test",
        "operation": {"name": "send_email", "tier": 2},
        "context": {"action": "Send email"}
        # Missing risk field
    }
    with pytest.raises(ValidationError, match="risk assessment required for tier >= 2"):
        validate_request(request)

def test_boundary_tier1_to_tier2():
    """Boundary test: Tier 1 should not require risk, Tier 2 should"""
    tier1_request = {
        "agent_id": "test",
        "operation": {"name": "organize_file", "tier": 1}
    }
    assert validate_request(tier1_request) == True  # No risk required

    tier2_request = {
        "agent_id": "test",
        "operation": {"name": "send_email", "tier": 2}
    }
    with pytest.raises(ValidationError):
        validate_request(tier2_request)  # Risk required

def test_request_id_uniqueness():
    """Request IDs must be unique UUIDs"""
    request = create_valid_request(tier=1)
    id1 = submit_request(request)
    id2 = submit_request(request)  # Same request content
    assert id1 != id2  # Different IDs generated
    assert is_valid_uuid(id1)
    assert is_valid_uuid(id2)

def test_request_checksum_generation():
    """Request checksum generated for integrity verification"""
    request = create_valid_request(tier=2)
    submitted = submit_request(request)
    assert submitted.checksum is not None
    assert submitted.checksum.startswith("sha256:")
    assert len(submitted.checksum) == 71  # "sha256:" + 64 hex chars

def test_request_timestamp_utc():
    """Request timestamps must be UTC"""
    request = create_valid_request(tier=1)
    submitted = submit_request(request)
    timestamp = datetime.fromisoformat(submitted.timestamp)
    assert timestamp.tzinfo == timezone.utc

# ... 6 more validation tests
```

### 1.2 SLA Calculation (10 tests)

```python
# tests/unit/test_sla.py

def test_tier0_no_sla():
    """Tier 0 operations have no SLA"""
    request = create_valid_request(tier=0)
    sla = calculate_sla(request)
    assert sla.required_by is None
    assert sla.escalation_at is None
    assert sla.timeout_action is None

def test_tier1_no_sla():
    """Tier 1 operations have no SLA (auto-approve)"""
    request = create_valid_request(tier=1)
    sla = calculate_sla(request)
    assert sla.required_by is None

def test_tier2_4hour_sla():
    """Tier 2 operations have 4-hour SLA"""
    request = create_valid_request(tier=2)
    submitted_at = datetime(2026, 2, 16, 12, 0, 0, tzinfo=timezone.utc)
    sla = calculate_sla(request, submitted_at=submitted_at)

    expected_expiry = submitted_at + timedelta(hours=4)
    assert sla.required_by == expected_expiry
    assert sla.required_by == datetime(2026, 2, 16, 16, 0, 0, tzinfo=timezone.utc)

def test_tier3_1hour_sla():
    """Tier 3 operations have 1-hour SLA"""
    request = create_valid_request(tier=3)
    submitted_at = datetime(2026, 2, 16, 12, 0, 0, tzinfo=timezone.utc)
    sla = calculate_sla(request, submitted_at=submitted_at)

    expected_expiry = submitted_at + timedelta(hours=1)
    assert sla.required_by == expected_expiry

def test_tier4_immediate_no_timeout():
    """Tier 4 operations require immediate decision (no timeout)"""
    request = create_valid_request(tier=4)
    sla = calculate_sla(request)
    assert sla.required_by is None  # No timeout
    assert sla.timeout_action is None  # Cannot timeout

def test_escalation_point_half_sla():
    """Escalation triggers at 50% of SLA time"""
    request = create_valid_request(tier=2)  # 4-hour SLA
    submitted_at = datetime(2026, 2, 16, 12, 0, 0, tzinfo=timezone.utc)
    sla = calculate_sla(request, submitted_at=submitted_at)

    expected_escalation = submitted_at + timedelta(hours=2)  # 50% of 4 hours
    assert sla.escalation_at == expected_escalation

def test_sla_custom_override():
    """Custom SLA can override default tier SLA"""
    request = create_valid_request(tier=2)
    request["sla_override"] = 1800  # 30 minutes
    submitted_at = datetime(2026, 2, 16, 12, 0, 0, tzinfo=timezone.utc)
    sla = calculate_sla(request, submitted_at=submitted_at)

    expected_expiry = submitted_at + timedelta(seconds=1800)
    assert sla.required_by == expected_expiry

def test_sla_timeout_default_action_deny():
    """Default timeout action is deny (fail-safe)"""
    request = create_valid_request(tier=2)
    sla = calculate_sla(request)
    assert sla.timeout_action == "deny"

def test_sla_remaining_time():
    """Calculate remaining SLA time accurately"""
    request = create_valid_request(tier=2)  # 4-hour SLA
    submitted_at = datetime(2026, 2, 16, 12, 0, 0, tzinfo=timezone.utc)
    current_time = datetime(2026, 2, 16, 14, 0, 0, tzinfo=timezone.utc)  # 2 hours later

    sla = calculate_sla(request, submitted_at=submitted_at)
    remaining = sla.remaining_time(current_time=current_time)

    assert remaining == timedelta(hours=2)  # 2 hours remaining

def test_sla_expired():
    """Detect SLA expiration accurately"""
    request = create_valid_request(tier=2)
    submitted_at = datetime(2026, 2, 16, 12, 0, 0, tzinfo=timezone.utc)
    current_time = datetime(2026, 2, 16, 17, 0, 0, tzinfo=timezone.utc)  # 5 hours later

    sla = calculate_sla(request, submitted_at=submitted_at)
    assert sla.is_expired(current_time=current_time) == True
```

### 1.3 Decision Processing (15 tests)

```python
# tests/unit/test_decision.py

def test_approve_decision():
    """Approve decision sets correct status"""
    request = create_and_submit_request(tier=2)
    decision = process_decision(
        request_id=request.id,
        action="approve",
        operator="operator-001",
        comment="Looks good"
    )
    assert decision.action == "APPROVED"
    assert decision.operator == "operator-001"
    assert decision.comment == "Looks good"
    assert decision.timestamp is not None

def test_deny_decision():
    """Deny decision blocks operation"""
    request = create_and_submit_request(tier=2)
    decision = process_decision(
        request_id=request.id,
        action="deny",
        operator="operator-001",
        reason="Insufficient justification"
    )
    assert decision.action == "DENIED"
    assert decision.reason == "Insufficient justification"
    assert request.status == "DENIED"

def test_defer_decision():
    """Defer decision extends SLA"""
    request = create_and_submit_request(tier=2)  # 4-hour SLA
    original_sla = request.sla.required_by

    decision = process_decision(
        request_id=request.id,
        action="defer",
        operator="operator-001",
        extend_seconds=3600  # 1-hour extension
    )

    assert decision.action == "DEFERRED"
    assert request.sla.required_by == original_sla + timedelta(seconds=3600)
    assert request.status == "PENDING"  # Still pending, just extended

def test_modify_decision():
    """Modify decision changes parameters and approves"""
    request = create_and_submit_request(tier=2)
    original_details = request.details.copy()

    modifications = {
        "recipient": "beta-users@company.com",  # Changed from all-users
        "estimated_reach": 100  # Changed from 10000
    }

    decision = process_decision(
        request_id=request.id,
        action="modify",
        operator="operator-001",
        modifications=modifications,
        approve_after_modify=True
    )

    assert decision.action == "APPROVED"
    assert decision.modifications == modifications
    assert request.details["recipient"] == "beta-users@company.com"
    assert request.details["estimated_reach"] == 100
    assert request.original_details == original_details  # Original preserved

def test_timeout_decision():
    """SLA timeout automatically denies request"""
    request = create_and_submit_request(tier=2)

    # Simulate time passing beyond SLA
    future_time = request.sla.required_by + timedelta(seconds=1)
    decision = process_sla_timeout(request, current_time=future_time)

    assert decision.action == "DENIED"
    assert decision.operator == "SYSTEM"
    assert "timeout" in decision.reason.lower()
    assert request.status == "DENIED"

def test_decision_idempotency():
    """Cannot make multiple decisions on same request"""
    request = create_and_submit_request(tier=2)

    # First decision
    decision1 = process_decision(request.id, "approve", "operator-001")
    assert decision1.action == "APPROVED"

    # Second decision should fail
    with pytest.raises(DecisionError, match="already decided"):
        process_decision(request.id, "deny", "operator-002")

def test_decision_checksum():
    """Decision generates integrity checksum"""
    request = create_and_submit_request(tier=2)
    decision = process_decision(request.id, "approve", "operator-001")

    assert decision.checksum is not None
    assert decision.checksum.startswith("sha256:")

    # Verify checksum includes all critical fields
    expected_data = f"{decision.action}{decision.operator}{decision.timestamp}"
    expected_checksum = f"sha256:{hashlib.sha256(expected_data.encode()).hexdigest()}"
    assert decision.checksum == expected_checksum

# ... 8 more decision tests
```

### 1.4 Notification System (10 tests)

```python
# tests/unit/test_notifications.py

def test_desktop_notification_tier2():
    """Desktop notification sent for Tier 2 request"""
    request = create_and_submit_request(tier=2)
    notifications = get_sent_notifications(request.id)

    desktop_notifications = [n for n in notifications if n.channel == "desktop"]
    assert len(desktop_notifications) == 1
    assert "Medium Risk" in desktop_notifications[0].content

def test_email_notification_tier2():
    """Email notification sent for Tier 2 request"""
    request = create_and_submit_request(tier=2)
    notifications = get_sent_notifications(request.id)

    email_notifications = [n for n in notifications if n.channel == "email"]
    assert len(email_notifications) == 1
    assert email_notifications[0].recipient == config.operator_email

def test_sms_notification_tier3():
    """SMS notification sent for Tier 3 request"""
    request = create_and_submit_request(tier=3)
    notifications = get_sent_notifications(request.id)

    sms_notifications = [n for n in notifications if n.channel == "sms"]
    assert len(sms_notifications) == 1
    assert "HIGH RISK" in sms_notifications[0].content

def test_all_channels_tier4():
    """All notification channels activated for Tier 4"""
    request = create_and_submit_request(tier=4)
    notifications = get_sent_notifications(request.id)

    channels = {n.channel for n in notifications}
    assert "desktop" in channels
    assert "email" in channels
    assert "sms" in channels
    # Phone call if configured

def test_escalation_notification():
    """Escalation triggers additional notification"""
    request = create_and_submit_request(tier=2, sla_override=600)  # 10-min SLA

    # Simulate time passing to escalation point (50% = 5 minutes)
    future_time = request.submitted_at + timedelta(seconds=300)
    process_escalation_check(request, current_time=future_time)

    notifications = get_sent_notifications(request.id)
    escalation_notifications = [n for n in notifications if "escalation" in n.content.lower()]
    assert len(escalation_notifications) >= 1

def test_notification_rate_limiting():
    """Rate limiting prevents notification spam"""
    # Submit 10 requests in rapid succession
    requests = [create_and_submit_request(tier=2) for _ in range(10)]

    # Check rate limiting engaged
    rate_limit_status = get_rate_limit_status()
    assert rate_limit_status.limited == True
    assert rate_limit_status.requests_queued > 0

def test_notification_retry_on_failure():
    """Failed notifications are retried"""
    with mock_notification_failure(channel="email"):
        request = create_and_submit_request(tier=2)

    # Check retry attempted
    notifications = get_sent_notifications(request.id, include_retries=True)
    email_attempts = [n for n in notifications if n.channel == "email"]
    assert len(email_attempts) > 1  # Original + retry

# ... 3 more notification tests
```

### 1.5 Audit Logging (10 tests)

```python
# tests/unit/test_audit_logging.py

def test_request_submission_logged():
    """Request submission creates audit log entry"""
    request = create_and_submit_request(tier=2)
    log_entries = read_audit_log(request.id)

    submission_entry = log_entries[0]
    assert "REQUEST_SUBMITTED" in submission_entry
    assert request.id in submission_entry
    assert request.agent_id in submission_entry

def test_decision_logged():
    """Decision creates audit log entry"""
    request = create_and_submit_request(tier=2)
    decision = process_decision(request.id, "approve", "operator-001")

    log_entries = read_audit_log(request.id)
    decision_entry = [e for e in log_entries if "DECISION_RECORDED" in e][0]

    assert "APPROVED" in decision_entry
    assert "operator-001" in decision_entry
    assert decision.timestamp.isoformat() in decision_entry

def test_audit_log_immutability():
    """Audit logs cannot be modified after creation"""
    request = create_and_submit_request(tier=2)
    log_path = get_audit_log_path(request.id)

    # Get original checksum
    with open(log_path, 'rb') as f:
        original_checksum = hashlib.sha256(f.read()).hexdigest()

    # Attempt to modify (should fail or be detected)
    try:
        with open(log_path, 'a') as f:
            f.write("\n[TAMPERED] Fake entry")
    except PermissionError:
        pass  # Expected: file should be read-only

    # Verify checksum changed (tampering detected) or write prevented
    with open(log_path, 'rb') as f:
        current_checksum = hashlib.sha256(f.read()).hexdigest()

    # Either tampering detected or write prevented
    assert current_checksum == original_checksum or verify_log_integrity(log_path) == False

def test_audit_log_checksum_chain():
    """Audit log entries form cryptographic chain"""
    request = create_and_submit_request(tier=2)
    process_decision(request.id, "approve", "operator-001")

    log_entries = parse_audit_log(request.id)

    # Verify each entry references previous entry's checksum
    for i in range(1, len(log_entries)):
        prev_checksum = log_entries[i-1].checksum
        current_prev_ref = log_entries[i].previous_checksum
        assert current_prev_ref == prev_checksum

def test_audit_log_retention():
    """Audit logs retained indefinitely (never deleted)"""
    request = create_and_submit_request(tier=2)
    log_path = get_audit_log_path(request.id)

    # Simulate cleanup/maintenance operations
    run_maintenance_cleanup()

    # Verify log still exists
    assert os.path.exists(log_path)

# ... 5 more audit logging tests
```

### 1.6 CLI Interface (10 tests)

```python
# tests/unit/test_cli.py

def test_cli_list_pending():
    """CLI list shows pending requests"""
    request = create_and_submit_request(tier=2)
    result = run_cli(["hitl", "list", "--status", "pending"])

    assert result.exit_code == 0
    assert request.id in result.output
    assert "PENDING" in result.output

def test_cli_view_request():
    """CLI view shows full request details"""
    request = create_and_submit_request(tier=2)
    result = run_cli(["hitl", "view", request.id])

    assert result.exit_code == 0
    assert request.agent_id in result.output
    assert request.operation.name in result.output
    assert "Tier: 2" in result.output

def test_cli_approve_request():
    """CLI approve command processes approval"""
    request = create_and_submit_request(tier=2)
    result = run_cli([
        "hitl", "approve", request.id,
        "--comment", "Test approval"
    ])

    assert result.exit_code == 0
    assert "approved successfully" in result.output.lower()

    # Verify decision recorded
    decision = get_decision(request.id)
    assert decision.action == "APPROVED"
    assert decision.comment == "Test approval"

def test_cli_deny_request():
    """CLI deny command blocks operation"""
    request = create_and_submit_request(tier=2)
    result = run_cli([
        "hitl", "deny", request.id,
        "--reason", "Test denial"
    ])

    assert result.exit_code == 0
    assert "denied successfully" in result.output.lower()

    decision = get_decision(request.id)
    assert decision.action == "DENIED"

def test_cli_batch_approve():
    """CLI batch approve processes multiple requests"""
    requests = [create_and_submit_request(tier=1) for _ in range(5)]

    result = run_cli([
        "hitl", "batch-approve",
        "--agent", "test-agent",
        "--tier", "1"
    ])

    assert result.exit_code == 0
    assert "5" in result.output  # 5 requests approved

    # Verify all approved
    for req in requests:
        decision = get_decision(req.id)
        assert decision.action == "APPROVED"

# ... 5 more CLI tests
```

---

## Level 2: Integration Tests

### 2.1 Agent Integration (10 tests)

```python
# tests/integration/test_agent_integration.py

def test_agent_submit_and_wait():
    """Agent submits request and waits for decision"""
    # Simulate agent behavior
    agent_id = "test-email-agent"

    # Agent submits request
    request_id = submit_approval_request(
        agent_id=agent_id,
        operation="send_email",
        tier=2,
        details={"recipient": "test@example.com"}
    )

    # Simulate human approval in background
    def approve_in_background():
        time.sleep(2)  # Simulate human review time
        hitl_cli_approve(request_id, operator="operator-001")

    threading.Thread(target=approve_in_background, daemon=True).start()

    # Agent waits for decision (blocking)
    decision = wait_for_decision(request_id, timeout=10)

    assert decision.approved == True
    assert decision.request_id == request_id

def test_agent_polling():
    """Agent polls for decision status"""
    request_id = submit_approval_request(
        agent_id="test-agent",
        operation="test_op",
        tier=2
    )

    # Agent polls (non-blocking)
    decision = check_decision_status(request_id)
    assert decision.status == "PENDING"

    # Approve request
    hitl_cli_approve(request_id, operator="operator-001")

    # Agent polls again
    decision = check_decision_status(request_id)
    assert decision.status == "APPROVED"

def test_agent_receives_modified_parameters():
    """Agent receives modified parameters after approval"""
    request_id = submit_approval_request(
        agent_id="test-agent",
        operation="send_email",
        tier=2,
        details={"recipient": "all-users@company.com", "count": 10000}
    )

    # Human modifies and approves
    hitl_cli_modify_and_approve(
        request_id,
        modifications={"recipient": "beta-users@company.com", "count": 100},
        operator="operator-001"
    )

    # Agent retrieves decision
    decision = get_decision(request_id)

    assert decision.approved == True
    assert decision.modified == True
    assert decision.modified_parameters["recipient"] == "beta-users@company.com"
    assert decision.modified_parameters["count"] == 100

def test_agent_blocked_on_denial():
    """Agent blocked when request denied"""
    request_id = submit_approval_request(
        agent_id="test-agent",
        operation="delete_data",
        tier=3
    )

    # Human denies
    hitl_cli_deny(request_id, reason="Insufficient justification", operator="operator-001")

    # Agent checks decision
    decision = get_decision(request_id)

    assert decision.approved == False
    assert decision.status == "DENIED"
    assert "Insufficient justification" in decision.reason

# ... 6 more agent integration tests
```

### 2.2 Notification Integration (8 tests)

```python
# tests/integration/test_notification_integration.py

def test_end_to_end_desktop_notification():
    """Desktop notification delivered and clickable"""
    request = create_and_submit_request(tier=2)

    # Verify notification appeared
    notifications = get_desktop_notifications()
    request_notifications = [n for n in notifications if request.id in n.data]
    assert len(request_notifications) == 1

    # Simulate clicking notification
    click_notification(request_notifications[0])

    # Verify opens request details
    assert get_active_cli_view() == request.id

def test_email_notification_with_action_links():
    """Email notification contains action links"""
    request = create_and_submit_request(tier=2)

    # Get sent email
    emails = get_sent_test_emails()
    request_email = [e for e in emails if request.id in e.body][0]

    # Verify action links present
    assert f"approve/{request.id}" in request_email.body
    assert f"deny/{request.id}" in request_email.body
    assert f"view/{request.id}" in request_email.body

def test_sms_notification_concise():
    """SMS notification concise (< 160 chars)"""
    request = create_and_submit_request(tier=3)

    # Get sent SMS
    sms_messages = get_sent_test_sms()
    request_sms = [s for s in sms_messages if request.id[:8] in s.body][0]

    # Verify concise format
    assert len(request_sms.body) <= 160
    assert request.operation.name in request_sms.body
    assert "HIGH RISK" in request_sms.body

# ... 5 more notification integration tests
```

### 2.3 Logging Integration (7 tests)

```python
# tests/integration/test_logging_integration.py

def test_full_lifecycle_logged():
    """Complete request lifecycle logged"""
    request = create_and_submit_request(tier=2)

    # Submit, escalate, decide, execute
    time.sleep(2)  # Wait for potential escalation
    process_decision(request.id, "approve", "operator-001")
    execute_operation(request.id)  # Simulate agent execution

    # Read log
    log_entries = read_audit_log(request.id)

    # Verify all events logged
    event_types = [entry.split(":")[1].strip().split()[0] for entry in log_entries]
    assert "REQUEST_SUBMITTED" in event_types
    assert "NOTIFICATION_SENT" in event_types
    assert "DECISION_RECORDED" in event_types
    assert "AGENT_NOTIFIED" in event_types
    assert "OPERATION_EXECUTED" in event_types

def test_log_searchability():
    """Logs searchable by agent, operation, tier, date"""
    # Create diverse requests
    create_and_submit_request(tier=1, agent_id="agent-A", operation="op1")
    create_and_submit_request(tier=2, agent_id="agent-B", operation="op2")
    create_and_submit_request(tier=3, agent_id="agent-A", operation="op3")

    # Search by agent
    agent_a_logs = search_audit_logs(agent_id="agent-A")
    assert len(agent_a_logs) == 2

    # Search by tier
    tier2_logs = search_audit_logs(tier=2)
    assert len(tier2_logs) >= 1

    # Search by operation
    op1_logs = search_audit_logs(operation="op1")
    assert len(op1_logs) >= 1

# ... 5 more logging integration tests
```

### 2.4 Workflow Integration (5 tests)

```python
# tests/integration/test_workflow_integration.py

def test_filesystem_skill_integration():
    """HITL integrates with filesystem automation skill"""
    # Filesystem skill submits Tier 1 request
    request_id = filesystem_skill_request_approval(
        operation="organize_file",
        source="vault/file.md",
        destination="vault/80-MEMORY/file.md"
    )

    # Tier 1 auto-approved
    decision = get_decision(request_id)
    assert decision.approved == True
    assert decision.auto_approved == True

    # Filesystem skill executes
    result = filesystem_skill_execute(request_id, decision)
    assert result.success == True

def test_multi_agent_coordination():
    """Multiple agents can have pending requests simultaneously"""
    request_1 = submit_approval_request(agent_id="agent-1", operation="op1", tier=2)
    request_2 = submit_approval_request(agent_id="agent-2", operation="op2", tier=2)
    request_3 = submit_approval_request(agent_id="agent-3", operation="op3", tier=2)

    # All pending
    pending = list_pending_requests()
    assert len(pending) >= 3

    # Approve selectively
    approve_request(request_1)
    deny_request(request_2)
    # Leave request_3 pending

    # Verify independent decisions
    assert get_decision(request_1).approved == True
    assert get_decision(request_2).approved == False
    assert get_decision_status(request_3) == "PENDING"

# ... 3 more workflow integration tests
```

---

## Level 3: System Tests

### 3.1 End-to-End Scenarios (5 tests)

```python
# tests/system/test_e2e_scenarios.py

def test_complete_tier2_approval_workflow():
    """Complete Tier 2 workflow from submission to execution"""
    # 1. Agent submits request
    request_id = agent_submit_approval(
        agent="email-sender",
        operation="send_email",
        tier=2,
        recipient="client@example.com"
    )

    # 2. Notifications sent
    time.sleep(1)
    notifications = get_all_notifications(request_id)
    assert len(notifications) >= 2  # Desktop + Email

    # 3. Human reviews via CLI
    cli_result = run_cli(["hitl", "view", request_id])
    assert cli_result.exit_code == 0

    # 4. Human approves
    cli_result = run_cli(["hitl", "approve", request_id, "--comment", "Approved"])
    assert cli_result.exit_code == 0

    # 5. Agent notified
    agent_notification = wait_for_agent_notification(request_id, timeout=5)
    assert agent_notification.decision == "APPROVED"

    # 6. Agent executes
    execution_result = agent_execute_operation(request_id)
    assert execution_result.success == True

    # 7. Verify full audit trail
    audit_log = read_complete_audit_log(request_id)
    assert "REQUEST_SUBMITTED" in audit_log
    assert "DECISION_RECORDED: APPROVED" in audit_log
    assert "OPERATION_EXECUTED" in audit_log

def test_complete_tier3_denial_workflow():
    """Complete Tier 3 workflow ending in denial"""
    # Submit high-risk request
    request_id = agent_submit_approval(
        agent="database-admin",
        operation="delete_records",
        tier=3,
        details={"table": "customers", "count": 500}
    )

    # Verify all notification channels
    time.sleep(1)
    notifications = get_all_notifications(request_id)
    channels = {n.channel for n in notifications}
    assert "desktop" in channels
    assert "email" in channels
    assert "sms" in channels

    # Human denies
    cli_result = run_cli([
        "hitl", "deny", request_id,
        "--reason", "Manual audit required before deletion"
    ])
    assert cli_result.exit_code == 0

    # Agent attempts execution (should be blocked)
    with pytest.raises(OperationBlockedError):
        agent_execute_operation(request_id)

    # Verify denial logged
    audit_log = read_complete_audit_log(request_id)
    assert "DECISION_RECORDED: DENIED" in audit_log
    assert "Manual audit required" in audit_log

def test_complete_tier4_critical_workflow():
    """Complete Tier 4 critical workflow with 2FA"""
    # Submit critical request
    request_id = agent_submit_approval(
        agent="incident-bot",
        operation="database_rollback",
        tier=4,
        details={"rollback_point": "2026-02-16T10:00:00Z"}
    )

    # Verify immediate notifications (all channels)
    time.sleep(1)
    notifications = get_all_notifications(request_id)
    assert len(notifications) >= 4  # Desktop, Email, SMS, Phone

    # 2FA required
    with pytest.raises(TwoFactorRequiredError):
        run_cli(["hitl", "view", request_id])  # Without 2FA

    # View with 2FA
    cli_result = run_cli(["hitl", "view", request_id, "--2fa", "123456"])
    assert cli_result.exit_code == 0

    # Approve with 2FA
    cli_result = run_cli([
        "hitl", "approve", request_id,
        "--2fa", "123456",
        "--comment", "Emergency rollback approved"
    ])
    assert cli_result.exit_code == 0

    # Agent executes critical operation
    execution_result = agent_execute_operation(request_id)
    assert execution_result.success == True

    # Verify 2FA in audit log
    audit_log = read_complete_audit_log(request_id)
    assert "2FA_VERIFICATION: SUCCESS" in audit_log
    assert "DECISION_RECORDED: APPROVED" in audit_log

# ... 2 more E2E scenarios
```

### 3.2 Failure Recovery (5 tests)

```python
# tests/system/test_failure_recovery.py

def test_recover_from_notification_failure():
    """System recovers when notification delivery fails"""
    # Mock notification failure
    with mock.patch('send_desktop_notification', side_effect=Exception("Notification service down")):
        request_id = create_and_submit_request(tier=2)

    # Request should still be created
    request = get_request(request_id)
    assert request.status == "PENDING"

    # Retry notification (manual or automatic)
    retry_failed_notifications(request_id)

    # Verify notification eventually delivered
    notifications = get_all_notifications(request_id)
    assert len(notifications) >= 1

def test_recover_from_log_write_failure():
    """System fails safe when audit log write fails"""
    # Mock log write failure
    with mock.patch('write_audit_log', side_effect=Exception("Disk full")):
        with pytest.raises(AuditLogError):
            create_and_submit_request(tier=2)

    # Request should NOT be created (fail-safe)
    # Cannot accept requests if audit logging fails

def test_recover_from_sla_timer_failure():
    """SLA timer failure fails safe (deny on timeout)"""
    request_id = create_and_submit_request(tier=2, sla_override=5)  # 5-second SLA

    # Simulate SLA timer crash
    stop_sla_timer_service()

    time.sleep(6)  # SLA expired

    # Restart timer service
    start_sla_timer_service()

    # Verify timeout processed correctly
    request = get_request(request_id)
    assert request.status == "DENIED"  # Fail-safe: timeout denies

# ... 2 more failure recovery tests
```

### 3.3 Concurrency Tests (5 tests)

```python
# tests/system/test_concurrency.py

def test_concurrent_request_submissions():
    """Handle 100 concurrent request submissions"""
    import concurrent.futures

    def submit_request(i):
        return create_and_submit_request(tier=2, agent_id=f"agent-{i}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(submit_request, i) for i in range(100)]
        request_ids = [f.result().id for f in futures]

    # Verify all 100 created
    assert len(request_ids) == 100
    assert len(set(request_ids)) == 100  # All unique

    # Verify all pending
    pending = list_pending_requests()
    assert len(pending) >= 100

def test_concurrent_approvals():
    """Handle concurrent approval decisions"""
    # Create 10 pending requests
    request_ids = [create_and_submit_request(tier=2).id for _ in range(10)]

    # Approve all concurrently
    def approve(req_id):
        return process_decision(req_id, "approve", "operator-001")

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(approve, req_id) for req_id in request_ids]
        decisions = [f.result() for f in futures]

    # Verify all approved
    assert all(d.action == "APPROVED" for d in decisions)

# ... 3 more concurrency tests
```

---

## Level 4: Security Tests

### 4.1 Authorization Tests (5 tests)

```python
# tests/security/test_authorization.py

def test_unauthorized_operator_cannot_approve():
    """Unauthorized operator blocked from approving"""
    request_id = create_and_submit_request(tier=2)

    # Attempt approval with unauthorized operator
    with pytest.raises(AuthorizationError):
        process_decision(
            request_id,
            "approve",
            operator="unauthorized-user"  # Not in authorized operators list
        )

    # Verify request still pending
    request = get_request(request_id)
    assert request.status == "PENDING"

def test_tier4_requires_elevated_permissions():
    """Tier 4 approval requires elevated operator permissions"""
    request_id = create_and_submit_request(tier=4)

    # Standard operator cannot approve Tier 4
    with pytest.raises(InsufficientPermissionsError):
        process_decision(request_id, "approve", operator="standard-operator")

    # Elevated operator can approve
    decision = process_decision(request_id, "approve", operator="admin-operator")
    assert decision.action == "APPROVED"

def test_2fa_required_for_tier4():
    """2FA mandatory for Tier 4 operations"""
    request_id = create_and_submit_request(tier=4)

    # Approve without 2FA fails
    with pytest.raises(TwoFactorRequiredError):
        process_decision(request_id, "approve", operator="admin-operator")

    # Approve with 2FA succeeds
    decision = process_decision(
        request_id,
        "approve",
        operator="admin-operator",
        two_factor_code="123456"
    )
    assert decision.action == "APPROVED"

# ... 2 more authorization tests
```

### 4.2 Fail-Safe Tests (5 tests)

```python
# tests/security/test_fail_safe.py

def test_fail_safe_on_unknown_error():
    """Unknown errors fail safe (deny request)"""
    request_id = create_and_submit_request(tier=2)

    # Inject unknown error during decision processing
    with mock.patch('validate_decision_internal', side_effect=Exception("Unknown error")):
        with pytest.raises(DecisionError):
            process_decision(request_id, "approve", "operator-001")

    # Verify request denied (fail-safe)
    request = get_request(request_id)
    assert request.status == "DENIED"
    assert "error" in request.failure_reason.lower()

def test_fail_safe_on_timeout():
    """Timeout fails safe (deny)"""
    request_id = create_and_submit_request(tier=2, sla_override=1)  # 1-second SLA

    time.sleep(2)  # SLA expired

    # Check timeout processed with fail-safe
    request = get_request(request_id)
    assert request.status == "DENIED"
    assert "timeout" in request.denial_reason.lower()

def test_fail_safe_on_invalid_modification():
    """Invalid modifications fail safe (deny)"""
    request_id = create_and_submit_request(tier=2)

    # Attempt invalid modification
    with pytest.raises(ValidationError):
        process_decision(
            request_id,
            "modify",
            operator="operator-001",
            modifications={"invalid_field": "value"}  # Field doesn't exist
        )

    # Verify request still pending (not approved with invalid modification)
    request = get_request(request_id)
    assert request.status == "PENDING"

# ... 2 more fail-safe tests
```

---

## Level 5: Performance Tests

### 5.1 Latency Tests (3 tests)

```python
# tests/performance/test_latency.py

def test_request_submission_latency():
    """Request submission completes in < 100ms"""
    start = time.time()
    request_id = create_and_submit_request(tier=2)
    duration = time.time() - start

    assert duration < 0.1  # < 100ms
    assert request_id is not None

def test_cli_list_latency():
    """CLI list command responds in < 500ms with 100 requests"""
    # Create 100 pending requests
    for _ in range(100):
        create_and_submit_request(tier=2)

    start = time.time()
    result = run_cli(["hitl", "list", "--status", "pending"])
    duration = time.time() - start

    assert result.exit_code == 0
    assert duration < 0.5  # < 500ms

def test_decision_processing_latency():
    """Decision processing completes in < 200ms"""
    request_id = create_and_submit_request(tier=2)

    start = time.time()
    decision = process_decision(request_id, "approve", "operator-001")
    duration = time.time() - start

    assert duration < 0.2  # < 200ms
    assert decision.action == "APPROVED"
```

### 5.2 Throughput Tests (2 tests)

```python
# tests/performance/test_throughput.py

def test_sustained_request_rate():
    """System handles 10 requests/second sustained for 1 minute"""
    start = time.time()
    request_count = 0

    while time.time() - start < 60:  # 1 minute
        create_and_submit_request(tier=1)
        request_count += 1
        time.sleep(0.1)  # 10 requests/second

    # Verify all created
    assert request_count >= 600  # ~10 req/sec * 60 sec
    pending = list_pending_requests()
    assert len(pending) >= 600

def test_batch_approval_throughput():
    """Batch approval processes 100 requests in < 5 seconds"""
    # Create 100 Tier 1 requests
    for _ in range(100):
        create_and_submit_request(tier=1)

    start = time.time()
    batch_approve_all(tier=1, operator="operator-001")
    duration = time.time() - start

    assert duration < 5.0  # < 5 seconds for 100 requests
```

---

## Level 6: Compliance Tests

### 6.1 Constitution Compliance (5 tests)

```python
# tests/compliance/test_constitution.py

def test_principle_ii_explicit_logging():
    """Principle II: All operations explicitly logged"""
    request_id = create_and_submit_request(tier=2)
    process_decision(request_id, "approve", "operator-001")

    # Verify every action logged
    audit_log = read_complete_audit_log(request_id)

    assert "REQUEST_SUBMITTED" in audit_log
    assert "NOTIFICATION_SENT" in audit_log
    assert "DECISION_RECORDED" in audit_log
    assert "AGENT_NOTIFIED" in audit_log

def test_principle_iii_hitl_enforcement():
    """Principle III: HITL enforced for Tier 2+"""
    # Tier 0-1: No HITL required (auto-approve)
    tier0_request = create_and_submit_request(tier=0)
    assert get_decision(tier0_request.id).auto_approved == True

    tier1_request = create_and_submit_request(tier=1)
    assert get_decision(tier1_request.id).auto_approved == True

    # Tier 2+: HITL required
    tier2_request = create_and_submit_request(tier=2)
    assert get_request(tier2_request.id).status == "PENDING"  # Awaiting human

    tier3_request = create_and_submit_request(tier=3)
    assert get_request(tier3_request.id).status == "PENDING"

def test_principle_vi_fail_safe():
    """Principle VI: System fails safe (deny on error)"""
    request_id = create_and_submit_request(tier=2)

    # Inject error
    with mock.patch('finalize_decision', side_effect=Exception("Simulated error")):
        with pytest.raises(DecisionError):
            process_decision(request_id, "approve", "operator-001")

    # Verify fail-safe: request denied (not approved despite error)
    request = get_request(request_id)
    assert request.status == "DENIED" or request.status == "PENDING"  # Not APPROVED

def test_vault_governance_logs_in_vault():
    """Vault Governance: All logs stored in vault"""
    request_id = create_and_submit_request(tier=2)
    log_path = get_audit_log_path(request_id)

    # Verify log path is within vault
    assert "obsidian-vault" in log_path
    assert "70-LOGS/approvals/" in log_path
    assert os.path.exists(log_path)

def test_audit_immutability():
    """Logging Requirements: Audit logs immutable"""
    request_id = create_and_submit_request(tier=2)
    log_path = get_audit_log_path(request_id)

    # Calculate original checksum
    original_checksum = calculate_file_checksum(log_path)

    # Wait and verify checksum unchanged
    time.sleep(2)
    current_checksum = calculate_file_checksum(log_path)
    assert current_checksum == original_checksum

    # Verify file permissions are read-only (or tampering detected)
    file_stat = os.stat(log_path)
    assert file_stat.st_mode & 0o200 == 0  # Write bit not set
```

---

## Test Execution Schedule

### Day 1: Unit Tests (6 hours)
```bash
# Morning: Core functionality (4 hours)
pytest tests/unit/test_request_validation.py -v
pytest tests/unit/test_sla.py -v
pytest tests/unit/test_decision.py -v

# Afternoon: Infrastructure (2 hours)
pytest tests/unit/test_notifications.py -v
pytest tests/unit/test_audit_logging.py -v
pytest tests/unit/test_cli.py -v

# Metrics
# Expected: 70+ tests pass, 0 failures, > 90% coverage
```

### Day 2: Integration Tests (4 hours)
```bash
# Morning: Agent & Notification Integration (2 hours)
pytest tests/integration/test_agent_integration.py -v
pytest tests/integration/test_notification_integration.py -v

# Afternoon: Logging & Workflow Integration (2 hours)
pytest tests/integration/test_logging_integration.py -v
pytest tests/integration/test_workflow_integration.py -v

# Metrics
# Expected: 30+ tests pass, end-to-end flows validated
```

### Day 3: System & Security Tests (5 hours)
```bash
# Morning: System Tests (3 hours)
pytest tests/system/test_e2e_scenarios.py -v
pytest tests/system/test_failure_recovery.py -v
pytest tests/system/test_concurrency.py -v

# Afternoon: Security Tests (2 hours)
pytest tests/security/test_authorization.py -v
pytest tests/security/test_fail_safe.py -v

# Metrics
# Expected: All E2E scenarios pass, security controls validated
```

### Day 4: Performance & Compliance Tests (3 hours)
```bash
# Morning: Performance Tests (1.5 hours)
pytest tests/performance/test_latency.py -v
pytest tests/performance/test_throughput.py -v

# Afternoon: Compliance Tests (1.5 hours)
pytest tests/compliance/test_constitution.py -v

# Metrics
# Expected: Latency < targets, 100% constitution compliance
```

---

## Test Coverage Report

### Coverage Targets

| Component | Line Coverage | Branch Coverage | Critical Paths |
|-----------|--------------|-----------------|----------------|
| Request Validation | > 95% | > 90% | 100% |
| SLA Calculation | > 90% | > 85% | 100% |
| Decision Processing | > 95% | > 90% | 100% |
| Notification System | > 85% | > 80% | 100% |
| Audit Logging | > 95% | > 90% | 100% |
| CLI Interface | > 85% | > 80% | N/A |
| **Overall** | **> 90%** | **> 85%** | **100%** |

### Generate Coverage Report

```bash
# Run all tests with coverage
pytest tests/ -v --cov=.claude/skills/safety/HUMAN_IN_THE_LOOP_APPROVAL_SKILL/ --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html

# Check critical path coverage
pytest tests/ --cov=.claude/skills/safety/HUMAN_IN_THE_LOOP_APPROVAL_SKILL/ --cov-report=term-missing | grep "MISSED"
```

---

## Bug Tracking Template

```yaml
Bug ID: BUG-HITL-001
Title: [Brief description]
Severity: Critical | High | Medium | Low
Component: [e.g., Request Validation, SLA, Decision Processing]
Tier Impact: [Which tiers affected: 0-4]

Description:
  [Detailed description of the bug]

Steps to Reproduce:
  1. [Step 1]
  2. [Step 2]
  3. [Expected: X, Actual: Y]

Test Case:
  [Link to failing test case]

Root Cause:
  [Analysis of why bug occurred]

Fix:
  [Description of fix applied]

Verification:
  [How fix was verified]

Regression Test:
  [New test added to prevent recurrence]

Status: Open | In Progress | Fixed | Verified | Closed
```

---

## Success Criteria

### Functional Acceptance
- ✅ All 100+ tests pass (0 failures)
- ✅ All demo workflows execute successfully
- ✅ All tiers (0-4) function correctly
- ✅ SLA timers accurate (< 1 second drift)
- ✅ Notifications delivered across all channels
- ✅ CLI interface responsive and accurate
- ✅ Audit logs complete and immutable

### Performance Acceptance
- ✅ Request submission: < 100ms (95th percentile)
- ✅ Decision processing: < 200ms (95th percentile)
- ✅ CLI list (100 requests): < 500ms
- ✅ Batch approval (100 requests): < 5 seconds
- ✅ Sustained throughput: > 10 requests/second

### Security Acceptance
- ✅ Authorization enforced (unauthorized operators blocked)
- ✅ 2FA required for Tier 4
- ✅ Fail-safe defaults (deny on error/timeout)
- ✅ Audit logs immutable and tamper-evident
- ✅ No security vulnerabilities detected

### Compliance Acceptance
- ✅ 100% constitution compliance (all 6 principles)
- ✅ All operations logged explicitly
- ✅ HITL enforced for Tier 2+
- ✅ Fail-safe behavior validated
- ✅ Vault governance rules followed

---

## Next Steps After Testing

1. **Fix Critical Bugs**: Address all severity=critical bugs immediately
2. **Optimize Performance**: If targets not met, profile and optimize
3. **Security Audit**: External security review of 2FA, authorization, logging
4. **Documentation**: Update SKILL.md with any test-driven changes
5. **User Acceptance Testing**: Onboard operators and gather feedback
6. **Production Deployment**: Deploy to Bronze Tier environment
7. **Monitoring Setup**: Configure alerting for SLA breaches, failures

---

**Last Updated**: 2026-02-16
**Version**: 1.0.0
**Status**: Ready for Test Execution

*For full specification, see SKILL.md. For practical demos, see DEMO-WORKFLOW.md.*
