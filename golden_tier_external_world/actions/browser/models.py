"""
BROWSER_MCP_SKILL — Data Models
Phase 1: BrowserRequest, BrowserResult, BrowserConfig, BrowserActionType, BrowserActionStatus.

Constitution compliance:
  - Section 9: Skill Design Rules — atomic, testable, composable
  - Section 8: Credential Storage — credentials_name is a reference, never the secret
  - Principle VI: Fail Safe — explicit statuses, no silent errors
  - Tier 2 (Medium-risk): HITL required for all browser actions
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class BrowserActionType:
    """Supported browser action types (Phase 1)."""
    OPEN_URL      = "open_url"
    EXTRACT_TEXT  = "extract_text"


class BrowserActionStatus:
    """Status constants for BrowserResult."""
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED         = "APPROVED"
    SUCCESS          = "SUCCESS"
    DENIED           = "DENIED"
    FAILED           = "FAILED"


class BrowserEventType:
    """Browser action event type string constants."""
    URL_OPENED        = "browser_url_opened"
    TEXT_EXTRACTED    = "browser_text_extracted"
    ACTION_DENIED     = "browser_action_denied"
    ACTION_FAILED     = "browser_action_failed"
    APPROVAL_REQUESTED = "browser_approval_requested"


# ---------------------------------------------------------------------------
# BrowserRequest — safe representation of a browser action request
# ---------------------------------------------------------------------------

@dataclass
class BrowserRequest:
    """
    Safe representation of a browser action request.

    Design contract:
      - Never stores auth tokens or passwords.
      - credentials_name is a logical name resolved by SecuritySkill.
      - extracted content is capped at 50 000 chars to prevent log bloat.
    """
    action:           str                    # BrowserActionType constant
    url:              str
    request_id:       str                    = field(default_factory=lambda: f"BROWSER-{uuid.uuid4().hex[:8].upper()}")
    selector:         str                    = ""    # CSS/XPath selector for extract_text
    max_content_len:  int                    = 50_000
    tier:             int                    = 2    # Default: Medium-risk → HITL required
    credentials_name: str                    = "browser_credential"
    submitted_at:     Optional[datetime]     = None

    def __post_init__(self) -> None:
        if self.submitted_at is None:
            self.submitted_at = datetime.now(tz=timezone.utc)

    def to_dict(self) -> dict:
        return {
            "request_id":       self.request_id,
            "action":           self.action,
            "url":              self.url,
            "selector":         self.selector,
            "tier":             self.tier,
            "credentials_name": self.credentials_name,
            "submitted_at":     self.submitted_at.isoformat() if self.submitted_at else None,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BrowserRequest":
        submitted_at = None
        if d.get("submitted_at"):
            submitted_at = datetime.fromisoformat(d["submitted_at"])
        return cls(
            request_id=d.get("request_id", f"BROWSER-{uuid.uuid4().hex[:8].upper()}"),
            action=d["action"],
            url=d["url"],
            selector=d.get("selector", ""),
            tier=d.get("tier", 2),
            credentials_name=d.get("credentials_name", "browser_credential"),
            submitted_at=submitted_at,
        )


# ---------------------------------------------------------------------------
# BrowserResult — outcome of a browser action
# ---------------------------------------------------------------------------

@dataclass
class BrowserResult:
    """Result of a browser action execution."""
    request_id:      str
    action:          str
    status:          str                   # BrowserActionStatus constant
    url:             str                   = ""
    content:         str                   = ""   # page title or extracted text
    status_code:     int                   = 0    # HTTP status (mock: 200/0)
    error:           str                   = ""
    adapter:         str                   = "mock"
    hitl_request_id: str                   = ""
    executed_at:     Optional[datetime]    = None

    def to_dict(self) -> dict:
        return {
            "request_id":      self.request_id,
            "action":          self.action,
            "status":          self.status,
            "url":             self.url,
            "content":         self.content[:500],   # safe preview
            "status_code":     self.status_code,
            "error":           self.error,
            "adapter":         self.adapter,
            "hitl_request_id": self.hitl_request_id,
            "executed_at":     self.executed_at.isoformat() if self.executed_at else None,
        }


# ---------------------------------------------------------------------------
# BrowserConfig
# ---------------------------------------------------------------------------

@dataclass
class BrowserConfig:
    """
    Configuration for BrowserSkill.

    credentials_name is a logical name resolved by SecuritySkill.
    The actual API key / session token is never stored here.
    """
    vault_root:       str = ""
    credentials_name: str = "browser_credential"
    default_tier:     int = 2     # Medium-risk by default

    def to_dict(self) -> dict:
        return {
            "vault_root":       self.vault_root,
            "credentials_name": self.credentials_name,
            "default_tier":     self.default_tier,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BrowserConfig":
        return cls(
            vault_root=d.get("vault_root", ""),
            credentials_name=d.get("credentials_name", "browser_credential"),
            default_tier=d.get("default_tier", 2),
        )


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def make_open_url_request(
    url: str,
    tier: int = 2,
    credentials_name: str = "browser_credential",
) -> BrowserRequest:
    """Create an open_url BrowserRequest."""
    return BrowserRequest(
        action=BrowserActionType.OPEN_URL,
        url=url,
        tier=tier,
        credentials_name=credentials_name,
    )


def make_extract_text_request(
    url: str,
    selector: str = "",
    tier: int = 2,
    credentials_name: str = "browser_credential",
) -> BrowserRequest:
    """Create an extract_text BrowserRequest."""
    return BrowserRequest(
        action=BrowserActionType.EXTRACT_TEXT,
        url=url,
        selector=selector,
        tier=tier,
        credentials_name=credentials_name,
    )
