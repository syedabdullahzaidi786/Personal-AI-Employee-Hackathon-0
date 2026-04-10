"""
RALPH_WIGGUM_LOOP_SKILL — Task Queue
File-based queue for tasks the loop should dispatch.

Layout inside vault_root::

    70-LOGS/ralph/queue/
        pending/    TASK-<id>.json    — waiting to run
        processing/ TASK-<id>.json    — currently running
        done/       TASK-<id>.json    — finished
        failed/     TASK-<id>.json    — errored
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import TaskEntry, TaskPriority, TaskStatus


class TaskQueue:
    """
    Persistent task queue using the filesystem.

    Tasks move through states: pending → processing → done | failed.
    """

    _QUEUE_ROOT = Path("70-LOGS") / "ralph" / "queue"

    def __init__(self, vault_root: str | Path) -> None:
        self._vault = Path(vault_root)
        self._dirs = {
            TaskStatus.PENDING:    self._vault / self._QUEUE_ROOT / "pending",
            TaskStatus.PROCESSING: self._vault / self._QUEUE_ROOT / "processing",
            TaskStatus.DONE:       self._vault / self._QUEUE_ROOT / "done",
            TaskStatus.FAILED:     self._vault / self._QUEUE_ROOT / "failed",
        }
        for d in self._dirs.values():
            d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def enqueue(self, task: TaskEntry) -> TaskEntry:
        """Add a task to the pending queue."""
        task.status = TaskStatus.PENDING
        if task.submitted_at is None:
            task.submitted_at = datetime.now(tz=timezone.utc)
        self._write(task, TaskStatus.PENDING)
        return task

    def start(self, task_id: str) -> Optional[TaskEntry]:
        """Move task from pending → processing."""
        task = self._load_from(task_id, TaskStatus.PENDING)
        if task is None:
            return None
        task.status     = TaskStatus.PROCESSING
        task.started_at = datetime.now(tz=timezone.utc)
        self._move(task, TaskStatus.PENDING, TaskStatus.PROCESSING)
        return task

    def complete(self, task_id: str, result: Optional[dict] = None) -> Optional[TaskEntry]:
        """Move task from processing → done."""
        task = self._load_from(task_id, TaskStatus.PROCESSING)
        if task is None:
            return None
        task.status      = TaskStatus.DONE
        task.finished_at = datetime.now(tz=timezone.utc)
        task.result      = result
        self._move(task, TaskStatus.PROCESSING, TaskStatus.DONE)
        return task

    def fail(self, task_id: str, error: str) -> Optional[TaskEntry]:
        """Move task from processing → failed."""
        task = self._load_from(task_id, TaskStatus.PROCESSING)
        if task is None:
            # Also try from pending (e.g. failed before start)
            task = self._load_from(task_id, TaskStatus.PENDING)
            if task is None:
                return None
            src = TaskStatus.PENDING
        else:
            src = TaskStatus.PROCESSING
        task.status      = TaskStatus.FAILED
        task.finished_at = datetime.now(tz=timezone.utc)
        task.error       = error
        self._move(task, src, TaskStatus.FAILED)
        return task

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def list_pending(
        self,
        priority: Optional[TaskPriority] = None,
        limit: int = 100,
    ) -> list[TaskEntry]:
        """Return pending tasks sorted by priority then submission time."""
        tasks = self._load_all(TaskStatus.PENDING)
        if priority is not None:
            tasks = [t for t in tasks if t.priority == priority]
        tasks.sort(key=lambda t: (t.priority.value, t.submitted_at or datetime.min))
        return tasks[:limit]

    def list_processing(self) -> list[TaskEntry]:
        return self._load_all(TaskStatus.PROCESSING)

    def list_done(self, limit: int = 50) -> list[TaskEntry]:
        tasks = self._load_all(TaskStatus.DONE)
        tasks.sort(key=lambda t: t.finished_at or datetime.min, reverse=True)
        return tasks[:limit]

    def list_failed(self, limit: int = 50) -> list[TaskEntry]:
        tasks = self._load_all(TaskStatus.FAILED)
        tasks.sort(key=lambda t: t.finished_at or datetime.min, reverse=True)
        return tasks[:limit]

    def get(self, task_id: str) -> Optional[TaskEntry]:
        """Find task in any state."""
        for status in TaskStatus:
            task = self._load_from(task_id, status)
            if task is not None:
                return task
        return None

    def pending_count(self) -> int:
        return len(list(self._dirs[TaskStatus.PENDING].glob("*.json")))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _path(self, task_id: str, status: TaskStatus) -> Path:
        return self._dirs[status] / f"{task_id}.json"

    def _write(self, task: TaskEntry, status: TaskStatus) -> None:
        path = self._path(task.task_id, status)
        path.write_text(json.dumps(task.to_dict(), indent=2), encoding="utf-8")

    def _load_from(self, task_id: str, status: TaskStatus) -> Optional[TaskEntry]:
        path = self._path(task_id, status)
        if not path.exists():
            return None
        try:
            return TaskEntry.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            return None

    def _move(self, task: TaskEntry, src: TaskStatus, dst: TaskStatus) -> None:
        old = self._path(task.task_id, src)
        self._write(task, dst)
        if old.exists():
            old.unlink()

    def _load_all(self, status: TaskStatus) -> list[TaskEntry]:
        tasks = []
        for f in self._dirs[status].glob("*.json"):
            try:
                tasks.append(TaskEntry.from_dict(json.loads(f.read_text(encoding="utf-8"))))
            except Exception:  # noqa: BLE001
                pass
        return tasks
