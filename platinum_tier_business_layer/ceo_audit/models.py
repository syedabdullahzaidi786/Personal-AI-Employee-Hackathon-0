"""
CEO_WEEKLY_AUDIT_SKILL — Data Models
Phase 1: ReportPeriod, KPI stats, and WeeklyReport.

Constitution compliance:
  - Section 9: Skill Design Rules (atomic, testable)
  - Read-only — no mutations of any system state
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Period helpers
# ---------------------------------------------------------------------------

def _iso_week_bounds(year: int, week: int) -> tuple[date, date]:
    """Return (monday, sunday) for the given ISO year/week."""
    # Jan 4 is always in ISO week 1
    jan4 = date(year, 1, 4)
    week1_monday = jan4 - timedelta(days=jan4.isoweekday() - 1)
    monday = week1_monday + timedelta(weeks=week - 1)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def current_week_period(offset: int = 0) -> "ReportPeriod":
    """
    Return the ReportPeriod for an ISO week relative to today.

    offset=0  → current ISO week
    offset=-1 → previous ISO week
    """
    today = date.today()
    iso = today.isocalendar()
    year: int = iso[0]
    week: int = iso[1] + offset

    # Handle year boundary (week underflow)
    while week < 1:
        year -= 1
        dec28 = date(year, 12, 28)  # always in the last ISO week of the year
        week += dec28.isocalendar()[1]

    # Handle year boundary (week overflow)
    while True:
        dec28 = date(year, 12, 28)
        max_week = dec28.isocalendar()[1]
        if week <= max_week:
            break
        week -= max_week
        year += 1

    start, end = _iso_week_bounds(year, week)
    return ReportPeriod(year=year, week_number=week, start_date=start, end_date=end)


# ---------------------------------------------------------------------------
# Report Period
# ---------------------------------------------------------------------------

@dataclass
class ReportPeriod:
    """An ISO calendar week (Monday–Sunday)."""
    year: int
    week_number: int
    start_date: date   # Monday
    end_date: date     # Sunday

    @property
    def label(self) -> str:
        return f"Week {self.week_number:02d}, {self.year}"

    @property
    def slug(self) -> str:
        return f"{self.year}-W{self.week_number:02d}"

    def contains(self, dt: datetime) -> bool:
        """Return True if the datetime falls within this week."""
        d = dt.date() if isinstance(dt, datetime) else dt
        return self.start_date <= d <= self.end_date

    def date_strings(self) -> list[str]:
        """Return YYYY-MM-DD strings for every day in the period (Mon–Sun)."""
        result = []
        current = self.start_date
        while current <= self.end_date:
            result.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        return result

    def to_dict(self) -> dict:
        return {
            "year": self.year,
            "week_number": self.week_number,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "label": self.label,
            "slug": self.slug,
        }


# ---------------------------------------------------------------------------
# KPI Stats
# ---------------------------------------------------------------------------

@dataclass
class HITLStats:
    """Aggregated HITL approval metrics for the period."""
    submitted: int = 0
    approved: int = 0
    auto_approved: int = 0
    denied: int = 0
    deferred: int = 0
    timeout: int = 0
    pending: int = 0

    @property
    def decided(self) -> int:
        return self.approved + self.auto_approved + self.denied + self.deferred + self.timeout

    @property
    def approval_rate(self) -> Optional[float]:
        """Fraction approved (human + auto) of all decided. None if no decisions."""
        if self.decided == 0:
            return None
        return round((self.approved + self.auto_approved) / self.decided, 3)

    def to_dict(self) -> dict:
        return {
            "submitted": self.submitted,
            "approved": self.approved,
            "auto_approved": self.auto_approved,
            "denied": self.denied,
            "deferred": self.deferred,
            "timeout": self.timeout,
            "pending": self.pending,
            "decided": self.decided,
            "approval_rate": self.approval_rate,
        }


@dataclass
class OrchestratorStats:
    """Aggregated orchestrator workflow metrics for the period."""
    runs_total: int = 0
    runs_success: int = 0
    runs_failed: int = 0
    steps_total: int = 0
    steps_failed: int = 0
    steps_skipped: int = 0
    hitl_gates: int = 0
    errors: int = 0

    @property
    def success_rate(self) -> Optional[float]:
        if self.runs_total == 0:
            return None
        return round(self.runs_success / self.runs_total, 3)

    def to_dict(self) -> dict:
        return {
            "runs_total": self.runs_total,
            "runs_success": self.runs_success,
            "runs_failed": self.runs_failed,
            "steps_total": self.steps_total,
            "steps_failed": self.steps_failed,
            "steps_skipped": self.steps_skipped,
            "hitl_gates": self.hitl_gates,
            "errors": self.errors,
            "success_rate": self.success_rate,
        }


@dataclass
class WatcherStats:
    """Per-watcher event/error metrics for the period."""
    watcher_id: str
    events: int = 0
    polls: int = 0
    errors: int = 0
    starts: int = 0

    def to_dict(self) -> dict:
        return {
            "watcher_id": self.watcher_id,
            "events": self.events,
            "polls": self.polls,
            "errors": self.errors,
            "starts": self.starts,
        }


@dataclass
class ActionStats:
    """Per-action-skill metrics for the period."""
    skill_name: str
    submitted: int = 0
    success: int = 0
    failed: int = 0
    denied: int = 0
    pending_approval: int = 0

    @property
    def success_rate(self) -> Optional[float]:
        settled = self.success + self.failed + self.denied
        if settled == 0:
            return None
        return round(self.success / settled, 3)

    def to_dict(self) -> dict:
        return {
            "skill_name": self.skill_name,
            "submitted": self.submitted,
            "success": self.success,
            "failed": self.failed,
            "denied": self.denied,
            "pending_approval": self.pending_approval,
            "success_rate": self.success_rate,
        }


# ---------------------------------------------------------------------------
# Overall health
# ---------------------------------------------------------------------------

class OverallHealth:
    HEALTHY  = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    UNKNOWN  = "UNKNOWN"


def compute_health(
    hitl: HITLStats,
    orch: OrchestratorStats,
    actions: list[ActionStats],
) -> str:
    """Compute an overall system health signal from aggregated stats."""
    # Critical thresholds
    if hitl.decided > 0 and hitl.denied / hitl.decided > 0.5:
        return OverallHealth.CRITICAL
    if orch.runs_total > 0 and orch.runs_failed / orch.runs_total > 0.5:
        return OverallHealth.CRITICAL
    # Degraded thresholds
    if hitl.denied > 0:
        return OverallHealth.DEGRADED
    if orch.runs_total > 0 and orch.runs_failed / orch.runs_total > 0.2:
        return OverallHealth.DEGRADED
    for a in actions:
        if a.denied > 0 or a.failed > 0:
            return OverallHealth.DEGRADED
    return OverallHealth.HEALTHY


# ---------------------------------------------------------------------------
# Weekly Report
# ---------------------------------------------------------------------------

@dataclass
class WeeklyReport:
    """Complete weekly audit report aggregated from all skill logs."""
    period: ReportPeriod
    generated_at: datetime
    hitl: HITLStats
    orchestrator: OrchestratorStats
    watchers: list[WatcherStats] = field(default_factory=list)
    actions: list[ActionStats] = field(default_factory=list)
    overall_health: str = OverallHealth.UNKNOWN

    def to_dict(self) -> dict:
        return {
            "period": self.period.to_dict(),
            "generated_at": self.generated_at.isoformat(),
            "overall_health": self.overall_health,
            "hitl": self.hitl.to_dict(),
            "orchestrator": self.orchestrator.to_dict(),
            "watchers": [w.to_dict() for w in self.watchers],
            "actions": [a.to_dict() for a in self.actions],
        }
