"""
Unit tests for HUMAN_IN_THE_LOOP_APPROVAL_SKILL Phase 1.

Coverage areas:
  - Models: SLAConfig, ApprovalRequest, DecisionRecord
  - Validator: required fields, tier rules, idempotency
  - RequestStore: save, load, list, move
  - HITLApprover: submit, approve, deny, defer, timeout, batch
  - HITLSkill: facade integration
  - CLI: list, view, approve, deny, batch-approve, submit

Run with:
    python -m pytest tests/test_hitl.py -v
"""

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from bronze_tier_governance.hitl import (
    DecisionError,
    HITLSkill,
    ValidationError,
    make_request,
)
from bronze_tier_governance.hitl.approver import HITLApprover
from bronze_tier_governance.hitl.audit import HITLAuditLogger
from bronze_tier_governance.hitl.cli import build_parser, main as cli_main
from bronze_tier_governance.hitl.models import (
    TIER_SLA_SECONDS,
    ApprovalRequest,
    Decision,
    DecisionRecord,
    SLAConfig,
    Tier,
)
from bronze_tier_governance.hitl.store import RequestStore
from bronze_tier_governance.hitl.validator import validate_request, validate_decision_input


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    """Minimal vault structure."""
    vault_root = tmp_path / "obsidian-vault"
    (vault_root / "70-LOGS" / "hitl" / "pending").mkdir(parents=True)
    (vault_root / "70-LOGS" / "hitl" / "completed").mkdir(parents=True)
    (vault_root / "70-LOGS" / "hitl" / "audit").mkdir(parents=True)
    (vault_root / "70-LOGS" / "hitl" / "daily").mkdir(parents=True)
    return vault_root


@pytest.fixture()
def store(vault: Path) -> RequestStore:
    return RequestStore(vault)


@pytest.fixture()
def audit(vault: Path) -> HITLAuditLogger:
    return HITLAuditLogger(vault)


@pytest.fixture()
def approver(store: RequestStore, audit: HITLAuditLogger) -> HITLApprover:
    return HITLApprover(store=store, audit=audit)


@pytest.fixture()
def skill(vault: Path) -> HITLSkill:
    return HITLSkill(vault_root=vault)


def _tier2_request(**kwargs) -> ApprovalRequest:
    defaults = dict(
        agent_id="test-agent",
        operation="send_email",
        tier=2,
        action_summary="Send email to user",
        reason="Test reason",
        details={"to": "user@example.com"},
        risk={"blast_radius": "single user", "reversibility": "cannot unsend"},
    )
    defaults.update(kwargs)
    return make_request(**defaults)


def _tier1_request(**kwargs) -> ApprovalRequest:
    defaults = dict(
        agent_id="fs-agent",
        operation="organize_file",
        tier=1,
        action_summary="Rename file",
        reason="Naming convention",
        details={"file": "test.md"},
    )
    defaults.update(kwargs)
    return make_request(**defaults)


# ===========================================================================
# SLAConfig
# ===========================================================================

class TestSLAConfig:

    def test_tier2_4hour_sla(self) -> None:
        now = datetime(2026, 2, 17, 10, 0, 0, tzinfo=timezone.utc)
        sla = SLAConfig(tier=2, submitted_at=now, sla_seconds=14400)
        expected = now + timedelta(hours=4)
        assert sla.required_by == expected

    def test_tier3_1hour_sla(self) -> None:
        now = datetime(2026, 2, 17, 10, 0, 0, tzinfo=timezone.utc)
        sla = SLAConfig(tier=3, submitted_at=now, sla_seconds=3600)
        expected = now + timedelta(hours=1)
        assert sla.required_by == expected

    def test_tier4_no_timeout(self) -> None:
        now = datetime(2026, 2, 17, 10, 0, 0, tzinfo=timezone.utc)
        sla = SLAConfig(tier=4, submitted_at=now, sla_seconds=None)
        assert sla.required_by is None
        assert sla.is_expired() is False

    def test_escalation_at_50_percent(self) -> None:
        now = datetime(2026, 2, 17, 10, 0, 0, tzinfo=timezone.utc)
        sla = SLAConfig(tier=2, submitted_at=now, sla_seconds=14400)
        expected_escalation = now + timedelta(hours=2)
        assert sla.escalation_at == expected_escalation

    def test_is_expired_true(self) -> None:
        now = datetime(2026, 2, 17, 10, 0, 0, tzinfo=timezone.utc)
        sla = SLAConfig(tier=2, submitted_at=now, sla_seconds=1)
        future = now + timedelta(seconds=2)
        assert sla.is_expired(now=future) is True

    def test_is_expired_false(self) -> None:
        now = datetime(2026, 2, 17, 10, 0, 0, tzinfo=timezone.utc)
        sla = SLAConfig(tier=2, submitted_at=now, sla_seconds=3600)
        assert sla.is_expired(now=now) is False

    def test_remaining_seconds(self) -> None:
        now = datetime(2026, 2, 17, 10, 0, 0, tzinfo=timezone.utc)
        sla = SLAConfig(tier=2, submitted_at=now, sla_seconds=3600)
        current = now + timedelta(seconds=1800)
        assert abs(sla.remaining_seconds(now=current) - 1800) < 1

    def test_serialise_round_trip(self) -> None:
        now = datetime(2026, 2, 17, 10, 0, 0, tzinfo=timezone.utc)
        sla = SLAConfig(tier=2, submitted_at=now, sla_seconds=3600)
        restored = SLAConfig.from_dict(sla.to_dict())
        assert restored.tier == sla.tier
        assert restored.sla_seconds == sla.sla_seconds


# ===========================================================================
# Validator
# ===========================================================================

class TestValidator:

    def test_valid_tier0(self) -> None:
        req = make_request("agent", "read_file", 0, "Read config", "Debug", {})
        validate_request(req)  # Should not raise

    def test_valid_tier2_with_risk(self) -> None:
        req = _tier2_request()
        validate_request(req)  # Should not raise

    def test_missing_agent_id(self) -> None:
        req = _tier2_request(agent_id="")
        with pytest.raises(ValidationError, match="agent_id"):
            validate_request(req)

    def test_missing_operation(self) -> None:
        req = _tier2_request(operation="")
        with pytest.raises(ValidationError, match="operation"):
            validate_request(req)

    def test_invalid_tier(self) -> None:
        req = _tier2_request(tier=5)
        with pytest.raises(ValidationError, match="tier must be 0-4"):
            validate_request(req)

    def test_tier2_missing_risk(self) -> None:
        req = make_request("agent", "send_email", 2, "Send email", "reason", {}, risk=None)
        with pytest.raises(ValidationError, match="risk assessment required"):
            validate_request(req)

    def test_tier2_incomplete_risk(self) -> None:
        req = make_request(
            "agent", "send_email", 2, "Send email", "reason", {},
            risk={"blast_radius": "low"}  # missing reversibility
        )
        with pytest.raises(ValidationError, match="missing required keys"):
            validate_request(req)

    def test_tier1_no_risk_required(self) -> None:
        req = _tier1_request()
        validate_request(req)  # Should not raise

    def test_decision_idempotency(self) -> None:
        req = _tier2_request()
        req.status = Decision.APPROVED
        with pytest.raises(DecisionError, match="already decided"):
            validate_decision_input(req, "approve", "operator")

    def test_invalid_decision_action(self) -> None:
        req = _tier2_request()
        with pytest.raises(DecisionError, match="Invalid action"):
            validate_decision_input(req, "maybe", "operator")

    def test_empty_operator(self) -> None:
        req = _tier2_request()
        with pytest.raises(DecisionError, match="operator cannot be empty"):
            validate_decision_input(req, "approve", "")


# ===========================================================================
# Models
# ===========================================================================

class TestApprovalRequest:

    def test_request_id_is_uuid_format(self) -> None:
        req = _tier2_request()
        assert req.request_id.startswith("REQ-")
        assert len(req.request_id) > 10

    def test_unique_ids(self) -> None:
        r1 = _tier2_request()
        r2 = _tier2_request()
        assert r1.request_id != r2.request_id

    def test_checksum_generated(self) -> None:
        req = _tier2_request()
        assert req.checksum.startswith("sha256:")

    def test_is_auto_approved_tier0(self) -> None:
        req = make_request("a", "op", 0, "act", "reason", {})
        assert req.is_auto_approved is True

    def test_is_auto_approved_tier1(self) -> None:
        req = _tier1_request()
        assert req.is_auto_approved is True

    def test_is_not_auto_approved_tier2(self) -> None:
        req = _tier2_request()
        assert req.is_auto_approved is False

    def test_serialise_round_trip(self) -> None:
        req = _tier2_request()
        restored = ApprovalRequest.from_dict(req.to_dict())
        assert restored.request_id == req.request_id
        assert restored.tier == req.tier
        assert restored.agent_id == req.agent_id


# ===========================================================================
# RequestStore
# ===========================================================================

class TestRequestStore:

    def test_save_and_get_pending(self, store: RequestStore) -> None:
        req = _tier2_request()
        store.save_pending(req)
        loaded = store.get(req.request_id)
        assert loaded is not None
        assert loaded.request_id == req.request_id

    def test_list_pending_empty(self, store: RequestStore) -> None:
        assert store.list_pending() == []

    def test_list_pending_returns_saved(self, store: RequestStore) -> None:
        req = _tier2_request()
        store.save_pending(req)
        pending = store.list_pending()
        assert len(pending) == 1
        assert pending[0].request_id == req.request_id

    def test_list_pending_filter_by_agent(self, store: RequestStore) -> None:
        r1 = _tier2_request(agent_id="agent-A")
        r2 = _tier2_request(agent_id="agent-B")
        store.save_pending(r1)
        store.save_pending(r2)
        filtered = store.list_pending(agent_id="agent-A")
        assert len(filtered) == 1
        assert filtered[0].agent_id == "agent-A"

    def test_list_pending_filter_by_tier(self, store: RequestStore) -> None:
        r1 = _tier2_request()
        r2 = _tier1_request()
        store.save_pending(r1)
        store.save_pending(r2)
        filtered = store.list_pending(tier=2)
        assert all(r.tier == 2 for r in filtered)

    def test_move_to_completed_removes_from_pending(self, store: RequestStore) -> None:
        req = _tier2_request()
        store.save_pending(req)
        req.status = Decision.APPROVED
        store.move_to_completed(req)
        assert store.list_pending() == []
        loaded = store.get(req.request_id)
        assert loaded is not None
        assert loaded.status == Decision.APPROVED

    def test_exists(self, store: RequestStore) -> None:
        req = _tier2_request()
        assert store.exists(req.request_id) is False
        store.save_pending(req)
        assert store.exists(req.request_id) is True


# ===========================================================================
# HITLApprover
# ===========================================================================

class TestHITLApprover:

    def test_submit_tier0_auto_approved(self, approver: HITLApprover) -> None:
        req = make_request("agent", "read_file", 0, "Read config", "Debug", {})
        result = approver.submit(req)
        assert result.status == Decision.AUTO

    def test_submit_tier1_auto_approved(self, approver: HITLApprover) -> None:
        req = _tier1_request()
        result = approver.submit(req)
        assert result.status == Decision.AUTO

    def test_submit_tier2_pending(self, approver: HITLApprover) -> None:
        req = _tier2_request()
        result = approver.submit(req)
        assert result.status == Decision.PENDING

    def test_submit_invalid_raises(self, approver: HITLApprover) -> None:
        req = _tier2_request(agent_id="")
        with pytest.raises(ValidationError):
            approver.submit(req)

    def test_approve_changes_status(self, approver: HITLApprover) -> None:
        req = _tier2_request()
        approver.submit(req)
        decision = approver.approve(req.request_id, "alice", comment="Looks good")
        assert decision.action == Decision.APPROVED
        assert decision.decided_by == "alice"
        assert decision.comment == "Looks good"

    def test_deny_changes_status(self, approver: HITLApprover) -> None:
        req = _tier2_request()
        approver.submit(req)
        decision = approver.deny(req.request_id, "alice", reason="Not needed")
        assert decision.action == Decision.DENIED
        assert "Not needed" in decision.reason

    def test_double_decision_raises(self, approver: HITLApprover) -> None:
        req = _tier2_request()
        approver.submit(req)
        approver.approve(req.request_id, "alice")
        with pytest.raises(DecisionError, match="already decided"):
            approver.deny(req.request_id, "bob", reason="late")

    def test_defer_extends_sla(self, approver: HITLApprover) -> None:
        req = _tier2_request()
        approver.submit(req)
        original_deadline = approver.get_request(req.request_id).sla.required_by
        approver.defer(req.request_id, "alice", extend_seconds=3600)
        updated = approver.get_request(req.request_id)
        assert updated.sla.required_by > original_deadline
        assert updated.status == Decision.PENDING  # Still pending

    def test_timeout_auto_denies(self, approver: HITLApprover) -> None:
        req = _tier2_request(sla_override_seconds=1)
        approver.submit(req)
        time.sleep(1.1)  # Let SLA expire
        decision = approver.process_timeout(req.request_id)
        assert decision.action == Decision.DENIED
        assert decision.decided_by == "SYSTEM"

    def test_timeout_fails_if_not_expired(self, approver: HITLApprover) -> None:
        req = _tier2_request()
        approver.submit(req)
        with pytest.raises(DecisionError, match="not expired"):
            approver.process_timeout(req.request_id)

    def test_check_and_timeout_expired(self, approver: HITLApprover) -> None:
        req = _tier2_request(sla_override_seconds=1)
        approver.submit(req)
        time.sleep(1.1)
        decisions = approver.check_and_timeout_expired()
        assert len(decisions) == 1
        assert decisions[0].action == Decision.DENIED

    def test_list_pending(self, approver: HITLApprover) -> None:
        for _ in range(3):
            approver.submit(_tier2_request())
        assert len(approver.list_pending()) == 3

    def test_get_request_not_found(self, approver: HITLApprover) -> None:
        assert approver.get_request("REQ-does-not-exist") is None

    def test_approve_with_modifications(self, approver: HITLApprover) -> None:
        req = _tier2_request()
        approver.submit(req)
        mods = {"recipient": "beta@example.com", "count": 100}
        decision = approver.approve(req.request_id, "alice", modifications=mods)
        assert decision.modifications == mods
        assert decision.action == Decision.APPROVED


# ===========================================================================
# HITLAuditLogger
# ===========================================================================

class TestHITLAuditLogger:

    def test_log_submitted_creates_audit_file(self, audit: HITLAuditLogger, vault: Path) -> None:
        req = _tier2_request()
        audit.log_submitted(req)
        audit_dir = vault / "70-LOGS" / "hitl" / "audit"
        files = list(audit_dir.glob("*.md"))
        assert len(files) == 1

    def test_log_submitted_creates_daily_log(self, audit: HITLAuditLogger, vault: Path) -> None:
        req = _tier2_request()
        audit.log_submitted(req)
        daily_dir = vault / "70-LOGS" / "hitl" / "daily"
        files = list(daily_dir.glob("*.md"))
        assert len(files) == 1
        content = files[0].read_text()
        assert "SUBMIT" in content

    def test_log_decision_appended(self, audit: HITLAuditLogger, vault: Path) -> None:
        req = _tier2_request()
        audit.log_submitted(req)
        decision = DecisionRecord(
            request_id=req.request_id,
            action=Decision.APPROVED,
            decided_by="alice",
            decided_at=datetime.now(tz=timezone.utc),
            comment="OK",
        )
        audit.log_decision(req, decision)
        audit_file = vault / "70-LOGS" / "hitl" / "audit" / f"{req.request_id}.md"
        content = audit_file.read_text()
        assert "DECISION_RECORDED" in content
        assert "APPROVED" in content

    def test_log_timeout(self, audit: HITLAuditLogger, vault: Path) -> None:
        req = _tier2_request()
        audit.log_timeout(req)
        audit_dir = vault / "70-LOGS" / "hitl" / "audit"
        files = list(audit_dir.glob("*.md"))
        assert len(files) == 1
        content = files[0].read_text()
        assert "SLA_TIMEOUT" in content


# ===========================================================================
# HITLSkill (Facade)
# ===========================================================================

class TestHITLSkill:

    def test_submit_tier0_auto_approved(self, skill: HITLSkill) -> None:
        req = skill.submit("agent", "read_file", 0, "Read", "Debug", {})
        assert req.status == Decision.AUTO

    def test_submit_tier2_pending(self, skill: HITLSkill) -> None:
        req = skill.submit(
            "agent", "send_email", 2, "Send email", "reason",
            details={"to": "x@y.com"},
            risk={"blast_radius": "low", "reversibility": "no"},
        )
        assert req.status == Decision.PENDING

    def test_approve_via_skill(self, skill: HITLSkill) -> None:
        req = skill.submit(
            "agent", "send_email", 2, "Send email", "reason",
            details={},
            risk={"blast_radius": "low", "reversibility": "no"},
        )
        d = skill.approve(req.request_id, "alice")
        assert d.action == Decision.APPROVED

    def test_deny_via_skill(self, skill: HITLSkill) -> None:
        req = skill.submit(
            "agent", "send_email", 2, "Send email", "reason",
            details={},
            risk={"blast_radius": "low", "reversibility": "no"},
        )
        d = skill.deny(req.request_id, "alice", reason="Nope")
        assert d.action == Decision.DENIED

    def test_list_pending(self, skill: HITLSkill) -> None:
        skill.submit(
            "agent", "send_email", 2, "Email", "reason",
            risk={"blast_radius": "low", "reversibility": "no"},
        )
        skill.submit(
            "agent", "send_email", 2, "Email2", "reason2",
            risk={"blast_radius": "low", "reversibility": "no"},
        )
        assert len(skill.list_pending()) == 2

    def test_get_request(self, skill: HITLSkill) -> None:
        req = skill.submit(
            "agent", "send_email", 2, "Email", "reason",
            risk={"blast_radius": "low", "reversibility": "no"},
        )
        loaded = skill.get_request(req.request_id)
        assert loaded is not None
        assert loaded.request_id == req.request_id

    def test_check_timeouts(self, skill: HITLSkill) -> None:
        req = skill.submit(
            "agent", "send_email", 2, "Email", "reason",
            risk={"blast_radius": "low", "reversibility": "no"},
            sla_override_seconds=1,
        )
        time.sleep(1.1)
        decisions = skill.check_timeouts()
        assert len(decisions) == 1
        assert decisions[0].action == Decision.DENIED


# ===========================================================================
# CLI
# ===========================================================================

class TestCLI:

    def test_list_empty(self, vault: Path) -> None:
        result = cli_main(["--vault", str(vault), "list"])
        assert result == 0

    def test_submit_tier1(self, vault: Path) -> None:
        result = cli_main([
            "--vault", str(vault),
            "submit",
            "--agent-id", "test-agent",
            "--operation", "organize_file",
            "--tier", "1",
            "--action", "Rename file",
            "--reason", "Convention",
        ])
        assert result == 0

    def test_submit_and_list_tier2(self, vault: Path) -> None:
        cli_main([
            "--vault", str(vault),
            "submit",
            "--agent-id", "email-agent",
            "--operation", "send_email",
            "--tier", "2",
            "--action", "Send welcome email",
            "--reason", "Onboarding",
            "--blast-radius", "single user",
            "--reversibility", "cannot unsend",
        ])
        result = cli_main(["--vault", str(vault), "list"])
        assert result == 0

    def test_submit_approve_cycle(self, vault: Path) -> None:
        # Submit
        skill = HITLSkill(vault_root=vault)
        req = skill.submit(
            "agent", "send_email", 2, "Send email", "reason",
            risk={"blast_radius": "low", "reversibility": "no"},
        )
        # Approve via CLI
        result = cli_main([
            "--vault", str(vault),
            "approve", req.request_id,
            "--operator", "alice",
            "--comment", "OK",
        ])
        assert result == 0
        # Verify
        loaded = skill.get_request(req.request_id)
        assert loaded.status == Decision.APPROVED

    def test_submit_deny_cycle(self, vault: Path) -> None:
        skill = HITLSkill(vault_root=vault)
        req = skill.submit(
            "agent", "send_email", 2, "Email", "reason",
            risk={"blast_radius": "low", "reversibility": "no"},
        )
        result = cli_main([
            "--vault", str(vault),
            "deny", req.request_id,
            "--operator", "alice",
            "--reason", "Not approved",
        ])
        assert result == 0

    def test_view_pending_request(self, vault: Path) -> None:
        skill = HITLSkill(vault_root=vault)
        req = skill.submit(
            "agent", "send_email", 2, "Email", "reason",
            risk={"blast_radius": "low", "reversibility": "no"},
        )
        result = cli_main(["--vault", str(vault), "view", req.request_id])
        assert result == 0

    def test_view_nonexistent_returns_error(self, vault: Path) -> None:
        result = cli_main(["--vault", str(vault), "view", "REQ-does-not-exist"])
        assert result == 1

    def test_batch_approve(self, vault: Path) -> None:
        skill = HITLSkill(vault_root=vault)
        for _ in range(3):
            skill.submit(
                "batch-agent", "organize_file", 1, "Rename", "reason",
            )
        result = cli_main([
            "--vault", str(vault),
            "batch-approve",
            "--operator", "alice",
            "--agent", "batch-agent",
        ])
        assert result == 0
        assert len(skill.list_pending(agent_id="batch-agent")) == 0

    def test_approve_already_decided_fails(self, vault: Path) -> None:
        skill = HITLSkill(vault_root=vault)
        req = skill.submit(
            "agent", "send_email", 2, "Email", "reason",
            risk={"blast_radius": "low", "reversibility": "no"},
        )
        skill.approve(req.request_id, "alice")
        result = cli_main([
            "--vault", str(vault),
            "approve", req.request_id,
            "--operator", "bob",
        ])
        assert result == 1  # Should fail — already decided
