"""
LinkedIn Post Action — Logger.

Constitution compliance:
  - Principle II: Explicit Over Implicit
  - Principle VI: Fail Safe, Fail Visible
  - Section 7:    Audit logging for all Tier 2+ actions
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class LinkedInPostLogger:
    """Logs LinkedIn post activity to vault/70-LOGS/actions/linkedin/."""

    _LOG_DIR   = Path("70-LOGS") / "actions" / "linkedin"
    _AUDIT_DIR = Path("70-LOGS") / "audit"

    def __init__(self, vault_root: str | Path) -> None:
        self._vault    = Path(vault_root)
        self._log_dir  = self._vault / self._LOG_DIR
        self._audit_dir = self._vault / self._AUDIT_DIR
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._audit_dir.mkdir(parents=True, exist_ok=True)

    def info(self, message: str, context: Optional[dict[str, Any]] = None) -> None:
        self._write("INFO", message, context)

    def warn(self, message: str, context: Optional[dict[str, Any]] = None) -> None:
        self._write("WARN", message, context)

    def error(self, message: str, context: Optional[dict[str, Any]] = None) -> None:
        self._write("ERROR", message, context)

    def log_post_draft(self, post_id: str, content_preview: str) -> None:
        self.info(
            f"LinkedIn post drafted: {post_id}",
            {"post_id": post_id, "preview": content_preview[:100]},
        )

    def log_post_submitted(self, post_id: str) -> None:
        self.info(f"LinkedIn post submitted for approval: {post_id}", {"post_id": post_id})

    def log_post_approved(self, post_id: str) -> None:
        self.info(f"LinkedIn post approved: {post_id}", {"post_id": post_id})

    def log_post_published(self, post_id: str, linkedin_id: str) -> None:
        self.info(
            f"LinkedIn post published: {post_id}",
            {"post_id": post_id, "linkedin_post_id": linkedin_id},
        )
        # Also write to audit log (Tier 2 external action)
        self._audit("linkedin_post_published", {
            "post_id": post_id,
            "linkedin_post_id": linkedin_id,
        })

    def log_post_failed(self, post_id: str, error: str) -> None:
        self.error(f"LinkedIn post failed: {post_id}", {"post_id": post_id, "error": error})

    # ------------------------------------------------------------------

    def _write(self, level: str, message: str, context: Optional[dict] = None) -> None:
        entry = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "level":   level,
            "agent":   "linkedin-poster",
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

    def _audit(self, action: str, context: dict) -> None:
        entry = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "level":   "AUDIT",
            "agent":   "linkedin-poster",
            "action":  action,
            "context": context,
        }
        date_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        audit_file = self._audit_dir / f"{date_str}-linkedin.jsonl"
        try:
            with audit_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:  # noqa: BLE001
            pass
