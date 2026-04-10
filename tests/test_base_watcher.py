"""
Unit tests for BASE_WATCHER_CREATION_SKILL Phase 1.

Coverage areas:
  - Models: WatcherConfig, WatcherEvent, WatcherState, WatcherTickResult, DispatchResult, make_event
  - BaseWatcher: concrete subclass, tick lifecycle, health failure, poll failure, start/stop
  - WatcherRegistry: register, get, require, unregister, list_all, list_running, list_ids
  - EventDispatcher: handlers, tier-0 direct, tier-2 no-HITL fail_open, wildcard, errors
  - EventStore: save, load_by_date, mark_processed, event_count, missing date
  - WatcherLogger: log_poll, log_event, log_error, log_start, log_stop — file creation
  - WatcherSkill: facade integration
  - CLI: build_parser, list, status, events

Run with:
    python -m pytest tests/test_base_watcher.py -v
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pytest

from golden_tier_external_world.watchers.base import (
    BaseWatcher,
    DispatchResult,
    EventDispatcher,
    EventStore,
    EventType,
    WatcherConfig,
    WatcherEvent,
    WatcherLogger,
    WatcherNotFoundError,
    WatcherRegistry,
    WatcherSkill,
    WatcherState,
    WatcherStatus,
    WatcherTickResult,
    make_event,
)
from golden_tier_external_world.watchers.base.cli import build_parser, main as cli_main


# ===========================================================================
# Helpers — concrete test watchers
# ===========================================================================

class _HealthyWatcher(BaseWatcher):
    """Returns a fixed list of events every tick."""

    def __init__(self, config: WatcherConfig, events: Optional[list] = None) -> None:
        super().__init__(config)
        self._events = events or []

    def poll(self) -> list[WatcherEvent]:
        return list(self._events)

    def health_check(self) -> bool:
        return True


class _UnhealthyWatcher(BaseWatcher):
    def poll(self) -> list[WatcherEvent]:
        return []

    def health_check(self) -> bool:
        return False


class _PollErrorWatcher(BaseWatcher):
    def poll(self) -> list[WatcherEvent]:
        raise RuntimeError("Connection refused")

    def health_check(self) -> bool:
        return True


class _HealthCheckErrorWatcher(BaseWatcher):
    def poll(self) -> list[WatcherEvent]:
        return []

    def health_check(self) -> bool:
        raise RuntimeError("Network unreachable")


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    return tmp_path / "obsidian-vault"


@pytest.fixture()
def config(vault: Path) -> WatcherConfig:
    return WatcherConfig(
        watcher_id="test-watcher",
        watcher_type="test",
        vault_root=str(vault),
        poll_interval_secs=10.0,
        tier=1,
    )


@pytest.fixture()
def watcher(config: WatcherConfig) -> _HealthyWatcher:
    return _HealthyWatcher(config)


@pytest.fixture()
def store(vault: Path) -> EventStore:
    return EventStore(vault)


@pytest.fixture()
def logger(vault: Path) -> WatcherLogger:
    return WatcherLogger(vault)


@pytest.fixture()
def dispatcher() -> EventDispatcher:
    return EventDispatcher(fail_open=True)


@pytest.fixture()
def registry() -> WatcherRegistry:
    return WatcherRegistry()


@pytest.fixture()
def skill(vault: Path) -> WatcherSkill:
    return WatcherSkill(vault_root=vault)


# ===========================================================================
# 1. Models
# ===========================================================================

class TestWatcherConfig:
    def test_defaults(self):
        cfg = WatcherConfig(watcher_id="x", watcher_type="fs")
        assert cfg.poll_interval_secs == 30.0
        assert cfg.enabled is True
        assert cfg.tier == 2

    def test_round_trip(self, config: WatcherConfig):
        cfg2 = WatcherConfig.from_dict(config.to_dict())
        assert cfg2.watcher_id == config.watcher_id
        assert cfg2.watcher_type == config.watcher_type
        assert cfg2.tier == config.tier


class TestWatcherEvent:
    def test_make_event_unique_ids(self):
        e1 = make_event("w1", "file_created", "fs:dir")
        e2 = make_event("w1", "file_created", "fs:dir")
        assert e1.event_id != e2.event_id

    def test_make_event_defaults(self):
        e = make_event("w1", "generic", "src")
        assert e.event_id.startswith("EVT-")
        assert e.tier == 2
        assert e.processed is False
        assert isinstance(e.timestamp, datetime)

    def test_make_event_with_payload(self):
        e = make_event("w1", "file_created", "fs", {"path": "/tmp/file.md"}, tier=1)
        assert e.payload["path"] == "/tmp/file.md"
        assert e.tier == 1

    def test_round_trip(self):
        e = make_event("w1", "message_received", "gmail:inbox", {"subject": "hi"})
        e2 = WatcherEvent.from_dict(e.to_dict())
        assert e2.event_id == e.event_id
        assert e2.event_type == e.event_type
        assert e2.payload == e.payload

    def test_processed_field_preserved(self):
        e = make_event("w1", "generic", "src")
        e.processed = True
        e2 = WatcherEvent.from_dict(e.to_dict())
        assert e2.processed is True


class TestWatcherState:
    def test_defaults(self):
        s = WatcherState(watcher_id="x")
        assert s.status == WatcherStatus.IDLE
        assert s.poll_count == 0
        assert s.error_count == 0

    def test_round_trip(self):
        s = WatcherState(watcher_id="x", status=WatcherStatus.RUNNING, poll_count=5)
        s.started_at = datetime.now(tz=timezone.utc)
        s2 = WatcherState.from_dict(s.to_dict())
        assert s2.watcher_id == "x"
        assert s2.status == WatcherStatus.RUNNING
        assert s2.poll_count == 5
        assert s2.started_at is not None


class TestWatcherTickResult:
    def test_to_dict(self):
        r = WatcherTickResult(
            watcher_id="w", poll_count=3, events_found=2,
            events_dispatched=2, errors=0, health_ok=True, duration_ms=5.0,
        )
        d = r.to_dict()
        assert d["events_found"] == 2
        assert d["health_ok"] is True


class TestDispatchResult:
    def test_to_dict(self):
        r = DispatchResult(
            event_id="EVT-001", dispatched=True,
            handler_called=True, hitl_submitted=False,
        )
        d = r.to_dict()
        assert d["dispatched"] is True
        assert d["hitl_submitted"] is False


class TestEventTypeEnum:
    def test_values_are_strings(self):
        assert EventType.GENERIC == "generic"
        assert EventType.FILE_CREATED == "file_created"


# ===========================================================================
# 2. BaseWatcher
# ===========================================================================

class TestBaseWatcher:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseWatcher(WatcherConfig("x", "fs"))  # type: ignore

    def test_start_sets_running(self, watcher: _HealthyWatcher):
        watcher.start()
        assert watcher.is_running() is True
        assert watcher.state.status == WatcherStatus.RUNNING
        assert watcher.state.started_at is not None

    def test_stop_sets_stopped(self, watcher: _HealthyWatcher):
        watcher.start()
        watcher.stop()
        assert watcher.is_running() is False
        assert watcher.state.status == WatcherStatus.STOPPED

    def test_tick_no_events(self, watcher: _HealthyWatcher):
        result = watcher.tick()
        assert result.events_found == 0
        assert result.health_ok is True
        assert result.errors == 0
        assert result.poll_count == 1

    def test_tick_with_events(self, config: WatcherConfig):
        events = [make_event("test-watcher", "file_created", "fs:dir", tier=1)]
        w = _HealthyWatcher(config, events=events)
        result = w.tick()
        assert result.events_found == 1
        assert result.events_dispatched == 1  # no dispatcher → counted as dispatched

    def test_tick_increments_poll_count(self, watcher: _HealthyWatcher):
        watcher.tick()
        watcher.tick()
        assert watcher.state.poll_count == 2

    def test_tick_health_failure_returns_early(self, config: WatcherConfig):
        w = _UnhealthyWatcher(config)
        result = w.tick()
        assert result.health_ok is False
        assert result.events_found == 0
        assert result.errors == 1
        assert result.error_message is not None

    def test_tick_health_check_exception(self, config: WatcherConfig):
        w = _HealthCheckErrorWatcher(config)
        result = w.tick()
        assert result.health_ok is False
        assert "health_check raised" in (result.error_message or "")

    def test_tick_poll_error_captured(self, config: WatcherConfig):
        w = _PollErrorWatcher(config)
        result = w.tick()
        assert result.health_ok is True  # health ok
        assert result.errors == 1        # poll failed
        assert result.events_found == 0

    def test_tick_updates_total_events(self, config: WatcherConfig):
        events = [
            make_event("test-watcher", "generic", "src", tier=1),
            make_event("test-watcher", "generic", "src", tier=1),
        ]
        w = _HealthyWatcher(config, events=events)
        w.tick()
        assert w.state.total_events == 2

    def test_tick_updates_last_event_at(self, config: WatcherConfig):
        events = [make_event("test-watcher", "generic", "src", tier=1)]
        w = _HealthyWatcher(config, events=events)
        w.tick()
        assert w.state.last_event_at is not None

    def test_config_property(self, watcher: _HealthyWatcher, config: WatcherConfig):
        assert watcher.config.watcher_id == config.watcher_id

    def test_state_persisted_to_vault(self, config: WatcherConfig, vault: Path):
        w = _HealthyWatcher(config)
        w.start()
        state_path = vault / "70-LOGS" / "watchers" / config.watcher_id / "state.json"
        assert state_path.exists()
        data = json.loads(state_path.read_text())
        assert data["status"] == "running"


# ===========================================================================
# 3. WatcherRegistry
# ===========================================================================

class TestWatcherRegistry:
    def test_register_and_get(self, registry: WatcherRegistry, watcher: _HealthyWatcher):
        registry.register(watcher)
        assert registry.get("test-watcher") is watcher

    def test_get_unknown_returns_none(self, registry: WatcherRegistry):
        assert registry.get("no-such") is None

    def test_require_raises_on_missing(self, registry: WatcherRegistry):
        with pytest.raises(WatcherNotFoundError):
            registry.require("no-such")

    def test_require_returns_watcher(self, registry: WatcherRegistry, watcher: _HealthyWatcher):
        registry.register(watcher)
        assert registry.require("test-watcher") is watcher

    def test_unregister_returns_true(self, registry: WatcherRegistry, watcher: _HealthyWatcher):
        registry.register(watcher)
        assert registry.unregister("test-watcher") is True

    def test_unregister_unknown_returns_false(self, registry: WatcherRegistry):
        assert registry.unregister("nobody") is False

    def test_list_all(self, registry: WatcherRegistry, watcher: _HealthyWatcher):
        registry.register(watcher)
        assert len(registry.list_all()) == 1

    def test_list_running_only_running(self, registry: WatcherRegistry, config: WatcherConfig):
        w1 = _HealthyWatcher(config)
        w1.start()
        cfg2 = WatcherConfig(watcher_id="w2", watcher_type="test", vault_root=config.vault_root)
        w2 = _HealthyWatcher(cfg2)
        registry.register(w1)
        registry.register(w2)
        running = registry.list_running()
        assert len(running) == 1
        assert running[0].config.watcher_id == "test-watcher"

    def test_list_ids(self, registry: WatcherRegistry, watcher: _HealthyWatcher):
        registry.register(watcher)
        assert "test-watcher" in registry.list_ids()

    def test_overwrite_existing(self, registry: WatcherRegistry, config: WatcherConfig):
        w1 = _HealthyWatcher(config)
        w2 = _HealthyWatcher(config)
        registry.register(w1)
        registry.register(w2)
        assert registry.get("test-watcher") is w2
        assert registry.count() == 1

    def test_is_registered(self, registry: WatcherRegistry, watcher: _HealthyWatcher):
        assert registry.is_registered("test-watcher") is False
        registry.register(watcher)
        assert registry.is_registered("test-watcher") is True


# ===========================================================================
# 4. EventDispatcher
# ===========================================================================

class TestEventDispatcher:
    def _tier1_event(self) -> WatcherEvent:
        return make_event("w1", "file_created", "fs:dir", tier=1)

    def _tier2_event(self) -> WatcherEvent:
        return make_event("w1", "message_received", "gmail", tier=2)

    def test_tier0_direct_dispatch(self, dispatcher: EventDispatcher):
        e = make_event("w1", "generic", "src", tier=0)
        result = dispatcher.dispatch(e)
        assert result.dispatched is True
        assert result.hitl_submitted is False

    def test_handler_called_for_tier1(self, dispatcher: EventDispatcher):
        received = []
        dispatcher.register_handler("file_created", received.append)
        e = self._tier1_event()
        result = dispatcher.dispatch(e)
        assert result.handler_called is True
        assert len(received) == 1

    def test_no_handler_still_dispatched(self, dispatcher: EventDispatcher):
        e = self._tier1_event()
        result = dispatcher.dispatch(e)
        assert result.dispatched is True
        assert result.handler_called is False

    def test_wildcard_handler_receives_all_events(self, dispatcher: EventDispatcher):
        received = []
        dispatcher.register_handler("*", received.append)
        dispatcher.dispatch(make_event("w1", "file_created", "fs", tier=1))
        dispatcher.dispatch(make_event("w1", "file_modified", "fs", tier=1))
        assert len(received) == 2

    def test_tier2_no_hitl_fail_open_dispatches_directly(self, dispatcher: EventDispatcher):
        received = []
        dispatcher.register_handler("message_received", received.append)
        e = self._tier2_event()
        result = dispatcher.dispatch(e)
        # fail_open=True → direct dispatch
        assert result.dispatched is True
        assert result.hitl_submitted is False
        assert len(received) == 1

    def test_tier2_fail_closed_does_not_dispatch(self):
        d = EventDispatcher(fail_open=False)
        e = make_event("w1", "generic", "src", tier=2)
        result = d.dispatch(e)
        assert result.dispatched is False
        assert "not configured" in (result.error or "").lower()

    def test_handler_exception_captured(self, dispatcher: EventDispatcher):
        def bad_handler(e):
            raise ValueError("handler crash")
        dispatcher.register_handler("generic", bad_handler)
        e = make_event("w1", "generic", "src", tier=0)
        result = dispatcher.dispatch(e)
        assert result.dispatched is True  # dispatch succeeds even if handler raises

    def test_multiple_handlers_called_in_order(self, dispatcher: EventDispatcher):
        order = []
        dispatcher.register_handler("generic", lambda e: order.append("first"))
        dispatcher.register_handler("generic", lambda e: order.append("second"))
        dispatcher.dispatch(make_event("w1", "generic", "src", tier=0))
        assert order == ["first", "second"]

    def test_unregister_handler(self, dispatcher: EventDispatcher):
        received = []
        dispatcher.register_handler("generic", received.append)
        dispatcher.unregister_handler("generic")
        dispatcher.dispatch(make_event("w1", "generic", "src", tier=0))
        assert received == []

    def test_list_handlers(self, dispatcher: EventDispatcher):
        dispatcher.register_handler("file_created", lambda e: None)
        dispatcher.register_handler("file_created", lambda e: None)
        dispatcher.register_handler("*", lambda e: None)
        h = dispatcher.list_handlers()
        assert h["file_created"] == 2
        assert h["*"] == 1


# ===========================================================================
# 5. EventStore
# ===========================================================================

class TestEventStore:
    def test_save_and_load_today(self, store: EventStore):
        e = make_event("w1", "generic", "src")
        store.save(e)
        events = store.load_by_date("w1")
        assert any(x.event_id == e.event_id for x in events)

    def test_load_by_date_empty_for_unknown(self, store: EventStore):
        events = store.load_by_date("w1", "1999-01-01")
        assert events == []

    def test_load_by_date_specific_date(self, store: EventStore):
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        e = make_event("w2", "file_created", "fs")
        store.save(e)
        events = store.load_by_date("w2", today)
        assert len(events) >= 1

    def test_event_count(self, store: EventStore):
        store.save(make_event("w3", "generic", "s"))
        store.save(make_event("w3", "generic", "s"))
        assert store.event_count("w3") == 2

    def test_mark_processed(self, store: EventStore):
        e = make_event("w4", "generic", "s")
        store.save(e)
        updated = store.mark_processed("w4", e.event_id)
        assert updated is True
        events = store.load_by_date("w4")
        assert events[0].processed is True

    def test_mark_processed_unknown_event(self, store: EventStore):
        updated = store.mark_processed("w4", "EVT-NOTEXIST")
        assert updated is False

    def test_multiple_watcher_ids_isolated(self, store: EventStore):
        store.save(make_event("watcher-a", "generic", "s"))
        store.save(make_event("watcher-b", "generic", "s"))
        a_events = store.load_by_date("watcher-a")
        b_events = store.load_by_date("watcher-b")
        assert len(a_events) == 1
        assert len(b_events) == 1

    def test_round_trip_preserves_payload(self, store: EventStore):
        e = make_event("w1", "file_created", "fs", {"path": "/vault/file.md"}, tier=1)
        store.save(e)
        loaded = store.load_by_date("w1")
        found = next(x for x in loaded if x.event_id == e.event_id)
        assert found.payload["path"] == "/vault/file.md"


# ===========================================================================
# 6. WatcherLogger
# ===========================================================================

class TestWatcherLogger:
    def test_log_poll_creates_daily_file(self, logger: WatcherLogger, vault: Path):
        logger.log_poll("wl-test", events_found=3)
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        log_path = vault / "70-LOGS" / "watchers" / "wl-test" / "daily" / f"{today}.md"
        assert log_path.exists()
        content = log_path.read_text()
        assert "POLL" in content

    def test_log_error_creates_error_file(self, logger: WatcherLogger, vault: Path):
        logger.log_error("wl-test", "Connection timed out")
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        err_path = vault / "70-LOGS" / "watchers" / "wl-test" / "errors" / f"{today}-errors.md"
        assert err_path.exists()
        assert "Connection timed out" in err_path.read_text()

    def test_log_start_writes_entry(self, logger: WatcherLogger, vault: Path):
        logger.log_start("wl-start")
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        path = vault / "70-LOGS" / "watchers" / "wl-start" / "daily" / f"{today}.md"
        assert "START" in path.read_text()

    def test_log_stop_writes_entry(self, logger: WatcherLogger, vault: Path):
        logger.log_stop("wl-stop")
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        path = vault / "70-LOGS" / "watchers" / "wl-stop" / "daily" / f"{today}.md"
        assert "STOP" in path.read_text()

    def test_log_event_writes_metadata(self, logger: WatcherLogger, vault: Path):
        e = make_event("wl-test", "file_created", "fs:dir")
        logger.log_event(e)
        date = e.timestamp.strftime("%Y-%m-%d")
        path = vault / "70-LOGS" / "watchers" / "wl-test" / "daily" / f"{date}.md"
        content = path.read_text()
        assert e.event_id in content
        assert "file_created" in content

    def test_logger_fail_safe_no_raise(self, vault: Path):
        """Logger must not raise even if vault root is bad."""
        bad_logger = WatcherLogger("/nonexistent/path/that/cannot/be/written")
        # Should not raise
        bad_logger.log_poll("x", 0)
        bad_logger.log_error("x", "some error")


# ===========================================================================
# 7. WatcherSkill (facade)
# ===========================================================================

class TestWatcherSkill:
    def test_register_and_list(self, skill: WatcherSkill, watcher: _HealthyWatcher):
        skill.register_watcher(watcher)
        assert "test-watcher" in skill.list_watchers()

    def test_tick_watcher_success(self, skill: WatcherSkill, config: WatcherConfig):
        w = _HealthyWatcher(config)
        skill.register_watcher(w)
        result = skill.tick_watcher("test-watcher")
        assert result.health_ok is True
        assert result.poll_count == 1

    def test_tick_watcher_not_found_raises(self, skill: WatcherSkill):
        with pytest.raises(WatcherNotFoundError):
            skill.tick_watcher("no-such-watcher")

    def test_tick_all_returns_all(self, skill: WatcherSkill, config: WatcherConfig):
        cfg2 = WatcherConfig("w2", "test", vault_root=config.vault_root)
        skill.register_watcher(_HealthyWatcher(config))
        skill.register_watcher(_HealthyWatcher(cfg2))
        results = skill.tick_all()
        assert "test-watcher" in results
        assert "w2" in results

    def test_tick_all_resilient_to_errors(self, skill: WatcherSkill, config: WatcherConfig):
        skill.register_watcher(_HealthyWatcher(config))
        cfg2 = WatcherConfig("err-watcher", "test", vault_root=config.vault_root)
        skill.register_watcher(_UnhealthyWatcher(cfg2))
        results = skill.tick_all()
        assert results["test-watcher"].health_ok is True
        assert results["err-watcher"].health_ok is False

    def test_get_events_empty_initially(self, skill: WatcherSkill):
        events = skill.get_events("nonexistent-watcher")
        assert events == []

    def test_get_events_after_tick(self, skill: WatcherSkill, config: WatcherConfig):
        events = [make_event("test-watcher", "generic", "src", tier=0)]
        w = _HealthyWatcher(config, events=events)
        skill.register_watcher(w)
        skill.tick_watcher("test-watcher")
        stored = skill.get_events("test-watcher")
        assert len(stored) >= 1

    def test_start_and_stop_watcher(self, skill: WatcherSkill, watcher: _HealthyWatcher):
        skill.register_watcher(watcher)
        skill.start_watcher("test-watcher")
        assert skill.is_running("test-watcher") is True
        skill.stop_watcher("test-watcher")
        assert skill.is_running("test-watcher") is False

    def test_start_not_found_raises(self, skill: WatcherSkill):
        with pytest.raises(WatcherNotFoundError):
            skill.start_watcher("ghost")

    def test_status_all_returns_list(self, skill: WatcherSkill, watcher: _HealthyWatcher):
        skill.register_watcher(watcher)
        status = skill.status_all()
        assert isinstance(status, list)
        assert len(status) == 1
        assert status[0]["watcher_id"] == "test-watcher"

    def test_register_handler_routes_events(self, skill: WatcherSkill, config: WatcherConfig):
        received = []
        skill.register_handler("generic", received.append)
        events = [make_event("test-watcher", "generic", "src", tier=0)]
        w = _HealthyWatcher(config, events=events)
        skill.register_watcher(w)
        skill.tick_watcher("test-watcher")
        assert len(received) == 1

    def test_unregister_watcher(self, skill: WatcherSkill, watcher: _HealthyWatcher):
        skill.register_watcher(watcher)
        skill.unregister_watcher("test-watcher")
        assert "test-watcher" not in skill.list_watchers()

    def test_is_running_false_for_unregistered(self, skill: WatcherSkill):
        assert skill.is_running("ghost") is False


# ===========================================================================
# 8. CLI
# ===========================================================================

class TestCLI:
    def test_build_parser_returns_parser(self):
        parser = build_parser()
        assert parser is not None

    def test_list_empty_vault(self, vault: Path):
        rc = cli_main(["--vault", str(vault), "list"])
        assert rc == 0

    def test_list_shows_watcher(self, vault: Path, config: WatcherConfig):
        # Create a watcher and trigger state persistence
        w = _HealthyWatcher(config)
        w.start()
        rc = cli_main(["--vault", str(vault), "list"])
        assert rc == 0

    def test_status_missing_watcher(self, vault: Path, capsys):
        rc = cli_main(["--vault", str(vault), "status", "--id", "nonexistent"])
        assert rc == 1

    def test_status_existing_watcher(self, vault: Path, config: WatcherConfig):
        w = _HealthyWatcher(config)
        w.start()
        rc = cli_main(["--vault", str(vault), "status", "--id", "test-watcher"])
        assert rc == 0

    def test_events_no_events(self, vault: Path):
        rc = cli_main(["--vault", str(vault), "events", "--id", "nobody"])
        assert rc == 0

    def test_events_with_stored_events(self, vault: Path, config: WatcherConfig):
        store = EventStore(vault)
        e = make_event("test-watcher", "generic", "src")
        store.save(e)
        rc = cli_main(["--vault", str(vault), "events", "--id", "test-watcher"])
        assert rc == 0
