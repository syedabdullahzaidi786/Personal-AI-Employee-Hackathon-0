"""
ODOO_MCP_INTEGRATION_SKILL — Phase 1 Unit Tests
Target: ~85 tests, stdlib only.

Coverage:
  - OdooOperation, OdooActionStatus, OdooEventType              (models.py)
  - OdooRequest, OdooResult, OdooConfig                         (models.py)
  - make_create_request, make_update_request, make_fetch_request (models.py)
  - OdooAdapter ABC, MockOdooAdapter, RealOdooAdapter            (adapter.py)
  - OdooLogger read/write                                        (logger.py)
  - OdooAction validation, direct execute, HITL gate             (action.py)
  - OdooSkill facade, orchestrator/security integration          (__init__.py)
  - CLI: create, update, fetch, status, logs                     (cli.py)
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
from golden_tier_external_world.actions.odoo.models import (
    OdooActionStatus,
    OdooConfig,
    OdooEventType,
    OdooOperation,
    OdooRequest,
    OdooResult,
    OPERATION_DEFAULT_TIER,
    make_create_request,
    make_fetch_request,
    make_update_request,
)
from golden_tier_external_world.actions.odoo.adapter import (
    MockOdooAdapter,
    OdooAdapter,
    RealOdooAdapter,
)
from golden_tier_external_world.actions.odoo.logger import OdooLogger
from golden_tier_external_world.actions.odoo.action import OdooAction, ValidationError, _validate
from golden_tier_external_world.actions.odoo import OdooSkill
from golden_tier_external_world.actions.odoo.cli import build_parser, main as cli_main


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def odoo_config(tmp_vault: Path) -> OdooConfig:
    return OdooConfig(
        vault_root=str(tmp_vault),
        odoo_url="https://test.odoo.com",
        database="test_db",
        default_tier=3,
    )


@pytest.fixture
def low_tier_config(tmp_vault: Path) -> OdooConfig:
    """Config with tier 1 — auto-executes without HITL."""
    return OdooConfig(vault_root=str(tmp_vault), default_tier=1)


@pytest.fixture
def mock_adapter() -> MockOdooAdapter:
    return MockOdooAdapter()


@pytest.fixture
def skill(odoo_config: OdooConfig, mock_adapter: MockOdooAdapter) -> OdooSkill:
    return OdooSkill(odoo_config, adapter=mock_adapter)


@pytest.fixture
def low_tier_skill(low_tier_config: OdooConfig) -> OdooSkill:
    return OdooSkill(low_tier_config, adapter=MockOdooAdapter())


# ===========================================================================
# TestOdooOperation
# ===========================================================================

class TestOdooOperation:

    def test_constants_defined(self) -> None:
        assert OdooOperation.CREATE_RECORD == "create_record"
        assert OdooOperation.UPDATE_RECORD == "update_record"
        assert OdooOperation.FETCH_RECORD  == "fetch_record"


# ===========================================================================
# TestOdooActionStatus
# ===========================================================================

class TestOdooActionStatus:

    def test_constants_defined(self) -> None:
        assert OdooActionStatus.PENDING_APPROVAL == "PENDING_APPROVAL"
        assert OdooActionStatus.APPROVED         == "APPROVED"
        assert OdooActionStatus.SUCCESS          == "SUCCESS"
        assert OdooActionStatus.DENIED           == "DENIED"
        assert OdooActionStatus.FAILED           == "FAILED"
        assert OdooActionStatus.NOT_FOUND        == "NOT_FOUND"


# ===========================================================================
# TestOdooEventType
# ===========================================================================

class TestOdooEventType:

    def test_constants_defined(self) -> None:
        assert OdooEventType.RECORD_CREATED     == "odoo_record_created"
        assert OdooEventType.RECORD_UPDATED     == "odoo_record_updated"
        assert OdooEventType.RECORD_FETCHED     == "odoo_record_fetched"
        assert OdooEventType.OPERATION_DENIED   == "odoo_operation_denied"
        assert OdooEventType.OPERATION_FAILED   == "odoo_operation_failed"
        assert OdooEventType.APPROVAL_REQUESTED == "odoo_approval_requested"


# ===========================================================================
# TestOperationDefaultTier
# ===========================================================================

class TestOperationDefaultTier:

    def test_write_ops_are_tier3(self) -> None:
        assert OPERATION_DEFAULT_TIER[OdooOperation.CREATE_RECORD] == 3
        assert OPERATION_DEFAULT_TIER[OdooOperation.UPDATE_RECORD] == 3

    def test_fetch_is_tier1(self) -> None:
        assert OPERATION_DEFAULT_TIER[OdooOperation.FETCH_RECORD] == 1


# ===========================================================================
# TestOdooRequest
# ===========================================================================

class TestOdooRequest:

    def test_auto_request_id(self) -> None:
        req = make_create_request("res.partner", {"name": "Test"})
        assert req.request_id.startswith("ODOO-")

    def test_auto_submitted_at_utc(self) -> None:
        req = make_create_request("res.partner", {"name": "Test"})
        assert req.submitted_at is not None
        assert req.submitted_at.tzinfo is not None

    def test_to_dict_keys(self) -> None:
        req = make_create_request("res.partner", {"name": "Test"})
        d   = req.to_dict()
        assert "request_id"  in d
        assert "operation"   in d
        assert "model"       in d
        assert "data"        in d
        assert "tier"        in d
        assert "record_id"   in d

    def test_from_dict_roundtrip(self) -> None:
        req  = make_update_request("sale.order", 42, {"state": "done"}, tier=2)
        req2 = OdooRequest.from_dict(req.to_dict())
        assert req2.request_id == req.request_id
        assert req2.operation  == req.operation
        assert req2.model      == req.model
        assert req2.record_id  == req.record_id
        assert req2.data       == req.data
        assert req2.tier       == req.tier

    def test_create_defaults(self) -> None:
        req = make_create_request("res.partner", {})
        assert req.record_id  is None
        assert req.tier       == 3

    def test_fetch_defaults_tier1(self) -> None:
        req = make_fetch_request("res.partner", 1)
        assert req.tier == 1

    def test_unique_request_ids(self) -> None:
        r1 = make_create_request("m", {"a": 1})
        r2 = make_create_request("m", {"a": 2})
        assert r1.request_id != r2.request_id


# ===========================================================================
# TestOdooResult
# ===========================================================================

class TestOdooResult:

    def test_to_dict_keys(self) -> None:
        res = OdooResult(
            request_id="ODOO-001",
            operation=OdooOperation.CREATE_RECORD,
            status=OdooActionStatus.SUCCESS,
            model="res.partner",
            record_id=1,
            record_data={"name": "Alice"},
            adapter="mock",
            executed_at=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
        )
        d = res.to_dict()
        assert d["request_id"]  == "ODOO-001"
        assert d["record_id"]   == 1
        assert d["record_data"] == {"name": "Alice"}
        assert "2026" in d["executed_at"]

    def test_to_dict_no_executed_at(self) -> None:
        res = OdooResult(request_id="X", operation="create_record", status="FAILED")
        assert res.to_dict()["executed_at"] is None


# ===========================================================================
# TestOdooConfig
# ===========================================================================

class TestOdooConfig:

    def test_to_dict_roundtrip(self) -> None:
        cfg  = OdooConfig(vault_root="/v", odoo_url="https://x.odoo.com", database="db", default_tier=2)
        cfg2 = OdooConfig.from_dict(cfg.to_dict())
        assert cfg2.odoo_url    == "https://x.odoo.com"
        assert cfg2.database    == "db"
        assert cfg2.default_tier == 2

    def test_defaults(self) -> None:
        cfg = OdooConfig()
        assert cfg.vault_root       == ""
        assert cfg.credentials_name == "odoo_credential"
        assert cfg.default_tier     == 3


# ===========================================================================
# TestFactories
# ===========================================================================

class TestFactories:

    def test_make_create_request(self) -> None:
        req = make_create_request("res.partner", {"name": "Bob"})
        assert req.operation == OdooOperation.CREATE_RECORD
        assert req.model     == "res.partner"
        assert req.data      == {"name": "Bob"}
        assert req.tier      == 3

    def test_make_update_request(self) -> None:
        req = make_update_request("res.partner", 5, {"phone": "123"})
        assert req.operation == OdooOperation.UPDATE_RECORD
        assert req.record_id == 5
        assert req.data      == {"phone": "123"}
        assert req.tier      == 3

    def test_make_fetch_request(self) -> None:
        req = make_fetch_request("res.partner", 10)
        assert req.operation == OdooOperation.FETCH_RECORD
        assert req.record_id == 10
        assert req.tier      == 1

    def test_custom_tier(self) -> None:
        req = make_create_request("sale.order", {"name": "SO001"}, tier=1)
        assert req.tier == 1


# ===========================================================================
# TestMockOdooAdapter
# ===========================================================================

class TestMockOdooAdapter:

    def test_create_returns_success(self, mock_adapter: MockOdooAdapter) -> None:
        req    = make_create_request("res.partner", {"name": "Alice"}, tier=1)
        result = mock_adapter.execute(req)
        assert result.status    == OdooActionStatus.SUCCESS
        assert result.record_id == 1
        assert result.record_data["name"] == "Alice"

    def test_create_auto_increments_id(self, mock_adapter: MockOdooAdapter) -> None:
        r1 = mock_adapter.execute(make_create_request("m", {"a": 1}, tier=1))
        r2 = mock_adapter.execute(make_create_request("m", {"a": 2}, tier=1))
        assert r1.record_id == 1
        assert r2.record_id == 2

    def test_create_ids_independent_per_model(self, mock_adapter: MockOdooAdapter) -> None:
        r1 = mock_adapter.execute(make_create_request("res.partner", {"a": 1}, tier=1))
        r2 = mock_adapter.execute(make_create_request("sale.order", {"b": 2}, tier=1))
        assert r1.record_id == 1
        assert r2.record_id == 1  # each model starts at 1

    def test_create_stores_record(self, mock_adapter: MockOdooAdapter) -> None:
        mock_adapter.execute(make_create_request("res.partner", {"name": "Bob"}, tier=1))
        stored = mock_adapter.get_stored("res.partner", 1)
        assert stored is not None
        assert stored["name"] == "Bob"

    def test_fetch_returns_stored_record(self, mock_adapter: MockOdooAdapter) -> None:
        mock_adapter.execute(make_create_request("res.partner", {"name": "Alice"}, tier=1))
        result = mock_adapter.execute(make_fetch_request("res.partner", 1))
        assert result.status == OdooActionStatus.SUCCESS
        assert result.record_data["name"] == "Alice"

    def test_fetch_not_found(self, mock_adapter: MockOdooAdapter) -> None:
        result = mock_adapter.execute(make_fetch_request("res.partner", 999))
        assert result.status == OdooActionStatus.NOT_FOUND
        assert result.error  != ""

    def test_update_modifies_record(self, mock_adapter: MockOdooAdapter) -> None:
        mock_adapter.execute(make_create_request("res.partner", {"name": "Alice", "phone": "111"}, tier=1))
        result = mock_adapter.execute(make_update_request("res.partner", 1, {"phone": "999"}, tier=1))
        assert result.status == OdooActionStatus.SUCCESS
        assert result.record_data["phone"]  == "999"
        assert result.record_data["name"]   == "Alice"  # untouched field preserved

    def test_update_not_found(self, mock_adapter: MockOdooAdapter) -> None:
        result = mock_adapter.execute(make_update_request("res.partner", 999, {"x": 1}, tier=1))
        assert result.status == OdooActionStatus.NOT_FOUND

    def test_update_without_record_id_returns_failed(
        self, mock_adapter: MockOdooAdapter
    ) -> None:
        req = OdooRequest(
            operation=OdooOperation.UPDATE_RECORD,
            model="res.partner",
            record_id=None,
            data={"name": "X"},
            tier=1,
        )
        result = mock_adapter.execute(req)
        assert result.status == OdooActionStatus.FAILED

    def test_fetch_without_record_id_returns_failed(
        self, mock_adapter: MockOdooAdapter
    ) -> None:
        req = OdooRequest(
            operation=OdooOperation.FETCH_RECORD,
            model="res.partner",
            record_id=None,
            tier=1,
        )
        result = mock_adapter.execute(req)
        assert result.status == OdooActionStatus.FAILED

    def test_unknown_operation_returns_failed(self, mock_adapter: MockOdooAdapter) -> None:
        req = OdooRequest(operation="delete_record", model="res.partner", tier=1)
        result = mock_adapter.execute(req)
        assert result.status == OdooActionStatus.FAILED

    def test_fail_execute_returns_failed(self) -> None:
        adapter = MockOdooAdapter(fail_execute=True)
        result  = adapter.execute(make_create_request("m", {"a": 1}, tier=1))
        assert result.status == OdooActionStatus.FAILED

    def test_execute_count_increments(self, mock_adapter: MockOdooAdapter) -> None:
        mock_adapter.execute(make_create_request("m", {"a": 1}, tier=1))
        mock_adapter.execute(make_fetch_request("m", 1))
        assert mock_adapter.execute_count == 2

    def test_results_captured(self, mock_adapter: MockOdooAdapter) -> None:
        mock_adapter.execute(make_create_request("m", {"x": 1}, tier=1))
        assert len(mock_adapter.results) == 1

    def test_results_defensive_copy(self, mock_adapter: MockOdooAdapter) -> None:
        mock_adapter.execute(make_create_request("m", {"x": 1}, tier=1))
        copy = mock_adapter.results
        copy.clear()
        assert len(mock_adapter.results) == 1

    def test_seed_record(self, mock_adapter: MockOdooAdapter) -> None:
        mock_adapter.seed_record("res.partner", 42, {"name": "Seeded"})
        result = mock_adapter.execute(make_fetch_request("res.partner", 42))
        assert result.status == OdooActionStatus.SUCCESS
        assert result.record_data["name"] == "Seeded"

    def test_health_check_default_true(self, mock_adapter: MockOdooAdapter) -> None:
        assert mock_adapter.health_check() is True

    def test_set_healthy_false(self, mock_adapter: MockOdooAdapter) -> None:
        mock_adapter.set_healthy(False)
        assert mock_adapter.health_check() is False

    def test_clear_resets_store(self, mock_adapter: MockOdooAdapter) -> None:
        mock_adapter.execute(make_create_request("m", {"a": 1}, tier=1))
        mock_adapter.clear()
        assert mock_adapter.execute_count == 0
        assert mock_adapter.results       == []
        assert mock_adapter.record_count("m") == 0

    def test_record_count(self, mock_adapter: MockOdooAdapter) -> None:
        assert mock_adapter.record_count("res.partner") == 0
        mock_adapter.execute(make_create_request("res.partner", {"a": 1}, tier=1))
        mock_adapter.execute(make_create_request("res.partner", {"b": 2}, tier=1))
        assert mock_adapter.record_count("res.partner") == 2


# ===========================================================================
# TestRealOdooAdapter
# ===========================================================================

class TestRealOdooAdapter:

    def test_execute_raises(self, odoo_config: OdooConfig) -> None:
        adapter = RealOdooAdapter(odoo_config)
        with pytest.raises(NotImplementedError):
            adapter.execute(make_create_request("m", {"a": 1}, tier=1))

    def test_health_check_returns_false(self, odoo_config: OdooConfig) -> None:
        adapter = RealOdooAdapter(odoo_config)
        assert adapter.health_check() is False


# ===========================================================================
# TestOdooLogger
# ===========================================================================

class TestOdooLogger:

    def test_log_submitted_creates_entry(self, tmp_vault: Path) -> None:
        logger = OdooLogger(tmp_vault)
        req    = make_create_request("res.partner", {"name": "A"})
        logger.log_submitted(req)
        entries = logger.read_entries()
        assert len(entries)               == 1
        assert entries[0]["event"]        == "submitted"
        assert entries[0]["operation"]    == OdooOperation.CREATE_RECORD
        assert entries[0]["model"]        == "res.partner"

    def test_log_result_writes_status(self, tmp_vault: Path) -> None:
        logger = OdooLogger(tmp_vault)
        result = OdooResult(
            request_id="ODOO-001",
            operation=OdooOperation.CREATE_RECORD,
            status=OdooActionStatus.SUCCESS,
            adapter="mock",
        )
        logger.log_result(result)
        entries = logger.read_entries()
        assert entries[0]["status"] == "SUCCESS"

    def test_log_queued_for_hitl(self, tmp_vault: Path) -> None:
        logger = OdooLogger(tmp_vault)
        req    = make_create_request("m", {"a": 1})
        logger.log_queued_for_hitl(req, "REQ-HITL-007")
        entries = logger.read_entries()
        assert entries[0]["event"]           == "queued_for_hitl"
        assert entries[0]["hitl_request_id"] == "REQ-HITL-007"

    def test_log_denied(self, tmp_vault: Path) -> None:
        logger = OdooLogger(tmp_vault)
        logger.log_denied("ODOO-001", reason="Policy")
        entries = logger.read_entries()
        assert entries[0]["event"]  == "denied"
        assert "Policy" in entries[0]["reason"]

    def test_log_error(self, tmp_vault: Path) -> None:
        logger = OdooLogger(tmp_vault)
        logger.log_error("ODOO-001", "connection refused")
        entries = logger.read_entries()
        assert entries[0]["event"] == "error"
        assert "refused" in entries[0]["error"]

    def test_read_entries_empty_for_missing_date(self, tmp_vault: Path) -> None:
        logger  = OdooLogger(tmp_vault)
        entries = logger.read_entries("1999-01-01")
        assert entries == []

    def test_log_dir_created_automatically(self, tmp_vault: Path) -> None:
        logger = OdooLogger(tmp_vault)
        logger.log_submitted(make_create_request("m", {"a": 1}))
        assert (tmp_vault / "70-LOGS" / "odoo").is_dir()

    def test_multiple_entries_appended(self, tmp_vault: Path) -> None:
        logger = OdooLogger(tmp_vault)
        for i in range(5):
            logger.log_error(f"ODOO-{i:03d}", f"err {i}")
        assert len(logger.read_entries()) == 5


# ===========================================================================
# TestValidation
# ===========================================================================

class TestValidation:

    def test_empty_model_raises(self) -> None:
        req = OdooRequest(operation=OdooOperation.CREATE_RECORD, model="", data={"a": 1})
        with pytest.raises(ValidationError, match="model"):
            _validate(req)

    def test_blank_model_raises(self) -> None:
        req = OdooRequest(operation=OdooOperation.CREATE_RECORD, model="  ", data={"a": 1})
        with pytest.raises(ValidationError, match="blank"):
            _validate(req)

    def test_unsupported_operation_raises(self) -> None:
        req = OdooRequest(operation="delete_record", model="res.partner", data={})
        with pytest.raises(ValidationError, match="Unsupported"):
            _validate(req)

    def test_update_without_record_id_raises(self) -> None:
        req = OdooRequest(
            operation=OdooOperation.UPDATE_RECORD,
            model="res.partner",
            record_id=None,
            data={"name": "X"},
        )
        with pytest.raises(ValidationError, match="record_id"):
            _validate(req)

    def test_fetch_without_record_id_raises(self) -> None:
        req = OdooRequest(
            operation=OdooOperation.FETCH_RECORD,
            model="res.partner",
            record_id=None,
        )
        with pytest.raises(ValidationError, match="record_id"):
            _validate(req)

    def test_create_without_data_raises(self) -> None:
        req = OdooRequest(
            operation=OdooOperation.CREATE_RECORD,
            model="res.partner",
            data={},
        )
        with pytest.raises(ValidationError, match="data"):
            _validate(req)

    def test_valid_create_does_not_raise(self) -> None:
        req = make_create_request("res.partner", {"name": "Alice"})
        _validate(req)

    def test_valid_update_does_not_raise(self) -> None:
        req = make_update_request("res.partner", 1, {"phone": "123"})
        _validate(req)

    def test_valid_fetch_does_not_raise(self) -> None:
        req = make_fetch_request("res.partner", 1)
        _validate(req)


# ===========================================================================
# TestOdooAction
# ===========================================================================

class TestOdooAction:

    def test_create_tier1_direct_execute(self, low_tier_config: OdooConfig) -> None:
        adapter = MockOdooAdapter()
        action  = OdooAction(config=low_tier_config, adapter=adapter)
        req     = make_create_request("res.partner", {"name": "Alice"}, tier=1)
        result  = action.execute(req)
        assert result.status          == OdooActionStatus.SUCCESS
        assert result.record_id       == 1
        assert adapter.execute_count  == 1

    def test_fetch_tier1_direct_execute(self, low_tier_config: OdooConfig) -> None:
        adapter = MockOdooAdapter()
        adapter.seed_record("res.partner", 5, {"name": "Bob"})
        action = OdooAction(config=low_tier_config, adapter=adapter)
        result = action.execute(make_fetch_request("res.partner", 5))
        assert result.status == OdooActionStatus.SUCCESS
        assert result.record_data["name"] == "Bob"

    def test_update_tier1_direct_execute(self, low_tier_config: OdooConfig) -> None:
        adapter = MockOdooAdapter()
        adapter.seed_record("res.partner", 1, {"name": "Alice", "phone": "111"})
        action  = OdooAction(config=low_tier_config, adapter=adapter)
        result  = action.execute(make_update_request("res.partner", 1, {"phone": "999"}, tier=1))
        assert result.status == OdooActionStatus.SUCCESS
        assert result.record_data["phone"] == "999"

    def test_validation_failure_returns_failed(self, odoo_config: OdooConfig) -> None:
        adapter = MockOdooAdapter()
        action  = OdooAction(config=odoo_config, adapter=adapter)
        req     = OdooRequest(operation=OdooOperation.CREATE_RECORD, model="", data={})
        result  = action.execute(req)
        assert result.status         == OdooActionStatus.FAILED
        assert adapter.execute_count == 0

    def test_hitl_gate_queues_tier3(self, odoo_config: OdooConfig) -> None:
        mock_hitl  = MagicMock()
        submitted  = []
        mock_hitl.submit.side_effect = lambda r: submitted.append(r)

        adapter = MockOdooAdapter()
        action  = OdooAction(config=odoo_config, adapter=adapter, hitl_skill=mock_hitl)
        req     = make_create_request("res.partner", {"name": "Alice"}, tier=3)
        result  = action.execute(req)

        assert result.status          == OdooActionStatus.PENDING_APPROVAL
        assert result.hitl_request_id != ""
        assert adapter.execute_count  == 0
        mock_hitl.submit.assert_called_once()

    def test_no_hitl_skill_tier3_executes_directly(self, odoo_config: OdooConfig) -> None:
        adapter = MockOdooAdapter()
        action  = OdooAction(config=odoo_config, adapter=adapter, hitl_skill=None)
        req     = make_create_request("res.partner", {"name": "Alice"}, tier=3)
        result  = action.execute(req)
        assert result.status         == OdooActionStatus.SUCCESS
        assert adapter.execute_count == 1

    def test_hitl_failure_denies_operation(self, odoo_config: OdooConfig) -> None:
        mock_hitl = MagicMock()
        mock_hitl.submit.side_effect = RuntimeError("HITL down")

        adapter = MockOdooAdapter()
        action  = OdooAction(config=odoo_config, adapter=adapter, hitl_skill=mock_hitl)
        req     = make_create_request("res.partner", {"name": "Alice"}, tier=3)
        result  = action.execute(req)

        assert result.status         == OdooActionStatus.DENIED
        assert adapter.execute_count == 0

    def test_adapter_failure_captured(self, low_tier_config: OdooConfig) -> None:
        adapter = MockOdooAdapter(fail_execute=True)
        action  = OdooAction(config=low_tier_config, adapter=adapter)
        req     = make_create_request("m", {"a": 1}, tier=1)
        result  = action.execute(req)
        assert result.status == OdooActionStatus.FAILED

    def test_health_check_delegates_to_adapter(self, odoo_config: OdooConfig) -> None:
        adapter = MockOdooAdapter()
        action  = OdooAction(config=odoo_config, adapter=adapter)
        assert action.health_check() is True
        adapter.set_healthy(False)
        assert action.health_check() is False

    def test_execute_logs_submitted_event(
        self, odoo_config: OdooConfig, tmp_vault: Path
    ) -> None:
        adapter = MockOdooAdapter()
        logger  = OdooLogger(tmp_vault)
        action  = OdooAction(config=odoo_config, adapter=adapter, logger=logger)
        req     = make_create_request("m", {"a": 1}, tier=1)
        action.execute(req)
        events  = [e["event"] for e in logger.read_entries()]
        assert "submitted" in events

    def test_hitl_summary_includes_model(self, odoo_config: OdooConfig) -> None:
        mock_hitl  = MagicMock()
        summaries  = []
        mock_hitl.submit.side_effect = lambda r: summaries.append(r.action_summary)
        action = OdooAction(config=odoo_config, adapter=MockOdooAdapter(), hitl_skill=mock_hitl)
        action.execute(make_create_request("sale.order", {"name": "SO001"}, tier=3))
        assert "sale.order" in summaries[0]

    def test_hitl_summary_includes_record_id_for_update(
        self, odoo_config: OdooConfig
    ) -> None:
        mock_hitl  = MagicMock()
        summaries  = []
        mock_hitl.submit.side_effect = lambda r: summaries.append(r.action_summary)
        action = OdooAction(config=odoo_config, adapter=MockOdooAdapter(), hitl_skill=mock_hitl)
        action.execute(make_update_request("res.partner", 77, {"phone": "999"}, tier=3))
        assert "77" in summaries[0]


# ===========================================================================
# TestOdooSkill (facade)
# ===========================================================================

class TestOdooSkill:

    def test_create_low_tier_returns_success(self, low_tier_skill: OdooSkill) -> None:
        result = low_tier_skill.create_record("res.partner", {"name": "Alice"})
        assert result.status    == OdooActionStatus.SUCCESS
        assert result.record_id == 1

    def test_fetch_returns_created_record(self, low_tier_skill: OdooSkill) -> None:
        low_tier_skill.create_record("res.partner", {"name": "Bob"})
        result = low_tier_skill.fetch_record("res.partner", 1)
        assert result.status == OdooActionStatus.SUCCESS
        assert result.record_data["name"] == "Bob"

    def test_update_modifies_record(self, low_tier_skill: OdooSkill) -> None:
        low_tier_skill.create_record("res.partner", {"name": "Carol", "phone": "000"})
        result = low_tier_skill.update_record("res.partner", 1, {"phone": "999"}, tier=1)
        assert result.status == OdooActionStatus.SUCCESS
        assert result.record_data["phone"] == "999"

    def test_fetch_not_found(self, low_tier_skill: OdooSkill) -> None:
        result = low_tier_skill.fetch_record("res.partner", 999)
        assert result.status == OdooActionStatus.NOT_FOUND

    def test_create_high_tier_no_hitl_executes(self, skill: OdooSkill) -> None:
        """Without HITL skill, tier 3 creates execute directly."""
        result = skill.create_record("res.partner", {"name": "Alice"})
        assert result.status == OdooActionStatus.SUCCESS

    def test_create_high_tier_with_hitl_queues(self, odoo_config: OdooConfig) -> None:
        mock_hitl = MagicMock()
        mock_hitl.submit.return_value = MagicMock(request_id="REQ-001")
        skill  = OdooSkill(odoo_config, hitl_skill=mock_hitl)
        result = skill.create_record("res.partner", {"name": "Alice"})
        assert result.status == OdooActionStatus.PENDING_APPROVAL
        mock_hitl.submit.assert_called_once()

    def test_update_high_tier_with_hitl_queues(self, odoo_config: OdooConfig) -> None:
        mock_hitl = MagicMock()
        mock_hitl.submit.return_value = MagicMock(request_id="REQ-002")
        skill  = OdooSkill(odoo_config, hitl_skill=mock_hitl)
        result = skill.update_record("res.partner", 1, {"phone": "999"})
        assert result.status == OdooActionStatus.PENDING_APPROVAL

    def test_fetch_auto_tier1(self, odoo_config: OdooConfig) -> None:
        """fetch_record defaults to tier 1 regardless of config default_tier."""
        adapter = MockOdooAdapter()
        adapter.seed_record("res.partner", 1, {"name": "X"})
        mock_hitl = MagicMock()
        skill     = OdooSkill(odoo_config, adapter=adapter, hitl_skill=mock_hitl)
        result    = skill.fetch_record("res.partner", 1)
        assert result.status == OdooActionStatus.SUCCESS
        mock_hitl.submit.assert_not_called()  # tier 1 bypasses HITL

    def test_execute_request(self, low_tier_skill: OdooSkill) -> None:
        req    = make_create_request("sale.order", {"name": "SO001"}, tier=1)
        result = low_tier_skill.execute_request(req)
        assert result.status == OdooActionStatus.SUCCESS

    def test_validation_failure(self, skill: OdooSkill) -> None:
        result = skill.create_record("", {"name": "X"})
        assert result.status == OdooActionStatus.FAILED

    def test_set_hitl(self, skill: OdooSkill) -> None:
        mock_hitl = MagicMock()
        skill.set_hitl(mock_hitl)
        assert skill.action._hitl is mock_hitl

    def test_health_check_true(self, skill: OdooSkill) -> None:
        assert skill.health_check() is True

    def test_health_check_false_unhealthy_adapter(self, odoo_config: OdooConfig) -> None:
        adapter = MockOdooAdapter(healthy=False)
        skill   = OdooSkill(odoo_config, adapter=adapter)
        assert skill.health_check() is False

    def test_read_logs_returns_list(self, low_tier_skill: OdooSkill) -> None:
        low_tier_skill.create_record("m", {"a": 1})
        logs = low_tier_skill.read_logs()
        assert isinstance(logs, list)
        assert len(logs) > 0

    def test_orchestrator_registers_three_operations(
        self, odoo_config: OdooConfig
    ) -> None:
        from silver_tier_core_autonomy.orchestrator.registry import SkillRegistry
        registry = SkillRegistry()
        OdooSkill(odoo_config, orchestrator_registry=registry)
        assert registry.has("odoo", "create_record")
        assert registry.has("odoo", "update_record")
        assert registry.has("odoo", "fetch_record")

    def test_orchestrator_create_handler(self, odoo_config: OdooConfig) -> None:
        low_cfg = OdooConfig(vault_root=odoo_config.vault_root, default_tier=1)
        from silver_tier_core_autonomy.orchestrator.registry import SkillRegistry
        registry = SkillRegistry()
        OdooSkill(low_cfg, orchestrator_registry=registry)
        handler = registry.get("odoo", "create_record")
        result  = handler(model="res.partner", data={"name": "Alice"}, tier=1)
        assert result["status"] == OdooActionStatus.SUCCESS

    def test_orchestrator_fetch_handler(self, odoo_config: OdooConfig) -> None:
        low_cfg = OdooConfig(vault_root=odoo_config.vault_root, default_tier=1)
        adapter = MockOdooAdapter()
        adapter.seed_record("res.partner", 1, {"name": "Bob"})
        from silver_tier_core_autonomy.orchestrator.registry import SkillRegistry
        registry = SkillRegistry()
        skill    = OdooSkill(low_cfg, adapter=adapter, orchestrator_registry=registry)
        handler  = registry.get("odoo", "fetch_record")
        result   = handler(model="res.partner", record_id=1, tier=1)
        assert result["status"] == OdooActionStatus.SUCCESS

    def test_orchestrator_update_handler(self, odoo_config: OdooConfig) -> None:
        low_cfg = OdooConfig(vault_root=odoo_config.vault_root, default_tier=1)
        adapter = MockOdooAdapter()
        adapter.seed_record("res.partner", 1, {"name": "Alice", "phone": "000"})
        from silver_tier_core_autonomy.orchestrator.registry import SkillRegistry
        registry = SkillRegistry()
        OdooSkill(low_cfg, adapter=adapter, orchestrator_registry=registry)
        handler = registry.get("odoo", "update_record")
        result  = handler(model="res.partner", record_id=1, data={"phone": "999"}, tier=1)
        assert result["status"] == OdooActionStatus.SUCCESS

    def test_security_integration_graceful(self, odoo_config: OdooConfig) -> None:
        bad_sec = MagicMock(side_effect=Exception("sec error"))
        skill   = OdooSkill(odoo_config, security_skill=bad_sec)
        assert skill is not None

    def test_security_integration_registers_credential(
        self, odoo_config: OdooConfig
    ) -> None:
        from bronze_tier_governance.security import SecuritySkill
        security = SecuritySkill(vault_root=odoo_config.vault_root)
        OdooSkill(odoo_config, security_skill=security)
        names = [c.name for c in security.list_credentials()]
        assert odoo_config.credentials_name in names

    def test_config_property(self, skill: OdooSkill, odoo_config: OdooConfig) -> None:
        assert skill.config is odoo_config

    def test_adapter_property(
        self, skill: OdooSkill, mock_adapter: MockOdooAdapter
    ) -> None:
        assert skill.adapter is mock_adapter


# ===========================================================================
# TestCLI
# ===========================================================================

class TestCLI:

    def test_build_parser_returns_parser(self) -> None:
        assert build_parser() is not None

    def test_create_returns_0(self, tmp_vault: Path) -> None:
        result = cli_main([
            "--vault", str(tmp_vault),
            "create",
            "--model", "res.partner",
            "--data",  '{"name":"Alice"}',
            "--tier",  "1",
        ])
        assert result == 0

    def test_create_empty_data_returns_0(self, tmp_vault: Path) -> None:
        # Empty data passes CLI (validation happens inside skill)
        result = cli_main([
            "--vault", str(tmp_vault),
            "create",
            "--model", "res.partner",
            "--tier",  "1",
        ])
        assert result == 0

    def test_update_returns_0(self, tmp_vault: Path) -> None:
        # update on non-existent record returns NOT_FOUND but CLI exits 0
        result = cli_main([
            "--vault", str(tmp_vault),
            "update",
            "--model", "res.partner",
            "--id",    "1",
            "--data",  '{"phone":"999"}',
            "--tier",  "1",
        ])
        assert result == 0

    def test_fetch_returns_0(self, tmp_vault: Path) -> None:
        # fetch on non-existent record returns NOT_FOUND but CLI exits 0
        result = cli_main([
            "--vault", str(tmp_vault),
            "fetch",
            "--model", "res.partner",
            "--id",    "1",
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

    def test_create_then_logs_shows_entry(self, tmp_vault: Path) -> None:
        cli_main([
            "--vault", str(tmp_vault),
            "create",
            "--model", "res.partner",
            "--data",  '{"name":"Test"}',
            "--tier",  "1",
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
