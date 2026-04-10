"""
WHATSAPP_WATCHER_SKILL — Phase 1
High-level facade for WhatsApp message monitoring.

Constitution compliance:
  - Section 9: Skill Design Rules (atomic, composable, testable)
  - Section 3: HITL by Default (Tier ≥ 2 events via EventDispatcher)
  - Principle I: Local-First (events + seen-IDs persisted to Obsidian vault)
  - Section 8: Credential Storage (credentials_name is a reference only)

Public surface::

    from skills.watchers.whatsapp import WhatsAppWatcherSkill, WhatsAppConfig, MockWhatsAppClient

    config = WhatsAppConfig(phone_number="+14155552671", vault_root="/vault")
    skill  = WhatsAppWatcherSkill(config)
    skill.register_handler("whatsapp_new_text_message", lambda e: print(e.payload["message_body"]))
    skill.start()
    result = skill.tick()
    print(result.events_found)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

from ..base import (
    EventDispatcher,
    WatcherEvent,
    WatcherTickResult,
)
from .client import MockWhatsAppClient, PlaywrightWhatsAppClient, WhatsAppClient
from .handlers import (
    make_filter_handler,
    make_group_filter,
    make_log_handler,
    make_media_filter,
    make_orchestrator_handler,
    make_private_filter,
    make_sender_filter,
)
from .models import (
    WhatsAppChatType,
    WhatsAppConfig,
    WhatsAppEventType,
    WhatsAppMessage,
    WhatsAppMessageType,
    make_whatsapp_message,
)
from .watcher import WhatsAppWatcher


class WhatsAppWatcherSkill:
    """
    High-level facade for WHATSAPP_WATCHER_SKILL Phase 1.

    Composes: WhatsAppWatcher + EventDispatcher.
    Optionally integrates with SecuritySkill (credential registration)
    and OrchestratorSkill (workflow triggering).

    HITL enforcement:
      Events emitted at tier ≥ 2 (the default) are routed through
      EventDispatcher.  When a HITLSkill is attached via set_hitl(),
      Tier 2+ events are submitted for human approval before handlers fire.
    """

    def __init__(
        self,
        wa_config: WhatsAppConfig,
        client: Optional[WhatsAppClient] = None,
        security_skill: Optional[Any] = None,
    ) -> None:
        self._wa_config       = wa_config
        self._dispatcher      = EventDispatcher()
        self._watcher         = WhatsAppWatcher(wa_config, client or MockWhatsAppClient())
        self._security_skill  = security_skill

        if security_skill is not None:
            self._register_credential_spec(security_skill)

    # ------------------------------------------------------------------
    # Credential integration (optional)
    # ------------------------------------------------------------------

    def _register_credential_spec(self, security_skill: Any) -> None:
        """Register a CredentialSpec for the WhatsApp API key. Non-fatal if it fails."""
        try:
            from ...safety.security.models import (  # type: ignore[import]
                CredentialSpec,
                CredentialType,
            )
            spec = CredentialSpec(
                name=self._wa_config.credentials_name,
                credential_type=CredentialType.API_KEY,
                description=f"WhatsApp API token for {self._wa_config.phone_number}",
                env_var=self._wa_config.credentials_name.upper(),
                required=True,
            )
            security_skill.register_credential(spec)
        except Exception:  # noqa: BLE001
            pass  # Security integration is optional in Phase 1

    # ------------------------------------------------------------------
    # HITL wiring
    # ------------------------------------------------------------------

    def set_hitl(self, hitl_skill: Any) -> None:
        """
        Attach HITLSkill for Tier ≥ 2 event routing.

        Once attached, all events at tier ≥ 2 are submitted to the HITL
        queue before any registered handlers are called.
        """
        self._dispatcher.set_hitl(hitl_skill)

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def register_handler(
        self,
        event_type: str,
        handler: Callable[[WatcherEvent], Any],
    ) -> None:
        """Register an event handler. Use ``"*"`` to catch all event types."""
        self._dispatcher.register_handler(event_type, handler)

    def unregister_handler(self, event_type: str) -> None:
        self._dispatcher.unregister_handler(event_type)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Mark watcher as RUNNING."""
        self._watcher.start()

    def stop(self) -> None:
        """Mark watcher as STOPPED."""
        self._watcher.stop()

    def is_running(self) -> bool:
        return self._watcher.is_running()

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def tick(self) -> WatcherTickResult:
        """
        Run one poll cycle.

        Events at tier ≥ 2 will be routed through the EventDispatcher
        (and HITLSkill if attached) before registered handlers fire.
        """
        return self._watcher.tick(self._dispatcher)

    # ------------------------------------------------------------------
    # Convenience: inject (testing / manual)
    # ------------------------------------------------------------------

    def inject_message(self, message: WhatsAppMessage) -> None:
        """
        Inject a message into the underlying MockWhatsAppClient.

        Raises TypeError if the client is not a MockWhatsAppClient.
        """
        if not isinstance(self._watcher.client, MockWhatsAppClient):
            raise TypeError(
                "inject_message() is only available when using MockWhatsAppClient."
            )
        self._watcher.client.inject_message(message)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def watcher(self) -> WhatsAppWatcher:
        return self._watcher

    @property
    def dispatcher(self) -> EventDispatcher:
        return self._dispatcher

    @property
    def wa_config(self) -> WhatsAppConfig:
        return self._wa_config


__all__ = [
    # Facade
    "WhatsAppWatcherSkill",
    # Config / models
    "WhatsAppConfig",
    "WhatsAppMessage",
    "WhatsAppEventType",
    "WhatsAppMessageType",
    "WhatsAppChatType",
    "make_whatsapp_message",
    # Clients
    "WhatsAppClient",
    "MockWhatsAppClient",
    "PlaywrightWhatsAppClient",
    # Watcher
    "WhatsAppWatcher",
    # Handlers
    "make_log_handler",
    "make_orchestrator_handler",
    "make_filter_handler",
    "make_group_filter",
    "make_private_filter",
    "make_sender_filter",
    "make_media_filter",
]
