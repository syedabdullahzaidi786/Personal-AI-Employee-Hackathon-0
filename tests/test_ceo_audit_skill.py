"""
Tests for CEO_WEEKLY_AUDIT_SKILL Phase 1.

Coverage:
  - ReportPeriod helpers (iso week bounds, date_strings, contains, slug)
  - HITLStats / OrchestratorStats / WatcherStats / ActionStats metrics
  - WeeklyReport / compute_health
  - LogCollector — HITL, Orchestrator, Watcher, Action collection
  - ReportGenerator — markdown structure, summary dict
  - AuditSkillLogger — read/write JSONL
  - CeoAuditSkill facade — generate, save, generate_and_save
  - CLI — build_parser, cmd_generate
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import pytest

from platinum_tier_business_layer.ceo_audit.models import (
    ActionStats,
    HITLStats,
    OrchestratorStats,
    OverallHealth,
    ReportPeriod,
    WeeklyReport,
    WatcherStats,
    _iso_week_bounds,
    compute_health,
    current_week_period,
)
from platinum_tier_business_layer.ceo_audit.collector import LogCollector
from platinum_tier_business_layer.ceo_audit.reporter import ReportGenerator
from platinum_tier_business_layer.ceo_audit.logger import AuditSkillLogger
from platinum_tier_business_layer.ceo_audit import CeoAuditSkill


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def fixed_period() -> ReportPeriod:
    """A fixed period for deterministic tests: 2026-W09 (Mon 2026-02-23 → Sun 2026-03-01)."""
    start, end = _iso_week_bounds(2026, 9)
    return ReportPeriod(year=2026, week_number=9, start_date=start, end_date=end)


@pytest.fixture
def collector(tmp_vault: Path) -> LogCollector:
    return LogCollector(tmp_vault)


@pytest.fixture
def skill(tmp_vault: Path) -> CeoAuditSkill:
    return CeoAuditSkill(vault_root=tmp_vault)


# ---------------------------------------------------------------------------
# TestIsoWeekBounds
# ---------------------------------------------------------------------------

class TestIsoWeekBounds:
    def test_2026_w09_monday(self) -> None:
        monday, sunday = _iso_week_bounds(2026, 9)
        assert monday == date(2026, 2, 23)

    def test_2026_w09_sunday(self) -> None:
        monday, sunday = _iso_week_bounds(2026, 9)
        assert sunday == date(2026, 3, 1)

    def test_monday_is_weekday_1(self) -> None:
        monday, _ = _iso_week_bounds(2026, 9)
        assert monday.isoweekday() == 1

    def test_sunday_is_weekday_7(self) -> None:
        _, sunday = _iso_week_bounds(2026, 9)
        assert sunday.isoweekday() == 7

    def test_span_is_7_days(self) -> None:
        monday, sunday = _iso_week_bounds(2026, 9)
        assert (sunday - monday).days == 6


# ---------------------------------------------------------------------------
# TestReportPeriod
# ---------------------------------------------------------------------------

class TestReportPeriod:
    def test_slug(self, fixed_period: ReportPeriod) -> None:
        assert fixed_period.slug == "2026-W09"

    def test_label(self, fixed_period: ReportPeriod) -> None:
        assert fixed_period.label == "Week 09, 2026"

    def test_date_strings_count(self, fixed_period: ReportPeriod) -> None:
        dates = fixed_period.date_strings()
        assert len(dates) == 7

    def test_date_strings_start(self, fixed_period: ReportPeriod) -> None:
        dates = fixed_period.date_strings()
        assert dates[0] == "2026-02-23"

    def test_date_strings_end(self, fixed_period: ReportPeriod) -> None:
        dates = fixed_period.date_strings()
        assert dates[-1] == "2026-03-01"

    def test_contains_start_date(self, fixed_period: ReportPeriod) -> None:
        dt = datetime(2026, 2, 23, 10, 0, tzinfo=timezone.utc)
        assert fixed_period.contains(dt) is True

    def test_contains_end_date(self, fixed_period: ReportPeriod) -> None:
        dt = datetime(2026, 3, 1, 23, 59, tzinfo=timezone.utc)
        assert fixed_period.contains(dt) is True

    def test_contains_mid_week(self, fixed_period: ReportPeriod) -> None:
        dt = datetime(2026, 2, 25, 12, 0, tzinfo=timezone.utc)
        assert fixed_period.contains(dt) is True

    def test_not_contains_before(self, fixed_period: ReportPeriod) -> None:
        dt = datetime(2026, 2, 22, 23, 59, tzinfo=timezone.utc)
        assert fixed_period.contains(dt) is False

    def test_not_contains_after(self, fixed_period: ReportPeriod) -> None:
        dt = datetime(2026, 3, 2, 0, 0, tzinfo=timezone.utc)
        assert fixed_period.contains(dt) is False

    def test_to_dict_keys(self, fixed_period: ReportPeriod) -> None:
        d = fixed_period.to_dict()
        assert set(d.keys()) == {"year", "week_number", "start_date", "end_date", "label", "slug"}

    def test_to_dict_values(self, fixed_period: ReportPeriod) -> None:
        d = fixed_period.to_dict()
        assert d["year"] == 2026
        assert d["week_number"] == 9
        assert d["slug"] == "2026-W09"


class TestCurrentWeekPeriod:
    def test_returns_report_period(self) -> None:
        p = current_week_period()
        assert isinstance(p, ReportPeriod)

    def test_start_is_monday(self) -> None:
        p = current_week_period()
        assert p.start_date.isoweekday() == 1

    def test_end_is_sunday(self) -> None:
        p = current_week_period()
        assert p.end_date.isoweekday() == 7

    def test_offset_minus1_earlier_than_offset0(self) -> None:
        current = current_week_period(0)
        prev    = current_week_period(-1)
        assert prev.start_date < current.start_date


# ---------------------------------------------------------------------------
# TestHITLStats
# ---------------------------------------------------------------------------

class TestHITLStats:
    def test_approval_rate_none_when_no_decisions(self) -> None:
        s = HITLStats(submitted=5, pending=5)
        assert s.approval_rate is None

    def test_approval_rate_all_approved(self) -> None:
        s = HITLStats(submitted=4, approved=4)
        assert s.approval_rate == 1.0

    def test_approval_rate_half(self) -> None:
        s = HITLStats(submitted=4, approved=2, denied=2)
        assert s.approval_rate == 0.5

    def test_decided_excludes_pending(self) -> None:
        s = HITLStats(approved=2, denied=1, pending=3)
        assert s.decided == 3

    def test_auto_approved_counts_toward_approved(self) -> None:
        s = HITLStats(approved=1, auto_approved=3)
        assert s.approval_rate == 1.0

    def test_to_dict_has_approval_rate(self) -> None:
        s = HITLStats(approved=3, denied=1)
        d = s.to_dict()
        assert "approval_rate" in d
        assert d["approval_rate"] == 0.75


# ---------------------------------------------------------------------------
# TestOrchestratorStats
# ---------------------------------------------------------------------------

class TestOrchestratorStats:
    def test_success_rate_none_when_no_runs(self) -> None:
        s = OrchestratorStats()
        assert s.success_rate is None

    def test_success_rate_all_success(self) -> None:
        s = OrchestratorStats(runs_total=5, runs_success=5)
        assert s.success_rate == 1.0

    def test_success_rate_partial(self) -> None:
        s = OrchestratorStats(runs_total=4, runs_success=3, runs_failed=1)
        assert s.success_rate == 0.75

    def test_to_dict_keys(self) -> None:
        s = OrchestratorStats()
        d = s.to_dict()
        assert "runs_total" in d and "success_rate" in d


# ---------------------------------------------------------------------------
# TestWatcherStats
# ---------------------------------------------------------------------------

class TestWatcherStats:
    def test_to_dict(self) -> None:
        w = WatcherStats(watcher_id="gmail-watcher", events=10, polls=5)
        d = w.to_dict()
        assert d["watcher_id"] == "gmail-watcher"
        assert d["events"] == 10
        assert d["polls"] == 5


# ---------------------------------------------------------------------------
# TestActionStats
# ---------------------------------------------------------------------------

class TestActionStats:
    def test_success_rate_none_when_nothing_settled(self) -> None:
        a = ActionStats(skill_name="email", submitted=3, pending_approval=3)
        assert a.success_rate is None

    def test_success_rate_all_success(self) -> None:
        a = ActionStats(skill_name="email", submitted=3, success=3)
        assert a.success_rate == 1.0

    def test_success_rate_mixed(self) -> None:
        a = ActionStats(skill_name="odoo", submitted=4, success=3, failed=1)
        assert a.success_rate == 0.75

    def test_to_dict_keys(self) -> None:
        a = ActionStats(skill_name="browser")
        d = a.to_dict()
        assert "skill_name" in d and "success_rate" in d


# ---------------------------------------------------------------------------
# TestComputeHealth
# ---------------------------------------------------------------------------

class TestComputeHealth:
    def test_healthy_when_all_empty(self) -> None:
        assert compute_health(HITLStats(), OrchestratorStats(), []) == OverallHealth.HEALTHY

    def test_critical_when_denial_rate_over_50pct(self) -> None:
        h = HITLStats(approved=1, denied=5)  # 5/6 denied ≈ 83%
        assert compute_health(h, OrchestratorStats(), []) == OverallHealth.CRITICAL

    def test_critical_when_run_fail_rate_over_50pct(self) -> None:
        o = OrchestratorStats(runs_total=4, runs_success=1, runs_failed=3)
        assert compute_health(HITLStats(), o, []) == OverallHealth.CRITICAL

    def test_degraded_when_any_denial(self) -> None:
        h = HITLStats(approved=9, denied=1)
        assert compute_health(h, OrchestratorStats(), []) == OverallHealth.DEGRADED

    def test_degraded_when_run_fail_rate_over_20pct(self) -> None:
        o = OrchestratorStats(runs_total=5, runs_success=3, runs_failed=2)
        assert compute_health(HITLStats(), o, []) == OverallHealth.DEGRADED

    def test_degraded_when_action_failure(self) -> None:
        a = ActionStats(skill_name="email", success=3, failed=1)
        assert compute_health(HITLStats(), OrchestratorStats(), [a]) == OverallHealth.DEGRADED

    def test_healthy_with_all_success(self) -> None:
        h = HITLStats(submitted=5, approved=5)
        o = OrchestratorStats(runs_total=3, runs_success=3)
        a = [ActionStats(skill_name="email", submitted=2, success=2)]
        assert compute_health(h, o, a) == OverallHealth.HEALTHY


# ---------------------------------------------------------------------------
# TestWeeklyReport
# ---------------------------------------------------------------------------

class TestWeeklyReport:
    def test_to_dict_keys(self, fixed_period: ReportPeriod) -> None:
        r = WeeklyReport(
            period=fixed_period,
            generated_at=datetime.now(tz=timezone.utc),
            hitl=HITLStats(),
            orchestrator=OrchestratorStats(),
        )
        d = r.to_dict()
        assert "period" in d
        assert "hitl" in d
        assert "orchestrator" in d
        assert "watchers" in d
        assert "actions" in d

    def test_to_dict_overall_health(self, fixed_period: ReportPeriod) -> None:
        r = WeeklyReport(
            period=fixed_period,
            generated_at=datetime.now(tz=timezone.utc),
            hitl=HITLStats(),
            orchestrator=OrchestratorStats(),
            overall_health=OverallHealth.HEALTHY,
        )
        assert r.to_dict()["overall_health"] == "HEALTHY"


# ---------------------------------------------------------------------------
# TestLogCollector — HITL
# ---------------------------------------------------------------------------

def _write_hitl_completed(vault: Path, request_id: str, submitted_at: str,
                           action: str) -> None:
    """Write a fake completed HITL JSON file."""
    d = vault / "70-LOGS" / "hitl" / "completed"
    d.mkdir(parents=True, exist_ok=True)
    decision = {"action": action, "decided_by": "operator", "decided_at": submitted_at}
    data = {
        "request_id": request_id,
        "agent_id": "test-agent",
        "operation": "test_op",
        "tier": 3,
        "action_summary": "Test action",
        "reason": "Test",
        "details": {},
        "risk": {},
        "submitted_at": submitted_at,
        "status": action,
        "options": ["approve", "deny"],
        "checksum": "sha256:abc",
        "sla": {"tier": 3, "sla_seconds": 3600, "submitted_at": submitted_at,
                "timeout_action": "deny"},
        "decision": decision,
    }
    (d / f"{request_id}.json").write_text(json.dumps(data), encoding="utf-8")


def _write_hitl_pending(vault: Path, request_id: str, submitted_at: str) -> None:
    d = vault / "70-LOGS" / "hitl" / "pending"
    d.mkdir(parents=True, exist_ok=True)
    data = {
        "request_id": request_id,
        "agent_id": "test-agent",
        "operation": "test_op",
        "tier": 3,
        "action_summary": "Test",
        "reason": "Test",
        "details": {},
        "risk": {},
        "submitted_at": submitted_at,
        "status": "PENDING",
        "options": ["approve", "deny"],
        "checksum": "sha256:abc",
        "sla": {"tier": 3, "sla_seconds": 3600, "submitted_at": submitted_at,
                "timeout_action": "deny"},
    }
    (d / f"{request_id}.json").write_text(json.dumps(data), encoding="utf-8")


class TestLogCollectorHITL:
    def test_empty_vault_returns_zeros(self, collector: LogCollector,
                                       fixed_period: ReportPeriod) -> None:
        stats = collector.collect_hitl(fixed_period)
        assert stats.submitted == 0
        assert stats.approved == 0

    def test_counts_approved(self, tmp_vault: Path, fixed_period: ReportPeriod) -> None:
        _write_hitl_completed(tmp_vault, "REQ-001", "2026-02-25T10:00:00+00:00", "APPROVED")
        stats = LogCollector(tmp_vault).collect_hitl(fixed_period)
        assert stats.submitted == 1
        assert stats.approved == 1

    def test_counts_denied(self, tmp_vault: Path, fixed_period: ReportPeriod) -> None:
        _write_hitl_completed(tmp_vault, "REQ-002", "2026-02-24T10:00:00+00:00", "DENIED")
        stats = LogCollector(tmp_vault).collect_hitl(fixed_period)
        assert stats.denied == 1

    def test_counts_deferred(self, tmp_vault: Path, fixed_period: ReportPeriod) -> None:
        _write_hitl_completed(tmp_vault, "REQ-003", "2026-02-24T10:00:00+00:00", "DEFERRED")
        stats = LogCollector(tmp_vault).collect_hitl(fixed_period)
        assert stats.deferred == 1

    def test_counts_pending(self, tmp_vault: Path, fixed_period: ReportPeriod) -> None:
        _write_hitl_pending(tmp_vault, "REQ-004", "2026-02-26T10:00:00+00:00")
        stats = LogCollector(tmp_vault).collect_hitl(fixed_period)
        assert stats.pending == 1

    def test_excludes_out_of_period(self, tmp_vault: Path, fixed_period: ReportPeriod) -> None:
        # Outside period (week before: 2026-02-16)
        _write_hitl_completed(tmp_vault, "REQ-005", "2026-02-16T10:00:00+00:00", "APPROVED")
        stats = LogCollector(tmp_vault).collect_hitl(fixed_period)
        assert stats.submitted == 0

    def test_mixed_approved_denied_pending(self, tmp_vault: Path,
                                            fixed_period: ReportPeriod) -> None:
        _write_hitl_completed(tmp_vault, "REQ-A", "2026-02-23T10:00:00+00:00", "APPROVED")
        _write_hitl_completed(tmp_vault, "REQ-B", "2026-02-24T10:00:00+00:00", "DENIED")
        _write_hitl_pending(tmp_vault, "REQ-C", "2026-02-25T10:00:00+00:00")
        stats = LogCollector(tmp_vault).collect_hitl(fixed_period)
        assert stats.submitted == 3
        assert stats.approved == 1
        assert stats.denied == 1
        assert stats.pending == 1

    def test_corrupted_file_skipped(self, tmp_vault: Path, fixed_period: ReportPeriod) -> None:
        d = tmp_vault / "70-LOGS" / "hitl" / "completed"
        d.mkdir(parents=True, exist_ok=True)
        (d / "bad.json").write_text("not-json", encoding="utf-8")
        stats = LogCollector(tmp_vault).collect_hitl(fixed_period)
        assert stats.submitted == 0  # graceful


# ---------------------------------------------------------------------------
# TestLogCollector — Orchestrator
# ---------------------------------------------------------------------------

def _write_orch_daily(vault: Path, date_str: str, lines: list[str]) -> None:
    d = vault / "70-LOGS" / "orchestrator" / "daily"
    d.mkdir(parents=True, exist_ok=True)
    content = "\n".join(lines) + "\n"
    (d / f"{date_str}-orchestrator.md").write_text(content, encoding="utf-8")


class TestLogCollectorOrchestrator:
    def test_empty_returns_zeros(self, collector: LogCollector,
                                  fixed_period: ReportPeriod) -> None:
        stats = collector.collect_orchestrator(fixed_period)
        assert stats.runs_total == 0

    def test_counts_run_started(self, tmp_vault: Path, fixed_period: ReportPeriod) -> None:
        _write_orch_daily(tmp_vault, "2026-02-25", [
            "| 2026-02-25T10:00:00Z | RUN_STARTED | RUN-001 | wf1 | steps=3 |",
        ])
        stats = LogCollector(tmp_vault).collect_orchestrator(fixed_period)
        assert stats.runs_total == 1

    def test_counts_run_finished_completed(self, tmp_vault: Path,
                                            fixed_period: ReportPeriod) -> None:
        _write_orch_daily(tmp_vault, "2026-02-25", [
            "| 2026-02-25T10:00:00Z | RUN_STARTED | RUN-001 | wf1 | steps=3 |",
            "| 2026-02-25T10:00:05Z | RUN_FINISHED | RUN-001 | status=completed | duration=500ms |",
        ])
        stats = LogCollector(tmp_vault).collect_orchestrator(fixed_period)
        assert stats.runs_success == 1
        assert stats.runs_failed == 0

    def test_counts_run_finished_failed(self, tmp_vault: Path,
                                         fixed_period: ReportPeriod) -> None:
        _write_orch_daily(tmp_vault, "2026-02-24", [
            "| 2026-02-24T09:00:00Z | RUN_STARTED | RUN-002 | wf2 | steps=2 |",
            "| 2026-02-24T09:00:02Z | RUN_FINISHED | RUN-002 | status=failed | duration=200ms |",
        ])
        stats = LogCollector(tmp_vault).collect_orchestrator(fixed_period)
        assert stats.runs_failed == 1

    def test_counts_steps(self, tmp_vault: Path, fixed_period: ReportPeriod) -> None:
        _write_orch_daily(tmp_vault, "2026-02-23", [
            "| T | STEP_START | RUN-003 | step1 | fs.create |",
            "| T | STEP_START | RUN-003 | step2 | email.send |",
            "| T | STEP_DONE  | RUN-003 | step2 | status=failed | 100ms |",
        ])
        stats = LogCollector(tmp_vault).collect_orchestrator(fixed_period)
        assert stats.steps_total == 2
        assert stats.steps_failed == 1

    def test_counts_hitl_gates(self, tmp_vault: Path, fixed_period: ReportPeriod) -> None:
        _write_orch_daily(tmp_vault, "2026-02-23", [
            "| T | HITL_GATE | RUN-004 | step1 | tier=3 | req=REQ-001 |",
        ])
        stats = LogCollector(tmp_vault).collect_orchestrator(fixed_period)
        assert stats.hitl_gates == 1

    def test_counts_errors(self, tmp_vault: Path, fixed_period: ReportPeriod) -> None:
        _write_orch_daily(tmp_vault, "2026-02-25", [
            "| T | ERROR | RUN-005 | step1 | Something went wrong |",
        ])
        stats = LogCollector(tmp_vault).collect_orchestrator(fixed_period)
        assert stats.errors == 1

    def test_skips_header_lines(self, tmp_vault: Path, fixed_period: ReportPeriod) -> None:
        _write_orch_daily(tmp_vault, "2026-02-25", [
            "# Orchestrator Daily Log — 2026-02-25",
            "",
            "| T | RUN_STARTED | RUN-006 | wf1 | steps=1 |",
        ])
        stats = LogCollector(tmp_vault).collect_orchestrator(fixed_period)
        assert stats.runs_total == 1

    def test_multiple_days(self, tmp_vault: Path, fixed_period: ReportPeriod) -> None:
        _write_orch_daily(tmp_vault, "2026-02-23", [
            "| T | RUN_STARTED | RUN-001 | wf1 | steps=1 |",
        ])
        _write_orch_daily(tmp_vault, "2026-02-24", [
            "| T | RUN_STARTED | RUN-002 | wf2 | steps=1 |",
        ])
        stats = LogCollector(tmp_vault).collect_orchestrator(fixed_period)
        assert stats.runs_total == 2


# ---------------------------------------------------------------------------
# TestLogCollector — Watchers
# ---------------------------------------------------------------------------

def _write_watcher_daily(vault: Path, watcher_id: str, date_str: str,
                          lines: list[str]) -> None:
    d = vault / "70-LOGS" / "watchers" / watcher_id / "daily"
    d.mkdir(parents=True, exist_ok=True)
    content = f"# Watcher Log — {watcher_id} — {date_str}\n\n"
    content += "| Time | Action | Events | Errors | Details |\n"
    content += "|------|--------|--------|--------|--------|\n"
    content += "\n".join(lines) + "\n"
    (d / f"{date_str}.md").write_text(content, encoding="utf-8")


def _write_watcher_error(vault: Path, watcher_id: str, date_str: str,
                          error_lines: list[str]) -> None:
    d = vault / "70-LOGS" / "watchers" / watcher_id / "errors"
    d.mkdir(parents=True, exist_ok=True)
    content = f"# Error Log — {watcher_id} — {date_str}\n\n"
    content += "| Time | Error |\n|------|-------|\n"
    content += "\n".join(error_lines) + "\n"
    (d / f"{date_str}-errors.md").write_text(content, encoding="utf-8")


class TestLogCollectorWatchers:
    def test_empty_returns_empty_list(self, collector: LogCollector,
                                       fixed_period: ReportPeriod) -> None:
        result = collector.collect_watchers(fixed_period)
        assert result == []

    def test_counts_polls_and_events(self, tmp_vault: Path,
                                      fixed_period: ReportPeriod) -> None:
        _write_watcher_daily(tmp_vault, "gmail-watcher", "2026-02-25", [
            "| T | START | - | 0 | Watcher started |",
            "| T | POLL | 3 | 0 | Poll cycle complete |",
            "| T | POLL | 2 | 0 | Poll cycle complete |",
        ])
        stats_list = LogCollector(tmp_vault).collect_watchers(fixed_period)
        assert len(stats_list) == 1
        w = stats_list[0]
        assert w.watcher_id == "gmail-watcher"
        assert w.polls == 2
        assert w.events == 5  # 3 + 2
        assert w.starts == 1

    def test_counts_errors(self, tmp_vault: Path, fixed_period: ReportPeriod) -> None:
        _write_watcher_daily(tmp_vault, "wa-watcher", "2026-02-24", [])
        _write_watcher_error(tmp_vault, "wa-watcher", "2026-02-24", [
            "| T | Connection refused |",
            "| T | Timeout |",
        ])
        stats_list = LogCollector(tmp_vault).collect_watchers(fixed_period)
        assert stats_list[0].errors == 2

    def test_multiple_watchers(self, tmp_vault: Path, fixed_period: ReportPeriod) -> None:
        _write_watcher_daily(tmp_vault, "gmail-watcher", "2026-02-23", [
            "| T | POLL | 1 | 0 | done |",
        ])
        _write_watcher_daily(tmp_vault, "wa-watcher", "2026-02-23", [
            "| T | POLL | 0 | 0 | done |",
        ])
        stats_list = LogCollector(tmp_vault).collect_watchers(fixed_period)
        ids = {s.watcher_id for s in stats_list}
        assert "gmail-watcher" in ids
        assert "wa-watcher" in ids

    def test_zero_events_poll(self, tmp_vault: Path, fixed_period: ReportPeriod) -> None:
        _write_watcher_daily(tmp_vault, "fs-watcher", "2026-02-23", [
            "| T | POLL | 0 | 0 | done |",
        ])
        stats_list = LogCollector(tmp_vault).collect_watchers(fixed_period)
        assert stats_list[0].events == 0


# ---------------------------------------------------------------------------
# TestLogCollector — Actions
# ---------------------------------------------------------------------------

def _write_action_jsonl(vault: Path, skill: str, date_str: str,
                         entries: list[dict]) -> None:
    d = vault / "70-LOGS" / skill
    d.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(e) for e in entries]
    (d / f"{date_str}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestLogCollectorActions:
    def test_empty_returns_three_skills_with_zeros(
        self, collector: LogCollector, fixed_period: ReportPeriod
    ) -> None:
        result = collector.collect_actions(fixed_period)
        assert len(result) == 3
        assert all(a.submitted == 0 for a in result)

    def test_counts_submitted(self, tmp_vault: Path, fixed_period: ReportPeriod) -> None:
        _write_action_jsonl(tmp_vault, "email", "2026-02-25", [
            {"event": "submitted", "request_id": "R1"},
            {"event": "submitted", "request_id": "R2"},
        ])
        stats_list = LogCollector(tmp_vault).collect_actions(fixed_period)
        email = next(a for a in stats_list if a.skill_name == "email")
        assert email.submitted == 2

    def test_counts_success(self, tmp_vault: Path, fixed_period: ReportPeriod) -> None:
        _write_action_jsonl(tmp_vault, "odoo", "2026-02-24", [
            {"event": "result", "status": "SUCCESS"},
        ])
        stats_list = LogCollector(tmp_vault).collect_actions(fixed_period)
        odoo = next(a for a in stats_list if a.skill_name == "odoo")
        assert odoo.success == 1

    def test_counts_sent_as_success(self, tmp_vault: Path, fixed_period: ReportPeriod) -> None:
        _write_action_jsonl(tmp_vault, "email", "2026-02-24", [
            {"event": "result", "status": "SENT"},
        ])
        stats_list = LogCollector(tmp_vault).collect_actions(fixed_period)
        email = next(a for a in stats_list if a.skill_name == "email")
        assert email.success == 1

    def test_counts_failed(self, tmp_vault: Path, fixed_period: ReportPeriod) -> None:
        _write_action_jsonl(tmp_vault, "browser", "2026-02-25", [
            {"event": "result", "status": "FAILED"},
        ])
        stats_list = LogCollector(tmp_vault).collect_actions(fixed_period)
        browser = next(a for a in stats_list if a.skill_name == "browser")
        assert browser.failed == 1

    def test_counts_not_found_as_failed(self, tmp_vault: Path,
                                         fixed_period: ReportPeriod) -> None:
        _write_action_jsonl(tmp_vault, "odoo", "2026-02-23", [
            {"event": "result", "status": "NOT_FOUND"},
        ])
        stats_list = LogCollector(tmp_vault).collect_actions(fixed_period)
        odoo = next(a for a in stats_list if a.skill_name == "odoo")
        assert odoo.failed == 1

    def test_counts_denied(self, tmp_vault: Path, fixed_period: ReportPeriod) -> None:
        _write_action_jsonl(tmp_vault, "odoo", "2026-02-25", [
            {"event": "result", "status": "DENIED"},
        ])
        stats_list = LogCollector(tmp_vault).collect_actions(fixed_period)
        odoo = next(a for a in stats_list if a.skill_name == "odoo")
        assert odoo.denied == 1

    def test_counts_queued_for_hitl_as_pending(self, tmp_vault: Path,
                                                fixed_period: ReportPeriod) -> None:
        _write_action_jsonl(tmp_vault, "odoo", "2026-02-25", [
            {"event": "queued_for_hitl", "request_id": "R1", "hitl_request_id": "H1"},
        ])
        stats_list = LogCollector(tmp_vault).collect_actions(fixed_period)
        odoo = next(a for a in stats_list if a.skill_name == "odoo")
        assert odoo.pending_approval == 1

    def test_bad_json_line_skipped(self, tmp_vault: Path, fixed_period: ReportPeriod) -> None:
        d = tmp_vault / "70-LOGS" / "email"
        d.mkdir(parents=True, exist_ok=True)
        (d / "2026-02-25.jsonl").write_text(
            'bad-json\n{"event":"submitted","request_id":"R1"}\n',
            encoding="utf-8",
        )
        stats_list = LogCollector(tmp_vault).collect_actions(fixed_period)
        email = next(a for a in stats_list if a.skill_name == "email")
        assert email.submitted == 1  # only valid line counted

    def test_multiple_days(self, tmp_vault: Path, fixed_period: ReportPeriod) -> None:
        _write_action_jsonl(tmp_vault, "email", "2026-02-23", [
            {"event": "submitted"}, {"event": "result", "status": "SENT"},
        ])
        _write_action_jsonl(tmp_vault, "email", "2026-02-24", [
            {"event": "submitted"}, {"event": "result", "status": "SENT"},
        ])
        stats_list = LogCollector(tmp_vault).collect_actions(fixed_period)
        email = next(a for a in stats_list if a.skill_name == "email")
        assert email.submitted == 2
        assert email.success == 2


# ---------------------------------------------------------------------------
# TestLogCollector — collect_all
# ---------------------------------------------------------------------------

class TestLogCollectorCollectAll:
    def test_returns_weekly_report(self, collector: LogCollector,
                                    fixed_period: ReportPeriod) -> None:
        r = collector.collect_all(fixed_period)
        assert isinstance(r, WeeklyReport)

    def test_period_matches(self, collector: LogCollector,
                             fixed_period: ReportPeriod) -> None:
        r = collector.collect_all(fixed_period)
        assert r.period.slug == fixed_period.slug

    def test_generated_at_is_utc(self, collector: LogCollector,
                                   fixed_period: ReportPeriod) -> None:
        r = collector.collect_all(fixed_period)
        assert r.generated_at.tzinfo is not None

    def test_overall_health_assigned(self, collector: LogCollector,
                                      fixed_period: ReportPeriod) -> None:
        r = collector.collect_all(fixed_period)
        assert r.overall_health in (
            OverallHealth.HEALTHY, OverallHealth.DEGRADED,
            OverallHealth.CRITICAL, OverallHealth.UNKNOWN,
        )


# ---------------------------------------------------------------------------
# TestReportGenerator
# ---------------------------------------------------------------------------

class TestReportGenerator:
    def _make_report(self, fixed_period: ReportPeriod) -> WeeklyReport:
        return WeeklyReport(
            period=fixed_period,
            generated_at=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
            hitl=HITLStats(submitted=10, approved=8, denied=1, pending=1),
            orchestrator=OrchestratorStats(runs_total=5, runs_success=4, runs_failed=1,
                                            steps_total=20, steps_failed=2),
            watchers=[WatcherStats("gmail-watcher", events=30, polls=10)],
            actions=[ActionStats("email", submitted=5, success=4, failed=1)],
            overall_health=OverallHealth.DEGRADED,
        )

    def test_to_markdown_returns_string(self, fixed_period: ReportPeriod) -> None:
        r = self._make_report(fixed_period)
        md = ReportGenerator().to_markdown(r)
        assert isinstance(md, str)
        assert len(md) > 100

    def test_markdown_contains_period_label(self, fixed_period: ReportPeriod) -> None:
        r = self._make_report(fixed_period)
        md = ReportGenerator().to_markdown(r)
        assert "Week 09, 2026" in md

    def test_markdown_contains_health(self, fixed_period: ReportPeriod) -> None:
        r = self._make_report(fixed_period)
        md = ReportGenerator().to_markdown(r)
        assert "DEGRADED" in md

    def test_markdown_contains_hitl_section(self, fixed_period: ReportPeriod) -> None:
        r = self._make_report(fixed_period)
        md = ReportGenerator().to_markdown(r)
        assert "HITL" in md
        assert "Approval Rate" in md

    def test_markdown_contains_orchestrator_section(self, fixed_period: ReportPeriod) -> None:
        r = self._make_report(fixed_period)
        md = ReportGenerator().to_markdown(r)
        assert "Orchestrator" in md

    def test_markdown_contains_watcher_section(self, fixed_period: ReportPeriod) -> None:
        r = self._make_report(fixed_period)
        md = ReportGenerator().to_markdown(r)
        assert "gmail-watcher" in md

    def test_markdown_contains_action_section(self, fixed_period: ReportPeriod) -> None:
        r = self._make_report(fixed_period)
        md = ReportGenerator().to_markdown(r)
        assert "email" in md

    def test_markdown_empty_watchers(self, fixed_period: ReportPeriod) -> None:
        r = WeeklyReport(
            period=fixed_period,
            generated_at=datetime.now(tz=timezone.utc),
            hitl=HITLStats(),
            orchestrator=OrchestratorStats(),
        )
        md = ReportGenerator().to_markdown(r)
        assert "No watcher data" in md

    def test_markdown_empty_actions(self, fixed_period: ReportPeriod) -> None:
        r = WeeklyReport(
            period=fixed_period,
            generated_at=datetime.now(tz=timezone.utc),
            hitl=HITLStats(),
            orchestrator=OrchestratorStats(),
        )
        md = ReportGenerator().to_markdown(r)
        assert "No action data" in md

    def test_to_summary_dict_keys(self, fixed_period: ReportPeriod) -> None:
        r = self._make_report(fixed_period)
        d = ReportGenerator().to_summary_dict(r)
        assert "event" in d
        assert "period" in d
        assert "overall_health" in d
        assert "hitl_submitted" in d

    def test_to_summary_dict_event_value(self, fixed_period: ReportPeriod) -> None:
        r = self._make_report(fixed_period)
        d = ReportGenerator().to_summary_dict(r)
        assert d["event"] == "report_generated"

    def test_to_summary_dict_period(self, fixed_period: ReportPeriod) -> None:
        r = self._make_report(fixed_period)
        d = ReportGenerator().to_summary_dict(r)
        assert d["period"] == "2026-W09"

    def test_hitl_na_approval_rate(self, fixed_period: ReportPeriod) -> None:
        r = WeeklyReport(
            period=fixed_period,
            generated_at=datetime.now(tz=timezone.utc),
            hitl=HITLStats(submitted=0),
            orchestrator=OrchestratorStats(),
        )
        md = ReportGenerator().to_markdown(r)
        assert "N/A" in md

    def test_footer_present(self, fixed_period: ReportPeriod) -> None:
        r = self._make_report(fixed_period)
        md = ReportGenerator().to_markdown(r)
        assert "CEO_WEEKLY_AUDIT_SKILL" in md


# ---------------------------------------------------------------------------
# TestAuditSkillLogger
# ---------------------------------------------------------------------------

class TestAuditSkillLogger:
    def test_read_entries_empty_when_no_log(self, tmp_vault: Path) -> None:
        logger = AuditSkillLogger(tmp_vault)
        assert logger.read_entries("2026-02-25") == []

    def test_log_report_generated_creates_entry(self, tmp_vault: Path) -> None:
        logger = AuditSkillLogger(tmp_vault)
        today  = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        logger.log_report_generated("2026-W09", ["/vault/50-BUSINESS/weekly/2026-W09.md"], "HEALTHY")
        entries = logger.read_entries(today)
        assert len(entries) == 1
        assert entries[0]["event"] == "report_generated"
        assert entries[0]["period"] == "2026-W09"

    def test_log_error_creates_entry(self, tmp_vault: Path) -> None:
        logger = AuditSkillLogger(tmp_vault)
        today  = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        logger.log_error("Something went wrong")
        entries = logger.read_entries(today)
        assert any(e["event"] == "error" for e in entries)

    def test_multiple_entries_appended(self, tmp_vault: Path) -> None:
        logger = AuditSkillLogger(tmp_vault)
        today  = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        logger.log_report_generated("2026-W08", [], "HEALTHY")
        logger.log_report_generated("2026-W09", [], "DEGRADED")
        entries = logger.read_entries(today)
        assert len(entries) == 2

    def test_log_dir_created_automatically(self, tmp_vault: Path) -> None:
        logger = AuditSkillLogger(tmp_vault)
        logger.log_error("test")
        assert (tmp_vault / "70-LOGS" / "business").exists()

    def test_read_entries_specific_date(self, tmp_vault: Path) -> None:
        logger = AuditSkillLogger(tmp_vault)
        assert logger.read_entries("2000-01-01") == []


# ---------------------------------------------------------------------------
# TestCeoAuditSkill
# ---------------------------------------------------------------------------

class TestCeoAuditSkill:
    def test_generate_report_returns_weekly_report(self, skill: CeoAuditSkill) -> None:
        r = skill.generate_report()
        assert isinstance(r, WeeklyReport)

    def test_generate_report_with_offset(self, skill: CeoAuditSkill) -> None:
        r = skill.generate_report(week_offset=-1)
        assert isinstance(r, WeeklyReport)

    def test_save_report_creates_markdown_file(
        self, skill: CeoAuditSkill, fixed_period: ReportPeriod, tmp_vault: Path
    ) -> None:
        r = WeeklyReport(
            period=fixed_period,
            generated_at=datetime.now(tz=timezone.utc),
            hitl=HITLStats(),
            orchestrator=OrchestratorStats(),
        )
        paths = skill.save_report(r)
        assert "markdown" in paths
        assert Path(paths["markdown"]).exists()

    def test_save_report_markdown_contains_period(
        self, skill: CeoAuditSkill, fixed_period: ReportPeriod
    ) -> None:
        r = WeeklyReport(
            period=fixed_period,
            generated_at=datetime.now(tz=timezone.utc),
            hitl=HITLStats(),
            orchestrator=OrchestratorStats(),
        )
        paths = skill.save_report(r)
        content = Path(paths["markdown"]).read_text(encoding="utf-8")
        assert "2026-W09" in content

    def test_save_report_creates_log_entry(
        self, skill: CeoAuditSkill, fixed_period: ReportPeriod
    ) -> None:
        r = WeeklyReport(
            period=fixed_period,
            generated_at=datetime.now(tz=timezone.utc),
            hitl=HITLStats(),
            orchestrator=OrchestratorStats(),
        )
        skill.save_report(r)
        today   = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        entries = skill.read_logs(today)
        assert len(entries) >= 1
        assert any(e["event"] == "report_generated" for e in entries)

    def test_generate_and_save_returns_tuple(self, skill: CeoAuditSkill) -> None:
        result = skill.generate_and_save()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_generate_and_save_report_is_weekly_report(self, skill: CeoAuditSkill) -> None:
        report, _ = skill.generate_and_save()
        assert isinstance(report, WeeklyReport)

    def test_generate_and_save_paths_has_markdown(self, skill: CeoAuditSkill) -> None:
        _, paths = skill.generate_and_save()
        assert "markdown" in paths

    def test_markdown_saved_under_50_business(
        self, skill: CeoAuditSkill, tmp_vault: Path
    ) -> None:
        _, paths = skill.generate_and_save()
        md_path = Path(paths["markdown"])
        assert "50-BUSINESS" in str(md_path)
        assert "weekly" in str(md_path)

    def test_read_logs_returns_list(self, skill: CeoAuditSkill) -> None:
        result = skill.read_logs("2000-01-01")
        assert isinstance(result, list)

    def test_vault_root_property(self, skill: CeoAuditSkill, tmp_vault: Path) -> None:
        assert skill.vault_root == tmp_vault

    def test_collector_property(self, skill: CeoAuditSkill) -> None:
        assert isinstance(skill.collector, LogCollector)

    def test_reporter_property(self, skill: CeoAuditSkill) -> None:
        assert isinstance(skill.reporter, ReportGenerator)

    def test_save_creates_weekly_dir(self, skill: CeoAuditSkill, fixed_period: ReportPeriod,
                                      tmp_vault: Path) -> None:
        r = WeeklyReport(
            period=fixed_period,
            generated_at=datetime.now(tz=timezone.utc),
            hitl=HITLStats(),
            orchestrator=OrchestratorStats(),
        )
        skill.save_report(r)
        assert (tmp_vault / "50-BUSINESS" / "weekly").exists()

    def test_full_integration_with_real_logs(
        self, tmp_vault: Path, fixed_period: ReportPeriod
    ) -> None:
        """Integration: write logs → generate report → verify stats."""
        # Write HITL completed file
        _write_hitl_completed(tmp_vault, "REQ-INT", "2026-02-25T10:00:00+00:00", "APPROVED")
        # Write orchestrator daily
        _write_orch_daily(tmp_vault, "2026-02-25", [
            "| T | RUN_STARTED | RUN-INT | wf | steps=2 |",
            "| T | RUN_FINISHED | RUN-INT | status=completed | duration=100ms |",
        ])
        # Write action JSONL
        _write_action_jsonl(tmp_vault, "email", "2026-02-25", [
            {"event": "submitted"}, {"event": "result", "status": "SENT"},
        ])
        skill = CeoAuditSkill(vault_root=tmp_vault)
        report, paths = skill.generate_and_save(-9)  # won't match fixed_period, zero counts
        # But with the fixed collector approach:
        collector = LogCollector(tmp_vault)
        r = collector.collect_all(fixed_period)
        assert r.hitl.submitted == 1
        assert r.hitl.approved == 1
        assert r.orchestrator.runs_total == 1
        assert r.orchestrator.runs_success == 1
        email_stats = next(a for a in r.actions if a.skill_name == "email")
        assert email_stats.submitted == 1
        assert email_stats.success == 1


# ---------------------------------------------------------------------------
# TestCLI
# ---------------------------------------------------------------------------

class TestCLI:
    def test_build_parser_returns_parser(self) -> None:
        from platinum_tier_business_layer.ceo_audit.cli import build_parser
        parser = build_parser()
        assert parser is not None

    def test_generate_subcommand_exists(self) -> None:
        from platinum_tier_business_layer.ceo_audit.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["--vault", "/tmp/v", "generate-weekly-report"])
        assert args.command == "generate-weekly-report"

    def test_generate_default_week_is_zero(self) -> None:
        from platinum_tier_business_layer.ceo_audit.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["--vault", "/tmp/v", "generate-weekly-report"])
        assert args.week == 0

    def test_generate_week_minus_one(self) -> None:
        from platinum_tier_business_layer.ceo_audit.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["--vault", "/tmp/v", "generate-weekly-report", "--week", "-1"])
        assert args.week == -1

    def test_cmd_generate_returns_zero(self, tmp_vault: Path) -> None:
        from platinum_tier_business_layer.ceo_audit.cli import main
        ret = main(["--vault", str(tmp_vault), "generate-weekly-report"])
        assert ret == 0

    def test_cmd_generate_creates_markdown_file(self, tmp_vault: Path) -> None:
        from platinum_tier_business_layer.ceo_audit.cli import main
        main(["--vault", str(tmp_vault), "generate-weekly-report"])
        weekly_dir = tmp_vault / "50-BUSINESS" / "weekly"
        assert weekly_dir.exists()
        md_files = list(weekly_dir.glob("*.md"))
        assert len(md_files) == 1

    def test_cmd_generate_previous_week(self, tmp_vault: Path) -> None:
        from platinum_tier_business_layer.ceo_audit.cli import main
        ret = main(["--vault", str(tmp_vault), "generate-weekly-report", "--week", "-1"])
        assert ret == 0

    def test_cmd_generate_logs_entry(self, tmp_vault: Path) -> None:
        from platinum_tier_business_layer.ceo_audit.cli import main
        main(["--vault", str(tmp_vault), "generate-weekly-report"])
        today   = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        entries = AuditSkillLogger(tmp_vault).read_entries(today)
        assert len(entries) >= 1

    def test_print_report_flag_accepted(self, tmp_vault: Path, capsys: pytest.CaptureFixture) -> None:
        from platinum_tier_business_layer.ceo_audit.cli import main
        ret = main(["--vault", str(tmp_vault), "generate-weekly-report", "--print-report"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "CEO Weekly Report" in out
