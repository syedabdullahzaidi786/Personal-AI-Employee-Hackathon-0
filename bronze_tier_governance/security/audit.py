"""
SECURITY_AND_CREDENTIAL_MANAGEMENT_SKILL — Security Audit Logger
Immutable, append-only audit trail for all credential access events.

Constitution compliance:
  - Section 7: "Audit Trail (Immutable)" — location 70-LOGS/audit/
  - Section 8: "All Tier 3+ actions" must be in audit trail
  - Tier 4 (Critical) — this skill's operations are all audited
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import AuditEntry, CredentialSource, make_audit_entry


class SecurityAuditLogger:
    """
    Append-only security audit logger.

    Layout::

        70-LOGS/security/
            audit/   YYYY-MM-DD-security-audit.md     — human-readable
            jsonl/   YYYY-MM-DD-security-audit.jsonl  — machine-readable
            errors/  YYYY-MM-DD-errors.md
    """

    _LOG_ROOT = Path("70-LOGS") / "security"

    def __init__(self, vault_root: str | Path) -> None:
        self._vault  = Path(vault_root)
        self._audit  = self._vault / self._LOG_ROOT / "audit"
        self._jsonl  = self._vault / self._LOG_ROOT / "jsonl"
        self._errors = self._vault / self._LOG_ROOT / "errors"
        for d in (self._audit, self._jsonl, self._errors):
            d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Event loggers
    # ------------------------------------------------------------------

    def log_access(self, cred_name: str, agent_id: str) -> None:
        """Log a successful credential read."""
        self._write(make_audit_entry("access", agent_id, cred_name, "success",
                                     f"Credential '{cred_name}' read by '{agent_id}'"))

    def log_denied(self, cred_name: str, agent_id: str) -> None:
        """Log a policy-denied access attempt."""
        self._write(make_audit_entry("denied", agent_id, cred_name, "denied",
                                     f"Access to '{cred_name}' denied for '{agent_id}'"))

    def log_load(
        self, cred_name: str, env_key: str, source: CredentialSource = CredentialSource.ENV_VAR
    ) -> None:
        """Log a credential load event (value NOT logged — only env_key name)."""
        self._write(make_audit_entry("load", "system", cred_name, "success",
                                     f"Loaded from {source.value} (key: {env_key})"))

    def log_rotation(self, cred_name: str) -> None:
        """Log a credential rotation event."""
        self._write(make_audit_entry("rotation", "operator", cred_name, "success",
                                     f"Credential '{cred_name}' marked as rotated"))

    def log_scan_finding(
        self, cred_name: str, file_path: str, severity: str, pattern: str
    ) -> None:
        """Log a vault scan finding."""
        self._write(make_audit_entry(
            "scan_finding", "vault_guard", cred_name, "warning",
            f"Pattern '{pattern}' ({severity}) found in {file_path}",
            source_file=file_path,
        ))

    def log_rotation_due(self, cred_name: str, days_overdue: int) -> None:
        """Log a rotation reminder."""
        self._write(make_audit_entry("rotation_due", "system", cred_name, "warning",
                                     f"Credential '{cred_name}' overdue by {days_overdue} days"))

    def log_error(self, cred_name: str, error: str) -> None:
        """Log an error (never includes secret values)."""
        self._write(make_audit_entry("error", "system", cred_name, "error", error))
        ts   = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        path = self._errors / f"{date}-errors.md"
        self._append_line(path, f"| {ts} | {cred_name} | {error[:200]} |")

    def log_policy_change(self, agent_id: str, change_desc: str) -> None:
        """Log a policy modification (always logged at Tier 4)."""
        self._write(make_audit_entry("policy_change", agent_id, "*", "success", change_desc))

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def read_entries(self, date: Optional[str] = None) -> list[AuditEntry]:
        """
        Read audit entries from the JSONL log.

        Parameters
        ----------
        date:
            ``YYYY-MM-DD`` string; defaults to today.
        """
        if date is None:
            date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        path = self._jsonl / f"{date}-security-audit.jsonl"
        if not path.exists():
            return []
        entries = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(AuditEntry.from_dict(json.loads(line)))
            except Exception:  # noqa: BLE001
                pass
        return entries

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _write(self, entry: AuditEntry) -> None:
        try:
            date = entry.timestamp.strftime("%Y-%m-%d")
            ts   = entry.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Human-readable markdown row
            md_path = self._audit / f"{date}-security-audit.md"
            if not md_path.exists():
                md_path.write_text(
                    f"# Security Audit Log — {date}\n\n"
                    "| Time | Event | Agent | Credential | Outcome | Details |\n"
                    "|------|-------|-------|------------|---------|--------|\n",
                    encoding="utf-8",
                )
            md_line = (
                f"| {ts} | {entry.event_type} | {entry.agent_id} "
                f"| {entry.cred_name} | {entry.outcome} | {entry.details[:120]} |"
            )
            self._append_line(md_path, md_line)

            # Machine-readable JSONL
            jsonl_path = self._jsonl / f"{date}-security-audit.jsonl"
            self._append_line(jsonl_path, json.dumps(entry.to_dict()))

        except Exception as exc:  # noqa: BLE001
            print(f"[SecurityAuditLogger] write failed: {exc}", file=sys.stderr)

    def _append_line(self, path: Path, line: str) -> None:
        try:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except Exception as exc:  # noqa: BLE001
            print(f"[SecurityAuditLogger] append failed {path}: {exc}", file=sys.stderr)
