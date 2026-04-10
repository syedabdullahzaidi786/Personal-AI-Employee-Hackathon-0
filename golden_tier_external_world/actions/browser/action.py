"""
BROWSER_MCP_SKILL — Core Action Engine
Phase 1: Validate → HITL gate (tier ≥ 2) → Execute via adapter.

Constitution compliance:
  - Principle III: HITL enforced for Tier ≥ 2
  - Principle VI: Fail Safe — execute() never raises; errors surface as BrowserResult
  - Section 8: No secrets in logs — adapter handles credentials transparently
"""

from __future__ import annotations

from typing import Any, Optional

from .adapter import BrowserAdapter, MockBrowserAdapter
from .logger import BrowserLogger
from .models import (
    BrowserActionStatus,
    BrowserActionType,
    BrowserConfig,
    BrowserRequest,
    BrowserResult,
)

# Supported actions in Phase 1
_SUPPORTED_ACTIONS = {BrowserActionType.OPEN_URL, BrowserActionType.EXTRACT_TEXT}


class ValidationError(Exception):
    """Raised when a BrowserRequest fails pre-execution validation."""


def _validate(request: BrowserRequest) -> None:
    """Validate BrowserRequest. Raises ValidationError on failure."""
    if not request.url:
        raise ValidationError("Browser request must have a non-empty URL.")
    if not request.url.strip():
        raise ValidationError("Browser request URL must not be blank.")
    if request.action not in _SUPPORTED_ACTIONS:
        raise ValidationError(
            f"Unsupported action: {request.action!r}. "
            f"Supported: {sorted(_SUPPORTED_ACTIONS)}"
        )


class BrowserAction:
    """
    Core action engine for BROWSER_MCP_SKILL.

    Execution flow:
      1. execute(request) → validate
      2. If tier ≥ 2 and hitl_skill provided → queue for human approval
      3. If tier < 2 or no hitl_skill → execute immediately via adapter
      4. Log every outcome to 70-LOGS/browser/

    Never raises — all errors are captured as BrowserResult.
    """

    def __init__(
        self,
        config: BrowserConfig,
        adapter: Optional[BrowserAdapter] = None,
        logger: Optional[BrowserLogger] = None,
        hitl_skill: Optional[Any] = None,
    ) -> None:
        self._config  = config
        self._adapter = adapter or MockBrowserAdapter()
        self._logger  = logger or BrowserLogger(config.vault_root)
        self._hitl    = hitl_skill

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, request: BrowserRequest) -> BrowserResult:
        """
        Validate and execute a browser action.

        Returns BrowserResult with status:
          - SUCCESS          → executed immediately (tier < 2)
          - PENDING_APPROVAL → queued in HITL (tier ≥ 2)
          - DENIED           → HITL submission failed (fail-safe)
          - FAILED           → validation or adapter error
        """
        # Validate
        try:
            _validate(request)
        except ValidationError as exc:
            result = BrowserResult(
                request_id=request.request_id,
                action=request.action,
                status=BrowserActionStatus.FAILED,
                url=request.url,
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

    def _run(self, request: BrowserRequest) -> BrowserResult:
        """Execute immediately via the adapter."""
        try:
            result = self._adapter.execute(request)
        except Exception as exc:  # noqa: BLE001
            result = BrowserResult(
                request_id=request.request_id,
                action=request.action,
                status=BrowserActionStatus.FAILED,
                url=request.url,
                error=str(exc),
            )
        self._logger.log_result(result)
        return result

    def _submit_to_hitl(self, request: BrowserRequest) -> BrowserResult:
        """Submit request to HITL for human approval. Fail-safe on error → DENIED."""
        try:
            from bronze_tier_governance.hitl.models import make_request

            hitl_req = make_request(
                agent_id="browser-mcp-skill",
                operation=request.action,
                tier=request.tier,
                action_summary=(
                    f"Browser {request.action}: {request.url[:80]}"
                    f"{f' [selector: {request.selector!r}]' if request.selector else ''}"
                ),
                reason=f"Browser action requested (tier {request.tier})",
                details=request.to_dict(),
                risk={
                    "action":     request.action,
                    "url":        request.url,
                    "tier":       request.tier,
                    "has_selector": bool(request.selector),
                },
            )
            self._hitl.submit(hitl_req)
            self._logger.log_queued_for_hitl(request, hitl_req.request_id)
            return BrowserResult(
                request_id=request.request_id,
                action=request.action,
                status=BrowserActionStatus.PENDING_APPROVAL,
                url=request.url,
                hitl_request_id=hitl_req.request_id,
            )

        except Exception as exc:  # noqa: BLE001
            # HITL failure → deny (fail-safe: refuse to act without approval)
            msg = f"HITL submission failed: {exc}. Action denied (fail-safe)."
            self._logger.log_error(request.request_id, msg)
            return BrowserResult(
                request_id=request.request_id,
                action=request.action,
                status=BrowserActionStatus.DENIED,
                url=request.url,
                error=msg,
            )
