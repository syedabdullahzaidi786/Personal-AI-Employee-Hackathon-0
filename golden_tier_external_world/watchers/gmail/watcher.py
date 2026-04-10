"""
GMAIL_WATCHER_SKILL — GmailWatcher
Phase 1: Extends BaseWatcher with Gmail-specific poll() and health_check().

Design:
  - poll() fetches via GmailClient, deduplicates via persisted seen-IDs set
  - health_check() delegates to GmailClient.health_check()
  - Seen IDs persisted to 70-LOGS/watchers/{id}/seen-ids.json
  - Events carry safe GmailMessage dict in payload (no secrets)

Constitution compliance:
  - Section 9: Extends BaseWatcher — atomic, composable, testable
  - Principle VI: Fail Safe — tick() never raises (inherited from BaseWatcher)
  - Principle I: Local-First — seen-IDs state written to vault
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..base.base import BaseWatcher
from ..base.models import WatcherConfig, WatcherEvent, make_event
from .client import GmailClient, MockGmailClient
from .models import GmailConfig, GmailEventType


_SEEN_IDS_FILENAME = "seen-ids.json"
_MAX_SEEN_IDS      = 5000   # keep last N seen IDs to prevent unbounded growth


class GmailWatcher(BaseWatcher):
    """
    Concrete watcher that polls a Gmail account for new messages.

    Phase 1 uses MockGmailClient by default.  Phase 2 will plug in
    RealGmailClient after credentials are loaded from SecuritySkill.

    Usage::

        config = GmailConfig(account_email="you@gmail.com", vault_root="/vault")
        client = MockGmailClient()
        watcher = GmailWatcher(config, client)
        watcher.start()
        result = watcher.tick()
    """

    def __init__(
        self,
        gmail_config: GmailConfig,
        client: Optional[GmailClient] = None,
    ) -> None:
        # Build WatcherConfig from GmailConfig
        watcher_cfg = WatcherConfig(
            watcher_id=gmail_config.watcher_id,
            watcher_type="gmail",
            vault_root=gmail_config.vault_root,
            poll_interval_secs=gmail_config.poll_interval_secs,
            tier=gmail_config.tier,
            description=f"Gmail watcher for {gmail_config.account_email}",
        )
        super().__init__(watcher_cfg)

        self._gmail_config = gmail_config
        self._client: GmailClient = client or MockGmailClient()
        self._seen_ids: set[str]  = self._load_seen_ids()

    # ------------------------------------------------------------------
    # BaseWatcher abstract interface
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        """Delegate to GmailClient.health_check()."""
        return self._client.health_check()

    def poll(self) -> list[WatcherEvent]:
        """
        Fetch unread Gmail messages; return WatcherEvents for new ones.

        Deduplication is handled by the seen-IDs set persisted to vault.
        """
        messages = self._client.fetch_unread(
            max_results=self._gmail_config.max_results,
            filter_labels=self._gmail_config.filter_labels or None,
        )

        events: list[WatcherEvent] = []
        new_ids: list[str] = []

        for msg in messages:
            if msg.message_id in self._seen_ids:
                continue  # already processed

            # Choose event type
            event_type = (
                GmailEventType.ATTACHMENT_RECEIVED
                if msg.has_attachments
                else GmailEventType.NEW_MESSAGE
            )

            event = make_event(
                watcher_id=self._gmail_config.watcher_id,
                event_type=event_type,
                source=f"gmail:{self._gmail_config.account_email}",
                payload=msg.to_dict(),
                tier=self._gmail_config.tier,
            )
            events.append(event)
            new_ids.append(msg.message_id)

            if self._gmail_config.mark_read_on_poll:
                self._client.mark_read(msg.message_id)

        # Update and persist seen IDs
        if new_ids:
            self._seen_ids.update(new_ids)
            self._trim_seen_ids()
            self._save_seen_ids()

        return events

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def gmail_config(self) -> GmailConfig:
        return self._gmail_config

    @property
    def client(self) -> GmailClient:
        return self._client

    @property
    def seen_ids(self) -> set[str]:
        return set(self._seen_ids)  # defensive copy

    # ------------------------------------------------------------------
    # Seen-IDs persistence
    # ------------------------------------------------------------------

    def _seen_ids_path(self) -> Path:
        vault = Path(self._gmail_config.vault_root or ".")
        d = vault / "70-LOGS" / "watchers" / self._gmail_config.watcher_id
        d.mkdir(parents=True, exist_ok=True)
        return d / _SEEN_IDS_FILENAME

    def _load_seen_ids(self) -> set[str]:
        path = self._seen_ids_path()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return set(data)
            except Exception:  # noqa: BLE001
                pass
        return set()

    def _save_seen_ids(self) -> None:
        try:
            path = self._seen_ids_path()
            path.write_text(
                json.dumps(sorted(self._seen_ids), indent=2),
                encoding="utf-8",
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.log_error(
                self._gmail_config.watcher_id,
                f"seen-ids save failed: {exc}",
            )

    def _trim_seen_ids(self) -> None:
        """Keep only the most recent _MAX_SEEN_IDS entries (approximate FIFO)."""
        if len(self._seen_ids) > _MAX_SEEN_IDS:
            overflow = len(self._seen_ids) - _MAX_SEEN_IDS
            # Remove arbitrary entries (set has no order, but prevents unbounded growth)
            for sid in list(self._seen_ids)[:overflow]:
                self._seen_ids.discard(sid)
