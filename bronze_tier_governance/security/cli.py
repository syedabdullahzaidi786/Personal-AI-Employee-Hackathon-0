"""
SECURITY_AND_CREDENTIAL_MANAGEMENT_SKILL — CLI
Commands: verify, scan-vault, rotate-reminder, list-credentials, audit

Usage::

    python -m skills.safety.security.cli --vault /path/to/vault verify
    python -m skills.safety.security.cli --vault /path/to/vault scan-vault
    python -m skills.safety.security.cli --vault /path/to/vault list-credentials
    python -m skills.safety.security.cli --vault /path/to/vault rotate-reminder
    python -m skills.safety.security.cli --vault /path/to/vault audit
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional

# ANSI colours
_GREEN  = "\033[92m"
_RED    = "\033[91m"
_YELLOW = "\033[93m"
_CYAN   = "\033[96m"
_RESET  = "\033[0m"


def _c(text: str, colour: str) -> str:
    return f"{colour}{text}{_RESET}"


def _severity_colour(s: str) -> str:
    return {
        "critical": _c(s, _RED),
        "high":     _c(s, _RED),
        "medium":   _c(s, _YELLOW),
        "info":     s,
    }.get(s.lower(), s)


def _build_skill(args: argparse.Namespace):
    from . import SecuritySkill
    return SecuritySkill(vault_root=args.vault)


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def cmd_verify(args: argparse.Namespace) -> int:
    """Check that required credentials are set in the environment."""
    skill = _build_skill(args)
    status = skill.check_credentials_status()

    print(f"{'Credential':30s} {'Env Key':30s} {'Status':12s} {'Type':20s}")
    print("-" * 95)

    all_ok = True
    for name, info in status.items():
        loaded = info["loaded"]
        icon   = _c("✓", _GREEN) if loaded else _c("✗", _RED)
        status_str = _c("loaded", _GREEN) if loaded else _c("missing", _RED)
        if not loaded and info.get("required"):
            all_ok = False
        print(f"{icon} {name:28s} {info['env_key']:30s} {status_str:22s} {info['cred_type']:20s}")

    print()
    if all_ok:
        print(_c("All credentials verified.", _GREEN))
        return 0
    else:
        print(_c("Some required credentials are missing. Add them to .env.", _RED))
        return 1


def cmd_scan_vault(args: argparse.Namespace) -> int:
    """Scan the vault for accidentally committed secrets."""
    skill    = _build_skill(args)
    findings = skill.scan_vault(path=args.path or None)

    if not findings:
        print(_c("No secrets detected in vault.", _GREEN))
        return 0

    print(f"\n{_c('FINDINGS', _RED)} — {len(findings)} potential secret(s) detected:\n")
    for f in findings:
        sev = _severity_colour(f.severity.value)
        print(f"  [{sev}] {f.file_path}:{f.line_number}")
        print(f"      Pattern  : {f.pattern_name}")
        print(f"      Match    : {f.redacted_match}")
        print(f"      Context  : {f.context[:100]}")
        print()

    print(_c(f"{len(findings)} finding(s). Review and remove secrets from vault files.", _RED))
    return 1


def cmd_list_credentials(args: argparse.Namespace) -> int:
    """List registered credentials and their status."""
    skill = _build_skill(args)
    data  = skill.to_safe_dict()

    if not data:
        print("No credentials registered.")
        return 0

    print(f"{'Name':30s} {'Env Key':30s} {'Type':20s} {'Loaded':8s} {'Rotation':10s}")
    print("-" * 100)

    for name, info in sorted(data.items()):
        loaded = _c("yes", _GREEN) if info["loaded"] else _c("no", _RED)
        rot    = ""
        if info.get("rotation_due"):
            rot = _c("OVERDUE", _RED)
        elif info.get("days_until_rotation") is not None:
            days = info["days_until_rotation"]
            rot  = _c(f"{days}d", _YELLOW if days <= 14 else _GREEN)
        print(f"{name:30s} {info['env_key']:30s} {info['cred_type']:20s} {loaded:18s} {rot}")

    return 0


def cmd_rotate_reminder(args: argparse.Namespace) -> int:
    """Print rotation reminders for overdue credentials."""
    skill = _build_skill(args)
    due   = skill.rotation_due()

    if not due:
        print(_c("No credentials overdue for rotation.", _GREEN))
        return 0

    print(_c(f"{len(due)} credential(s) overdue for rotation:\n", _YELLOW))
    for spec in due:
        days = abs(spec.days_until_rotation or 0)
        print(f"  {_c(spec.name, _RED):40s} overdue by {days} days (env: {spec.env_key})")

    return 1


def cmd_audit(args: argparse.Namespace) -> int:
    """Show recent audit log entries."""
    skill   = _build_skill(args)
    entries = skill.read_audit(date=args.date or None)

    if not entries:
        print("No audit entries found.")
        return 0

    print(f"{'Time':22s} {'Event':18s} {'Agent':20s} {'Credential':25s} {'Outcome':10s}")
    print("-" * 100)
    for e in entries[-50:]:  # Show last 50
        ts = e.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        outcome_str = _c(e.outcome, _GREEN if e.outcome == "success" else _RED)
        print(f"{ts:22s} {e.event_type:18s} {e.agent_id:20s} {e.cred_name:25s} {outcome_str}")

    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="security",
        description="SECURITY_AND_CREDENTIAL_MANAGEMENT_SKILL CLI",
    )
    parser.add_argument("--vault", required=True, help="Path to Obsidian vault root")

    sub = parser.add_subparsers(dest="command", required=True)

    # verify
    p = sub.add_parser("verify", help="Verify credentials are set in environment")
    p.set_defaults(func=cmd_verify)

    # scan-vault
    p = sub.add_parser("scan-vault", help="Scan vault for accidentally committed secrets")
    p.add_argument("--path", default=None, help="Relative path within vault to scan")
    p.set_defaults(func=cmd_scan_vault)

    # list-credentials
    p = sub.add_parser("list-credentials", help="List registered credentials and status")
    p.set_defaults(func=cmd_list_credentials)

    # rotate-reminder
    p = sub.add_parser("rotate-reminder", help="Show overdue rotation reminders")
    p.set_defaults(func=cmd_rotate_reminder)

    # audit
    p = sub.add_parser("audit", help="Show recent security audit log")
    p.add_argument("--date", default=None, help="Date YYYY-MM-DD (default: today)")
    p.set_defaults(func=cmd_audit)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args   = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
