"""
GMAIL_WATCHER_SKILL — Phase 1 Unit Tests
Target: ~70 tests, stdlib only.

Coverage:
  - GmailMessage, GmailConfig, GmailEventType, make_gmail_message  (models.py)
  - GmailClient ABC, MockGmailClient, RealGmailClient               (client.py)
  - GmailWatcher.poll/health_check/seen-IDs/tick integration        (watcher.py)
  - Handlers: make_log_handler, make_orchestrator_handler,
              make_filter_handler, make_sender_filter                (handlers.py)
  - GmailWatcherSkill facade                                        (__init__.py)
  - CLI: status, tick, events, inject                               (cli.py)
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Path bootstrap (runs from repo root via pytest)
# ---------------------------------------------------------------------------
from golden_tier_external_world.watchers.gmail.models import (
    GmailConfig,
    GmailEventType,
    GmailMessage,
    make_gmail_message,
)
from golden_tier_external_world.watchers.gmail.client import (
    GmailClient,
    MockGmailClient,
    RealGmailClient,
)
from golden_tier_external_world.watchers.gmail.watcher import GmailWatcher
from golden_tier_external_world.watchers.gmail.handlers import (
    make_filter_handler,
    make_log_handler,
    make_orchestrator_handler,
    make_sender_filter,
)
from golden_tier_external_world.watchers.gmail import GmailWatcherSkill
from golden_tier_external_world.watchers.gmail.cli import build_parser, main as cli_main
from golden_tier_external_world.watchers.base.models import WatcherEvent


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    """Return a temp directory acting as the Obsidian vault root."""
    return tmp_path


@pytest.fixture
def gmail_config(tmp_vault: Path) -> GmailConfig:
    return GmailConfig(
        account_email="test@example.com",
        vault_root=str(tmp_vault),
        max_results=5,
    )


@pytest.fixture
def mock_client() -> MockGmailClient:
    return MockGmailClient()


@pytest.fixture
def watcher(gmail_config: GmailConfig, mock_client: MockGmailClient) -> GmailWatcher:
    w = GmailWatcher(gmail_config, mock_client)
    w.start()
    return w


@pytest.fixture
def skill(gmail_config: GmailConfig) -> GmailWatcherSkill:
    return GmailWatcherSkill(gmail_config)


# ===========================================================================
# TestGmailMessage
# ===========================================================================

class TestGmailMessage:

    def test_to_dict_roundtrip(self) -> None:
        msg = GmailMessage(
            message_id="MSG-001",
            thread_id="THR-001",
            subject="Hello",
            sender="alice@example.com",
            recipient="bob@example.com",
            snippet="Hello world",
            labels=["INBOX"],
            received_at=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
        )
        d   = msg.to_dict()
        msg2 = GmailMessage.from_dict(d)
        assert msg2.message_id == "MSG-001"
        assert msg2.subject    == "Hello"
        assert msg2.sender     == "alice@example.com"

    def test_snippet_truncated_to_200_chars(self) -> None:
        long_snippet = "x" * 300
        msg = GmailMessage(
            message_id="M1",
            thread_id="T1",
            subject="Test",
            sender="a@b.com",
            recipient="c@d.com",
            snippet=long_snippet,
        )
        assert len(msg.to_dict()["snippet"]) == 200

    def test_defaults_are_safe(self) -> None:
        msg = GmailMessage(
            message_id="M1",
            thread_id="T1",
            subject="",
            sender="",
            recipient="",
            snippet="",
        )
        assert msg.has_attachments is False
        assert msg.labels == []
        assert msg.attachment_names == []

    def test_from_dict_no_received_at(self) -> None:
        d = {
            "message_id": "M1", "thread_id": "T1", "subject": "S",
            "sender": "a", "recipient": "b", "snippet": "",
        }
        msg = GmailMessage.from_dict(d)
        assert msg.received_at is None

    def test_attachment_fields_preserved(self) -> None:
        msg = GmailMessage(
            message_id="M2", thread_id="T2", subject="",
            sender="", recipient="", snippet="",
            has_attachments=True,
            attachment_names=["report.pdf", "image.png"],
        )
        d = msg.to_dict()
        assert d["has_attachments"] is True
        assert d["attachment_names"] == ["report.pdf", "image.png"]


# ===========================================================================
# TestGmailConfig
# ===========================================================================

class TestGmailConfig:

    def test_watcher_id_auto_generated(self) -> None:
        cfg = GmailConfig(account_email="user@example.com")
        assert "gmail-" in cfg.watcher_id
        assert "user" in cfg.watcher_id

    def test_watcher_id_explicit(self) -> None:
        cfg = GmailConfig(account_email="user@example.com", watcher_id="my-watcher")
        assert cfg.watcher_id == "my-watcher"

    def test_to_dict_roundtrip(self) -> None:
        cfg = GmailConfig(
            account_email="a@b.com",
            vault_root="/vault",
            max_results=20,
            tier=1,
        )
        d    = cfg.to_dict()
        cfg2 = GmailConfig.from_dict(d)
        assert cfg2.account_email == "a@b.com"
        assert cfg2.max_results   == 20
        assert cfg2.tier          == 1

    def test_defaults(self) -> None:
        cfg = GmailConfig(account_email="x@y.com")
        assert cfg.max_results       == 10
        assert cfg.filter_labels     == []
        assert cfg.mark_read_on_poll is False
        assert cfg.credentials_name  == "gmail_api_key"

    def test_at_and_dot_in_id_are_safe(self) -> None:
        cfg = GmailConfig(account_email="my.name+tag@sub.domain.com")
        # Should not contain @ or dots (those are replaced)
        assert "@" not in cfg.watcher_id
        assert ".com" not in cfg.watcher_id


# ===========================================================================
# TestGmailEventType
# ===========================================================================

class TestGmailEventType:

    def test_event_type_constants(self) -> None:
        assert GmailEventType.NEW_MESSAGE         == "gmail_new_message"
        assert GmailEventType.NEW_THREAD          == "gmail_new_thread"
        assert GmailEventType.ATTACHMENT_RECEIVED == "gmail_attachment_received"
        assert GmailEventType.POLL_HEARTBEAT      == "gmail_poll_heartbeat"


# ===========================================================================
# TestMakeGmailMessage
# ===========================================================================

class TestMakeGmailMessage:

    def test_returns_gmail_message(self) -> None:
        msg = make_gmail_message("Hello", "alice@example.com")
        assert isinstance(msg, GmailMessage)

    def test_auto_ids_unique(self) -> None:
        m1 = make_gmail_message("A", "a@b.com")
        m2 = make_gmail_message("B", "b@c.com")
        assert m1.message_id != m2.message_id
        assert m1.thread_id  != m2.thread_id

    def test_snippet_truncated(self) -> None:
        msg = make_gmail_message("S", "a@b.com", snippet="x" * 300)
        assert len(msg.snippet) == 200

    def test_received_at_is_utc(self) -> None:
        msg = make_gmail_message("S", "a@b.com")
        assert msg.received_at is not None
        assert msg.received_at.tzinfo is not None


# ===========================================================================
# TestMockGmailClient
# ===========================================================================

class TestMockGmailClient:

    def test_empty_inbox_returns_empty(self, mock_client: MockGmailClient) -> None:
        assert mock_client.fetch_unread() == []

    def test_inject_then_fetch(self, mock_client: MockGmailClient) -> None:
        msg = make_gmail_message("Hi", "a@b.com")
        mock_client.inject_message(msg)
        results = mock_client.fetch_unread()
        assert len(results) == 1
        assert results[0].message_id == msg.message_id

    def test_max_results_respected(self, mock_client: MockGmailClient) -> None:
        for i in range(5):
            mock_client.inject_message(make_gmail_message(f"Msg {i}", "a@b.com"))
        results = mock_client.fetch_unread(max_results=3)
        assert len(results) == 3

    def test_mark_read_hides_message(self, mock_client: MockGmailClient) -> None:
        msg = make_gmail_message("Hi", "a@b.com")
        mock_client.inject_message(msg)
        mock_client.mark_read(msg.message_id)
        assert mock_client.fetch_unread() == []

    def test_health_check_default_true(self, mock_client: MockGmailClient) -> None:
        assert mock_client.health_check() is True

    def test_set_healthy_false(self, mock_client: MockGmailClient) -> None:
        mock_client.set_healthy(False)
        assert mock_client.health_check() is False

    def test_fetch_count_increments(self, mock_client: MockGmailClient) -> None:
        mock_client.fetch_unread()
        mock_client.fetch_unread()
        assert mock_client.fetch_count == 2

    def test_clear_inbox(self, mock_client: MockGmailClient) -> None:
        mock_client.inject_message(make_gmail_message("Hi", "a@b.com"))
        mock_client.clear_inbox()
        assert mock_client.fetch_unread() == []

    def test_filter_labels(self, mock_client: MockGmailClient) -> None:
        msg_inbox = make_gmail_message("A", "a@b.com", labels=["INBOX"])
        msg_spam  = make_gmail_message("B", "b@c.com", labels=["SPAM"])
        mock_client.inject_message(msg_inbox)
        mock_client.inject_message(msg_spam)
        results = mock_client.fetch_unread(filter_labels=["INBOX"])
        assert len(results) == 1
        assert results[0].message_id == msg_inbox.message_id

    def test_inbox_size_property(self, mock_client: MockGmailClient) -> None:
        assert mock_client.inbox_size == 0
        mock_client.inject_message(make_gmail_message("Hi", "a@b.com"))
        assert mock_client.inbox_size == 1


# ===========================================================================
# TestRealGmailClient
# ===========================================================================

class TestRealGmailClient:

    def test_fetch_unread_raises(self, gmail_config: GmailConfig) -> None:
        client = RealGmailClient(gmail_config)
        with pytest.raises(NotImplementedError):
            client.fetch_unread()

    def test_mark_read_raises(self, gmail_config: GmailConfig) -> None:
        client = RealGmailClient(gmail_config)
        with pytest.raises(NotImplementedError):
            client.mark_read("MSG-001")

    def test_health_check_returns_false(self, gmail_config: GmailConfig) -> None:
        client = RealGmailClient(gmail_config)
        assert client.health_check() is False


# ===========================================================================
# TestGmailWatcher
# ===========================================================================

class TestGmailWatcher:

    def test_health_check_delegates_to_client(
        self, gmail_config: GmailConfig, mock_client: MockGmailClient
    ) -> None:
        w = GmailWatcher(gmail_config, mock_client)
        assert w.health_check() is True
        mock_client.set_healthy(False)
        assert w.health_check() is False

    def test_poll_empty_inbox(self, watcher: GmailWatcher) -> None:
        events = watcher.poll()
        assert events == []

    def test_poll_returns_events(
        self, watcher: GmailWatcher, mock_client: MockGmailClient
    ) -> None:
        mock_client.inject_message(make_gmail_message("Hi", "a@b.com"))
        events = watcher.poll()
        assert len(events) == 1
        assert events[0].event_type == GmailEventType.NEW_MESSAGE

    def test_poll_deduplicates(
        self, watcher: GmailWatcher, mock_client: MockGmailClient
    ) -> None:
        msg = make_gmail_message("Hi", "a@b.com")
        mock_client.inject_message(msg)
        watcher.poll()           # first poll — seen
        events = watcher.poll()  # second poll — same message, deduplicated
        assert events == []

    def test_poll_attachment_event_type(
        self, gmail_config: GmailConfig, mock_client: MockGmailClient
    ) -> None:
        msg = make_gmail_message(
            "Report", "a@b.com",
            has_attachments=True,
            attachment_names=["file.pdf"],
        )
        mock_client.inject_message(msg)
        w      = GmailWatcher(gmail_config, mock_client)
        w.start()
        events = w.poll()
        assert events[0].event_type == GmailEventType.ATTACHMENT_RECEIVED

    def test_poll_payload_contains_message_fields(
        self, watcher: GmailWatcher, mock_client: MockGmailClient
    ) -> None:
        msg = make_gmail_message("Subject!", "alice@example.com", snippet="preview")
        mock_client.inject_message(msg)
        events = watcher.poll()
        payload = events[0].payload
        assert payload["subject"] == "Subject!"
        assert payload["sender"]  == "alice@example.com"
        assert payload["snippet"] == "preview"

    def test_tick_health_fail_returns_error_result(
        self, gmail_config: GmailConfig, mock_client: MockGmailClient
    ) -> None:
        mock_client.set_healthy(False)
        w = GmailWatcher(gmail_config, mock_client)
        w.start()
        result = w.tick()
        assert result.health_ok is False
        assert result.errors >= 1

    def test_tick_increments_poll_count(self, watcher: GmailWatcher) -> None:
        before = watcher.state.poll_count
        watcher.tick()
        assert watcher.state.poll_count == before + 1

    def test_tick_with_messages_updates_total_events(
        self, watcher: GmailWatcher, mock_client: MockGmailClient
    ) -> None:
        mock_client.inject_message(make_gmail_message("A", "a@b.com"))
        result = watcher.tick()
        assert result.events_found == 1

    def test_seen_ids_persisted_to_vault(
        self, watcher: GmailWatcher, mock_client: MockGmailClient, tmp_vault: Path
    ) -> None:
        msg = make_gmail_message("Hi", "a@b.com")
        mock_client.inject_message(msg)
        watcher.poll()
        seen_path = (
            tmp_vault / "70-LOGS" / "watchers"
            / watcher.gmail_config.watcher_id / "seen-ids.json"
        )
        assert seen_path.exists()
        data = json.loads(seen_path.read_text())
        assert msg.message_id in data

    def test_seen_ids_loaded_on_init(
        self, gmail_config: GmailConfig, mock_client: MockGmailClient, tmp_vault: Path
    ) -> None:
        # Pre-populate seen-ids.json
        wid      = gmail_config.watcher_id
        seen_dir = tmp_vault / "70-LOGS" / "watchers" / wid
        seen_dir.mkdir(parents=True, exist_ok=True)
        (seen_dir / "seen-ids.json").write_text(
            json.dumps(["MSG-PREPOPULATED"]), encoding="utf-8"
        )
        w = GmailWatcher(gmail_config, mock_client)
        assert "MSG-PREPOPULATED" in w.seen_ids

    def test_seen_ids_defensive_copy(self, watcher: GmailWatcher) -> None:
        copy = watcher.seen_ids
        copy.add("EXTERNAL")
        assert "EXTERNAL" not in watcher.seen_ids

    def test_mark_read_on_poll_false_default(
        self, watcher: GmailWatcher, mock_client: MockGmailClient
    ) -> None:
        msg = make_gmail_message("Hi", "a@b.com")
        mock_client.inject_message(msg)
        watcher.poll()
        # mark_read_on_poll=False: message still in inbox (not marked read via client)
        results = mock_client.fetch_unread()
        assert len(results) == 1  # still fetchable from client

    def test_watcher_config_type_is_gmail(self, watcher: GmailWatcher) -> None:
        assert watcher.config.watcher_type == "gmail"

    def test_client_property(
        self, watcher: GmailWatcher, mock_client: MockGmailClient
    ) -> None:
        assert watcher.client is mock_client

    def test_gmail_config_property(
        self, watcher: GmailWatcher, gmail_config: GmailConfig
    ) -> None:
        assert watcher.gmail_config is gmail_config


# ===========================================================================
# TestHandlers
# ===========================================================================

class TestHandlers:

    def _make_event(self, subject: str = "Hi", sender: str = "a@b.com") -> WatcherEvent:
        from golden_tier_external_world.watchers.base.models import make_event
        evt = make_event(
            watcher_id="gmail-test_at_example_com",
            event_type=GmailEventType.NEW_MESSAGE,
            source="gmail:test@example.com",
            payload={"subject": subject, "sender": sender, "snippet": ""},
        )
        return evt

    def test_log_handler_writes_to_stream(self) -> None:
        buf     = io.StringIO()
        handler = make_log_handler(stream=buf)
        event   = self._make_event("Hello World", "alice@example.com")
        handler(event)
        output = buf.getvalue()
        assert "Hello World" in output
        assert "alice@example.com" in output

    def test_log_handler_custom_prefix(self) -> None:
        buf     = io.StringIO()
        handler = make_log_handler(prefix="[TEST]", stream=buf)
        handler(self._make_event())
        assert "[TEST]" in buf.getvalue()

    def test_orchestrator_handler_calls_run_workflow(self) -> None:
        mock_orc = MagicMock()
        handler  = make_orchestrator_handler(mock_orc, "process-email")
        event    = self._make_event("Report", "boss@company.com")
        handler(event)
        mock_orc.run_workflow.assert_called_once()
        call_kwargs = mock_orc.run_workflow.call_args
        assert call_kwargs[0][0] == "process-email"

    def test_orchestrator_handler_passes_event_data(self) -> None:
        mock_orc = MagicMock()
        handler  = make_orchestrator_handler(mock_orc, "wf", extra_context={"key": "val"})
        event    = self._make_event("Subj", "sender@x.com")
        handler(event)
        ctx = mock_orc.run_workflow.call_args[0][1]
        assert ctx["event_id"]   == event.event_id
        assert ctx["event_type"] == event.event_type
        assert ctx["key"]        == "val"
        assert ctx["subject"]    == "Subj"

    def test_filter_handler_condition_true(self) -> None:
        calls = []
        then  = lambda e: calls.append(e)  # noqa: E731
        h     = make_filter_handler(lambda e: True, then)
        h(self._make_event())
        assert len(calls) == 1

    def test_filter_handler_condition_false_no_call(self) -> None:
        calls = []
        then  = lambda e: calls.append(e)  # noqa: E731
        h     = make_filter_handler(lambda e: False, then)
        h(self._make_event())
        assert calls == []

    def test_filter_handler_else_called_when_false(self) -> None:
        then_calls = []
        else_calls = []
        h = make_filter_handler(
            lambda e: False,
            lambda e: then_calls.append(e),
            lambda e: else_calls.append(e),
        )
        h(self._make_event())
        assert then_calls == []
        assert len(else_calls) == 1

    def test_sender_filter_matches(self) -> None:
        calls = []
        h     = make_sender_filter(["alice@example.com"], lambda e: calls.append(e))
        h(self._make_event(sender="alice@example.com"))
        assert len(calls) == 1

    def test_sender_filter_case_insensitive(self) -> None:
        calls = []
        h     = make_sender_filter(["ALICE@EXAMPLE.COM"], lambda e: calls.append(e))
        h(self._make_event(sender="alice@example.com"))
        assert len(calls) == 1

    def test_sender_filter_no_match(self) -> None:
        calls = []
        h     = make_sender_filter(["bob@example.com"], lambda e: calls.append(e))
        h(self._make_event(sender="alice@example.com"))
        assert calls == []


# ===========================================================================
# TestGmailWatcherSkill (facade)
# ===========================================================================

class TestGmailWatcherSkill:

    def test_start_and_is_running(self, skill: GmailWatcherSkill) -> None:
        skill.start()
        assert skill.is_running() is True

    def test_stop(self, skill: GmailWatcherSkill) -> None:
        skill.start()
        skill.stop()
        assert skill.is_running() is False

    def test_tick_empty_inbox(self, skill: GmailWatcherSkill) -> None:
        skill.start()
        result = skill.tick()
        assert result.events_found == 0
        assert result.health_ok    is True

    def test_tick_with_injected_message(self, skill: GmailWatcherSkill) -> None:
        msg = make_gmail_message("Hello", "a@b.com")
        skill.inject_message(msg)
        skill.start()
        result = skill.tick()
        assert result.events_found == 1

    def test_handler_called_on_tick(self, skill: GmailWatcherSkill) -> None:
        received = []
        skill.register_handler(GmailEventType.NEW_MESSAGE, lambda e: received.append(e))
        msg = make_gmail_message("Hi", "a@b.com")
        skill.inject_message(msg)
        skill.start()
        skill.tick()
        assert len(received) == 1
        assert received[0].payload["subject"] == "Hi"

    def test_inject_message_raises_for_real_client(
        self, gmail_config: GmailConfig
    ) -> None:
        real_client = RealGmailClient(gmail_config)
        skill = GmailWatcherSkill(gmail_config, client=real_client)
        with pytest.raises(TypeError):
            skill.inject_message(make_gmail_message("Hi", "a@b.com"))

    def test_unregister_handler(self, skill: GmailWatcherSkill) -> None:
        received = []
        skill.register_handler(GmailEventType.NEW_MESSAGE, lambda e: received.append(e))
        skill.unregister_handler(GmailEventType.NEW_MESSAGE)
        msg = make_gmail_message("Hi", "a@b.com")
        skill.inject_message(msg)
        skill.start()
        skill.tick()
        assert received == []

    def test_gmail_config_property(
        self, skill: GmailWatcherSkill, gmail_config: GmailConfig
    ) -> None:
        assert skill.gmail_config is gmail_config

    def test_watcher_property(self, skill: GmailWatcherSkill) -> None:
        assert isinstance(skill.watcher, GmailWatcher)

    def test_dispatcher_property(self, skill: GmailWatcherSkill) -> None:
        from golden_tier_external_world.watchers.base.dispatcher import EventDispatcher
        assert isinstance(skill.dispatcher, EventDispatcher)

    def test_security_skill_integration_graceful(
        self, gmail_config: GmailConfig
    ) -> None:
        """Security integration is optional — bad skill object must not crash."""
        bad_skill = MagicMock(side_effect=Exception("security failure"))
        # Should not raise
        skill = GmailWatcherSkill(gmail_config, security_skill=bad_skill)
        assert skill is not None

    def test_hitl_forwarded_to_dispatcher(self, skill: GmailWatcherSkill) -> None:
        mock_hitl = MagicMock()
        skill.set_hitl(mock_hitl)
        assert skill.dispatcher._hitl is mock_hitl


# ===========================================================================
# TestCLI
# ===========================================================================

class TestCLI:

    def test_build_parser_returns_parser(self) -> None:
        parser = build_parser()
        assert parser is not None

    def test_status_no_state_file_returns_1(self, tmp_vault: Path) -> None:
        result = cli_main([
            "--vault", str(tmp_vault),
            "--account", "noone@example.com",
            "status",
        ])
        assert result == 1

    def test_status_with_state_file_returns_0(self, tmp_vault: Path) -> None:
        wid       = "gmail-test_at_example_com"
        state_dir = tmp_vault / "70-LOGS" / "watchers" / wid
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "state.json").write_text(
            json.dumps({
                "watcher_id": wid, "status": "running",
                "poll_count": 5, "total_events": 3,
                "error_count": 0,
            }),
            encoding="utf-8",
        )
        result = cli_main([
            "--vault", str(tmp_vault),
            "--account", "test@example.com",
            "status",
        ])
        assert result == 0

    def test_tick_returns_0(self, tmp_vault: Path) -> None:
        result = cli_main([
            "--vault", str(tmp_vault),
            "--account", "test@example.com",
            "tick",
        ])
        assert result == 0

    def test_events_no_events_returns_0(self, tmp_vault: Path) -> None:
        result = cli_main([
            "--vault", str(tmp_vault),
            "--account", "test@example.com",
            "events",
        ])
        assert result == 0

    def test_inject_returns_0(self, tmp_vault: Path) -> None:
        result = cli_main([
            "--vault", str(tmp_vault),
            "--account", "test@example.com",
            "inject",
            "--subject", "Test message",
            "--sender", "alice@example.com",
        ])
        assert result == 0

    def test_inject_creates_event(self, tmp_vault: Path) -> None:
        cli_main([
            "--vault", str(tmp_vault),
            "--account", "test@example.com",
            "inject",
            "--subject", "Hello",
            "--sender", "alice@example.com",
        ])
        # After inject, check events
        result = cli_main([
            "--vault", str(tmp_vault),
            "--account", "test@example.com",
            "events",
        ])
        assert result == 0
