"""
LinkedIn Watcher — LinkedInWatcher.

Extends BaseWatcher to monitor LinkedIn activity:
messages, connection requests, mentions, and notifications.

Constitution compliance:
  - Section 9: Extends BaseWatcher — atomic, composable, testable
  - Principle VI: Fail Safe — tick() never raises (inherited from BaseWatcher)
  - Principle I:  Local-First — seen-IDs state written to vault
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..base.base import BaseWatcher
from ..base.models import WatcherConfig, WatcherEvent, make_event
from .client import LinkedInClient, MockLinkedInClient
from .models import LinkedInConfig, LinkedInEventType


_SEEN_IDS_FILENAME = "seen-ids.json"
_MAX_SEEN_IDS = 5000


class LinkedInWatcher(BaseWatcher):
    """
    Concrete watcher that polls LinkedIn for new activity.

    Uses MockLinkedInClient by default.
    In production, swap with RealLinkedInClient (browser MCP).

    Usage::

        config = LinkedInConfig(vault_root="/vault")
        client = MockLinkedInClient()
        watcher = LinkedInWatcher(config, client)
        watcher.start()
        result = watcher.tick()
    """

    def __init__(
        self,
        linkedin_config: LinkedInConfig,
        client: Optional[LinkedInClient] = None,
    ) -> None:
        # Build WatcherConfig from LinkedInConfig
        watcher_cfg = WatcherConfig(
            watcher_id=linkedin_config.watcher_id,
            watcher_type="linkedin",
            vault_root=linkedin_config.vault_root,
            poll_interval_secs=linkedin_config.poll_interval_secs,
            tier=linkedin_config.tier,
        )
        super().__init__(watcher_cfg)

        self._linkedin_cfg = linkedin_config
        self._client       = client or MockLinkedInClient()
        self._seen_ids: set[str] = set()
        self._seen_ids_path = (
            Path(linkedin_config.vault_root)
            / "70-LOGS" / "watchers" / linkedin_config.watcher_id
            / _SEEN_IDS_FILENAME
        )
        self._load_seen_ids()

    # ------------------------------------------------------------------
    # BaseWatcher implementation
    # ------------------------------------------------------------------

    def poll(self) -> list[WatcherEvent]:
        """Fetch LinkedIn activity, deduplicate, return new events."""
        activities = self._client.fetch_activity(
            max_results=self._linkedin_cfg.max_results,
            event_types=self._linkedin_cfg.event_types,
        )

        new_events: list[WatcherEvent] = []
        for activity in activities:
            if activity.activity_id in self._seen_ids:
                continue

            event = make_event(
                watcher_id=self._config.watcher_id,
                event_type=activity.event_type.value,
                source="linkedin",
                payload=activity.to_dict(),
                tier=self._config.tier,
            )
            new_events.append(event)
            self._seen_ids.add(activity.activity_id)

        self._trim_seen_ids()
        self._save_seen_ids()
        return new_events

    def health_check(self) -> bool:
        """Return True if LinkedIn client is reachable."""
        try:
            return self._client.health_check()
        except Exception:  # noqa: BLE001
            return False

    # ------------------------------------------------------------------
    # Seen-IDs persistence
    # ------------------------------------------------------------------

    def _load_seen_ids(self) -> None:
        try:
            if self._seen_ids_path.exists():
                data = json.loads(self._seen_ids_path.read_text(encoding="utf-8"))
                self._seen_ids = set(data.get("seen_ids", []))
        except Exception:  # noqa: BLE001
            self._seen_ids = set()

    def _save_seen_ids(self) -> None:
        try:
            self._seen_ids_path.parent.mkdir(parents=True, exist_ok=True)
            self._seen_ids_path.write_text(
                json.dumps({"seen_ids": list(self._seen_ids)}, indent=2),
                encoding="utf-8",
            )
        except Exception:  # noqa: BLE001
            pass

    def _trim_seen_ids(self) -> None:
        if len(self._seen_ids) > _MAX_SEEN_IDS:
            # Keep only the most recent (by converting to list and slicing)
            ids_list = list(self._seen_ids)
            self._seen_ids = set(ids_list[-_MAX_SEEN_IDS:])
