"""
Scheduler — Data Models.

Constitution compliance:
  - Principle II: Explicit Over Implicit
  - Principle IV: Composability Through Standards
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional


class IntervalUnit(str, Enum):
    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS   = "hours"


class JobStatus(str, Enum):
    PENDING  = "pending"
    RUNNING  = "running"
    SUCCESS  = "success"
    FAILED   = "failed"
    DISABLED = "disabled"


@dataclass
class JobConfig:
    """Configuration for one scheduled job."""
    job_id: str
    name: str
    fn: Callable[..., Any]
    interval: int                        # How often to run
    unit: IntervalUnit = IntervalUnit.MINUTES
    kwargs: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    max_retries: int = 3
    tags: list[str] = field(default_factory=list)

    def interval_seconds(self) -> float:
        if self.unit == IntervalUnit.SECONDS:
            return float(self.interval)
        if self.unit == IntervalUnit.MINUTES:
            return float(self.interval * 60)
        return float(self.interval * 3600)


@dataclass
class JobResult:
    """Result of one job execution."""
    job_id: str
    run_id: str = field(default_factory=lambda: f"JR-{uuid.uuid4().hex[:8]}")
    status: JobStatus = JobStatus.PENDING
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    output: Any = None
    error: Optional[str] = None
    attempt: int = 1

    @property
    def duration_ms(self) -> float:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds() * 1000
        return 0.0

    def to_dict(self) -> dict:
        return {
            "job_id":      self.job_id,
            "run_id":      self.run_id,
            "status":      self.status.value,
            "started_at":  self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": round(self.duration_ms, 2),
            "error":       self.error,
            "attempt":     self.attempt,
        }


@dataclass
class SchedulerState:
    """Runtime state of the scheduler."""
    total_runs: int = 0
    total_failures: int = 0
    last_tick_at: Optional[datetime] = None
    running: bool = False
    job_run_counts: dict[str, int] = field(default_factory=dict)
    job_fail_counts: dict[str, int] = field(default_factory=dict)

    def record_run(self, job_id: str, success: bool) -> None:
        self.total_runs += 1
        self.job_run_counts[job_id] = self.job_run_counts.get(job_id, 0) + 1
        if not success:
            self.total_failures += 1
            self.job_fail_counts[job_id] = self.job_fail_counts.get(job_id, 0) + 1

    def to_dict(self) -> dict:
        return {
            "total_runs":      self.total_runs,
            "total_failures":  self.total_failures,
            "last_tick_at":    self.last_tick_at.isoformat() if self.last_tick_at else None,
            "running":         self.running,
            "job_run_counts":  self.job_run_counts,
            "job_fail_counts": self.job_fail_counts,
        }
