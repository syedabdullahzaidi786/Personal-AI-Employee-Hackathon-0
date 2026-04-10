"""
BASE_WATCHER_CREATION_SKILL — BaseWatcher Abstract Class
Defines the contract all concrete watchers must implement.

Constitution compliance:
  - Section 9: Skill Anatomy — single responsibility, observable, testable
  - Principle II: Explicit Over Implicit — start/stop/tick fully logged
  - Principle VI: Fail Safe — tick() never raises; health failures short-circuit poll
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from .logger import WatcherLogger
from .models import (
    WatcherConfig,
    WatcherEvent,
    WatcherState,
    WatcherStatus,
    WatcherTickResult,
)
from .store import EventStore

if TYPE_CHECKING:
    from .dispatcher import EventDispatcher


_STATE_SUBPATH = Path("70-LOGS") / "watchers"


class BaseWatcher(ABC):
    """
    Abstract base class for all watchers.

    Concrete subclasses must implement:
      - :meth:`poll`          — check the source for new events
      - :meth:`health_check`  — verify the source is reachable

    The framework provides:
      - :meth:`tick`     — one full poll cycle (health → poll → store → dispatch)
      - :meth:`start`    — set status RUNNING, log start
      - :meth:`stop`     — set status STOPPED, log stop
      - :meth:`is_running` — check current status

    Usage (concrete subclass)::

        class FileWatcher(BaseWatcher):
            def poll(self) -> list[WatcherEvent]:
                # Check watched directory for new files
                ...
            def health_check(self) -> bool:
                return self._watch_dir.exists()

        config = WatcherConfig(watcher_id="fs-watcher", watcher_type="filesystem",
                               vault_root="/vault")
        watcher = FileWatcher(config)
        watcher.start()
        result = watcher.tick()
    """

    def __init__(self, config: WatcherConfig) -> None:
        self._config  = config
        vault         = Path(config.vault_root) if config.vault_root else Path(".")
        self._logger  = WatcherLogger(vault)
        self._store   = EventStore(vault)
        self._state   = self._load_state(vault)

    # ------------------------------------------------------------------
    # Abstract interface (subclasses must implement)
    # ------------------------------------------------------------------

    @abstractmethod
    def poll(self) -> list[WatcherEvent]:
        """
        Check the event source and return any new events.

        Must never raise — raise internal exceptions; let tick() handle them.
        Events must NOT contain credentials or secrets in their payload.
        """

    @abstractmethod
    def health_check(self) -> bool:
        """
        Verify the event source is reachable / healthy.

        Return True if the source is available, False otherwise.
        Must never raise.
        """

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Mark watcher as RUNNING and log the start event."""
        self._state.status     = WatcherStatus.RUNNING
        self._state.started_at = datetime.now(tz=timezone.utc)
        self._logger.log_start(self._config.watcher_id)
        self._save_state()

    def stop(self) -> None:
        """Mark watcher as STOPPED and log the stop event."""
        self._state.status     = WatcherStatus.STOPPED
        self._state.stopped_at = datetime.now(tz=timezone.utc)
        self._logger.log_stop(self._config.watcher_id)
        self._save_state()

    def pause(self) -> None:
        """Mark watcher as PAUSED."""
        self._state.status = WatcherStatus.PAUSED
        self._save_state()

    def is_running(self) -> bool:
        """Return True if status is RUNNING."""
        return self._state.status == WatcherStatus.RUNNING

    # ------------------------------------------------------------------
    # Tick (one poll cycle)
    # ------------------------------------------------------------------

    def tick(self, dispatcher: Optional["EventDispatcher"] = None) -> WatcherTickResult:
        """
        Execute one full poll cycle.

        Phases:
          1. health_check()  — if fails, return early tick result
          2. poll()          — collect new events
          3. store events    — write each to EventStore
          4. dispatch events — route via EventDispatcher (or count only)
          5. update state    — consecutive_errors, last_poll_at

        Never raises. All exceptions are captured in WatcherTickResult.
        """
        started       = datetime.now(tz=timezone.utc)
        events_found  = 0
        events_disp   = 0
        errors        = 0
        error_msg: Optional[str] = None

        self._state.poll_count  += 1
        self._state.last_poll_at = started

        # Phase 1 — Health check
        health_ok = False
        try:
            health_ok = self.health_check()
        except Exception as exc:  # noqa: BLE001
            health_ok = False
            error_msg = f"health_check raised: {exc}"

        if not health_ok:
            errors += 1
            msg = error_msg or "health_check returned False"
            self._logger.log_error(self._config.watcher_id, msg)
            self._state.consecutive_errors += 1
            self._state.error_count        += 1
            self._state.status              = WatcherStatus.ERROR
            self._save_state()
            return WatcherTickResult(
                watcher_id=self._config.watcher_id,
                poll_count=self._state.poll_count,
                events_found=0,
                events_dispatched=0,
                errors=errors,
                health_ok=False,
                duration_ms=self._elapsed_ms(started),
                error_message=msg,
            )

        # Health OK — reset error streak
        self._state.consecutive_errors = 0

        # Phase 2 — Poll
        events: list[WatcherEvent] = []
        try:
            events      = self.poll()
            events_found = len(events)
        except Exception as exc:  # noqa: BLE001
            error_msg = f"poll raised: {exc}"
            errors    += 1
            self._logger.log_error(self._config.watcher_id, error_msg)
            self._state.error_count        += 1
            self._state.consecutive_errors += 1

        # Phase 3 & 4 — Store + Dispatch
        for event in events:
            self._logger.log_event(event)
            try:
                self._store.save(event)
            except Exception as exc:  # noqa: BLE001
                errors += 1
                self._logger.log_error(self._config.watcher_id, f"store.save failed: {exc}")

            if dispatcher is not None:
                try:
                    result = dispatcher.dispatch(event)
                    if result.dispatched:
                        events_disp += 1
                except Exception as exc:  # noqa: BLE001
                    errors += 1
                    self._logger.log_error(
                        self._config.watcher_id, f"dispatch failed: {exc}"
                    )
            else:
                # No dispatcher — count as dispatched for tick result
                events_disp += 1

        # Update state
        if events_found > 0:
            self._state.last_event_at = datetime.now(tz=timezone.utc)
        self._state.total_events += events_found
        if errors == 0:
            self._state.consecutive_errors = 0

        self._logger.log_poll(self._config.watcher_id, events_found, errors)
        self._save_state()

        return WatcherTickResult(
            watcher_id=self._config.watcher_id,
            poll_count=self._state.poll_count,
            events_found=events_found,
            events_dispatched=events_disp,
            errors=errors,
            health_ok=True,
            duration_ms=self._elapsed_ms(started),
            error_message=error_msg,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def config(self) -> WatcherConfig:
        return self._config

    @property
    def state(self) -> WatcherState:
        return self._state

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _state_path(self, vault: Path) -> Path:
        d = vault / _STATE_SUBPATH / self._config.watcher_id
        d.mkdir(parents=True, exist_ok=True)
        return d / "state.json"

    def _load_state(self, vault: Path) -> WatcherState:
        path = self._state_path(vault)
        if path.exists():
            try:
                return WatcherState.from_dict(json.loads(path.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001
                pass
        return WatcherState(watcher_id=self._config.watcher_id)

    def _save_state(self) -> None:
        try:
            vault = Path(self._config.vault_root) if self._config.vault_root else Path(".")
            path  = self._state_path(vault)
            path.write_text(json.dumps(self._state.to_dict(), indent=2), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            self._logger.log_error(self._config.watcher_id, f"state save failed: {exc}")

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    @staticmethod
    def _elapsed_ms(started: datetime) -> float:
        return (datetime.now(tz=timezone.utc) - started).total_seconds() * 1000
