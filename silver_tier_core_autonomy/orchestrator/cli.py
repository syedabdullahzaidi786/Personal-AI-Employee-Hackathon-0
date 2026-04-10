"""
ORCHESTRATOR_SYSTEM_SKILL — CLI
Commands: run, status, list, registry

Usage::

    python -m skills.core.orchestrator.cli --vault /path/to/vault run workflow.json
    python -m skills.core.orchestrator.cli --vault /path/to/vault status RUN-<uuid>
    python -m skills.core.orchestrator.cli --vault /path/to/vault list
    python -m skills.core.orchestrator.cli --vault /path/to/vault registry
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# ANSI colours
_GREEN  = "\033[92m"
_RED    = "\033[91m"
_YELLOW = "\033[93m"
_CYAN   = "\033[96m"
_RESET  = "\033[0m"


def _colour(text: str, colour: str) -> str:
    return f"{colour}{text}{_RESET}"


def _status_colour(status: str) -> str:
    s = status.upper()
    if s in ("SUCCESS", "COMPLETED", "AUTO_APPROVED", "APPROVED"):
        return _colour(s, _GREEN)
    if s in ("FAILED", "ABORTED", "DENIED", "BLOCKED"):
        return _colour(s, _RED)
    if s in ("PENDING", "RUNNING", "WAITING"):
        return _colour(s, _YELLOW)
    return s


# ---------------------------------------------------------------------------
# Build orchestrator (lazy import to keep CLI startup light)
# ---------------------------------------------------------------------------

def _build_skill(vault: str):
    from . import OrchestratorSkill
    return OrchestratorSkill(vault_root=vault)


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def cmd_run(args: argparse.Namespace) -> int:
    """Load a workflow JSON and execute it."""
    skill = _build_skill(args.vault)

    path = Path(args.workflow_file)
    if not path.exists():
        print(f"{_colour('ERROR', _RED)}: Workflow file not found: {path}", file=sys.stderr)
        return 1

    try:
        wf_data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"{_colour('ERROR', _RED)}: Invalid JSON: {exc}", file=sys.stderr)
        return 1

    from .models import Workflow
    workflow = Workflow.from_dict(wf_data)

    print(f"Running workflow {_colour(workflow.name, _CYAN)} ({len(workflow.steps)} steps)…")
    run = skill.run_workflow(workflow, triggered_by=args.triggered_by)

    print(f"\nRun ID : {run.run_id}")
    print(f"Status : {_status_colour(run.status.value)}")
    print(f"Time   : {run.duration_ms:.0f}ms\n")

    for step_id, result in run.step_results.items():
        icon = "✓" if result.status.value == "success" else "✗"
        print(f"  {icon} {step_id:30s} {_status_colour(result.status.value)}")
        if result.error:
            print(f"      Error: {result.error[:120]}")

    return 0 if run.status.value in ("completed",) else 1


def cmd_status(args: argparse.Namespace) -> int:
    """Show status of a specific run."""
    skill = _build_skill(args.vault)
    run = skill.get_run(args.run_id)
    if run is None:
        print(f"{_colour('ERROR', _RED)}: Run '{args.run_id}' not found.", file=sys.stderr)
        return 1

    print(f"Run ID   : {run.run_id}")
    print(f"Workflow : {run.workflow_name}")
    print(f"Status   : {_status_colour(run.status.value)}")
    print(f"Started  : {run.started_at}")
    print(f"Finished : {run.finished_at}")
    print(f"Duration : {run.duration_ms:.0f}ms\n")

    print("Steps:")
    for step_id, result in run.step_results.items():
        icon = "✓" if result.status.value == "success" else ("…" if result.status.value == "waiting" else "✗")
        hitl = f" [HITL:{result.hitl_request_id}]" if result.hitl_request_id else ""
        print(f"  {icon} {step_id:30s} {_status_colour(result.status.value)}{hitl}")
        if result.error:
            print(f"      {result.error[:120]}")

    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List all workflow runs."""
    skill = _build_skill(args.vault)
    runs  = skill.list_runs()

    if not runs:
        print("No runs found.")
        return 0

    print(f"{'Run ID':40s} {'Workflow':30s} {'Status':15s} {'Duration':>10s}")
    print("-" * 100)
    for run in runs:
        dur = f"{run.duration_ms:.0f}ms" if run.duration_ms else "—"
        print(
            f"{run.run_id:40s} {run.workflow_name:30s} "
            f"{_status_colour(run.status.value):25s} {dur:>10s}"
        )
    return 0


def cmd_registry(args: argparse.Namespace) -> int:
    """Print registered skills and operations."""
    skill = _build_skill(args.vault)
    mapping = skill.list_registry()
    if not mapping:
        print("No handlers registered.")
        return 0
    for skill_name, ops in mapping.items():
        print(f"  {_colour(skill_name, _CYAN)}: {', '.join(ops)}")
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orchestrator",
        description="ORCHESTRATOR_SYSTEM_SKILL CLI",
    )
    parser.add_argument("--vault", required=True, help="Path to Obsidian vault root")

    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = sub.add_parser("run", help="Execute a workflow from a JSON file")
    p_run.add_argument("workflow_file", help="Path to workflow JSON file")
    p_run.add_argument("--triggered-by", default="cli", dest="triggered_by")
    p_run.set_defaults(func=cmd_run)

    # status
    p_status = sub.add_parser("status", help="Show status of a workflow run")
    p_status.add_argument("run_id", help="Run ID (e.g. RUN-<uuid>)")
    p_status.set_defaults(func=cmd_status)

    # list
    p_list = sub.add_parser("list", help="List all workflow runs")
    p_list.set_defaults(func=cmd_list)

    # registry
    p_reg = sub.add_parser("registry", help="Show registered skill handlers")
    p_reg.set_defaults(func=cmd_registry)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args   = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
