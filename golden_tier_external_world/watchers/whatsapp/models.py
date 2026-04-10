"""
WHATSAPP_WATCHER_SKILL — Data Models
Phase 1: WhatsAppMessage, WhatsAppConfig, event type constants.

Constitution compliance:
  - Section 9: Skill Design Rules — atomic, testable, composable
  - Principle VI: Fail Safe — structured events, no silent errors
  - Section 8: Credential Storage — credentials_name is a reference, never the secret
  - No media payloads stored — only metadata (filename, mime_type, size_bytes)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# String constants (not Enum so they are directly usable as event_type keys)
# ---------------------------------------------------------------------------

class WhatsAppEventType:
    """WhatsApp-specific event type string constants."""
    NEW_TEXT_MESSAGE     = "whatsapp_new_text_message"
    NEW_MEDIA_MESSAGE    = "whatsapp_new_media_message"
    NEW_GROUP_MESSAGE    = "whatsapp_new_group_message"
    NEW_LOCATION_MESSAGE = "whatsapp_new_location_message"
    CONTACT_RECEIVED     = "whatsapp_contact_received"
    POLL_HEARTBEAT       = "whatsapp_poll_heartbeat"


class WhatsAppMessageType:
    """WhatsApp message content types."""
    TEXT     = "text"
    IMAGE    = "image"
    AUDIO    = "audio"
    VIDEO    = "video"
    DOCUMENT = "document"
    LOCATION = "location"
    CONTACT  = "contact"
    STICKER  = "sticker"
    UNKNOWN  = "unknown"

    _MEDIA_TYPES = {IMAGE, AUDIO, VIDEO, DOCUMENT, STICKER}

    @classmethod
    def is_media(cls, msg_type: str) -> bool:
        return msg_type in cls._MEDIA_TYPES


class WhatsAppChatType:
    """Chat scope — private (direct message) or group."""
    PRIVATE = "private"
    GROUP   = "group"


# ---------------------------------------------------------------------------
# WhatsAppMessage — safe representation (no raw media bytes, no credentials)
# ---------------------------------------------------------------------------

@dataclass
class WhatsAppMessage:
    """
    Safe, normalised representation of a received WhatsApp message.

    Design contract:
      - message_body is plain text only; media payloads are NOT stored.
      - media_filename / media_mime_type / media_size_bytes are metadata-only.
      - sender_phone / group_id are normalised E.164-ish strings (no display names
        needed — display_name is optional and informational only).
      - location fields (latitude / longitude) are only set for LOCATION messages.
    """
    message_id:      str
    chat_id:         str                          # phone number or group id
    chat_type:       str                          # WhatsAppChatType constant
    message_type:    str                          # WhatsAppMessageType constant
    sender_phone:    str                          # E.164-ish e.g. "+14155552671"
    sender_name:     str                          # display name (may be empty)
    message_body:    str                          # text content (empty for media)
    received_at:     Optional[datetime]           = None
    group_id:        str                          = ""
    group_name:      str                          = ""
    # Media metadata (not the bytes)
    media_filename:  str                          = ""
    media_mime_type: str                          = ""
    media_size_bytes: int                         = 0
    # Location
    latitude:        Optional[float]              = None
    longitude:       Optional[float]              = None
    # Forwarded / reply context
    is_forwarded:    bool                         = False
    reply_to_id:     str                          = ""

    def is_group_message(self) -> bool:
        return self.chat_type == WhatsAppChatType.GROUP

    def is_media_message(self) -> bool:
        return WhatsAppMessageType.is_media(self.message_type)

    def to_dict(self) -> dict:
        return {
            "message_id":      self.message_id,
            "chat_id":         self.chat_id,
            "chat_type":       self.chat_type,
            "message_type":    self.message_type,
            "sender_phone":    self.sender_phone,
            "sender_name":     self.sender_name,
            "message_body":    self.message_body[:500],  # cap at 500 chars
            "received_at":     self.received_at.isoformat() if self.received_at else None,
            "group_id":        self.group_id,
            "group_name":      self.group_name,
            "media_filename":  self.media_filename,
            "media_mime_type": self.media_mime_type,
            "media_size_bytes": self.media_size_bytes,
            "latitude":        self.latitude,
            "longitude":       self.longitude,
            "is_forwarded":    self.is_forwarded,
            "reply_to_id":     self.reply_to_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WhatsAppMessage":
        received_at = None
        if d.get("received_at"):
            received_at = datetime.fromisoformat(d["received_at"])
        return cls(
            message_id=d["message_id"],
            chat_id=d["chat_id"],
            chat_type=d.get("chat_type", WhatsAppChatType.PRIVATE),
            message_type=d.get("message_type", WhatsAppMessageType.TEXT),
            sender_phone=d["sender_phone"],
            sender_name=d.get("sender_name", ""),
            message_body=d.get("message_body", ""),
            received_at=received_at,
            group_id=d.get("group_id", ""),
            group_name=d.get("group_name", ""),
            media_filename=d.get("media_filename", ""),
            media_mime_type=d.get("media_mime_type", ""),
            media_size_bytes=d.get("media_size_bytes", 0),
            latitude=d.get("latitude"),
            longitude=d.get("longitude"),
            is_forwarded=d.get("is_forwarded", False),
            reply_to_id=d.get("reply_to_id", ""),
        )


# ---------------------------------------------------------------------------
# WhatsAppConfig
# ---------------------------------------------------------------------------

@dataclass
class WhatsAppConfig:
    """
    Configuration for WhatsAppWatcher.

    phone_number is the account identifier (E.164 format recommended).
    credentials_name is a logical name passed to SecuritySkill.get_credential().
    The actual API token / session secret is NEVER stored here.
    """
    phone_number:       str
    watcher_id:         str         = ""          # auto-generated if empty
    vault_root:         str         = ""
    credentials_name:   str         = "whatsapp_api_key"
    max_results:        int         = 20          # max messages per poll
    filter_chat_types:  list[str]   = field(default_factory=list)  # [] = all
    filter_senders:     list[str]   = field(default_factory=list)  # [] = all
    poll_interval_secs: float       = 30.0
    tier:               int         = 2           # HITL tier for emitted events
    send_read_receipts: bool        = False       # True only with real API

    def __post_init__(self) -> None:
        if not self.watcher_id:
            safe = self.phone_number.lstrip("+").replace(" ", "_")
            self.watcher_id = f"whatsapp-{safe}"

    def to_dict(self) -> dict:
        return {
            "phone_number":       self.phone_number,
            "watcher_id":         self.watcher_id,
            "vault_root":         self.vault_root,
            "credentials_name":   self.credentials_name,
            "max_results":        self.max_results,
            "filter_chat_types":  self.filter_chat_types,
            "filter_senders":     self.filter_senders,
            "poll_interval_secs": self.poll_interval_secs,
            "tier":               self.tier,
            "send_read_receipts": self.send_read_receipts,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WhatsAppConfig":
        return cls(
            phone_number=d["phone_number"],
            watcher_id=d.get("watcher_id", ""),
            vault_root=d.get("vault_root", ""),
            credentials_name=d.get("credentials_name", "whatsapp_api_key"),
            max_results=d.get("max_results", 20),
            filter_chat_types=d.get("filter_chat_types", []),
            filter_senders=d.get("filter_senders", []),
            poll_interval_secs=d.get("poll_interval_secs", 30.0),
            tier=d.get("tier", 2),
            send_read_receipts=d.get("send_read_receipts", False),
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_whatsapp_message(
    sender_phone: str,
    message_body: str = "",
    message_type: str = WhatsAppMessageType.TEXT,
    chat_type: str    = WhatsAppChatType.PRIVATE,
    sender_name: str  = "",
    group_id: str     = "",
    group_name: str   = "",
    media_filename: str     = "",
    media_mime_type: str    = "",
    media_size_bytes: int   = 0,
    latitude: Optional[float]  = None,
    longitude: Optional[float] = None,
    is_forwarded: bool         = False,
) -> WhatsAppMessage:
    """Create a WhatsAppMessage with auto-generated IDs and UTC timestamp."""
    chat_id = group_id if chat_type == WhatsAppChatType.GROUP else sender_phone
    return WhatsAppMessage(
        message_id=f"WA-{uuid.uuid4().hex[:8].upper()}",
        chat_id=chat_id,
        chat_type=chat_type,
        message_type=message_type,
        sender_phone=sender_phone,
        sender_name=sender_name,
        message_body=message_body[:500],
        received_at=datetime.now(tz=timezone.utc),
        group_id=group_id,
        group_name=group_name,
        media_filename=media_filename,
        media_mime_type=media_mime_type,
        media_size_bytes=media_size_bytes,
        latitude=latitude,
        longitude=longitude,
        is_forwarded=is_forwarded,
    )
