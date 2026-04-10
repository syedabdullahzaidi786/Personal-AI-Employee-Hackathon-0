"""
HUMAN_IN_THE_LOOP_APPROVAL_SKILL — Decision Processor
Phase 1: Process approve / deny / defer / timeout decisions.

Constitution compliance:
  - Principle VI: Fail Safe (deny on error/timeout)
  - Principle III: HITL enforced for Tier 2+
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from .audit import HITLAuditLogger
from .models import ApprovalRequest, Decision, DecisionRecord, make_request
from .store import RequestStore
from .validator import DecisionError, ValidationError, validate_decision_input, validate_request


class HITLApprover:
    """
    Core decision engine for the HITL approval system.

    Handles:
      - Auto-approve (Tier 0–1)
      - Human approve/deny/defer
      - SLA timeout (auto-deny)
      - Request submission with validation
    """

    def __init__(self, store: RequestStore, audit: HITLAuditLogger) -> None:
        self._store = store
        self._audit = audit

    # ------------------------------------------------------------------
    # Submit
    # ------------------------------------------------------------------

    def submit(self, request: ApprovalRequest) -> ApprovalRequest:
        """
        Validate and queue an approval request.

        For Tier 0–1: auto-approves immediately.
        For Tier 2+:  persists to pending queue.

        Returns the (possibly decided) request.
        """
        validate_request(request)

        if request.is_auto_approved:
            return self._auto_approve(request)

        self._store.save_pending(request)
        self._audit.log_submitted(request)
        return request

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
        """Human approves a pending request."""
        request = self._load_pending(request_id)
        validate_decision_input(request, "approve", operator)

        decision = DecisionRecord(
            request_id=request_id,
            action=Decision.APPROVED,
            decided_by=operator,
            decided_at=datetime.now(tz=timezone.utc),
            comment=comment,
            modifications=modifications,
        )
        self._finalize(request, decision)
        return decision

    def deny(
        self,
        request_id: str,
        operator: str,
        reason: str = "",
        comment: str = "",
    ) -> DecisionRecord:
        """Human denies a pending request."""
        request = self._load_pending(request_id)
        validate_decision_input(request, "deny", operator)

        decision = DecisionRecord(
            request_id=request_id,
            action=Decision.DENIED,
            decided_by=operator,
            decided_at=datetime.now(tz=timezone.utc),
            reason=reason,
            comment=comment,
        )
        self._finalize(request, decision)
        return decision

    def defer(
        self,
        request_id: str,
        operator: str,
        extend_seconds: int = 3600,
        comment: str = "",
    ) -> ApprovalRequest:
        """
        Defer a request, extending its SLA.

        Returns the updated (still-pending) request.
        """
        request = self._load_pending(request_id)
        validate_decision_input(request, "defer", operator)

        # Extend SLA
        if request.sla.sla_seconds is not None:
            request.sla.sla_seconds = request.sla.sla_seconds + extend_seconds
        # Log a defer entry (not a final decision — request stays PENDING)
        self._audit._append_request_log(
            request,
            f"DEFERRED: {request_id}",
            details={
                "Deferred By": operator,
                "Extension": f"{extend_seconds}s",
                "New Deadline": (
                    request.sla.required_by.isoformat()
                    if request.sla.required_by else "N/A"
                ),
                "Comment": comment or "—",
            },
        )
        self._store.save_pending(request)
        return request

    def process_timeout(self, request_id: str) -> DecisionRecord:
        """
        System-triggered timeout: auto-deny the request (fail-safe).
        """
        request = self._load_pending(request_id)
        if not request.sla.is_expired():
            raise DecisionError(
                f"Request {request_id!r} SLA has not expired yet."
            )

        decision = DecisionRecord(
            request_id=request_id,
            action=Decision.DENIED,
            decided_by="SYSTEM",
            decided_at=datetime.now(tz=timezone.utc),
            reason=f"SLA timeout — no decision received. Default action: {request.sla.timeout_action}",
        )
        self._audit.log_timeout(request)
        self._finalize(request, decision)
        return decision

    def check_and_timeout_expired(self) -> list[DecisionRecord]:
        """
        Scan all pending requests; auto-deny any with expired SLA.
        Returns list of timeout decisions applied.
        """
        decisions = []
        for req in self._store.list_pending():
            if req.sla.is_expired():
                try:
                    d = self.process_timeout(req.request_id)
                    decisions.append(d)
                except DecisionError:
                    pass
        return decisions

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        return self._store.get(request_id)

    def list_pending(
        self,
        agent_id: Optional[str] = None,
        tier: Optional[int] = None,
    ) -> list[ApprovalRequest]:
        return self._store.list_pending(agent_id=agent_id, tier=tier)

    def list_all(self) -> list[ApprovalRequest]:
        pending = self._store.list_pending()
        completed = self._store.list_completed()
        return pending + completed

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _auto_approve(self, request: ApprovalRequest) -> ApprovalRequest:
        decision = DecisionRecord(
            request_id=request.request_id,
            action=Decision.AUTO,
            decided_by="SYSTEM",
            decided_at=datetime.now(tz=timezone.utc),
            reason="Tier 0/1 — auto-approve policy",
            auto_approved=True,
        )
        request.status = Decision.AUTO
        request.decision = decision
        self._store.move_to_completed(request)
        self._audit.log_auto_approved(request)
        return request

    def _finalize(
        self, request: ApprovalRequest, decision: DecisionRecord
    ) -> None:
        request.status = decision.action
        request.decision = decision
        self._store.move_to_completed(request)
        self._audit.log_decision(request, decision)

    def _load_pending(self, request_id: str) -> ApprovalRequest:
        request = self._store.get(request_id)
        if request is None:
            raise DecisionError(f"Request not found: {request_id!r}")
        if request.status != Decision.PENDING:
            raise DecisionError(
                f"Request {request_id!r} already decided (status={request.status!r})"
            )
        return request
