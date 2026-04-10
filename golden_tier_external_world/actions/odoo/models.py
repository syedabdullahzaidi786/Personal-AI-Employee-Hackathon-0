"""
ODOO_MCP_INTEGRATION_SKILL — Data Models
Phase 1: OdooRequest, OdooResult, OdooConfig, OdooOperation, OdooActionStatus.

Constitution compliance:
  - Section 9: Skill Design Rules — atomic, testable, composable
  - Section 8: Credential Storage — credentials_name is a reference, never the secret
  - Principle VI: Fail Safe — explicit statuses, no silent errors
  - Tier 3 (High-risk): HITL required for write operations (create/update)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class OdooOperation:
    """Supported Odoo operation types (Phase 1)."""
    CREATE_RECORD = "create_record"
    UPDATE_RECORD = "update_record"
    FETCH_RECORD  = "fetch_record"


class OdooActionStatus:
    """Status constants for OdooResult."""
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED         = "APPROVED"
    SUCCESS          = "SUCCESS"
    DENIED           = "DENIED"
    FAILED           = "FAILED"
    NOT_FOUND        = "NOT_FOUND"


class OdooEventType:
    """Odoo integration event type string constants."""
    RECORD_CREATED     = "odoo_record_created"
    RECORD_UPDATED     = "odoo_record_updated"
    RECORD_FETCHED     = "odoo_record_fetched"
    OPERATION_DENIED   = "odoo_operation_denied"
    OPERATION_FAILED   = "odoo_operation_failed"
    APPROVAL_REQUESTED = "odoo_approval_requested"


# Risk tier by operation — write ops are high-risk, reads are lower
OPERATION_DEFAULT_TIER: dict[str, int] = {
    OdooOperation.CREATE_RECORD: 3,
    OdooOperation.UPDATE_RECORD: 3,
    OdooOperation.FETCH_RECORD:  1,   # Read-only: auto-approve
}


# ---------------------------------------------------------------------------
# OdooRequest — safe representation of an Odoo API operation
# ---------------------------------------------------------------------------

@dataclass
class OdooRequest:
    """
    Safe representation of an Odoo API operation request.

    Design contract:
      - Never stores Odoo API keys or passwords.
      - credentials_name is a logical name resolved by SecuritySkill.
      - data dict is the record payload — must not contain raw secrets.
    """
    operation:        str                      # OdooOperation constant
    model:            str                      # Odoo model name, e.g. "res.partner"
    request_id:       str                      = field(default_factory=lambda: f"ODOO-{uuid.uuid4().hex[:8].upper()}")
    record_id:        Optional[int]            = None   # Required for update/fetch
    data:             dict[str, Any]           = field(default_factory=dict)
    tier:             int                      = 3
    credentials_name: str                      = "odoo_credential"
    submitted_at:     Optional[datetime]       = None

    def __post_init__(self) -> None:
        if self.submitted_at is None:
            self.submitted_at = datetime.now(tz=timezone.utc)

    def to_dict(self) -> dict:
        return {
            "request_id":       self.request_id,
            "operation":        self.operation,
            "model":            self.model,
            "record_id":        self.record_id,
            "data":             self.data,
            "tier":             self.tier,
            "credentials_name": self.credentials_name,
            "submitted_at":     self.submitted_at.isoformat() if self.submitted_at else None,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "OdooRequest":
        submitted_at = None
        if d.get("submitted_at"):
            submitted_at = datetime.fromisoformat(d["submitted_at"])
        return cls(
            request_id=d.get("request_id", f"ODOO-{uuid.uuid4().hex[:8].upper()}"),
            operation=d["operation"],
            model=d["model"],
            record_id=d.get("record_id"),
            data=d.get("data", {}),
            tier=d.get("tier", 3),
            credentials_name=d.get("credentials_name", "odoo_credential"),
            submitted_at=submitted_at,
        )


# ---------------------------------------------------------------------------
# OdooResult — outcome of an Odoo operation
# ---------------------------------------------------------------------------

@dataclass
class OdooResult:
    """Result of an Odoo integration operation."""
    request_id:      str
    operation:       str
    status:          str                    # OdooActionStatus constant
    model:           str                    = ""
    record_id:       Optional[int]          = None
    record_data:     dict[str, Any]         = field(default_factory=dict)
    error:           str                    = ""
    adapter:         str                    = "mock"
    hitl_request_id: str                    = ""
    executed_at:     Optional[datetime]     = None

    def to_dict(self) -> dict:
        return {
            "request_id":      self.request_id,
            "operation":       self.operation,
            "status":          self.status,
            "model":           self.model,
            "record_id":       self.record_id,
            "record_data":     self.record_data,
            "error":           self.error,
            "adapter":         self.adapter,
            "hitl_request_id": self.hitl_request_id,
            "executed_at":     self.executed_at.isoformat() if self.executed_at else None,
        }


# ---------------------------------------------------------------------------
# OdooConfig
# ---------------------------------------------------------------------------

@dataclass
class OdooConfig:
    """
    Configuration for OdooSkill.

    credentials_name is a logical name resolved by SecuritySkill.
    The actual Odoo API key / password is never stored here.
    """
    vault_root:       str = ""
    odoo_url:         str = ""          # e.g. "https://mycompany.odoo.com"
    database:         str = ""          # Odoo database name
    credentials_name: str = "odoo_credential"
    default_tier:     int = 3           # High-risk by default

    def to_dict(self) -> dict:
        return {
            "vault_root":       self.vault_root,
            "odoo_url":         self.odoo_url,
            "database":         self.database,
            "credentials_name": self.credentials_name,
            "default_tier":     self.default_tier,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "OdooConfig":
        return cls(
            vault_root=d.get("vault_root", ""),
            odoo_url=d.get("odoo_url", ""),
            database=d.get("database", ""),
            credentials_name=d.get("credentials_name", "odoo_credential"),
            default_tier=d.get("default_tier", 3),
        )


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def make_create_request(
    model: str,
    data: dict[str, Any],
    tier: int = 3,
    credentials_name: str = "odoo_credential",
) -> OdooRequest:
    """Create a create_record OdooRequest."""
    return OdooRequest(
        operation=OdooOperation.CREATE_RECORD,
        model=model,
        data=data,
        tier=tier,
        credentials_name=credentials_name,
    )


def make_update_request(
    model: str,
    record_id: int,
    data: dict[str, Any],
    tier: int = 3,
    credentials_name: str = "odoo_credential",
) -> OdooRequest:
    """Create an update_record OdooRequest."""
    return OdooRequest(
        operation=OdooOperation.UPDATE_RECORD,
        model=model,
        record_id=record_id,
        data=data,
        tier=tier,
        credentials_name=credentials_name,
    )


def make_fetch_request(
    model: str,
    record_id: int,
    tier: int = 1,
    credentials_name: str = "odoo_credential",
) -> OdooRequest:
    """Create a fetch_record OdooRequest (default tier 1 — read-only)."""
    return OdooRequest(
        operation=OdooOperation.FETCH_RECORD,
        model=model,
        record_id=record_id,
        tier=tier,
        credentials_name=credentials_name,
    )
