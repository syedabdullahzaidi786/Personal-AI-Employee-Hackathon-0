"""
ORCHESTRATOR_SYSTEM_SKILL — Phase 1
Workflow execution engine with skill registry, HITL integration, and audit logging.

Constitution compliance:
  - Principle II:  Explicit Over Implicit  (workflow-as-data; all state declared)
  - Principle III: Human-in-the-Loop by Default  (tier>=2 gates HITL)
  - Principle IV:  Composability Through Standards  (registered skill handlers)
  - Principle V:   Memory as Knowledge  (all runs persisted and logged)
  - Principle VI:  Fail Safe  (STOP/CONTINUE/SKIP failure modes)

Public surface::

    from skills.core.orchestrator import OrchestratorSkill

    skill = OrchestratorSkill(vault_root="/path/to/obsidian-vault")

    # Register skill handlers
    skill.register("filesystem", "rename", my_rename_fn)
    skill.register("hitl", "submit", my_hitl_submit_fn)

    # Build a workflow
    from skills.core.orchestrator.models import Workflow, WorkflowStep, OnFailure
    wf = Workflow(
        id="wf-001",
        name="Rename and Tag",
        steps=[
            WorkflowStep(id="s1", skill_name="filesystem", operation="rename",
                         params={"source": "old.md", "destination": "new.md"}),
            WorkflowStep(id="s2", skill_name="filesystem", operation="add_frontmatter",
                         params={"path": "{s1.output.destination}", "tags": ["done"]}),
        ],
    )

    run = skill.run_workflow(wf, triggered_by="cli")
    print(run.status)  # WorkflowStatus.COMPLETED
"""

from pathlib import Path
from typing import Any, Callable, Optional

from .engine import WorkflowEngine
from .executor import StepExecutor
from .logger import OrchestratorLogger
from .models import (
    OnFailure,
    StepResult,
    StepStatus,
    Workflow,
    WorkflowRun,
    WorkflowStatus,
    WorkflowStep,
    make_run,
)
from .registry import SkillRegistry
from .store import RunStore


class OrchestratorSkill:
    """
    High-level facade for ORCHESTRATOR_SYSTEM_SKILL Phase 1.

    Composes: SkillRegistry + StepExecutor + WorkflowEngine + RunStore + OrchestratorLogger.
    """

    def __init__(
        self,
        vault_root: str | Path,
        hitl_skill: Optional[Any] = None,
    ) -> None:
        vault = Path(vault_root)
        self._registry = SkillRegistry()
        self._logger   = OrchestratorLogger(vault)
        self._store    = RunStore(vault)
        self._executor = StepExecutor(
            registry=self._registry,
            logger=self._logger,
            hitl_skill=hitl_skill,
        )
        self._engine = WorkflowEngine(
            executor=self._executor,
            logger=self._logger,
            run_store=self._store,
        )

    # ------------------------------------------------------------------
    # Registry
    # ------------------------------------------------------------------

    def register(
        self,
        skill_name: str,
        operation: str,
        handler: Callable[..., dict[str, Any]],
        *,
        overwrite: bool = False,
    ) -> None:
        """Register a handler for ``skill_name.operation``."""
        self._registry.register(skill_name, operation, handler, overwrite=overwrite)

    def register_skill(
        self,
        skill_name: str,
        operations: dict[str, Callable[..., dict[str, Any]]],
        *,
        overwrite: bool = False,
    ) -> None:
        """Batch-register multiple operations for a skill."""
        self._registry.register_skill(skill_name, operations, overwrite=overwrite)

    def list_registry(self) -> dict[str, list[str]]:
        """Return {skill_name: [operations]} mapping."""
        return self._registry.to_dict()

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run_workflow(
        self,
        workflow: Workflow,
        triggered_by: str = "manual",
        context: Optional[dict[str, Any]] = None,
    ) -> WorkflowRun:
        """
        Execute *workflow* and return the completed :class:`WorkflowRun`.

        Steps are run sequentially in declaration order, with dependency
        checks applied before each step.
        """
        return self._engine.run(workflow, triggered_by=triggered_by, context=context)

    # ------------------------------------------------------------------
    # Query / introspection
    # ------------------------------------------------------------------

    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        """Fetch a persisted WorkflowRun by ID."""
        return self._store.get(run_id)

    def list_runs(self) -> list[WorkflowRun]:
        """Return all persisted runs (active + completed)."""
        return self._store.list_all()

    def list_active_runs(self) -> list[WorkflowRun]:
        """Return runs that are still active (RUNNING / WAITING)."""
        return self._store.list_active()


__all__ = [
    "OrchestratorSkill",
    "WorkflowEngine",
    "StepExecutor",
    "SkillRegistry",
    "OrchestratorLogger",
    "RunStore",
    # Models
    "Workflow",
    "WorkflowStep",
    "WorkflowRun",
    "StepResult",
    "WorkflowStatus",
    "StepStatus",
    "OnFailure",
    "make_run",
]
