"""
BASE_WATCHER_CREATION_SKILL — Phase 1
Event-driven monitoring framework for the Personal AI Employee system.

Constitution compliance:
  - Section 9: Skill Design Rules (atomic, composable, testable)
  - Section 3: HITL by Default (Tier 2 events routed via EventDispatcher)
  - Principle I: Local-First (all events persisted to Obsidian vault)

Public surface::

    from skills.watchers.base import WatcherSkill, BaseWatcher, WatcherConfig, make_event

    # 1. Implement a concrete watcher
    class FileWatcher(BaseWatcher):
        def poll(self):
            events = []
            for f in self._watch_dir.glob("*.md"):
                if f.stat().st_mtime > self._last_mtime:
                    events.append(make_event(
                        self.config.watcher_id, "file_created",
                        f"filesystem:{f.name}", {"path": str(f)}, tier=1,
                    ))
            return events

        def health_check(self):
            return self._watch_dir.exists()

    # 2. Register and run
    config = WatcherConfig(watcher_id="vault-fs", watcher_type="filesystem",
                           vault_root="/path/to/vault")
    skill  = WatcherSkill(vault_root="/path/to/vault")
    skill.register_watcher(FileWatcher(config))
    skill.register_handler("file_created", lambda e: print("New file:", e.payload))

    skill.start_watcher("vault-fs")
    result = skill.tick_watcher("vault-fs")
    print(result.events_found)
"""

from pathlib import Path
from typing import Any, Callable, Optional

from .base import BaseWatcher
from .dispatcher import EventDispatcher
from .logger import WatcherLogger
from .models import (
    DispatchResult,
    EventType,
    WatcherConfig,
    WatcherEvent,
    WatcherState,
    WatcherStatus,
    WatcherTickResult,
    make_event,
)
from .registry import WatcherNotFoundError, WatcherRegistry
from .store import EventStore


class WatcherSkill:
    """
    High-level facade for BASE_WATCHER_CREATION_SKILL Phase 1.

    Composes: WatcherRegistry + EventDispatcher + EventStore + WatcherLogger.
    """

    def __init__(self, vault_root: str | Path) -> None:
        vault              = Path(vault_root)
        self._vault        = vault
        self._registry     = WatcherRegistry()
        self._dispatcher   = EventDispatcher()
        self._store        = EventStore(vault)
        self._logger       = WatcherLogger(vault)

    # ------------------------------------------------------------------
    # Watcher registration
    # ------------------------------------------------------------------

    def register_watcher(self, watcher: BaseWatcher) -> None:
        """Register a concrete watcher instance."""
        self._registry.register(watcher)

    def unregister_watcher(self, watcher_id: str) -> bool:
        """Remove a watcher from the registry. Returns True if it existed."""
        return self._registry.unregister(watcher_id)

    def list_watchers(self) -> list[str]:
        """Return list of registered watcher IDs."""
        return self._registry.list_ids()

    # ------------------------------------------------------------------
    # HITL + handler wiring
    # ------------------------------------------------------------------

    def set_hitl(self, hitl_skill: Any) -> None:
        """Attach HITLSkill for Tier 2+ event routing."""
        self._dispatcher.set_hitl(hitl_skill)

    def register_handler(self, event_type: str, handler: Callable[[WatcherEvent], Any]) -> None:
        """Register an event handler. Use ``"*"`` to catch all event types."""
        self._dispatcher.register_handler(event_type, handler)

    def unregister_handler(self, event_type: str) -> None:
        """Remove handlers for *event_type*."""
        self._dispatcher.unregister_handler(event_type)

    # ------------------------------------------------------------------
    # Tick operations
    # ------------------------------------------------------------------

    def tick_watcher(self, watcher_id: str) -> WatcherTickResult:
        """Run one poll cycle for a specific watcher."""
        watcher = self._registry.require(watcher_id)
        return watcher.tick(self._dispatcher)

    def tick_all(self) -> dict[str, WatcherTickResult]:
        """
        Run one poll cycle for every registered watcher.

        Returns {watcher_id: WatcherTickResult}. Never raises — error watchers
        produce an error-flagged WatcherTickResult.
        """
        results: dict[str, WatcherTickResult] = {}
        for watcher in self._registry.list_all():
            wid = watcher.config.watcher_id
            try:
                results[wid] = watcher.tick(self._dispatcher)
            except Exception as exc:  # noqa: BLE001
                results[wid] = WatcherTickResult(
                    watcher_id=wid,
                    poll_count=0,
                    events_found=0,
                    events_dispatched=0,
                    errors=1,
                    health_ok=False,
                    duration_ms=0.0,
                    error_message=str(exc),
                )
        return results

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_watcher(self, watcher_id: str) -> None:
        """Mark watcher as RUNNING."""
        self._registry.require(watcher_id).start()

    def stop_watcher(self, watcher_id: str) -> None:
        """Mark watcher as STOPPED."""
        self._registry.require(watcher_id).stop()

    # ------------------------------------------------------------------
    # Event retrieval
    # ------------------------------------------------------------------

    def get_events(self, watcher_id: str, date: Optional[str] = None) -> list[WatcherEvent]:
        """Return stored events for *watcher_id* on *date* (default: today)."""
        return self._store.load_by_date(watcher_id, date)

    # ------------------------------------------------------------------
    # Status / introspection
    # ------------------------------------------------------------------

    def status_all(self) -> list[dict]:
        """Return safe status dicts for all registered watchers."""
        return [
            watcher.state.to_dict()
            for watcher in self._registry.list_all()
        ]

    def is_running(self, watcher_id: str) -> bool:
        """Return True if *watcher_id* is in RUNNING state."""
        w = self._registry.get(watcher_id)
        return w.is_running() if w else False


__all__ = [
    "WatcherSkill",
    "BaseWatcher",
    "WatcherRegistry",
    "EventDispatcher",
    "EventStore",
    "WatcherLogger",
    # Models
    "WatcherConfig",
    "WatcherEvent",
    "WatcherState",
    "WatcherStatus",
    "WatcherTickResult",
    "DispatchResult",
    "EventType",
    # Errors
    "WatcherNotFoundError",
    # Factories
    "make_event",
]
