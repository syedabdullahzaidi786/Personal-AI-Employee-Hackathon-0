"""
ORCHESTRATOR_SYSTEM_SKILL — Step Executor
Runs a single WorkflowStep: resolves template params, checks HITL gate,
calls the registered handler, and returns a StepResult.

Constitution compliance:
  - Principle III: Human-in-the-Loop by Default  (tier >= 2 → HITL gate)
  - Principle VI:  Fail Safe  (errors produce FAILED results, never crash the engine)
"""

from __future__ import annotations

import re
import traceback
from datetime import datetime, timezone
from typing import Any, Optional

from .logger import OrchestratorLogger
from .models import OnFailure, StepResult, StepStatus, WorkflowStep
from .registry import LookupError, SkillRegistry


# ---------------------------------------------------------------------------
# Template resolver
# ---------------------------------------------------------------------------

_TEMPLATE_RE = re.compile(r"\{(?P<step_id>[^.]+)\.output\.(?P<key>[^}]+)\}")


def resolve_params(
    params: dict[str, Any],
    step_results: dict[str, StepResult],
) -> dict[str, Any]:
    """
    Recursively resolve template references in *params*.

    Template syntax: ``{step_id.output.key}``

    Raises ``ValueError`` if a referenced step hasn't run yet or the key
    is missing from its output.
    """
    resolved: dict[str, Any] = {}
    for k, v in params.items():
        resolved[k] = _resolve_value(v, step_results)
    return resolved


def _resolve_value(value: Any, step_results: dict[str, StepResult]) -> Any:
    if isinstance(value, str):
        return _resolve_string(value, step_results)
    if isinstance(value, dict):
        return {k: _resolve_value(v, step_results) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_value(item, step_results) for item in value]
    return value


def _resolve_string(value: str, step_results: dict[str, StepResult]) -> Any:
    # Full-match replacement: return typed value from output
    m = _TEMPLATE_RE.fullmatch(value)
    if m:
        return _lookup(m.group("step_id"), m.group("key"), step_results)
    # Partial replacement: inline substitution (string only)
    def sub(match: re.Match) -> str:  # type: ignore[type-arg]
        v = _lookup(match.group("step_id"), match.group("key"), step_results)
        return str(v)
    return _TEMPLATE_RE.sub(sub, value)


def _lookup(step_id: str, key: str, step_results: dict[str, StepResult]) -> Any:
    if step_id not in step_results:
        raise ValueError(f"Template references step '{step_id}' which has not run yet")
    result = step_results[step_id]
    if key not in result.output:
        raise ValueError(
            f"Step '{step_id}' output has no key '{key}'. "
            f"Available keys: {sorted(result.output.keys())}"
        )
    return result.output[key]


# ---------------------------------------------------------------------------
# Step Executor
# ---------------------------------------------------------------------------

class StepExecutor:
    """
    Runs a single WorkflowStep.

    HITL gate logic
    ---------------
    If ``step.tier >= 2`` and a ``hitl_skill`` is provided, the executor
    submits a HITL approval request **before** calling the handler.

    - Auto-approved (tier 0-1): handler runs immediately.
    - Pending (tier 2+):        step returns WAITING status; run_id and
      hitl_request_id are captured so the engine can poll later.
    - Denied:                   step returns BLOCKED status.
    """

    def __init__(
        self,
        registry: SkillRegistry,
        logger: OrchestratorLogger,
        hitl_skill: Optional[Any] = None,   # HITLSkill instance (optional)
    ) -> None:
        self._registry  = registry
        self._logger    = logger
        self._hitl      = hitl_skill

    # ------------------------------------------------------------------

    def execute(
        self,
        step: WorkflowStep,
        run_id: str,
        step_results: dict[str, StepResult],
    ) -> StepResult:
        """
        Execute *step* and return a :class:`StepResult`.

        This method never raises — all exceptions are captured into the result.
        """
        started_at = datetime.now(tz=timezone.utc)
        self._logger.log_step_started(run_id, step.id, step.skill_name, step.operation)

        # 1. Resolve template params
        try:
            params = resolve_params(step.params, step_results)
        except ValueError as exc:
            return self._fail(step.id, started_at, f"Parameter resolution failed: {exc}")

        # 2. HITL gate (tier >= 2 requires human approval)
        if step.tier >= 2 and self._hitl is not None:
            hitl_result = self._check_hitl(step, run_id, params)
            if hitl_result is not None:
                return hitl_result   # WAITING or BLOCKED

        # 3. Resolve handler
        try:
            handler = self._registry.get(step.skill_name, step.operation)
        except LookupError as exc:
            return self._fail(step.id, started_at, str(exc))

        # 4. Call handler
        try:
            output = handler(**params)
            if not isinstance(output, dict):
                output = {"result": output}
        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc()
            self._logger.log_error(run_id, step.id, str(exc))
            finished_at = datetime.now(tz=timezone.utc)
            result = StepResult(
                step_id=step.id,
                status=StepStatus.FAILED,
                error=f"{type(exc).__name__}: {exc}\n{tb}",
                started_at=started_at,
                finished_at=finished_at,
            )
            self._logger.log_step_finished(
                run_id, step.id, StepStatus.FAILED.value,
                result.duration_ms, error=str(exc),
            )
            return result

        finished_at = datetime.now(tz=timezone.utc)
        result = StepResult(
            step_id=step.id,
            status=StepStatus.SUCCESS,
            output=output,
            started_at=started_at,
            finished_at=finished_at,
        )
        self._logger.log_step_finished(
            run_id, step.id, StepStatus.SUCCESS.value, result.duration_ms,
        )
        return result

    # ------------------------------------------------------------------
    # HITL helpers
    # ------------------------------------------------------------------

    def _check_hitl(
        self,
        step: WorkflowStep,
        run_id: str,
        params: dict[str, Any],
    ) -> Optional[StepResult]:
        """
        Submit HITL approval request.

        Returns a StepResult (WAITING or BLOCKED) if execution must pause,
        or None if the request was auto-approved and execution can proceed.
        """
        # HITL decision status constants (string values from hitl.models.Decision)
        _AUTO_STATUSES     = ("AUTO_APPROVED", "APPROVED")
        _DENIED_STATUS     = "DENIED"

        try:
            req = self._hitl.submit(
                agent_id="orchestrator",
                operation=f"{step.skill_name}.{step.operation}",
                tier=step.tier,
                action_summary=step.description or f"Run {step.skill_name}.{step.operation}",
                reason=f"Orchestrator workflow step {step.id} (run {run_id})",
                details={
                    "run_id": run_id,
                    "step_id": step.id,
                    "params": params,
                },
                risk={"tier": step.tier},
            )
        except Exception as exc:  # noqa: BLE001
            # Fail safe: if HITL submit fails, block the step
            return StepResult(
                step_id=step.id,
                status=StepStatus.FAILED,
                error=f"HITL submission failed: {exc}",
                started_at=datetime.now(tz=timezone.utc),
                finished_at=datetime.now(tz=timezone.utc),
            )

        self._logger.log_hitl_gate(run_id, step.id, req.request_id, step.tier)

        # Tier 0-1 → auto-approved → proceed
        if req.status in _AUTO_STATUSES:
            return None

        # Denied → BLOCKED
        if req.status == _DENIED_STATUS:
            return StepResult(
                step_id=step.id,
                status=StepStatus.BLOCKED,
                error="HITL denied",
                hitl_request_id=req.request_id,
                started_at=datetime.now(tz=timezone.utc),
                finished_at=datetime.now(tz=timezone.utc),
            )

        # PENDING → WAITING (human must decide)
        return StepResult(
            step_id=step.id,
            status=StepStatus.WAITING,
            hitl_request_id=req.request_id,
            started_at=datetime.now(tz=timezone.utc),
        )

    def _fail(self, step_id: str, started_at: datetime, error: str) -> StepResult:
        finished_at = datetime.now(tz=timezone.utc)
        return StepResult(
            step_id=step_id,
            status=StepStatus.FAILED,
            error=error,
            started_at=started_at,
            finished_at=finished_at,
        )
