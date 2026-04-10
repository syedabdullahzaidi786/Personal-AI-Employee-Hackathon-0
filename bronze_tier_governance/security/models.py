"""
SECURITY_AND_CREDENTIAL_MANAGEMENT_SKILL — Data Models
Phase 1: Credential specs, access policy, audit entries, rotation policy.

Constitution compliance:
  - Section 8: Credential Storage rules
  - Principle VI: Fail Safe — security errors must be explicit, never silent
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CredentialType(str, Enum):
    API_KEY      = "api_key"
    PASSWORD     = "password"
    TOKEN        = "token"
    OAUTH_SECRET = "oauth_secret"
    PRIVATE_KEY  = "private_key"
    CONNECTION_STRING = "connection_string"
    GENERIC      = "generic"


class CredentialSource(str, Enum):
    ENV_VAR   = "env_var"    # Loaded from os.environ
    DOTENV    = "dotenv"     # Loaded from .env file
    INLINE    = "inline"     # Provided directly at runtime (testing only)


class PolicyEffect(str, Enum):
    ALLOW = "allow"
    DENY  = "deny"


class ScanSeverity(str, Enum):
    CRITICAL = "critical"   # Clear plaintext secret found
    HIGH     = "high"       # High-confidence pattern match
    MEDIUM   = "medium"     # Possible secret, needs review
    INFO     = "info"       # Informational finding


# ---------------------------------------------------------------------------
# Credential Spec (metadata — never stores the value)
# ---------------------------------------------------------------------------

@dataclass
class CredentialSpec:
    """
    Declarative description of a credential.

    The actual secret VALUE is never stored in this object.
    Values live only in OS environment / .env at runtime.
    """
    name:         str                   # Logical name, e.g. "gmail_api_key"
    env_key:      str                   # OS env var that holds the value
    cred_type:    CredentialType = CredentialType.GENERIC
    description:  str = ""
    required:     bool = True
    rotation_days: int = 90             # How often to rotate (0 = no rotation tracking)
    last_rotated: Optional[datetime] = None
    owner_agent:  str = ""              # Agent that "owns" this credential

    def to_dict(self) -> dict:
        return {
            "name":          self.name,
            "env_key":       self.env_key,
            "cred_type":     self.cred_type.value,
            "description":   self.description,
            "required":      self.required,
            "rotation_days": self.rotation_days,
            "last_rotated":  self.last_rotated.isoformat() if self.last_rotated else None,
            "owner_agent":   self.owner_agent,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CredentialSpec":
        obj = cls(
            name=d["name"],
            env_key=d["env_key"],
            cred_type=CredentialType(d.get("cred_type", "generic")),
            description=d.get("description", ""),
            required=d.get("required", True),
            rotation_days=d.get("rotation_days", 90),
            owner_agent=d.get("owner_agent", ""),
        )
        if d.get("last_rotated"):
            obj.last_rotated = datetime.fromisoformat(d["last_rotated"])
        return obj

    @property
    def rotation_due(self) -> bool:
        """Return True if rotation is overdue."""
        if self.rotation_days <= 0 or self.last_rotated is None:
            return False
        due_at = self.last_rotated + timedelta(days=self.rotation_days)
        return datetime.now(tz=timezone.utc) >= due_at

    @property
    def days_until_rotation(self) -> Optional[int]:
        if self.rotation_days <= 0 or self.last_rotated is None:
            return None
        due_at = self.last_rotated + timedelta(days=self.rotation_days)
        delta  = (due_at - datetime.now(tz=timezone.utc)).days
        return delta


# ---------------------------------------------------------------------------
# Access Policy Rule
# ---------------------------------------------------------------------------

@dataclass
class PolicyRule:
    """
    Declares which agents can access which credentials.

    Implements least-privilege: default-deny, explicit allow required.
    """
    agent_id:    str               # Agent identifier; "*" matches any
    cred_name:   str               # Credential name; "*" matches any
    effect:      PolicyEffect = PolicyEffect.ALLOW
    reason:      str = ""          # Human-readable justification

    def matches(self, agent_id: str, cred_name: str) -> bool:
        agent_match = self.agent_id == "*" or self.agent_id == agent_id
        cred_match  = self.cred_name == "*" or self.cred_name == cred_name
        return agent_match and cred_match

    def to_dict(self) -> dict:
        return {
            "agent_id":  self.agent_id,
            "cred_name": self.cred_name,
            "effect":    self.effect.value,
            "reason":    self.reason,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PolicyRule":
        return cls(
            agent_id=d["agent_id"],
            cred_name=d["cred_name"],
            effect=PolicyEffect(d.get("effect", "allow")),
            reason=d.get("reason", ""),
        )


# ---------------------------------------------------------------------------
# Audit Entry (immutable, append-only)
# ---------------------------------------------------------------------------

@dataclass
class AuditEntry:
    """Immutable record of a credential access or security event."""
    entry_id:    str
    event_type:  str               # "access", "load", "denied", "scan_finding", "rotation_due"
    agent_id:    str               # Who triggered the event
    cred_name:   str               # Credential name (NEVER the value)
    timestamp:   datetime
    outcome:     str               # "success" | "denied" | "error"
    details:     str = ""          # Extra context (no secret values!)
    source_file: Optional[str] = None  # For scan findings

    def to_dict(self) -> dict:
        return {
            "entry_id":    self.entry_id,
            "event_type":  self.event_type,
            "agent_id":    self.agent_id,
            "cred_name":   self.cred_name,
            "timestamp":   self.timestamp.isoformat(),
            "outcome":     self.outcome,
            "details":     self.details,
            "source_file": self.source_file,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AuditEntry":
        return cls(
            entry_id=d["entry_id"],
            event_type=d["event_type"],
            agent_id=d["agent_id"],
            cred_name=d["cred_name"],
            timestamp=datetime.fromisoformat(d["timestamp"]),
            outcome=d.get("outcome", ""),
            details=d.get("details", ""),
            source_file=d.get("source_file"),
        )


# ---------------------------------------------------------------------------
# Vault Scan Finding
# ---------------------------------------------------------------------------

@dataclass
class ScanFinding:
    """A potential secret exposure detected in the vault."""
    file_path:   str
    line_number: int
    pattern_name: str              # Which pattern matched (e.g. "api_key_generic")
    severity:    ScanSeverity
    redacted_match: str            # The matched text with secret chars replaced by ***
    context:     str = ""          # Line content with secret redacted

    def to_dict(self) -> dict:
        return {
            "file_path":      self.file_path,
            "line_number":    self.line_number,
            "pattern_name":   self.pattern_name,
            "severity":       self.severity.value,
            "redacted_match": self.redacted_match,
            "context":        self.context,
        }


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def make_audit_entry(
    event_type: str,
    agent_id: str,
    cred_name: str,
    outcome: str,
    details: str = "",
    source_file: Optional[str] = None,
) -> AuditEntry:
    return AuditEntry(
        entry_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
        event_type=event_type,
        agent_id=agent_id,
        cred_name=cred_name,
        timestamp=datetime.now(tz=timezone.utc),
        outcome=outcome,
        details=details,
        source_file=source_file,
    )
