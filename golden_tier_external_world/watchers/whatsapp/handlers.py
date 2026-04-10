"""
WHATSAPP_WATCHER_SKILL — Pre-built Event Handlers
Phase 1: Factory functions returning WatcherEvent → Any callables.

Included handlers:
  - make_log_handler          — print one-line event summary
  - make_orchestrator_handler — trigger an Orchestrator workflow
  - make_filter_handler       — conditional routing
  - make_group_filter         — pass only group messages
  - make_private_filter       — pass only private (DM) messages
  - make_sender_filter        — pass only messages from specific senders
  - make_media_filter         — pass only media messages

Constitution compliance:
  - Section 9: Skill Design Rules — composable, single-purpose handlers
  - Section 8: No secrets in handler output — payload already sanitised by WhatsAppWatcher
"""

from __future__ import annotations

import sys
from typing import Any, Callable, Optional

from ..base.models import WatcherEvent
from .models import WhatsAppChatType, WhatsAppEventType, WhatsAppMessageType


# ---------------------------------------------------------------------------
# Log handler
# ---------------------------------------------------------------------------

def make_log_handler(
    prefix: str = "[WhatsAppWatcher]",
    stream: Any = None,
) -> Callable[[WatcherEvent], None]:
    """
    Return a handler that prints a one-line summary of each event.

    Args:
        prefix: String prepended to each log line.
        stream: Output stream (default: sys.stdout).
    """
    out = stream or sys.stdout

    def _handler(event: WatcherEvent) -> None:
        sender  = event.payload.get("sender_phone", "(unknown)")
        name    = event.payload.get("sender_name",  "")
        body    = event.payload.get("message_body", "")[:60]
        grp     = event.payload.get("group_name",   "")
        ts      = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        source  = f"{name} ({sender})" if name else sender
        if grp:
            source = f"{source} in {grp}"
        out.write(f"{prefix} [{ts}] {event.event_type} | {source}: {body!r}\n")
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

    The context dict passed to ``orchestrator.run_workflow()`` contains:
      - event_id, event_type, source, timestamp
      - all payload fields (WhatsAppMessage safe metadata)
      - any keys from *extra_context*

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
# Generic filter handler
# ---------------------------------------------------------------------------

def make_filter_handler(
    condition: Callable[[WatcherEvent], bool],
    then_handler: Callable[[WatcherEvent], Any],
    else_handler: Optional[Callable[[WatcherEvent], Any]] = None,
) -> Callable[[WatcherEvent], Any]:
    """
    Return a handler that routes based on *condition*.

    Args:
        condition:    Callable(event) → bool
        then_handler: Called when condition is True.
        else_handler: Optional handler called when condition is False.
    """

    def _handler(event: WatcherEvent) -> Any:
        if condition(event):
            return then_handler(event)
        if else_handler is not None:
            return else_handler(event)
        return None

    return _handler


# ---------------------------------------------------------------------------
# Convenience filters
# ---------------------------------------------------------------------------

def make_group_filter(
    then_handler: Callable[[WatcherEvent], Any],
    else_handler: Optional[Callable[[WatcherEvent], Any]] = None,
) -> Callable[[WatcherEvent], Any]:
    """
    Pass only group messages to *then_handler*.

    Convenience wrapper: checks ``event.payload["chat_type"] == "group"``.
    """
    return make_filter_handler(
        lambda e: e.payload.get("chat_type", "") == WhatsAppChatType.GROUP,
        then_handler,
        else_handler,
    )


def make_private_filter(
    then_handler: Callable[[WatcherEvent], Any],
    else_handler: Optional[Callable[[WatcherEvent], Any]] = None,
) -> Callable[[WatcherEvent], Any]:
    """
    Pass only private (DM) messages to *then_handler*.
    """
    return make_filter_handler(
        lambda e: e.payload.get("chat_type", "") == WhatsAppChatType.PRIVATE,
        then_handler,
        else_handler,
    )


def make_sender_filter(
    allowed_senders: list[str],
    then_handler: Callable[[WatcherEvent], Any],
    else_handler: Optional[Callable[[WatcherEvent], Any]] = None,
) -> Callable[[WatcherEvent], Any]:
    """
    Pass only messages from *allowed_senders* (phone numbers, case-insensitive strip).
    """
    normalised = {s.strip() for s in allowed_senders}

    return make_filter_handler(
        lambda e: e.payload.get("sender_phone", "") in normalised,
        then_handler,
        else_handler,
    )


def make_media_filter(
    then_handler: Callable[[WatcherEvent], Any],
    else_handler: Optional[Callable[[WatcherEvent], Any]] = None,
) -> Callable[[WatcherEvent], Any]:
    """
    Pass only media messages (image, audio, video, document, sticker).
    """
    _media_event_types = {
        WhatsAppEventType.NEW_MEDIA_MESSAGE,
        WhatsAppEventType.NEW_GROUP_MESSAGE,  # group messages may carry media
    }
    _media_msg_types = WhatsAppMessageType._MEDIA_TYPES

    def _is_media(event: WatcherEvent) -> bool:
        return event.payload.get("message_type", "") in _media_msg_types

    return make_filter_handler(_is_media, then_handler, else_handler)
