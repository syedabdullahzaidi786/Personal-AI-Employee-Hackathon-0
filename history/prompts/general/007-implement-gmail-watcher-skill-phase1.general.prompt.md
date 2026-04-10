---
id: "007"
title: "Implement GMAIL_WATCHER_SKILL Phase 1"
stage: general
date: 2026-03-01
surface: agent
model: claude-sonnet-4-6
feature: gmail-watcher-skill
branch: master
user: operator
command: "Implement GMAIL_WATCHER_SKILL Phase 1"
labels: ["implementation", "phase1", "watcher", "gmail", "python", "event-driven", "mockable"]
links:
  spec: ".claude/skills/watchers/GMAIL_WATCHER_SKILL/SKILL.md"
  ticket: "null"
  adr: "null"
  pr: "null"
files:
  - src/skills/watchers/gmail/__init__.py (created)
  - src/skills/watchers/gmail/models.py (created)
  - src/skills/watchers/gmail/client.py (created)
  - src/skills/watchers/gmail/watcher.py (created)
  - src/skills/watchers/gmail/handlers.py (created)
  - src/skills/watchers/gmail/cli.py (created)
  - tests/test_gmail_watcher.py (created)
  - .claude/skills/watchers/GMAIL_WATCHER_SKILL/SKILL.md (updated)
tests:
  - tests/test_gmail_watcher.py (73 tests, 73 passed)
  - Total suite: 499 tests, all pass
---

## Prompt

Implement GMAIL_WATCHER_SKILL Phase 1. Requirements: Extend Base Watcher framework, Poll Gmail (mockable interface for now, no real API calls), Detect new messages and emit structured events, Integrate with Orchestrator registry, Respect Security & Credential policies, Logging under 70-LOGS/, Unit tests required. Follow existing architecture and constitution. Do not modify completed skills.

## Response snapshot

Implemented **GMAIL_WATCHER_SKILL Phase 1** — 6 modules + 73 unit tests, all passing.
Full suite: 499/499 green.

### Modules

| Module | Responsibility |
|--------|---------------|
| `models.py` | GmailMessage, GmailConfig, GmailEventType constants, make_gmail_message factory |
| `client.py` | GmailClient ABC, MockGmailClient (in-memory/testable), RealGmailClient (Phase 2 stub) |
| `watcher.py` | GmailWatcher(BaseWatcher): poll/health_check + seen-IDs deduplication persisted to vault |
| `handlers.py` | make_log_handler, make_orchestrator_handler, make_filter_handler, make_sender_filter |
| `cli.py` | CLI: status, tick, events, inject |
| `__init__.py` | GmailWatcherSkill facade composing watcher + dispatcher |

### Key design decisions
- GmailClient ABC: clean separation of interface from implementation — MockGmailClient enables tests with zero network
- Seen-IDs deduplication: persisted to 70-LOGS/watchers/{id}/seen-ids.json — survives restarts; capped at 5000 entries
- Attachment detection: emits `gmail_attachment_received` when `has_attachments=True`
- No secrets in payload: GmailMessage.to_dict() exposes only safe metadata
- credentials_name is a reference to SecuritySkill — actual token never stored in config
- RealGmailClient is a Phase 2 stub (raises NotImplementedError, health_check=False)

### Test classes (73 tests)
TestGmailMessage (5), TestGmailConfig (5), TestGmailEventType (1),
TestMakeGmailMessage (4), TestMockGmailClient (10), TestRealGmailClient (3),
TestGmailWatcher (15), TestHandlers (10), TestGmailWatcherSkill (12), TestCLI (7)

## Outcome

- ✅ Impact: GMAIL_WATCHER_SKILL Phase 1 complete; polls Gmail via mockable interface, emits structured WatcherEvents
- 🧪 Tests: 73 new tests, 499 total — all passing
- 📁 Files: 6 new source files created, 1 test file, 1 SKILL.md updated
- 🔁 Next prompts: WHATSAPP_WATCHER_SKILL or EMAIL_MCP_ACTION_SKILL
- 🧠 Reflection: GmailClient ABC pattern keeps watcher testable at zero cost; seen-IDs persistence ensures idempotent polling

## Evaluation notes (flywheel)

- Failure modes observed: none — first run 73/73 green
- Graders run and results (PASS/FAIL): pytest 73/73 PASS, full suite 499/499 PASS
- Prompt variant (if applicable): none
- Next experiment: Wire GmailWatcherSkill.tick() into RalphWiggumLoop.tick_all() to auto-process emails
