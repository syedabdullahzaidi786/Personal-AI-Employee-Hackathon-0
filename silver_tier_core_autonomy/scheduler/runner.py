"""
Scheduler — Runner.

Time-based job dispatcher. Uses wall-clock tracking (no external
dependency needed — pure stdlib). Compatible with cron/Task Scheduler
when this process is launched externally.

Constitution compliance:
  - Principle II: Explicit Over Implicit   (every job execution logged)
  - Principle IV: Composability            (any callable is a valid job)
  - Principle VI: Fail Safe                (job exceptions never crash the scheduler)
"""

from __future__ import annotations

import signal
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from .logger import SchedulerLogger
from .models import JobConfig, JobResult, JobStatus, SchedulerState
from .registry import JobRegistry


class SchedulerRunner:
    """
    Runs registered jobs based on their configured intervals.

    How it works
    ------------
    - Tracks `last_run_at` per job (in memory).
    - On each ``tick()``, checks all enabled jobs to see if their
      interval has elapsed since last run.
    - Jobs are executed synchronously in the order they are registered.
    - Failures are caught and logged; the scheduler continues.

    Usage::

        runner = SchedulerRunner(registry, vault_root="/path/to/vault")
        runner.run_forever(tick_interval_secs=10)
    """

    def __init__(
        self,
        registry: JobRegistry,
        vault_root: str | Path = ".",
        tick_interval_secs: float = 10.0,
    ) -> None:
        self._registry  = registry
        self._logger    = SchedulerLogger(vault_root)
        self._state     = SchedulerState()
        self._tick_secs = tick_interval_secs
        self._last_run: dict[str, float] = {}   # job_id → monotonic time of last run

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def tick(self) -> list[JobResult]:
        """
        Execute one scheduler tick.

        Runs all enabled jobs whose interval has elapsed.
        Returns list of JobResults for jobs that ran this tick.
        Never raises.
        """
        now = time.monotonic()
        self._state.last_tick_at = datetime.now(tz=timezone.utc)

        due_jobs = [
            job for job in self._registry.enabled_jobs()
            if self._is_due(job, now)
        ]

        results: list[JobResult] = []
        for job in due_jobs:
            result = self._run_job(job)
            results.append(result)
            self._last_run[job.job_id] = now
            self._state.record_run(job.job_id, result.status == JobStatus.SUCCESS)

        self._logger.log_tick(jobs_due=len(due_jobs), jobs_run=len(results))
        return results

    def run_forever(self, on_tick: Optional[Callable[[list[JobResult]], None]] = None) -> None:
        """
        Block and run tick() in a loop until SIGINT/SIGTERM.

        Parameters
        ----------
        on_tick:
            Optional callback called after each tick with the list of results.
        """
        self._state.running = True
        self._logger.info("Scheduler started", {"jobs": len(self._registry)})

        def _stop(signum, frame):
            self._state.running = False

        signal.signal(signal.SIGINT,  _stop)
        signal.signal(signal.SIGTERM, _stop)

        while self._state.running:
            results = self.tick()
            if on_tick:
                try:
                    on_tick(results)
                except Exception:  # noqa: BLE001
                    pass
            time.sleep(self._tick_secs)

        self._logger.info(
            "Scheduler stopped",
            {
                "total_runs":     self._state.total_runs,
                "total_failures": self._state.total_failures,
            },
        )

    def force_run(self, job_id: str) -> JobResult:
        """
        Immediately run a specific job regardless of schedule.
        Useful for testing and manual triggers.
        """
        job = self._registry.get(job_id)
        if job is None:
            result = JobResult(job_id=job_id, status=JobStatus.FAILED)
            result.error = f"Job '{job_id}' not found"
            return result
        result = self._run_job(job)
        self._last_run[job_id] = time.monotonic()
        self._state.record_run(job_id, result.status == JobStatus.SUCCESS)
        return result

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> SchedulerState:
        return self._state

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_due(self, job: JobConfig, now: float) -> bool:
        """Return True if the job should run on this tick."""
        last = self._last_run.get(job.job_id)
        if last is None:
            return True  # Never run — run immediately
        return (now - last) >= job.interval_seconds()

    def _run_job(self, job: JobConfig) -> JobResult:
        """Execute job.fn with retry logic. Never raises."""
        result = JobResult(job_id=job.job_id)
        result.started_at = datetime.now(tz=timezone.utc)

        self._logger.log_job_started(job.job_id, job.name)

        last_error: Optional[str] = None
        for attempt in range(1, job.max_retries + 1):
            result.attempt = attempt
            try:
                output = job.fn(**job.kwargs)
                result.output     = output
                result.status     = JobStatus.SUCCESS
                result.finished_at = datetime.now(tz=timezone.utc)
                self._logger.log_job_finished(
                    job.job_id, result.status.value, result.duration_ms
                )
                return result
            except Exception as exc:  # noqa: BLE001
                last_error = f"{type(exc).__name__}: {exc}"
                self._logger.log_job_failed(job.job_id, last_error, attempt)
                if attempt < job.max_retries:
                    time.sleep(min(2 ** attempt, 30))  # exponential backoff, max 30s

        result.status     = JobStatus.FAILED
        result.error      = last_error
        result.finished_at = datetime.now(tz=timezone.utc)
        self._logger.log_job_finished(
            job.job_id, result.status.value, result.duration_ms
        )
        return result
