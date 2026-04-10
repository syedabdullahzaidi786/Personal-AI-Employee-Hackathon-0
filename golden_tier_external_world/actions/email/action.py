"""
EMAIL_MCP_ACTION_SKILL — Core Action Engine
Phase 1: Validate → HITL gate (tier ≥ 2) → Send via adapter.

Constitution compliance:
  - Principle III: HITL enforced for Tier ≥ 2
  - Principle VI: Fail Safe — submit() never raises; errors surface as EmailResult
  - Section 8: No secrets in logs — adapter handles credentials transparently
"""

from __future__ import annotations

from typing import Any, Optional

from .adapter import EmailAdapter, MockEmailAdapter
from .logger import EmailActionLogger
from .models import (
    EmailActionStatus,
    EmailConfig,
    EmailRequest,
    EmailResult,
)


class ValidationError(Exception):
    """Raised when an EmailRequest fails pre-send validation."""


def _validate(request: EmailRequest, config: EmailConfig) -> None:
    """Validate EmailRequest against EmailConfig constraints. Raises ValidationError."""
    if not request.to:
        raise ValidationError("Email must have at least one recipient.")
    if len(request.to) > config.max_to:
        raise ValidationError(
            f"Too many recipients: {len(request.to)} > max {config.max_to}."
        )
    if not request.subject:
        raise ValidationError("Email subject must not be empty.")
    if not request.subject.strip():
        raise ValidationError("Email subject must not be blank.")


class EmailAction:
    """
    Core action engine for EMAIL_MCP_ACTION_SKILL.

    Send flow:
      1. submit(request) → validate
      2. If tier ≥ 2 and hitl_skill provided → queue for human approval
      3. If tier < 2 or no hitl_skill → send immediately via adapter
      4. Log every outcome to 70-LOGS/email/

    Never raises — all errors are captured as EmailResult.
    """

    def __init__(
        self,
        config: EmailConfig,
        adapter: Optional[EmailAdapter] = None,
        logger: Optional[EmailActionLogger] = None,
        hitl_skill: Optional[Any] = None,
    ) -> None:
        self._config  = config
        self._adapter = adapter or MockEmailAdapter()
        self._logger  = logger or EmailActionLogger(config.vault_root)
        self._hitl    = hitl_skill

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(self, request: EmailRequest) -> EmailResult:
        """
        Validate and dispatch an email request.

        Returns EmailResult with status:
          - SENT             → sent immediately (tier < 2)
          - PENDING_APPROVAL → queued in HITL (tier ≥ 2)
          - DENIED           → HITL submission failed (fail-safe)
          - FAILED           → validation or adapter error
        """
        # Fill sender from config if not set
        if not request.sender:
            request.sender = self._config.sender_address

        # Validate
        try:
            _validate(request, self._config)
        except ValidationError as exc:
            result = EmailResult(
                request_id=request.request_id,
                status=EmailActionStatus.FAILED,
                error=str(exc),
            )
            self._logger.log_error(request.request_id, str(exc))
            return result

        self._logger.log_submitted(request)

        # HITL gate: tier ≥ 2 requires human approval
        if request.tier >= 2 and self._hitl is not None:
            return self._submit_to_hitl(request)

        # Direct send
        return self._send(request)

    def health_check(self) -> bool:
        """Return True if the adapter is healthy."""
        return self._adapter.health_check()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _send(self, request: EmailRequest) -> EmailResult:
        """Send immediately via the adapter."""
        try:
            result = self._adapter.send(request)
        except Exception as exc:  # noqa: BLE001
            result = EmailResult(
                request_id=request.request_id,
                status=EmailActionStatus.FAILED,
                error=str(exc),
            )
        self._logger.log_result(result)
        return result

    def _submit_to_hitl(self, request: EmailRequest) -> EmailResult:
        """Submit request to HITL for human approval. Fail-safe on error → DENIED."""
        try:
            from bronze_tier_governance.hitl.models import make_request

            hitl_req = make_request(
                agent_id="email-action-skill",
                operation="send_email",
                tier=request.tier,
                action_summary=(
                    f"Send email to {', '.join(request.to[:3])}"
                    f"{'...' if len(request.to) > 3 else ''}: {request.subject!r}"
                ),
                reason=f"Email send requested (tier {request.tier})",
                details=request.to_dict(),
                risk={
                    "recipients":       len(request.to),
                    "has_attachments":  bool(request.attachment_names),
                    "tier":             request.tier,
                },
            )
            self._hitl.submit(hitl_req)
            self._logger.log_queued_for_hitl(request, hitl_req.request_id)
            return EmailResult(
                request_id=request.request_id,
                status=EmailActionStatus.PENDING_APPROVAL,
                hitl_request_id=hitl_req.request_id,
            )

        except Exception as exc:  # noqa: BLE001
            # HITL failure → deny (fail-safe: refuse to send without approval)
            msg = f"HITL submission failed: {exc}. Email denied (fail-safe)."
            self._logger.log_error(request.request_id, msg)
            return EmailResult(
                request_id=request.request_id,
                status=EmailActionStatus.DENIED,
                error=msg,
            )
