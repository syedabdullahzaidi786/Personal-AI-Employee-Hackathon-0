"""
BROWSER_MCP_SKILL — Phase 1 Unit Tests
Target: ~80 tests, stdlib only.

Coverage:
  - BrowserActionType, BrowserActionStatus, BrowserEventType   (models.py)
  - BrowserRequest, BrowserResult, BrowserConfig               (models.py)
  - make_open_url_request, make_extract_text_request           (models.py)
  - BrowserAdapter ABC, MockBrowserAdapter, RealBrowserAdapter (adapter.py)
  - BrowserLogger read/write                                   (logger.py)
  - BrowserAction validation, direct execute, HITL gate        (action.py)
  - BrowserSkill facade, orchestrator/security integration     (__init__.py)
  - CLI: open, extract, status, logs                           (cli.py)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
from golden_tier_external_world.actions.browser.models import (
    BrowserActionStatus,
    BrowserActionType,
    BrowserConfig,
    BrowserEventType,
    BrowserRequest,
    BrowserResult,
    make_extract_text_request,
    make_open_url_request,
)
from golden_tier_external_world.actions.browser.adapter import (
    BrowserAdapter,
    MockBrowserAdapter,
    RealBrowserAdapter,
)
from golden_tier_external_world.actions.browser.logger import BrowserLogger
from golden_tier_external_world.actions.browser.action import BrowserAction, ValidationError, _validate
from golden_tier_external_world.actions.browser import BrowserSkill
from golden_tier_external_world.actions.browser.cli import build_parser, main as cli_main


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def browser_config(tmp_vault: Path) -> BrowserConfig:
    return BrowserConfig(vault_root=str(tmp_vault), default_tier=2)


@pytest.fixture
def low_tier_config(tmp_vault: Path) -> BrowserConfig:
    """Config with tier 1 — auto-executes without HITL."""
    return BrowserConfig(vault_root=str(tmp_vault), default_tier=1)


@pytest.fixture
def mock_adapter() -> MockBrowserAdapter:
    return MockBrowserAdapter()


@pytest.fixture
def skill(browser_config: BrowserConfig, mock_adapter: MockBrowserAdapter) -> BrowserSkill:
    return BrowserSkill(browser_config, adapter=mock_adapter)


@pytest.fixture
def low_tier_skill(low_tier_config: BrowserConfig) -> BrowserSkill:
    return BrowserSkill(low_tier_config, adapter=MockBrowserAdapter())


# ===========================================================================
# TestBrowserActionType
# ===========================================================================

class TestBrowserActionType:

    def test_constants_defined(self) -> None:
        assert BrowserActionType.OPEN_URL     == "open_url"
        assert BrowserActionType.EXTRACT_TEXT == "extract_text"


# ===========================================================================
# TestBrowserActionStatus
# ===========================================================================

class TestBrowserActionStatus:

    def test_constants_defined(self) -> None:
        assert BrowserActionStatus.PENDING_APPROVAL == "PENDING_APPROVAL"
        assert BrowserActionStatus.APPROVED         == "APPROVED"
        assert BrowserActionStatus.SUCCESS          == "SUCCESS"
        assert BrowserActionStatus.DENIED           == "DENIED"
        assert BrowserActionStatus.FAILED           == "FAILED"


# ===========================================================================
# TestBrowserEventType
# ===========================================================================

class TestBrowserEventType:

    def test_constants_defined(self) -> None:
        assert BrowserEventType.URL_OPENED         == "browser_url_opened"
        assert BrowserEventType.TEXT_EXTRACTED     == "browser_text_extracted"
        assert BrowserEventType.ACTION_DENIED      == "browser_action_denied"
        assert BrowserEventType.ACTION_FAILED      == "browser_action_failed"
        assert BrowserEventType.APPROVAL_REQUESTED == "browser_approval_requested"


# ===========================================================================
# TestBrowserRequest
# ===========================================================================

class TestBrowserRequest:

    def test_auto_request_id(self) -> None:
        req = BrowserRequest(action=BrowserActionType.OPEN_URL, url="https://example.com")
        assert req.request_id.startswith("BROWSER-")

    def test_auto_submitted_at_utc(self) -> None:
        req = BrowserRequest(action=BrowserActionType.OPEN_URL, url="https://example.com")
        assert req.submitted_at is not None
        assert req.submitted_at.tzinfo is not None

    def test_to_dict_keys(self) -> None:
        req = BrowserRequest(action=BrowserActionType.OPEN_URL, url="https://example.com")
        d   = req.to_dict()
        assert "request_id" in d
        assert "action"     in d
        assert "url"        in d
        assert "tier"       in d
        assert "selector"   in d

    def test_from_dict_roundtrip(self) -> None:
        req  = BrowserRequest(
            action=BrowserActionType.EXTRACT_TEXT,
            url="https://example.com",
            selector="h1",
            tier=1,
        )
        req2 = BrowserRequest.from_dict(req.to_dict())
        assert req2.request_id == req.request_id
        assert req2.action     == req.action
        assert req2.url        == req.url
        assert req2.selector   == req.selector
        assert req2.tier       == req.tier

    def test_defaults(self) -> None:
        req = BrowserRequest(action=BrowserActionType.OPEN_URL, url="https://x.com")
        assert req.selector         == ""
        assert req.tier             == 2
        assert req.credentials_name == "browser_credential"

    def test_unique_request_ids(self) -> None:
        r1 = BrowserRequest(action=BrowserActionType.OPEN_URL, url="https://a.com")
        r2 = BrowserRequest(action=BrowserActionType.OPEN_URL, url="https://b.com")
        assert r1.request_id != r2.request_id


# ===========================================================================
# TestBrowserResult
# ===========================================================================

class TestBrowserResult:

    def test_to_dict(self) -> None:
        res = BrowserResult(
            request_id="BROWSER-001",
            action=BrowserActionType.OPEN_URL,
            status=BrowserActionStatus.SUCCESS,
            url="https://example.com",
            content="Example Domain",
            status_code=200,
            adapter="mock",
            executed_at=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
        )
        d = res.to_dict()
        assert d["request_id"]  == "BROWSER-001"
        assert d["status"]      == "SUCCESS"
        assert d["status_code"] == 200
        assert "2026" in d["executed_at"]

    def test_content_preview_capped_at_500(self) -> None:
        res = BrowserResult(
            request_id="X", action="open_url", status="SUCCESS",
            content="x" * 1000,
        )
        assert len(res.to_dict()["content"]) == 500

    def test_to_dict_no_executed_at(self) -> None:
        res = BrowserResult(request_id="X", action="open_url", status="FAILED")
        assert res.to_dict()["executed_at"] is None


# ===========================================================================
# TestBrowserConfig
# ===========================================================================

class TestBrowserConfig:

    def test_to_dict_roundtrip(self) -> None:
        cfg  = BrowserConfig(vault_root="/vault", default_tier=1)
        cfg2 = BrowserConfig.from_dict(cfg.to_dict())
        assert cfg2.vault_root   == "/vault"
        assert cfg2.default_tier == 1

    def test_defaults(self) -> None:
        cfg = BrowserConfig()
        assert cfg.vault_root       == ""
        assert cfg.credentials_name == "browser_credential"
        assert cfg.default_tier     == 2


# ===========================================================================
# TestFactories
# ===========================================================================

class TestFactories:

    def test_make_open_url_request(self) -> None:
        req = make_open_url_request("https://example.com")
        assert isinstance(req, BrowserRequest)
        assert req.action == BrowserActionType.OPEN_URL
        assert req.url    == "https://example.com"
        assert req.tier   == 2

    def test_make_open_url_request_custom_tier(self) -> None:
        req = make_open_url_request("https://example.com", tier=1)
        assert req.tier == 1

    def test_make_extract_text_request(self) -> None:
        req = make_extract_text_request("https://example.com", selector="h1")
        assert req.action   == BrowserActionType.EXTRACT_TEXT
        assert req.selector == "h1"

    def test_make_extract_text_request_no_selector(self) -> None:
        req = make_extract_text_request("https://example.com")
        assert req.selector == ""


# ===========================================================================
# TestMockBrowserAdapter
# ===========================================================================

class TestMockBrowserAdapter:

    def test_open_url_returns_success(self, mock_adapter: MockBrowserAdapter) -> None:
        req    = make_open_url_request("https://example.com", tier=1)
        result = mock_adapter.execute(req)
        assert result.status      == BrowserActionStatus.SUCCESS
        assert result.status_code == 200
        assert result.content     != ""
        assert result.executed_at is not None

    def test_open_url_content_contains_host(self, mock_adapter: MockBrowserAdapter) -> None:
        req    = make_open_url_request("https://example.com", tier=1)
        result = mock_adapter.execute(req)
        assert "example.com" in result.content

    def test_extract_text_returns_success(self, mock_adapter: MockBrowserAdapter) -> None:
        req    = make_extract_text_request("https://example.com", selector="h1", tier=1)
        result = mock_adapter.execute(req)
        assert result.status      == BrowserActionStatus.SUCCESS
        assert result.status_code == 200
        assert result.content     != ""

    def test_extract_text_includes_selector_in_content(
        self, mock_adapter: MockBrowserAdapter
    ) -> None:
        req    = make_extract_text_request("https://x.com", selector="p.intro", tier=1)
        result = mock_adapter.execute(req)
        assert "p.intro" in result.content

    def test_inject_page_title(self, mock_adapter: MockBrowserAdapter) -> None:
        mock_adapter.inject_page("https://example.com", "Custom Title")
        req    = make_open_url_request("https://example.com", tier=1)
        result = mock_adapter.execute(req)
        assert result.content == "Custom Title"

    def test_inject_content(self, mock_adapter: MockBrowserAdapter) -> None:
        mock_adapter.inject_content("https://example.com", "Injected text")
        req    = make_extract_text_request("https://example.com", tier=1)
        result = mock_adapter.execute(req)
        assert result.content == "Injected text"

    def test_fail_execute_returns_failed(self) -> None:
        adapter = MockBrowserAdapter(fail_execute=True)
        req     = make_open_url_request("https://example.com", tier=1)
        result  = adapter.execute(req)
        assert result.status == BrowserActionStatus.FAILED
        assert result.error  != ""

    def test_set_fail_execute(self, mock_adapter: MockBrowserAdapter) -> None:
        mock_adapter.set_fail_execute(True)
        result = mock_adapter.execute(make_open_url_request("https://x.com", tier=1))
        assert result.status == BrowserActionStatus.FAILED

    def test_unknown_action_returns_failed(self, mock_adapter: MockBrowserAdapter) -> None:
        req = BrowserRequest(action="unknown_action", url="https://x.com", tier=1)
        result = mock_adapter.execute(req)
        assert result.status == BrowserActionStatus.FAILED

    def test_execute_count_increments(self, mock_adapter: MockBrowserAdapter) -> None:
        mock_adapter.execute(make_open_url_request("https://a.com", tier=1))
        mock_adapter.execute(make_open_url_request("https://b.com", tier=1))
        assert mock_adapter.execute_count == 2

    def test_results_captured(self, mock_adapter: MockBrowserAdapter) -> None:
        req = make_open_url_request("https://example.com", tier=1)
        mock_adapter.execute(req)
        assert len(mock_adapter.results) == 1

    def test_results_is_defensive_copy(self, mock_adapter: MockBrowserAdapter) -> None:
        mock_adapter.execute(make_open_url_request("https://x.com", tier=1))
        copy = mock_adapter.results
        copy.clear()
        assert len(mock_adapter.results) == 1

    def test_health_check_default_true(self, mock_adapter: MockBrowserAdapter) -> None:
        assert mock_adapter.health_check() is True

    def test_set_healthy_false(self, mock_adapter: MockBrowserAdapter) -> None:
        mock_adapter.set_healthy(False)
        assert mock_adapter.health_check() is False

    def test_clear_resets_state(self, mock_adapter: MockBrowserAdapter) -> None:
        mock_adapter.execute(make_open_url_request("https://x.com", tier=1))
        mock_adapter.inject_content("https://x.com", "text")
        mock_adapter.clear()
        assert mock_adapter.execute_count == 0
        assert mock_adapter.results       == []

    def test_content_capped_by_max_content_len(self, mock_adapter: MockBrowserAdapter) -> None:
        mock_adapter.inject_content("https://x.com", "x" * 100_000)
        req    = make_extract_text_request("https://x.com", tier=1)
        req.max_content_len = 200
        result = mock_adapter.execute(req)
        assert len(result.content) == 200


# ===========================================================================
# TestRealBrowserAdapter
# ===========================================================================

class TestRealBrowserAdapter:

    def test_execute_raises(self, browser_config: BrowserConfig) -> None:
        adapter = RealBrowserAdapter(browser_config)
        req     = make_open_url_request("https://example.com", tier=1)
        with pytest.raises(NotImplementedError):
            adapter.execute(req)

    def test_health_check_returns_false(self, browser_config: BrowserConfig) -> None:
        adapter = RealBrowserAdapter(browser_config)
        assert adapter.health_check() is False


# ===========================================================================
# TestBrowserLogger
# ===========================================================================

class TestBrowserLogger:

    def test_log_submitted_creates_entry(self, tmp_vault: Path) -> None:
        logger = BrowserLogger(tmp_vault)
        req    = make_open_url_request("https://example.com")
        logger.log_submitted(req)
        entries = logger.read_entries()
        assert len(entries) == 1
        assert entries[0]["event"]      == "submitted"
        assert entries[0]["request_id"] == req.request_id
        assert entries[0]["action"]     == BrowserActionType.OPEN_URL

    def test_log_result_writes_status(self, tmp_vault: Path) -> None:
        logger = BrowserLogger(tmp_vault)
        result = BrowserResult(
            request_id="BROWSER-001",
            action=BrowserActionType.OPEN_URL,
            status=BrowserActionStatus.SUCCESS,
            adapter="mock",
        )
        logger.log_result(result)
        entries = logger.read_entries()
        assert entries[0]["status"] == "SUCCESS"

    def test_log_queued_for_hitl(self, tmp_vault: Path) -> None:
        logger = BrowserLogger(tmp_vault)
        req    = make_open_url_request("https://x.com")
        logger.log_queued_for_hitl(req, "REQ-HITL-001")
        entries = logger.read_entries()
        assert entries[0]["event"]           == "queued_for_hitl"
        assert entries[0]["hitl_request_id"] == "REQ-HITL-001"

    def test_log_denied(self, tmp_vault: Path) -> None:
        logger = BrowserLogger(tmp_vault)
        logger.log_denied("BROWSER-001", "Policy block")
        entries = logger.read_entries()
        assert entries[0]["event"]  == "denied"
        assert "Policy" in entries[0]["reason"]

    def test_log_error(self, tmp_vault: Path) -> None:
        logger = BrowserLogger(tmp_vault)
        logger.log_error("BROWSER-001", "timeout occurred")
        entries = logger.read_entries()
        assert entries[0]["event"] == "error"
        assert "timeout" in entries[0]["error"]

    def test_read_entries_empty_for_missing_date(self, tmp_vault: Path) -> None:
        logger  = BrowserLogger(tmp_vault)
        entries = logger.read_entries("1999-01-01")
        assert entries == []

    def test_log_dir_created_automatically(self, tmp_vault: Path) -> None:
        logger = BrowserLogger(tmp_vault)
        logger.log_submitted(make_open_url_request("https://x.com"))
        assert (tmp_vault / "70-LOGS" / "browser").is_dir()

    def test_multiple_entries_appended(self, tmp_vault: Path) -> None:
        logger = BrowserLogger(tmp_vault)
        for i in range(4):
            logger.log_error(f"BROWSER-{i:03d}", f"err {i}")
        entries = logger.read_entries()
        assert len(entries) == 4


# ===========================================================================
# TestValidation
# ===========================================================================

class TestValidation:

    def test_empty_url_raises(self) -> None:
        req = BrowserRequest(action=BrowserActionType.OPEN_URL, url="")
        with pytest.raises(ValidationError, match="URL"):
            _validate(req)

    def test_blank_url_raises(self) -> None:
        req = BrowserRequest(action=BrowserActionType.OPEN_URL, url="   ")
        with pytest.raises(ValidationError, match="blank"):
            _validate(req)

    def test_unsupported_action_raises(self) -> None:
        req = BrowserRequest(action="click_button", url="https://x.com")
        with pytest.raises(ValidationError, match="Unsupported"):
            _validate(req)

    def test_valid_open_url_does_not_raise(self) -> None:
        req = make_open_url_request("https://example.com")
        _validate(req)  # no raise

    def test_valid_extract_text_does_not_raise(self) -> None:
        req = make_extract_text_request("https://example.com", selector="p")
        _validate(req)  # no raise


# ===========================================================================
# TestBrowserAction
# ===========================================================================

class TestBrowserAction:

    def test_open_url_tier1_direct_execute(self, low_tier_config: BrowserConfig) -> None:
        adapter = MockBrowserAdapter()
        action  = BrowserAction(config=low_tier_config, adapter=adapter)
        req     = make_open_url_request("https://example.com", tier=1)
        result  = action.execute(req)
        assert result.status          == BrowserActionStatus.SUCCESS
        assert adapter.execute_count  == 1

    def test_extract_text_tier1_direct_execute(self, low_tier_config: BrowserConfig) -> None:
        adapter = MockBrowserAdapter()
        action  = BrowserAction(config=low_tier_config, adapter=adapter)
        req     = make_extract_text_request("https://example.com", selector="h1", tier=1)
        result  = action.execute(req)
        assert result.status == BrowserActionStatus.SUCCESS

    def test_validation_failure_returns_failed(self, browser_config: BrowserConfig) -> None:
        adapter = MockBrowserAdapter()
        action  = BrowserAction(config=browser_config, adapter=adapter)
        req     = BrowserRequest(action=BrowserActionType.OPEN_URL, url="")
        result  = action.execute(req)
        assert result.status         == BrowserActionStatus.FAILED
        assert "URL" in result.error
        assert adapter.execute_count == 0

    def test_hitl_gate_queues_tier2(self, browser_config: BrowserConfig) -> None:
        mock_hitl = MagicMock()
        submitted = []
        mock_hitl.submit.side_effect = lambda r: submitted.append(r)

        adapter = MockBrowserAdapter()
        action  = BrowserAction(config=browser_config, adapter=adapter, hitl_skill=mock_hitl)
        req     = make_open_url_request("https://example.com", tier=2)
        result  = action.execute(req)

        assert result.status         == BrowserActionStatus.PENDING_APPROVAL
        assert result.hitl_request_id != ""
        assert adapter.execute_count == 0
        mock_hitl.submit.assert_called_once()

    def test_no_hitl_skill_tier2_executes_directly(self, browser_config: BrowserConfig) -> None:
        """Without a HITL skill, tier 2 falls through to direct execution."""
        adapter = MockBrowserAdapter()
        action  = BrowserAction(config=browser_config, adapter=adapter, hitl_skill=None)
        req     = make_open_url_request("https://example.com", tier=2)
        result  = action.execute(req)
        assert result.status         == BrowserActionStatus.SUCCESS
        assert adapter.execute_count == 1

    def test_hitl_failure_denies_action(self, browser_config: BrowserConfig) -> None:
        mock_hitl = MagicMock()
        mock_hitl.submit.side_effect = RuntimeError("HITL unavailable")

        adapter = MockBrowserAdapter()
        action  = BrowserAction(config=browser_config, adapter=adapter, hitl_skill=mock_hitl)
        req     = make_open_url_request("https://example.com", tier=2)
        result  = action.execute(req)

        assert result.status         == BrowserActionStatus.DENIED
        assert adapter.execute_count == 0

    def test_adapter_failure_captured(self, low_tier_config: BrowserConfig) -> None:
        adapter = MockBrowserAdapter(fail_execute=True)
        action  = BrowserAction(config=low_tier_config, adapter=adapter)
        req     = make_open_url_request("https://example.com", tier=1)
        result  = action.execute(req)
        assert result.status == BrowserActionStatus.FAILED

    def test_health_check_delegates_to_adapter(self, browser_config: BrowserConfig) -> None:
        adapter = MockBrowserAdapter()
        action  = BrowserAction(config=browser_config, adapter=adapter)
        assert action.health_check() is True
        adapter.set_healthy(False)
        assert action.health_check() is False

    def test_submit_logs_submitted_event(
        self, browser_config: BrowserConfig, tmp_vault: Path
    ) -> None:
        adapter = MockBrowserAdapter()
        logger  = BrowserLogger(tmp_vault)
        action  = BrowserAction(config=browser_config, adapter=adapter, logger=logger)
        req     = make_open_url_request("https://example.com", tier=1)
        action.execute(req)
        events = [e["event"] for e in logger.read_entries()]
        assert "submitted" in events

    def test_hitl_action_summary_includes_url(self, browser_config: BrowserConfig) -> None:
        mock_hitl  = MagicMock()
        summaries  = []
        def capture_submit(r):
            summaries.append(r.action_summary)
        mock_hitl.submit.side_effect = capture_submit

        action = BrowserAction(config=browser_config, adapter=MockBrowserAdapter(), hitl_skill=mock_hitl)
        action.execute(make_open_url_request("https://target.com", tier=2))
        assert "https://target.com" in summaries[0]

    def test_extract_text_selector_in_hitl_summary(self, browser_config: BrowserConfig) -> None:
        mock_hitl  = MagicMock()
        summaries  = []
        mock_hitl.submit.side_effect = lambda r: summaries.append(r.action_summary)

        action = BrowserAction(config=browser_config, adapter=MockBrowserAdapter(), hitl_skill=mock_hitl)
        action.execute(make_extract_text_request("https://x.com", selector="h2", tier=2))
        assert "h2" in summaries[0]


# ===========================================================================
# TestBrowserSkill (facade)
# ===========================================================================

class TestBrowserSkill:

    def test_open_url_low_tier_returns_success(self, low_tier_skill: BrowserSkill) -> None:
        result = low_tier_skill.open_url("https://example.com")
        assert result.status == BrowserActionStatus.SUCCESS

    def test_extract_text_low_tier_returns_success(self, low_tier_skill: BrowserSkill) -> None:
        result = low_tier_skill.extract_text("https://example.com", selector="p")
        assert result.status == BrowserActionStatus.SUCCESS

    def test_open_url_tier2_no_hitl_executes(self, skill: BrowserSkill) -> None:
        """Without HITL skill, tier 2 executes directly."""
        result = skill.open_url("https://example.com")
        assert result.status == BrowserActionStatus.SUCCESS

    def test_open_url_tier2_with_hitl_queues(self, browser_config: BrowserConfig) -> None:
        mock_hitl = MagicMock()
        mock_hitl.submit.return_value = MagicMock(request_id="REQ-001")
        skill  = BrowserSkill(browser_config, hitl_skill=mock_hitl)
        result = skill.open_url("https://example.com")
        assert result.status == BrowserActionStatus.PENDING_APPROVAL
        mock_hitl.submit.assert_called_once()

    def test_extract_text_with_hitl_queues(self, browser_config: BrowserConfig) -> None:
        mock_hitl = MagicMock()
        mock_hitl.submit.return_value = MagicMock(request_id="REQ-002")
        skill  = BrowserSkill(browser_config, hitl_skill=mock_hitl)
        result = skill.extract_text("https://example.com", selector="h1")
        assert result.status == BrowserActionStatus.PENDING_APPROVAL

    def test_execute_request_open_url(self, low_tier_skill: BrowserSkill) -> None:
        req    = make_open_url_request("https://example.com", tier=1)
        result = low_tier_skill.execute_request(req)
        assert result.status == BrowserActionStatus.SUCCESS

    def test_execute_request_extract_text(self, low_tier_skill: BrowserSkill) -> None:
        req    = make_extract_text_request("https://example.com", selector="div", tier=1)
        result = low_tier_skill.execute_request(req)
        assert result.status == BrowserActionStatus.SUCCESS

    def test_validation_failure_empty_url(self, skill: BrowserSkill) -> None:
        result = skill.open_url("")
        assert result.status == BrowserActionStatus.FAILED

    def test_set_hitl(self, skill: BrowserSkill) -> None:
        mock_hitl = MagicMock()
        skill.set_hitl(mock_hitl)
        assert skill.action._hitl is mock_hitl

    def test_health_check_true(self, skill: BrowserSkill) -> None:
        assert skill.health_check() is True

    def test_health_check_false_when_adapter_unhealthy(
        self, browser_config: BrowserConfig
    ) -> None:
        adapter = MockBrowserAdapter(healthy=False)
        skill   = BrowserSkill(browser_config, adapter=adapter)
        assert skill.health_check() is False

    def test_read_logs_returns_list(self, low_tier_skill: BrowserSkill) -> None:
        low_tier_skill.open_url("https://example.com")
        logs = low_tier_skill.read_logs()
        assert isinstance(logs, list)
        assert len(logs) > 0

    def test_config_property(
        self, skill: BrowserSkill, browser_config: BrowserConfig
    ) -> None:
        assert skill.config is browser_config

    def test_adapter_property(
        self, skill: BrowserSkill, mock_adapter: MockBrowserAdapter
    ) -> None:
        assert skill.adapter is mock_adapter

    def test_orchestrator_registers_open_url(self, browser_config: BrowserConfig) -> None:
        from silver_tier_core_autonomy.orchestrator.registry import SkillRegistry
        registry = SkillRegistry()
        BrowserSkill(browser_config, orchestrator_registry=registry)
        assert registry.has("browser", "open_url")

    def test_orchestrator_registers_extract_text(self, browser_config: BrowserConfig) -> None:
        from silver_tier_core_autonomy.orchestrator.registry import SkillRegistry
        registry = SkillRegistry()
        BrowserSkill(browser_config, orchestrator_registry=registry)
        assert registry.has("browser", "extract_text")

    def test_orchestrator_open_url_handler_executes(
        self, browser_config: BrowserConfig
    ) -> None:
        low_cfg = BrowserConfig(vault_root=browser_config.vault_root, default_tier=1)
        from silver_tier_core_autonomy.orchestrator.registry import SkillRegistry
        registry = SkillRegistry()
        BrowserSkill(low_cfg, orchestrator_registry=registry)
        handler = registry.get("browser", "open_url")
        result  = handler(url="https://example.com", tier=1)
        assert result["status"] == BrowserActionStatus.SUCCESS

    def test_orchestrator_extract_text_handler_executes(
        self, browser_config: BrowserConfig
    ) -> None:
        low_cfg = BrowserConfig(vault_root=browser_config.vault_root, default_tier=1)
        from silver_tier_core_autonomy.orchestrator.registry import SkillRegistry
        registry = SkillRegistry()
        BrowserSkill(low_cfg, orchestrator_registry=registry)
        handler = registry.get("browser", "extract_text")
        result  = handler(url="https://example.com", selector="p", tier=1)
        assert result["status"] == BrowserActionStatus.SUCCESS

    def test_security_integration_graceful(self, browser_config: BrowserConfig) -> None:
        bad_security = MagicMock(side_effect=Exception("sec failure"))
        skill = BrowserSkill(browser_config, security_skill=bad_security)
        assert skill is not None

    def test_security_integration_registers_credential(
        self, browser_config: BrowserConfig
    ) -> None:
        from bronze_tier_governance.security import SecuritySkill
        security = SecuritySkill(vault_root=browser_config.vault_root)
        BrowserSkill(browser_config, security_skill=security)
        creds = security.list_credentials()
        names = [c.name for c in creds]
        assert browser_config.credentials_name in names

    def test_inject_page_title_via_adapter(self, browser_config: BrowserConfig) -> None:
        adapter = MockBrowserAdapter()
        adapter.inject_page("https://test.com", "Test Page Title")
        skill  = BrowserSkill(browser_config, adapter=adapter)
        result = skill.open_url("https://test.com", tier=1)
        assert result.content == "Test Page Title"

    def test_inject_content_via_adapter(self, browser_config: BrowserConfig) -> None:
        adapter = MockBrowserAdapter()
        adapter.inject_content("https://test.com", "Extracted paragraph text")
        skill  = BrowserSkill(browser_config, adapter=adapter)
        result = skill.extract_text("https://test.com", tier=1)
        assert result.content == "Extracted paragraph text"


# ===========================================================================
# TestCLI
# ===========================================================================

class TestCLI:

    def test_build_parser_returns_parser(self) -> None:
        parser = build_parser()
        assert parser is not None

    def test_open_returns_0(self, tmp_vault: Path) -> None:
        result = cli_main([
            "--vault", str(tmp_vault),
            "open",
            "--url",  "https://example.com",
            "--tier", "1",
        ])
        assert result == 0

    def test_extract_returns_0(self, tmp_vault: Path) -> None:
        result = cli_main([
            "--vault",    str(tmp_vault),
            "extract",
            "--url",      "https://example.com",
            "--selector", "h1",
            "--tier",     "1",
        ])
        assert result == 0

    def test_extract_no_selector_returns_0(self, tmp_vault: Path) -> None:
        result = cli_main([
            "--vault", str(tmp_vault),
            "extract",
            "--url",   "https://example.com",
            "--tier",  "1",
        ])
        assert result == 0

    def test_status_returns_0(self, tmp_vault: Path) -> None:
        result = cli_main([
            "--vault", str(tmp_vault),
            "status",
        ])
        assert result == 0

    def test_logs_no_entries_returns_0(self, tmp_vault: Path) -> None:
        result = cli_main([
            "--vault", str(tmp_vault),
            "logs",
        ])
        assert result == 0

    def test_open_then_logs_shows_entry(self, tmp_vault: Path) -> None:
        cli_main([
            "--vault", str(tmp_vault),
            "open",
            "--url",  "https://example.com",
            "--tier", "1",
        ])
        result = cli_main([
            "--vault", str(tmp_vault),
            "logs",
        ])
        assert result == 0

    def test_logs_with_date_filter_returns_0(self, tmp_vault: Path) -> None:
        result = cli_main([
            "--vault", str(tmp_vault),
            "logs",
            "--date", "1999-01-01",
        ])
        assert result == 0
