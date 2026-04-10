"""
HUMAN_IN_THE_LOOP_APPROVAL_SKILL — Audit Logger
Phase 1: Immutable, append-only audit trail in vault 70-LOGS/hitl/.

Log locations:
  pending request created  → 70-LOGS/hitl/pending/{id}.json   (managed by store)
  per-request audit trail  → 70-LOGS/hitl/audit/{id}.md       (this module)
  daily summary            → 70-LOGS/hitl/daily/YYYY-MM-DD.md

Constitution compliance:
  - Principle II: Explicit Over Implicit (every action logged)
  - Principle VI: Fail Safe, Fail Visible
  - Section 7: Logging Requirements
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from .models import ApprovalRequest, DecisionRecord


class HITLAuditLogger:
    """
    Append-only audit logger for HITL events.

    Never raises on write failure — prints to stderr instead so logging
    bugs cannot block the approval workflow.
    """

    def __init__(self, vault_root: str | Path) -> None:
        base = Path(vault_root) / "70-LOGS" / "hitl"
        self._audit_dir = base / "audit"
        self._daily_dir = base / "daily"
        for d in (self._audit_dir, self._daily_dir):
            d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_submitted(self, request: ApprovalRequest) -> None:
        """Log a new request submission."""
        self._append_request_log(
            request,
            f"REQUEST_SUBMITTED: {request.request_id}",
            details={
                "Agent": request.agent_id,
                "Operation": f"{request.operation} (Tier {request.tier})",
                "Action": request.action_summary,
                "SLA": self._sla_str(request),
                "Checksum": request.checksum,
            },
        )
        self._append_daily_log(
            f"SUBMIT  | {request.request_id} | Tier {request.tier} | "
            f"{request.agent_id} | {request.operation}"
        )

    def log_decision(
        self, request: ApprovalRequest, decision: DecisionRecord
    ) -> None:
        """Log the human (or system) decision."""
        self._append_request_log(
            request,
            f"DECISION_RECORDED: {decision.action}",
            details={
                "Decided By": decision.decided_by,
                "Decided At": decision.decided_at.isoformat(),
                "Reason": decision.reason or "—",
                "Comment": decision.comment or "—",
                "Checksum": decision.checksum,
            },
        )
        self._append_daily_log(
            f"DECIDE  | {request.request_id} | {decision.action} | "
            f"by={decision.decided_by}"
        )

    def log_auto_approved(self, request: ApprovalRequest) -> None:
        """Log an automatic approval (Tier 0–1)."""
        self._append_request_log(
            request,
            f"AUTO_APPROVED: {request.request_id}",
            details={
                "Agent": request.agent_id,
                "Operation": request.operation,
                "Tier": str(request.tier),
                "Reason": "Tier 0/1 — auto-approve policy",
            },
        )
        self._append_daily_log(
            f"AUTO    | {request.request_id} | Tier {request.tier} | "
            f"{request.agent_id} | {request.operation}"
        )

    def log_timeout(self, request: ApprovalRequest) -> None:
        """Log an SLA timeout event."""
        self._append_request_log(
            request,
            f"SLA_TIMEOUT: {request.request_id}",
            details={
                "SLA": self._sla_str(request),
                "Default Action": request.sla.timeout_action,
                "Decided By": "SYSTEM (timeout)",
            },
        )
        self._append_daily_log(
            f"TIMEOUT | {request.request_id} | Tier {request.tier} | "
            f"agent={request.agent_id}"
        )

    def log_escalation(self, request: ApprovalRequest) -> None:
        """Log an escalation trigger."""
        self._append_request_log(
            request,
            f"ESCALATION_TRIGGERED: {request.request_id}",
            details={
                "Escalation At": (
                    request.sla.escalation_at.isoformat()
                    if request.sla.escalation_at else "N/A"
                ),
                "Remaining": f"{request.sla.remaining_seconds():.0f}s",
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _audit_path(self, request: ApprovalRequest) -> Path:
        return self._audit_dir / f"{request.request_id}.md"

    def _append_request_log(
        self,
        request: ApprovalRequest,
        event: str,
        details: dict,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        path = self._audit_path(request)

        if not path.exists():
            header = (
                f"# HITL Audit Log — {request.request_id}\n\n"
                f"_Agent_: `{request.agent_id}`  \n"
                f"_Operation_: `{request.operation}`  \n"
                f"_Tier_: `{request.tier}`  \n"
                f"_Submitted_: `{request.submitted_at.isoformat()}`  \n\n"
                "---\n\n"
            )
            self._safe_write(path, header)

        lines = [f"\n## [{now.strftime('%H:%M:%S')} UTC] {event}\n"]
        for k, v in details.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")
        self._safe_append(path, "\n".join(lines))

    def _append_daily_log(self, message: str) -> None:
        now = datetime.now(tz=timezone.utc)
        day_path = self._daily_dir / f"{now.strftime('%Y-%m-%d')}.md"
        entry = f"- `{now.strftime('%H:%M:%S')}` {message}\n"
        if not day_path.exists():
            self._safe_write(
                day_path,
                f"# HITL Daily Log — {now.strftime('%Y-%m-%d')}\n\n"
                "_Generated by HUMAN_IN_THE_LOOP_APPROVAL_SKILL v1.0.0_\n\n",
            )
        self._safe_append(day_path, entry)

    @staticmethod
    def _sla_str(request: ApprovalRequest) -> str:
        rb = request.sla.required_by
        if rb is None:
            return "No timeout (Tier 4)" if request.tier == 4 else "Auto-approve"
        return rb.isoformat()

    @staticmethod
    def _safe_write(path: Path, content: str) -> None:
        try:
            path.write_text(content, encoding="utf-8")
        except OSError as exc:
            import sys
            print(f"[HITL AUDIT WARNING] write failed {path}: {exc}", file=sys.stderr)

    @staticmethod
    def _safe_append(path: Path, content: str) -> None:
        try:
            with path.open("a", encoding="utf-8") as f:
                f.write(content)
        except OSError as exc:
            import sys
            print(f"[HITL AUDIT WARNING] append failed {path}: {exc}", file=sys.stderr)
