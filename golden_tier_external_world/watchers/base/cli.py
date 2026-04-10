"""
BASE_WATCHER_CREATION_SKILL — CLI
Commands: list, status, events

Usage::

    python -m skills.watchers.base.cli --vault /path/to/vault list
    python -m skills.watchers.base.cli --vault /path/to/vault status --id <watcher_id>
    python -m skills.watchers.base.cli --vault /path/to/vault events --id <watcher_id>
    python -m skills.watchers.base.cli --vault /path/to/vault events --id <watcher_id> --date 2026-03-01
"""

from __future__ import annotations

import argparse
import json
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


def _read_state(vault: Path, watcher_id: str) -> Optional[dict]:
    """Read persisted watcher state from vault."""
    state_file = vault / "70-LOGS" / "watchers" / watcher_id / "state.json"
    if not state_file.exists():
        return None
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _list_watcher_ids(vault: Path) -> list[str]:
    """Discover watcher IDs from vault directory structure."""
    watcher_root = vault / "70-LOGS" / "watchers"
    if not watcher_root.exists():
        return []
    return sorted(
        d.name for d in watcher_root.iterdir()
        if d.is_dir() and (d / "state.json").exists()
    )


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def cmd_list(args: argparse.Namespace) -> int:
    """List all watchers discovered in vault."""
    vault = Path(args.vault)
    ids   = _list_watcher_ids(vault)

    if not ids:
        print("No watchers found in vault (no state.json files).")
        return 0

    print(f"{'Watcher ID':30s} {'Type':20s} {'Status':12s} {'Polls':8s} {'Events':8s}")
    print("-" * 82)
    for wid in ids:
        state = _read_state(vault, wid)
        if state is None:
            continue
        status = _status_colour(state.get("status", "unknown"))
        wtype  = state.get("watcher_type", "?") if "watcher_type" in state else "?"
        polls  = state.get("poll_count", 0)
        events = state.get("total_events", 0)
        print(f"{wid:30s} {wtype:20s} {status:22s} {polls:<8} {events:<8}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Show detailed status of a specific watcher."""
    vault = Path(args.vault)
    state = _read_state(vault, args.id)

    if state is None:
        print(_c(f"No state found for watcher '{args.id}'.", _RED))
        return 1

    print(f"\n{'Watcher':15s}: {state.get('watcher_id', args.id)}")
    print(f"{'Status':15s}: {_status_colour(state.get('status', '?'))}")
    print(f"{'Poll count':15s}: {state.get('poll_count', 0)}")
    print(f"{'Total events':15s}: {state.get('total_events', 0)}")
    print(f"{'Error count':15s}: {state.get('error_count', 0)}")
    print(f"{'Consec errors':15s}: {state.get('consecutive_errors', 0)}")
    print(f"{'Last poll':15s}: {state.get('last_poll_at') or 'never'}")
    print(f"{'Last event':15s}: {state.get('last_event_at') or 'never'}")
    print(f"{'Started at':15s}: {state.get('started_at') or 'not started'}")
    return 0


def cmd_events(args: argparse.Namespace) -> int:
    """Show events for a specific watcher."""
    from .store import EventStore

    vault = Path(args.vault)
    store = EventStore(vault)
    date  = args.date or None
    events = store.load_by_date(args.id, date)

    display_date = date or datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

    if not events:
        print(f"No events found for watcher '{args.id}' on {display_date}.")
        return 0

    print(f"\n{len(events)} event(s) for '{args.id}' on {display_date}:\n")
    print(f"{'Event ID':15s} {'Type':22s} {'Source':25s} {'Tier':6s} {'Done':6s} {'Time'}")
    print("-" * 95)
    for e in events:
        ts   = e.timestamp.strftime("%H:%M:%S")
        done = _c("yes", _GREEN) if e.processed else _c("no", _YELLOW)
        print(f"{e.event_id:15s} {e.event_type:22s} {e.source:25s} {e.tier:<6} {done:16s} {ts}")
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="watcher",
        description="BASE_WATCHER_CREATION_SKILL CLI",
    )
    parser.add_argument("--vault", required=True, help="Path to Obsidian vault root")

    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p = sub.add_parser("list", help="List all registered watchers in vault")
    p.set_defaults(func=cmd_list)

    # status
    p = sub.add_parser("status", help="Show detailed status for a watcher")
    p.add_argument("--id", required=True, help="Watcher ID")
    p.set_defaults(func=cmd_status)

    # events
    p = sub.add_parser("events", help="Show events for a watcher")
    p.add_argument("--id",   required=True,  help="Watcher ID")
    p.add_argument("--date", default=None,   help="Date YYYY-MM-DD (default: today)")
    p.set_defaults(func=cmd_events)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args   = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
