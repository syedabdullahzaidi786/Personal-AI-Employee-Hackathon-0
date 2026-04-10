---
id: "008"
title: "Implement WHATSAPP_WATCHER_SKILL Phase 1"
stage: general
date: 2026-03-01
surface: agent
model: claude-sonnet-4-6
feature: whatsapp-watcher-skill
branch: master
user: operator
command: "Implement WHATSAPP_WATCHER_SKILL Phase 1"
labels: ["implementation", "phase1", "watcher", "whatsapp", "python", "event-driven", "hitl", "mockable"]
links:
  spec: ".claude/skills/watchers/WHATSAPP_WATCHER_SKILL/SKILL.md"
  ticket: "null"
  adr: "null"
  pr: "null"
files:
  - src/skills/watchers/whatsapp/__init__.py (created)
  - src/skills/watchers/whatsapp/models.py (created)
  - src/skills/watchers/whatsapp/client.py (created)
  - src/skills/watchers/whatsapp/watcher.py (created)
  - src/skills/watchers/whatsapp/handlers.py (created)
  - src/skills/watchers/whatsapp/cli.py (created)
  - tests/test_whatsapp_watcher.py (created)
  - .claude/skills/watchers/WHATSAPP_WATCHER_SKILL/SKILL.md (updated)
tests:
  - tests/test_whatsapp_watcher.py (89 tests, 89 passed)
  - Total suite: 588 tests, all pass
---

## Prompt

Implement WHATSAPP_WATCHER_SKILL Phase 1.

Requirements:
- Extend Base Watcher framework
- Use mock / adapter-based interface (no real WhatsApp API)
- Detect incoming messages and normalize events
- Register events with Orchestrator
- Enforce HITL for tier ≥ 2 actions
- Log to 70-LOGS/whatsapp/
- Full unit test coverage

Follow existing architecture, security rules, and constitution.
Do not modify completed skills.

## Response snapshot

Implemented **WHATSAPP_WATCHER_SKILL Phase 1** — 6 modules + 89 unit tests, all passing.
Full suite: 588/588 green.

### Modules

| Module | Responsibility |
|--------|---------------|
| `models.py` | WhatsAppMessage, WhatsAppConfig, WhatsAppEventType/MessageType/ChatType constants, make_whatsapp_message |
| `client.py` | WhatsAppClient ABC, MockWhatsAppClient (in-memory), RealWhatsAppClient (Phase 2 stub) |
| `watcher.py` | WhatsAppWatcher(BaseWatcher): poll/health_check + 5-way event-type mapping + seen-IDs |
| `handlers.py` | 7 handlers: log, orchestrator, filter, group_filter, private_filter, sender_filter, media_filter |
| `cli.py` | CLI: status, tick, events, inject (private + group variants) |
| `__init__.py` | WhatsAppWatcherSkill facade: watcher + dispatcher + HITL wiring + security integration |

### Key design decisions
- WhatsAppClient ABC: adapter pattern keeps watcher testable with zero network
- 5-way event type mapping: group → `whatsapp_new_group_message`; location → `whatsapp_new_location_message`; contact → `whatsapp_contact_received`; media → `whatsapp_new_media_message`; default → `whatsapp_new_text_message`
- Seen-IDs deduplication: persisted to vault, capped at 5000 entries
- No media bytes in payload: only filename/mime_type/size_bytes metadata
- HITL enforced: set_hitl() attaches HITLSkill; Tier 2+ events route through approval queue
- credentials_name is reference only; RealWhatsAppClient Phase 2 stub (health_check=False)

### Test classes (89 tests)
TestWhatsAppMessage (8), TestWhatsAppConfig (5), TestWhatsAppEventTypeConstants (2),
TestMakeWhatsAppMessage (6), TestMockWhatsAppClient (13), TestRealWhatsAppClient (3),
TestWhatsAppWatcher (16), TestHandlers (16), TestWhatsAppWatcherSkill (12), TestCLI (8)

## Outcome

- ✅ Impact: WHATSAPP_WATCHER_SKILL Phase 1 complete; monitors WhatsApp via mockable adapter, emits normalised WatcherEvents, enforces HITL for Tier ≥ 2
- 🧪 Tests: 89 new tests, 588 total — all passing
- 📁 Files: 6 new source files, 1 test file, 1 SKILL.md updated
- 🔁 Next prompts: EMAIL_MCP_ACTION_SKILL, BROWSER_MCP_SKILL, or ODOO_MCP_INTEGRATION_SKILL
- 🧠 Reflection: 5-way event type resolution in watcher._resolve_event_type() keeps dispatch routing clean; adapter pattern lets watchers grow with zero test friction

## Evaluation notes (flywheel)

- Failure modes observed: none — first run 89/89 green
- Graders run and results (PASS/FAIL): pytest 89/89 PASS, full suite 588/588 PASS
- Prompt variant (if applicable): none
- Next experiment: Wire WhatsAppWatcherSkill into RalphWiggumLoop.tick_all() alongside GmailWatcherSkill
