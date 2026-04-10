"""
BASE_WATCHER_CREATION_SKILL — Watcher Logger
Append-only vault logging for all watcher activity.

Constitution compliance:
  - Section 7: Logging requirements — timestamp, agent, action, result
  - Principle VI: Fail Safe — logger never raises, prints to stderr on failure
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import WatcherEvent


class WatcherLogger:
    """
    Append-only logger for watcher events and errors.

    Layout::

        70-LOGS/watchers/{watcher_id}/
            daily/  YYYY-MM-DD.md
            errors/ YYYY-MM-DD-errors.md
    """

    _LOG_ROOT = Path("70-LOGS") / "watchers"

    def __init__(self, vault_root: str | Path) -> None:
        self._vault = Path(vault_root)

    # ------------------------------------------------------------------
    # Public log methods
    # ------------------------------------------------------------------

    def log_start(self, watcher_id: str) -> None:
        """Log watcher start."""
        ts = self._ts()
        date = self._date()
        path = self._daily(watcher_id, date)
        self._ensure_daily_header(path, watcher_id, date)
        self._append(path, f"| {ts} | START | - | 0 | Watcher started |")

    def log_stop(self, watcher_id: str) -> None:
        """Log watcher stop."""
        ts = self._ts()
        date = self._date()
        path = self._daily(watcher_id, date)
        self._ensure_daily_header(path, watcher_id, date)
        self._append(path, f"| {ts} | STOP | - | 0 | Watcher stopped |")

    def log_poll(self, watcher_id: str, events_found: int, error_count: int = 0) -> None:
        """Log a completed poll cycle."""
        ts = self._ts()
        date = self._date()
        path = self._daily(watcher_id, date)
        self._ensure_daily_header(path, watcher_id, date)
        self._append(path, f"| {ts} | POLL | {events_found} | {error_count} | Poll cycle complete |")

    def log_event(self, event: "WatcherEvent") -> None:
        """Log a received event (payload NOT logged — only metadata)."""
        ts = event.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        date = event.timestamp.strftime("%Y-%m-%d")
        path = self._daily(event.watcher_id, date)
        self._ensure_daily_header(path, event.watcher_id, date)
        self._append(
            path,
            f"| {ts} | EVENT | 1 | 0 | "
            f"id={event.event_id} type={event.event_type} source={event.source} tier={event.tier} |",
        )

    def log_error(self, watcher_id: str, error: str) -> None:
        """Log an error (never includes secret values)."""
        ts = self._ts()
        date = self._date()
        err_path = self._errors(watcher_id, date)
        self._ensure_error_header(err_path, watcher_id, date)
        self._append(err_path, f"| {ts} | {error[:200]} |")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _daily(self, watcher_id: str, date: str) -> Path:
        d = self._vault / self._LOG_ROOT / watcher_id / "daily"
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{date}.md"

    def _errors(self, watcher_id: str, date: str) -> Path:
        d = self._vault / self._LOG_ROOT / watcher_id / "errors"
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{date}-errors.md"

    def _ensure_daily_header(self, path: Path, watcher_id: str, date: str) -> None:
        if not path.exists():
            try:
                path.write_text(
                    f"# Watcher Log — {watcher_id} — {date}\n\n"
                    "| Time | Action | Events | Errors | Details |\n"
                    "|------|--------|--------|--------|--------|\n",
                    encoding="utf-8",
                )
            except Exception as exc:  # noqa: BLE001
                print(f"[WatcherLogger] header write failed {path}: {exc}", file=sys.stderr)

    def _ensure_error_header(self, path: Path, watcher_id: str, date: str) -> None:
        if not path.exists():
            try:
                path.write_text(
                    f"# Error Log — {watcher_id} — {date}\n\n"
                    "| Time | Error |\n"
                    "|------|-------|\n",
                    encoding="utf-8",
                )
            except Exception as exc:  # noqa: BLE001
                print(f"[WatcherLogger] error header write failed {path}: {exc}", file=sys.stderr)

    def _append(self, path: Path, line: str) -> None:
        try:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except Exception as exc:  # noqa: BLE001
            print(f"[WatcherLogger] append failed {path}: {exc}", file=sys.stderr)

    @staticmethod
    def _ts() -> str:
        return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _date() -> str:
        return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
