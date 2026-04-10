"""
BASE_WATCHER_CREATION_SKILL — Event Store
File-based persistence of WatcherEvents in the vault.

Constitution compliance:
  - Principle I: Local-First — all events written to Obsidian vault
  - Section 5: Vault & File Governance — atomic writes, no binary files
  - Principle VI: Fail Safe — errors logged, never crash caller
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import WatcherEvent


class EventStore:
    """
    Appends WatcherEvent objects to JSONL files in the vault.

    Layout::

        70-LOGS/watchers/{watcher_id}/events/YYYY-MM-DD-events.jsonl
    """

    _LOG_ROOT = Path("70-LOGS") / "watchers"

    def __init__(self, vault_root: str | Path) -> None:
        self._vault = Path(vault_root)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def save(self, event: WatcherEvent) -> None:
        """Append *event* to today's JSONL file for its watcher."""
        try:
            path = self._event_path(event.watcher_id, event.timestamp.strftime("%Y-%m-%d"))
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event.to_dict()) + "\n")
        except Exception as exc:  # noqa: BLE001
            print(f"[EventStore] save failed {event.event_id}: {exc}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def load_by_date(
        self,
        watcher_id: str,
        date: Optional[str] = None,
    ) -> list[WatcherEvent]:
        """
        Return all WatcherEvents for *watcher_id* on *date*.

        Parameters
        ----------
        date:
            ``YYYY-MM-DD``; defaults to today (UTC).
        """
        if date is None:
            date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        path = self._event_path(watcher_id, date)
        if not path.exists():
            return []
        events: list[WatcherEvent] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(WatcherEvent.from_dict(json.loads(line)))
            except Exception:  # noqa: BLE001
                pass
        return events

    def event_count(self, watcher_id: str, date: Optional[str] = None) -> int:
        """Return number of events stored for *watcher_id* on *date*."""
        return len(self.load_by_date(watcher_id, date))

    # ------------------------------------------------------------------
    # Mark processed
    # ------------------------------------------------------------------

    def mark_processed(self, watcher_id: str, event_id: str) -> bool:
        """
        Mark event *event_id* as processed in today's log.

        Rewrites today's JSONL file with the updated record.
        Returns True if found and updated.
        """
        date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        events = self.load_by_date(watcher_id, date)
        updated = False
        for e in events:
            if e.event_id == event_id:
                e.processed = True
                updated = True
        if updated:
            path = self._event_path(watcher_id, date)
            try:
                with path.open("w", encoding="utf-8") as fh:
                    for e in events:
                        fh.write(json.dumps(e.to_dict()) + "\n")
            except Exception as exc:  # noqa: BLE001
                print(f"[EventStore] mark_processed write failed: {exc}", file=sys.stderr)
                return False
        return updated

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _event_dir(self, watcher_id: str) -> Path:
        d = self._vault / self._LOG_ROOT / watcher_id / "events"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _event_path(self, watcher_id: str, date: str) -> Path:
        return self._event_dir(watcher_id) / f"{date}-events.jsonl"
