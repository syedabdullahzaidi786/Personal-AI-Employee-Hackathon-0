"""
GMAIL_WATCHER_SKILL — Phase 1
High-level facade for Gmail event monitoring.

Constitution compliance:
  - Section 9: Skill Design Rules (atomic, composable, testable)
  - Section 3: HITL by Default (Tier 2 events via EventDispatcher)
  - Principle I: Local-First (events + seen-IDs persisted to Obsidian vault)
  - Section 8: Credential Storage (credentials_name is a reference only)

Public surface::

    from skills.watchers.gmail import GmailWatcherSkill, GmailConfig, MockGmailClient

    config = GmailConfig(account_email="you@gmail.com", vault_root="/vault")
    skill  = GmailWatcherSkill(config)
    skill.register_handler("gmail_new_message", lambda e: print(e.payload["subject"]))
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
from .client import GmailClient, MockGmailClient, RealGmailClient
from .handlers import (
    make_filter_handler,
    make_log_handler,
    make_orchestrator_handler,
    make_sender_filter,
)
from .models import (
    GmailConfig,
    GmailEventType,
    GmailMessage,
    make_gmail_message,
)
from .watcher import GmailWatcher


class GmailWatcherSkill:
    """
    High-level facade for GMAIL_WATCHER_SKILL Phase 1.

    Composes: GmailWatcher + EventDispatcher.
    Optionally integrates with SecuritySkill (credential registration)
    and OrchestratorSkill (workflow triggering).
    """

    def __init__(
        self,
        gmail_config: GmailConfig,
        client: Optional[GmailClient] = None,
        security_skill: Optional[Any] = None,
    ) -> None:
        self._gmail_config    = gmail_config
        self._dispatcher      = EventDispatcher()
        self._watcher         = GmailWatcher(gmail_config, client or MockGmailClient())
        self._security_skill  = security_skill

        # Optionally register a CredentialSpec with SecuritySkill
        if security_skill is not None:
            self._register_credential_spec(security_skill)

    # ------------------------------------------------------------------
    # Credential integration
    # ------------------------------------------------------------------

    def _register_credential_spec(self, security_skill: Any) -> None:
        """
        Register a CredentialSpec for the Gmail API key with SecuritySkill.

        Silently skips if SecuritySkill doesn't support register_credential.
        """
        try:
            from ...safety.security.models import (  # type: ignore[import]
                CredentialSpec,
                CredentialType,
            )
            spec = CredentialSpec(
                name=self._gmail_config.credentials_name,
                credential_type=CredentialType.OAUTH_SECRET,
                description=f"Gmail OAuth token for {self._gmail_config.account_email}",
                env_var=self._gmail_config.credentials_name.upper(),
                required=True,
            )
            security_skill.register_credential(spec)
        except Exception:  # noqa: BLE001
            # Non-fatal — security integration is optional in Phase 1
            pass

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

    def set_hitl(self, hitl_skill: Any) -> None:
        """Attach HITLSkill for Tier 2+ event routing."""
        self._dispatcher.set_hitl(hitl_skill)

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
        """Run one poll cycle."""
        return self._watcher.tick(self._dispatcher)

    # ------------------------------------------------------------------
    # Convenience: inject (testing / manual)
    # ------------------------------------------------------------------

    def inject_message(self, message: GmailMessage) -> None:
        """
        Inject a message into the underlying MockGmailClient.

        Raises TypeError if the client is not a MockGmailClient.
        """
        if not isinstance(self._watcher.client, MockGmailClient):
            raise TypeError(
                "inject_message() is only available when using MockGmailClient."
            )
        self._watcher.client.inject_message(message)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def watcher(self) -> GmailWatcher:
        return self._watcher

    @property
    def dispatcher(self) -> EventDispatcher:
        return self._dispatcher

    @property
    def gmail_config(self) -> GmailConfig:
        return self._gmail_config


__all__ = [
    # Facade
    "GmailWatcherSkill",
    # Config / models
    "GmailConfig",
    "GmailMessage",
    "GmailEventType",
    "make_gmail_message",
    # Clients
    "GmailClient",
    "MockGmailClient",
    "RealGmailClient",
    # Watcher
    "GmailWatcher",
    # Handlers
    "make_log_handler",
    "make_orchestrator_handler",
    "make_filter_handler",
    "make_sender_filter",
]
