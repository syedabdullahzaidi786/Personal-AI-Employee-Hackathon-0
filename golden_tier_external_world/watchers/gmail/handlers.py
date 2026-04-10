"""
GMAIL_WATCHER_SKILL — Pre-built Event Handlers
Phase 1: Factory functions returning WatcherEvent → Any callables.

Usage::

    from skills.watchers.gmail.handlers import make_log_handler, make_orchestrator_handler

    skill.register_handler("gmail_new_message", make_log_handler())
    skill.register_handler("gmail_new_message", make_orchestrator_handler(orc, "process-email"))

Constitution compliance:
  - Section 9: Skill Design Rules — composable, single-purpose handlers
  - Section 8: No secrets in handler output — payload already sanitised by GmailWatcher
"""

from __future__ import annotations

import sys
from typing import Any, Callable, Optional

from ..base.models import WatcherEvent


# ---------------------------------------------------------------------------
# Log handler
# ---------------------------------------------------------------------------

def make_log_handler(
    prefix: str = "[GmailWatcher]",
    stream: Any = None,
) -> Callable[[WatcherEvent], None]:
    """
    Return a handler that prints a one-line summary of the event.

    Args:
        prefix: String prepended to each log line.
        stream: Output stream (default: sys.stdout).
    """
    out = stream or sys.stdout

    def _handler(event: WatcherEvent) -> None:
        subject = event.payload.get("subject", "(no subject)")
        sender  = event.payload.get("sender",  "(unknown)")
        ts      = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        out.write(
            f"{prefix} [{ts}] {event.event_type} | {sender} → {subject}\n"
        )
        out.flush()

    return _handler


# ---------------------------------------------------------------------------
# Orchestrator handler
# ---------------------------------------------------------------------------

def make_orchestrator_handler(
    orchestrator: Any,
    workflow_name: str,
    extra_context: Optional[dict] = None,
) -> Callable[[WatcherEvent], Any]:
    """
    Return a handler that triggers an Orchestrator workflow for each event.

    The handler calls ``orchestrator.run_workflow(workflow_name, context)``
    where context contains the event payload plus any extra_context keys.

    Args:
        orchestrator:  An OrchestratorSkill instance (or any object with
                       a ``run_workflow(name, context)`` method).
        workflow_name: Name of the workflow to trigger.
        extra_context: Optional additional keys merged into the context dict.
    """

    def _handler(event: WatcherEvent) -> Any:
        ctx = {
            "event_id":   event.event_id,
            "event_type": event.event_type,
            "source":     event.source,
            "timestamp":  event.timestamp.isoformat(),
            **event.payload,
            **(extra_context or {}),
        }
        return orchestrator.run_workflow(workflow_name, ctx)

    return _handler


# ---------------------------------------------------------------------------
# Filter handler
# ---------------------------------------------------------------------------

def make_filter_handler(
    condition: Callable[[WatcherEvent], bool],
    then_handler: Callable[[WatcherEvent], Any],
    else_handler: Optional[Callable[[WatcherEvent], Any]] = None,
) -> Callable[[WatcherEvent], Any]:
    """
    Return a handler that applies *then_handler* only when *condition* is True.

    Args:
        condition:    Callable(event) → bool
        then_handler: Handler to call when condition is True.
        else_handler: Optional handler to call when condition is False.
    """

    def _handler(event: WatcherEvent) -> Any:
        if condition(event):
            return then_handler(event)
        if else_handler is not None:
            return else_handler(event)
        return None

    return _handler


# ---------------------------------------------------------------------------
# Sender-filter shortcut
# ---------------------------------------------------------------------------

def make_sender_filter(
    allowed_senders: list[str],
    then_handler: Callable[[WatcherEvent], Any],
) -> Callable[[WatcherEvent], Any]:
    """
    Convenience wrapper around make_filter_handler for sender-based filtering.

    Only calls *then_handler* when event.payload["sender"] is in *allowed_senders*.
    Comparison is case-insensitive.
    """
    normalised = {s.lower() for s in allowed_senders}

    def _condition(event: WatcherEvent) -> bool:
        sender = event.payload.get("sender", "").lower()
        return sender in normalised

    return make_filter_handler(_condition, then_handler)
