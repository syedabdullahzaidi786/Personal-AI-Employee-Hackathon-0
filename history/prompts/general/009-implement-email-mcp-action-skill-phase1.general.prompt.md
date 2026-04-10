---
id: 009
title: "Implement EMAIL_MCP_ACTION_SKILL Phase 1"
stage: green
date: 2026-03-01
surface: agent
model: claude-sonnet-4-6
feature: email-mcp-action-skill
branch: main
user: Computer Technology
command: implement EMAIL_MCP_ACTION_SKILL Phase 1
labels: ["email","mcp","action","hitl","orchestrator","security","phase1"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - src/skills/actions/__init__.py
  - src/skills/actions/email/__init__.py
  - src/skills/actions/email/models.py
  - src/skills/actions/email/adapter.py
  - src/skills/actions/email/action.py
  - src/skills/actions/email/logger.py
  - src/skills/actions/email/cli.py
  - tests/test_email_action.py
  - .claude/skills/actions/EMAIL_MCP_ACTION_SKILL/SKILL.md
tests:
  - tests/test_email_action.py (75 tests)
---

## Prompt

Implement EMAIL_MCP_ACTION_SKILL Phase 1.

Requirements:
- MCP-style action interface
- Mock email sending adapter (no real SMTP)
- Integrate with Orchestrator
- Enforce HITL for tier ≥ 2
- Respect Security & Credential policies
- Logging under 70-LOGS/email/
- Unit tests required

Follow existing architecture.
Do not modify completed skills.

## Response snapshot

Implemented **EMAIL_MCP_ACTION_SKILL Phase 1** — all 75 unit tests passing.

Architecture follows existing skill patterns (GmailWatcher, WhatsAppWatcher):
- `models.py` — EmailRequest, EmailResult, EmailConfig, EmailActionStatus, EmailEventType
- `adapter.py` — EmailAdapter ABC, MockEmailAdapter (in-memory, no SMTP), RealEmailAdapter (Phase 2 stub)
- `action.py` — EmailAction: validate → HITL gate (tier ≥ 2) → send via adapter
- `logger.py` — Append-only JSONL to 70-LOGS/email/YYYY-MM-DD.jsonl
- `cli.py` — CLI: send, status, logs
- `__init__.py` — EmailActionSkill facade with Orchestrator + Security integration

Key design decisions:
- Tier 3 (High-risk) default: all sends require HITL approval when HITLSkill is attached
- Without HITLSkill: falls back to direct send (test/dev mode)
- HITL failure → DENIED (fail-safe, never sends without approval)
- Registers `email.send` in SkillRegistry (MCP action interface)
- Registers `smtp_credential` CredentialSpec with SecuritySkill

All Phase 1 deliverables complete:
- [x] MCP-style action interface (SkillRegistry registration)
- [x] MockEmailAdapter (in-memory, no SMTP)
- [x] Orchestrator integration (email.send registered)
- [x] HITL gate for tier ≥ 2
- [x] Security credential spec registration
- [x] Logging under 70-LOGS/email/
- [x] 75 unit tests — all passing

## Outcome

- ✅ Impact: EMAIL_MCP_ACTION_SKILL Phase 1 fully tested and complete
- 🧪 Tests: pytest 75/75 PASS, full suite 663/663 PASS
- 📁 Files: 9 files created/updated
- 🔁 Next prompts: Phase 2 — RealEmailAdapter with smtplib/SMTP API; BROWSER_MCP_SKILL or ODOO_MCP_INTEGRATION_SKILL Phase 1
- 🧠 Reflection: MCP action pattern (send → validate → HITL gate → adapter) is distinct from watcher pattern (poll → events). Clear separation of adapter/action/logger enables easy Phase 2 upgrade.

## Evaluation notes (flywheel)

- Failure modes observed: None — all 75 tests passed on first run
- Graders run and results (PASS/FAIL): pytest 75/75 PASS, full suite 663/663 PASS
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Add RealEmailAdapter with smtplib in Phase 2
