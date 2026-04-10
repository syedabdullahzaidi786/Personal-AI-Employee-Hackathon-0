"""
WHATSAPP_BROADCAST_ACTION — Data Models
Playwright WhatsApp Web broadcast (no Twilio required).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


class WhatsAppBroadcastStatus:
    SUCCESS  = "SUCCESS"
    PARTIAL  = "PARTIAL"   # some sent, some failed
    FAILED   = "FAILED"


@dataclass
class WhatsAppBroadcastRequest:
    """
    Request to send the same message to multiple WhatsApp numbers.

    to_numbers : E.164 format list, e.g. ["+923001234567", "+923009876543"]
    message    : plain text message body
    tier       : 1 = auto-send, 2+ = HITL required
    """
    to_numbers: list[str]
    message:    str
    request_id: str = field(default_factory=lambda: f"WAB-{uuid.uuid4().hex[:8].upper()}")
    tier:       int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def __post_init__(self) -> None:
        # Sanitise numbers — strip spaces
        self.to_numbers = [n.strip() for n in self.to_numbers if n.strip()]


@dataclass
class WhatsAppBroadcastResult:
    """Result of a broadcast send attempt."""
    request_id:  str
    sent:        list[str]   = field(default_factory=list)   # numbers that succeeded
    failed:      list[str]   = field(default_factory=list)   # numbers that failed
    status:      str         = WhatsAppBroadcastStatus.FAILED
    error:       str         = ""
    completed_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.completed_at is None:
            self.completed_at = datetime.now(tz=timezone.utc)
        if not self.status:
            self._compute_status()

    def _compute_status(self) -> None:
        if self.sent and not self.failed:
            self.status = WhatsAppBroadcastStatus.SUCCESS
        elif self.sent and self.failed:
            self.status = WhatsAppBroadcastStatus.PARTIAL
        else:
            self.status = WhatsAppBroadcastStatus.FAILED

    def to_dict(self) -> dict:
        return {
            "request_id":   self.request_id,
            "sent":         self.sent,
            "failed":       self.failed,
            "status":       self.status,
            "error":        self.error,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
