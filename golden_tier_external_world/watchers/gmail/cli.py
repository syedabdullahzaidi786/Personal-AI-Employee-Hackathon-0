"""
GMAIL_WATCHER_SKILL — CLI
Commands: status, tick, events, inject

Usage::

    python -m skills.watchers.gmail.cli --vault /vault --account you@gmail.com status
    python -m skills.watchers.gmail.cli --vault /vault --account you@gmail.com tick
    python -m skills.watchers.gmail.cli --vault /vault --account you@gmail.com events [--date YYYY-MM-DD]
    python -m skills.watchers.gmail.cli --vault /vault --account you@gmail.com inject --subject "Hi" --sender alice@example.com
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_GREEN  = "\033[92m"
_RED    = "\033[91m"
_YELLOW = "\033[93m"
_CYAN   = "\033[96m"
_RESET  = "\033[0m"


def _c(text: str, colour: str) -> str:
    return f"{colour}{text}{_RESET}"


def _status_colour(status: str) -> str:
    return {
        "running": _c(status, _GREEN),
        "idle":    _c(status, _CYAN),
        "paused":  _c(status, _YELLOW),
        "error":   _c(status, _RED),
        "stopped": _c(status, _RED),
    }.get(status.lower(), status)


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def cmd_status(args: argparse.Namespace) -> int:
    """Show watcher status by reading persisted state.json."""
    import json

    vault   = Path(args.vault)
    account = args.account
    # Derive watcher_id from account email (matches GmailConfig logic)
    safe_id = account.replace("@", "_at_").replace(".", "_")
    wid     = f"gmail-{safe_id}"

    state_file = vault / "70-LOGS" / "watchers" / wid / "state.json"
    if not state_file.exists():
        print(_c(f"No state found for watcher '{wid}'.", _RED))
        print(f"  → Expected: {state_file}")
        return 1

    state = json.loads(state_file.read_text(encoding="utf-8"))
    print(f"\n{'Watcher':15s}: {state.get('watcher_id', wid)}")
    print(f"{'Status':15s}: {_status_colour(state.get('status', '?'))}")
    print(f"{'Poll count':15s}: {state.get('poll_count', 0)}")
    print(f"{'Total events':15s}: {state.get('total_events', 0)}")
    print(f"{'Error count':15s}: {state.get('error_count', 0)}")
    print(f"{'Last poll':15s}: {state.get('last_poll_at') or 'never'}")
    print(f"{'Last event':15s}: {state.get('last_event_at') or 'never'}")
    return 0


def cmd_tick(args: argparse.Namespace) -> int:
    """Run one poll cycle against the mock client and print the result."""
    from .models import GmailConfig
    from .client import MockGmailClient
    from .watcher import GmailWatcher
    from ..base.dispatcher import EventDispatcher

    config = GmailConfig(
        account_email=args.account,
        vault_root=args.vault,
    )
    client  = MockGmailClient()
    watcher = GmailWatcher(config, client)
    watcher.start()

    dispatcher = EventDispatcher()
    result = watcher.tick(dispatcher)

    print(f"\nTick result for '{config.watcher_id}':")
    print(f"  health_ok:         {result.health_ok}")
    print(f"  events_found:      {result.events_found}")
    print(f"  events_dispatched: {result.events_dispatched}")
    print(f"  errors:            {result.errors}")
    print(f"  duration_ms:       {result.duration_ms:.1f}")
    if result.error_message:
        print(f"  error:             {_c(result.error_message, _RED)}")
    return 0


def cmd_events(args: argparse.Namespace) -> int:
    """Show stored events for the Gmail watcher."""
    from ..base.store import EventStore

    vault   = Path(args.vault)
    account = args.account
    safe_id = account.replace("@", "_at_").replace(".", "_")
    wid     = f"gmail-{safe_id}"

    store  = EventStore(vault)
    date   = args.date or None
    events = store.load_by_date(wid, date)

    display_date = date or datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

    if not events:
        print(f"No events found for '{wid}' on {display_date}.")
        return 0

    print(f"\n{len(events)} event(s) for '{wid}' on {display_date}:\n")
    print(f"{'Event ID':15s} {'Type':30s} {'Done':6s} {'Time'}")
    print("-" * 70)
    for e in events:
        ts   = e.timestamp.strftime("%H:%M:%S")
        done = _c("yes", _GREEN) if e.processed else _c("no", _YELLOW)
        subj = e.payload.get("subject", "")[:30]
        print(f"{e.event_id:15s} {e.event_type:30s} {done:16s} {ts}  {subj}")
    return 0


def cmd_inject(args: argparse.Namespace) -> int:
    """Inject a mock message and immediately tick the watcher."""
    from .models import GmailConfig, make_gmail_message
    from .client import MockGmailClient
    from .watcher import GmailWatcher
    from ..base.dispatcher import EventDispatcher

    config  = GmailConfig(account_email=args.account, vault_root=args.vault)
    client  = MockGmailClient()
    msg     = make_gmail_message(
        subject=args.subject,
        sender=args.sender,
        snippet=args.snippet or "",
    )
    client.inject_message(msg)

    watcher = GmailWatcher(config, client)
    watcher.start()

    result = watcher.tick(EventDispatcher())
    print(f"Injected message '{args.subject}' from '{args.sender}'.")
    print(f"Events found: {result.events_found}, dispatched: {result.events_dispatched}")
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gmail-watcher",
        description="GMAIL_WATCHER_SKILL CLI",
    )
    parser.add_argument("--vault",   required=True, help="Path to Obsidian vault root")
    parser.add_argument("--account", required=True, help="Gmail account email address")

    sub = parser.add_subparsers(dest="command", required=True)

    # status
    p = sub.add_parser("status", help="Show watcher status")
    p.set_defaults(func=cmd_status)

    # tick
    p = sub.add_parser("tick", help="Run one poll cycle (mock client)")
    p.set_defaults(func=cmd_tick)

    # events
    p = sub.add_parser("events", help="Show stored events")
    p.add_argument("--date", default=None, help="Date YYYY-MM-DD (default: today)")
    p.set_defaults(func=cmd_events)

    # inject
    p = sub.add_parser("inject", help="Inject a mock message and tick")
    p.add_argument("--subject", required=True, help="Message subject")
    p.add_argument("--sender",  required=True, help="Sender email")
    p.add_argument("--snippet", default="",   help="Optional message preview")
    p.set_defaults(func=cmd_inject)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args   = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
