"""
Scheduler — Logger.

Constitution compliance:
  - Principle II: Explicit Over Implicit
  - Principle VI: Fail Safe, Fail Visible
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class SchedulerLogger:
    """Writes scheduler events to vault/70-LOGS/scheduler/."""

    _LOG_DIR = Path("70-LOGS") / "scheduler"

    def __init__(self, vault_root: str | Path) -> None:
        self._log_dir = Path(vault_root) / self._LOG_DIR
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def info(self, message: str, context: Optional[dict[str, Any]] = None) -> None:
        self._write("INFO", message, context)

    def warn(self, message: str, context: Optional[dict[str, Any]] = None) -> None:
        self._write("WARN", message, context)

    def error(self, message: str, context: Optional[dict[str, Any]] = None) -> None:
        self._write("ERROR", message, context)

    def log_job_started(self, job_id: str, name: str) -> None:
        self.info(f"Job started: {name}", {"job_id": job_id})

    def log_job_finished(self, job_id: str, status: str, duration_ms: float) -> None:
        self.info(
            f"Job finished: {job_id} [{status}]",
            {"job_id": job_id, "status": status, "duration_ms": round(duration_ms, 2)},
        )

    def log_job_failed(self, job_id: str, error: str, attempt: int) -> None:
        self.error(
            f"Job failed: {job_id} (attempt {attempt})",
            {"job_id": job_id, "error": error, "attempt": attempt},
        )

    def log_tick(self, jobs_due: int, jobs_run: int) -> None:
        self.info("Scheduler tick", {"jobs_due": jobs_due, "jobs_run": jobs_run})

    # ------------------------------------------------------------------

    def _write(self, level: str, message: str, context: Optional[dict] = None) -> None:
        entry = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "level":   level,
            "agent":   "scheduler",
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
