"""
RALPH_WIGGUM_LOOP_SKILL — Data Models
Phase 1: Loop configuration, tick results, health status, task entries.

Constitution compliance:
  - Principle II: Explicit Over Implicit  (all state declared, logged)
  - Principle V:  Memory as Knowledge     (tick history persisted)
  - Principle VI: Fail Safe               (health status drives loop behaviour)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class LoopPhase(str, Enum):
    """Named phases within a single tick."""
    HEALTH_CHECK    = "health_check"
    HITL_PROCESS    = "hitl_process"
    TASK_DISPATCH   = "task_dispatch"
    MEMORY_CONSOLIDATE = "memory_consolidate"
    STATUS_REPORT   = "status_report"


class TickStatus(str, Enum):
    SUCCESS  = "success"
    PARTIAL  = "partial"    # Some phases failed but loop continues
    FAILED   = "failed"     # Critical failure; loop should pause
    SKIPPED  = "skipped"    # Tick skipped (still within min_interval)


class HealthState(str, Enum):
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"  # Responding but with errors
    UNHEALTHY = "unhealthy" # Not responding or critical errors
    UNKNOWN   = "unknown"   # Never checked yet


class TaskStatus(str, Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    DONE       = "done"
    FAILED     = "failed"


class TaskPriority(int, Enum):
    LOW    = 3
    NORMAL = 2
    HIGH   = 1
    URGENT = 0


# ---------------------------------------------------------------------------
# Loop Configuration
# ---------------------------------------------------------------------------

@dataclass
class LoopConfig:
    """Runtime configuration for the RalphRunner."""
    vault_root:          str
    tick_interval_secs:  int   = 300    # 5 minutes between ticks
    min_interval_secs:   int   = 60     # Never tick faster than this
    max_consecutive_fails: int = 3      # After N fails, pause loop
    pause_on_unhealthy:  bool  = True   # Pause loop if system unhealthy
    enable_health_check: bool  = True
    enable_hitl_process: bool  = True
    enable_task_dispatch: bool = True
    enable_memory_consolidate: bool = True
    enable_status_report: bool = True
    agent_id:            str   = "ralph"

    def to_dict(self) -> dict:
        return {
            "vault_root":              self.vault_root,
            "tick_interval_secs":      self.tick_interval_secs,
            "min_interval_secs":       self.min_interval_secs,
            "max_consecutive_fails":   self.max_consecutive_fails,
            "pause_on_unhealthy":      self.pause_on_unhealthy,
            "enable_health_check":     self.enable_health_check,
            "enable_hitl_process":     self.enable_hitl_process,
            "enable_task_dispatch":    self.enable_task_dispatch,
            "enable_memory_consolidate": self.enable_memory_consolidate,
            "enable_status_report":    self.enable_status_report,
            "agent_id":                self.agent_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "LoopConfig":
        return cls(
            vault_root=d["vault_root"],
            tick_interval_secs=d.get("tick_interval_secs", 300),
            min_interval_secs=d.get("min_interval_secs", 60),
            max_consecutive_fails=d.get("max_consecutive_fails", 3),
            pause_on_unhealthy=d.get("pause_on_unhealthy", True),
            enable_health_check=d.get("enable_health_check", True),
            enable_hitl_process=d.get("enable_hitl_process", True),
            enable_task_dispatch=d.get("enable_task_dispatch", True),
            enable_memory_consolidate=d.get("enable_memory_consolidate", True),
            enable_status_report=d.get("enable_status_report", True),
            agent_id=d.get("agent_id", "ralph"),
        )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@dataclass
class ComponentHealth:
    """Health status for a single registered component."""
    name:       str
    state:      HealthState = HealthState.UNKNOWN
    last_check: Optional[datetime] = None
    message:    str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name":       self.name,
            "state":      self.state.value,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "message":    self.message,
            "latency_ms": round(self.latency_ms, 2),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ComponentHealth":
        obj = cls(name=d["name"], state=HealthState(d.get("state", "unknown")),
                  message=d.get("message", ""), latency_ms=d.get("latency_ms", 0.0))
        if d.get("last_check"):
            obj.last_check = datetime.fromisoformat(d["last_check"])
        return obj


@dataclass
class HealthReport:
    """Aggregated health of all registered components."""
    checked_at: datetime
    components: list[ComponentHealth] = field(default_factory=list)
    overall:    HealthState = HealthState.UNKNOWN

    @property
    def healthy_count(self) -> int:
        return sum(1 for c in self.components if c.state == HealthState.HEALTHY)

    @property
    def unhealthy_count(self) -> int:
        return sum(1 for c in self.components if c.state == HealthState.UNHEALTHY)

    def to_dict(self) -> dict:
        return {
            "checked_at":     self.checked_at.isoformat(),
            "overall":        self.overall.value,
            "healthy_count":  self.healthy_count,
            "unhealthy_count": self.unhealthy_count,
            "components":     [c.to_dict() for c in self.components],
        }


# ---------------------------------------------------------------------------
# Phase Result
# ---------------------------------------------------------------------------

@dataclass
class PhaseResult:
    """Result of executing one loop phase within a tick."""
    phase:      LoopPhase
    status:     TickStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    details:    dict[str, Any] = field(default_factory=dict)
    error:      Optional[str] = None

    @property
    def duration_ms(self) -> float:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds() * 1000
        return 0.0

    def to_dict(self) -> dict:
        return {
            "phase":       self.phase.value,
            "status":      self.status.value,
            "started_at":  self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": round(self.duration_ms, 2),
            "details":     self.details,
            "error":       self.error,
        }


# ---------------------------------------------------------------------------
# Tick Result
# ---------------------------------------------------------------------------

@dataclass
class TickResult:
    """Complete result of one loop tick."""
    tick_id:     str
    tick_number: int
    status:      TickStatus
    started_at:  datetime
    finished_at: Optional[datetime] = None
    phase_results: list[PhaseResult] = field(default_factory=list)
    health:      Optional[HealthReport] = None

    @property
    def duration_ms(self) -> float:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds() * 1000
        return 0.0

    def to_dict(self) -> dict:
        return {
            "tick_id":      self.tick_id,
            "tick_number":  self.tick_number,
            "status":       self.status.value,
            "started_at":   self.started_at.isoformat(),
            "finished_at":  self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms":  round(self.duration_ms, 2),
            "phase_results": [p.to_dict() for p in self.phase_results],
            "health":       self.health.to_dict() if self.health else None,
        }


# ---------------------------------------------------------------------------
# Task Entry (task queue)
# ---------------------------------------------------------------------------

@dataclass
class TaskEntry:
    """A single task waiting in the loop's task queue."""
    task_id:     str
    title:       str
    skill_name:  str
    operation:   str
    params:      dict[str, Any] = field(default_factory=dict)
    priority:    TaskPriority = TaskPriority.NORMAL
    status:      TaskStatus = TaskStatus.PENDING
    submitted_at: Optional[datetime] = None
    started_at:  Optional[datetime] = None
    finished_at: Optional[datetime] = None
    submitted_by: str = "operator"
    error:       Optional[str] = None
    result:      Optional[dict[str, Any]] = None

    def to_dict(self) -> dict:
        return {
            "task_id":      self.task_id,
            "title":        self.title,
            "skill_name":   self.skill_name,
            "operation":    self.operation,
            "params":       self.params,
            "priority":     self.priority.value,
            "status":       self.status.value,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "started_at":   self.started_at.isoformat() if self.started_at else None,
            "finished_at":  self.finished_at.isoformat() if self.finished_at else None,
            "submitted_by": self.submitted_by,
            "error":        self.error,
            "result":       self.result,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TaskEntry":
        entry = cls(
            task_id=d["task_id"],
            title=d.get("title", ""),
            skill_name=d["skill_name"],
            operation=d["operation"],
            params=d.get("params", {}),
            priority=TaskPriority(d.get("priority", 2)),
            status=TaskStatus(d.get("status", "pending")),
            submitted_by=d.get("submitted_by", "operator"),
            error=d.get("error"),
            result=d.get("result"),
        )
        for attr in ("submitted_at", "started_at", "finished_at"):
            if d.get(attr):
                setattr(entry, attr, datetime.fromisoformat(d[attr]))
        return entry


# ---------------------------------------------------------------------------
# Loop State  (persisted across restarts)
# ---------------------------------------------------------------------------

@dataclass
class LoopState:
    """Persistent state of the Ralph loop, saved after each tick."""
    agent_id:          str = "ralph"
    tick_count:        int = 0
    consecutive_fails: int = 0
    last_tick_at:      Optional[datetime] = None
    last_tick_status:  Optional[TickStatus] = None
    started_at:        Optional[datetime] = None
    uptime_ticks:      int = 0       # successful ticks
    total_tasks_done:  int = 0

    def to_dict(self) -> dict:
        return {
            "agent_id":          self.agent_id,
            "tick_count":        self.tick_count,
            "consecutive_fails": self.consecutive_fails,
            "last_tick_at":      self.last_tick_at.isoformat() if self.last_tick_at else None,
            "last_tick_status":  self.last_tick_status.value if self.last_tick_status else None,
            "started_at":        self.started_at.isoformat() if self.started_at else None,
            "uptime_ticks":      self.uptime_ticks,
            "total_tasks_done":  self.total_tasks_done,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "LoopState":
        state = cls(
            agent_id=d.get("agent_id", "ralph"),
            tick_count=d.get("tick_count", 0),
            consecutive_fails=d.get("consecutive_fails", 0),
            uptime_ticks=d.get("uptime_ticks", 0),
            total_tasks_done=d.get("total_tasks_done", 0),
        )
        for attr in ("last_tick_at", "started_at"):
            if d.get(attr):
                setattr(state, attr, datetime.fromisoformat(d[attr]))
        if d.get("last_tick_status"):
            state.last_tick_status = TickStatus(d["last_tick_status"])
        return state


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def make_tick(tick_number: int) -> TickResult:
    return TickResult(
        tick_id=f"TICK-{uuid.uuid4().hex[:8].upper()}",
        tick_number=tick_number,
        status=TickStatus.SUCCESS,
        started_at=datetime.now(tz=timezone.utc),
    )


def make_task(
    title: str,
    skill_name: str,
    operation: str,
    params: Optional[dict] = None,
    priority: TaskPriority = TaskPriority.NORMAL,
    submitted_by: str = "operator",
) -> TaskEntry:
    return TaskEntry(
        task_id=f"TASK-{uuid.uuid4().hex[:8].upper()}",
        title=title,
        skill_name=skill_name,
        operation=operation,
        params=params or {},
        priority=priority,
        submitted_by=submitted_by,
        submitted_at=datetime.now(tz=timezone.utc),
    )
