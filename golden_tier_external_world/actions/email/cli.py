"""
EMAIL_MCP_ACTION_SKILL — CLI
Commands: send, status, logs

Usage::

    python -m skills.actions.email.cli --vault /vault --sender agent@company.com send \
        --to alice@example.com --subject "Hello" --body "Hi!"
    python -m skills.actions.email.cli --vault /vault --sender agent@company.com status
    python -m skills.actions.email.cli --vault /vault --sender agent@company.com logs [--date YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
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
        "SENT":             _c(status, _GREEN),
        "PENDING_APPROVAL": _c(status, _YELLOW),
        "APPROVED":         _c(status, _CYAN),
        "DENIED":           _c(status, _RED),
        "FAILED":           _c(status, _RED),
    }.get(status, status)


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def cmd_send(args: argparse.Namespace) -> int:
    """Submit a mock email send request and print the result."""
    from .models import EmailConfig
    from .adapter import MockEmailAdapter
    from . import EmailActionSkill

    config  = EmailConfig(
        sender_address=args.sender,
        vault_root=args.vault,
        default_tier=args.tier,
    )
    skill  = EmailActionSkill(config, adapter=MockEmailAdapter())
    to_list = [t.strip() for t in args.to.split(",") if t.strip()]
    result  = skill.send(
        to=to_list,
        subject=args.subject,
        body=args.body,
    )

    print(f"\nEmail Action Result:")
    print(f"  request_id : {result.request_id}")
    print(f"  status     : {_status_colour(result.status)}")
    if result.sent_at:
        print(f"  sent_at    : {result.sent_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    if result.hitl_request_id:
        print(f"  hitl_req   : {result.hitl_request_id}")
    if result.error:
        print(f"  error      : {_c(result.error, _RED)}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Show adapter health status."""
    from .adapter import MockEmailAdapter

    adapter = MockEmailAdapter()
    healthy = adapter.health_check()
    colour  = _GREEN if healthy else _RED
    label   = "healthy" if healthy else "unhealthy"

    print(f"\nEmail Adapter Status:")
    print(f"  health     : {_c(label, colour)}")
    print(f"  adapter    : MockEmailAdapter (Phase 1 — no real SMTP)")
    print(f"  vault      : {args.vault}")
    print(f"  sender     : {args.sender}")
    return 0 if healthy else 1


def cmd_logs(args: argparse.Namespace) -> int:
    """Show email action log entries."""
    from .logger import EmailActionLogger

    logger  = EmailActionLogger(args.vault)
    entries = logger.read_entries(args.date)

    display_date = args.date or "today"
    if not entries:
        print(f"No email logs found for {display_date}.")
        return 0

    print(f"\n{len(entries)} log entry/entries for {display_date}:\n")
    print(f"{'Event':25s} {'Request ID':18s} {'Status/Info':25s} {'Time'}")
    print("-" * 85)
    for e in entries:
        event  = e.get("event", "?")
        rid    = e.get("request_id", "?")
        status = e.get("status", e.get("reason", e.get("error", "")))[:24]
        ts     = e.get("ts", "")[:19]
        print(f"{event:25s} {rid:18s} {_status_colour(status):35s} {ts}")
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="email-action",
        description="EMAIL_MCP_ACTION_SKILL CLI",
    )
    parser.add_argument("--vault",  required=True, help="Path to Obsidian vault root")
    parser.add_argument("--sender", required=True, help="Sender email address")

    sub = parser.add_subparsers(dest="command", required=True)

    # send
    p = sub.add_parser("send", help="Submit a mock email send request")
    p.add_argument("--to",      required=True, help="Recipient(s), comma-separated")
    p.add_argument("--subject", required=True, help="Email subject")
    p.add_argument("--body",    default="",    help="Email body text")
    p.add_argument("--tier",    type=int, default=3, help="HITL tier (default: 3)")
    p.set_defaults(func=cmd_send)

    # status
    p = sub.add_parser("status", help="Show adapter health status")
    p.set_defaults(func=cmd_status)

    # logs
    p = sub.add_parser("logs", help="Show email action logs")
    p.add_argument("--date", default=None, help="Date YYYY-MM-DD (default: today)")
    p.set_defaults(func=cmd_logs)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args   = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
