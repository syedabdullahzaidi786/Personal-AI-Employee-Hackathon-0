"""
Scheduler — Job Registry.

Stores and manages scheduled job configurations.

Constitution compliance:
  - Principle IV: Composability — any callable can be registered
  - Principle VI: Fail Safe — duplicate/missing IDs are rejected cleanly
"""

from __future__ import annotations

from typing import Optional

from .models import IntervalUnit, JobConfig


class RegistrationError(Exception):
    """Raised when a job cannot be registered."""


class JobRegistry:
    """
    Registry of scheduled jobs.

    Usage::

        registry = JobRegistry()
        registry.register(JobConfig(
            job_id="gmail-watcher",
            name="Gmail Watcher",
            fn=my_watcher.run,
            interval=5,
            unit=IntervalUnit.MINUTES,
        ))
        job = registry.get("gmail-watcher")
    """

    def __init__(self) -> None:
        self._jobs: dict[str, JobConfig] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, config: JobConfig) -> None:
        """
        Register a new job.

        Raises :exc:`RegistrationError` if *job_id* is already registered.
        """
        if config.job_id in self._jobs:
            raise RegistrationError(f"Job '{config.job_id}' is already registered")
        if config.interval <= 0:
            raise RegistrationError(f"Job '{config.job_id}': interval must be > 0")
        self._jobs[config.job_id] = config

    def unregister(self, job_id: str) -> None:
        """Remove a job from the registry (no-op if not found)."""
        self._jobs.pop(job_id, None)

    def enable(self, job_id: str) -> None:
        """Enable a disabled job."""
        job = self._require(job_id)
        job.enabled = True

    def disable(self, job_id: str) -> None:
        """Disable a job without removing it."""
        job = self._require(job_id)
        job.enabled = False

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get(self, job_id: str) -> Optional[JobConfig]:
        return self._jobs.get(job_id)

    def all_jobs(self) -> list[JobConfig]:
        return list(self._jobs.values())

    def enabled_jobs(self) -> list[JobConfig]:
        return [j for j in self._jobs.values() if j.enabled]

    def __len__(self) -> int:
        return len(self._jobs)

    def __contains__(self, job_id: str) -> bool:
        return job_id in self._jobs

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _require(self, job_id: str) -> JobConfig:
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(f"Job '{job_id}' not found in registry")
        return job
