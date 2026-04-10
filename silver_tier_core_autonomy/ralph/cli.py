"""
RALPH_WIGGUM_LOOP_SKILL — CLI
Commands: tick, start, status, queue, memory

Usage::

    python -m skills.core.ralph.cli --vault /path/to/vault tick
    python -m skills.core.ralph.cli --vault /path/to/vault start
    python -m skills.core.ralph.cli --vault /path/to/vault status
    python -m skills.core.ralph.cli --vault /path/to/vault queue list
    python -m skills.core.ralph.cli --vault /path/to/vault queue add --skill echo --op say --title "Hello"
    python -m skills.core.ralph.cli --vault /path/to/vault memory consolidate
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

# ANSI colours
_GREEN  = "\033[92m"
_RED    = "\033[91m"
_YELLOW = "\033[93m"
_CYAN   = "\033[96m"
_RESET  = "\033[0m"


def _c(text: str, colour: str) -> str:
    return f"{colour}{text}{_RESET}"


def _status_c(status: str) -> str:
    s = status.upper()
    if s in ("SUCCESS", "HEALTHY", "DONE"):     return _c(s, _GREEN)
    if s in ("FAILED", "UNHEALTHY", "ERROR"):   return _c(s, _RED)
    if s in ("PARTIAL", "DEGRADED", "PENDING"): return _c(s, _YELLOW)
    return s


def _build_runner(args: argparse.Namespace):
    from . import RalphSkill
    skill = RalphSkill(vault_root=args.vault)
    return skill


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def cmd_tick(args: argparse.Namespace) -> int:
    """Execute a single tick."""
    skill = _build_runner(args)
    print(f"Running tick #{skill.runner.state.tick_count + 1}…")
    tick = skill.tick()
    print(f"\nTick {_c(tick.tick_id, _CYAN)} — {_status_c(tick.status.value)} ({tick.duration_ms:.0f}ms)\n")
    for pr in tick.phase_results:
        icon = "✓" if pr.status.value == "success" else "✗"
        print(f"  {icon} {pr.phase.value:30s} {_status_c(pr.status.value)} ({pr.duration_ms:.0f}ms)")
        if pr.error:
            print(f"      Error: {pr.error[:100]}")
    if tick.health:
        print(f"\nHealth: {_status_c(tick.health.overall.value)}")
        for comp in tick.health.components:
            icon = "●" if comp.state.value == "healthy" else "○"
            print(f"  {icon} {comp.name:25s} {_status_c(comp.state.value)} ({comp.latency_ms:.1f}ms)")
    return 0 if tick.status.value in ("success", "partial") else 1


def cmd_start(args: argparse.Namespace) -> int:
    """Run the loop continuously until SIGINT/SIGTERM."""
    skill = _build_runner(args)
    print(f"Starting Ralph loop (interval={args.interval}s, Ctrl+C to stop)…\n")
    skill.runner.set_max_tasks_per_tick(args.max_tasks)
    if hasattr(args, 'interval') and args.interval:
        skill.runner._config.tick_interval_secs = args.interval

    def on_tick(tick):
        icon = "✅" if tick.status.value == "success" else ("⚠️" if tick.status.value == "partial" else "❌")
        print(f"{icon} Tick #{tick.tick_number} {tick.tick_id} — {tick.status.value} ({tick.duration_ms:.0f}ms)")

    skill.runner.run_forever(on_tick=on_tick)
    print("\nLoop stopped.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Show loop state."""
    skill = _build_runner(args)
    state = skill.runner.state
    pending = skill.runner.queue.pending_count()
    print(f"Agent ID         : {state.agent_id}")
    print(f"Total ticks      : {state.tick_count}")
    print(f"Uptime ticks     : {state.uptime_ticks}")
    print(f"Consecutive fails: {state.consecutive_fails}")
    print(f"Last tick        : {state.last_tick_at or 'never'}")
    print(f"Last status      : {_status_c(state.last_tick_status.value) if state.last_tick_status else 'n/a'}")
    print(f"Tasks done       : {state.total_tasks_done}")
    print(f"Tasks pending    : {pending}")
    return 0


def cmd_queue(args: argparse.Namespace) -> int:
    """Manage the task queue."""
    skill = _build_runner(args)
    q     = skill.runner.queue

    if args.queue_cmd == "list":
        pending = q.list_pending()
        if not pending:
            print("No pending tasks.")
        else:
            print(f"{'Task ID':20s} {'Title':30s} {'Skill.Op':25s} {'Pri':5s}")
            print("-" * 85)
            for t in pending:
                print(f"{t.task_id:20s} {t.title[:30]:30s} "
                      f"{t.skill_name}.{t.operation:20s} {t.priority.name:5s}")
        return 0

    if args.queue_cmd == "add":
        from .models import make_task, TaskPriority
        priority = TaskPriority[args.priority.upper()] if args.priority else TaskPriority.NORMAL
        task = make_task(
            title=args.title,
            skill_name=args.skill,
            operation=args.op,
            priority=priority,
        )
        q.enqueue(task)
        print(f"Task enqueued: {_c(task.task_id, _CYAN)}")
        return 0

    print(f"Unknown queue sub-command: {args.queue_cmd}", file=sys.stderr)
    return 1


def cmd_memory(args: argparse.Namespace) -> int:
    """Memory consolidation commands."""
    skill = _build_runner(args)
    m     = skill.runner.memory

    if args.memory_cmd == "consolidate":
        result = m.consolidate()
        print(f"Consolidated : {result['consolidated_count']} entries")
        print(f"Skipped      : {result['skipped_count']}")
        print(f"Summary file : {result['summary_path']}")
        return 0

    if args.memory_cmd == "stats":
        print(f"Episodic entries : {m.get_episodic_count()}")
        print(f"Semantic summaries: {m.get_semantic_count()}")
        return 0

    print(f"Unknown memory sub-command: {args.memory_cmd}", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ralph",
        description="RALPH_WIGGUM_LOOP_SKILL CLI",
    )
    parser.add_argument("--vault", required=True, help="Path to Obsidian vault root")

    sub = parser.add_subparsers(dest="command", required=True)

    # tick
    p_tick = sub.add_parser("tick", help="Execute a single loop tick")
    p_tick.set_defaults(func=cmd_tick)

    # start
    p_start = sub.add_parser("start", help="Run the loop continuously")
    p_start.add_argument("--interval", type=int, default=300, help="Seconds between ticks")
    p_start.add_argument("--max-tasks", type=int, default=5, dest="max_tasks",
                         help="Max tasks dispatched per tick")
    p_start.set_defaults(func=cmd_start)

    # status
    p_status = sub.add_parser("status", help="Show current loop state")
    p_status.set_defaults(func=cmd_status)

    # queue
    p_queue = sub.add_parser("queue", help="Manage the task queue")
    qsub    = p_queue.add_subparsers(dest="queue_cmd", required=True)

    qsub.add_parser("list", help="List pending tasks")

    p_qadd = qsub.add_parser("add", help="Add a task to the queue")
    p_qadd.add_argument("--skill", required=True)
    p_qadd.add_argument("--op", required=True)
    p_qadd.add_argument("--title", default="Manual task")
    p_qadd.add_argument("--priority", default="normal",
                        choices=["urgent", "high", "normal", "low"])

    p_queue.set_defaults(func=cmd_queue)

    # memory
    p_mem = sub.add_parser("memory", help="Memory consolidation")
    msub  = p_mem.add_subparsers(dest="memory_cmd", required=True)
    msub.add_parser("consolidate", help="Run consolidation now")
    msub.add_parser("stats", help="Show memory stats")
    p_mem.set_defaults(func=cmd_memory)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args   = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
