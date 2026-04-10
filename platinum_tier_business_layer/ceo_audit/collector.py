"""
CEO_WEEKLY_AUDIT_SKILL — Log Collector
Phase 1: Reads and aggregates log data from all skill log directories.

Log sources:
  - 70-LOGS/hitl/pending/*.json        — HITL pending requests
  - 70-LOGS/hitl/completed/*.json      — HITL decided requests
  - 70-LOGS/orchestrator/daily/        — Orchestrator pipe-delimited .md logs
  - 70-LOGS/watchers/{id}/daily/       — Watcher pipe-delimited .md logs
  - 70-LOGS/watchers/{id}/errors/      — Watcher error .md logs
  - 70-LOGS/email/YYYY-MM-DD.jsonl     — Email action JSONL logs
  - 70-LOGS/browser/YYYY-MM-DD.jsonl   — Browser action JSONL logs
  - 70-LOGS/odoo/YYYY-MM-DD.jsonl      — Odoo action JSONL logs

Constitution compliance:
  - Read-only — never writes to any log directory
  - Principle VI: Fail Safe — all reads non-raising; data gaps → zero counts
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import (
    ActionStats,
    HITLStats,
    OrchestratorStats,
    OverallHealth,
    ReportPeriod,
    WeeklyReport,
    WatcherStats,
    compute_health,
)

# Successful statuses across action skills (names differ by skill)
_SUCCESS_STATUSES = {"SUCCESS", "SENT", "APPROVED"}
_FAILURE_STATUSES = {"FAILED", "NOT_FOUND", "ERROR"}
_DENIED_STATUSES  = {"DENIED"}


class LogCollector:
    """
    Reads 70-LOGS/ sub-directories and aggregates KPI data for a ReportPeriod.

    All public methods are non-raising — file-system gaps yield zero counts.
    """

    def __init__(self, vault_root: str | Path) -> None:
        self._vault = Path(vault_root)
        self._logs  = self._vault / "70-LOGS"

    # ------------------------------------------------------------------
    # HITL
    # ------------------------------------------------------------------

    def collect_hitl(self, period: ReportPeriod) -> HITLStats:
        """
        Aggregate HITL approval metrics from pending/ and completed/ JSON stores.
        Filters requests by submitted_at falling within the period.
        """
        stats = HITLStats()
        hitl_base = self._logs / "hitl"

        # Completed requests
        completed_dir = hitl_base / "completed"
        if completed_dir.exists():
            for path in sorted(completed_dir.glob("*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    submitted_at = datetime.fromisoformat(data.get("submitted_at", "1970-01-01"))
                    if not period.contains(submitted_at):
                        continue
                    stats.submitted += 1
                    decision = data.get("decision") or {}
                    action = decision.get("action", "").upper() if decision else ""
                    if not action:
                        action = data.get("status", "").upper()
                    if action == "APPROVED":
                        stats.approved += 1
                    elif action == "AUTO_APPROVED":
                        stats.auto_approved += 1
                    elif action == "DENIED":
                        stats.denied += 1
                    elif action == "DEFERRED":
                        stats.deferred += 1
                    elif action == "TIMEOUT":
                        stats.timeout += 1
                except Exception:  # noqa: BLE001
                    pass

        # Pending requests
        pending_dir = hitl_base / "pending"
        if pending_dir.exists():
            for path in sorted(pending_dir.glob("*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    submitted_at = datetime.fromisoformat(data.get("submitted_at", "1970-01-01"))
                    if not period.contains(submitted_at):
                        continue
                    stats.submitted += 1
                    stats.pending += 1
                except Exception:  # noqa: BLE001
                    pass

        return stats

    # ------------------------------------------------------------------
    # Orchestrator
    # ------------------------------------------------------------------

    def collect_orchestrator(self, period: ReportPeriod) -> OrchestratorStats:
        """
        Parse orchestrator daily pipe-delimited .md files.

        Line format:
            | ts | EVENT_TYPE | run_id | col4 | col5 | ... |
        """
        stats = OrchestratorStats()
        daily_dir = self._logs / "orchestrator" / "daily"
        if not daily_dir.exists():
            return stats

        for date_str in period.date_strings():
            log_file = daily_dir / f"{date_str}-orchestrator.md"
            if not log_file.exists():
                continue
            try:
                for raw in log_file.read_text(encoding="utf-8").splitlines():
                    raw = raw.strip()
                    if not raw.startswith("|"):
                        continue
                    parts = [p.strip() for p in raw.split("|")]
                    # parts[0]="" parts[1]=ts parts[2]=EVENT parts[3]=run_id parts[4+]=vary
                    if len(parts) < 4:
                        continue
                    event = parts[2]

                    if event == "RUN_STARTED":
                        stats.runs_total += 1

                    elif event == "RUN_FINISHED":
                        col4 = parts[4] if len(parts) > 4 else ""
                        if "status=completed" in col4 or "status=success" in col4:
                            stats.runs_success += 1
                        elif "status=failed" in col4 or "status=aborted" in col4:
                            stats.runs_failed += 1
                        else:
                            # Unknown/partial finish — count as success
                            stats.runs_success += 1

                    elif event == "STEP_START":
                        stats.steps_total += 1

                    elif event == "STEP_DONE":
                        # Format: | ts | STEP_DONE | run_id | step_id | status=X | duration |
                        # status is in parts[5], not parts[4] (which is step_id)
                        status_col = parts[5] if len(parts) > 5 else (parts[4] if len(parts) > 4 else "")
                        if "status=failed" in status_col or "status=blocked" in status_col:
                            stats.steps_failed += 1

                    elif event == "STEP_SKIPPED":
                        stats.steps_skipped += 1

                    elif event == "HITL_GATE":
                        stats.hitl_gates += 1

                    elif event == "ERROR":
                        stats.errors += 1

            except Exception:  # noqa: BLE001
                pass

        return stats

    # ------------------------------------------------------------------
    # Watchers
    # ------------------------------------------------------------------

    def collect_watchers(self, period: ReportPeriod) -> list[WatcherStats]:
        """
        Parse per-watcher daily and error .md logs.

        Daily line format:
            | ts | ACTION | events | errors | details |
        """
        watchers_dir = self._logs / "watchers"
        if not watchers_dir.exists():
            return []

        result: dict[str, WatcherStats] = {}

        for watcher_dir in sorted(watchers_dir.iterdir()):
            if not watcher_dir.is_dir():
                continue
            wid = watcher_dir.name
            stats = WatcherStats(watcher_id=wid)

            daily_dir  = watcher_dir / "daily"
            errors_dir = watcher_dir / "errors"

            for date_str in period.date_strings():
                # Daily log
                if daily_dir.exists():
                    log_file = daily_dir / f"{date_str}.md"
                    if log_file.exists():
                        try:
                            for raw in log_file.read_text(encoding="utf-8").splitlines():
                                raw = raw.strip()
                                if not raw.startswith("|"):
                                    continue
                                parts = [p.strip() for p in raw.split("|")]
                                if len(parts) < 4:
                                    continue
                                action     = parts[2]
                                events_col = parts[3]

                                if action == "START":
                                    stats.starts += 1
                                elif action == "POLL":
                                    stats.polls += 1
                                    try:
                                        stats.events += int(events_col)
                                    except ValueError:
                                        pass
                                # EVENT rows are already counted inside POLL
                        except Exception:  # noqa: BLE001
                            pass

                # Error log
                if errors_dir.exists():
                    err_file = errors_dir / f"{date_str}-errors.md"
                    if err_file.exists():
                        try:
                            for raw in err_file.read_text(encoding="utf-8").splitlines():
                                raw = raw.strip()
                                if not raw.startswith("|"):
                                    continue
                                # Skip header row ("| Time | Error |") and separator
                                if "| Time |" in raw or "----" in raw:
                                    continue
                                stats.errors += 1
                        except Exception:  # noqa: BLE001
                            pass

            result[wid] = stats

        return list(result.values())

    # ------------------------------------------------------------------
    # Action skills (JSONL)
    # ------------------------------------------------------------------

    def collect_actions(self, period: ReportPeriod) -> list[ActionStats]:
        """
        Parse JSONL action logs for email, browser, and odoo skills.

        Event types counted:
          "submitted"       → submitted += 1
          "result"          → success / failed / denied by status field
          "queued_for_hitl" → pending_approval += 1
        """
        action_dirs = {
            "email":   self._logs / "email",
            "browser": self._logs / "browser",
            "odoo":    self._logs / "odoo",
        }
        results: list[ActionStats] = []

        for skill_name, log_dir in action_dirs.items():
            stats = ActionStats(skill_name=skill_name)

            if not log_dir.exists():
                results.append(stats)
                continue

            for date_str in period.date_strings():
                jsonl_file = log_dir / f"{date_str}.jsonl"
                if not jsonl_file.exists():
                    continue
                try:
                    for raw in jsonl_file.read_text(encoding="utf-8").splitlines():
                        raw = raw.strip()
                        if not raw:
                            continue
                        try:
                            entry = json.loads(raw)
                        except json.JSONDecodeError:
                            continue

                        event  = entry.get("event", "")
                        status = entry.get("status", "").upper()

                        if event == "submitted":
                            stats.submitted += 1
                        elif event == "result":
                            if status in _SUCCESS_STATUSES:
                                stats.success += 1
                            elif status in _FAILURE_STATUSES:
                                stats.failed += 1
                            elif status in _DENIED_STATUSES:
                                stats.denied += 1
                        elif event == "queued_for_hitl":
                            stats.pending_approval += 1

                except Exception:  # noqa: BLE001
                    pass

            results.append(stats)

        return results

    # ------------------------------------------------------------------
    # Aggregate
    # ------------------------------------------------------------------

    def collect_all(self, period: ReportPeriod) -> WeeklyReport:
        """
        Collect metrics from all log sources and assemble a WeeklyReport.
        """
        hitl         = self.collect_hitl(period)
        orchestrator = self.collect_orchestrator(period)
        watchers     = self.collect_watchers(period)
        actions      = self.collect_actions(period)
        health       = compute_health(hitl, orchestrator, actions)

        return WeeklyReport(
            period=period,
            generated_at=datetime.now(tz=timezone.utc),
            hitl=hitl,
            orchestrator=orchestrator,
            watchers=watchers,
            actions=actions,
            overall_health=health,
        )
