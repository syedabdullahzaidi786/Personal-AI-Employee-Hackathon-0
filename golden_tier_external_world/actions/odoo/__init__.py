"""
ODOO_MCP_INTEGRATION_SKILL — Phase 1
MCP-style integration skill for Odoo ERP with HITL enforcement.

Constitution compliance:
  - Section 9: Skill Design Rules (atomic, composable, testable)
  - Principle III: HITL by Default (Tier 3 for writes, Tier 1 for reads)
  - Section 8: Credential Storage (credentials_name is a reference only)
  - Principle VI: Fail Safe — denied on HITL failure

Supported operations (Phase 1):
  - create_record  → create a new Odoo record (tier 3 — HITL required)
  - update_record  → update an existing record (tier 3 — HITL required)
  - fetch_record   → read a record (tier 1 — auto-approve)

Public surface::

    from skills.actions.odoo import OdooSkill, OdooConfig

    config = OdooConfig(vault_root="/vault", odoo_url="https://myco.odoo.com", database="prod")
    skill  = OdooSkill(config)

    # Tier 3 write — returns PENDING_APPROVAL when HITLSkill is attached
    result = skill.create_record("res.partner", {"name": "Alice", "email": "alice@example.com"})

    # Tier 1 read — auto-executes
    result = skill.fetch_record("res.partner", record_id=1)
    print(result.record_data)
"""

from __future__ import annotations

from typing import Any, Optional

from .action import OdooAction, ValidationError
from .adapter import MockOdooAdapter, OdooAdapter, RealOdooAdapter
from .logger import OdooLogger
from .models import (
    OdooActionStatus,
    OdooConfig,
    OdooEventType,
    OdooOperation,
    OdooRequest,
    OdooResult,
    make_create_request,
    make_fetch_request,
    make_update_request,
)


class OdooSkill:
    """
    High-level facade for ODOO_MCP_INTEGRATION_SKILL Phase 1.

    Composes: OdooAction + OdooAdapter + OdooLogger.
    Optionally integrates with:
      - HITLSkill             (required for Tier ≥ 2 operations)
      - SecuritySkill         (credential spec registration)
      - OrchestratorSkill     (registers odoo.create_record, odoo.update_record,
                               odoo.fetch_record in SkillRegistry)
    """

    def __init__(
        self,
        config: OdooConfig,
        adapter: Optional[OdooAdapter] = None,
        hitl_skill: Optional[Any] = None,
        security_skill: Optional[Any] = None,
        orchestrator_registry: Optional[Any] = None,
    ) -> None:
        self._config  = config
        self._adapter = adapter or MockOdooAdapter()
        self._logger  = OdooLogger(config.vault_root)
        self._action  = OdooAction(
            config=config,
            adapter=self._adapter,
            logger=self._logger,
            hitl_skill=hitl_skill,
        )

        if security_skill is not None:
            self._register_credential_spec(security_skill)

        if orchestrator_registry is not None:
            self._register_with_orchestrator(orchestrator_registry)

    # ------------------------------------------------------------------
    # Main interface
    # ------------------------------------------------------------------

    def create_record(
        self,
        model: str,
        data: dict[str, Any],
        tier: Optional[int] = None,
    ) -> OdooResult:
        """
        Create a new Odoo record.

        Default tier: 3 (High-risk) → HITL required when HITLSkill attached.
        Returns OdooResult with record_id on SUCCESS.
        """
        request = make_create_request(
            model=model,
            data=data,
            tier=tier if tier is not None else self._config.default_tier,
            credentials_name=self._config.credentials_name,
        )
        return self._action.execute(request)

    def update_record(
        self,
        model: str,
        record_id: int,
        data: dict[str, Any],
        tier: Optional[int] = None,
    ) -> OdooResult:
        """
        Update an existing Odoo record.

        Default tier: 3 (High-risk) → HITL required when HITLSkill attached.
        Returns OdooResult with updated record_data on SUCCESS.
        """
        request = make_update_request(
            model=model,
            record_id=record_id,
            data=data,
            tier=tier if tier is not None else self._config.default_tier,
            credentials_name=self._config.credentials_name,
        )
        return self._action.execute(request)

    def fetch_record(
        self,
        model: str,
        record_id: int,
        tier: Optional[int] = None,
    ) -> OdooResult:
        """
        Fetch an Odoo record by ID.

        Default tier: 1 (read-only, auto-approve).
        Returns OdooResult with record_data on SUCCESS.
        """
        request = make_fetch_request(
            model=model,
            record_id=record_id,
            tier=tier if tier is not None else 1,  # reads default to tier 1
            credentials_name=self._config.credentials_name,
        )
        return self._action.execute(request)

    def execute_request(self, request: OdooRequest) -> OdooResult:
        """Execute a pre-built OdooRequest directly."""
        return self._action.execute(request)

    def health_check(self) -> bool:
        """Return True if the Odoo adapter is healthy."""
        return self._action.health_check()

    # ------------------------------------------------------------------
    # HITL integration
    # ------------------------------------------------------------------

    def set_hitl(self, hitl_skill: Any) -> None:
        """Attach a HITLSkill for Tier ≥ 2 routing."""
        self._action._hitl = hitl_skill

    # ------------------------------------------------------------------
    # Logging / introspection
    # ------------------------------------------------------------------

    def read_logs(self, date: Optional[str] = None) -> list[dict]:
        """Return Odoo log entries for a given date (YYYY-MM-DD). Default: today."""
        return self._logger.read_entries(date)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def config(self) -> OdooConfig:
        return self._config

    @property
    def adapter(self) -> OdooAdapter:
        return self._adapter

    @property
    def logger(self) -> OdooLogger:
        return self._logger

    @property
    def action(self) -> OdooAction:
        return self._action

    # ------------------------------------------------------------------
    # Security integration
    # ------------------------------------------------------------------

    def _register_credential_spec(self, security_skill: Any) -> None:
        """Register a CredentialSpec for the Odoo credential with SecuritySkill."""
        try:
            from bronze_tier_governance.security.models import (
                CredentialSpec,
                CredentialType,
            )
            spec = CredentialSpec(
                name=self._config.credentials_name,
                env_key=self._config.credentials_name.upper(),
                cred_type=CredentialType.API_KEY,
                description=(
                    f"Odoo API credential for {self._config.odoo_url or 'Odoo instance'}"
                    f"{f' / db={self._config.database}' if self._config.database else ''}"
                ),
                required=True,
            )
            security_skill.register(spec)
        except Exception:  # noqa: BLE001
            pass  # Non-fatal — security integration is optional in Phase 1

    # ------------------------------------------------------------------
    # Orchestrator integration (MCP action registration)
    # ------------------------------------------------------------------

    def _register_with_orchestrator(self, registry: Any) -> None:
        """Register odoo.create_record, odoo.update_record, odoo.fetch_record."""
        try:
            def _create_handler(**kwargs: Any) -> dict:
                model  = kwargs.get("model", "")
                data   = kwargs.get("data", {})
                tier   = kwargs.get("tier", self._config.default_tier)
                result = self.create_record(model=model, data=data, tier=tier)
                return result.to_dict()

            def _update_handler(**kwargs: Any) -> dict:
                model     = kwargs.get("model", "")
                record_id = int(kwargs.get("record_id", 0))
                data      = kwargs.get("data", {})
                tier      = kwargs.get("tier", self._config.default_tier)
                result    = self.update_record(model=model, record_id=record_id, data=data, tier=tier)
                return result.to_dict()

            def _fetch_handler(**kwargs: Any) -> dict:
                model     = kwargs.get("model", "")
                record_id = int(kwargs.get("record_id", 0))
                tier      = kwargs.get("tier", 1)
                result    = self.fetch_record(model=model, record_id=record_id, tier=tier)
                return result.to_dict()

            registry.register("odoo", "create_record", _create_handler)
            registry.register("odoo", "update_record", _update_handler)
            registry.register("odoo", "fetch_record",  _fetch_handler)
        except Exception:  # noqa: BLE001
            pass  # Non-fatal


__all__ = [
    # Facade
    "OdooSkill",
    # Config / models
    "OdooConfig",
    "OdooRequest",
    "OdooResult",
    "OdooActionStatus",
    "OdooOperation",
    "OdooEventType",
    "make_create_request",
    "make_update_request",
    "make_fetch_request",
    # Adapters
    "OdooAdapter",
    "MockOdooAdapter",
    "RealOdooAdapter",
    # Action
    "OdooAction",
    "ValidationError",
    # Logger
    "OdooLogger",
]
