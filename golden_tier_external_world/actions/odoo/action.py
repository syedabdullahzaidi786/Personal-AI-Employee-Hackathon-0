"""
ODOO_MCP_INTEGRATION_SKILL — Core Action Engine
Phase 1: Validate → HITL gate (tier ≥ 2) → Execute via adapter.

Constitution compliance:
  - Principle III: HITL enforced for Tier ≥ 2
  - Principle VI: Fail Safe — execute() never raises; errors surface as OdooResult
  - Section 8: No secrets in logs — adapter handles credentials transparently
"""

from __future__ import annotations

from typing import Any, Optional

from .adapter import OdooAdapter, MockOdooAdapter
from .logger import OdooLogger
from .models import (
    OdooActionStatus,
    OdooConfig,
    OdooOperation,
    OdooRequest,
    OdooResult,
)

# Supported operations in Phase 1
_SUPPORTED_OPERATIONS = {
    OdooOperation.CREATE_RECORD,
    OdooOperation.UPDATE_RECORD,
    OdooOperation.FETCH_RECORD,
}


class ValidationError(Exception):
    """Raised when an OdooRequest fails pre-execution validation."""


def _validate(request: OdooRequest) -> None:
    """Validate OdooRequest. Raises ValidationError on failure."""
    if not request.model:
        raise ValidationError("Odoo request must specify a model name.")
    if not request.model.strip():
        raise ValidationError("Odoo model name must not be blank.")
    if request.operation not in _SUPPORTED_OPERATIONS:
        raise ValidationError(
            f"Unsupported operation: {request.operation!r}. "
            f"Supported: {sorted(_SUPPORTED_OPERATIONS)}"
        )
    if request.operation in (OdooOperation.UPDATE_RECORD, OdooOperation.FETCH_RECORD):
        if request.record_id is None:
            raise ValidationError(
                f"{request.operation} requires a record_id."
            )
    if request.operation == OdooOperation.CREATE_RECORD and not request.data:
        raise ValidationError("create_record requires non-empty data.")


class OdooAction:
    """
    Core action engine for ODOO_MCP_INTEGRATION_SKILL.

    Execution flow:
      1. execute(request) → validate
      2. If tier ≥ 2 and hitl_skill provided → queue for human approval
      3. If tier < 2 or no hitl_skill → execute immediately via adapter
      4. Log every outcome to 70-LOGS/odoo/

    Never raises — all errors are captured as OdooResult.
    """

    def __init__(
        self,
        config: OdooConfig,
        adapter: Optional[OdooAdapter] = None,
        logger: Optional[OdooLogger] = None,
        hitl_skill: Optional[Any] = None,
    ) -> None:
        self._config  = config
        self._adapter = adapter or MockOdooAdapter()
        self._logger  = logger or OdooLogger(config.vault_root)
        self._hitl    = hitl_skill

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, request: OdooRequest) -> OdooResult:
        """
        Validate and execute an Odoo operation.

        Returns OdooResult with status:
          - SUCCESS          → executed immediately (tier < 2)
          - PENDING_APPROVAL → queued in HITL (tier ≥ 2)
          - DENIED           → HITL submission failed (fail-safe)
          - FAILED           → validation or adapter error
          - NOT_FOUND        → record does not exist
        """
        # Validate
        try:
            _validate(request)
        except ValidationError as exc:
            result = OdooResult(
                request_id=request.request_id,
                operation=request.operation,
                status=OdooActionStatus.FAILED,
                model=request.model,
                record_id=request.record_id,
                error=str(exc),
            )
            self._logger.log_error(request.request_id, str(exc))
            return result

        self._logger.log_submitted(request)

        # HITL gate: tier ≥ 2 requires human approval
        if request.tier >= 2 and self._hitl is not None:
            return self._submit_to_hitl(request)

        # Direct execution
        return self._run(request)

    def health_check(self) -> bool:
        """Return True if the adapter is healthy."""
        return self._adapter.health_check()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run(self, request: OdooRequest) -> OdooResult:
        """Execute immediately via the adapter."""
        try:
            result = self._adapter.execute(request)
        except Exception as exc:  # noqa: BLE001
            result = OdooResult(
                request_id=request.request_id,
                operation=request.operation,
                status=OdooActionStatus.FAILED,
                model=request.model,
                record_id=request.record_id,
                error=str(exc),
            )
        self._logger.log_result(result)
        return result

    def _submit_to_hitl(self, request: OdooRequest) -> OdooResult:
        """Submit request to HITL for human approval. Fail-safe on error → DENIED."""
        try:
            from bronze_tier_governance.hitl.models import make_request

            hitl_req = make_request(
                agent_id="odoo-mcp-skill",
                operation=request.operation,
                tier=request.tier,
                action_summary=(
                    f"Odoo {request.operation} on {request.model}"
                    f"{f' (id={request.record_id})' if request.record_id else ''}"
                    f": {list(request.data.keys())[:5]}"
                ),
                reason=f"Odoo {request.operation} requested (tier {request.tier})",
                details=request.to_dict(),
                risk={
                    "operation":  request.operation,
                    "model":      request.model,
                    "record_id":  request.record_id,
                    "field_count": len(request.data),
                    "tier":       request.tier,
                },
            )
            self._hitl.submit(hitl_req)
            self._logger.log_queued_for_hitl(request, hitl_req.request_id)
            return OdooResult(
                request_id=request.request_id,
                operation=request.operation,
                status=OdooActionStatus.PENDING_APPROVAL,
                model=request.model,
                record_id=request.record_id,
                hitl_request_id=hitl_req.request_id,
            )

        except Exception as exc:  # noqa: BLE001
            # HITL failure → deny (fail-safe: refuse to mutate without approval)
            msg = f"HITL submission failed: {exc}. Operation denied (fail-safe)."
            self._logger.log_error(request.request_id, msg)
            return OdooResult(
                request_id=request.request_id,
                operation=request.operation,
                status=OdooActionStatus.DENIED,
                model=request.model,
                record_id=request.record_id,
                error=msg,
            )
