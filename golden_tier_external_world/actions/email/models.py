"""
EMAIL_MCP_ACTION_SKILL — Data Models
Phase 1: EmailRequest, EmailResult, EmailConfig, EmailActionStatus, EmailEventType.

Constitution compliance:
  - Section 9: Skill Design Rules — atomic, testable, composable
  - Section 8: Credential Storage — credentials_name is a reference, never the secret
  - Principle VI: Fail Safe — explicit statuses, no silent errors
  - Tier 3 (High-risk): HITL required for all sends
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class EmailActionStatus:
    """Status constants for EmailResult."""
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED         = "APPROVED"
    SENT             = "SENT"
    DENIED           = "DENIED"
    FAILED           = "FAILED"


class EmailEventType:
    """Email action event type string constants."""
    EMAIL_SENT         = "email_sent"
    EMAIL_DENIED       = "email_denied"
    EMAIL_FAILED       = "email_failed"
    EMAIL_QUEUED       = "email_queued"
    APPROVAL_REQUESTED = "email_approval_requested"


# ---------------------------------------------------------------------------
# EmailRequest — safe representation of a send request (no secrets)
# ---------------------------------------------------------------------------

@dataclass
class EmailRequest:
    """
    Safe representation of an email send request.

    Design contract:
      - Never stores SMTP passwords or raw OAuth tokens.
      - credentials_name is a logical name resolved by SecuritySkill.
      - body is capped at 10 000 chars to prevent log bloat.
      - attachment_names lists filenames only, not file contents.
    """
    to:               list[str]
    subject:          str
    body:             str
    request_id:       str             = field(default_factory=lambda: f"EMAIL-{uuid.uuid4().hex[:8].upper()}")
    sender:           str             = ""
    cc:               list[str]       = field(default_factory=list)
    bcc:              list[str]       = field(default_factory=list)
    attachment_names: list[str]       = field(default_factory=list)
    tier:             int             = 3        # Default: High-risk → HITL required
    credentials_name: str             = "smtp_credential"
    submitted_at:     Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.submitted_at is None:
            self.submitted_at = datetime.now(tz=timezone.utc)
        # Cap body length to prevent log bloat
        if len(self.body) > 10_000:
            self.body = self.body[:10_000]

    def to_dict(self) -> dict:
        return {
            "request_id":       self.request_id,
            "to":               self.to,
            "subject":          self.subject,
            "body_preview":     self.body[:500],   # safe preview only
            "sender":           self.sender,
            "cc":               self.cc,
            "bcc":              self.bcc,
            "attachment_names": self.attachment_names,
            "tier":             self.tier,
            "credentials_name": self.credentials_name,
            "submitted_at":     self.submitted_at.isoformat() if self.submitted_at else None,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EmailRequest":
        submitted_at = None
        if d.get("submitted_at"):
            submitted_at = datetime.fromisoformat(d["submitted_at"])
        return cls(
            request_id=d.get("request_id", f"EMAIL-{uuid.uuid4().hex[:8].upper()}"),
            to=d["to"],
            subject=d["subject"],
            body=d.get("body", d.get("body_preview", "")),
            sender=d.get("sender", ""),
            cc=d.get("cc", []),
            bcc=d.get("bcc", []),
            attachment_names=d.get("attachment_names", []),
            tier=d.get("tier", 3),
            credentials_name=d.get("credentials_name", "smtp_credential"),
            submitted_at=submitted_at,
        )


# ---------------------------------------------------------------------------
# EmailResult — outcome of a send attempt
# ---------------------------------------------------------------------------

@dataclass
class EmailResult:
    """Result of an email send attempt."""
    request_id:      str
    status:          str                   # EmailActionStatus constant
    sent_at:         Optional[datetime]  = None
    error:           str                 = ""
    adapter:         str                 = "mock"
    hitl_request_id: str                 = ""  # HITL ApprovalRequest.request_id if queued

    def to_dict(self) -> dict:
        return {
            "request_id":      self.request_id,
            "status":          self.status,
            "sent_at":         self.sent_at.isoformat() if self.sent_at else None,
            "error":           self.error,
            "adapter":         self.adapter,
            "hitl_request_id": self.hitl_request_id,
        }


# ---------------------------------------------------------------------------
# EmailConfig
# ---------------------------------------------------------------------------

@dataclass
class EmailConfig:
    """
    Configuration for EmailActionSkill.

    credentials_name is a logical name resolved by SecuritySkill.
    The actual SMTP password / OAuth token is never stored here.
    """
    sender_address:   str
    vault_root:       str = ""
    credentials_name: str = "smtp_credential"
    default_tier:     int = 3   # High-risk by default
    max_to:           int = 50  # Max recipients per email

    def to_dict(self) -> dict:
        return {
            "sender_address":   self.sender_address,
            "vault_root":       self.vault_root,
            "credentials_name": self.credentials_name,
            "default_tier":     self.default_tier,
            "max_to":           self.max_to,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EmailConfig":
        return cls(
            sender_address=d["sender_address"],
            vault_root=d.get("vault_root", ""),
            credentials_name=d.get("credentials_name", "smtp_credential"),
            default_tier=d.get("default_tier", 3),
            max_to=d.get("max_to", 50),
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_email_request(
    to: list[str] | str,
    subject: str,
    body: str,
    sender: str = "",
    cc: Optional[list[str]] = None,
    bcc: Optional[list[str]] = None,
    attachment_names: Optional[list[str]] = None,
    tier: int = 3,
    credentials_name: str = "smtp_credential",
) -> EmailRequest:
    """Create an EmailRequest with an auto-generated ID and UTC timestamp."""
    if isinstance(to, str):
        to = [to]
    return EmailRequest(
        to=to,
        subject=subject,
        body=body,
        sender=sender,
        cc=cc or [],
        bcc=bcc or [],
        attachment_names=attachment_names or [],
        tier=tier,
        credentials_name=credentials_name,
    )
