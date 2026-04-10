"""
HUMAN_IN_THE_LOOP_APPROVAL_SKILL — Pending Queue Store
Phase 1: File-based request persistence inside 70-LOGS/hitl/.

Pending  → obsidian-vault/70-LOGS/hitl/pending/{request_id}.json
Completed→ obsidian-vault/70-LOGS/hitl/completed/{request_id}.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .models import ApprovalRequest, Decision


class RequestStore:
    """
    Manages approval request lifecycle on disk.

    Structure:
        vault/70-LOGS/hitl/
          pending/    — requests awaiting decision
          completed/  — decided requests (immutable after write)
    """

    def __init__(self, vault_root: str | Path) -> None:
        base = Path(vault_root) / "70-LOGS" / "hitl"
        self._pending_dir   = base / "pending"
        self._completed_dir = base / "completed"
        self._pending_dir.mkdir(parents=True, exist_ok=True)
        self._completed_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def save_pending(self, request: ApprovalRequest) -> None:
        """Persist a pending request to disk."""
        path = self._pending_dir / f"{request.request_id}.json"
        self._write_json(path, request.to_dict())

    def move_to_completed(self, request: ApprovalRequest) -> None:
        """
        Move a decided request from pending to completed.
        The completed file is written first, then the pending file removed.
        """
        completed_path = self._completed_dir / f"{request.request_id}.json"
        self._write_json(completed_path, request.to_dict())

        pending_path = self._pending_dir / f"{request.request_id}.json"
        pending_path.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, request_id: str) -> Optional[ApprovalRequest]:
        """Load request by ID from pending or completed store."""
        for directory in (self._pending_dir, self._completed_dir):
            path = directory / f"{request_id}.json"
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                return ApprovalRequest.from_dict(data)
        return None

    def list_pending(
        self,
        agent_id: Optional[str] = None,
        tier: Optional[int] = None,
    ) -> list[ApprovalRequest]:
        """Return all pending requests, optionally filtered."""
        results = []
        for path in sorted(self._pending_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                req = ApprovalRequest.from_dict(data)
                if req.status != Decision.PENDING:
                    continue
                if agent_id and req.agent_id != agent_id:
                    continue
                if tier is not None and req.tier != tier:
                    continue
                results.append(req)
            except (json.JSONDecodeError, KeyError):
                pass  # Skip corrupted files
        return results

    def list_completed(
        self,
        status: Optional[str] = None,
    ) -> list[ApprovalRequest]:
        """Return all completed requests, optionally filtered by status."""
        results = []
        for path in sorted(self._completed_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                req = ApprovalRequest.from_dict(data)
                if status and req.status != status:
                    continue
                results.append(req)
            except (json.JSONDecodeError, KeyError):
                pass
        return results

    def exists(self, request_id: str) -> bool:
        return (
            (self._pending_dir / f"{request_id}.json").exists()
            or (self._completed_dir / f"{request_id}.json").exists()
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _write_json(path: Path, data: dict) -> None:
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
