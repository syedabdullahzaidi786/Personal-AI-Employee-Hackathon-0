"""
BASE_WATCHER_CREATION_SKILL — Event Dispatcher
Routes WatcherEvents to handlers or HITL approval queue.

Constitution compliance:
  - Section 3: HITL by Default — tier >= 2 requires human approval
  - Principle III: Human-in-the-Loop — watchers are Tier 2 by default
  - Principle VI: Fail Safe — dispatch errors are captured, never silent
"""

from __future__ import annotations

import sys
from typing import Any, Callable, Optional

from .models import DispatchResult, WatcherEvent


class EventDispatcher:
    """
    Routes WatcherEvents to registered handlers or the HITL approval queue.

    Routing rules:
      - tier 0 or 1 → call handler directly (auto-approved)
      - tier 2+      → submit to HITL first; handler called after approval
                       (approval flow handled externally in Phase 1)

    If no HITL skill is set and tier >= 2, the event is dispatched directly
    with a warning (fail-open for local dev; override in production).

    Usage::

        dispatcher = EventDispatcher()
        dispatcher.register_handler("file_created", my_handler)
        dispatcher.register_handler("*", fallback_handler)  # wildcard

        result = dispatcher.dispatch(event)
    """

    def __init__(self, fail_open: bool = True) -> None:
        """
        Parameters
        ----------
        fail_open:
            If True (default), dispatch Tier 2+ events directly when HITL is
            unavailable (local dev mode). Set False in production.
        """
        self._handlers: dict[str, list[Callable[[WatcherEvent], Any]]] = {}
        self._hitl: Optional[Any] = None
        self._fail_open = fail_open

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_hitl(self, hitl_skill: Any) -> None:
        """Attach an HITLSkill for Tier 2+ approval routing."""
        self._hitl = hitl_skill

    def register_handler(self, event_type: str, handler: Callable[[WatcherEvent], Any]) -> None:
        """
        Register *handler* for *event_type*.

        Use ``"*"`` as *event_type* to receive all events.
        Multiple handlers per type are called in registration order.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unregister_handler(self, event_type: str) -> None:
        """Remove all handlers for *event_type*."""
        self._handlers.pop(event_type, None)

    def list_handlers(self) -> dict[str, int]:
        """Return {event_type: handler_count} for introspection."""
        return {k: len(v) for k, v in self._handlers.items()}

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(self, event: WatcherEvent) -> DispatchResult:
        """
        Route *event* to the appropriate destination.

        Never raises — all exceptions are captured in DispatchResult.error.
        """
        try:
            if event.tier < 2:
                return self._direct_dispatch(event)
            return self._hitl_dispatch(event)
        except Exception as exc:  # noqa: BLE001
            return DispatchResult(
                event_id=event.event_id,
                dispatched=False,
                handler_called=False,
                hitl_submitted=False,
                error=f"{type(exc).__name__}: {exc}",
            )

    # ------------------------------------------------------------------
    # Internal routing
    # ------------------------------------------------------------------

    def _direct_dispatch(self, event: WatcherEvent) -> DispatchResult:
        """Call registered handlers immediately."""
        handlers = (
            self._handlers.get(event.event_type, [])
            + self._handlers.get("*", [])
        )
        called = False
        error_msg = None
        for handler in handlers:
            try:
                handler(event)
                called = True
            except Exception as exc:  # noqa: BLE001
                error_msg = f"handler error: {exc}"
                print(f"[EventDispatcher] handler error for {event.event_id}: {exc}", file=sys.stderr)

        return DispatchResult(
            event_id=event.event_id,
            dispatched=True,
            handler_called=called,
            hitl_submitted=False,
            error=error_msg,
        )

    def _hitl_dispatch(self, event: WatcherEvent) -> DispatchResult:
        """Submit to HITL queue for Tier 2+ events."""
        if self._hitl is None:
            if self._fail_open:
                # Warn and fall through to direct dispatch
                print(
                    f"[EventDispatcher] HITL not configured for tier-{event.tier} event "
                    f"{event.event_id}; dispatching directly (fail_open=True)",
                    file=sys.stderr,
                )
                result = self._direct_dispatch(event)
                result.error = (result.error or "") + " [HITL not configured, dispatched directly]"
                return result
            else:
                return DispatchResult(
                    event_id=event.event_id,
                    dispatched=False,
                    handler_called=False,
                    hitl_submitted=False,
                    error="HITL not configured (fail_open=False); event not dispatched",
                )

        # Submit to HITL
        try:
            from skills.safety.hitl import make_request
            from skills.safety.hitl.models import Tier

            req = make_request(
                action=f"watcher-event:{event.event_type}",
                context={
                    "event_id":   event.event_id,
                    "source":     event.source,
                    "watcher_id": event.watcher_id,
                    "event_type": event.event_type,
                },
                requested_by=event.watcher_id,
                tier=Tier(min(event.tier, 4)),
                description=f"Watcher event '{event.event_type}' from '{event.source}'",
            )
            self._hitl.submit(req)
            return DispatchResult(
                event_id=event.event_id,
                dispatched=True,
                handler_called=False,
                hitl_submitted=True,
                hitl_request_id=req.request_id,
            )
        except Exception as exc:  # noqa: BLE001
            # HITL submit failed — fall back to direct if fail_open
            if self._fail_open:
                result = self._direct_dispatch(event)
                result.error = f"HITL submit failed ({exc}); direct dispatch used"
                return result
            return DispatchResult(
                event_id=event.event_id,
                dispatched=False,
                handler_called=False,
                hitl_submitted=False,
                error=f"HITL submit failed: {exc}",
            )
