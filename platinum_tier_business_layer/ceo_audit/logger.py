"""
CEO_WEEKLY_AUDIT_SKILL — Audit Logger
Phase 1: Append-only JSONL log under 70-LOGS/business/YYYY-MM-DD.jsonl.

Constitution compliance:
  - Section 7: All skills must log to 70-LOGS/
  - Principle VI: Fail Safe — logger never raises; failures are swallowed
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class AuditSkillLogger:
    """
    Writes append-only JSONL records to 70-LOGS/business/YYYY-MM-DD.jsonl.

    Every public method is non-throwing — logging failures must not
    interrupt the report generation flow.
    """

    def __init__(self, vault_root: str | Path = ".") -> None:
        self._log_dir = Path(vault_root) / "70-LOGS" / "business"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_report_generated(
        self,
        period_slug: str,
        output_paths: list[str],
        health: str,
    ) -> None:
        self._append({
            "event":        "report_generated",
            "period":       period_slug,
            "output_paths": output_paths,
            "health":       health,
            "ts":           self._now(),
        })

    def log_error(self, error: str) -> None:
        self._append({
            "event": "error",
            "error": error,
            "ts":    self._now(),
        })

    def read_entries(self, date: Optional[str] = None) -> list[dict]:
        """Read log entries for a given date (YYYY-MM-DD). Default: today."""
        date = date or datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        log_file = self._log_dir / f"{date}.jsonl"
        if not log_file.exists():
            return []
        entries: list[dict] = []
        for line in log_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return entries

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _now(self) -> str:
        return datetime.now(tz=timezone.utc).isoformat()

    def _append(self, record: dict) -> None:
        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            date     = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
            log_file = self._log_dir / f"{date}.jsonl"
            with log_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:  # noqa: BLE001
            pass  # Logging failures are non-fatal
