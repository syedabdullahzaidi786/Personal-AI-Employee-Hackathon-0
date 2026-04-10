"""
HUMAN_IN_THE_LOOP_APPROVAL_SKILL — Phase 1
Safety foundation: 5-tier human approval system.

Public surface:

    from skills.safety.hitl import HITLSkill

    skill = HITLSkill(vault_root="/path/to/obsidian-vault")

    # Tier 0–1: auto-approves immediately
    req = skill.submit(
        agent_id="my-agent",
        operation="organize_file",
        tier=1,
        action_summary="Rename Meeting Notes.md",
        reason="Vault naming enforcement",
        details={"source": "vault/root/file.md"},
    )
    print(req.status)   # AUTO_APPROVED

    # Tier 2+: queued for human decision
    req = skill.submit(
        agent_id="email-agent",
        operation="send_email",
        tier=2,
        action_summary="Send onboarding email",
        reason="Customer onboarding workflow",
        details={"to": "user@example.com"},
        risk={"blast_radius": "single customer", "reversibility": "cannot unsend"},
    )
    print(req.status)   # PENDING

    # Human decides via CLI or programmatically:
    decision = skill.approve("REQ-xxx", operator="alice", comment="OK")
    decision = skill.deny("REQ-xxx", operator="alice", reason="Not needed")
"""

from pathlib import Path
from typing import Optional

from .approver import HITLApprover
from .audit import HITLAuditLogger
from .models import (
    ApprovalRequest,
    Decision,
    DecisionRecord,
    SLAConfig,
    Tier,
    make_request,
)
from .store import RequestStore
from .validator import DecisionError, ValidationError


class HITLSkill:
    """
    High-level facade for HUMAN_IN_THE_LOOP_APPROVAL_SKILL Phase 1.

    Composes: RequestStore + HITLAuditLogger + HITLApprover.
    """

    def __init__(self, vault_root: str | Path) -> None:
        vault = Path(vault_root)
        self._store   = RequestStore(vault)
        self._audit   = HITLAuditLogger(vault)
        self._approver = HITLApprover(store=self._store, audit=self._audit)

    # ------------------------------------------------------------------
    # Submit
    # ------------------------------------------------------------------

    def submit(
        self,
        agent_id: str,
        operation: str,
        tier: int,
        action_summary: str,
        reason: str,
        details: Optional[dict] = None,
        risk: Optional[dict] = None,
        options: Optional[list[str]] = None,
        sla_override_seconds: Optional[int] = None,
    ) -> ApprovalRequest:
        """
        Submit an approval request.

        Tier 0–1  → auto-approved immediately, returns decided request.
        Tier 2–4  → queued for human decision, returns pending request.
        """
        request = make_request(
            agent_id=agent_id,
            operation=operation,
            tier=tier,
            action_summary=action_summary,
            reason=reason,
            details=details or {},
            risk=risk,
            options=options,
            sla_override_seconds=sla_override_seconds,
        )
        return self._approver.submit(request)

    # ------------------------------------------------------------------
    # Decide
    # ------------------------------------------------------------------

    def approve(
        self,
        request_id: str,
        operator: str,
        comment: str = "",
        modifications: Optional[dict] = None,
    ) -> DecisionRecord:
        return self._approver.approve(request_id, operator, comment, modifications)

    def deny(
        self,
        request_id: str,
        operator: str,
        reason: str = "",
        comment: str = "",
    ) -> DecisionRecord:
        return self._approver.deny(request_id, operator, reason, comment)

    def defer(
        self,
        request_id: str,
        operator: str,
        extend_seconds: int = 3600,
        comment: str = "",
    ) -> ApprovalRequest:
        return self._approver.defer(request_id, operator, extend_seconds, comment)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        return self._approver.get_request(request_id)

    def list_pending(
        self,
        agent_id: Optional[str] = None,
        tier: Optional[int] = None,
    ) -> list[ApprovalRequest]:
        return self._approver.list_pending(agent_id=agent_id, tier=tier)

    def check_timeouts(self) -> list[DecisionRecord]:
        """Process any expired SLAs (auto-deny). Call periodically."""
        return self._approver.check_and_timeout_expired()


__all__ = [
    "HITLSkill",
    "HITLApprover",
    "HITLAuditLogger",
    "RequestStore",
    "ApprovalRequest",
    "DecisionRecord",
    "SLAConfig",
    "Decision",
    "Tier",
    "make_request",
    "ValidationError",
    "DecisionError",
]
