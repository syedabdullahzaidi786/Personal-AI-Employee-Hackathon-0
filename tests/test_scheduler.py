"""
Unit tests for Silver Tier — Basic Scheduler.
Covers: models, registry, runner, logger.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from silver_tier_core_autonomy.scheduler.models import (
    IntervalUnit,
    JobConfig,
    JobResult,
    JobStatus,
    SchedulerState,
)
from silver_tier_core_autonomy.scheduler.registry import JobRegistry, RegistrationError
from silver_tier_core_autonomy.scheduler.runner import SchedulerRunner
from silver_tier_core_autonomy.scheduler.logger import SchedulerLogger


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    return tmp_path


def _noop(**kwargs) -> str:
    return "ok"


def _failing(**kwargs) -> None:
    raise RuntimeError("job error")


def _make_job(job_id="test-job", interval=5, unit=IntervalUnit.MINUTES, fn=None) -> JobConfig:
    return JobConfig(
        job_id=job_id,
        name=f"Test Job {job_id}",
        fn=fn or _noop,
        interval=interval,
        unit=unit,
    )


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestJobConfig:
    def test_interval_seconds_minutes(self):
        job = _make_job(interval=5, unit=IntervalUnit.MINUTES)
        assert job.interval_seconds() == 300.0

    def test_interval_seconds_hours(self):
        job = _make_job(interval=1, unit=IntervalUnit.HOURS)
        assert job.interval_seconds() == 3600.0

    def test_interval_seconds_seconds(self):
        job = _make_job(interval=30, unit=IntervalUnit.SECONDS)
        assert job.interval_seconds() == 30.0

    def test_enabled_by_default(self):
        job = _make_job()
        assert job.enabled is True

    def test_max_retries_default(self):
        job = _make_job()
        assert job.max_retries == 3


class TestJobResult:
    def test_default_status_pending(self):
        result = JobResult(job_id="j1")
        assert result.status == JobStatus.PENDING

    def test_duration_ms_zero_when_no_timestamps(self):
        result = JobResult(job_id="j1")
        assert result.duration_ms == 0.0

    def test_to_dict_keys(self):
        result = JobResult(job_id="j1", status=JobStatus.SUCCESS)
        d = result.to_dict()
        assert "job_id" in d
        assert "status" in d
        assert "duration_ms" in d


class TestSchedulerState:
    def test_record_run_increments_total(self):
        state = SchedulerState()
        state.record_run("job1", success=True)
        assert state.total_runs == 1
        assert state.total_failures == 0

    def test_record_run_failure(self):
        state = SchedulerState()
        state.record_run("job1", success=False)
        assert state.total_failures == 1

    def test_job_run_counts_tracked(self):
        state = SchedulerState()
        state.record_run("job1", True)
        state.record_run("job1", True)
        assert state.job_run_counts["job1"] == 2

    def test_to_dict(self):
        state = SchedulerState()
        d = state.to_dict()
        assert "total_runs" in d
        assert "running" in d


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------

class TestJobRegistry:
    def test_register_and_get(self):
        reg = JobRegistry()
        job = _make_job("j1")
        reg.register(job)
        assert reg.get("j1") is job

    def test_register_duplicate_raises(self):
        reg = JobRegistry()
        reg.register(_make_job("j1"))
        with pytest.raises(RegistrationError):
            reg.register(_make_job("j1"))

    def test_register_zero_interval_raises(self):
        reg = JobRegistry()
        with pytest.raises(RegistrationError):
            reg.register(_make_job(interval=0))

    def test_unregister_removes_job(self):
        reg = JobRegistry()
        reg.register(_make_job("j1"))
        reg.unregister("j1")
        assert reg.get("j1") is None

    def test_unregister_nonexistent_noop(self):
        reg = JobRegistry()
        reg.unregister("nonexistent")  # should not raise

    def test_disable_excludes_from_enabled(self):
        reg = JobRegistry()
        reg.register(_make_job("j1"))
        reg.disable("j1")
        assert len(reg.enabled_jobs()) == 0

    def test_enable_restores_job(self):
        reg = JobRegistry()
        reg.register(_make_job("j1"))
        reg.disable("j1")
        reg.enable("j1")
        assert len(reg.enabled_jobs()) == 1

    def test_all_jobs_returns_all(self):
        reg = JobRegistry()
        reg.register(_make_job("j1"))
        reg.register(_make_job("j2"))
        assert len(reg.all_jobs()) == 2

    def test_len(self):
        reg = JobRegistry()
        reg.register(_make_job("j1"))
        assert len(reg) == 1

    def test_contains(self):
        reg = JobRegistry()
        reg.register(_make_job("j1"))
        assert "j1" in reg
        assert "j2" not in reg

    def test_enabled_jobs_only_enabled(self):
        reg = JobRegistry()
        reg.register(_make_job("j1"))
        reg.register(_make_job("j2"))
        reg.disable("j1")
        assert len(reg.enabled_jobs()) == 1


# ---------------------------------------------------------------------------
# Runner tests
# ---------------------------------------------------------------------------

class TestSchedulerRunner:
    def test_tick_runs_due_jobs(self, tmp_vault):
        reg = JobRegistry()
        mock_fn = MagicMock(return_value="done")
        reg.register(JobConfig(
            job_id="j1", name="J1", fn=mock_fn,
            interval=1, unit=IntervalUnit.SECONDS,
        ))
        runner = SchedulerRunner(reg, tmp_vault)
        results = runner.tick()
        assert len(results) == 1
        mock_fn.assert_called_once()

    def test_tick_first_run_always_executes(self, tmp_vault):
        reg = JobRegistry()
        called = []
        def fn(): called.append(1)
        reg.register(JobConfig(
            job_id="j1", name="J1", fn=fn,
            interval=999, unit=IntervalUnit.HOURS,
        ))
        runner = SchedulerRunner(reg, tmp_vault)
        runner.tick()
        assert len(called) == 1

    def test_tick_respects_interval(self, tmp_vault):
        reg = JobRegistry()
        mock_fn = MagicMock(return_value="ok")
        reg.register(JobConfig(
            job_id="j1", name="J1", fn=mock_fn,
            interval=9999, unit=IntervalUnit.SECONDS,
        ))
        runner = SchedulerRunner(reg, tmp_vault)
        runner.tick()   # first tick — runs
        runner.tick()   # second tick — interval not elapsed, should NOT run
        assert mock_fn.call_count == 1

    def test_job_failure_returns_failed_result(self, tmp_vault):
        reg = JobRegistry()
        reg.register(JobConfig(
            job_id="bad", name="Bad", fn=_failing,
            interval=1, unit=IntervalUnit.SECONDS,
            max_retries=1,
        ))
        runner = SchedulerRunner(reg, tmp_vault)
        results = runner.tick()
        assert results[0].status == JobStatus.FAILED
        assert "job error" in results[0].error

    def test_job_failure_does_not_crash_scheduler(self, tmp_vault):
        reg = JobRegistry()
        reg.register(JobConfig(
            job_id="bad", name="Bad", fn=_failing,
            interval=1, unit=IntervalUnit.SECONDS,
            max_retries=1,
        ))
        reg.register(JobConfig(
            job_id="good", name="Good", fn=_noop,
            interval=1, unit=IntervalUnit.SECONDS,
        ))
        runner = SchedulerRunner(reg, tmp_vault)
        results = runner.tick()
        statuses = {r.job_id: r.status for r in results}
        assert statuses["bad"] == JobStatus.FAILED
        assert statuses["good"] == JobStatus.SUCCESS

    def test_disabled_job_not_run(self, tmp_vault):
        reg = JobRegistry()
        mock_fn = MagicMock(return_value="ok")
        reg.register(JobConfig(
            job_id="j1", name="J1", fn=mock_fn,
            interval=1, unit=IntervalUnit.SECONDS,
        ))
        reg.disable("j1")
        runner = SchedulerRunner(reg, tmp_vault)
        results = runner.tick()
        assert len(results) == 0
        mock_fn.assert_not_called()

    def test_force_run_executes_immediately(self, tmp_vault):
        reg = JobRegistry()
        mock_fn = MagicMock(return_value="forced")
        reg.register(JobConfig(
            job_id="j1", name="J1", fn=mock_fn,
            interval=9999, unit=IntervalUnit.HOURS,
        ))
        runner = SchedulerRunner(reg, tmp_vault)
        runner.tick()         # first run
        result = runner.force_run("j1")  # force second run
        assert result.status == JobStatus.SUCCESS
        assert mock_fn.call_count == 2

    def test_force_run_unknown_job_returns_failed(self, tmp_vault):
        reg = JobRegistry()
        runner = SchedulerRunner(reg, tmp_vault)
        result = runner.force_run("nonexistent")
        assert result.status == JobStatus.FAILED
        assert "not found" in result.error

    def test_state_tracks_total_runs(self, tmp_vault):
        reg = JobRegistry()
        reg.register(JobConfig(
            job_id="j1", name="J1", fn=_noop,
            interval=1, unit=IntervalUnit.SECONDS,
        ))
        runner = SchedulerRunner(reg, tmp_vault)
        runner.tick()
        assert runner.state.total_runs == 1

    def test_state_tracks_failures(self, tmp_vault):
        reg = JobRegistry()
        reg.register(JobConfig(
            job_id="bad", name="Bad", fn=_failing,
            interval=1, unit=IntervalUnit.SECONDS,
            max_retries=1,
        ))
        runner = SchedulerRunner(reg, tmp_vault)
        runner.tick()
        assert runner.state.total_failures == 1

    def test_kwargs_passed_to_fn(self, tmp_vault):
        reg = JobRegistry()
        received = {}

        def fn(key=None):
            received["key"] = key
            return key

        reg.register(JobConfig(
            job_id="j1", name="J1", fn=fn,
            interval=1, unit=IntervalUnit.SECONDS,
            kwargs={"key": "value123"},
        ))
        runner = SchedulerRunner(reg, tmp_vault)
        runner.tick()
        assert received["key"] == "value123"

    def test_empty_registry_tick_returns_empty(self, tmp_vault):
        reg = JobRegistry()
        runner = SchedulerRunner(reg, tmp_vault)
        results = runner.tick()
        assert results == []


# ---------------------------------------------------------------------------
# Logger tests
# ---------------------------------------------------------------------------

class TestSchedulerLogger:
    def test_log_creates_file(self, tmp_vault):
        logger = SchedulerLogger(tmp_vault)
        logger.info("test")
        files = list((tmp_vault / "70-LOGS" / "scheduler").glob("*.jsonl"))
        assert len(files) == 1

    def test_log_entry_valid_json(self, tmp_vault):
        logger = SchedulerLogger(tmp_vault)
        logger.log_job_started("j1", "My Job")
        log_file = list((tmp_vault / "70-LOGS" / "scheduler").glob("*.jsonl"))[0]
        entry = json.loads(log_file.read_text().strip())
        assert entry["level"] == "INFO"
        assert "j1" in entry["context"].get("job_id", "")

    def test_error_level_logged(self, tmp_vault):
        logger = SchedulerLogger(tmp_vault)
        logger.log_job_failed("j1", "something broke", 2)
        log_file = list((tmp_vault / "70-LOGS" / "scheduler").glob("*.jsonl"))[0]
        content = log_file.read_text()
        assert "ERROR" in content
        assert "j1" in content
