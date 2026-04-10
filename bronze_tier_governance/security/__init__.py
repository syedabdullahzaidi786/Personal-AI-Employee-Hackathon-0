"""
SECURITY_AND_CREDENTIAL_MANAGEMENT_SKILL — Phase 1
Secure credential management: load, store, enforce policy, redact, audit, scan.

Constitution compliance:
  - Section 8: Credential Storage rules (env vars only, never vault plaintext)
  - Principle VI: Fail Safe — security errors are explicit and logged
  - Tier 4 (Critical): HITL required for all operations (stub in Phase 1)

Public surface::

    from skills.safety.security import SecuritySkill
    from skills.safety.security.models import CredentialSpec, CredentialType

    skill = SecuritySkill(vault_root="/path/to/obsidian-vault")

    # Declare what credentials this system needs
    skill.register(CredentialSpec(
        name="gmail_api_key",
        env_key="GMAIL_API_KEY",
        cred_type=CredentialType.API_KEY,
        description="Gmail API key for email watcher",
        rotation_days=90,
    ))

    # Load from .env + environment
    skill.load_dotenv(".env")
    skill.load_all()

    # Retrieve (policy-enforced, access logged)
    value = skill.get("gmail_api_key", agent_id="gmail-watcher")

    # Scan vault for accidental secret exposure
    findings = skill.scan_vault()

    # Redact secrets from log strings
    safe_log = skill.redact("API_KEY=super-secret-value")
"""

from pathlib import Path
from typing import Optional

from .audit import SecurityAuditLogger
from .loader import CredentialLoader
from .models import (
    AuditEntry,
    CredentialSource,
    CredentialSpec,
    CredentialType,
    PolicyEffect,
    PolicyRule,
    ScanFinding,
    ScanSeverity,
    make_audit_entry,
)
from .policy import AccessPolicy, PolicyViolation
from .redactor import SecretRedactor, redact, redact_dict, register_secret
from .store import CredentialNotFoundError, CredentialStore
from .vault_guard import VaultGuard


class SecuritySkill:
    """
    High-level facade for SECURITY_AND_CREDENTIAL_MANAGEMENT_SKILL Phase 1.

    Composes: CredentialLoader + SecretRedactor + AccessPolicy +
              CredentialStore + VaultGuard + SecurityAuditLogger.
    """

    def __init__(
        self,
        vault_root: str | Path,
        default_policy: PolicyEffect = PolicyEffect.DENY,
    ) -> None:
        vault              = Path(vault_root)
        self._redactor     = SecretRedactor()
        self._loader       = CredentialLoader()
        self._audit        = SecurityAuditLogger(vault)
        self._policy       = AccessPolicy(default_effect=default_policy)
        self._store        = CredentialStore(
            policy=self._policy,
            loader=self._loader,
            redactor=self._redactor,
            audit=self._audit,
        )
        self._guard        = VaultGuard(vault)

    # ------------------------------------------------------------------
    # Credential Registration
    # ------------------------------------------------------------------

    def register(self, spec: CredentialSpec) -> None:
        """Register a credential spec."""
        self._store.register(spec)

    def register_many(self, specs: list[CredentialSpec]) -> None:
        for spec in specs:
            self.register(spec)

    # ------------------------------------------------------------------
    # Policy
    # ------------------------------------------------------------------

    def allow(self, agent_id: str, cred_name: str, reason: str = "") -> None:
        """Grant *agent_id* access to *cred_name*."""
        self._policy.add_allow(agent_id, cred_name, reason)
        self._audit.log_policy_change(agent_id, f"ALLOW {agent_id} → {cred_name}: {reason}")

    def deny(self, agent_id: str, cred_name: str, reason: str = "") -> None:
        """Explicitly deny *agent_id* access to *cred_name*."""
        self._policy.add_deny(agent_id, cred_name, reason)
        self._audit.log_policy_change(agent_id, f"DENY {agent_id} → {cred_name}: {reason}")

    def is_allowed(self, agent_id: str, cred_name: str) -> bool:
        return self._policy.is_allowed(agent_id, cred_name)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_dotenv(self, path: str | Path = ".env", *, override: bool = False) -> list[str]:
        """Parse a .env file and inject into os.environ."""
        return self._loader.load_dotenv(path, override=override)

    def load_dotenv_safe(self, path: str | Path = ".env") -> list[str]:
        """Like load_dotenv but returns [] if the file is missing."""
        return self._loader.load_dotenv_safe(path)

    def load_all(self) -> dict[str, bool]:
        """Load all registered credentials from the environment."""
        return self._store.load_all()

    def load(self, cred_name: str) -> bool:
        """Load a single credential by name."""
        return self._store.load(cred_name)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, cred_name: str, agent_id: str) -> str:
        """Return credential value. Raises on missing or denied."""
        return self._store.get(cred_name, agent_id)

    def get_safe(self, cred_name: str, agent_id: str) -> Optional[str]:
        """Return credential value or None."""
        return self._store.get_safe(cred_name, agent_id)

    # ------------------------------------------------------------------
    # Redaction
    # ------------------------------------------------------------------

    def redact(self, text: str) -> str:
        """Redact secrets from *text* before logging."""
        return self._redactor.redact(text)

    def redact_dict(self, d) -> dict:
        """Recursively redact secrets from *d* before logging."""
        return self._redactor.redact_dict(d)

    def register_secret(self, value: str) -> None:
        """Register a literal secret value for redaction (no-op if empty)."""
        self._redactor.register_secret(value)

    # ------------------------------------------------------------------
    # Vault scanning
    # ------------------------------------------------------------------

    def scan_vault(
        self,
        path: Optional[str] = None,
        min_severity: ScanSeverity = ScanSeverity.MEDIUM,
    ) -> list[ScanFinding]:
        """Scan the vault for accidentally committed secrets."""
        findings = self._guard.scan(path=path, min_severity=min_severity)
        for f in findings:
            self._audit.log_scan_finding(
                cred_name="unknown",
                file_path=f.file_path,
                severity=f.severity.value,
                pattern=f.pattern_name,
            )
        return findings

    def is_safe_to_write(self, content: str) -> tuple[bool, list[ScanFinding]]:
        """Return (True, []) if content is safe to write to vault."""
        return self._guard.is_safe_to_write(content)

    # ------------------------------------------------------------------
    # Rotation tracking
    # ------------------------------------------------------------------

    def rotation_due(self) -> list[CredentialSpec]:
        """Return specs whose rotation is overdue."""
        due = self._store.rotation_due()
        for spec in due:
            days = abs(spec.days_until_rotation or 0)
            self._audit.log_rotation_due(spec.name, days)
        return due

    def mark_rotated(self, cred_name: str) -> None:
        """Record that a credential was manually rotated and reload is needed."""
        self._store.mark_rotated(cred_name)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def check_credentials_status(self) -> dict:
        """Return safe status dict — NO secret values."""
        return self._store.to_safe_dict()

    def to_safe_dict(self) -> dict:
        """Alias for check_credentials_status()."""
        return self._store.to_safe_dict()

    def is_loaded(self, cred_name: str) -> bool:
        return self._store.is_loaded(cred_name)

    def list_credentials(self) -> list[CredentialSpec]:
        return self._store.list_specs()

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def read_audit(self, date: Optional[str] = None) -> list[AuditEntry]:
        return self._audit.read_entries(date)


__all__ = [
    "SecuritySkill",
    "CredentialStore",
    "CredentialLoader",
    "SecretRedactor",
    "AccessPolicy",
    "VaultGuard",
    "SecurityAuditLogger",
    # Models
    "CredentialSpec",
    "CredentialType",
    "CredentialSource",
    "PolicyRule",
    "PolicyEffect",
    "ScanFinding",
    "ScanSeverity",
    "AuditEntry",
    # Errors
    "PolicyViolation",
    "CredentialNotFoundError",
    # Convenience
    "redact",
    "redact_dict",
    "register_secret",
    "make_audit_entry",
]
