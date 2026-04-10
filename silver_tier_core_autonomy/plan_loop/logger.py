"""
Plan Loop — Logger.

Constitution compliance:
  - Principle II: Explicit Over Implicit (structured log entries)
  - Principle VI: Fail Safe, Fail Visible
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class PlanLogger:
    """Writes plan loop events to vault/70-LOGS/plan-loop/."""

    _LOG_DIR = Path("70-LOGS") / "plan-loop"

    def __init__(self, vault_root: str | Path) -> None:
        self._log_dir = Path(vault_root) / self._LOG_DIR
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def info(self, message: str, context: Optional[dict[str, Any]] = None) -> None:
        self._write("INFO", message, context)

    def warn(self, message: str, context: Optional[dict[str, Any]] = None) -> None:
        self._write("WARN", message, context)

    def error(self, message: str, context: Optional[dict[str, Any]] = None) -> None:
        self._write("ERROR", message, context)

    def log_plan_created(self, plan_id: str, title: str, steps: int, dest: str) -> None:
        self.info(
            f"Plan created: {plan_id}",
            {"title": title, "steps": steps, "dest": dest},
        )

    def log_item_processed(self, source: str, plan_id: str) -> None:
        self.info(f"Inbox item processed → {plan_id}", {"source": source})

    def log_loop_run(self, items_found: int, plans_created: int, errors: int) -> None:
        self.info(
            "Plan loop run complete",
            {"items_found": items_found, "plans_created": plans_created, "errors": errors},
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _write(self, level: str, message: str, context: Optional[dict] = None) -> None:
        entry = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "level": level,
            "agent": "plan-loop",
            "message": message,
            "context": context or {},
        }
        date_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        log_file = self._log_dir / f"{date_str}.jsonl"
        try:
            with log_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:  # noqa: BLE001
            pass  # never crash on logging failure
