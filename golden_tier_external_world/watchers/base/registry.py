"""
BASE_WATCHER_CREATION_SKILL — Watcher Registry
Tracks all registered watcher instances.

Constitution compliance:
  - Section 9: Skill Design Rules — composable, single responsibility
  - Principle II: Explicit Over Implicit — registry state always inspectable
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseWatcher


class WatcherNotFoundError(Exception):
    """Raised when a requested watcher ID is not registered."""


class WatcherRegistry:
    """
    Central registry of :class:`BaseWatcher` instances keyed by watcher_id.

    Usage::

        registry = WatcherRegistry()
        registry.register(my_watcher)
        watcher = registry.get("filesystem-watcher")
        running = registry.list_running()
    """

    def __init__(self) -> None:
        self._watchers: dict[str, "BaseWatcher"] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, watcher: "BaseWatcher") -> None:
        """Register *watcher*. Overwrites existing entry with the same ID."""
        self._watchers[watcher.config.watcher_id] = watcher

    def unregister(self, watcher_id: str) -> bool:
        """Remove watcher by ID. Returns True if it existed."""
        if watcher_id in self._watchers:
            del self._watchers[watcher_id]
            return True
        return False

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, watcher_id: str) -> Optional["BaseWatcher"]:
        """Return watcher or None."""
        return self._watchers.get(watcher_id)

    def require(self, watcher_id: str) -> "BaseWatcher":
        """Return watcher or raise :class:`WatcherNotFoundError`."""
        w = self._watchers.get(watcher_id)
        if w is None:
            raise WatcherNotFoundError(
                f"No watcher registered with id '{watcher_id}'. "
                f"Registered: {list(self._watchers)}"
            )
        return w

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    def list_all(self) -> list["BaseWatcher"]:
        """Return all registered watchers."""
        return list(self._watchers.values())

    def list_running(self) -> list["BaseWatcher"]:
        """Return only watchers whose status is RUNNING."""
        return [w for w in self._watchers.values() if w.is_running()]

    def list_ids(self) -> list[str]:
        """Return list of registered watcher IDs."""
        return list(self._watchers.keys())

    def count(self) -> int:
        return len(self._watchers)

    def is_registered(self, watcher_id: str) -> bool:
        return watcher_id in self._watchers
