---
id: "006"
title: "Implement BASE_WATCHER_CREATION_SKILL Phase 1"
stage: general
date: 2026-03-01
surface: agent
model: claude-sonnet-4-6
feature: base-watcher-creation-skill
branch: master
user: operator
command: "BASE_WATCHER_CREATION_SKILL"
labels: ["implementation", "phase1", "watcher", "framework", "python", "event-driven"]
links:
  spec: ".claude/skills/watchers/BASE_WATCHER_CREATION_SKILL/SKILL.md"
  ticket: "null"
  adr: "null"
  pr: "null"
files:
  - src/skills/watchers/base/__init__.py (created)
  - src/skills/watchers/base/models.py (created)
  - src/skills/watchers/base/base.py (created)
  - src/skills/watchers/base/registry.py (created)
  - src/skills/watchers/base/dispatcher.py (created)
  - src/skills/watchers/base/store.py (created)
  - src/skills/watchers/base/logger.py (created)
  - src/skills/watchers/base/cli.py (created)
  - tests/test_base_watcher.py (created)
  - .claude/skills/watchers/BASE_WATCHER_CREATION_SKILL/SKILL.md (updated)
tests:
  - tests/test_base_watcher.py (80 tests, 80 passed)
  - Total suite: 426 tests, all pass
---

## Prompt

BASE_WATCHER_CREATION_SKILL

## Response snapshot

Implemented **BASE_WATCHER_CREATION_SKILL Phase 1** from scratch — 8 modules +
80 unit tests, all passing. Full suite: 426/426 green.

### Modules

| Module | Responsibility |
|--------|---------------|
| `models.py` | WatcherConfig, WatcherEvent, WatcherState, WatcherTickResult, DispatchResult, make_event |
| `base.py` | BaseWatcher ABC: abstract poll/health_check; tick()/start()/stop() with state persistence |
| `registry.py` | WatcherRegistry: register, require, unregister, list_running |
| `dispatcher.py` | EventDispatcher: tier 0/1 direct, tier 2+ HITL, wildcard handlers, fail_open |
| `store.py` | EventStore: JSONL per watcher per date in 70-LOGS/watchers/ |
| `logger.py` | WatcherLogger: daily + error logs, fail-safe |
| `__init__.py` | WatcherSkill facade |
| `cli.py` | list / status / events commands |

### Key design decisions
- BaseWatcher.tick() is the core unit: health → poll → store → dispatch → save_state
- tick() NEVER raises — health failures short-circuit, poll errors are captured
- EventDispatcher.fail_open=True for local dev (Tier 2+ dispatches directly without HITL)
- State persisted to vault: 70-LOGS/watchers/{id}/state.json — CLI can read without running process
- EventStore uses JSONL files: append-on-write, full round-trip with mark_processed

### Test classes (80 tests)
TestWatcherConfig (2), TestWatcherEvent (5), TestWatcherState (2),
TestWatcherTickResult (1), TestDispatchResult (1), TestEventTypeEnum (1),
TestBaseWatcher (15), TestWatcherRegistry (11), TestEventDispatcher (10),
TestEventStore (8), TestWatcherLogger (6), TestWatcherSkill (13), TestCLI (7)

## Outcome

- ✅ Impact: BASE_WATCHER_CREATION_SKILL Phase 1 complete; GMAIL + WhatsApp watchers can now extend BaseWatcher
- 🧪 Tests: 80 new tests, 426 total — all passing
- 📁 Files: 9 new files created, 1 updated (SKILL.md)
- 🔁 Next prompts: GMAIL_WATCHER_SKILL or WHATSAPP_WATCHER_SKILL
- 🧠 Reflection: Clean ABC pattern works well; fail_open=True on dispatcher prevents blocking in dev environment

## Evaluation notes (flywheel)

- Failure modes observed: none — first run 80/80 green
- Graders run and results (PASS/FAIL): pytest 80/80 PASS, full suite 426/426 PASS
- Prompt variant (if applicable): none
- Next experiment: Add integration test chaining WatcherSkill.tick_all() → Ralph loop task queue
