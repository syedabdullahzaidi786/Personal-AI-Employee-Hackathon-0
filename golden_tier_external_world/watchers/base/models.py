"""
BASE_WATCHER_CREATION_SKILL — Data Models
Phase 1: Event, config, state, tick result, dispatch result.

Constitution compliance:
  - Section 9: Skill Design Rules — atomic, testable, observable
  - Principle VI: Fail Safe — structured errors, never silent
  - Principle II: Explicit Over Implicit — all events typed and logged
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class WatcherStatus(str, Enum):
    IDLE    = "idle"
    RUNNING = "running"
    PAUSED  = "paused"
    ERROR   = "error"
    STOPPED = "stopped"


class EventType(str, Enum):
    """Base event types. Concrete watchers extend with their own types."""
    GENERIC        = "generic"
    FILE_CREATED   = "file_created"
    FILE_MODIFIED  = "file_modified"
    FILE_DELETED   = "file_deleted"
    MESSAGE_RECEIVED = "message_received"
    POLL_HEARTBEAT = "poll_heartbeat"


# ---------------------------------------------------------------------------
# WatcherConfig
# ---------------------------------------------------------------------------

@dataclass
class WatcherConfig:
    """
    Configuration for a single watcher instance.

    vault_root is required so the watcher writes logs to the correct vault.
    """
    watcher_id:         str
    watcher_type:       str                   # e.g. "filesystem", "gmail", "whatsapp"
    vault_root:         str   = ""
    poll_interval_secs: float = 30.0
    enabled:            bool  = True
    tier:               int   = 2             # Default HITL tier for events from this watcher
    description:        str   = ""
    max_consecutive_errors: int = 5

    def to_dict(self) -> dict:
        return {
            "watcher_id":           self.watcher_id,
            "watcher_type":         self.watcher_type,
            "vault_root":           self.vault_root,
            "poll_interval_secs":   self.poll_interval_secs,
            "enabled":              self.enabled,
            "tier":                 self.tier,
            "description":          self.description,
            "max_consecutive_errors": self.max_consecutive_errors,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WatcherConfig":
        return cls(
            watcher_id=d["watcher_id"],
            watcher_type=d["watcher_type"],
            vault_root=d.get("vault_root", ""),
            poll_interval_secs=d.get("poll_interval_secs", 30.0),
            enabled=d.get("enabled", True),
            tier=d.get("tier", 2),
            description=d.get("description", ""),
            max_consecutive_errors=d.get("max_consecutive_errors", 5),
        )


# ---------------------------------------------------------------------------
# WatcherEvent
# ---------------------------------------------------------------------------

@dataclass
class WatcherEvent:
    """
    An event detected by a watcher.

    payload: raw event data — must NEVER contain credentials or secrets.
    tier:    HITL tier for this specific event (overrides watcher default if set).
    """
    event_id:   str
    watcher_id: str
    event_type: str
    source:     str           # Human-readable source label, e.g. "gmail:inbox"
    timestamp:  datetime
    payload:    dict = field(default_factory=dict)
    tier:       int  = 2
    processed:  bool = False

    def to_dict(self) -> dict:
        return {
            "event_id":   self.event_id,
            "watcher_id": self.watcher_id,
            "event_type": self.event_type,
            "source":     self.source,
            "timestamp":  self.timestamp.isoformat(),
            "payload":    self.payload,
            "tier":       self.tier,
            "processed":  self.processed,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WatcherEvent":
        return cls(
            event_id=d["event_id"],
            watcher_id=d["watcher_id"],
            event_type=d["event_type"],
            source=d["source"],
            timestamp=datetime.fromisoformat(d["timestamp"]),
            payload=d.get("payload", {}),
            tier=d.get("tier", 2),
            processed=d.get("processed", False),
        )


# ---------------------------------------------------------------------------
# WatcherState
# ---------------------------------------------------------------------------

@dataclass
class WatcherState:
    """Runtime state for a single watcher (in-memory + persisted to vault)."""
    watcher_id:         str
    status:             WatcherStatus = WatcherStatus.IDLE
    poll_count:         int           = 0
    error_count:        int           = 0
    consecutive_errors: int           = 0
    total_events:       int           = 0
    last_poll_at:       Optional[datetime] = None
    last_event_at:      Optional[datetime] = None
    started_at:         Optional[datetime] = None
    stopped_at:         Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "watcher_id":         self.watcher_id,
            "status":             self.status.value,
            "poll_count":         self.poll_count,
            "error_count":        self.error_count,
            "consecutive_errors": self.consecutive_errors,
            "total_events":       self.total_events,
            "last_poll_at":       self.last_poll_at.isoformat() if self.last_poll_at else None,
            "last_event_at":      self.last_event_at.isoformat() if self.last_event_at else None,
            "started_at":         self.started_at.isoformat() if self.started_at else None,
            "stopped_at":         self.stopped_at.isoformat() if self.stopped_at else None,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WatcherState":
        obj = cls(watcher_id=d["watcher_id"])
        obj.status             = WatcherStatus(d.get("status", "idle"))
        obj.poll_count         = d.get("poll_count", 0)
        obj.error_count        = d.get("error_count", 0)
        obj.consecutive_errors = d.get("consecutive_errors", 0)
        obj.total_events       = d.get("total_events", 0)
        for ts_field in ("last_poll_at", "last_event_at", "started_at", "stopped_at"):
            raw = d.get(ts_field)
            if raw:
                setattr(obj, ts_field, datetime.fromisoformat(raw))
        return obj


# ---------------------------------------------------------------------------
# WatcherTickResult
# ---------------------------------------------------------------------------

@dataclass
class WatcherTickResult:
    """Summary of a single poll cycle."""
    watcher_id:        str
    poll_count:        int
    events_found:      int
    events_dispatched: int
    errors:            int
    health_ok:         bool
    duration_ms:       float
    error_message:     Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "watcher_id":        self.watcher_id,
            "poll_count":        self.poll_count,
            "events_found":      self.events_found,
            "events_dispatched": self.events_dispatched,
            "errors":            self.errors,
            "health_ok":         self.health_ok,
            "duration_ms":       self.duration_ms,
            "error_message":     self.error_message,
        }


# ---------------------------------------------------------------------------
# DispatchResult
# ---------------------------------------------------------------------------

@dataclass
class DispatchResult:
    """Result of routing a single WatcherEvent through EventDispatcher."""
    event_id:        str
    dispatched:      bool
    handler_called:  bool
    hitl_submitted:  bool
    hitl_request_id: Optional[str] = None
    error:           Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "event_id":        self.event_id,
            "dispatched":      self.dispatched,
            "handler_called":  self.handler_called,
            "hitl_submitted":  self.hitl_submitted,
            "hitl_request_id": self.hitl_request_id,
            "error":           self.error,
        }


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def make_event(
    watcher_id: str,
    event_type: str,
    source: str,
    payload: Optional[dict] = None,
    tier: int = 2,
) -> WatcherEvent:
    """Create a WatcherEvent with a unique ID and UTC timestamp."""
    return WatcherEvent(
        event_id=f"EVT-{uuid.uuid4().hex[:8].upper()}",
        watcher_id=watcher_id,
        event_type=event_type,
        source=source,
        timestamp=datetime.now(tz=timezone.utc),
        payload=payload or {},
        tier=tier,
    )
