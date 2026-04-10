"""
BROWSER_MCP_SKILL — Phase 1
MCP-style action skill for browser automation with HITL enforcement.

Constitution compliance:
  - Section 9: Skill Design Rules (atomic, composable, testable)
  - Principle III: HITL by Default (Tier 2 → HITL required)
  - Section 8: Credential Storage (credentials_name is a reference only)
  - Principle VI: Fail Safe — denied on HITL failure

Supported actions (Phase 1):
  - open_url      → open a URL, return page title
  - extract_text  → extract text from URL with optional CSS/XPath selector

Public surface::

    from skills.actions.browser import BrowserSkill, BrowserConfig

    config = BrowserConfig(vault_root="/vault")
    skill  = BrowserSkill(config)

    # Tier 2 (default) — returns PENDING_APPROVAL when HITLSkill attached
    result = skill.open_url("https://example.com")
    print(result.status)   # PENDING_APPROVAL or SUCCESS (no HITL skill)

    result = skill.extract_text("https://example.com", selector="h1")
    print(result.content)
"""

from __future__ import annotations

from typing import Any, Optional

from .action import BrowserAction, ValidationError
from .adapter import BrowserAdapter, MockBrowserAdapter, RealBrowserAdapter
from .logger import BrowserLogger
from .models import (
    BrowserActionStatus,
    BrowserActionType,
    BrowserConfig,
    BrowserEventType,
    BrowserRequest,
    BrowserResult,
    make_extract_text_request,
    make_open_url_request,
)


class BrowserSkill:
    """
    High-level facade for BROWSER_MCP_SKILL Phase 1.

    Composes: BrowserAction + BrowserAdapter + BrowserLogger.
    Optionally integrates with:
      - HITLSkill             (required for Tier ≥ 2 actions)
      - SecuritySkill         (credential spec registration)
      - OrchestratorSkill     (registers browser.open_url + browser.extract_text)
    """

    def __init__(
        self,
        config: BrowserConfig,
        adapter: Optional[BrowserAdapter] = None,
        hitl_skill: Optional[Any] = None,
        security_skill: Optional[Any] = None,
        orchestrator_registry: Optional[Any] = None,
    ) -> None:
        self._config  = config
        self._adapter = adapter or MockBrowserAdapter()
        self._logger  = BrowserLogger(config.vault_root)
        self._action  = BrowserAction(
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

    def open_url(
        self,
        url: str,
        tier: Optional[int] = None,
    ) -> BrowserResult:
        """
        Open a URL and return the page title.

        Returns BrowserResult with:
          - SUCCESS          → page opened (content = page title)
          - PENDING_APPROVAL → queued for HITL (tier ≥ 2 + HITLSkill)
          - DENIED           → HITL submission failed (fail-safe)
          - FAILED           → validation or adapter error
        """
        request = make_open_url_request(
            url=url,
            tier=tier if tier is not None else self._config.default_tier,
            credentials_name=self._config.credentials_name,
        )
        return self._action.execute(request)

    def extract_text(
        self,
        url: str,
        selector: str = "",
        tier: Optional[int] = None,
    ) -> BrowserResult:
        """
        Extract text from a URL using an optional CSS/XPath selector.

        Returns BrowserResult with:
          - SUCCESS          → text extracted (content = extracted text)
          - PENDING_APPROVAL → queued for HITL (tier ≥ 2 + HITLSkill)
          - DENIED           → HITL submission failed (fail-safe)
          - FAILED           → validation or adapter error
        """
        request = make_extract_text_request(
            url=url,
            selector=selector,
            tier=tier if tier is not None else self._config.default_tier,
            credentials_name=self._config.credentials_name,
        )
        return self._action.execute(request)

    def execute_request(self, request: BrowserRequest) -> BrowserResult:
        """Execute a pre-built BrowserRequest directly."""
        return self._action.execute(request)

    def health_check(self) -> bool:
        """Return True if the browser adapter is healthy."""
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
        """Return browser log entries for a given date (YYYY-MM-DD). Default: today."""
        return self._logger.read_entries(date)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def config(self) -> BrowserConfig:
        return self._config

    @property
    def adapter(self) -> BrowserAdapter:
        return self._adapter

    @property
    def logger(self) -> BrowserLogger:
        return self._logger

    @property
    def action(self) -> BrowserAction:
        return self._action

    # ------------------------------------------------------------------
    # Security integration
    # ------------------------------------------------------------------

    def _register_credential_spec(self, security_skill: Any) -> None:
        """Register a CredentialSpec for the browser credential with SecuritySkill."""
        try:
            from bronze_tier_governance.security.models import (
                CredentialSpec,
                CredentialType,
            )
            spec = CredentialSpec(
                name=self._config.credentials_name,
                env_key=self._config.credentials_name.upper(),
                cred_type=CredentialType.API_KEY,
                description="Browser automation credential (API key or session token)",
                required=False,  # Not required for Phase 1 (mock adapter)
            )
            security_skill.register(spec)
        except Exception:  # noqa: BLE001
            pass  # Non-fatal — security integration is optional in Phase 1

    # ------------------------------------------------------------------
    # Orchestrator integration (MCP action registration)
    # ------------------------------------------------------------------

    def _register_with_orchestrator(self, registry: Any) -> None:
        """Register browser.open_url and browser.extract_text in the SkillRegistry."""
        try:
            def _open_url_handler(**kwargs: Any) -> dict:
                url    = kwargs.get("url", "")
                tier   = kwargs.get("tier", self._config.default_tier)
                result = self.open_url(url=url, tier=tier)
                return result.to_dict()

            def _extract_text_handler(**kwargs: Any) -> dict:
                url      = kwargs.get("url", "")
                selector = kwargs.get("selector", "")
                tier     = kwargs.get("tier", self._config.default_tier)
                result   = self.extract_text(url=url, selector=selector, tier=tier)
                return result.to_dict()

            registry.register("browser", "open_url",     _open_url_handler)
            registry.register("browser", "extract_text", _extract_text_handler)
        except Exception:  # noqa: BLE001
            pass  # Non-fatal


__all__ = [
    # Facade
    "BrowserSkill",
    # Config / models
    "BrowserConfig",
    "BrowserRequest",
    "BrowserResult",
    "BrowserActionStatus",
    "BrowserActionType",
    "BrowserEventType",
    "make_open_url_request",
    "make_extract_text_request",
    # Adapters
    "BrowserAdapter",
    "MockBrowserAdapter",
    "RealBrowserAdapter",
    # Action
    "BrowserAction",
    "ValidationError",
    # Logger
    "BrowserLogger",
]
