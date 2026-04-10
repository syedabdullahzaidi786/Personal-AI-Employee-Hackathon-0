"""
RALPH_WIGGUM_LOOP_SKILL — Logger
Append-only logs for the loop in 70-LOGS/ralph/.

Constitution compliance:
  - Principle VI: Fail Safe  (never raises on write failure)
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class RalphLogger:
    """
    Structured logger for RALPH_WIGGUM_LOOP_SKILL.

    Layout::

        70-LOGS/ralph/
            daily/   YYYY-MM-DD-ralph.md
            errors/  YYYY-MM-DD-errors.md
            ticks/   TICK-<id>.md
    """

    _LOG_ROOT = Path("70-LOGS") / "ralph"

    def __init__(self, vault_root: str | Path) -> None:
        self._vault      = Path(vault_root)
        self._daily_dir  = self._vault / self._LOG_ROOT / "daily"
        self._errors_dir = self._vault / self._LOG_ROOT / "errors"
        self._ticks_dir  = self._vault / self._LOG_ROOT / "ticks"
        for d in (self._daily_dir, self._errors_dir, self._ticks_dir):
            d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _now(self) -> datetime:
        return datetime.now(tz=timezone.utc)

    def _ts(self) -> str:
        return self._now().strftime("%Y-%m-%dT%H:%M:%SZ")

    def _date(self) -> str:
        return self._now().strftime("%Y-%m-%d")

    def _append(self, path: Path, line: str) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except Exception as exc:  # noqa: BLE001
            print(f"[RalphLogger] write failed: {exc}", file=sys.stderr)

    def _daily(self) -> Path:
        return self._daily_dir / f"{self._date()}-ralph.md"

    def _errors(self) -> Path:
        return self._errors_dir / f"{self._date()}-errors.md"

    def _tick_path(self, tick_id: str) -> Path:
        return self._ticks_dir / f"{tick_id}.md"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_tick_start(self, tick_id: str, tick_number: int) -> None:
        ts = self._ts()
        self._append(self._daily(), f"| {ts} | TICK_START | #{tick_number} {tick_id} |")
        self._append(self._tick_path(tick_id),
                     f"# {tick_id}\n\nTick #{tick_number} started: {ts}\n\n## Events\n")

    def log_tick_end(self, tick_id: str, status: str, duration_ms: float) -> None:
        ts = self._ts()
        self._append(self._daily(),
                     f"| {ts} | TICK_END | {tick_id} | {status} | {duration_ms:.0f}ms |")
        self._append(self._tick_path(tick_id),
                     f"- {ts} FINISHED status={status} {duration_ms:.0f}ms")

    def log_phase_start(self, tick_id: str, phase: str) -> None:
        ts = self._ts()
        self._append(self._daily(), f"| {ts} | PHASE_START | {tick_id} | {phase} |")
        self._append(self._tick_path(tick_id), f"- {ts} PHASE_START {phase}")

    def log_phase_end(self, tick_id: str, phase: str, status: str, duration_ms: float) -> None:
        ts = self._ts()
        self._append(self._daily(),
                     f"| {ts} | PHASE_END | {tick_id} | {phase} | {status} | {duration_ms:.0f}ms |")
        self._append(self._tick_path(tick_id),
                     f"- {ts} PHASE_END {phase} status={status} {duration_ms:.0f}ms")

    def log_task_dispatched(self, tick_id: str, task_id: str, skill: str, op: str) -> None:
        ts = self._ts()
        self._append(self._daily(),
                     f"| {ts} | TASK_DISPATCH | {tick_id} | {task_id} | {skill}.{op} |")

    def log_health(self, tick_id: str, overall: str, healthy: int, total: int) -> None:
        ts = self._ts()
        self._append(self._daily(),
                     f"| {ts} | HEALTH | {tick_id} | {overall} | {healthy}/{total} |")

    def log_error(self, tick_id: Optional[str], message: str, exc: Optional[Exception] = None) -> None:
        ts = self._ts()
        detail = f" [{type(exc).__name__}: {exc}]" if exc else ""
        line = f"| {ts} | ERROR | {tick_id or '-'} | {message}{detail} |"
        self._append(self._daily(), line)
        self._append(self._errors(), line)
        if tick_id:
            self._append(self._tick_path(tick_id), f"- {ts} ERROR {message}{detail}")

    def log_info(self, tick_id: Optional[str], message: str, meta: Optional[dict[str, Any]] = None) -> None:
        ts = self._ts()
        suffix = " " + str(meta) if meta else ""
        self._append(self._daily(), f"| {ts} | INFO | {tick_id or '-'} | {message}{suffix} |")
