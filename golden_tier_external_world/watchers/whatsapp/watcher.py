"""
WHATSAPP_WATCHER_SKILL — WhatsAppWatcher
Phase 1: Extends BaseWatcher with WhatsApp-specific poll() and health_check().

Design:
  - poll() fetches via WhatsAppClient, deduplicates via persisted seen-IDs set
  - health_check() delegates to WhatsAppClient.health_check()
  - Event type is derived from message content (text / media / group / location)
  - Seen IDs persisted to 70-LOGS/watchers/{id}/seen-ids.json
  - Events carry safe WhatsAppMessage dict in payload (no secrets, no raw media)
  - Tier ≥ 2 events enforced via EventDispatcher (HITL routing)

Constitution compliance:
  - Section 9: Extends BaseWatcher — atomic, composable, testable
  - Principle VI: Fail Safe — tick() never raises (inherited from BaseWatcher)
  - Principle I: Local-First — seen-IDs state written to vault
  - Section 3: HITL by Default — events at tier ≥ 2 routed via EventDispatcher
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..base.base import BaseWatcher
from ..base.models import WatcherConfig, WatcherEvent, make_event
from .client import MockWhatsAppClient, WhatsAppClient
from .models import (
    WhatsAppChatType,
    WhatsAppConfig,
    WhatsAppEventType,
    WhatsAppMessage,
    WhatsAppMessageType,
)


_SEEN_IDS_FILENAME = "seen-ids.json"
_MAX_SEEN_IDS      = 5000   # cap to prevent unbounded growth


class WhatsAppWatcher(BaseWatcher):
    """
    Concrete watcher that polls a WhatsApp account for incoming messages.

    Phase 1 uses MockWhatsAppClient by default.  Phase 2 will plug in
    RealWhatsAppClient after credentials are loaded from SecuritySkill.

    Event type mapping:
      - GROUP message of any type           → whatsapp_new_group_message
      - PRIVATE + LOCATION                  → whatsapp_new_location_message
      - PRIVATE + CONTACT                   → whatsapp_contact_received
      - PRIVATE + media (image/audio/...)   → whatsapp_new_media_message
      - PRIVATE + TEXT (default)            → whatsapp_new_text_message

    Usage::

        config = WhatsAppConfig(phone_number="+14155552671", vault_root="/vault")
        client = MockWhatsAppClient()
        watcher = WhatsAppWatcher(config, client)
        watcher.start()
        result = watcher.tick()
    """

    def __init__(
        self,
        wa_config: WhatsAppConfig,
        client: Optional[WhatsAppClient] = None,
    ) -> None:
        watcher_cfg = WatcherConfig(
            watcher_id=wa_config.watcher_id,
            watcher_type="whatsapp",
            vault_root=wa_config.vault_root,
            poll_interval_secs=wa_config.poll_interval_secs,
            tier=wa_config.tier,
            description=f"WhatsApp watcher for {wa_config.phone_number}",
        )
        super().__init__(watcher_cfg)

        self._wa_config  = wa_config
        self._client: WhatsAppClient = client or MockWhatsAppClient()
        self._seen_ids: set[str]     = self._load_seen_ids()

    # ------------------------------------------------------------------
    # BaseWatcher abstract interface
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        """Delegate to WhatsAppClient.health_check()."""
        return self._client.health_check()

    def poll(self) -> list[WatcherEvent]:
        """
        Fetch incoming WhatsApp messages; return WatcherEvents for new ones.

        Deduplication is handled by the seen-IDs set persisted to vault.
        """
        filter_chat_types = self._wa_config.filter_chat_types or None
        filter_senders    = self._wa_config.filter_senders    or None

        messages = self._client.fetch_messages(
            max_results=self._wa_config.max_results,
            filter_chat_types=filter_chat_types,
            filter_senders=filter_senders,
        )

        events: list[WatcherEvent] = []
        new_ids: list[str] = []

        for msg in messages:
            if msg.message_id in self._seen_ids:
                continue  # already processed

            event_type = self._resolve_event_type(msg)
            event = make_event(
                watcher_id=self._wa_config.watcher_id,
                event_type=event_type,
                source=f"whatsapp:{self._wa_config.phone_number}",
                payload=msg.to_dict(),
                tier=self._wa_config.tier,
            )
            events.append(event)
            new_ids.append(msg.message_id)

            if self._wa_config.send_read_receipts:
                self._client.send_read_receipt(msg.message_id)

        # Persist updated seen-IDs
        if new_ids:
            self._seen_ids.update(new_ids)
            self._trim_seen_ids()
            self._save_seen_ids()

        return events

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def wa_config(self) -> WhatsAppConfig:
        return self._wa_config

    @property
    def client(self) -> WhatsAppClient:
        return self._client

    @property
    def seen_ids(self) -> set[str]:
        return set(self._seen_ids)  # defensive copy

    # ------------------------------------------------------------------
    # Event type normalisation
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_event_type(msg: WhatsAppMessage) -> str:
        """Derive the WatcherEvent event_type from a WhatsAppMessage."""
        if msg.is_group_message():
            return WhatsAppEventType.NEW_GROUP_MESSAGE
        if msg.message_type == WhatsAppMessageType.LOCATION:
            return WhatsAppEventType.NEW_LOCATION_MESSAGE
        if msg.message_type == WhatsAppMessageType.CONTACT:
            return WhatsAppEventType.CONTACT_RECEIVED
        if msg.is_media_message():
            return WhatsAppEventType.NEW_MEDIA_MESSAGE
        return WhatsAppEventType.NEW_TEXT_MESSAGE

    # ------------------------------------------------------------------
    # Seen-IDs persistence
    # ------------------------------------------------------------------

    def _seen_ids_path(self) -> Path:
        vault = Path(self._wa_config.vault_root or ".")
        d = vault / "70-LOGS" / "watchers" / self._wa_config.watcher_id
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
                self._wa_config.watcher_id,
                f"seen-ids save failed: {exc}",
            )

    def _trim_seen_ids(self) -> None:
        """Remove arbitrary entries when seen-IDs exceeds cap."""
        if len(self._seen_ids) > _MAX_SEEN_IDS:
            overflow = len(self._seen_ids) - _MAX_SEEN_IDS
            for sid in list(self._seen_ids)[:overflow]:
                self._seen_ids.discard(sid)
