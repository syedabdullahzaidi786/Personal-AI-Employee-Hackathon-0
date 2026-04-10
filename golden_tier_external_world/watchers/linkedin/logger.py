"""
LinkedIn Watcher — Logger.

Constitution compliance:
  - Principle II: Explicit Over Implicit
  - Principle VI: Fail Safe, Fail Visible
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class LinkedInWatcherLogger:
    """Writes LinkedIn watcher events to vault/70-LOGS/watchers/linkedin/."""

    _LOG_DIR = Path("70-LOGS") / "watchers" / "linkedin"

    def __init__(self, vault_root: str | Path) -> None:
        self._log_dir = Path(vault_root) / self._LOG_DIR
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def info(self, message: str, context: Optional[dict[str, Any]] = None) -> None:
        self._write("INFO", message, context)

    def warn(self, message: str, context: Optional[dict[str, Any]] = None) -> None:
        self._write("WARN", message, context)

    def error(self, message: str, context: Optional[dict[str, Any]] = None) -> None:
        self._write("ERROR", message, context)

    def log_poll(self, new_count: int, total_seen: int) -> None:
        self.info(
            f"LinkedIn poll complete — {new_count} new event(s)",
            {"new_count": new_count, "total_seen": total_seen},
        )

    def log_event(self, activity_id: str, event_type: str) -> None:
        self.info(
            f"New LinkedIn event: {event_type}",
            {"activity_id": activity_id, "event_type": event_type},
        )

    # ------------------------------------------------------------------

    def _write(self, level: str, message: str, context: Optional[dict] = None) -> None:
        entry = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "level":   level,
            "agent":   "linkedin-watcher",
            "message": message,
            "context": context or {},
        }
        date_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        log_file = self._log_dir / f"{date_str}.jsonl"
        try:
            with log_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:  # noqa: BLE001
            pass
