"""
EMAIL_MCP_ACTION_SKILL — Phase 1 Unit Tests
Target: ~75 tests, stdlib only.

Coverage:
  - EmailRequest, EmailConfig, EmailActionStatus, EmailEventType  (models.py)
  - make_email_request factory                                    (models.py)
  - EmailAdapter ABC, MockEmailAdapter, RealEmailAdapter          (adapter.py)
  - EmailActionLogger read/write                                  (logger.py)
  - EmailAction validation, direct send, HITL gate               (action.py)
  - EmailActionSkill facade, orchestrator/security integration    (__init__.py)
  - CLI: send, status, logs                                       (cli.py)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
from golden_tier_external_world.actions.email.models import (
    EmailActionStatus,
    EmailConfig,
    EmailEventType,
    EmailRequest,
    EmailResult,
    make_email_request,
)
from golden_tier_external_world.actions.email.adapter import (
    EmailAdapter,
    MockEmailAdapter,
    RealEmailAdapter,
)
from golden_tier_external_world.actions.email.logger import EmailActionLogger
from golden_tier_external_world.actions.email.action import EmailAction, ValidationError, _validate
from golden_tier_external_world.actions.email import EmailActionSkill
from golden_tier_external_world.actions.email.cli import build_parser, main as cli_main


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def email_config(tmp_vault: Path) -> EmailConfig:
    return EmailConfig(
        sender_address="agent@company.com",
        vault_root=str(tmp_vault),
        default_tier=3,
    )


@pytest.fixture
def low_tier_config(tmp_vault: Path) -> EmailConfig:
    """Config with tier 1 — auto-sends without HITL."""
    return EmailConfig(
        sender_address="agent@company.com",
        vault_root=str(tmp_vault),
        default_tier=1,
    )


@pytest.fixture
def mock_adapter() -> MockEmailAdapter:
    return MockEmailAdapter()


@pytest.fixture
def skill(email_config: EmailConfig, mock_adapter: MockEmailAdapter) -> EmailActionSkill:
    return EmailActionSkill(email_config, adapter=mock_adapter)


@pytest.fixture
def low_tier_skill(low_tier_config: EmailConfig) -> EmailActionSkill:
    return EmailActionSkill(low_tier_config, adapter=MockEmailAdapter())


# ===========================================================================
# TestEmailActionStatus
# ===========================================================================

class TestEmailActionStatus:

    def test_constants_defined(self) -> None:
        assert EmailActionStatus.PENDING_APPROVAL == "PENDING_APPROVAL"
        assert EmailActionStatus.APPROVED         == "APPROVED"
        assert EmailActionStatus.SENT             == "SENT"
        assert EmailActionStatus.DENIED           == "DENIED"
        assert EmailActionStatus.FAILED           == "FAILED"


# ===========================================================================
# TestEmailEventType
# ===========================================================================

class TestEmailEventType:

    def test_constants_defined(self) -> None:
        assert EmailEventType.EMAIL_SENT         == "email_sent"
        assert EmailEventType.EMAIL_DENIED       == "email_denied"
        assert EmailEventType.EMAIL_FAILED       == "email_failed"
        assert EmailEventType.EMAIL_QUEUED       == "email_queued"
        assert EmailEventType.APPROVAL_REQUESTED == "email_approval_requested"


# ===========================================================================
# TestEmailRequest
# ===========================================================================

class TestEmailRequest:

    def test_auto_request_id(self) -> None:
        req = EmailRequest(to=["a@b.com"], subject="Hi", body="Body")
        assert req.request_id.startswith("EMAIL-")

    def test_auto_submitted_at_utc(self) -> None:
        req = EmailRequest(to=["a@b.com"], subject="Hi", body="Body")
        assert req.submitted_at is not None
        assert req.submitted_at.tzinfo is not None

    def test_body_capped_at_10000_chars(self) -> None:
        req = EmailRequest(to=["a@b.com"], subject="S", body="x" * 15_000)
        assert len(req.body) == 10_000

    def test_to_dict_contains_expected_keys(self) -> None:
        req = EmailRequest(to=["a@b.com"], subject="Hi", body="Body")
        d   = req.to_dict()
        assert "request_id"   in d
        assert "to"           in d
        assert "subject"      in d
        assert "body_preview" in d
        assert "tier"         in d

    def test_body_preview_limited_to_500(self) -> None:
        req = EmailRequest(to=["a@b.com"], subject="S", body="x" * 1000)
        d   = req.to_dict()
        assert len(d["body_preview"]) == 500

    def test_from_dict_roundtrip(self) -> None:
        req  = EmailRequest(to=["a@b.com", "b@c.com"], subject="Test", body="Body",
                            cc=["c@d.com"], tier=2)
        d    = req.to_dict()
        d["body"] = req.body   # from_dict reads "body", not "body_preview"
        req2 = EmailRequest.from_dict(d)
        assert req2.request_id == req.request_id
        assert req2.to         == req.to
        assert req2.subject    == req.subject
        assert req2.tier       == req.tier

    def test_defaults(self) -> None:
        req = EmailRequest(to=["x@y.com"], subject="S", body="B")
        assert req.cc               == []
        assert req.bcc              == []
        assert req.attachment_names == []
        assert req.tier             == 3
        assert req.credentials_name == "smtp_credential"

    def test_unique_request_ids(self) -> None:
        r1 = EmailRequest(to=["a@b.com"], subject="A", body="")
        r2 = EmailRequest(to=["a@b.com"], subject="B", body="")
        assert r1.request_id != r2.request_id


# ===========================================================================
# TestEmailConfig
# ===========================================================================

class TestEmailConfig:

    def test_to_dict_roundtrip(self) -> None:
        cfg  = EmailConfig(sender_address="x@y.com", vault_root="/vault", default_tier=2)
        d    = cfg.to_dict()
        cfg2 = EmailConfig.from_dict(d)
        assert cfg2.sender_address == "x@y.com"
        assert cfg2.default_tier   == 2

    def test_defaults(self) -> None:
        cfg = EmailConfig(sender_address="a@b.com")
        assert cfg.credentials_name == "smtp_credential"
        assert cfg.default_tier     == 3
        assert cfg.max_to           == 50
        assert cfg.vault_root       == ""


# ===========================================================================
# TestMakeEmailRequest
# ===========================================================================

class TestMakeEmailRequest:

    def test_string_to_becomes_list(self) -> None:
        req = make_email_request(to="a@b.com", subject="S", body="B")
        assert isinstance(req.to, list)
        assert req.to == ["a@b.com"]

    def test_list_to_preserved(self) -> None:
        req = make_email_request(to=["a@b.com", "c@d.com"], subject="S", body="B")
        assert len(req.to) == 2

    def test_returns_email_request(self) -> None:
        req = make_email_request(to="a@b.com", subject="S", body="B")
        assert isinstance(req, EmailRequest)

    def test_tier_passed_through(self) -> None:
        req = make_email_request(to="a@b.com", subject="S", body="B", tier=1)
        assert req.tier == 1


# ===========================================================================
# TestEmailResult
# ===========================================================================

class TestEmailResult:

    def test_to_dict(self) -> None:
        res = EmailResult(
            request_id="EMAIL-001",
            status=EmailActionStatus.SENT,
            sent_at=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
            adapter="mock",
        )
        d = res.to_dict()
        assert d["request_id"] == "EMAIL-001"
        assert d["status"]     == "SENT"
        assert d["adapter"]    == "mock"
        assert "2026" in d["sent_at"]

    def test_to_dict_no_sent_at(self) -> None:
        res = EmailResult(request_id="X", status=EmailActionStatus.FAILED)
        d   = res.to_dict()
        assert d["sent_at"] is None


# ===========================================================================
# TestMockEmailAdapter
# ===========================================================================

class TestMockEmailAdapter:

    def test_send_returns_sent_status(self, mock_adapter: MockEmailAdapter) -> None:
        req    = make_email_request("a@b.com", "Hi", "Body")
        result = mock_adapter.send(req)
        assert result.status     == EmailActionStatus.SENT
        assert result.sent_at    is not None
        assert result.request_id == req.request_id

    def test_send_increments_count(self, mock_adapter: MockEmailAdapter) -> None:
        mock_adapter.send(make_email_request("a@b.com", "S", "B"))
        mock_adapter.send(make_email_request("x@y.com", "S", "B"))
        assert mock_adapter.send_count == 2

    def test_sent_captured(self, mock_adapter: MockEmailAdapter) -> None:
        req = make_email_request("a@b.com", "S", "B")
        mock_adapter.send(req)
        assert len(mock_adapter.sent) == 1
        assert mock_adapter.sent[0].request_id == req.request_id

    def test_sent_is_defensive_copy(self, mock_adapter: MockEmailAdapter) -> None:
        mock_adapter.send(make_email_request("a@b.com", "S", "B"))
        copy = mock_adapter.sent
        copy.clear()
        assert len(mock_adapter.sent) == 1

    def test_fail_send_returns_failed_status(self) -> None:
        adapter = MockEmailAdapter(fail_send=True)
        result  = adapter.send(make_email_request("a@b.com", "S", "B"))
        assert result.status  == EmailActionStatus.FAILED
        assert result.error   != ""

    def test_set_fail_send(self, mock_adapter: MockEmailAdapter) -> None:
        mock_adapter.set_fail_send(True)
        result = mock_adapter.send(make_email_request("a@b.com", "S", "B"))
        assert result.status == EmailActionStatus.FAILED

    def test_health_check_default_true(self, mock_adapter: MockEmailAdapter) -> None:
        assert mock_adapter.health_check() is True

    def test_set_healthy_false(self, mock_adapter: MockEmailAdapter) -> None:
        mock_adapter.set_healthy(False)
        assert mock_adapter.health_check() is False

    def test_clear_sent(self, mock_adapter: MockEmailAdapter) -> None:
        mock_adapter.send(make_email_request("a@b.com", "S", "B"))
        mock_adapter.clear_sent()
        assert mock_adapter.send_count == 0
        assert mock_adapter.sent       == []


# ===========================================================================
# TestRealEmailAdapter
# ===========================================================================

class TestRealEmailAdapter:

    def test_send_raises(self, email_config: EmailConfig) -> None:
        adapter = RealEmailAdapter(email_config)
        req     = make_email_request("a@b.com", "S", "B")
        with pytest.raises(NotImplementedError):
            adapter.send(req)

    def test_health_check_returns_false(self, email_config: EmailConfig) -> None:
        adapter = RealEmailAdapter(email_config)
        assert adapter.health_check() is False


# ===========================================================================
# TestEmailActionLogger
# ===========================================================================

class TestEmailActionLogger:

    def test_log_submitted_writes_file(self, tmp_vault: Path) -> None:
        logger = EmailActionLogger(tmp_vault)
        req    = make_email_request("a@b.com", "Test", "Body")
        logger.log_submitted(req)
        entries = logger.read_entries()
        assert len(entries) == 1
        assert entries[0]["event"]      == "submitted"
        assert entries[0]["request_id"] == req.request_id

    def test_log_result_writes_status(self, tmp_vault: Path) -> None:
        logger = EmailActionLogger(tmp_vault)
        result = EmailResult(request_id="EMAIL-XYZ", status=EmailActionStatus.SENT, adapter="mock")
        logger.log_result(result)
        entries = logger.read_entries()
        assert entries[0]["status"] == "SENT"

    def test_log_denied_writes_entry(self, tmp_vault: Path) -> None:
        logger = EmailActionLogger(tmp_vault)
        logger.log_denied("EMAIL-001", reason="Policy violation")
        entries = logger.read_entries()
        assert entries[0]["event"]  == "denied"
        assert "Policy" in entries[0]["reason"]

    def test_log_error_writes_entry(self, tmp_vault: Path) -> None:
        logger = EmailActionLogger(tmp_vault)
        logger.log_error("EMAIL-001", "Something went wrong")
        entries = logger.read_entries()
        assert entries[0]["event"] == "error"
        assert "Something" in entries[0]["error"]

    def test_read_entries_empty_for_missing_date(self, tmp_vault: Path) -> None:
        logger  = EmailActionLogger(tmp_vault)
        entries = logger.read_entries("1999-01-01")
        assert entries == []

    def test_log_dir_created_automatically(self, tmp_vault: Path) -> None:
        logger = EmailActionLogger(tmp_vault)
        req    = make_email_request("a@b.com", "S", "B")
        logger.log_submitted(req)
        assert (tmp_vault / "70-LOGS" / "email").is_dir()

    def test_multiple_entries_appended(self, tmp_vault: Path) -> None:
        logger = EmailActionLogger(tmp_vault)
        for i in range(3):
            logger.log_error(f"EMAIL-{i:03d}", f"err {i}")
        entries = logger.read_entries()
        assert len(entries) == 3

    def test_log_queued_for_hitl(self, tmp_vault: Path) -> None:
        logger = EmailActionLogger(tmp_vault)
        req    = make_email_request("a@b.com", "S", "B")
        logger.log_queued_for_hitl(req, "REQ-HITL-001")
        entries = logger.read_entries()
        assert entries[0]["event"]           == "queued_for_hitl"
        assert entries[0]["hitl_request_id"] == "REQ-HITL-001"


# ===========================================================================
# TestValidation
# ===========================================================================

class TestValidation:

    def test_empty_to_raises(self, email_config: EmailConfig) -> None:
        req = make_email_request(to=[], subject="S", body="B")
        with pytest.raises(ValidationError, match="recipient"):
            _validate(req, email_config)

    def test_too_many_recipients_raises(self, email_config: EmailConfig) -> None:
        req = make_email_request(to=[f"u{i}@x.com" for i in range(60)], subject="S", body="B")
        with pytest.raises(ValidationError, match="Too many"):
            _validate(req, email_config)

    def test_empty_subject_raises(self, email_config: EmailConfig) -> None:
        req = make_email_request(to=["a@b.com"], subject="", body="B")
        with pytest.raises(ValidationError, match="subject"):
            _validate(req, email_config)

    def test_blank_subject_raises(self, email_config: EmailConfig) -> None:
        req = make_email_request(to=["a@b.com"], subject="   ", body="B")
        with pytest.raises(ValidationError, match="blank"):
            _validate(req, email_config)

    def test_valid_request_does_not_raise(self, email_config: EmailConfig) -> None:
        req = make_email_request(to=["a@b.com"], subject="Hello", body="Body")
        _validate(req, email_config)  # should not raise


# ===========================================================================
# TestEmailAction
# ===========================================================================

class TestEmailAction:

    def test_direct_send_tier1(self, low_tier_config: EmailConfig) -> None:
        adapter = MockEmailAdapter()
        action  = EmailAction(config=low_tier_config, adapter=adapter)
        req     = make_email_request("a@b.com", "Hi", "Body", tier=1)
        result  = action.submit(req)
        assert result.status     == EmailActionStatus.SENT
        assert adapter.send_count == 1

    def test_validation_failure_returns_failed(self, email_config: EmailConfig) -> None:
        adapter = MockEmailAdapter()
        action  = EmailAction(config=email_config, adapter=adapter)
        req     = make_email_request(to=[], subject="S", body="B")
        result  = action.submit(req)
        assert result.status  == EmailActionStatus.FAILED
        assert "recipient"    in result.error.lower()
        assert adapter.send_count == 0

    def test_hitl_gate_queues_tier3(self, email_config: EmailConfig) -> None:
        mock_hitl = MagicMock()
        # Make hitl.submit accept and record the request
        submitted_requests = []
        def fake_submit(r):
            submitted_requests.append(r)
            return r
        mock_hitl.submit.side_effect = fake_submit

        adapter = MockEmailAdapter()
        action  = EmailAction(config=email_config, adapter=adapter, hitl_skill=mock_hitl)
        req     = make_email_request("a@b.com", "Critical", "Body", tier=3)
        result  = action.submit(req)

        assert result.status      == EmailActionStatus.PENDING_APPROVAL
        assert result.hitl_request_id != ""
        assert adapter.send_count == 0   # not sent yet
        mock_hitl.submit.assert_called_once()

    def test_no_hitl_skill_tier3_sends_directly(self, email_config: EmailConfig) -> None:
        """Without a HITL skill, high-tier emails fall through to direct send."""
        adapter = MockEmailAdapter()
        action  = EmailAction(config=email_config, adapter=adapter, hitl_skill=None)
        req     = make_email_request("a@b.com", "Urgent", "Body", tier=3)
        result  = action.submit(req)
        assert result.status     == EmailActionStatus.SENT
        assert adapter.send_count == 1

    def test_hitl_failure_denies_email(self, email_config: EmailConfig) -> None:
        mock_hitl = MagicMock()
        mock_hitl.submit.side_effect = RuntimeError("HITL unavailable")

        adapter = MockEmailAdapter()
        action  = EmailAction(config=email_config, adapter=adapter, hitl_skill=mock_hitl)
        req     = make_email_request("a@b.com", "Test", "Body", tier=3)
        result  = action.submit(req)

        assert result.status     == EmailActionStatus.DENIED
        assert adapter.send_count == 0

    def test_adapter_failure_captured_in_result(self, email_config: EmailConfig) -> None:
        adapter = MockEmailAdapter(fail_send=True)
        action  = EmailAction(config=email_config, adapter=adapter, hitl_skill=None)
        req     = make_email_request("a@b.com", "S", "B", tier=1)
        result  = action.submit(req)
        assert result.status == EmailActionStatus.FAILED

    def test_sender_filled_from_config(self, email_config: EmailConfig) -> None:
        adapter = MockEmailAdapter()
        action  = EmailAction(config=email_config, adapter=adapter)
        req     = make_email_request("a@b.com", "S", "B", tier=1)
        assert req.sender == ""
        action.submit(req)
        assert req.sender == email_config.sender_address

    def test_health_check_delegates_to_adapter(self, email_config: EmailConfig) -> None:
        adapter = MockEmailAdapter()
        action  = EmailAction(config=email_config, adapter=adapter)
        assert action.health_check() is True
        adapter.set_healthy(False)
        assert action.health_check() is False

    def test_submit_logs_submitted_event(self, email_config: EmailConfig, tmp_vault: Path) -> None:
        adapter = MockEmailAdapter()
        logger  = EmailActionLogger(tmp_vault)
        action  = EmailAction(config=email_config, adapter=adapter, logger=logger)
        req     = make_email_request("a@b.com", "S", "B", tier=1)
        action.submit(req)
        entries = logger.read_entries()
        events  = [e["event"] for e in entries]
        assert "submitted" in events


# ===========================================================================
# TestEmailActionSkill (facade)
# ===========================================================================

class TestEmailActionSkill:

    def test_send_low_tier_returns_sent(self, low_tier_skill: EmailActionSkill) -> None:
        result = low_tier_skill.send(to="alice@example.com", subject="Hello", body="Hi!")
        assert result.status == EmailActionStatus.SENT

    def test_send_high_tier_no_hitl_returns_sent(self, skill: EmailActionSkill) -> None:
        """Without HITL skill, tier 3 sends directly."""
        result = skill.send(to="alice@example.com", subject="Hello", body="Hi!")
        assert result.status == EmailActionStatus.SENT

    def test_send_high_tier_with_hitl_queues(self, email_config: EmailConfig) -> None:
        mock_hitl = MagicMock()
        mock_hitl.submit.return_value = MagicMock(request_id="REQ-001")
        skill  = EmailActionSkill(email_config, hitl_skill=mock_hitl)
        result = skill.send(to="alice@example.com", subject="Report", body="Body")
        assert result.status == EmailActionStatus.PENDING_APPROVAL
        mock_hitl.submit.assert_called_once()

    def test_send_request_accepts_email_request(self, low_tier_skill: EmailActionSkill) -> None:
        req    = make_email_request("x@y.com", "Subject", "Body", tier=1)
        result = low_tier_skill.send_request(req)
        assert result.status == EmailActionStatus.SENT

    def test_send_validation_failure(self, skill: EmailActionSkill) -> None:
        result = skill.send(to=[], subject="S", body="B")
        assert result.status == EmailActionStatus.FAILED

    def test_set_hitl(self, skill: EmailActionSkill) -> None:
        mock_hitl = MagicMock()
        skill.set_hitl(mock_hitl)
        assert skill.action._hitl is mock_hitl

    def test_health_check_true(self, skill: EmailActionSkill) -> None:
        assert skill.health_check() is True

    def test_health_check_false_when_adapter_unhealthy(self, email_config: EmailConfig) -> None:
        adapter = MockEmailAdapter(healthy=False)
        skill   = EmailActionSkill(email_config, adapter=adapter)
        assert skill.health_check() is False

    def test_read_logs_returns_list(self, skill: EmailActionSkill) -> None:
        skill.send(to="a@b.com", subject="S", body="B", tier=1)
        logs = skill.read_logs()
        assert isinstance(logs, list)
        assert len(logs) > 0

    def test_config_property(self, skill: EmailActionSkill, email_config: EmailConfig) -> None:
        assert skill.config is email_config

    def test_adapter_property(self, skill: EmailActionSkill, mock_adapter: MockEmailAdapter) -> None:
        assert skill.adapter is mock_adapter

    def test_orchestrator_registration(self, email_config: EmailConfig) -> None:
        from silver_tier_core_autonomy.orchestrator.registry import SkillRegistry
        registry = SkillRegistry()
        skill    = EmailActionSkill(email_config, orchestrator_registry=registry)
        assert registry.has("email", "send")

    def test_orchestrator_handler_sends_email(self, email_config: EmailConfig) -> None:
        low_cfg  = EmailConfig(sender_address="a@b.com", default_tier=1)
        from silver_tier_core_autonomy.orchestrator.registry import SkillRegistry
        registry = SkillRegistry()
        skill    = EmailActionSkill(low_cfg, orchestrator_registry=registry)
        handler  = registry.get("email", "send")
        result   = handler(to=["x@y.com"], subject="Test", body="Body", tier=1)
        assert result["status"] == EmailActionStatus.SENT

    def test_security_integration_graceful(self, email_config: EmailConfig) -> None:
        bad_security = MagicMock(side_effect=Exception("security failure"))
        skill = EmailActionSkill(email_config, security_skill=bad_security)
        assert skill is not None  # should not raise

    def test_security_integration_registers_credential(self, email_config: EmailConfig) -> None:
        from bronze_tier_governance.security import SecuritySkill
        security = SecuritySkill(vault_root=email_config.vault_root)
        EmailActionSkill(email_config, security_skill=security)
        creds = security.list_credentials()
        names = [c.name for c in creds]
        assert email_config.credentials_name in names

    def test_send_multiple_recipients(self, low_tier_skill: EmailActionSkill) -> None:
        result = low_tier_skill.send(
            to=["a@b.com", "c@d.com", "e@f.com"],
            subject="Broadcast",
            body="Hello everyone",
            tier=1,
        )
        assert result.status == EmailActionStatus.SENT

    def test_send_with_cc_bcc(self, low_tier_skill: EmailActionSkill) -> None:
        result = low_tier_skill.send(
            to="primary@x.com",
            subject="CC test",
            body="Body",
            cc=["cc@x.com"],
            bcc=["bcc@x.com"],
            tier=1,
        )
        assert result.status == EmailActionStatus.SENT


# ===========================================================================
# TestCLI
# ===========================================================================

class TestCLI:

    def test_build_parser_returns_parser(self) -> None:
        parser = build_parser()
        assert parser is not None

    def test_send_command_returns_0(self, tmp_vault: Path) -> None:
        result = cli_main([
            "--vault",  str(tmp_vault),
            "--sender", "agent@company.com",
            "send",
            "--to",      "alice@example.com",
            "--subject", "Test",
            "--body",    "Hello",
            "--tier",    "1",
        ])
        assert result == 0

    def test_status_command_returns_0(self, tmp_vault: Path) -> None:
        result = cli_main([
            "--vault",  str(tmp_vault),
            "--sender", "agent@company.com",
            "status",
        ])
        assert result == 0

    def test_logs_no_entries_returns_0(self, tmp_vault: Path) -> None:
        result = cli_main([
            "--vault",  str(tmp_vault),
            "--sender", "agent@company.com",
            "logs",
        ])
        assert result == 0

    def test_send_then_logs_shows_entry(self, tmp_vault: Path) -> None:
        cli_main([
            "--vault",  str(tmp_vault),
            "--sender", "agent@company.com",
            "send",
            "--to",      "alice@example.com",
            "--subject", "Hello",
            "--body",    "Hi!",
            "--tier",    "1",
        ])
        result = cli_main([
            "--vault",  str(tmp_vault),
            "--sender", "agent@company.com",
            "logs",
        ])
        assert result == 0

    def test_send_comma_separated_recipients(self, tmp_vault: Path) -> None:
        result = cli_main([
            "--vault",  str(tmp_vault),
            "--sender", "a@b.com",
            "send",
            "--to",      "x@y.com,z@w.com",
            "--subject", "Multi-recipient",
            "--tier",    "1",
        ])
        assert result == 0

    def test_logs_with_date_filter(self, tmp_vault: Path) -> None:
        result = cli_main([
            "--vault",  str(tmp_vault),
            "--sender", "a@b.com",
            "logs",
            "--date", "1999-01-01",
        ])
        assert result == 0  # no entries, but no error
