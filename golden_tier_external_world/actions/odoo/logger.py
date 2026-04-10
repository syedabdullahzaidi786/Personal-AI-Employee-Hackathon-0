"""
ODOO_MCP_INTEGRATION_SKILL — Audit Logger
Phase 1: Append-only JSONL log under 70-LOGS/odoo/YYYY-MM-DD.jsonl.

Constitution compliance:
  - Section 7: All skills must log to 70-LOGS/
  - Principle VI: Fail Safe — logger never raises; failures are swallowed
  - Section 8: No secrets in logs — OdooResult carries no credentials
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import OdooRequest, OdooResult


class OdooLogger:
    """
    Writes append-only JSONL records to 70-LOGS/odoo/YYYY-MM-DD.jsonl.

    Every public method is non-throwing — logging failures must not
    interrupt the Odoo operation flow.
    """

    def __init__(self, vault_root: str | Path = ".") -> None:
        self._vault   = Path(vault_root)
        self._log_dir = self._vault / "70-LOGS" / "odoo"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_submitted(self, request: OdooRequest) -> None:
        self._append({
            "event":      "submitted",
            "request_id": request.request_id,
            "operation":  request.operation,
            "model":      request.model,
            "record_id":  request.record_id,
            "tier":       request.tier,
            "ts":         self._now(),
        })

    def log_queued_for_hitl(self, request: OdooRequest, hitl_request_id: str) -> None:
        self._append({
            "event":           "queued_for_hitl",
            "request_id":      request.request_id,
            "hitl_request_id": hitl_request_id,
            "operation":       request.operation,
            "model":           request.model,
            "tier":            request.tier,
            "ts":              self._now(),
        })

    def log_result(self, result: OdooResult) -> None:
        self._append({
            "event":      "result",
            "request_id": result.request_id,
            "operation":  result.operation,
            "status":     result.status,
            "model":      result.model,
            "record_id":  result.record_id,
            "adapter":    result.adapter,
            "error":      result.error,
            "ts":         self._now(),
        })

    def log_denied(self, request_id: str, reason: str = "") -> None:
        self._append({
            "event":      "denied",
            "request_id": request_id,
            "reason":     reason,
            "ts":         self._now(),
        })

    def log_error(self, request_id: str, error: str) -> None:
        self._append({
            "event":      "error",
            "request_id": request_id,
            "error":      error,
            "ts":         self._now(),
        })

    def read_entries(self, date: Optional[str] = None) -> list[dict]:
        """Read log entries for a given date (YYYY-MM-DD). Default: today."""
        date     = date or datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        log_file = self._log_dir / f"{date}.jsonl"
        if not log_file.exists():
            return []
        entries = []
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
