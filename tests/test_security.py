"""
Unit tests for SECURITY_AND_CREDENTIAL_MANAGEMENT_SKILL Phase 1.

Coverage areas:
  - Models: CredentialSpec, PolicyRule, AuditEntry, ScanFinding, make_audit_entry
  - Redactor: register_secret, redact, redact_dict, pattern matching
  - Loader: DotEnvParser, load_dotenv, require, require_all, is_set
  - Policy: add_allow, add_deny, wildcard, default-deny, check
  - Store: register, load, get, get_safe, to_safe_dict, rotation_due, mark_rotated
  - VaultGuard: scan_string, is_safe_to_write, severity filter, file scan
  - SecurityAuditLogger: log events, read_entries
  - SecuritySkill: facade integration
  - CLI: build_parser, verify, scan-vault, list-credentials, rotate-reminder, audit

Run with:
    python -m pytest tests/test_security.py -v
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from bronze_tier_governance.security import (
    AccessPolicy,
    CredentialLoader,
    CredentialNotFoundError,
    CredentialSpec,
    CredentialStore,
    CredentialType,
    PolicyEffect,
    PolicyRule,
    PolicyViolation,
    ScanFinding,
    ScanSeverity,
    SecretRedactor,
    SecurityAuditLogger,
    SecuritySkill,
    VaultGuard,
    make_audit_entry,
    redact,
    redact_dict,
    register_secret,
)
from bronze_tier_governance.security.loader import CredentialError, DotEnvParser
from bronze_tier_governance.security.models import CredentialSource, AuditEntry
from bronze_tier_governance.security.cli import build_parser, main as cli_main


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    """Minimal vault structure for security skill."""
    vault_root = tmp_path / "obsidian-vault"
    (vault_root / "70-LOGS" / "security" / "audit").mkdir(parents=True)
    (vault_root / "70-LOGS" / "security" / "jsonl").mkdir(parents=True)
    (vault_root / "70-LOGS" / "security" / "errors").mkdir(parents=True)
    return vault_root


@pytest.fixture()
def audit_logger(vault: Path) -> SecurityAuditLogger:
    return SecurityAuditLogger(vault)


@pytest.fixture()
def policy() -> AccessPolicy:
    return AccessPolicy(default_effect=PolicyEffect.DENY)


@pytest.fixture()
def loader() -> CredentialLoader:
    return CredentialLoader()


@pytest.fixture()
def redactor() -> SecretRedactor:
    return SecretRedactor()


@pytest.fixture()
def store(policy: AccessPolicy, loader: CredentialLoader,
          redactor: SecretRedactor, audit_logger: SecurityAuditLogger) -> CredentialStore:
    return CredentialStore(policy=policy, loader=loader,
                           redactor=redactor, audit=audit_logger)


@pytest.fixture()
def skill(vault: Path) -> SecuritySkill:
    return SecuritySkill(vault_root=vault)


@pytest.fixture()
def dotenv_file(tmp_path: Path) -> Path:
    p = tmp_path / ".env"
    p.write_text("TEST_API_KEY=secret123\nTEST_TOKEN=tok_abc\n", encoding="utf-8")
    return p


# ===========================================================================
# 1. Models
# ===========================================================================

class TestCredentialSpec:
    def test_defaults(self):
        spec = CredentialSpec(name="x", env_key="X_KEY")
        assert spec.cred_type == CredentialType.GENERIC
        assert spec.required is True
        assert spec.rotation_days == 90
        assert spec.last_rotated is None

    def test_to_dict_round_trip(self):
        spec = CredentialSpec(
            name="gmail", env_key="GMAIL_KEY",
            cred_type=CredentialType.API_KEY, description="test", required=False,
        )
        d = spec.to_dict()
        spec2 = CredentialSpec.from_dict(d)
        assert spec2.name == "gmail"
        assert spec2.env_key == "GMAIL_KEY"
        assert spec2.cred_type == CredentialType.API_KEY
        assert spec2.required is False

    def test_rotation_not_due_when_no_last_rotated(self):
        spec = CredentialSpec(name="x", env_key="X")
        assert spec.rotation_due is False

    def test_rotation_due_when_overdue(self):
        spec = CredentialSpec(name="x", env_key="X", rotation_days=30)
        spec.last_rotated = datetime.now(tz=timezone.utc) - timedelta(days=31)
        assert spec.rotation_due is True

    def test_rotation_not_due_when_recent(self):
        spec = CredentialSpec(name="x", env_key="X", rotation_days=90)
        spec.last_rotated = datetime.now(tz=timezone.utc) - timedelta(days=10)
        assert spec.rotation_due is False

    def test_days_until_rotation_returns_none_without_last_rotated(self):
        spec = CredentialSpec(name="x", env_key="X")
        assert spec.days_until_rotation is None

    def test_days_until_rotation_positive(self):
        spec = CredentialSpec(name="x", env_key="X", rotation_days=90)
        spec.last_rotated = datetime.now(tz=timezone.utc) - timedelta(days=50)
        days = spec.days_until_rotation
        assert days is not None and days > 0


class TestPolicyRule:
    def test_exact_match(self):
        rule = PolicyRule("agent-a", "cred-1", PolicyEffect.ALLOW)
        assert rule.matches("agent-a", "cred-1") is True
        assert rule.matches("agent-b", "cred-1") is False

    def test_wildcard_agent(self):
        rule = PolicyRule("*", "cred-1", PolicyEffect.ALLOW)
        assert rule.matches("anyone", "cred-1") is True
        assert rule.matches("anyone", "cred-2") is False

    def test_wildcard_cred(self):
        rule = PolicyRule("agent-a", "*", PolicyEffect.ALLOW)
        assert rule.matches("agent-a", "anything") is True

    def test_double_wildcard(self):
        rule = PolicyRule("*", "*", PolicyEffect.DENY)
        assert rule.matches("x", "y") is True

    def test_round_trip(self):
        rule = PolicyRule("ag", "cr", PolicyEffect.DENY, "reason")
        rule2 = PolicyRule.from_dict(rule.to_dict())
        assert rule2.agent_id == "ag"
        assert rule2.effect == PolicyEffect.DENY


class TestAuditEntry:
    def test_make_audit_entry(self):
        e = make_audit_entry("access", "agent-1", "gmail_key", "success", "detail")
        assert e.event_type == "access"
        assert e.agent_id == "agent-1"
        assert e.cred_name == "gmail_key"
        assert e.outcome == "success"
        assert e.entry_id.startswith("AUD-")

    def test_round_trip(self):
        e = make_audit_entry("load", "sys", "key", "success")
        e2 = AuditEntry.from_dict(e.to_dict())
        assert e2.entry_id == e.entry_id
        assert e2.event_type == "load"


class TestScanFinding:
    def test_to_dict(self):
        f = ScanFinding(
            file_path="test.md", line_number=5,
            pattern_name="aws_key", severity=ScanSeverity.CRITICAL,
            redacted_match="AKIA***", context="line context",
        )
        d = f.to_dict()
        assert d["severity"] == "critical"
        assert d["line_number"] == 5


# ===========================================================================
# 2. DotEnvParser
# ===========================================================================

class TestDotEnvParser:
    def test_basic_key_value(self):
        result = DotEnvParser.parse("KEY=value\n")
        assert result["KEY"] == "value"

    def test_double_quoted_value(self):
        result = DotEnvParser.parse('API_KEY="my secret"\n')
        assert result["API_KEY"] == "my secret"

    def test_single_quoted_value(self):
        result = DotEnvParser.parse("TOKEN='tok_abc'\n")
        assert result["TOKEN"] == "tok_abc"

    def test_comments_ignored(self):
        result = DotEnvParser.parse("# comment\nKEY=val\n")
        assert "KEY" in result
        assert len(result) == 1

    def test_export_prefix(self):
        result = DotEnvParser.parse("export MY_VAR=hello\n")
        assert result["MY_VAR"] == "hello"

    def test_empty_lines_ignored(self):
        result = DotEnvParser.parse("\n\nKEY=val\n\n")
        assert result == {"KEY": "val"}


# ===========================================================================
# 3. CredentialLoader
# ===========================================================================

class TestCredentialLoader:
    def test_load_dotenv_injects_env(self, dotenv_file, monkeypatch):
        monkeypatch.delenv("TEST_API_KEY", raising=False)
        monkeypatch.delenv("TEST_TOKEN", raising=False)
        loader = CredentialLoader()
        keys = loader.load_dotenv(dotenv_file)
        assert "TEST_API_KEY" in keys
        assert os.environ.get("TEST_API_KEY") == "secret123"

    def test_load_dotenv_no_override_by_default(self, dotenv_file, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "original")
        loader = CredentialLoader()
        loader.load_dotenv(dotenv_file)
        assert os.environ["TEST_API_KEY"] == "original"

    def test_load_dotenv_override_flag(self, dotenv_file, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "original")
        loader = CredentialLoader()
        loader.load_dotenv(dotenv_file, override=True)
        assert os.environ["TEST_API_KEY"] == "secret123"

    def test_load_dotenv_missing_file(self, tmp_path):
        loader = CredentialLoader()
        with pytest.raises(CredentialError, match="not found"):
            loader.load_dotenv(tmp_path / "nonexistent.env")

    def test_load_dotenv_safe_returns_empty_on_missing(self, tmp_path):
        loader = CredentialLoader()
        keys = loader.load_dotenv_safe(tmp_path / "nonexistent.env")
        assert keys == []

    def test_require_returns_value(self, monkeypatch):
        monkeypatch.setenv("MY_SECRET", "super_secret")
        loader = CredentialLoader()
        assert loader.require("MY_SECRET") == "super_secret"

    def test_require_raises_on_missing(self, monkeypatch):
        monkeypatch.delenv("NO_SUCH_KEY", raising=False)
        loader = CredentialLoader()
        with pytest.raises(CredentialError):
            loader.require("NO_SUCH_KEY")

    def test_require_all_success(self, monkeypatch):
        monkeypatch.setenv("A_KEY", "aval")
        monkeypatch.setenv("B_KEY", "bval")
        loader = CredentialLoader()
        result = loader.require_all(["A_KEY", "B_KEY"])
        assert result["A_KEY"] == "aval"
        assert result["B_KEY"] == "bval"

    def test_require_all_raises_with_missing_list(self, monkeypatch):
        monkeypatch.delenv("MISSING_1", raising=False)
        monkeypatch.delenv("MISSING_2", raising=False)
        loader = CredentialLoader()
        with pytest.raises(CredentialError):
            loader.require_all(["MISSING_1", "MISSING_2"])

    def test_is_set_true(self, monkeypatch):
        monkeypatch.setenv("PRESENT_KEY", "value")
        loader = CredentialLoader()
        assert loader.is_set("PRESENT_KEY") is True

    def test_is_set_false(self, monkeypatch):
        monkeypatch.delenv("ABSENT_KEY", raising=False)
        loader = CredentialLoader()
        assert loader.is_set("ABSENT_KEY") is False

    def test_check_all_set(self, monkeypatch):
        monkeypatch.setenv("SET_KEY", "val")
        monkeypatch.delenv("UNSET_KEY", raising=False)
        loader = CredentialLoader()
        result = loader.check_all_set(["SET_KEY", "UNSET_KEY"])
        assert result["SET_KEY"] is True
        assert result["UNSET_KEY"] is False


# ===========================================================================
# 4. SecretRedactor
# ===========================================================================

class TestSecretRedactor:
    def test_register_and_redact_known_secret(self):
        r = SecretRedactor()
        r.register_secret("my_super_secret_value")
        result = r.redact("token is my_super_secret_value here")
        assert "my_super_secret_value" not in result
        assert "[REDACTED]" in result

    def test_too_short_secret_not_registered(self):
        r = SecretRedactor()
        r.register_secret("abc")  # < 4 chars — should be ignored
        result = r.redact("abc is here")
        assert result == "abc is here"

    def test_redact_key_value_pattern(self):
        r = SecretRedactor()
        result = r.redact("password=hunter2")
        assert "hunter2" not in result
        assert "[REDACTED]" in result

    def test_redact_token_assignment(self):
        r = SecretRedactor()
        result = r.redact("token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
        assert "[REDACTED]" in result

    def test_redact_aws_access_key(self):
        r = SecretRedactor()
        result = r.redact("AKIAIOSFODNN7EXAMPLE is the key")
        assert "[REDACTED]" in result

    def test_redact_github_token(self):
        r = SecretRedactor()
        token = "ghp_" + "A" * 36
        result = r.redact(f"token: {token}")
        assert token not in result

    def test_redact_dict_masks_secret_keys(self):
        r = SecretRedactor()
        d = {"username": "alice", "password": "topsecret", "api_key": "abc123"}
        safe = r.redact_dict(d)
        assert safe["username"] == "alice"
        assert safe["password"] == "[REDACTED]"
        assert safe["api_key"] == "[REDACTED]"

    def test_redact_dict_recursive(self):
        r = SecretRedactor()
        d = {"inner": {"secret": "hide_me"}}
        safe = r.redact_dict(d)
        assert safe["inner"]["secret"] == "[REDACTED]"

    def test_is_safe_clean_text(self):
        r = SecretRedactor()
        assert r.is_safe("hello world no secrets here") is True

    def test_unregister_all(self):
        r = SecretRedactor()
        r.register_secret("my_known_secret")
        r.unregister_all()
        result = r.redact("my_known_secret")
        # After unregister, known literal is gone; pattern match may still catch it
        # but the direct known-secret substitution won't
        assert r._known_secrets == []

    def test_non_string_input_handled(self):
        r = SecretRedactor()
        result = r.redact(12345)  # type: ignore[arg-type]
        assert isinstance(result, str)


# ===========================================================================
# 5. AccessPolicy
# ===========================================================================

class TestAccessPolicy:
    def test_default_deny(self, policy: AccessPolicy):
        assert policy.is_allowed("any-agent", "any-cred") is False

    def test_default_allow_policy(self):
        p = AccessPolicy(default_effect=PolicyEffect.ALLOW)
        assert p.is_allowed("x", "y") is True

    def test_add_allow_grants_access(self, policy: AccessPolicy):
        policy.add_allow("agent-a", "gmail_key")
        assert policy.is_allowed("agent-a", "gmail_key") is True

    def test_allow_does_not_leak_to_other_agent(self, policy: AccessPolicy):
        policy.add_allow("agent-a", "gmail_key")
        assert policy.is_allowed("agent-b", "gmail_key") is False

    def test_explicit_deny_overrides_allow(self, policy: AccessPolicy):
        policy.add_allow("agent-a", "key")
        policy.add_deny("agent-a", "key")
        assert policy.is_allowed("agent-a", "key") is False

    def test_check_raises_policy_violation(self, policy: AccessPolicy):
        with pytest.raises(PolicyViolation):
            policy.check("no-access", "secret")

    def test_check_passes_for_allowed(self, policy: AccessPolicy):
        policy.add_allow("agent-a", "cred-1")
        policy.check("agent-a", "cred-1")  # must not raise

    def test_wildcard_agent_allows_all(self, policy: AccessPolicy):
        policy.add_allow("*", "shared_key")
        assert policy.is_allowed("anyone", "shared_key") is True

    def test_allowed_credentials_filter(self, policy: AccessPolicy):
        policy.add_allow("bot", "key-a")
        policy.add_allow("bot", "key-b")
        allowed = policy.allowed_credentials("bot", ["key-a", "key-b", "key-c"])
        assert set(allowed) == {"key-a", "key-b"}

    def test_round_trip(self, policy: AccessPolicy):
        policy.add_allow("ag", "cr")
        p2 = AccessPolicy.from_dict(policy.to_dict())
        assert p2.is_allowed("ag", "cr") is True


# ===========================================================================
# 6. CredentialStore
# ===========================================================================

class TestCredentialStore:
    def test_register_adds_spec(self, store: CredentialStore):
        spec = CredentialSpec("test_key", env_key="TEST_KEY")
        store.register(spec)
        assert any(s.name == "test_key" for s in store.list_specs())

    def test_load_from_env(self, store: CredentialStore, policy: AccessPolicy, monkeypatch):
        monkeypatch.setenv("GMAIL_KEY_ENV", "super_secret")
        spec = CredentialSpec("gmail", env_key="GMAIL_KEY_ENV")
        store.register(spec)
        result = store.load("gmail")
        assert result is True
        assert store.is_loaded("gmail")

    def test_load_missing_required_raises(self, store: CredentialStore, monkeypatch):
        monkeypatch.delenv("MISSING_CRED_KEY", raising=False)
        spec = CredentialSpec("missing", env_key="MISSING_CRED_KEY", required=True)
        store.register(spec)
        with pytest.raises(Exception):
            store.load("missing")

    def test_load_missing_optional_returns_false(self, store: CredentialStore, monkeypatch):
        monkeypatch.delenv("OPT_CRED_KEY", raising=False)
        spec = CredentialSpec("optional", env_key="OPT_CRED_KEY", required=False)
        store.register(spec)
        result = store.load("optional")
        assert result is False

    def test_load_unregistered_raises(self, store: CredentialStore):
        with pytest.raises(CredentialNotFoundError):
            store.load("nonexistent")

    def test_get_requires_policy_allow(
        self, store: CredentialStore, policy: AccessPolicy, monkeypatch
    ):
        monkeypatch.setenv("GET_CRED_KEY", "value123")
        spec = CredentialSpec("get_cred", env_key="GET_CRED_KEY")
        store.register(spec)
        store.load("get_cred")
        # No allow rule → should raise
        with pytest.raises(PolicyViolation):
            store.get("get_cred", "agent-x")

    def test_get_succeeds_with_allow(
        self, store: CredentialStore, policy: AccessPolicy, monkeypatch
    ):
        monkeypatch.setenv("ALLOWED_KEY", "secretvalue")
        spec = CredentialSpec("allowed_cred", env_key="ALLOWED_KEY")
        store.register(spec)
        store.load("allowed_cred")
        policy.add_allow("trusted-agent", "allowed_cred")
        value = store.get("allowed_cred", "trusted-agent")
        assert value == "secretvalue"

    def test_get_not_loaded_raises(
        self, store: CredentialStore, policy: AccessPolicy
    ):
        spec = CredentialSpec("unloaded", env_key="UNLOADED_KEY")
        store.register(spec)
        policy.add_allow("agent", "unloaded")
        with pytest.raises(CredentialNotFoundError, match="not loaded"):
            store.get("unloaded", "agent")

    def test_get_safe_returns_none_on_denied(self, store: CredentialStore):
        spec = CredentialSpec("safe_cred", env_key="SAFE_KEY")
        store.register(spec)
        assert store.get_safe("safe_cred", "no-access") is None

    def test_to_safe_dict_never_exposes_values(
        self, store: CredentialStore, policy: AccessPolicy, monkeypatch
    ):
        monkeypatch.setenv("SAFE_DICT_KEY", "top_secret")
        spec = CredentialSpec("safe_dict_cred", env_key="SAFE_DICT_KEY")
        store.register(spec)
        store.load("safe_dict_cred")
        d = store.to_safe_dict()
        assert "safe_dict_cred" in d
        info = d["safe_dict_cred"]
        assert "top_secret" not in str(info)
        assert info["loaded"] is True

    def test_rotation_due_returns_overdue_specs(self, store: CredentialStore):
        spec = CredentialSpec("rot_cred", env_key="ROT_KEY", rotation_days=30)
        spec.last_rotated = datetime.now(tz=timezone.utc) - timedelta(days=60)
        store.register(spec)
        due = store.rotation_due()
        assert any(s.name == "rot_cred" for s in due)

    def test_mark_rotated_clears_value(
        self, store: CredentialStore, policy: AccessPolicy, monkeypatch
    ):
        monkeypatch.setenv("ROTATED_KEY", "old_value")
        spec = CredentialSpec("rotated_cred", env_key="ROTATED_KEY")
        store.register(spec)
        store.load("rotated_cred")
        store.mark_rotated("rotated_cred")
        assert not store.is_loaded("rotated_cred")


# ===========================================================================
# 7. VaultGuard
# ===========================================================================

class TestVaultGuard:
    def test_scan_string_clean_returns_empty(self, vault: Path):
        guard = VaultGuard(vault)
        findings = guard.scan_string("This is a clean note with no secrets.")
        assert findings == []

    def test_scan_string_detects_aws_key(self, vault: Path):
        guard = VaultGuard(vault)
        # Valid AWS access key ID: AKIA + exactly 16 uppercase alphanumeric chars
        findings = guard.scan_string("key: AKIAIOSFODNN7EXAMPLE")
        assert any(f.pattern_name == "aws_access_key_id" for f in findings)

    def test_scan_string_detects_github_token(self, vault: Path):
        guard = VaultGuard(vault)
        token = "ghp_" + "A" * 40
        findings = guard.scan_string(f"token: {token}")
        assert any(f.pattern_name == "github_token" for f in findings)

    def test_scan_string_detects_private_key_header(self, vault: Path):
        guard = VaultGuard(vault)
        findings = guard.scan_string("-----BEGIN RSA PRIVATE KEY-----")
        assert any(f.pattern_name == "private_key_pem" for f in findings)

    def test_scan_string_detects_password_assignment(self, vault: Path):
        guard = VaultGuard(vault)
        findings = guard.scan_string("password=verylongpassword123", min_severity=ScanSeverity.HIGH)
        assert len(findings) > 0

    def test_is_safe_to_write_clean_content(self, vault: Path):
        guard = VaultGuard(vault)
        safe, findings = guard.is_safe_to_write("## My note\nNo secrets here.")
        assert safe is True
        assert findings == []

    def test_is_safe_to_write_detects_secret(self, vault: Path):
        guard = VaultGuard(vault)
        safe, findings = guard.is_safe_to_write(
            "key: AKIAIOSFODNN7EXAMPLE"
        )
        assert safe is False
        assert len(findings) > 0

    def test_severity_filter_excludes_low(self, vault: Path):
        guard = VaultGuard(vault)
        # medium hex pattern should be excluded when min_severity=HIGH
        findings = guard.scan_string(
            "hash: " + "a" * 40,
            min_severity=ScanSeverity.HIGH,
        )
        # generic_hex_secret is MEDIUM, should not appear
        assert all(f.pattern_name != "generic_hex_secret" for f in findings)

    def test_redacted_match_does_not_expose_full_secret(self, vault: Path):
        guard = VaultGuard(vault)
        token = "ghp_" + "B" * 40
        findings = guard.scan_string(f"token={token}")
        for f in findings:
            assert token not in f.redacted_match

    def test_scan_file_in_vault(self, vault: Path):
        guard = VaultGuard(vault)
        secret_file = vault / "10-KNOWLEDGE" / "test-note.md"
        secret_file.parent.mkdir(parents=True, exist_ok=True)
        secret_file.write_text("## Note\nAKIAIOSFODNN7EXAMPLE is the key\n")
        findings = guard.scan()
        assert any("test-note.md" in f.file_path for f in findings)


# ===========================================================================
# 8. SecurityAuditLogger
# ===========================================================================

class TestSecurityAuditLogger:
    def test_log_access_creates_files(self, audit_logger: SecurityAuditLogger):
        audit_logger.log_access("gmail_key", "gmail-watcher")
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        jsonl_files = list(
            (audit_logger._jsonl).glob(f"*{today}*.jsonl")
        )
        assert len(jsonl_files) > 0

    def test_log_denied_writes_entry(self, audit_logger: SecurityAuditLogger):
        audit_logger.log_denied("secret_key", "bad-agent")
        entries = audit_logger.read_entries()
        assert any(e.event_type == "denied" for e in entries)

    def test_log_load_writes_entry(self, audit_logger: SecurityAuditLogger):
        audit_logger.log_load("my_cred", "MY_ENV_KEY", CredentialSource.ENV_VAR)
        entries = audit_logger.read_entries()
        assert any(e.event_type == "load" for e in entries)

    def test_log_scan_finding(self, audit_logger: SecurityAuditLogger):
        audit_logger.log_scan_finding("unknown", "vault/note.md", "critical", "aws_key")
        entries = audit_logger.read_entries()
        assert any(e.event_type == "scan_finding" for e in entries)

    def test_log_rotation(self, audit_logger: SecurityAuditLogger):
        audit_logger.log_rotation("api_key")
        entries = audit_logger.read_entries()
        assert any(e.event_type == "rotation" for e in entries)

    def test_log_error_writes_error_file(self, audit_logger: SecurityAuditLogger, vault: Path):
        audit_logger.log_error("broken_cred", "Something went wrong")
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        error_files = list(audit_logger._errors.glob(f"*{today}*.md"))
        assert len(error_files) > 0

    def test_read_entries_returns_empty_for_missing_date(self, audit_logger: SecurityAuditLogger):
        entries = audit_logger.read_entries(date="1999-01-01")
        assert entries == []

    def test_audit_entries_never_contain_secret_value(self, audit_logger: SecurityAuditLogger):
        audit_logger.log_access("my_cred", "agent-1")
        entries = audit_logger.read_entries()
        for e in entries:
            assert "super_secret_value" not in e.details
            assert "super_secret_value" not in e.to_dict().get("details", "")


# ===========================================================================
# 9. SecuritySkill (facade)
# ===========================================================================

class TestSecuritySkill:
    def test_register_and_load(self, skill: SecuritySkill, monkeypatch):
        monkeypatch.setenv("FACADE_TEST_KEY", "facade_secret")
        spec = CredentialSpec("facade_cred", env_key="FACADE_TEST_KEY")
        skill.register(spec)
        results = skill.load_all()
        assert results.get("facade_cred") is True
        assert skill.is_loaded("facade_cred")

    def test_get_requires_allow_rule(self, skill: SecuritySkill, monkeypatch):
        monkeypatch.setenv("DENY_TEST_KEY", "value")
        spec = CredentialSpec("deny_cred", env_key="DENY_TEST_KEY")
        skill.register(spec)
        skill.load("deny_cred")
        with pytest.raises(PolicyViolation):
            skill.get("deny_cred", "unauthorized-agent")

    def test_allow_and_get(self, skill: SecuritySkill, monkeypatch):
        monkeypatch.setenv("ALLOW_TEST_KEY", "allowed_value")
        spec = CredentialSpec("allow_cred", env_key="ALLOW_TEST_KEY")
        skill.register(spec)
        skill.load("allow_cred")
        skill.allow("trusted-bot", "allow_cred", reason="integration test")
        value = skill.get("allow_cred", "trusted-bot")
        assert value == "allowed_value"

    def test_deny_overrides_allow(self, skill: SecuritySkill, monkeypatch):
        monkeypatch.setenv("DENY_OVR_KEY", "secret")
        spec = CredentialSpec("deny_ovr", env_key="DENY_OVR_KEY")
        skill.register(spec)
        skill.load("deny_ovr")
        skill.allow("bot", "deny_ovr")
        skill.deny("bot", "deny_ovr")
        with pytest.raises(PolicyViolation):
            skill.get("deny_ovr", "bot")

    def test_get_safe_returns_none_on_denied(self, skill: SecuritySkill):
        spec = CredentialSpec("safe_get_cred", env_key="SAFE_GET_KEY", required=False)
        skill.register(spec)
        result = skill.get_safe("safe_get_cred", "no-agent")
        assert result is None

    def test_redact_masks_secrets(self, skill: SecuritySkill):
        result = skill.redact("password=hunter2_value")
        assert "hunter2_value" not in result

    def test_scan_vault_clean(self, skill: SecuritySkill):
        findings = skill.scan_vault()
        # A clean vault should have no critical/high findings
        critical = [f for f in findings if f.severity in (ScanSeverity.CRITICAL, ScanSeverity.HIGH)]
        assert len(critical) == 0

    def test_check_credentials_status_no_values(self, skill: SecuritySkill, monkeypatch):
        monkeypatch.setenv("STATUS_KEY", "secretvalue")
        spec = CredentialSpec("status_cred", env_key="STATUS_KEY")
        skill.register(spec)
        skill.load("status_cred")
        status = skill.check_credentials_status()
        assert "status_cred" in status
        assert "secretvalue" not in str(status)

    def test_list_credentials(self, skill: SecuritySkill):
        spec1 = CredentialSpec("cred_a", env_key="CRED_A", required=False)
        spec2 = CredentialSpec("cred_b", env_key="CRED_B", required=False)
        skill.register_many([spec1, spec2])
        creds = skill.list_credentials()
        names = [c.name for c in creds]
        assert "cred_a" in names
        assert "cred_b" in names

    def test_rotation_due_empty_initially(self, skill: SecuritySkill):
        due = skill.rotation_due()
        assert isinstance(due, list)

    def test_mark_rotated(self, skill: SecuritySkill, monkeypatch):
        monkeypatch.setenv("ROTATE_ME_KEY", "old_secret")
        spec = CredentialSpec("rotate_me", env_key="ROTATE_ME_KEY")
        skill.register(spec)
        skill.load("rotate_me")
        skill.mark_rotated("rotate_me")
        assert not skill.is_loaded("rotate_me")

    def test_is_allowed(self, skill: SecuritySkill):
        spec = CredentialSpec("perm_cred", env_key="PERM_KEY", required=False)
        skill.register(spec)
        assert skill.is_allowed("any-agent", "perm_cred") is False
        skill.allow("any-agent", "perm_cred")
        assert skill.is_allowed("any-agent", "perm_cred") is True


# ===========================================================================
# 10. CLI
# ===========================================================================

class TestCLI:
    def test_build_parser_has_subcommands(self):
        parser = build_parser()
        assert parser is not None

    def test_verify_command_exits_zero_no_creds(self, vault: Path, capsys):
        """verify with no registered creds → all ok → exit 0."""
        rc = cli_main(["--vault", str(vault), "verify"])
        assert rc == 0

    def test_scan_vault_clean_exits_zero(self, vault: Path, capsys):
        rc = cli_main(["--vault", str(vault), "scan-vault"])
        assert rc == 0

    def test_scan_vault_with_secret_exits_nonzero(self, vault: Path):
        secret_file = vault / "bad-file.md"
        secret_file.write_text("AKIAIOSFODNN7EXAMPLE\n")
        rc = cli_main(["--vault", str(vault), "scan-vault"])
        assert rc != 0

    def test_list_credentials_no_creds(self, vault: Path, capsys):
        rc = cli_main(["--vault", str(vault), "list-credentials"])
        assert rc == 0

    def test_rotate_reminder_no_due(self, vault: Path, capsys):
        rc = cli_main(["--vault", str(vault), "rotate-reminder"])
        assert rc == 0

    def test_audit_empty(self, vault: Path, capsys):
        rc = cli_main(["--vault", str(vault), "audit"])
        assert rc == 0
