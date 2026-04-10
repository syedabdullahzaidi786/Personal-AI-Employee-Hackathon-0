"""
WHATSAPP_WATCHER_SKILL — Phase 1 Unit Tests
Target: ~80 tests, stdlib only.

Coverage:
  - WhatsAppMessage, WhatsAppConfig, type constants, make_whatsapp_message  (models.py)
  - WhatsAppClient ABC, MockWhatsAppClient, RealWhatsAppClient               (client.py)
  - WhatsAppWatcher.poll/health_check/seen-IDs/event-type-mapping/tick      (watcher.py)
  - Handlers: make_log_handler, make_orchestrator_handler,
              make_filter_handler, make_group_filter, make_private_filter,
              make_sender_filter, make_media_filter                          (handlers.py)
  - WhatsAppWatcherSkill facade + HITL wiring                               (__init__.py)
  - CLI: status, tick, events, inject (private + group)                     (cli.py)
"""

from __future__ import annotations

import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
from golden_tier_external_world.watchers.whatsapp.models import (
    WhatsAppChatType,
    WhatsAppConfig,
    WhatsAppEventType,
    WhatsAppMessage,
    WhatsAppMessageType,
    make_whatsapp_message,
)
from golden_tier_external_world.watchers.whatsapp.client import (
    MockWhatsAppClient,
    RealWhatsAppClient,
    WhatsAppClient,
)
from golden_tier_external_world.watchers.whatsapp.watcher import WhatsAppWatcher
from golden_tier_external_world.watchers.whatsapp.handlers import (
    make_filter_handler,
    make_group_filter,
    make_log_handler,
    make_media_filter,
    make_orchestrator_handler,
    make_private_filter,
    make_sender_filter,
)
from golden_tier_external_world.watchers.whatsapp import WhatsAppWatcherSkill
from golden_tier_external_world.watchers.whatsapp.cli import build_parser, main as cli_main
from golden_tier_external_world.watchers.base.models import WatcherEvent


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def wa_config(tmp_vault: Path) -> WhatsAppConfig:
    return WhatsAppConfig(
        phone_number="+14155552671",
        vault_root=str(tmp_vault),
        max_results=10,
    )


@pytest.fixture
def mock_client() -> MockWhatsAppClient:
    return MockWhatsAppClient()


@pytest.fixture
def watcher(wa_config: WhatsAppConfig, mock_client: MockWhatsAppClient) -> WhatsAppWatcher:
    w = WhatsAppWatcher(wa_config, mock_client)
    w.start()
    return w


@pytest.fixture
def skill(wa_config: WhatsAppConfig) -> WhatsAppWatcherSkill:
    return WhatsAppWatcherSkill(wa_config)


# ===========================================================================
# TestWhatsAppMessage
# ===========================================================================

class TestWhatsAppMessage:

    def test_to_dict_roundtrip(self) -> None:
        msg = WhatsAppMessage(
            message_id="WA-001",
            chat_id="+14155552671",
            chat_type=WhatsAppChatType.PRIVATE,
            message_type=WhatsAppMessageType.TEXT,
            sender_phone="+14155552671",
            sender_name="Alice",
            message_body="Hello!",
            received_at=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
        )
        d    = msg.to_dict()
        msg2 = WhatsAppMessage.from_dict(d)
        assert msg2.message_id   == "WA-001"
        assert msg2.sender_phone == "+14155552671"
        assert msg2.sender_name  == "Alice"
        assert msg2.message_body == "Hello!"

    def test_message_body_truncated_to_500(self) -> None:
        msg = WhatsAppMessage(
            message_id="M1", chat_id="X", chat_type=WhatsAppChatType.PRIVATE,
            message_type=WhatsAppMessageType.TEXT,
            sender_phone="+1", sender_name="", message_body="x" * 600,
        )
        assert len(msg.to_dict()["message_body"]) == 500

    def test_is_group_message_true(self) -> None:
        msg = make_whatsapp_message(
            "+1", chat_type=WhatsAppChatType.GROUP,
            group_id="grp1", group_name="Team",
        )
        assert msg.is_group_message() is True

    def test_is_group_message_false(self) -> None:
        msg = make_whatsapp_message("+1")
        assert msg.is_group_message() is False

    def test_is_media_message_image(self) -> None:
        msg = make_whatsapp_message("+1", message_type=WhatsAppMessageType.IMAGE)
        assert msg.is_media_message() is True

    def test_is_media_message_text_false(self) -> None:
        msg = make_whatsapp_message("+1", message_type=WhatsAppMessageType.TEXT)
        assert msg.is_media_message() is False

    def test_from_dict_no_received_at(self) -> None:
        d = {
            "message_id": "M1", "chat_id": "C1",
            "sender_phone": "+1", "message_body": "",
        }
        msg = WhatsAppMessage.from_dict(d)
        assert msg.received_at is None

    def test_defaults_are_safe(self) -> None:
        msg = WhatsAppMessage(
            message_id="M1", chat_id="C1",
            chat_type=WhatsAppChatType.PRIVATE,
            message_type=WhatsAppMessageType.TEXT,
            sender_phone="+1", sender_name="", message_body="",
        )
        assert msg.is_forwarded      is False
        assert msg.group_id          == ""
        assert msg.media_filename    == ""
        assert msg.media_size_bytes  == 0


# ===========================================================================
# TestWhatsAppConfig
# ===========================================================================

class TestWhatsAppConfig:

    def test_watcher_id_auto_generated(self) -> None:
        cfg = WhatsAppConfig(phone_number="+14155552671")
        assert cfg.watcher_id.startswith("whatsapp-")
        assert "14155552671" in cfg.watcher_id

    def test_watcher_id_no_plus_sign(self) -> None:
        cfg = WhatsAppConfig(phone_number="+14155552671")
        assert "+" not in cfg.watcher_id

    def test_watcher_id_explicit(self) -> None:
        cfg = WhatsAppConfig(phone_number="+1", watcher_id="my-wa")
        assert cfg.watcher_id == "my-wa"

    def test_to_dict_roundtrip(self) -> None:
        cfg = WhatsAppConfig(
            phone_number="+1", vault_root="/v",
            max_results=30, tier=1,
        )
        d    = cfg.to_dict()
        cfg2 = WhatsAppConfig.from_dict(d)
        assert cfg2.phone_number == "+1"
        assert cfg2.max_results  == 30
        assert cfg2.tier         == 1

    def test_defaults(self) -> None:
        cfg = WhatsAppConfig(phone_number="+1")
        assert cfg.max_results       == 20
        assert cfg.filter_chat_types == []
        assert cfg.filter_senders    == []
        assert cfg.credentials_name  == "whatsapp_api_key"
        assert cfg.send_read_receipts is False


# ===========================================================================
# TestWhatsAppEventTypeConstants
# ===========================================================================

class TestWhatsAppEventTypeConstants:

    def test_all_constants_are_strings(self) -> None:
        assert isinstance(WhatsAppEventType.NEW_TEXT_MESSAGE,     str)
        assert isinstance(WhatsAppEventType.NEW_MEDIA_MESSAGE,    str)
        assert isinstance(WhatsAppEventType.NEW_GROUP_MESSAGE,    str)
        assert isinstance(WhatsAppEventType.NEW_LOCATION_MESSAGE, str)
        assert isinstance(WhatsAppEventType.CONTACT_RECEIVED,     str)

    def test_all_start_with_whatsapp(self) -> None:
        for attr in vars(WhatsAppEventType):
            if attr.startswith("_"):
                continue
            val = getattr(WhatsAppEventType, attr)
            if isinstance(val, str):
                assert val.startswith("whatsapp_"), f"{attr} = {val!r}"


# ===========================================================================
# TestMakeWhatsAppMessage
# ===========================================================================

class TestMakeWhatsAppMessage:

    def test_returns_whatsapp_message(self) -> None:
        msg = make_whatsapp_message("+1", "Hi")
        assert isinstance(msg, WhatsAppMessage)

    def test_auto_ids_unique(self) -> None:
        m1 = make_whatsapp_message("+1")
        m2 = make_whatsapp_message("+2")
        assert m1.message_id != m2.message_id

    def test_received_at_utc(self) -> None:
        msg = make_whatsapp_message("+1")
        assert msg.received_at is not None
        assert msg.received_at.tzinfo is not None

    def test_group_message_sets_chat_id_to_group_id(self) -> None:
        msg = make_whatsapp_message(
            "+1", chat_type=WhatsAppChatType.GROUP,
            group_id="grp-abc", group_name="Fam",
        )
        assert msg.chat_id    == "grp-abc"
        assert msg.group_id   == "grp-abc"
        assert msg.group_name == "Fam"

    def test_private_message_chat_id_is_sender(self) -> None:
        msg = make_whatsapp_message("+14155550001")
        assert msg.chat_id == "+14155550001"

    def test_message_body_truncated(self) -> None:
        msg = make_whatsapp_message("+1", message_body="x" * 600)
        assert len(msg.message_body) == 500


# ===========================================================================
# TestMockWhatsAppClient
# ===========================================================================

class TestMockWhatsAppClient:

    def test_empty_inbox(self, mock_client: MockWhatsAppClient) -> None:
        assert mock_client.fetch_messages() == []

    def test_inject_then_fetch(self, mock_client: MockWhatsAppClient) -> None:
        msg = make_whatsapp_message("+1", "Hello")
        mock_client.inject_message(msg)
        results = mock_client.fetch_messages()
        assert len(results) == 1
        assert results[0].message_id == msg.message_id

    def test_max_results_respected(self, mock_client: MockWhatsAppClient) -> None:
        for i in range(8):
            mock_client.inject_message(make_whatsapp_message(f"+{i}", f"Msg {i}"))
        results = mock_client.fetch_messages(max_results=3)
        assert len(results) == 3

    def test_read_receipt_hides_message(self, mock_client: MockWhatsAppClient) -> None:
        msg = make_whatsapp_message("+1", "Hi")
        mock_client.inject_message(msg)
        mock_client.send_read_receipt(msg.message_id)
        assert mock_client.fetch_messages() == []

    def test_health_check_default_true(self, mock_client: MockWhatsAppClient) -> None:
        assert mock_client.health_check() is True

    def test_set_healthy_false(self, mock_client: MockWhatsAppClient) -> None:
        mock_client.set_healthy(False)
        assert mock_client.health_check() is False

    def test_fetch_count_increments(self, mock_client: MockWhatsAppClient) -> None:
        mock_client.fetch_messages()
        mock_client.fetch_messages()
        assert mock_client.fetch_count == 2

    def test_clear_inbox(self, mock_client: MockWhatsAppClient) -> None:
        mock_client.inject_message(make_whatsapp_message("+1", "Hi"))
        mock_client.clear_inbox()
        assert mock_client.fetch_messages() == []

    def test_filter_chat_types_private_only(self, mock_client: MockWhatsAppClient) -> None:
        private_msg = make_whatsapp_message("+1", "DM")
        group_msg   = make_whatsapp_message("+2", "Group!", chat_type=WhatsAppChatType.GROUP,
                                             group_id="grp1")
        mock_client.inject_message(private_msg)
        mock_client.inject_message(group_msg)
        results = mock_client.fetch_messages(filter_chat_types=[WhatsAppChatType.PRIVATE])
        assert len(results) == 1
        assert results[0].message_id == private_msg.message_id

    def test_filter_senders(self, mock_client: MockWhatsAppClient) -> None:
        m1 = make_whatsapp_message("+111", "From 111")
        m2 = make_whatsapp_message("+222", "From 222")
        mock_client.inject_message(m1)
        mock_client.inject_message(m2)
        results = mock_client.fetch_messages(filter_senders=["+111"])
        assert len(results) == 1
        assert results[0].message_id == m1.message_id

    def test_inbox_size_property(self, mock_client: MockWhatsAppClient) -> None:
        assert mock_client.inbox_size == 0
        mock_client.inject_message(make_whatsapp_message("+1"))
        assert mock_client.inbox_size == 1

    def test_receipts_sent_property(self, mock_client: MockWhatsAppClient) -> None:
        msg = make_whatsapp_message("+1")
        mock_client.inject_message(msg)
        mock_client.send_read_receipt(msg.message_id)
        assert msg.message_id in mock_client.receipts_sent


# ===========================================================================
# TestRealWhatsAppClient
# ===========================================================================

class TestRealWhatsAppClient:

    def test_fetch_messages_raises(self, wa_config: WhatsAppConfig) -> None:
        client = RealWhatsAppClient(wa_config)
        with pytest.raises(NotImplementedError):
            client.fetch_messages()

    def test_send_read_receipt_raises(self, wa_config: WhatsAppConfig) -> None:
        client = RealWhatsAppClient(wa_config)
        with pytest.raises(NotImplementedError):
            client.send_read_receipt("WA-001")

    def test_health_check_returns_false(self, wa_config: WhatsAppConfig) -> None:
        client = RealWhatsAppClient(wa_config)
        assert client.health_check() is False


# ===========================================================================
# TestWhatsAppWatcher
# ===========================================================================

class TestWhatsAppWatcher:

    def test_health_check_delegates_to_client(
        self, wa_config: WhatsAppConfig, mock_client: MockWhatsAppClient
    ) -> None:
        w = WhatsAppWatcher(wa_config, mock_client)
        assert w.health_check() is True
        mock_client.set_healthy(False)
        assert w.health_check() is False

    def test_poll_empty_inbox(self, watcher: WhatsAppWatcher) -> None:
        assert watcher.poll() == []

    def test_poll_text_message_event_type(
        self, watcher: WhatsAppWatcher, mock_client: MockWhatsAppClient
    ) -> None:
        mock_client.inject_message(make_whatsapp_message("+1", "Hello"))
        events = watcher.poll()
        assert len(events) == 1
        assert events[0].event_type == WhatsAppEventType.NEW_TEXT_MESSAGE

    def test_poll_media_message_event_type(
        self, wa_config: WhatsAppConfig, mock_client: MockWhatsAppClient
    ) -> None:
        mock_client.inject_message(
            make_whatsapp_message("+1", message_type=WhatsAppMessageType.IMAGE)
        )
        w = WhatsAppWatcher(wa_config, mock_client)
        w.start()
        events = w.poll()
        assert events[0].event_type == WhatsAppEventType.NEW_MEDIA_MESSAGE

    def test_poll_group_message_event_type(
        self, wa_config: WhatsAppConfig, mock_client: MockWhatsAppClient
    ) -> None:
        mock_client.inject_message(
            make_whatsapp_message("+1", "Hi group",
                                  chat_type=WhatsAppChatType.GROUP,
                                  group_id="grp1")
        )
        w = WhatsAppWatcher(wa_config, mock_client)
        w.start()
        events = w.poll()
        assert events[0].event_type == WhatsAppEventType.NEW_GROUP_MESSAGE

    def test_poll_location_event_type(
        self, wa_config: WhatsAppConfig, mock_client: MockWhatsAppClient
    ) -> None:
        mock_client.inject_message(
            make_whatsapp_message("+1", message_type=WhatsAppMessageType.LOCATION,
                                  latitude=40.7128, longitude=-74.0060)
        )
        w = WhatsAppWatcher(wa_config, mock_client)
        w.start()
        events = w.poll()
        assert events[0].event_type == WhatsAppEventType.NEW_LOCATION_MESSAGE

    def test_poll_contact_event_type(
        self, wa_config: WhatsAppConfig, mock_client: MockWhatsAppClient
    ) -> None:
        mock_client.inject_message(
            make_whatsapp_message("+1", message_type=WhatsAppMessageType.CONTACT)
        )
        w = WhatsAppWatcher(wa_config, mock_client)
        w.start()
        events = w.poll()
        assert events[0].event_type == WhatsAppEventType.CONTACT_RECEIVED

    def test_poll_deduplicates(
        self, watcher: WhatsAppWatcher, mock_client: MockWhatsAppClient
    ) -> None:
        msg = make_whatsapp_message("+1", "Hi")
        mock_client.inject_message(msg)
        watcher.poll()           # first — seen
        events = watcher.poll()  # second — deduplicated
        assert events == []

    def test_poll_payload_contains_message_fields(
        self, watcher: WhatsAppWatcher, mock_client: MockWhatsAppClient
    ) -> None:
        msg = make_whatsapp_message("+14155550001", "Test body", sender_name="Bob")
        mock_client.inject_message(msg)
        events = watcher.poll()
        payload = events[0].payload
        assert payload["sender_phone"] == "+14155550001"
        assert payload["message_body"] == "Test body"
        assert payload["sender_name"]  == "Bob"

    def test_tick_health_fail_returns_error_result(
        self, wa_config: WhatsAppConfig, mock_client: MockWhatsAppClient
    ) -> None:
        mock_client.set_healthy(False)
        w = WhatsAppWatcher(wa_config, mock_client)
        w.start()
        result = w.tick()
        assert result.health_ok is False
        assert result.errors >= 1

    def test_tick_increments_poll_count(self, watcher: WhatsAppWatcher) -> None:
        before = watcher.state.poll_count
        watcher.tick()
        assert watcher.state.poll_count == before + 1

    def test_tick_with_message_updates_events_found(
        self, watcher: WhatsAppWatcher, mock_client: MockWhatsAppClient
    ) -> None:
        mock_client.inject_message(make_whatsapp_message("+1", "Hi"))
        result = watcher.tick()
        assert result.events_found == 1

    def test_seen_ids_persisted_to_vault(
        self, watcher: WhatsAppWatcher, mock_client: MockWhatsAppClient, tmp_vault: Path
    ) -> None:
        msg = make_whatsapp_message("+1", "Hi")
        mock_client.inject_message(msg)
        watcher.poll()
        seen_path = (
            tmp_vault / "70-LOGS" / "watchers"
            / watcher.wa_config.watcher_id / "seen-ids.json"
        )
        assert seen_path.exists()
        data = json.loads(seen_path.read_text())
        assert msg.message_id in data

    def test_seen_ids_loaded_on_init(
        self, wa_config: WhatsAppConfig, mock_client: MockWhatsAppClient, tmp_vault: Path
    ) -> None:
        wid      = wa_config.watcher_id
        seen_dir = tmp_vault / "70-LOGS" / "watchers" / wid
        seen_dir.mkdir(parents=True, exist_ok=True)
        (seen_dir / "seen-ids.json").write_text(
            json.dumps(["WA-PREPOPULATED"]), encoding="utf-8"
        )
        w = WhatsAppWatcher(wa_config, mock_client)
        assert "WA-PREPOPULATED" in w.seen_ids

    def test_seen_ids_defensive_copy(self, watcher: WhatsAppWatcher) -> None:
        copy = watcher.seen_ids
        copy.add("EXTERNAL")
        assert "EXTERNAL" not in watcher.seen_ids

    def test_watcher_config_type_is_whatsapp(self, watcher: WhatsAppWatcher) -> None:
        assert watcher.config.watcher_type == "whatsapp"

    def test_send_read_receipt_on_poll(
        self, wa_config: WhatsAppConfig, mock_client: MockWhatsAppClient, tmp_vault: Path
    ) -> None:
        cfg = WhatsAppConfig(
            phone_number=wa_config.phone_number,
            vault_root=str(tmp_vault),
            send_read_receipts=True,
        )
        msg = make_whatsapp_message("+1", "Hi")
        mock_client.inject_message(msg)
        w = WhatsAppWatcher(cfg, mock_client)
        w.start()
        w.poll()
        assert msg.message_id in mock_client.receipts_sent


# ===========================================================================
# TestHandlers
# ===========================================================================

class TestHandlers:

    def _make_text_event(self, sender: str = "+1", body: str = "Hi",
                          chat_type: str = WhatsAppChatType.PRIVATE) -> WatcherEvent:
        from golden_tier_external_world.watchers.base.models import make_event
        return make_event(
            watcher_id="whatsapp-test",
            event_type=WhatsAppEventType.NEW_TEXT_MESSAGE,
            source="whatsapp:+1",
            payload={
                "sender_phone": sender,
                "sender_name":  "",
                "message_body": body,
                "chat_type":    chat_type,
                "message_type": WhatsAppMessageType.TEXT,
                "group_name":   "",
            },
        )

    def _make_media_event(self) -> WatcherEvent:
        from golden_tier_external_world.watchers.base.models import make_event
        return make_event(
            watcher_id="whatsapp-test",
            event_type=WhatsAppEventType.NEW_MEDIA_MESSAGE,
            source="whatsapp:+1",
            payload={
                "sender_phone": "+1",
                "sender_name":  "",
                "message_body": "",
                "chat_type":    WhatsAppChatType.PRIVATE,
                "message_type": WhatsAppMessageType.IMAGE,
                "group_name":   "",
            },
        )

    def test_log_handler_writes_sender(self) -> None:
        buf = io.StringIO()
        h   = make_log_handler(stream=buf)
        h(self._make_text_event(sender="+14155550001"))
        assert "+14155550001" in buf.getvalue()

    def test_log_handler_writes_body(self) -> None:
        buf = io.StringIO()
        h   = make_log_handler(stream=buf)
        h(self._make_text_event(body="Secret message"))
        assert "Secret message" in buf.getvalue()

    def test_log_handler_custom_prefix(self) -> None:
        buf = io.StringIO()
        h   = make_log_handler(prefix="[WAPP]", stream=buf)
        h(self._make_text_event())
        assert "[WAPP]" in buf.getvalue()

    def test_orchestrator_handler_calls_run_workflow(self) -> None:
        mock_orc = MagicMock()
        h        = make_orchestrator_handler(mock_orc, "process-wa")
        h(self._make_text_event())
        mock_orc.run_workflow.assert_called_once()
        assert mock_orc.run_workflow.call_args[0][0] == "process-wa"

    def test_orchestrator_handler_context_contains_event_data(self) -> None:
        mock_orc = MagicMock()
        h        = make_orchestrator_handler(mock_orc, "wf", extra_context={"k": "v"})
        event    = self._make_text_event(sender="+99", body="hello")
        h(event)
        ctx = mock_orc.run_workflow.call_args[0][1]
        assert ctx["event_id"]      == event.event_id
        assert ctx["sender_phone"]  == "+99"
        assert ctx["message_body"]  == "hello"
        assert ctx["k"]             == "v"

    def test_filter_handler_condition_true(self) -> None:
        calls = []
        h     = make_filter_handler(lambda e: True, lambda e: calls.append(e))
        h(self._make_text_event())
        assert len(calls) == 1

    def test_filter_handler_condition_false(self) -> None:
        calls = []
        h     = make_filter_handler(lambda e: False, lambda e: calls.append(e))
        h(self._make_text_event())
        assert calls == []

    def test_filter_handler_else(self) -> None:
        then_calls, else_calls = [], []
        h = make_filter_handler(
            lambda e: False,
            lambda e: then_calls.append(e),
            lambda e: else_calls.append(e),
        )
        h(self._make_text_event())
        assert then_calls == []
        assert len(else_calls) == 1

    def test_group_filter_passes_group(self) -> None:
        calls = []
        h     = make_group_filter(lambda e: calls.append(e))
        h(self._make_text_event(chat_type=WhatsAppChatType.GROUP))
        assert len(calls) == 1

    def test_group_filter_blocks_private(self) -> None:
        calls = []
        h     = make_group_filter(lambda e: calls.append(e))
        h(self._make_text_event(chat_type=WhatsAppChatType.PRIVATE))
        assert calls == []

    def test_private_filter_passes_private(self) -> None:
        calls = []
        h     = make_private_filter(lambda e: calls.append(e))
        h(self._make_text_event(chat_type=WhatsAppChatType.PRIVATE))
        assert len(calls) == 1

    def test_private_filter_blocks_group(self) -> None:
        calls = []
        h     = make_private_filter(lambda e: calls.append(e))
        h(self._make_text_event(chat_type=WhatsAppChatType.GROUP))
        assert calls == []

    def test_sender_filter_match(self) -> None:
        calls = []
        h     = make_sender_filter(["+14155550001"], lambda e: calls.append(e))
        h(self._make_text_event(sender="+14155550001"))
        assert len(calls) == 1

    def test_sender_filter_no_match(self) -> None:
        calls = []
        h     = make_sender_filter(["+9999"], lambda e: calls.append(e))
        h(self._make_text_event(sender="+14155550001"))
        assert calls == []

    def test_media_filter_passes_image(self) -> None:
        calls = []
        h     = make_media_filter(lambda e: calls.append(e))
        h(self._make_media_event())
        assert len(calls) == 1

    def test_media_filter_blocks_text(self) -> None:
        calls = []
        h     = make_media_filter(lambda e: calls.append(e))
        h(self._make_text_event())
        assert calls == []


# ===========================================================================
# TestWhatsAppWatcherSkill (facade)
# ===========================================================================

class TestWhatsAppWatcherSkill:

    def test_start_and_is_running(self, skill: WhatsAppWatcherSkill) -> None:
        skill.start()
        assert skill.is_running() is True

    def test_stop(self, skill: WhatsAppWatcherSkill) -> None:
        skill.start()
        skill.stop()
        assert skill.is_running() is False

    def test_tick_empty_returns_zero_events(self, skill: WhatsAppWatcherSkill) -> None:
        skill.start()
        result = skill.tick()
        assert result.events_found == 0
        assert result.health_ok    is True

    def test_tick_with_injected_message(self, skill: WhatsAppWatcherSkill) -> None:
        msg = make_whatsapp_message("+1", "Test")
        skill.inject_message(msg)
        skill.start()
        result = skill.tick()
        assert result.events_found == 1

    def test_handler_called_on_tick(self, skill: WhatsAppWatcherSkill) -> None:
        received = []
        skill.register_handler(
            WhatsAppEventType.NEW_TEXT_MESSAGE, lambda e: received.append(e)
        )
        msg = make_whatsapp_message("+1", "Hello handler")
        skill.inject_message(msg)
        skill.start()
        skill.tick()
        assert len(received) == 1
        assert received[0].payload["message_body"] == "Hello handler"

    def test_inject_message_raises_for_real_client(
        self, wa_config: WhatsAppConfig
    ) -> None:
        real_client = RealWhatsAppClient(wa_config)
        sk = WhatsAppWatcherSkill(wa_config, client=real_client)
        with pytest.raises(TypeError):
            sk.inject_message(make_whatsapp_message("+1"))

    def test_unregister_handler(self, skill: WhatsAppWatcherSkill) -> None:
        received = []
        skill.register_handler(
            WhatsAppEventType.NEW_TEXT_MESSAGE, lambda e: received.append(e)
        )
        skill.unregister_handler(WhatsAppEventType.NEW_TEXT_MESSAGE)
        skill.inject_message(make_whatsapp_message("+1", "Ignored"))
        skill.start()
        skill.tick()
        assert received == []

    def test_hitl_forwarded_to_dispatcher(self, skill: WhatsAppWatcherSkill) -> None:
        mock_hitl = MagicMock()
        skill.set_hitl(mock_hitl)
        assert skill.dispatcher._hitl is mock_hitl

    def test_security_skill_integration_graceful(
        self, wa_config: WhatsAppConfig
    ) -> None:
        bad_skill = MagicMock(side_effect=Exception("security failure"))
        sk = WhatsAppWatcherSkill(wa_config, security_skill=bad_skill)
        assert sk is not None

    def test_wa_config_property(
        self, skill: WhatsAppWatcherSkill, wa_config: WhatsAppConfig
    ) -> None:
        assert skill.wa_config is wa_config

    def test_watcher_property(self, skill: WhatsAppWatcherSkill) -> None:
        assert isinstance(skill.watcher, WhatsAppWatcher)

    def test_dispatcher_property(self, skill: WhatsAppWatcherSkill) -> None:
        from golden_tier_external_world.watchers.base.dispatcher import EventDispatcher
        assert isinstance(skill.dispatcher, EventDispatcher)


# ===========================================================================
# TestCLI
# ===========================================================================

class TestCLI:

    def test_build_parser_not_none(self) -> None:
        assert build_parser() is not None

    def test_status_no_state_file_returns_1(self, tmp_vault: Path) -> None:
        result = cli_main([
            "--vault", str(tmp_vault),
            "--phone", "+14155552671",
            "status",
        ])
        assert result == 1

    def test_status_with_state_file_returns_0(self, tmp_vault: Path) -> None:
        wid       = "whatsapp-14155552671"
        state_dir = tmp_vault / "70-LOGS" / "watchers" / wid
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "state.json").write_text(
            json.dumps({
                "watcher_id": wid, "status": "running",
                "poll_count": 3, "total_events": 2, "error_count": 0,
            }),
            encoding="utf-8",
        )
        result = cli_main([
            "--vault", str(tmp_vault),
            "--phone", "+14155552671",
            "status",
        ])
        assert result == 0

    def test_tick_returns_0(self, tmp_vault: Path) -> None:
        result = cli_main([
            "--vault", str(tmp_vault),
            "--phone", "+14155552671",
            "tick",
        ])
        assert result == 0

    def test_events_no_events_returns_0(self, tmp_vault: Path) -> None:
        result = cli_main([
            "--vault", str(tmp_vault),
            "--phone", "+14155552671",
            "events",
        ])
        assert result == 0

    def test_inject_private_message_returns_0(self, tmp_vault: Path) -> None:
        result = cli_main([
            "--vault", str(tmp_vault),
            "--phone", "+14155552671",
            "inject",
            "--sender", "+19175550100",
            "--body", "Hello!",
        ])
        assert result == 0

    def test_inject_group_message_returns_0(self, tmp_vault: Path) -> None:
        result = cli_main([
            "--vault", str(tmp_vault),
            "--phone", "+14155552671",
            "inject",
            "--sender",     "+19175550100",
            "--body",       "Group hi",
            "--group-id",   "grp-001",
            "--group-name", "Family",
        ])
        assert result == 0

    def test_inject_then_events_shows_event(self, tmp_vault: Path) -> None:
        cli_main([
            "--vault", str(tmp_vault),
            "--phone", "+14155552671",
            "inject",
            "--sender", "+19175550100",
            "--body",   "Persisted",
        ])
        result = cli_main([
            "--vault", str(tmp_vault),
            "--phone", "+14155552671",
            "events",
        ])
        assert result == 0
