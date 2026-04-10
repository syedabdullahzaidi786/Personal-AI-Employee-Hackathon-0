"""
ORCHESTRATOR_SYSTEM_SKILL — Run Store
File-based persistence for WorkflowRun objects.

Layout inside vault_root::

    70-LOGS/orchestrator/runs/
        active/     RUN-<uuid>.json   — currently running/waiting
        completed/  RUN-<uuid>.json   — finished runs
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .models import WorkflowRun, WorkflowStatus


class RunStore:
    """Persists WorkflowRun objects as JSON files."""

    _STORE_ROOT = Path("70-LOGS") / "orchestrator" / "runs"

    def __init__(self, vault_root: str | Path) -> None:
        self._vault    = Path(vault_root)
        self._active   = self._vault / self._STORE_ROOT / "active"
        self._completed = self._vault / self._STORE_ROOT / "completed"
        self._active.mkdir(parents=True, exist_ok=True)
        self._completed.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------

    def save(self, run: WorkflowRun) -> None:
        """Persist *run* to the appropriate directory."""
        terminal = {WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.ABORTED}
        directory = self._completed if run.status in terminal else self._active
        path = directory / f"{run.run_id}.json"
        path.write_text(json.dumps(run.to_dict(), indent=2), encoding="utf-8")

        # Remove from active if now completed
        if run.status in terminal:
            active_path = self._active / f"{run.run_id}.json"
            if active_path.exists():
                active_path.unlink()

    def get(self, run_id: str) -> Optional[WorkflowRun]:
        """Load a run by ID, searching both active and completed."""
        for directory in (self._active, self._completed):
            path = directory / f"{run_id}.json"
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                return WorkflowRun.from_dict(data)
        return None

    def list_active(self) -> list[WorkflowRun]:
        return self._load_all(self._active)

    def list_completed(self) -> list[WorkflowRun]:
        return self._load_all(self._completed)

    def list_all(self) -> list[WorkflowRun]:
        return self.list_active() + self.list_completed()

    # ------------------------------------------------------------------

    def _load_all(self, directory: Path) -> list[WorkflowRun]:
        runs = []
        for f in sorted(directory.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                runs.append(WorkflowRun.from_dict(data))
            except Exception:  # noqa: BLE001
                pass
        return runs
