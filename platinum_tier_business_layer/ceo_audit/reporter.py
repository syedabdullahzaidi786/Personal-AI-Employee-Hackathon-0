"""
CEO_WEEKLY_AUDIT_SKILL — Report Generator
Phase 1: Converts a WeeklyReport into structured Markdown.

Output sections:
  1. Header (period, health, generated timestamp)
  2. Executive Summary (KPI table)
  3. HITL Approvals
  4. Orchestrator Activity
  5. Watchers
  6. Action Skills

Constitution compliance:
  - Read-only — produces text; never writes files directly
"""

from __future__ import annotations

from .models import (
    ActionStats,
    HITLStats,
    OrchestratorStats,
    OverallHealth,
    WatcherStats,
    WeeklyReport,
)

_HEALTH_EMOJI: dict[str, str] = {
    OverallHealth.HEALTHY:  "✅",
    OverallHealth.DEGRADED: "⚠️",
    OverallHealth.CRITICAL: "🔴",
    OverallHealth.UNKNOWN:  "❓",
}


class ReportGenerator:
    """Converts a WeeklyReport into a Markdown document."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def to_markdown(self, report: WeeklyReport) -> str:
        """Return the full Markdown report as a string."""
        sections = [
            self._header(report),
            self._exec_summary(report),
            self._hitl_section(report.hitl),
            self._orchestrator_section(report.orchestrator),
            self._watchers_section(report.watchers),
            self._actions_section(report.actions),
            self._footer(report),
        ]
        return "\n\n".join(s for s in sections if s)

    def to_summary_dict(self, report: WeeklyReport) -> dict:
        """Return a compact dict suitable for JSONL audit logging."""
        return {
            "event":                    "report_generated",
            "period":                   report.period.slug,
            "generated_at":             report.generated_at.isoformat(),
            "overall_health":           report.overall_health,
            "hitl_submitted":           report.hitl.submitted,
            "hitl_approval_rate":       report.hitl.approval_rate,
            "orchestrator_runs":        report.orchestrator.runs_total,
            "orchestrator_success_rate": report.orchestrator.success_rate,
            "action_skills":            [a.skill_name for a in report.actions],
        }

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------

    def _header(self, report: WeeklyReport) -> str:
        p      = report.period
        health = report.overall_health
        emoji  = _HEALTH_EMOJI.get(health, "❓")
        return (
            f"# CEO Weekly Report — {p.label}\n\n"
            f"**Report ID**: `{p.slug}`  \n"
            f"**Period**: {p.start_date} → {p.end_date}  \n"
            f"**Generated**: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')} UTC  \n"
            f"**Overall Health**: {emoji} **{health}**"
        )

    def _exec_summary(self, report: WeeklyReport) -> str:
        h  = report.hitl
        o  = report.orchestrator
        ar = f"{h.approval_rate:.0%}" if h.approval_rate is not None else "N/A"
        sr = f"{o.success_rate:.0%}" if o.success_rate is not None else "N/A"
        total_events  = sum(w.events for w in report.watchers)
        total_actions = sum(a.submitted for a in report.actions)

        lines = [
            "## Executive Summary\n",
            "| Metric | Value |",
            "|---|---|",
            f"| HITL Requests | {h.submitted} |",
            f"| HITL Approval Rate | {ar} |",
            f"| HITL Pending | {h.pending} |",
            f"| Orchestrator Runs | {o.runs_total} |",
            f"| Run Success Rate | {sr} |",
            f"| Watcher Events | {total_events} |",
            f"| Action Submissions | {total_actions} |",
            f"| Overall Health | {report.overall_health} |",
        ]
        return "\n".join(lines)

    def _hitl_section(self, h: HITLStats) -> str:
        ar = f"{h.approval_rate:.1%}" if h.approval_rate is not None else "N/A"
        lines = [
            "## HITL Approvals\n",
            "| Status | Count |",
            "|---|---|",
            f"| Submitted | {h.submitted} |",
            f"| Approved (human) | {h.approved} |",
            f"| Auto-Approved (Tier 0–1) | {h.auto_approved} |",
            f"| Denied | {h.denied} |",
            f"| Deferred | {h.deferred} |",
            f"| Timeout | {h.timeout} |",
            f"| Pending | {h.pending} |",
            f"\n**Approval Rate**: {ar}",
        ]
        return "\n".join(lines)

    def _orchestrator_section(self, o: OrchestratorStats) -> str:
        sr = f"{o.success_rate:.1%}" if o.success_rate is not None else "N/A"
        lines = [
            "## Orchestrator Activity\n",
            "| Metric | Count |",
            "|---|---|",
            f"| Workflow Runs | {o.runs_total} |",
            f"| Successful Runs | {o.runs_success} |",
            f"| Failed Runs | {o.runs_failed} |",
            f"| Total Steps | {o.steps_total} |",
            f"| Failed Steps | {o.steps_failed} |",
            f"| Skipped Steps | {o.steps_skipped} |",
            f"| HITL Gates Triggered | {o.hitl_gates} |",
            f"| Errors | {o.errors} |",
            f"\n**Run Success Rate**: {sr}",
        ]
        return "\n".join(lines)

    def _watchers_section(self, watchers: list[WatcherStats]) -> str:
        if not watchers:
            return "## Watchers\n\n_No watcher data for this period._"
        lines = [
            "## Watchers\n",
            "| Watcher | Events | Polls | Errors | Starts |",
            "|---|---|---|---|---|",
        ]
        for w in watchers:
            lines.append(f"| `{w.watcher_id}` | {w.events} | {w.polls} | {w.errors} | {w.starts} |")
        return "\n".join(lines)

    def _actions_section(self, actions: list[ActionStats]) -> str:
        if not actions:
            return "## Action Skills\n\n_No action data for this period._"
        lines = [
            "## Action Skills\n",
            "| Skill | Submitted | Success | Failed | Denied | Pending Approval |",
            "|---|---|---|---|---|---|",
        ]
        for a in actions:
            lines.append(
                f"| `{a.skill_name}` | {a.submitted} | {a.success} | "
                f"{a.failed} | {a.denied} | {a.pending_approval} |"
            )
        return "\n".join(lines)

    def _footer(self, report: WeeklyReport) -> str:
        return (
            "---\n\n"
            f"_Generated by CEO_WEEKLY_AUDIT_SKILL — "
            f"{report.generated_at.strftime('%Y-%m-%d %H:%M:%S')} UTC_"
        )
