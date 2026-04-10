"""
HUMAN_IN_THE_LOOP_APPROVAL_SKILL — Request Validator
Phase 1: Validate incoming approval requests before queuing.
"""

from .models import ApprovalRequest


class ValidationError(Exception):
    """Raised when an approval request fails validation."""


class DecisionError(Exception):
    """Raised when a decision cannot be processed."""


# Minimum context keys required for Tier 2+
_MIN_RISK_KEYS = {"blast_radius", "reversibility"}


def validate_request(request: ApprovalRequest) -> None:
    """
    Validate *request* before it is queued.

    Raises ValidationError with a descriptive message on failure.
    """
    # Required identity fields
    if not request.agent_id or not request.agent_id.strip():
        raise ValidationError("agent_id is required and cannot be empty")

    if not request.operation or not request.operation.strip():
        raise ValidationError("operation is required and cannot be empty")

    if not request.action_summary or not request.action_summary.strip():
        raise ValidationError("action_summary is required and cannot be empty")

    # Tier must be 0–4
    if request.tier not in range(5):
        raise ValidationError(f"tier must be 0-4, got {request.tier!r}")

    # Tier 2+ requires explicit risk assessment
    if request.tier >= 2:
        if not request.risk:
            raise ValidationError(
                f"risk assessment required for tier >= 2 (tier={request.tier})"
            )
        missing = _MIN_RISK_KEYS - request.risk.keys()
        if missing:
            raise ValidationError(
                f"risk assessment missing required keys for tier {request.tier}: {missing}"
            )

    # Reason must be non-empty for all tiers
    if not request.reason or not request.reason.strip():
        raise ValidationError("reason is required and cannot be empty")


def validate_decision_input(
    request: ApprovalRequest,
    action: str,
    operator: str,
) -> None:
    """
    Validate that a decision can be applied to *request*.

    Raises DecisionError on failure.
    """
    from .models import Decision

    allowed_actions = {"approve", "deny", "defer", "timeout"}
    if action not in allowed_actions:
        raise DecisionError(
            f"Invalid action '{action}'. Allowed: {allowed_actions}"
        )

    if not operator or not operator.strip():
        raise DecisionError("operator cannot be empty")

    if request.status != Decision.PENDING:
        raise DecisionError(
            f"Request {request.request_id!r} already decided "
            f"(status={request.status!r}). Cannot apply '{action}'."
        )
