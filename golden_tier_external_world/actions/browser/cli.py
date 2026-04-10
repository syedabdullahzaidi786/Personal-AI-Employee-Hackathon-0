"""
BROWSER_MCP_SKILL — CLI
Commands: open, extract, status, logs

Usage::

    python -m skills.actions.browser.cli --vault /vault open --url https://example.com
    python -m skills.actions.browser.cli --vault /vault extract --url https://example.com --selector h1
    python -m skills.actions.browser.cli --vault /vault status
    python -m skills.actions.browser.cli --vault /vault logs [--date YYYY-MM-DD]
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
        "SUCCESS":          _c(status, _GREEN),
        "PENDING_APPROVAL": _c(status, _YELLOW),
        "APPROVED":         _c(status, _CYAN),
        "DENIED":           _c(status, _RED),
        "FAILED":           _c(status, _RED),
    }.get(status, status)


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def cmd_open(args: argparse.Namespace) -> int:
    """Open a URL with the mock browser adapter and print the result."""
    from .models import BrowserConfig
    from .adapter import MockBrowserAdapter
    from . import BrowserSkill

    config = BrowserConfig(vault_root=args.vault, default_tier=args.tier)
    skill  = BrowserSkill(config, adapter=MockBrowserAdapter())
    result = skill.open_url(args.url)

    print(f"\nBrowser open_url Result:")
    print(f"  request_id  : {result.request_id}")
    print(f"  status      : {_status_colour(result.status)}")
    print(f"  url         : {result.url}")
    print(f"  status_code : {result.status_code}")
    if result.content:
        print(f"  content     : {result.content[:120]}")
    if result.hitl_request_id:
        print(f"  hitl_req    : {result.hitl_request_id}")
    if result.error:
        print(f"  error       : {_c(result.error, _RED)}")
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    """Extract text from a URL with the mock browser adapter."""
    from .models import BrowserConfig
    from .adapter import MockBrowserAdapter
    from . import BrowserSkill

    config = BrowserConfig(vault_root=args.vault, default_tier=args.tier)
    skill  = BrowserSkill(config, adapter=MockBrowserAdapter())
    result = skill.extract_text(args.url, selector=args.selector or "")

    print(f"\nBrowser extract_text Result:")
    print(f"  request_id  : {result.request_id}")
    print(f"  status      : {_status_colour(result.status)}")
    print(f"  url         : {result.url}")
    print(f"  status_code : {result.status_code}")
    if args.selector:
        print(f"  selector    : {args.selector}")
    if result.content:
        print(f"  content     : {result.content[:200]}")
    if result.hitl_request_id:
        print(f"  hitl_req    : {result.hitl_request_id}")
    if result.error:
        print(f"  error       : {_c(result.error, _RED)}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Show adapter health status."""
    from .adapter import MockBrowserAdapter

    adapter = MockBrowserAdapter()
    healthy = adapter.health_check()
    colour  = _GREEN if healthy else _RED
    label   = "healthy" if healthy else "unhealthy"

    print(f"\nBrowser Adapter Status:")
    print(f"  health   : {_c(label, colour)}")
    print(f"  adapter  : MockBrowserAdapter (Phase 1 — no real browser)")
    print(f"  actions  : open_url, extract_text")
    print(f"  vault    : {args.vault}")
    return 0 if healthy else 1


def cmd_logs(args: argparse.Namespace) -> int:
    """Show browser action log entries."""
    from .logger import BrowserLogger

    logger  = BrowserLogger(args.vault)
    entries = logger.read_entries(args.date)

    display_date = args.date or "today"
    if not entries:
        print(f"No browser logs found for {display_date}.")
        return 0

    print(f"\n{len(entries)} log entry/entries for {display_date}:\n")
    print(f"{'Event':22s} {'Request ID':18s} {'Action':15s} {'Status':20s} {'Time'}")
    print("-" * 92)
    for e in entries:
        event  = e.get("event", "?")
        rid    = e.get("request_id", "?")
        action = e.get("action", "?")[:14]
        status = e.get("status", e.get("reason", e.get("error", "")))[:18]
        ts     = e.get("ts", "")[:19]
        print(f"{event:22s} {rid:18s} {action:15s} {_status_colour(status):30s} {ts}")
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="browser-skill",
        description="BROWSER_MCP_SKILL CLI",
    )
    parser.add_argument("--vault", required=True, help="Path to Obsidian vault root")

    sub = parser.add_subparsers(dest="command", required=True)

    # open
    p = sub.add_parser("open", help="Open a URL (mock browser)")
    p.add_argument("--url",  required=True, help="URL to open")
    p.add_argument("--tier", type=int, default=2, help="HITL tier (default: 2)")
    p.set_defaults(func=cmd_open)

    # extract
    p = sub.add_parser("extract", help="Extract text from a URL (mock browser)")
    p.add_argument("--url",      required=True, help="URL to extract from")
    p.add_argument("--selector", default="",    help="CSS/XPath selector (optional)")
    p.add_argument("--tier",     type=int, default=2, help="HITL tier (default: 2)")
    p.set_defaults(func=cmd_extract)

    # status
    p = sub.add_parser("status", help="Show adapter health status")
    p.set_defaults(func=cmd_status)

    # logs
    p = sub.add_parser("logs", help="Show browser action logs")
    p.add_argument("--date", default=None, help="Date YYYY-MM-DD (default: today)")
    p.set_defaults(func=cmd_logs)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args   = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
