"""
ORCHESTRATOR_SYSTEM_SKILL — Logger
Writes structured logs to 70-LOGS/orchestrator/ inside the Obsidian vault.

Constitution compliance:
  - Principle VI: Fail Safe  (never raises on write failure)
  - Principle V:  Memory as Knowledge (all events persisted)
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class OrchestratorLogger:
    """
    Append-only logger for the orchestration engine.

    Log layout inside vault_root::

        70-LOGS/orchestrator/
            daily/      YYYY-MM-DD-orchestrator.md  — chronological event log
            runs/       RUN-<uuid>.md               — per-run summary
            errors/     YYYY-MM-DD-errors.md        — error-only stream
    """

    _LOG_ROOT = Path("70-LOGS") / "orchestrator"

    def __init__(self, vault_root: str | Path) -> None:
        self._vault = Path(vault_root)
        self._daily_dir  = self._vault / self._LOG_ROOT / "daily"
        self._runs_dir   = self._vault / self._LOG_ROOT / "runs"
        self._errors_dir = self._vault / self._LOG_ROOT / "errors"
        for d in (self._daily_dir, self._runs_dir, self._errors_dir):
            d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _now(self) -> datetime:
        return datetime.now(tz=timezone.utc)

    def _date_str(self, dt: Optional[datetime] = None) -> str:
        return (dt or self._now()).strftime("%Y-%m-%d")

    def _ts(self, dt: Optional[datetime] = None) -> str:
        return (dt or self._now()).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _append(self, path: Path, line: str) -> None:
        """Append a line to a log file. Never raises."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except Exception as exc:  # noqa: BLE001
            print(f"[OrchestratorLogger] write failed: {exc}", file=sys.stderr)

    def _daily_path(self) -> Path:
        return self._daily_dir / f"{self._date_str()}-orchestrator.md"

    def _errors_path(self) -> Path:
        return self._errors_dir / f"{self._date_str()}-errors.md"

    def _run_path(self, run_id: str) -> Path:
        return self._runs_dir / f"{run_id}.md"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_run_started(self, run_id: str, workflow_name: str, step_count: int) -> None:
        ts = self._ts()
        line = f"| {ts} | RUN_STARTED | {run_id} | {workflow_name} | steps={step_count} |"
        self._append(self._daily_path(), line)
        self._append(
            self._run_path(run_id),
            f"# {run_id}\n\nWorkflow: **{workflow_name}** — {step_count} steps\nStarted: {ts}\n\n## Events\n",
        )

    def log_run_finished(self, run_id: str, status: str, duration_ms: float) -> None:
        ts = self._ts()
        line = f"| {ts} | RUN_FINISHED | {run_id} | status={status} | duration={duration_ms:.0f}ms |"
        self._append(self._daily_path(), line)
        self._append(self._run_path(run_id), f"- {ts} FINISHED status={status} duration={duration_ms:.0f}ms")

    def log_step_started(self, run_id: str, step_id: str, skill: str, operation: str) -> None:
        ts = self._ts()
        line = f"| {ts} | STEP_START | {run_id} | {step_id} | {skill}.{operation} |"
        self._append(self._daily_path(), line)
        self._append(self._run_path(run_id), f"- {ts} STEP_START {step_id} ({skill}.{operation})")

    def log_step_finished(
        self,
        run_id: str,
        step_id: str,
        status: str,
        duration_ms: float,
        error: Optional[str] = None,
    ) -> None:
        ts = self._ts()
        suffix = f" error={error}" if error else ""
        line = f"| {ts} | STEP_DONE | {run_id} | {step_id} | status={status} | {duration_ms:.0f}ms{suffix} |"
        self._append(self._daily_path(), line)
        self._append(self._run_path(run_id), f"- {ts} STEP_DONE {step_id} status={status}{suffix}")

    def log_hitl_gate(self, run_id: str, step_id: str, request_id: str, tier: int) -> None:
        ts = self._ts()
        line = f"| {ts} | HITL_GATE | {run_id} | {step_id} | tier={tier} | req={request_id} |"
        self._append(self._daily_path(), line)
        self._append(self._run_path(run_id), f"- {ts} HITL_GATE {step_id} tier={tier} req={request_id}")

    def log_step_skipped(self, run_id: str, step_id: str, reason: str) -> None:
        ts = self._ts()
        line = f"| {ts} | STEP_SKIPPED | {run_id} | {step_id} | {reason} |"
        self._append(self._daily_path(), line)
        self._append(self._run_path(run_id), f"- {ts} STEP_SKIPPED {step_id} reason={reason}")

    def log_error(
        self,
        run_id: str,
        step_id: Optional[str],
        message: str,
        exc: Optional[Exception] = None,
    ) -> None:
        ts = self._ts()
        detail = f" [{type(exc).__name__}: {exc}]" if exc else ""
        line = f"| {ts} | ERROR | {run_id} | {step_id or '-'} | {message}{detail} |"
        self._append(self._daily_path(), line)
        self._append(self._errors_path(), line)
        self._append(self._run_path(run_id), f"- {ts} ERROR {message}{detail}")

    def log_info(self, run_id: str, message: str, meta: Optional[dict[str, Any]] = None) -> None:
        ts = self._ts()
        suffix = " " + str(meta) if meta else ""
        line = f"| {ts} | INFO | {run_id} | {message}{suffix} |"
        self._append(self._daily_path(), line)
