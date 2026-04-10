"""Silver Tier — Basic Scheduler.

Registers and runs watchers + skills on a schedule.
Supports interval-based jobs (every N seconds/minutes/hours).

Constitution compliance:
  - Principle II: Explicit Over Implicit (all jobs declared upfront)
  - Principle IV: Composability (any callable can be scheduled)
  - Principle VI: Fail Safe (job failures isolated; scheduler continues)
"""

from .models import JobConfig, JobResult, JobStatus, SchedulerState
from .registry import JobRegistry
from .runner import SchedulerRunner

__all__ = [
    "JobConfig",
    "JobResult",
    "JobStatus",
    "SchedulerState",
    "JobRegistry",
    "SchedulerRunner",
]
