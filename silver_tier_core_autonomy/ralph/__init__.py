"""
RALPH_WIGGUM_LOOP_SKILL — Phase 1
The heartbeat of the Personal AI Employee system.

The Ralph Wiggum Loop runs continuously, executing one "tick" at a time.
Each tick:
  1. Health-checks all registered components
  2. Processes expired HITL requests (auto-deny SLA violations)
  3. Dispatches pending tasks via the orchestrator
  4. Consolidates episodic memory into semantic summaries
  5. Writes loop status to the vault

Constitution compliance:
  - Principle I:   Local-First Sovereignty  (all state in vault)
  - Principle II:  Explicit Over Implicit   (all actions logged before execution)
  - Principle III: HITL by Default          (HITL timeouts processed each tick)
  - Principle V:   Memory as Knowledge      (episodic → semantic consolidation)
  - Principle VI:  Fail Safe                (consecutive-fail limit, pause on unhealthy)

Public surface::

    from skills.core.ralph import RalphSkill

    skill = RalphSkill(vault_root="/path/to/obsidian-vault")

    # Register health probes
    skill.register_health_probe("vault", lambda: Path(vault_root).exists())

    # Connect HITL and orchestrator (optional)
    skill.set_hitl_skill(hitl_skill)
    skill.set_orchestrator(orchestrator_skill)

    # Enqueue a task
    skill.enqueue_task(
        title="Rename file",
        skill_name="filesystem",
        operation="rename",
        params={"source": "old.md", "destination": "new.md"},
    )

    # Run one tick
    tick = skill.tick()
    print(tick.status)  # TickStatus.SUCCESS

    # Run forever
    skill.start()
"""

from pathlib import Path
from typing import Any, Callable, Optional

from .health import HealthChecker
from .logger import RalphLogger
from .memory import MemoryConsolidator
from .models import (
    ComponentHealth,
    HealthReport,
    HealthState,
    LoopConfig,
    LoopPhase,
    LoopState,
    PhaseResult,
    TaskEntry,
    TaskPriority,
    TaskStatus,
    TickResult,
    TickStatus,
    make_task,
    make_tick,
)
from .reporter import StatusReporter
from .runner import LoopRunner
from .task_queue import TaskQueue


class RalphSkill:
    """
    High-level facade for RALPH_WIGGUM_LOOP_SKILL Phase 1.

    Composes: LoopRunner + HealthChecker + TaskQueue + MemoryConsolidator +
              StatusReporter + RalphLogger.
    """

    def __init__(
        self,
        vault_root: str | Path,
        config: Optional[LoopConfig] = None,
    ) -> None:
        if config is None:
            config = LoopConfig(vault_root=str(vault_root))
        config.vault_root = str(vault_root)
        self._config = config
        self._runner = LoopRunner(config)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def register_health_probe(self, name: str, probe: Callable[[], bool]) -> None:
        """Register a health probe for a named component."""
        self._runner.register_health_probe(name, probe)

    def set_hitl_skill(self, hitl: Any) -> None:
        """Attach a HITLSkill instance for timeout processing each tick."""
        self._runner.set_hitl_skill(hitl)

    def set_orchestrator(self, orchestrator: Any) -> None:
        """Attach an OrchestratorSkill instance for task dispatch each tick."""
        self._runner.set_orchestrator(orchestrator)

    def set_max_tasks_per_tick(self, n: int) -> None:
        self._runner.set_max_tasks_per_tick(n)

    # ------------------------------------------------------------------
    # Task management
    # ------------------------------------------------------------------

    def enqueue_task(
        self,
        title: str,
        skill_name: str,
        operation: str,
        params: Optional[dict] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        submitted_by: str = "operator",
    ) -> TaskEntry:
        """Add a task to the pending queue. It will be dispatched on the next tick."""
        task = make_task(
            title=title,
            skill_name=skill_name,
            operation=operation,
            params=params,
            priority=priority,
            submitted_by=submitted_by,
        )
        return self._runner.queue.enqueue(task)

    def list_pending_tasks(self, limit: int = 50) -> list[TaskEntry]:
        return self._runner.queue.list_pending(limit=limit)

    def list_done_tasks(self, limit: int = 50) -> list[TaskEntry]:
        return self._runner.queue.list_done(limit=limit)

    def pending_count(self) -> int:
        return self._runner.queue.pending_count()

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def tick(self) -> TickResult:
        """Execute one loop tick and return the result."""
        return self._runner.tick()

    def start(self, on_tick: Optional[Callable[[TickResult], None]] = None) -> None:
        """Block and run the loop continuously. Stops on SIGINT/SIGTERM."""
        self._runner.run_forever(on_tick=on_tick)

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------

    def consolidate_memory(self) -> dict:
        """Manually trigger memory consolidation."""
        return self._runner.memory.consolidate()

    def write_episodic(
        self, title: str, content: str, tags: Optional[list[str]] = None
    ) -> Path:
        """Write a new episodic memory entry to the vault."""
        return self._runner.memory.write_episodic(title, content, tags)

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def check_health(self) -> HealthReport:
        """Run health checks now and return the report."""
        return self._runner.checker.check_all()

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def runner(self) -> LoopRunner:
        return self._runner

    @property
    def state(self) -> LoopState:
        return self._runner.state

    @property
    def config(self) -> LoopConfig:
        return self._config


__all__ = [
    "RalphSkill",
    "LoopRunner",
    "HealthChecker",
    "TaskQueue",
    "MemoryConsolidator",
    "StatusReporter",
    "RalphLogger",
    # Models
    "LoopConfig",
    "LoopState",
    "TickResult",
    "TickStatus",
    "LoopPhase",
    "PhaseResult",
    "HealthReport",
    "ComponentHealth",
    "HealthState",
    "TaskEntry",
    "TaskStatus",
    "TaskPriority",
    "make_task",
    "make_tick",
]
