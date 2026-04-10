"""
GMAIL_WATCHER_SKILL — Data Models
Phase 1: GmailMessage, GmailConfig, GmailEventType.

Constitution compliance:
  - Section 9: Skill Design Rules — atomic, testable, composable
  - Principle VI: Fail Safe — structured events, no silent errors
  - Section 8: Credential Storage — credentials_name is a reference, never the secret
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Enums (string-based for WatcherEvent.event_type compatibility)
# ---------------------------------------------------------------------------

class GmailEventType:
    """Gmail-specific event type string constants."""
    NEW_MESSAGE         = "gmail_new_message"
    NEW_THREAD          = "gmail_new_thread"
    ATTACHMENT_RECEIVED = "gmail_attachment_received"
    POLL_HEARTBEAT      = "gmail_poll_heartbeat"


# ---------------------------------------------------------------------------
# GmailMessage — safe representation of a Gmail message (no secrets)
# ---------------------------------------------------------------------------

@dataclass
class GmailMessage:
    """
    Safe representation of a Gmail message.

    Design contract:
      - Never stores raw auth tokens or passwords.
      - snippet is max 200 chars — no full body (body can contain sensitive data).
      - attachment_names lists filenames only, not file contents.
    """
    message_id:       str
    thread_id:        str
    subject:          str
    sender:           str
    recipient:        str
    snippet:          str                    # ≤200 chars preview
    labels:           list[str]              = field(default_factory=list)
    received_at:      Optional[datetime]     = None
    has_attachments:  bool                   = False
    attachment_names: list[str]              = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "message_id":       self.message_id,
            "thread_id":        self.thread_id,
            "subject":          self.subject,
            "sender":           self.sender,
            "recipient":        self.recipient,
            "snippet":          self.snippet[:200],
            "labels":           self.labels,
            "received_at":      self.received_at.isoformat() if self.received_at else None,
            "has_attachments":  self.has_attachments,
            "attachment_names": self.attachment_names,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GmailMessage":
        received_at = None
        if d.get("received_at"):
            received_at = datetime.fromisoformat(d["received_at"])
        return cls(
            message_id=d["message_id"],
            thread_id=d["thread_id"],
            subject=d["subject"],
            sender=d["sender"],
            recipient=d["recipient"],
            snippet=d["snippet"],
            labels=d.get("labels", []),
            received_at=received_at,
            has_attachments=d.get("has_attachments", False),
            attachment_names=d.get("attachment_names", []),
        )


# ---------------------------------------------------------------------------
# GmailConfig
# ---------------------------------------------------------------------------

@dataclass
class GmailConfig:
    """
    Configuration for GmailWatcher.

    credentials_name is a logical name passed to SecuritySkill.get_credential().
    The actual OAuth token / API key is never stored in this config.
    """
    account_email:      str
    watcher_id:         str   = ""          # Defaults to "gmail-<account_email>" if empty
    vault_root:         str   = ""
    credentials_name:   str   = "gmail_api_key"
    max_results:        int   = 10          # Max messages per poll
    filter_labels:      list[str] = field(default_factory=list)  # [] = all labels
    mark_read_on_poll:  bool  = False       # True only with real API
    poll_interval_secs: float = 60.0
    tier:               int   = 2           # HITL tier for emitted events

    def __post_init__(self) -> None:
        if not self.watcher_id:
            safe = self.account_email.replace("@", "_at_").replace(".", "_")
            self.watcher_id = f"gmail-{safe}"

    def to_dict(self) -> dict:
        return {
            "account_email":     self.account_email,
            "watcher_id":        self.watcher_id,
            "vault_root":        self.vault_root,
            "credentials_name":  self.credentials_name,
            "max_results":       self.max_results,
            "filter_labels":     self.filter_labels,
            "mark_read_on_poll": self.mark_read_on_poll,
            "poll_interval_secs": self.poll_interval_secs,
            "tier":              self.tier,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GmailConfig":
        return cls(
            account_email=d["account_email"],
            watcher_id=d.get("watcher_id", ""),
            vault_root=d.get("vault_root", ""),
            credentials_name=d.get("credentials_name", "gmail_api_key"),
            max_results=d.get("max_results", 10),
            filter_labels=d.get("filter_labels", []),
            mark_read_on_poll=d.get("mark_read_on_poll", False),
            poll_interval_secs=d.get("poll_interval_secs", 60.0),
            tier=d.get("tier", 2),
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_gmail_message(
    subject: str,
    sender: str,
    recipient: str = "",
    snippet: str = "",
    thread_id: str = "",
    labels: Optional[list[str]] = None,
    has_attachments: bool = False,
    attachment_names: Optional[list[str]] = None,
) -> GmailMessage:
    """Create a GmailMessage with auto-generated IDs and UTC timestamp."""
    return GmailMessage(
        message_id=f"MSG-{uuid.uuid4().hex[:8].upper()}",
        thread_id=thread_id or f"THR-{uuid.uuid4().hex[:8].upper()}",
        subject=subject,
        sender=sender,
        recipient=recipient,
        snippet=snippet[:200],
        labels=labels or [],
        received_at=datetime.now(tz=timezone.utc),
        has_attachments=has_attachments,
        attachment_names=attachment_names or [],
    )
