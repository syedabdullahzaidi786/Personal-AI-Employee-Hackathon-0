"""
CEO Weekly Audit Runner
=======================
Reads all skill logs from the Obsidian vault and generates a professional
CEO Briefing report — saved to 50-BUSINESS/weekly/ inside the vault.

Usage:
    python run_ceo_audit.py                  # current week
    python run_ceo_audit.py --week -1        # last week
    python run_ceo_audit.py --print          # show full report in terminal
    python run_ceo_audit.py --week -1 --print
"""

import sys
import os
import time
import argparse

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

VAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "obsidian-vault")

# ── Colours ─────────────────────────────────────────────────────────────────

_GREEN  = "\033[92m"
_RED    = "\033[91m"
_YELLOW = "\033[93m"
_CYAN   = "\033[96m"
_RESET  = "\033[0m"


def _c(text: str, colour: str) -> str:
    return f"{colour}{text}{_RESET}"


def _health_display(health: str) -> str:
    mapping = {
        "HEALTHY":  ("✅", _GREEN),
        "DEGRADED": ("⚠️ ", _YELLOW),
        "CRITICAL": ("🔴", _RED),
        "UNKNOWN":  ("❓", _CYAN),
    }
    emoji, colour = mapping.get(health, ("❓", _CYAN))
    return f"{emoji}  {_c(health, colour)}"


# ── Helpers ──────────────────────────────────────────────────────────────────

def ticker(msg: str, delay: float = 0.03):
    for ch in msg:
        print(ch, end="", flush=True)
        time.sleep(delay)
    print()


def step_header(title: str):
    print()
    print("┌" + "─" * 60 + "┐")
    print(f"│  {title:<58}│")
    print("└" + "─" * 60 + "┘")


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="CEO Weekly Audit — Gold Tier Business Intelligence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--week", type=int, default=0,
        help="Week offset: 0=current week (default), -1=last week"
    )
    parser.add_argument(
        "--print", dest="print_report", action="store_true",
        help="Print the full Markdown report to terminal after saving"
    )
    args = parser.parse_args()

    # ── Header ───────────────────────────────────────────────────────────────
    print()
    print("╔" + "═" * 60 + "╗")
    print("║   CEO Weekly Audit — Personal AI Employee                 ║")
    print("║   Gold Tier: Business Intelligence & KPI Briefing         ║")
    print("╚" + "═" * 60 + "╝")

    week_label = "Current Week" if args.week == 0 else f"Week Offset: {args.week}"
    step_header(f"📊 GENERATING REPORT — {week_label}")

    # ── Import & Run ─────────────────────────────────────────────────────────
    try:
        from platinum_tier_business_layer.ceo_audit import CeoAuditSkill
    except ImportError as e:
        print(f"\n   ❌ Import failed: {e}")
        print("   💡 Make sure you are running from the project root directory.")
        sys.exit(1)

    ticker("   📂 Vault logs scan ho rahe hain...")
    skill = CeoAuditSkill(vault_root=VAULT)

    ticker("   📈 KPIs aggregate ho rahe hain...")
    report, paths = skill.generate_and_save(week_offset=args.week)

    # ── Report Summary ───────────────────────────────────────────────────────
    p = report.period
    h = report.hitl
    o = report.orchestrator

    print()
    print("╔" + "═" * 60 + "╗")
    print("║   CEO BRIEFING — EXECUTIVE SUMMARY                        ║")
    print("╚" + "═" * 60 + "╝")
    print()
    print(f"   Report Period : {p.start_date}  →  {p.end_date}")
    print(f"   Report ID     : {p.slug}")
    print(f"   Overall Health: {_health_display(report.overall_health)}")
    print()

    # HITL
    ar = f"{h.approval_rate:.1%}" if h.approval_rate is not None else "N/A"
    step_header("🤝 HITL APPROVALS")
    print(f"   Submitted     : {h.submitted}")
    print(f"   Approved      : {h.approved}  (human)   Auto-Approved: {h.auto_approved}")
    print(f"   Denied        : {h.denied}   Deferred: {h.deferred}   Timeout: {h.timeout}")
    print(f"   Pending       : {h.pending}")
    print(f"   Approval Rate : {_c(ar, _GREEN)}")

    # Orchestrator
    sr = f"{o.success_rate:.1%}" if o.success_rate is not None else "N/A"
    step_header("⚙️  ORCHESTRATOR ACTIVITY")
    print(f"   Workflow Runs : {o.runs_total}  (Success: {o.runs_success}  Failed: {o.runs_failed})")
    print(f"   Steps         : {o.steps_total}  (Failed: {o.steps_failed}  Skipped: {o.steps_skipped})")
    print(f"   HITL Gates    : {o.hitl_gates}")
    print(f"   Success Rate  : {_c(sr, _GREEN)}")

    # Watchers
    if report.watchers:
        step_header("👁️  WATCHERS")
        for w in report.watchers:
            print(f"   {w.watcher_id:<30} events={w.events}  polls={w.polls}  errors={w.errors}")

    # Action Skills
    if report.actions:
        step_header("🚀 ACTION SKILLS")
        for a in report.actions:
            asr = f"{a.success_rate:.1%}" if a.success_rate is not None else "N/A"
            print(
                f"   {a.skill_name:<12} "
                f"submitted={a.submitted}  success={a.success}  "
                f"failed={a.failed}  denied={a.denied}  "
                f"success_rate={_c(asr, _GREEN)}"
            )

    # ── Saved Path ────────────────────────────────────────────────────────────
    print()
    print("╔" + "═" * 60 + "╗")
    print("║   Report Saved!                                           ║")
    print("╚" + "═" * 60 + "╝")
    print()
    print(f"   📄 Markdown  : {paths.get('markdown', 'N/A')}")
    print()
    print("   ✅ CEO Briefing complete — report vault mein save ho gaya.")
    print()

    # ── Optional full print ───────────────────────────────────────────────────
    if args.print_report:
        from platinum_tier_business_layer.ceo_audit import ReportGenerator
        print("=" * 80)
        print(ReportGenerator().to_markdown(report))
        print("=" * 80)


if __name__ == "__main__":
    main()
