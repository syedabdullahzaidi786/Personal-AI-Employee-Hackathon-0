"""
HUMAN_IN_THE_LOOP_APPROVAL_SKILL — Data Models
Phase 1: Core request, decision, and SLA data structures.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import IntEnum
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class Tier(IntEnum):
    READ_ONLY   = 0   # Auto-approve
    LOW_RISK    = 1   # Auto-approve
    MEDIUM_RISK = 2   # 4-hour SLA
    HIGH_RISK   = 3   # 1-hour SLA
    CRITICAL    = 4   # Immediate / no timeout


# SLA in seconds per tier (None = no timeout)
TIER_SLA_SECONDS: dict[int, Optional[int]] = {
    0: None,
    1: None,
    2: 14400,   # 4 hours
    3: 3600,    # 1 hour
    4: None,    # No timeout for critical
}

# Escalation at this fraction of the SLA
ESCALATION_FRACTION = 0.5


class Decision(str):
    """Decision constants."""
    APPROVED  = "APPROVED"
    DENIED    = "DENIED"
    DEFERRED  = "DEFERRED"
    TIMEOUT   = "TIMEOUT"
    PENDING   = "PENDING"
    AUTO      = "AUTO_APPROVED"


# ---------------------------------------------------------------------------
# SLA Config
# ---------------------------------------------------------------------------

@dataclass
class SLAConfig:
    tier: int
    submitted_at: datetime
    sla_seconds: Optional[int]         # None = no timeout
    timeout_action: str = "deny"       # fail-safe default

    @property
    def required_by(self) -> Optional[datetime]:
        if self.sla_seconds is None:
            return None
        return self.submitted_at + timedelta(seconds=self.sla_seconds)

    @property
    def escalation_at(self) -> Optional[datetime]:
        if self.sla_seconds is None:
            return None
        return self.submitted_at + timedelta(
            seconds=int(self.sla_seconds * ESCALATION_FRACTION)
        )

    def remaining_seconds(self, now: Optional[datetime] = None) -> Optional[float]:
        if self.required_by is None:
            return None
        now = now or datetime.now(tz=timezone.utc)
        delta = (self.required_by - now).total_seconds()
        return max(delta, 0.0)

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        if self.required_by is None:
            return False
        now = now or datetime.now(tz=timezone.utc)
        return now >= self.required_by

    def should_escalate(self, now: Optional[datetime] = None) -> bool:
        if self.escalation_at is None:
            return False
        now = now or datetime.now(tz=timezone.utc)
        return now >= self.escalation_at

    def to_dict(self) -> dict:
        return {
            "tier": self.tier,
            "sla_seconds": self.sla_seconds,
            "submitted_at": self.submitted_at.isoformat(),
            "required_by": self.required_by.isoformat() if self.required_by else None,
            "escalation_at": self.escalation_at.isoformat() if self.escalation_at else None,
            "timeout_action": self.timeout_action,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SLAConfig":
        return cls(
            tier=d["tier"],
            submitted_at=datetime.fromisoformat(d["submitted_at"]),
            sla_seconds=d.get("sla_seconds"),
            timeout_action=d.get("timeout_action", "deny"),
        )


# ---------------------------------------------------------------------------
# Approval Request
# ---------------------------------------------------------------------------

@dataclass
class ApprovalRequest:
    request_id: str
    agent_id: str
    operation: str
    tier: int
    action_summary: str
    reason: str
    details: dict
    risk: dict
    submitted_at: datetime
    sla: SLAConfig
    status: str = Decision.PENDING
    options: list[str] = field(default_factory=lambda: ["approve", "deny", "defer"])
    checksum: str = ""
    decision: Optional["DecisionRecord"] = None

    def __post_init__(self) -> None:
        if not self.checksum:
            self.checksum = self._compute_checksum()

    def _compute_checksum(self) -> str:
        data = json.dumps({
            "request_id": self.request_id,
            "agent_id": self.agent_id,
            "operation": self.operation,
            "tier": self.tier,
            "submitted_at": self.submitted_at.isoformat(),
        }, sort_keys=True)
        return "sha256:" + hashlib.sha256(data.encode()).hexdigest()

    @property
    def is_auto_approved(self) -> bool:
        return self.tier <= 1

    @property
    def is_pending(self) -> bool:
        return self.status == Decision.PENDING

    def to_dict(self) -> dict:
        d = {
            "request_id": self.request_id,
            "agent_id": self.agent_id,
            "operation": self.operation,
            "tier": self.tier,
            "action_summary": self.action_summary,
            "reason": self.reason,
            "details": self.details,
            "risk": self.risk,
            "submitted_at": self.submitted_at.isoformat(),
            "status": self.status,
            "options": self.options,
            "checksum": self.checksum,
            "sla": self.sla.to_dict(),
        }
        if self.decision:
            d["decision"] = self.decision.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ApprovalRequest":
        sla = SLAConfig.from_dict(d["sla"])
        req = cls(
            request_id=d["request_id"],
            agent_id=d["agent_id"],
            operation=d["operation"],
            tier=d["tier"],
            action_summary=d["action_summary"],
            reason=d["reason"],
            details=d.get("details", {}),
            risk=d.get("risk", {}),
            submitted_at=datetime.fromisoformat(d["submitted_at"]),
            sla=sla,
            status=d.get("status", Decision.PENDING),
            options=d.get("options", ["approve", "deny", "defer"]),
            checksum=d.get("checksum", ""),
        )
        if "decision" in d and d["decision"]:
            req.decision = DecisionRecord.from_dict(d["decision"])
        return req


# ---------------------------------------------------------------------------
# Decision Record
# ---------------------------------------------------------------------------

@dataclass
class DecisionRecord:
    request_id: str
    action: str                    # APPROVED | DENIED | DEFERRED | TIMEOUT | AUTO_APPROVED
    decided_by: str                # operator id or "SYSTEM"
    decided_at: datetime
    reason: str = ""
    comment: str = ""
    modifications: Optional[dict] = None
    checksum: str = ""
    auto_approved: bool = False

    def __post_init__(self) -> None:
        if not self.checksum:
            self.checksum = self._compute_checksum()

    def _compute_checksum(self) -> str:
        data = json.dumps({
            "request_id": self.request_id,
            "action": self.action,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at.isoformat(),
        }, sort_keys=True)
        return "sha256:" + hashlib.sha256(data.encode()).hexdigest()

    @property
    def approved(self) -> bool:
        return self.action in (Decision.APPROVED, Decision.AUTO)

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "action": self.action,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at.isoformat(),
            "reason": self.reason,
            "comment": self.comment,
            "modifications": self.modifications,
            "checksum": self.checksum,
            "auto_approved": self.auto_approved,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DecisionRecord":
        return cls(
            request_id=d["request_id"],
            action=d["action"],
            decided_by=d["decided_by"],
            decided_at=datetime.fromisoformat(d["decided_at"]),
            reason=d.get("reason", ""),
            comment=d.get("comment", ""),
            modifications=d.get("modifications"),
            checksum=d.get("checksum", ""),
            auto_approved=d.get("auto_approved", False),
        )


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def make_request(
    agent_id: str,
    operation: str,
    tier: int,
    action_summary: str,
    reason: str,
    details: dict,
    risk: Optional[dict] = None,
    options: Optional[list[str]] = None,
    sla_override_seconds: Optional[int] = None,
) -> ApprovalRequest:
    """Create a new ApprovalRequest with auto-generated ID and SLA."""
    now = datetime.now(tz=timezone.utc)
    request_id = f"REQ-{uuid.uuid4()}"
    sla_secs = sla_override_seconds if sla_override_seconds is not None else TIER_SLA_SECONDS.get(tier)
    sla = SLAConfig(tier=tier, submitted_at=now, sla_seconds=sla_secs)
    return ApprovalRequest(
        request_id=request_id,
        agent_id=agent_id,
        operation=operation,
        tier=tier,
        action_summary=action_summary,
        reason=reason,
        details=details,
        risk=risk or {},
        submitted_at=now,
        sla=sla,
        options=options or ["approve", "deny", "defer"],
    )
