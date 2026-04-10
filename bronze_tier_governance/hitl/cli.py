"""
HUMAN_IN_THE_LOOP_APPROVAL_SKILL — CLI Interface
Phase 1: list, view, approve, deny, defer, batch-approve.

Usage:
    python -m skills.safety.hitl.cli --vault <path> list
    python -m skills.safety.hitl.cli --vault <path> view REQ-xxx
    python -m skills.safety.hitl.cli --vault <path> approve REQ-xxx --operator alice --comment "OK"
    python -m skills.safety.hitl.cli --vault <path> deny REQ-xxx --operator alice --reason "Not needed"
    python -m skills.safety.hitl.cli --vault <path> defer REQ-xxx --operator alice --extend 3600
    python -m skills.safety.hitl.cli --vault <path> batch-approve --operator alice --tier 1
    python -m skills.safety.hitl.cli --vault <path> submit ...
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from .approver import HITLApprover
from .audit import HITLAuditLogger
from .models import Decision, make_request
from .store import RequestStore
from .validator import DecisionError, ValidationError


# ---------------------------------------------------------------------------
# ANSI colours (safe — falls back gracefully on non-TTY)
# ---------------------------------------------------------------------------

def _c(code: str, text: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"

GREEN  = lambda t: _c("32", t)
RED    = lambda t: _c("31", t)
YELLOW = lambda t: _c("33", t)
BOLD   = lambda t: _c("1",  t)
DIM    = lambda t: _c("2",  t)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tier_label(tier: int) -> str:
    labels = {0: "Read-Only", 1: "Low-Risk", 2: "Medium-Risk", 3: "High-Risk", 4: "CRITICAL"}
    return labels.get(tier, str(tier))


def _status_colored(status: str) -> str:
    if status in (Decision.APPROVED, Decision.AUTO):
        return GREEN(status)
    if status == Decision.DENIED:
        return RED(status)
    if status == Decision.PENDING:
        return YELLOW(status)
    return status


def _remaining(request) -> str:
    secs = request.sla.remaining_seconds()
    if secs is None:
        return "N/A"
    m, s = divmod(int(secs), 60)
    h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s"


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_list(approver: HITLApprover, args: argparse.Namespace) -> int:
    requests = approver.list_pending(
        agent_id=getattr(args, "agent", None),
        tier=getattr(args, "tier", None),
    )
    if not requests:
        print("No pending requests.")
        return 0

    print(BOLD(f"\nPending Approvals ({len(requests)}):\n"))
    fmt = "{:<44} {:<20} {:<20} {:<6} {:<15}"
    print(DIM(fmt.format("ID", "Agent", "Operation", "Tier", "SLA Remaining")))
    print(DIM("-" * 110))
    for req in requests:
        print(fmt.format(
            req.request_id[:44],
            req.agent_id[:20],
            req.operation[:20],
            req.tier,
            _remaining(req),
        ))
    print()
    return 0


def cmd_view(approver: HITLApprover, args: argparse.Namespace) -> int:
    req = approver.get_request(args.request_id)
    if req is None:
        print(RED(f"Request not found: {args.request_id}"))
        return 1

    box_width = 60
    border = "─" * box_width
    print(f"\n┌{border}┐")
    print(f"│ {BOLD(f'Approval Request: {req.request_id[:40]}')}".ljust(box_width + 20) + "│")
    print(f"│ Tier {req.tier} ({_tier_label(req.tier)}) — Status: {_status_colored(req.status)}".ljust(box_width + 20) + "│")
    print(f"├{border}┤")
    print(f"│ Agent     : {req.agent_id[:46]}".ljust(box_width + 2) + "│")
    print(f"│ Operation : {req.operation[:46]}".ljust(box_width + 2) + "│")
    print(f"│ Submitted : {req.submitted_at.strftime('%Y-%m-%d %H:%M:%S UTC')[:46]}".ljust(box_width + 2) + "│")
    print(f"├{border}┤")
    print(f"│ {BOLD('Action:')}".ljust(box_width + 10) + "│")
    print(f"│   {req.action_summary[:55]}".ljust(box_width + 2) + "│")
    print(f"│ {BOLD('Reason:')}".ljust(box_width + 10) + "│")
    print(f"│   {req.reason[:55]}".ljust(box_width + 2) + "│")

    if req.risk:
        print(f"├{border}┤")
        print(f"│ {BOLD('Risk Assessment:')}".ljust(box_width + 10) + "│")
        for k, v in req.risk.items():
            print(f"│   {k}: {str(v)[:50]}".ljust(box_width + 2) + "│")

    if req.details:
        print(f"├{border}┤")
        print(f"│ {BOLD('Details:')}".ljust(box_width + 10) + "│")
        for k, v in req.details.items():
            print(f"│   {k}: {str(v)[:50]}".ljust(box_width + 2) + "│")

    print(f"├{border}┤")
    print(f"│ {BOLD('SLA:')}".ljust(box_width + 10) + "│")
    rb = req.sla.required_by
    print(f"│   Deadline: {rb.strftime('%Y-%m-%d %H:%M UTC') if rb else 'None'}".ljust(box_width + 2) + "│")
    print(f"│   Remaining: {_remaining(req)}".ljust(box_width + 2) + "│")

    if req.decision:
        d = req.decision
        print(f"├{border}┤")
        print(f"│ {BOLD('Decision:')} {_status_colored(d.action)}".ljust(box_width + 20) + "│")
        print(f"│   By     : {d.decided_by[:46]}".ljust(box_width + 2) + "│")
        print(f"│   At     : {d.decided_at.strftime('%Y-%m-%d %H:%M:%S UTC')[:46]}".ljust(box_width + 2) + "│")
        if d.reason:
            print(f"│   Reason : {d.reason[:46]}".ljust(box_width + 2) + "│")
        if d.comment:
            print(f"│   Comment: {d.comment[:46]}".ljust(box_width + 2) + "│")

    if req.is_pending:
        print(f"├{border}┤")
        print(f"│ {BOLD('Options:')}".ljust(box_width + 10) + "│")
        for opt in req.options:
            print(f"│   • {opt}".ljust(box_width + 2) + "│")
    print(f"└{border}┘\n")
    return 0


def cmd_approve(approver: HITLApprover, args: argparse.Namespace) -> int:
    try:
        decision = approver.approve(
            request_id=args.request_id,
            operator=args.operator,
            comment=getattr(args, "comment", ""),
        )
        print(GREEN(f"\n✅ Approved: {args.request_id}"))
        print(f"   By     : {decision.decided_by}")
        print(f"   At     : {decision.decided_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if decision.comment:
            print(f"   Comment: {decision.comment}")
        print()
        return 0
    except (DecisionError, ValidationError) as exc:
        print(RED(f"\n❌ Error: {exc}\n"))
        return 1


def cmd_deny(approver: HITLApprover, args: argparse.Namespace) -> int:
    try:
        decision = approver.deny(
            request_id=args.request_id,
            operator=args.operator,
            reason=getattr(args, "reason", ""),
            comment=getattr(args, "comment", ""),
        )
        print(RED(f"\n❌ Denied: {args.request_id}"))
        print(f"   By    : {decision.decided_by}")
        print(f"   At    : {decision.decided_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if decision.reason:
            print(f"   Reason: {decision.reason}")
        print()
        return 0
    except (DecisionError, ValidationError) as exc:
        print(RED(f"\n❌ Error: {exc}\n"))
        return 1


def cmd_defer(approver: HITLApprover, args: argparse.Namespace) -> int:
    try:
        req = approver.defer(
            request_id=args.request_id,
            operator=args.operator,
            extend_seconds=getattr(args, "extend", 3600),
            comment=getattr(args, "comment", ""),
        )
        print(YELLOW(f"\n⏳ Deferred: {args.request_id}"))
        rb = req.sla.required_by
        print(f"   New deadline: {rb.strftime('%Y-%m-%d %H:%M UTC') if rb else 'N/A'}")
        print()
        return 0
    except (DecisionError, ValidationError) as exc:
        print(RED(f"\n❌ Error: {exc}\n"))
        return 1


def cmd_batch_approve(approver: HITLApprover, args: argparse.Namespace) -> int:
    pending = approver.list_pending(
        agent_id=getattr(args, "agent", None),
        tier=getattr(args, "tier", None),
    )
    if not pending:
        print("No matching pending requests.")
        return 0

    approved = 0
    errors = 0
    for req in pending:
        try:
            approver.approve(
                request_id=req.request_id,
                operator=args.operator,
                comment=getattr(args, "comment", "Batch approval"),
            )
            print(GREEN(f"  ✅ {req.request_id} — {req.operation}"))
            approved += 1
        except (DecisionError, ValidationError) as exc:
            print(RED(f"  ❌ {req.request_id} — {exc}"))
            errors += 1

    print(f"\nBatch Summary: {approved} approved, {errors} errors\n")
    return 0 if errors == 0 else 1


def cmd_submit(approver: HITLApprover, args: argparse.Namespace) -> int:
    """Submit a new approval request from the CLI (mainly for testing)."""
    details = {}
    if getattr(args, "details", None):
        try:
            details = json.loads(args.details)
        except json.JSONDecodeError:
            print(RED("--details must be valid JSON"))
            return 1

    risk = {}
    if getattr(args, "blast_radius", None):
        risk["blast_radius"] = args.blast_radius
    if getattr(args, "reversibility", None):
        risk["reversibility"] = args.reversibility

    try:
        req = make_request(
            agent_id=args.agent_id,
            operation=args.operation,
            tier=args.tier,
            action_summary=args.action,
            reason=args.reason,
            details=details,
            risk=risk if risk else None,
            sla_override_seconds=getattr(args, "sla_override", None),
        )
        result = approver.submit(req)
        print(GREEN(f"\n✅ Request submitted: {result.request_id}"))
        print(f"   Tier  : {result.tier} ({_tier_label(result.tier)})")
        print(f"   Status: {_status_colored(result.status)}")
        rb = result.sla.required_by
        print(f"   SLA   : {rb.strftime('%Y-%m-%d %H:%M UTC') if rb else 'N/A'}")
        print()
        return 0
    except ValidationError as exc:
        print(RED(f"\n❌ Validation error: {exc}\n"))
        return 1


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="hitl",
        description="HUMAN_IN_THE_LOOP_APPROVAL_SKILL CLI v1.0.0",
    )
    p.add_argument("--vault", required=True, help="Path to obsidian-vault root")

    sub = p.add_subparsers(dest="command", required=True)

    # list
    sl = sub.add_parser("list", help="List pending requests")
    sl.add_argument("--agent", help="Filter by agent ID")
    sl.add_argument("--tier", type=int, help="Filter by tier")

    # view
    sv = sub.add_parser("view", help="View request details")
    sv.add_argument("request_id")

    # approve
    sa = sub.add_parser("approve", help="Approve a request")
    sa.add_argument("request_id")
    sa.add_argument("--operator", required=True)
    sa.add_argument("--comment", default="")

    # deny
    sd = sub.add_parser("deny", help="Deny a request")
    sd.add_argument("request_id")
    sd.add_argument("--operator", required=True)
    sd.add_argument("--reason", default="")
    sd.add_argument("--comment", default="")

    # defer
    sdf = sub.add_parser("defer", help="Defer a request (extend SLA)")
    sdf.add_argument("request_id")
    sdf.add_argument("--operator", required=True)
    sdf.add_argument("--extend", type=int, default=3600, help="Extension in seconds")
    sdf.add_argument("--comment", default="")

    # batch-approve
    sb = sub.add_parser("batch-approve", help="Approve multiple requests")
    sb.add_argument("--operator", required=True)
    sb.add_argument("--agent", help="Filter by agent ID")
    sb.add_argument("--tier", type=int, help="Filter by tier")
    sb.add_argument("--comment", default="Batch approval")

    # submit (for testing / agent simulation)
    ss = sub.add_parser("submit", help="Submit a new approval request")
    ss.add_argument("--agent-id", required=True)
    ss.add_argument("--operation", required=True)
    ss.add_argument("--tier", type=int, required=True)
    ss.add_argument("--action", required=True, dest="action")
    ss.add_argument("--reason", required=True)
    ss.add_argument("--details", default="{}", help="JSON string of operation details")
    ss.add_argument("--blast-radius", default="")
    ss.add_argument("--reversibility", default="")
    ss.add_argument("--sla-override", type=int, default=None, help="Override SLA in seconds")

    return p


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    vault = Path(args.vault)
    store  = RequestStore(vault)
    audit  = HITLAuditLogger(vault)
    approver = HITLApprover(store=store, audit=audit)

    # Check expired SLAs on every invocation
    approver.check_and_timeout_expired()

    commands = {
        "list":         cmd_list,
        "view":         cmd_view,
        "approve":      cmd_approve,
        "deny":         cmd_deny,
        "defer":        cmd_defer,
        "batch-approve": cmd_batch_approve,
        "submit":       cmd_submit,
    }
    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    return handler(approver, args)


if __name__ == "__main__":
    sys.exit(main())
