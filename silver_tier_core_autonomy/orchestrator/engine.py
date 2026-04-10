"""
ORCHESTRATOR_SYSTEM_SKILL — Workflow Engine
Dependency resolution, sequential step execution, and run lifecycle management.

Constitution compliance:
  - Principle IV: Composability Through Standards  (workflows are data)
  - Principle VI: Fail Safe  (STOP/CONTINUE/SKIP on_failure modes)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from .executor import StepExecutor
from .logger import OrchestratorLogger
from .models import (
    OnFailure,
    StepResult,
    StepStatus,
    Workflow,
    WorkflowRun,
    WorkflowStatus,
    make_run,
)


class DependencyError(Exception):
    """Raised when a workflow has circular or unsatisfiable dependencies."""


class WorkflowEngine:
    """
    Executes a Workflow sequentially, respecting step dependencies.

    Dependency resolution
    ---------------------
    Steps are executed in the order they appear in ``workflow.steps``.
    Before each step, all IDs in ``step.depends_on`` must be SUCCESS.
    If a dependency is FAILED/SKIPPED/BLOCKED the dependant step is
    SKIPPED (on_failure=SKIP) or the run is halted (on_failure=STOP).

    Failure modes
    -------------
    - STOP     → mark remaining steps SKIPPED; set run status FAILED.
    - CONTINUE → log the error, continue to next step.
    - SKIP     → mark this step SKIPPED, continue.

    WAITING steps (HITL pending) are returned immediately. The caller
    must poll / resume after the human makes a decision.
    """

    def __init__(
        self,
        executor: StepExecutor,
        logger: OrchestratorLogger,
        run_store: Optional[Any] = None,  # optional persistence layer
    ) -> None:
        self._executor  = executor
        self._logger    = logger
        self._run_store = run_store

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(
        self,
        workflow: Workflow,
        triggered_by: str = "manual",
        context: Optional[dict[str, Any]] = None,
    ) -> WorkflowRun:
        """
        Execute *workflow* from start to finish (or until blocked).

        Returns the :class:`WorkflowRun` in its final state.
        """
        run = make_run(workflow, triggered_by=triggered_by, context=context)
        run.status    = WorkflowStatus.RUNNING
        run.started_at = datetime.now(tz=timezone.utc)

        self._logger.log_run_started(run.run_id, workflow.name, len(workflow.steps))

        try:
            self._execute_steps(workflow, run)
        except Exception as exc:  # noqa: BLE001
            self._logger.log_error(run.run_id, None, f"Unexpected engine error: {exc}", exc)
            run.status = WorkflowStatus.FAILED

        run.finished_at = datetime.now(tz=timezone.utc)
        # Derive final status if not already set to FAILED/ABORTED
        if run.status == WorkflowStatus.RUNNING:
            run.status = self._derive_final_status(run)

        self._logger.log_run_finished(run.run_id, run.status.value, run.duration_ms)
        self._persist(run)
        return run

    # ------------------------------------------------------------------
    # Step execution loop
    # ------------------------------------------------------------------

    def _execute_steps(self, workflow: Workflow, run: WorkflowRun) -> None:
        for step in workflow.steps:
            # Check if any dependency failed/was blocked/skipped
            dep_ok, dep_reason = self._check_dependencies(step.depends_on, run)

            if not dep_ok:
                # Dependency not satisfied
                if step.on_failure == OnFailure.SKIP:
                    result = StepResult(
                        step_id=step.id,
                        status=StepStatus.SKIPPED,
                        error=dep_reason,
                        started_at=datetime.now(tz=timezone.utc),
                        finished_at=datetime.now(tz=timezone.utc),
                    )
                    run.step_results[step.id] = result
                    self._logger.log_step_skipped(run.run_id, step.id, dep_reason or "dependency not met")
                    continue
                else:  # STOP (default) or CONTINUE treats dep failure as step failure
                    result = StepResult(
                        step_id=step.id,
                        status=StepStatus.SKIPPED,
                        error=dep_reason,
                        started_at=datetime.now(tz=timezone.utc),
                        finished_at=datetime.now(tz=timezone.utc),
                    )
                    run.step_results[step.id] = result
                    self._logger.log_step_skipped(run.run_id, step.id, dep_reason or "dependency not met")
                    if step.on_failure == OnFailure.STOP:
                        run.status = WorkflowStatus.FAILED
                        self._skip_remaining(workflow, run, after_step=step.id)
                        return
                    continue

            # Execute the step
            result = self._executor.execute(step, run.run_id, run.step_results)
            run.step_results[step.id] = result

            # If WAITING (HITL pending), pause the run
            if result.status == StepStatus.WAITING:
                self._logger.log_info(
                    run.run_id,
                    f"Step {step.id} waiting for HITL approval (req={result.hitl_request_id})",
                )
                run.status = WorkflowStatus.RUNNING  # still running, just paused
                return  # caller must resume after human decision

            # Handle step failure
            if result.status == StepStatus.FAILED:
                if step.on_failure == OnFailure.STOP:
                    run.status = WorkflowStatus.FAILED
                    self._skip_remaining(workflow, run, after_step=step.id)
                    return
                elif step.on_failure == OnFailure.SKIP:
                    # Retroactively mark as skipped (handler already ran but failed)
                    result.status = StepStatus.SKIPPED
                    run.step_results[step.id] = result
                    self._logger.log_step_skipped(run.run_id, step.id, result.error or "on_failure=skip")
                # CONTINUE: just proceed to next step

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _check_dependencies(
        self, depends_on: list[str], run: WorkflowRun
    ) -> tuple[bool, Optional[str]]:
        """
        Return (True, None) if all dependencies are SUCCESS.
        Return (False, reason) otherwise.
        """
        for dep_id in depends_on:
            dep_result = run.step_results.get(dep_id)
            if dep_result is None:
                return False, f"Dependency '{dep_id}' has not run yet"
            if dep_result.status != StepStatus.SUCCESS:
                return False, (
                    f"Dependency '{dep_id}' is {dep_result.status.value} "
                    f"(error: {dep_result.error or 'n/a'})"
                )
        return True, None

    def _skip_remaining(
        self, workflow: Workflow, run: WorkflowRun, after_step: str
    ) -> None:
        """Mark all steps after *after_step* as SKIPPED (they won't run)."""
        seen = False
        for step in workflow.steps:
            if step.id == after_step:
                seen = True
                continue
            if seen and step.id not in run.step_results:
                run.step_results[step.id] = StepResult(
                    step_id=step.id,
                    status=StepStatus.SKIPPED,
                    error=f"Skipped because step '{after_step}' failed",
                    started_at=datetime.now(tz=timezone.utc),
                    finished_at=datetime.now(tz=timezone.utc),
                )
                self._logger.log_step_skipped(
                    run.run_id, step.id, f"upstream failure at {after_step}"
                )

    def _derive_final_status(self, run: WorkflowRun) -> WorkflowStatus:
        """Infer completion status from step results."""
        statuses = {r.status for r in run.step_results.values()}
        if StepStatus.FAILED in statuses:
            return WorkflowStatus.FAILED
        return WorkflowStatus.COMPLETED

    def _persist(self, run: WorkflowRun) -> None:
        """Optionally persist the run to a store (no-op if store not set)."""
        if self._run_store is not None:
            try:
                self._run_store.save(run)
            except Exception as exc:  # noqa: BLE001
                self._logger.log_error(run.run_id, None, f"Run persist failed: {exc}", exc)
