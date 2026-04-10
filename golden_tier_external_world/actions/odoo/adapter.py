"""
ODOO_MCP_INTEGRATION_SKILL — Odoo Adapter
Phase 1: OdooAdapter ABC, MockOdooAdapter (in-memory store),
         RealOdooAdapter (Phase 2 stub).

Constitution compliance:
  - Principle I: Local-First — MockOdooAdapter requires no network
  - Section 8: Credential Storage — RealOdooAdapter never logs credentials
  - Principle VI: Fail Safe — execute() and health_check() never raise
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from .models import (
    OdooActionStatus,
    OdooOperation,
    OdooRequest,
    OdooResult,
)


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class OdooAdapter(ABC):
    """
    Abstract contract for Odoo API access.

    Phase 1 uses MockOdooAdapter.
    Phase 2 will provide RealOdooAdapter backed by Odoo XML-RPC / JSON-RPC.
    """

    @abstractmethod
    def execute(self, request: OdooRequest) -> OdooResult:
        """
        Execute an Odoo operation. Returns OdooResult. Never raises.
        On failure, return OdooResult with status=FAILED and error message.
        """

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the adapter can reach Odoo. Never raises."""


# ---------------------------------------------------------------------------
# MockOdooAdapter — in-memory record store, no network
# ---------------------------------------------------------------------------

class MockOdooAdapter(OdooAdapter):
    """
    In-memory Odoo adapter for unit tests and local development.
    No Odoo server or network is used.

    Behaviour:
      - create_record → auto-increments record_id per model; stores record
      - update_record → merges data into stored record; returns updated record
      - fetch_record  → returns stored record or NOT_FOUND

    Usage::

        adapter = MockOdooAdapter()
        req = make_create_request("res.partner", {"name": "Alice", "email": "alice@example.com"})
        result = adapter.execute(req)
        assert result.status    == OdooActionStatus.SUCCESS
        assert result.record_id == 1
    """

    def __init__(self, healthy: bool = True, fail_execute: bool = False) -> None:
        # {model: {record_id: data}}
        self._store:         dict[str, dict[int, dict[str, Any]]] = {}
        # {model: next_id}
        self._id_counters:   dict[str, int]                       = {}
        self._results:       list[OdooResult]                     = []
        self._healthy:       bool                                 = healthy
        self._fail_execute:  bool                                 = fail_execute
        self._execute_count: int                                  = 0

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def set_healthy(self, healthy: bool) -> None:
        self._healthy = healthy

    def set_fail_execute(self, fail: bool) -> None:
        """Simulate execution failures when True."""
        self._fail_execute = fail

    def seed_record(self, model: str, record_id: int, data: dict[str, Any]) -> None:
        """Pre-populate a record in the mock store (for fetch/update tests)."""
        if model not in self._store:
            self._store[model] = {}
        self._store[model][record_id] = dict(data)
        # Advance counter so next create doesn't collide
        current = self._id_counters.get(model, 0)
        if record_id >= current:
            self._id_counters[model] = record_id + 1

    def get_stored(self, model: str, record_id: int) -> dict[str, Any] | None:
        """Return raw stored data for a record (test introspection)."""
        return self._store.get(model, {}).get(record_id)

    def clear(self) -> None:
        self._store.clear()
        self._id_counters.clear()
        self._results.clear()
        self._execute_count = 0

    @property
    def results(self) -> list[OdooResult]:
        """All results produced by this adapter (defensive copy)."""
        return list(self._results)

    @property
    def execute_count(self) -> int:
        return self._execute_count

    def record_count(self, model: str) -> int:
        """Return number of records stored for a model."""
        return len(self._store.get(model, {}))

    # ------------------------------------------------------------------
    # OdooAdapter interface
    # ------------------------------------------------------------------

    def execute(self, request: OdooRequest) -> OdooResult:
        self._execute_count += 1

        if self._fail_execute:
            result = OdooResult(
                request_id=request.request_id,
                operation=request.operation,
                status=OdooActionStatus.FAILED,
                model=request.model,
                record_id=request.record_id,
                error="MockOdooAdapter: simulated execution failure",
                adapter="mock",
            )
            self._results.append(result)
            return result

        if request.operation == OdooOperation.CREATE_RECORD:
            result = self._create(request)
        elif request.operation == OdooOperation.UPDATE_RECORD:
            result = self._update(request)
        elif request.operation == OdooOperation.FETCH_RECORD:
            result = self._fetch(request)
        else:
            result = OdooResult(
                request_id=request.request_id,
                operation=request.operation,
                status=OdooActionStatus.FAILED,
                model=request.model,
                error=f"Unknown operation: {request.operation!r}",
                adapter="mock",
            )

        self._results.append(result)
        return result

    def health_check(self) -> bool:
        return self._healthy

    # ------------------------------------------------------------------
    # Internal operation handlers
    # ------------------------------------------------------------------

    def _next_id(self, model: str) -> int:
        nid = self._id_counters.get(model, 1)
        self._id_counters[model] = nid + 1
        return nid

    def _create(self, request: OdooRequest) -> OdooResult:
        """Create a new record in the mock store."""
        model     = request.model
        record_id = self._next_id(model)
        record    = dict(request.data)
        record["id"] = record_id

        if model not in self._store:
            self._store[model] = {}
        self._store[model][record_id] = record

        return OdooResult(
            request_id=request.request_id,
            operation=request.operation,
            status=OdooActionStatus.SUCCESS,
            model=model,
            record_id=record_id,
            record_data=dict(record),
            adapter="mock",
            executed_at=datetime.now(tz=timezone.utc),
        )

    def _update(self, request: OdooRequest) -> OdooResult:
        """Update an existing record in the mock store."""
        model     = request.model
        record_id = request.record_id

        if record_id is None:
            return OdooResult(
                request_id=request.request_id,
                operation=request.operation,
                status=OdooActionStatus.FAILED,
                model=model,
                error="update_record requires a record_id.",
                adapter="mock",
            )

        existing = self._store.get(model, {}).get(record_id)
        if existing is None:
            return OdooResult(
                request_id=request.request_id,
                operation=request.operation,
                status=OdooActionStatus.NOT_FOUND,
                model=model,
                record_id=record_id,
                error=f"Record {model}:{record_id} not found.",
                adapter="mock",
            )

        existing.update(request.data)

        return OdooResult(
            request_id=request.request_id,
            operation=request.operation,
            status=OdooActionStatus.SUCCESS,
            model=model,
            record_id=record_id,
            record_data=dict(existing),
            adapter="mock",
            executed_at=datetime.now(tz=timezone.utc),
        )

    def _fetch(self, request: OdooRequest) -> OdooResult:
        """Fetch a record from the mock store."""
        model     = request.model
        record_id = request.record_id

        if record_id is None:
            return OdooResult(
                request_id=request.request_id,
                operation=request.operation,
                status=OdooActionStatus.FAILED,
                model=model,
                error="fetch_record requires a record_id.",
                adapter="mock",
            )

        record = self._store.get(model, {}).get(record_id)
        if record is None:
            return OdooResult(
                request_id=request.request_id,
                operation=request.operation,
                status=OdooActionStatus.NOT_FOUND,
                model=model,
                record_id=record_id,
                error=f"Record {model}:{record_id} not found.",
                adapter="mock",
            )

        return OdooResult(
            request_id=request.request_id,
            operation=request.operation,
            status=OdooActionStatus.SUCCESS,
            model=model,
            record_id=record_id,
            record_data=dict(record),
            adapter="mock",
            executed_at=datetime.now(tz=timezone.utc),
        )


# ---------------------------------------------------------------------------
# RealOdooAdapter — Odoo XML-RPC LIVE integration
# ---------------------------------------------------------------------------

class RealOdooAdapter(OdooAdapter):
    """
    LIVE Odoo adapter backed by Odoo XML-RPC API.

    Connects to Odoo via standard XML-RPC endpoints:
      - /xmlrpc/2/common  → authentication + version
      - /xmlrpc/2/object  → model operations (create / write / read)

    credential_token = Odoo user password (never logged).

    Usage::

        config = OdooConfig(
            odoo_url="http://localhost:8069",
            database="mycompany",
        )
        adapter = RealOdooAdapter(config, username="admin", credential_token="admin123")
        if adapter.health_check():
            req = make_create_request("res.partner", {"name": "Alice"})
            result = adapter.execute(req)
    """

    def __init__(
        self,
        config: OdooConfig,
        username: str = "admin",
        credential_token: str = "",
    ) -> None:
        self._config   = config
        self._username = username
        self._password = credential_token  # never logged
        self._uid: Optional[int] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _common(self):
        import xmlrpc.client
        return xmlrpc.client.ServerProxy(
            f"{self._config.odoo_url}/xmlrpc/2/common"
        )

    def _models(self):
        import xmlrpc.client
        return xmlrpc.client.ServerProxy(
            f"{self._config.odoo_url}/xmlrpc/2/object"
        )

    def _authenticate(self) -> int:
        """Authenticate and cache UID. Returns user ID (int > 0) or raises."""
        if self._uid is not None:
            return self._uid
        uid = self._common().authenticate(
            self._config.database,
            self._username,
            self._password,
            {},
        )
        if not uid:
            raise RuntimeError(
                "Odoo authentication failed — check ODOO_USERNAME / ODOO_PASSWORD / ODOO_DB"
            )
        self._uid = int(uid)
        return self._uid

    # ------------------------------------------------------------------
    # OdooAdapter interface
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        """
        Return True if Odoo is reachable and credentials are valid.
        Never raises.
        """
        try:
            version = self._common().version()
            if not version:
                return False
            # Also verify credentials by authenticating
            uid = self._common().authenticate(
                self._config.database,
                self._username,
                self._password,
                {},
            )
            return bool(uid)
        except Exception:  # noqa: BLE001
            return False

    def execute(self, request: OdooRequest) -> OdooResult:
        """
        Execute an Odoo operation via XML-RPC.

        Supports: CREATE_RECORD, UPDATE_RECORD, FETCH_RECORD.
        Never raises — errors returned as OdooResult with status=FAILED.
        """
        try:
            uid    = self._authenticate()
            models = self._models()
            db     = self._config.database
            pwd    = self._password

            if request.operation == OdooOperation.CREATE_RECORD:
                record_id = models.execute_kw(
                    db, uid, pwd,
                    request.model, "create",
                    [request.data],
                )
                # Fetch the newly created record
                records = models.execute_kw(
                    db, uid, pwd,
                    request.model, "read",
                    [[int(record_id)]],
                )
                return OdooResult(
                    request_id=request.request_id,
                    operation=request.operation,
                    status=OdooActionStatus.SUCCESS,
                    model=request.model,
                    record_id=int(record_id),
                    record_data=records[0] if records else {},
                    adapter="real_odoo",
                    executed_at=datetime.now(tz=timezone.utc),
                )

            elif request.operation == OdooOperation.UPDATE_RECORD:
                models.execute_kw(
                    db, uid, pwd,
                    request.model, "write",
                    [[request.record_id], request.data],
                )
                records = models.execute_kw(
                    db, uid, pwd,
                    request.model, "read",
                    [[request.record_id]],
                )
                return OdooResult(
                    request_id=request.request_id,
                    operation=request.operation,
                    status=OdooActionStatus.SUCCESS,
                    model=request.model,
                    record_id=request.record_id,
                    record_data=records[0] if records else {},
                    adapter="real_odoo",
                    executed_at=datetime.now(tz=timezone.utc),
                )

            elif request.operation == OdooOperation.FETCH_RECORD:
                records = models.execute_kw(
                    db, uid, pwd,
                    request.model, "read",
                    [[request.record_id]],
                )
                if not records:
                    return OdooResult(
                        request_id=request.request_id,
                        operation=request.operation,
                        status=OdooActionStatus.NOT_FOUND,
                        model=request.model,
                        record_id=request.record_id,
                        error=f"Record {request.model}:{request.record_id} not found.",
                        adapter="real_odoo",
                    )
                return OdooResult(
                    request_id=request.request_id,
                    operation=request.operation,
                    status=OdooActionStatus.SUCCESS,
                    model=request.model,
                    record_id=request.record_id,
                    record_data=records[0],
                    adapter="real_odoo",
                    executed_at=datetime.now(tz=timezone.utc),
                )

            else:
                return OdooResult(
                    request_id=request.request_id,
                    operation=request.operation,
                    status=OdooActionStatus.FAILED,
                    model=request.model,
                    error=f"Unsupported operation: {request.operation!r}",
                    adapter="real_odoo",
                )

        except Exception as exc:  # noqa: BLE001
            return OdooResult(
                request_id=request.request_id,
                operation=request.operation,
                status=OdooActionStatus.FAILED,
                model=request.model,
                record_id=request.record_id,
                error=str(exc),
                adapter="real_odoo",
            )
