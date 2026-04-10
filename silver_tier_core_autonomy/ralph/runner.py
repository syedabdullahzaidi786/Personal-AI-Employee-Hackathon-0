"""
RALPH_WIGGUM_LOOP_SKILL — Loop Runner
The main loop coordinator: executes one tick at a time, managing all phases.

Constitution compliance:
  - Principle II:  Explicit Over Implicit   (all phases logged before execution)
  - Principle III: HITL by Default          (hitl_skill.check_timeouts() called each tick)
  - Principle V:   Memory as Knowledge      (memory consolidation phase)
  - Principle VI:  Fail Safe                (max_consecutive_fails → pause)
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .health import HealthChecker
from .logger import RalphLogger
from .memory import MemoryConsolidator
from .models import (
    LoopConfig,
    LoopPhase,
    LoopState,
    PhaseResult,
    TickResult,
    TickStatus,
    make_tick,
)
from .reporter import StatusReporter
from .task_queue import TaskQueue


_STATE_FILE = Path("70-LOGS") / "ralph" / "loop-state.json"


class LoopRunner:
    """
    Coordinates one full tick of the Ralph Wiggum loop.

    Each tick executes (in order):
      1. Health check   — verify all registered components are responding
      2. HITL process   — timeout expired HITL requests (via hitl_skill)
      3. Task dispatch  — pull next N pending tasks, dispatch via orchestrator
      4. Memory consolidate — merge today's episodic entries into semantic summary
      5. Status report  — write loop status to vault

    Usage::

        runner = LoopRunner(config)
        runner.register_health_probe("filesystem", lambda: True)
        runner.set_hitl_skill(hitl)
        runner.set_orchestrator(orchestrator)

        tick = runner.tick()  # one iteration
    """

    def __init__(self, config: LoopConfig) -> None:
        self._config   = config
        vault          = Path(config.vault_root)
        self._logger   = RalphLogger(vault)
        self._checker  = HealthChecker()
        self._queue    = TaskQueue(vault)
        self._memory   = MemoryConsolidator(vault)
        self._reporter = StatusReporter(vault)
        self._state    = self._load_state(vault)
        self._hitl     = None   # Optional HITLSkill
        self._orchestrator = None  # Optional OrchestratorSkill
        self._max_tasks_per_tick = 5

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def register_health_probe(self, name: str, probe) -> None:
        self._checker.register(name, probe)

    def set_hitl_skill(self, hitl) -> None:
        self._hitl = hitl

    def set_orchestrator(self, orchestrator) -> None:
        self._orchestrator = orchestrator

    def set_max_tasks_per_tick(self, n: int) -> None:
        self._max_tasks_per_tick = max(1, n)

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def tick(self) -> TickResult:
        """
        Execute one loop iteration.

        Returns a :class:`TickResult` describing what happened.
        This method never raises — all exceptions are captured.
        """
        # Increment state
        self._state.tick_count += 1
        tick = make_tick(self._state.tick_count)

        self._logger.log_tick_start(tick.tick_id, tick.tick_number)

        # Run each phase
        phase_fns = [
            (LoopPhase.HEALTH_CHECK,       self._config.enable_health_check,       self._phase_health),
            (LoopPhase.HITL_PROCESS,       self._config.enable_hitl_process,       self._phase_hitl),
            (LoopPhase.TASK_DISPATCH,      self._config.enable_task_dispatch,      self._phase_tasks),
            (LoopPhase.MEMORY_CONSOLIDATE, self._config.enable_memory_consolidate, self._phase_memory),
            (LoopPhase.STATUS_REPORT,      self._config.enable_status_report,      self._phase_report),
        ]

        critical_fail = False
        for phase, enabled, fn in phase_fns:
            if not enabled:
                continue
            pr = self._run_phase(tick, phase, fn)
            tick.phase_results.append(pr)
            if pr.status == TickStatus.FAILED and phase == LoopPhase.HEALTH_CHECK:
                # Health failures can halt the tick early if configured
                if self._config.pause_on_unhealthy:
                    critical_fail = True
                    break

        # Derive tick status
        phase_statuses = {p.status for p in tick.phase_results}
        if TickStatus.FAILED in phase_statuses:
            tick.status = TickStatus.FAILED if critical_fail else TickStatus.PARTIAL
        elif TickStatus.PARTIAL in phase_statuses:
            tick.status = TickStatus.PARTIAL
        else:
            tick.status = TickStatus.SUCCESS

        tick.finished_at = datetime.now(tz=timezone.utc)

        # Update persistent state
        if tick.status == TickStatus.SUCCESS:
            self._state.consecutive_fails = 0
            self._state.uptime_ticks += 1
        else:
            self._state.consecutive_fails += 1

        self._state.last_tick_at     = tick.finished_at
        self._state.last_tick_status = tick.status
        self._save_state()

        self._logger.log_tick_end(tick.tick_id, tick.status.value, tick.duration_ms)
        return tick

    # ------------------------------------------------------------------
    # Phases
    # ------------------------------------------------------------------

    def _phase_health(self, tick: TickResult) -> dict:
        report = self._checker.check_all()
        tick.health = report
        self._logger.log_health(
            tick.tick_id, report.overall.value, report.healthy_count, len(report.components)
        )
        return report.to_dict()

    def _phase_hitl(self, tick: TickResult) -> dict:
        if self._hitl is None:
            return {"skipped": "no hitl_skill configured"}
        try:
            expired = self._hitl.check_timeouts()
            return {"timeouts_processed": len(expired)}
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"HITL timeout check failed: {exc}") from exc

    def _phase_tasks(self, tick: TickResult) -> dict:
        if self._orchestrator is None:
            return {"skipped": "no orchestrator configured"}

        pending = self._queue.list_pending(limit=self._max_tasks_per_tick)
        dispatched = 0
        failed     = 0

        for task in pending:
            self._queue.start(task.task_id)
            self._logger.log_task_dispatched(tick.tick_id, task.task_id,
                                              task.skill_name, task.operation)
            try:
                # Build a single-step workflow for this task
                from silver_tier_core_autonomy.orchestrator.models import Workflow, WorkflowStep
                wf = Workflow(
                    id=f"wf-{task.task_id}",
                    name=task.title,
                    steps=[
                        WorkflowStep(
                            id="s1",
                            skill_name=task.skill_name,
                            operation=task.operation,
                            params=task.params,
                        )
                    ],
                )
                run = self._orchestrator.run_workflow(wf, triggered_by="ralph-loop")
                result_dict = run.to_dict()
                self._queue.complete(task.task_id, result=result_dict)
                self._state.total_tasks_done += 1
                dispatched += 1
            except Exception as exc:  # noqa: BLE001
                self._queue.fail(task.task_id, str(exc))
                self._logger.log_error(tick.tick_id, f"Task {task.task_id} failed", exc)
                failed += 1

        return {
            "dispatched": dispatched,
            "failed":     failed,
            "remaining":  self._queue.pending_count(),
        }

    def _phase_memory(self, tick: TickResult) -> dict:
        return self._memory.consolidate()

    def _phase_report(self, tick: TickResult) -> dict:
        mem_stats = next(
            (p.details for p in tick.phase_results
             if p.phase == LoopPhase.MEMORY_CONSOLIDATE and p.status != TickStatus.FAILED),
            None,
        )
        self._reporter.report(
            tick,
            self._state,
            pending_tasks=self._queue.pending_count(),
            memory_stats=mem_stats,
        )
        return {"status_file": str(StatusReporter._STATUS_FILE)}

    # ------------------------------------------------------------------
    # Phase runner helper
    # ------------------------------------------------------------------

    def _run_phase(self, tick: TickResult, phase: LoopPhase, fn) -> PhaseResult:
        started_at = datetime.now(tz=timezone.utc)
        self._logger.log_phase_start(tick.tick_id, phase.value)
        pr = PhaseResult(phase=phase, status=TickStatus.SUCCESS, started_at=started_at)
        try:
            pr.details = fn(tick) or {}
            pr.status  = TickStatus.SUCCESS
        except Exception as exc:  # noqa: BLE001
            pr.status = TickStatus.FAILED
            pr.error  = f"{type(exc).__name__}: {exc}"
            self._logger.log_error(tick.tick_id, f"Phase {phase.value} failed", exc)
        pr.finished_at = datetime.now(tz=timezone.utc)
        self._logger.log_phase_end(tick.tick_id, phase.value, pr.status.value, pr.duration_ms)
        return pr

    # ------------------------------------------------------------------
    # Blocking loop (for CLI)
    # ------------------------------------------------------------------

    def run_forever(self, on_tick=None) -> None:
        """
        Block and run tick() in a loop until interrupted.

        Parameters
        ----------
        on_tick:
            Optional callback ``fn(TickResult) -> None`` called after each tick.
        """
        import signal
        self._running = True
        self._state.started_at = datetime.now(tz=timezone.utc)

        def _stop(signum, frame):
            self._running = False

        signal.signal(signal.SIGINT,  _stop)
        signal.signal(signal.SIGTERM, _stop)

        while self._running:
            tick = self.tick()
            if on_tick:
                try:
                    on_tick(tick)
                except Exception:  # noqa: BLE001
                    pass

            # Pause loop on too many consecutive failures
            if self._state.consecutive_fails >= self._config.max_consecutive_fails:
                self._logger.log_error(
                    None,
                    f"Loop paused after {self._state.consecutive_fails} consecutive failures",
                )
                break

            if not self._running:
                break
            # Sleep until next tick
            time.sleep(self._config.tick_interval_secs)

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _state_path(self, vault: Path) -> Path:
        return vault / _STATE_FILE

    def _load_state(self, vault: Path) -> LoopState:
        path = self._state_path(vault)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            try:
                return LoopState.from_dict(json.loads(path.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001
                pass
        return LoopState(agent_id=self._config.agent_id)

    def _save_state(self) -> None:
        try:
            path = self._state_path(Path(self._config.vault_root))
            path.write_text(json.dumps(self._state.to_dict(), indent=2), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            self._logger.log_error(None, f"State save failed: {exc}", exc)

    # ------------------------------------------------------------------
    # Properties (for CLI / tests)
    # ------------------------------------------------------------------

    @property
    def state(self) -> LoopState:
        return self._state

    @property
    def queue(self) -> TaskQueue:
        return self._queue

    @property
    def memory(self) -> MemoryConsolidator:
        return self._memory

    @property
    def checker(self) -> HealthChecker:
        return self._checker
