"""
CEO_WEEKLY_AUDIT_SKILL — Phase 1
Read-only analytics skill that aggregates weekly KPIs from all skill logs
and generates executive Markdown reports.

Constitution compliance:
  - Section 9: Skill Design Rules (atomic, composable, testable)
  - Tier 0: Read-only — no system mutations; no HITL required
  - Section 7: Logs own activity to 70-LOGS/business/
  - Section 8: Never reads credential values from vault

Supported operations:
  - generate_report   → collect metrics from logs for the period
  - save_report       → write Markdown to 50-BUSINESS/weekly/ and log to 70-LOGS/business/
  - generate_and_save → convenience: generate + save in one call

Public surface::

    from skills.business.ceo_audit import CeoAuditSkill

    skill = CeoAuditSkill(vault_root="/vault")

    # Current week
    report, paths = skill.generate_and_save()

    # Previous week
    report, paths = skill.generate_and_save(week_offset=-1)

    print(report.overall_health)
    print(report.hitl.approval_rate)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .collector import LogCollector
from .logger import AuditSkillLogger
from .models import (
    ActionStats,
    HITLStats,
    OrchestratorStats,
    OverallHealth,
    ReportPeriod,
    WeeklyReport,
    WatcherStats,
    compute_health,
    current_week_period,
)
from .reporter import ReportGenerator


class CeoAuditSkill:
    """
    High-level facade for CEO_WEEKLY_AUDIT_SKILL Phase 1.

    Composes: LogCollector + ReportGenerator + AuditSkillLogger.
    Read-only: never mutates Odoo, HITL, watchers, or action state.
    """

    _BUSINESS_DIR = "50-BUSINESS"
    _WEEKLY_SUBDIR = "weekly"

    def __init__(self, vault_root: str | Path) -> None:
        self._vault     = Path(vault_root)
        self._collector = LogCollector(vault_root)
        self._reporter  = ReportGenerator()
        self._logger    = AuditSkillLogger(vault_root)

    # ------------------------------------------------------------------
    # Main interface
    # ------------------------------------------------------------------

    def generate_report(self, week_offset: int = 0) -> WeeklyReport:
        """
        Collect and return a WeeklyReport for the target ISO week.

        week_offset=0  → current week
        week_offset=-1 → previous week
        """
        period = current_week_period(week_offset)
        return self._collector.collect_all(period)

    def save_report(self, report: WeeklyReport) -> dict[str, str]:
        """
        Persist the report to:
          - 50-BUSINESS/weekly/{slug}.md   (human-readable Markdown)
          - 70-LOGS/business/YYYY-MM-DD.jsonl  (machine audit entry)

        Returns a dict mapping keys to absolute file paths:
          {"markdown": "/vault/50-BUSINESS/weekly/2026-W09.md"}
        """
        # Markdown under 50-BUSINESS/
        md_dir = self._vault / self._BUSINESS_DIR / self._WEEKLY_SUBDIR
        md_dir.mkdir(parents=True, exist_ok=True)
        md_path = md_dir / f"{report.period.slug}.md"
        md_path.write_text(self._reporter.to_markdown(report), encoding="utf-8")

        # Log the event
        self._logger.log_report_generated(
            period_slug=report.period.slug,
            output_paths=[str(md_path)],
            health=report.overall_health,
        )

        return {"markdown": str(md_path)}

    def generate_and_save(
        self, week_offset: int = 0
    ) -> tuple[WeeklyReport, dict[str, str]]:
        """Generate and immediately save the weekly report."""
        report = self.generate_report(week_offset)
        paths  = self.save_report(report)
        return report, paths

    # ------------------------------------------------------------------
    # Logging / introspection
    # ------------------------------------------------------------------

    def read_logs(self, date: Optional[str] = None) -> list[dict]:
        """Return business audit log entries for a given date (YYYY-MM-DD). Default: today."""
        return self._logger.read_entries(date)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def vault_root(self) -> Path:
        return self._vault

    @property
    def collector(self) -> LogCollector:
        return self._collector

    @property
    def reporter(self) -> ReportGenerator:
        return self._reporter

    @property
    def logger(self) -> AuditSkillLogger:
        return self._logger


__all__ = [
    # Facade
    "CeoAuditSkill",
    # Models
    "ReportPeriod",
    "WeeklyReport",
    "HITLStats",
    "OrchestratorStats",
    "WatcherStats",
    "ActionStats",
    "OverallHealth",
    "compute_health",
    "current_week_period",
    # Components
    "LogCollector",
    "ReportGenerator",
    "AuditSkillLogger",
]
