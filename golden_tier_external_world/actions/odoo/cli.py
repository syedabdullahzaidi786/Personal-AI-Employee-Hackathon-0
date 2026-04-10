"""
ODOO_MCP_INTEGRATION_SKILL — CLI
Commands: create, update, fetch, status, logs

Usage::

    python -m skills.actions.odoo.cli --vault /vault create \\
        --model res.partner --data '{"name":"Alice","email":"alice@example.com"}'
    python -m skills.actions.odoo.cli --vault /vault update \\
        --model res.partner --id 1 --data '{"phone":"555-1234"}'
    python -m skills.actions.odoo.cli --vault /vault fetch \\
        --model res.partner --id 1
    python -m skills.actions.odoo.cli --vault /vault status
    python -m skills.actions.odoo.cli --vault /vault logs [--date YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import json
import sys
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
        "SUCCESS":          _c(status, _GREEN),
        "PENDING_APPROVAL": _c(status, _YELLOW),
        "APPROVED":         _c(status, _CYAN),
        "DENIED":           _c(status, _RED),
        "FAILED":           _c(status, _RED),
        "NOT_FOUND":        _c(status, _RED),
    }.get(status, status)


def _parse_data(raw: str) -> dict:
    """Parse a JSON string into a dict. Returns {} on error."""
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        print(_c(f"Invalid JSON for --data: {exc}", _RED), file=sys.stderr)
        return {}


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def cmd_create(args: argparse.Namespace) -> int:
    """Create a new Odoo record (mock)."""
    from .models import OdooConfig
    from .adapter import MockOdooAdapter
    from . import OdooSkill

    data   = _parse_data(args.data)
    config = OdooConfig(vault_root=args.vault, default_tier=args.tier)
    skill  = OdooSkill(config, adapter=MockOdooAdapter())
    result = skill.create_record(model=args.model, data=data)

    print(f"\nOdoo create_record Result:")
    print(f"  request_id : {result.request_id}")
    print(f"  status     : {_status_colour(result.status)}")
    print(f"  model      : {result.model}")
    print(f"  record_id  : {result.record_id}")
    if result.record_data:
        print(f"  data       : {json.dumps(result.record_data, indent=4)}")
    if result.hitl_request_id:
        print(f"  hitl_req   : {result.hitl_request_id}")
    if result.error:
        print(f"  error      : {_c(result.error, _RED)}")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    """Update an existing Odoo record (mock)."""
    from .models import OdooConfig
    from .adapter import MockOdooAdapter
    from . import OdooSkill

    data   = _parse_data(args.data)
    config = OdooConfig(vault_root=args.vault, default_tier=args.tier)
    skill  = OdooSkill(config, adapter=MockOdooAdapter())
    result = skill.update_record(model=args.model, record_id=args.id, data=data)

    print(f"\nOdoo update_record Result:")
    print(f"  request_id : {result.request_id}")
    print(f"  status     : {_status_colour(result.status)}")
    print(f"  model      : {result.model}")
    print(f"  record_id  : {result.record_id}")
    if result.record_data:
        print(f"  data       : {json.dumps(result.record_data, indent=4)}")
    if result.hitl_request_id:
        print(f"  hitl_req   : {result.hitl_request_id}")
    if result.error:
        print(f"  error      : {_c(result.error, _RED)}")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    """Fetch an Odoo record by ID (mock)."""
    from .models import OdooConfig
    from .adapter import MockOdooAdapter
    from . import OdooSkill

    config = OdooConfig(vault_root=args.vault)
    skill  = OdooSkill(config, adapter=MockOdooAdapter())
    result = skill.fetch_record(model=args.model, record_id=args.id)

    print(f"\nOdoo fetch_record Result:")
    print(f"  request_id : {result.request_id}")
    print(f"  status     : {_status_colour(result.status)}")
    print(f"  model      : {result.model}")
    print(f"  record_id  : {result.record_id}")
    if result.record_data:
        print(f"  data       : {json.dumps(result.record_data, indent=4)}")
    if result.error:
        print(f"  error      : {_c(result.error, _RED)}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Show adapter health status."""
    from .adapter import MockOdooAdapter

    adapter = MockOdooAdapter()
    healthy = adapter.health_check()
    colour  = _GREEN if healthy else _RED
    label   = "healthy" if healthy else "unhealthy"

    print(f"\nOdoo Adapter Status:")
    print(f"  health     : {_c(label, colour)}")
    print(f"  adapter    : MockOdooAdapter (Phase 1 — no real Odoo API)")
    print(f"  operations : create_record, update_record, fetch_record")
    print(f"  vault      : {args.vault}")
    return 0 if healthy else 1


def cmd_logs(args: argparse.Namespace) -> int:
    """Show Odoo integration log entries."""
    from .logger import OdooLogger

    logger  = OdooLogger(args.vault)
    entries = logger.read_entries(args.date)

    display_date = args.date or "today"
    if not entries:
        print(f"No Odoo logs found for {display_date}.")
        return 0

    print(f"\n{len(entries)} log entry/entries for {display_date}:\n")
    print(f"{'Event':22s} {'Request ID':18s} {'Operation':17s} {'Status':20s} {'Time'}")
    print("-" * 95)
    for e in entries:
        event     = e.get("event", "?")
        rid       = e.get("request_id", "?")
        operation = e.get("operation", "?")[:16]
        status    = e.get("status", e.get("reason", e.get("error", "")))[:18]
        ts        = e.get("ts", "")[:19]
        print(f"{event:22s} {rid:18s} {operation:17s} {_status_colour(status):30s} {ts}")
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="odoo-skill",
        description="ODOO_MCP_INTEGRATION_SKILL CLI",
    )
    parser.add_argument("--vault", required=True, help="Path to Obsidian vault root")

    sub = parser.add_subparsers(dest="command", required=True)

    # create
    p = sub.add_parser("create", help="Create a new Odoo record")
    p.add_argument("--model", required=True, help="Odoo model name (e.g. res.partner)")
    p.add_argument("--data",  default="{}", help="Record fields as JSON string")
    p.add_argument("--tier",  type=int, default=3, help="HITL tier (default: 3)")
    p.set_defaults(func=cmd_create)

    # update
    p = sub.add_parser("update", help="Update an existing Odoo record")
    p.add_argument("--model", required=True, help="Odoo model name")
    p.add_argument("--id",    required=True, type=int, help="Record ID to update")
    p.add_argument("--data",  default="{}", help="Fields to update as JSON string")
    p.add_argument("--tier",  type=int, default=3, help="HITL tier (default: 3)")
    p.set_defaults(func=cmd_update)

    # fetch
    p = sub.add_parser("fetch", help="Fetch an Odoo record by ID")
    p.add_argument("--model", required=True, help="Odoo model name")
    p.add_argument("--id",    required=True, type=int, help="Record ID to fetch")
    p.set_defaults(func=cmd_fetch)

    # status
    p = sub.add_parser("status", help="Show adapter health status")
    p.set_defaults(func=cmd_status)

    # logs
    p = sub.add_parser("logs", help="Show Odoo integration logs")
    p.add_argument("--date", default=None, help="Date YYYY-MM-DD (default: today)")
    p.set_defaults(func=cmd_logs)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args   = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
