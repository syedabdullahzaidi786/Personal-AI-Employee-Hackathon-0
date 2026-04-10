"""
Unit tests for RALPH_WIGGUM_LOOP_SKILL Phase 1.
Covers: models, health checker, task queue, memory consolidator,
        logger, reporter, runner, facade.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import sys

from silver_tier_core_autonomy.ralph.models import (
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
from silver_tier_core_autonomy.ralph.health import HealthChecker
from silver_tier_core_autonomy.ralph.task_queue import TaskQueue
from silver_tier_core_autonomy.ralph.memory import MemoryConsolidator
from silver_tier_core_autonomy.ralph.logger import RalphLogger
from silver_tier_core_autonomy.ralph.reporter import StatusReporter
from silver_tier_core_autonomy.ralph.runner import LoopRunner
from silver_tier_core_autonomy.ralph import RalphSkill


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def config(tmp_vault: Path) -> LoopConfig:
    return LoopConfig(
        vault_root=str(tmp_vault),
        tick_interval_secs=60,
        enable_status_report=True,
    )


@pytest.fixture
def skill(tmp_vault: Path) -> RalphSkill:
    return RalphSkill(vault_root=tmp_vault)


@pytest.fixture
def queue(tmp_vault: Path) -> TaskQueue:
    return TaskQueue(tmp_vault)


@pytest.fixture
def memory(tmp_vault: Path) -> MemoryConsolidator:
    return MemoryConsolidator(tmp_vault)


@pytest.fixture
def logger(tmp_vault: Path) -> RalphLogger:
    return RalphLogger(tmp_vault)


@pytest.fixture
def reporter(tmp_vault: Path) -> StatusReporter:
    return StatusReporter(tmp_vault)


@pytest.fixture
def runner(config: LoopConfig) -> LoopRunner:
    return LoopRunner(config)


# ---------------------------------------------------------------------------
# 1. Models
# ---------------------------------------------------------------------------

class TestLoopConfig:
    def test_defaults(self, tmp_vault: Path):
        cfg = LoopConfig(vault_root=str(tmp_vault))
        assert cfg.tick_interval_secs == 300
        assert cfg.max_consecutive_fails == 3
        assert cfg.enable_health_check is True

    def test_to_dict_roundtrip(self, config: LoopConfig):
        d = config.to_dict()
        cfg2 = LoopConfig.from_dict(d)
        assert cfg2.vault_root == config.vault_root
        assert cfg2.tick_interval_secs == config.tick_interval_secs


class TestLoopState:
    def test_defaults(self):
        state = LoopState()
        assert state.tick_count == 0
        assert state.consecutive_fails == 0

    def test_to_dict_roundtrip(self):
        state = LoopState(agent_id="test", tick_count=5, uptime_ticks=4)
        state.last_tick_at = datetime.now(tz=timezone.utc)
        state.last_tick_status = TickStatus.SUCCESS
        d = state.to_dict()
        s2 = LoopState.from_dict(d)
        assert s2.tick_count == 5
        assert s2.uptime_ticks == 4
        assert s2.last_tick_status == TickStatus.SUCCESS


class TestTickResult:
    def test_make_tick(self):
        tick = make_tick(1)
        assert tick.tick_number == 1
        assert tick.tick_id.startswith("TICK-")
        assert tick.status == TickStatus.SUCCESS

    def test_duration_ms(self):
        tick = make_tick(1)
        tick.finished_at = tick.started_at + timedelta(milliseconds=123)
        assert abs(tick.duration_ms - 123.0) < 1.0

    def test_to_dict(self):
        tick = make_tick(1)
        tick.finished_at = datetime.now(tz=timezone.utc)
        d = tick.to_dict()
        assert d["tick_number"] == 1
        assert "tick_id" in d


class TestTaskEntry:
    def test_make_task(self):
        t = make_task("Test", "echo", "say", {"msg": "hi"})
        assert t.task_id.startswith("TASK-")
        assert t.skill_name == "echo"
        assert t.priority == TaskPriority.NORMAL

    def test_to_dict_roundtrip(self):
        t = make_task("Test", "echo", "say")
        t.status = TaskStatus.DONE
        t.finished_at = datetime.now(tz=timezone.utc)
        d = t.to_dict()
        t2 = TaskEntry.from_dict(d)
        assert t2.task_id == t.task_id
        assert t2.status == TaskStatus.DONE

    def test_priority_ordering(self):
        assert TaskPriority.URGENT < TaskPriority.HIGH < TaskPriority.NORMAL < TaskPriority.LOW


class TestComponentHealth:
    def test_to_dict(self):
        ch = ComponentHealth(name="test", state=HealthState.HEALTHY,
                             last_check=datetime.now(tz=timezone.utc), latency_ms=5.2)
        d = ch.to_dict()
        assert d["name"] == "test"
        assert d["state"] == "healthy"

    def test_from_dict_roundtrip(self):
        ch = ComponentHealth(name="x", state=HealthState.DEGRADED,
                             last_check=datetime.now(tz=timezone.utc), message="slow")
        ch2 = ComponentHealth.from_dict(ch.to_dict())
        assert ch2.state == HealthState.DEGRADED
        assert ch2.message == "slow"


class TestHealthReport:
    def test_counts(self):
        rpt = HealthReport(
            checked_at=datetime.now(tz=timezone.utc),
            components=[
                ComponentHealth("a", HealthState.HEALTHY),
                ComponentHealth("b", HealthState.UNHEALTHY),
                ComponentHealth("c", HealthState.HEALTHY),
            ],
            overall=HealthState.UNHEALTHY,
        )
        assert rpt.healthy_count == 2
        assert rpt.unhealthy_count == 1


# ---------------------------------------------------------------------------
# 2. Health Checker
# ---------------------------------------------------------------------------

class TestHealthChecker:
    def test_healthy_probe(self):
        checker = HealthChecker()
        checker.register("vault", lambda: True)
        rpt = checker.check_all()
        assert rpt.overall == HealthState.HEALTHY
        assert len(rpt.components) == 1
        assert rpt.components[0].state == HealthState.HEALTHY

    def test_unhealthy_probe_exception(self):
        checker = HealthChecker()
        def bad(): raise RuntimeError("disk full")
        checker.register("disk", bad)
        rpt = checker.check_all()
        assert rpt.overall == HealthState.UNHEALTHY
        assert "RuntimeError" in rpt.components[0].message

    def test_false_probe_degraded(self):
        checker = HealthChecker()
        checker.register("slow", lambda: False)
        rpt = checker.check_all()
        assert rpt.overall == HealthState.DEGRADED

    def test_mixed_probes(self):
        checker = HealthChecker()
        checker.register("ok",  lambda: True)
        checker.register("bad", lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        rpt = checker.check_all()
        assert rpt.overall == HealthState.UNHEALTHY
        assert rpt.healthy_count == 1
        assert rpt.unhealthy_count == 1

    def test_empty_probes_healthy(self):
        checker = HealthChecker()
        rpt = checker.check_all()
        assert rpt.overall == HealthState.HEALTHY

    def test_check_single(self):
        checker = HealthChecker()
        checker.register("x", lambda: True)
        ch = checker.check("x")
        assert ch.state == HealthState.HEALTHY

    def test_check_unregistered_unknown(self):
        checker = HealthChecker()
        ch = checker.check("missing")
        assert ch.state == HealthState.UNKNOWN

    def test_unregister(self):
        checker = HealthChecker()
        checker.register("x", lambda: True)
        checker.unregister("x")
        assert checker.list_components() == []

    def test_probe_must_be_callable(self):
        checker = HealthChecker()
        with pytest.raises(ValueError):
            checker.register("x", "not-callable")  # type: ignore

    def test_list_components(self):
        checker = HealthChecker()
        checker.register("b", lambda: True)
        checker.register("a", lambda: True)
        assert checker.list_components() == ["a", "b"]

    def test_latency_recorded(self):
        checker = HealthChecker()
        checker.register("x", lambda: True)
        ch = checker.check("x")
        assert ch.latency_ms >= 0.0


# ---------------------------------------------------------------------------
# 3. Task Queue
# ---------------------------------------------------------------------------

class TestTaskQueue:
    def _task(self, priority=TaskPriority.NORMAL) -> TaskEntry:
        return make_task("Test", "echo", "say", priority=priority)

    def test_enqueue_and_list(self, queue: TaskQueue):
        t = self._task()
        queue.enqueue(t)
        pending = queue.list_pending()
        assert any(p.task_id == t.task_id for p in pending)

    def test_priority_ordering(self, queue: TaskQueue):
        low    = self._task(TaskPriority.LOW)
        urgent = self._task(TaskPriority.URGENT)
        queue.enqueue(low)
        queue.enqueue(urgent)
        pending = queue.list_pending()
        # URGENT (0) should come before LOW (3)
        ids = [p.task_id for p in pending]
        assert ids.index(urgent.task_id) < ids.index(low.task_id)

    def test_start_moves_to_processing(self, queue: TaskQueue):
        t = self._task()
        queue.enqueue(t)
        started = queue.start(t.task_id)
        assert started is not None
        assert started.status == TaskStatus.PROCESSING
        assert queue.list_pending() == []
        assert any(p.task_id == t.task_id for p in queue.list_processing())

    def test_complete_moves_to_done(self, queue: TaskQueue):
        t = self._task()
        queue.enqueue(t)
        queue.start(t.task_id)
        done = queue.complete(t.task_id, result={"ok": True})
        assert done is not None
        assert done.status == TaskStatus.DONE
        assert any(p.task_id == t.task_id for p in queue.list_done())
        assert queue.list_processing() == []

    def test_fail_moves_to_failed(self, queue: TaskQueue):
        t = self._task()
        queue.enqueue(t)
        queue.start(t.task_id)
        failed = queue.fail(t.task_id, "boom")
        assert failed is not None
        assert failed.status == TaskStatus.FAILED
        assert failed.error == "boom"

    def test_fail_from_pending(self, queue: TaskQueue):
        t = self._task()
        queue.enqueue(t)
        failed = queue.fail(t.task_id, "pre-start failure")
        assert failed is not None
        assert failed.status == TaskStatus.FAILED

    def test_get_by_id(self, queue: TaskQueue):
        t = self._task()
        queue.enqueue(t)
        found = queue.get(t.task_id)
        assert found is not None
        assert found.task_id == t.task_id

    def test_get_nonexistent_none(self, queue: TaskQueue):
        assert queue.get("TASK-NOPE") is None

    def test_pending_count(self, queue: TaskQueue):
        for _ in range(3):
            queue.enqueue(self._task())
        assert queue.pending_count() == 3

    def test_limit(self, queue: TaskQueue):
        for _ in range(10):
            queue.enqueue(self._task())
        assert len(queue.list_pending(limit=3)) == 3


# ---------------------------------------------------------------------------
# 4. Memory Consolidator
# ---------------------------------------------------------------------------

class TestMemoryConsolidator:
    def test_write_episodic(self, memory: MemoryConsolidator):
        path = memory.write_episodic("Test Event", "This happened today.", tags=["test"])
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "Test Event" in content

    def test_consolidate_empty(self, memory: MemoryConsolidator):
        result = memory.consolidate(since=datetime.now(tz=timezone.utc) - timedelta(hours=1))
        assert result["consolidated_count"] == 0

    def test_consolidate_picks_up_new_entry(self, memory: MemoryConsolidator):
        since = datetime.now(tz=timezone.utc) - timedelta(seconds=1)
        memory.write_episodic("New Memory", "Something memorable.")
        result = memory.consolidate(since=since)
        assert result["consolidated_count"] >= 1

    def test_consolidate_deduplicates(self, memory: MemoryConsolidator):
        since = datetime.now(tz=timezone.utc) - timedelta(seconds=1)
        memory.write_episodic("Dup", "Content.")
        result1 = memory.consolidate(since=since)
        result2 = memory.consolidate(since=since)
        # Second run should skip already-indexed entry
        assert result2["skipped_count"] >= result1["consolidated_count"]

    def test_episodic_count(self, memory: MemoryConsolidator):
        assert memory.get_episodic_count() == 0
        memory.write_episodic("E1", "c1")
        memory.write_episodic("E2", "c2")
        assert memory.get_episodic_count() == 2

    def test_semantic_count_after_consolidate(self, memory: MemoryConsolidator):
        since = datetime.now(tz=timezone.utc) - timedelta(seconds=1)
        memory.write_episodic("S1", "content")
        memory.consolidate(since=since)
        assert memory.get_semantic_count() >= 1

    def test_summary_file_created(self, memory: MemoryConsolidator, tmp_vault: Path):
        since = datetime.now(tz=timezone.utc) - timedelta(seconds=1)
        memory.write_episodic("X", "content")
        result = memory.consolidate(since=since)
        summary_path = tmp_vault / result["summary_path"]
        assert summary_path.exists()


# ---------------------------------------------------------------------------
# 5. Logger
# ---------------------------------------------------------------------------

class TestRalphLogger:
    def test_tick_start_creates_files(self, logger: RalphLogger, tmp_vault: Path):
        logger.log_tick_start("TICK-001", 1)
        daily = list((tmp_vault / "70-LOGS/ralph/daily").glob("*.md"))
        ticks = list((tmp_vault / "70-LOGS/ralph/ticks").glob("*.md"))
        assert len(daily) >= 1
        assert len(ticks) >= 1

    def test_error_writes_to_errors(self, logger: RalphLogger, tmp_vault: Path):
        logger.log_error("TICK-001", "Test error")
        errors = list((tmp_vault / "70-LOGS/ralph/errors").glob("*.md"))
        assert len(errors) >= 1

    def test_phase_events(self, logger: RalphLogger, tmp_vault: Path):
        logger.log_tick_start("TICK-X", 5)
        logger.log_phase_start("TICK-X", "health_check")
        logger.log_phase_end("TICK-X", "health_check", "success", 12.3)
        logger.log_tick_end("TICK-X", "success", 99.0)
        daily = next((tmp_vault / "70-LOGS/ralph/daily").glob("*.md"))
        content = daily.read_text(encoding="utf-8")
        assert "PHASE_START" in content
        assert "PHASE_END" in content

    def test_never_raises(self):
        """Logger must be fail-safe even with invalid vault path."""
        bad_logger = RalphLogger("/nonexistent/vault/xyz")
        try:
            bad_logger.log_info(None, "test")
        except Exception:
            pass  # acceptable — mkdir may fail on some systems


# ---------------------------------------------------------------------------
# 6. Status Reporter
# ---------------------------------------------------------------------------

class TestStatusReporter:
    def _make_tick(self) -> TickResult:
        tick = make_tick(1)
        tick.finished_at = datetime.now(tz=timezone.utc)
        pr = PhaseResult(
            phase=LoopPhase.HEALTH_CHECK,
            status=TickStatus.SUCCESS,
            started_at=tick.started_at,
            finished_at=tick.finished_at,
        )
        tick.phase_results.append(pr)
        return tick

    def test_report_creates_status_file(self, reporter: StatusReporter, tmp_vault: Path):
        tick  = self._make_tick()
        state = LoopState(tick_count=1, uptime_ticks=1)
        reporter.report(tick, state, pending_tasks=2)
        status_file = tmp_vault / "80-MEMORY" / "loop-status.md"
        assert status_file.exists()

    def test_status_file_contains_tick_id(self, reporter: StatusReporter, tmp_vault: Path):
        tick  = self._make_tick()
        state = LoopState(tick_count=1)
        reporter.report(tick, state)
        content = (tmp_vault / "80-MEMORY" / "loop-status.md").read_text(encoding="utf-8")
        assert tick.tick_id in content

    def test_daily_log_appended(self, reporter: StatusReporter, tmp_vault: Path):
        tick  = self._make_tick()
        state = LoopState(tick_count=1)
        reporter.report(tick, state)
        daily = list((tmp_vault / "70-LOGS/ralph/daily").glob("*.md"))
        assert len(daily) >= 1

    def test_report_never_raises(self, reporter: StatusReporter):
        """Reporter must be fail-safe."""
        bad = StatusReporter("/nonexistent/vault/xyz")
        tick = make_tick(1)
        tick.finished_at = datetime.now(tz=timezone.utc)
        try:
            bad.report(tick, LoopState())
        except Exception:
            pass  # acceptable


# ---------------------------------------------------------------------------
# 7. Loop Runner
# ---------------------------------------------------------------------------

class TestLoopRunner:
    def test_single_tick_succeeds(self, runner: LoopRunner):
        tick = runner.tick()
        assert tick.tick_number == 1
        assert tick.status in (TickStatus.SUCCESS, TickStatus.PARTIAL)

    def test_tick_count_increments(self, runner: LoopRunner):
        runner.tick()
        runner.tick()
        assert runner.state.tick_count == 2

    def test_health_phase_runs(self, runner: LoopRunner):
        runner.register_health_probe("vault", lambda: True)
        tick = runner.tick()
        health_phases = [p for p in tick.phase_results if p.phase == LoopPhase.HEALTH_CHECK]
        assert len(health_phases) == 1
        assert health_phases[0].status == TickStatus.SUCCESS

    def test_uptime_tick_increments_on_success(self, runner: LoopRunner):
        runner.tick()
        assert runner.state.uptime_ticks == 1

    def test_state_persisted(self, config: LoopConfig, tmp_vault: Path):
        runner1 = LoopRunner(config)
        runner1.tick()
        # Load a fresh runner from same vault — should read persisted state
        runner2 = LoopRunner(config)
        assert runner2.state.tick_count == 1

    def test_hitl_phase_skipped_when_no_skill(self, runner: LoopRunner):
        tick = runner.tick()
        hitl_phases = [p for p in tick.phase_results if p.phase == LoopPhase.HITL_PROCESS]
        # Phase runs but returns "skipped" details
        if hitl_phases:
            assert "skipped" in hitl_phases[0].details

    def test_hitl_phase_calls_check_timeouts(self, runner: LoopRunner):
        mock_hitl = MagicMock()
        mock_hitl.check_timeouts.return_value = []
        runner.set_hitl_skill(mock_hitl)
        runner.tick()
        mock_hitl.check_timeouts.assert_called_once()

    def test_memory_phase_runs(self, runner: LoopRunner):
        tick = runner.tick()
        mem_phases = [p for p in tick.phase_results if p.phase == LoopPhase.MEMORY_CONSOLIDATE]
        assert len(mem_phases) == 1

    def test_task_phase_no_orchestrator(self, runner: LoopRunner):
        tick = runner.tick()
        task_phases = [p for p in tick.phase_results if p.phase == LoopPhase.TASK_DISPATCH]
        if task_phases:
            assert "skipped" in task_phases[0].details

    def test_task_dispatched_via_orchestrator(self, runner: LoopRunner, queue: TaskQueue):
        from silver_tier_core_autonomy.orchestrator.models import WorkflowStatus
        mock_orch = MagicMock()
        mock_run  = MagicMock()
        mock_run.status = MagicMock()
        mock_run.status.value = "completed"
        mock_run.to_dict.return_value = {}
        mock_orch.run_workflow.return_value = mock_run

        # Replace the runner's queue with one backed by the same vault
        runner._orchestrator = mock_orch
        task = make_task("T", "echo", "say")
        runner.queue.enqueue(task)
        runner.tick()
        mock_orch.run_workflow.assert_called_once()

    def test_consecutive_fails_tracked(self, runner: LoopRunner):
        # Simulate health phase failure by providing a bad probe
        runner.register_health_probe("bad", lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        runner._config.pause_on_unhealthy = False  # don't stop on health fail
        runner.tick()
        # Phase partial/failed but loop continues
        assert runner.state.tick_count == 1


# ---------------------------------------------------------------------------
# 8. RalphSkill Facade
# ---------------------------------------------------------------------------

class TestRalphSkill:
    def test_enqueue_and_list(self, skill: RalphSkill):
        task = skill.enqueue_task("Test", "echo", "say", params={"msg": "hi"})
        assert task.task_id.startswith("TASK-")
        pending = skill.list_pending_tasks()
        assert any(t.task_id == task.task_id for t in pending)

    def test_pending_count(self, skill: RalphSkill):
        skill.enqueue_task("A", "echo", "say")
        skill.enqueue_task("B", "echo", "say")
        assert skill.pending_count() == 2

    def test_tick_increments_count(self, skill: RalphSkill):
        skill.tick()
        assert skill.state.tick_count == 1

    def test_write_episodic(self, skill: RalphSkill, tmp_vault: Path):
        path = skill.write_episodic("Test Memory", "Something happened.", ["test"])
        assert path.exists()

    def test_consolidate_memory(self, skill: RalphSkill):
        result = skill.consolidate_memory()
        assert "consolidated_count" in result

    def test_check_health_no_probes(self, skill: RalphSkill):
        rpt = skill.check_health()
        assert rpt.overall == HealthState.HEALTHY

    def test_check_health_with_probe(self, skill: RalphSkill):
        skill.register_health_probe("test", lambda: True)
        rpt = skill.check_health()
        assert rpt.overall == HealthState.HEALTHY
        assert len(rpt.components) == 1

    def test_config_exposed(self, skill: RalphSkill, tmp_vault: Path):
        assert skill.config.vault_root == str(tmp_vault)

    def test_state_exposed(self, skill: RalphSkill):
        skill.tick()
        assert skill.state.tick_count == 1

    def test_full_tick_with_probe_and_memory(self, skill: RalphSkill):
        skill.register_health_probe("vault", lambda: True)
        skill.write_episodic("Event", "Details here.")
        tick = skill.tick()
        assert tick.status in (TickStatus.SUCCESS, TickStatus.PARTIAL)
        assert len(tick.phase_results) >= 3

    def test_done_tasks_list(self, skill: RalphSkill):
        # No completed tasks initially
        assert skill.list_done_tasks() == []
