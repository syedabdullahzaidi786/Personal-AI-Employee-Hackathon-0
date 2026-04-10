"""
CEO_WEEKLY_AUDIT_SKILL — CLI
Command: generate-weekly-report

Usage::

    python -m skills.business.ceo_audit.cli --vault /vault generate-weekly-report
    python -m skills.business.ceo_audit.cli --vault /vault generate-weekly-report --week -1
    python -m skills.business.ceo_audit.cli --vault /vault generate-weekly-report --print-report
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


def _health_colour(health: str) -> str:
    return {
        "HEALTHY":  _c(health, _GREEN),
        "DEGRADED": _c(health, _YELLOW),
        "CRITICAL": _c(health, _RED),
        "UNKNOWN":  _c(health, _CYAN),
    }.get(health, health)


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def cmd_generate(args: argparse.Namespace) -> int:
    """Generate and save the CEO weekly audit report."""
    from . import CeoAuditSkill

    skill = CeoAuditSkill(vault_root=args.vault)
    report, paths = skill.generate_and_save(week_offset=args.week)

    p = report.period
    h = report.hitl
    o = report.orchestrator

    print(f"\nCEO Weekly Report — {p.label}")
    print(f"  Period    : {p.start_date} → {p.end_date}")
    print(f"  Health    : {_health_colour(report.overall_health)}")
    print()

    # HITL
    ar = f"{h.approval_rate:.1%}" if h.approval_rate is not None else "N/A"
    print("  HITL Approvals:")
    print(f"    submitted     : {h.submitted}")
    print(f"    approved      : {h.approved}  auto: {h.auto_approved}  "
          f"denied: {h.denied}  pending: {h.pending}")
    print(f"    approval_rate : {ar}")
    print()

    # Orchestrator
    sr = f"{o.success_rate:.1%}" if o.success_rate is not None else "N/A"
    print("  Orchestrator:")
    print(f"    runs          : {o.runs_total}  "
          f"success: {o.runs_success}  failed: {o.runs_failed}")
    print(f"    steps         : {o.steps_total}  failed: {o.steps_failed}  "
          f"skipped: {o.steps_skipped}")
    print(f"    hitl_gates    : {o.hitl_gates}")
    print(f"    success_rate  : {sr}")
    print()

    # Watchers
    if report.watchers:
        print("  Watchers:")
        for w in report.watchers:
            print(f"    {w.watcher_id}: events={w.events} polls={w.polls} errors={w.errors}")
        print()

    # Actions
    if report.actions:
        print("  Action Skills:")
        for a in report.actions:
            asr = f"{a.success_rate:.1%}" if a.success_rate is not None else "N/A"
            print(f"    {a.skill_name}: submitted={a.submitted} success={a.success} "
                  f"failed={a.failed} denied={a.denied}  success_rate={asr}")
        print()

    print(f"  Saved to  : {paths.get('markdown', 'N/A')}")

    if args.print_report:
        from . import ReportGenerator
        print()
        print("=" * 80)
        print(ReportGenerator().to_markdown(report))

    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ceo-audit",
        description="CEO_WEEKLY_AUDIT_SKILL CLI",
    )
    parser.add_argument("--vault", required=True, help="Path to Obsidian vault root")

    sub = parser.add_subparsers(dest="command", required=True)

    # generate-weekly-report
    p = sub.add_parser(
        "generate-weekly-report",
        help="Generate and save the CEO weekly audit report",
    )
    p.add_argument(
        "--week", type=int, default=0,
        help="Week offset: 0=current, -1=last week (default: 0)",
    )
    p.add_argument(
        "--print-report", action="store_true",
        help="Also print the full Markdown report to stdout",
    )
    p.set_defaults(func=cmd_generate)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args   = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
