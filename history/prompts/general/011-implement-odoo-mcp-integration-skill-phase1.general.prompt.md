---
id: 011
title: Implement ODOO_MCP_INTEGRATION_SKILL Phase 1
stage: green
date: 2026-03-01
surface: agent
model: claude-sonnet-4-6
feature: ODOO_MCP_INTEGRATION_SKILL
branch: main
user: architext
command: implement ODOO_MCP_INTEGRATION_SKILL Phase 1
labels: ["odoo","skill","phase1","hitl","mock-adapter","mcp","erp"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - src/skills/actions/odoo/__init__.py
  - src/skills/actions/odoo/models.py
  - src/skills/actions/odoo/adapter.py
  - src/skills/actions/odoo/logger.py
  - src/skills/actions/odoo/action.py
  - src/skills/actions/odoo/cli.py
  - tests/test_odoo_skill.py
  - .claude/skills/actions/ODOO_MCP_INTEGRATION_SKILL/SKILL.md
tests:
  - tests/test_odoo_skill.py (102 tests — all pass)
---

## Prompt

Implement ODOO_MCP_INTEGRATION_SKILL Phase 1. Requirements: MCP-style integration interface, Mock Odoo adapter (no real API calls yet), Support basic operations: create_record, update_record, fetch_record, Integrate with Orchestrator registry, Enforce HITL for tier ≥ 2 operations, Use Security & Credential Management for Odoo credentials, Logging under 70-LOGS/odoo/, Unit tests required. Follow existing architecture and constitution. Do not modify completed skills.

## Response snapshot

Implemented ODOO_MCP_INTEGRATION_SKILL Phase 1 following the established action skill pattern:

**models.py** — OdooOperation (CREATE_RECORD, UPDATE_RECORD, FETCH_RECORD), OdooActionStatus (PENDING_APPROVAL, APPROVED, SUCCESS, DENIED, FAILED, NOT_FOUND), OPERATION_DEFAULT_TIER dict {writes: 3, reads: 1}, OdooRequest/OdooResult dataclasses with to_dict/from_dict roundtrip, OdooConfig, make_create_request / make_update_request / make_fetch_request factories.

**adapter.py** — OdooAdapter ABC, MockOdooAdapter with in-memory per-model record stores, auto-incrementing IDs per model, seed_record/get_stored/record_count test helpers, set_healthy/clear/set_fail_execute control methods. RealOdooAdapter Phase 2 stub.

**logger.py** — OdooLogger writing JSONL to 70-LOGS/odoo/YYYY-MM-DD.jsonl. All methods non-raising (fail-safe).

**action.py** — OdooAction: validate (model non-empty, operation supported, record_id required for update/fetch, data required for create) → HITL gate (tier ≥ 2) → execute via adapter → log. Fail-safe DENIED on HITL failure.

**__init__.py** — OdooSkill facade: create_record (default tier 3), update_record (default tier 3), fetch_record (always tier 1 for reads). Orchestrator: registers odoo.create_record, odoo.update_record, odoo.fetch_record. Security: registers odoo_credential CredentialSpec (required=True).

**cli.py** — Commands: create (--model, --data JSON, --tier), update (--model, --id, --data JSON, --tier), fetch (--model, --id), status, logs (--date). Color-coded status output.

**tests/test_odoo_skill.py** — 102 tests covering all layers.

Results: 102/102 pass. Full suite: 855/855.

## Outcome

- ✅ Impact: ODOO_MCP_INTEGRATION_SKILL Phase 1 complete — 3 operations (create/update/fetch) with mock adapter, HITL tier gate, Security credential spec, Orchestrator registration, audit logging
- 🧪 Tests: 102 new tests, all pass; full suite 855/855
- 📁 Files: 7 source files created, SKILL.md updated
- 🔁 Next prompts: Phase 2 (RealOdooAdapter with xmlrpc/JSON-RPC); CEO_WEEKLY_AUDIT_SKILL Phase 1
- 🧠 Reflection: fetch_record always defaults to tier 1 regardless of config.default_tier — reads are inherently lower-risk than writes; this mirrors the HITL constitution principle of proportionate oversight

## Evaluation notes (flywheel)

- Failure modes observed: none — all 102 tests passed first run
- Graders run and results (PASS/FAIL): pytest tests/test_odoo_skill.py → PASS (102/102); pytest tests/ → PASS (855/855)
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): implement RealOdooAdapter using Python xmlrpc.client for Phase 2
