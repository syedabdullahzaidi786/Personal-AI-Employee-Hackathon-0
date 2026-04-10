---
id: 013
title: Refactor Project Into Maturity Tier Folders
stage: general
date: 2026-03-02
surface: agent
model: claude-sonnet-4-6
feature: none
branch: main
user: Computer Technology
command: /login + manual prompt
labels: ["refactor", "architecture", "tier-structure", "import-paths", "migration"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - bronze_tier_governance/__init__.py
  - bronze_tier_governance/hitl/ (7 files, from src/skills/safety/hitl/)
  - bronze_tier_governance/security/ (9 files, from src/skills/safety/security/)
  - silver_tier_core_autonomy/__init__.py
  - silver_tier_core_autonomy/filesystem_automation/ (5 files, from src/skills/core/filesystem_automation/)
  - silver_tier_core_autonomy/orchestrator/ (8 files, from src/skills/core/orchestrator/)
  - silver_tier_core_autonomy/ralph/ (9 files, from src/skills/core/ralph/)
  - golden_tier_external_world/__init__.py
  - golden_tier_external_world/actions/__init__.py
  - golden_tier_external_world/actions/browser/ (6 files, from src/skills/actions/browser/)
  - golden_tier_external_world/actions/email/ (6 files, from src/skills/actions/email/)
  - golden_tier_external_world/actions/odoo/ (6 files, from src/skills/actions/odoo/)
  - golden_tier_external_world/watchers/__init__.py
  - golden_tier_external_world/watchers/base/ (8 files, from src/skills/watchers/base/)
  - golden_tier_external_world/watchers/gmail/ (6 files, from src/skills/watchers/gmail/)
  - golden_tier_external_world/watchers/whatsapp/ (6 files, from src/skills/watchers/whatsapp/)
  - platinum_tier_business_layer/__init__.py
  - platinum_tier_business_layer/ceo_audit/ (6 files, from src/skills/business/ceo_audit/)
  - enterprise_bonus_tier/__init__.py
  - conftest.py (new - root pytest path anchor)
  - tests/test_hitl.py (import paths updated)
  - tests/test_security.py (import paths updated)
  - tests/test_orchestrator.py (import paths updated)
  - tests/test_filesystem_automation.py (import paths updated)
  - tests/test_ralph.py (import paths updated)
  - tests/test_browser_skill.py (import paths updated)
  - tests/test_email_action.py (import paths updated)
  - tests/test_odoo_skill.py (import paths updated)
  - tests/test_base_watcher.py (import paths updated)
  - tests/test_gmail_watcher.py (import paths updated)
  - tests/test_whatsapp_watcher.py (import paths updated)
  - tests/test_ceo_audit_skill.py (import paths updated)
  - src/ (DELETED — replaced by tier folders)
tests:
  - pytest tests/ — 964 passed, 16 failed (16 pre-existing behavioral failures confirmed pre-migration)
---

## Prompt

Refactor the project into maturity-based tier folders without breaking existing functionality.

Create the following top-level directories:

1. bronze_tier_governance/
2. silver_tier_core_autonomy/
3. golden_tier_external_world/
4. platinum_tier_business_layer/
5. enterprise_bonus_tier/



Rules:
- Keep constitution.md in the root (HACKATHON_0/)
- Do not modify business logic
- Do not break the test suite (all 980 tests must still pass)
- Update import paths where required
- Maintain clean, professional architecture
- Preserve current vault structure

First provide a detailed migration plan, then apply changes after approval.

## Response snapshot

Executed a 5-step migration plan (approved by user):

1. **conftest.py created** — root-level pytest path anchor replacing per-test `sys.path.insert` hacks.

2. **5 tier directories created** with docstring `__init__.py` files explaining each tier's purpose:
   - `bronze_tier_governance/` — HITL + Security (foundational safety controls)
   - `silver_tier_core_autonomy/` — Filesystem + Orchestrator + Ralph (core infrastructure)
   - `golden_tier_external_world/` — Actions (browser/email/odoo) + Watchers (base/gmail/whatsapp)
   - `platinum_tier_business_layer/` — CEO Audit (business intelligence)
   - `enterprise_bonus_tier/` — Placeholder for future enterprise skills

3. **All 84 source files copied** via `cp -r` to new tier locations. Zero content changes needed — all source files use only relative imports.

4. **All 12 test files updated**: removed `sys.path.insert(0, .../src)` bootstrap and replaced `from skills.*` absolute import prefixes with tier-specific paths. Both top-level imports and inline inline imports within test methods were updated.

5. **`src/` directory deleted** after final verification.

Key discovery: source files exclusively use relative imports (`.models`, `.adapter`, etc.) — zero edits needed inside the 84 moved Python files.

Final test run: **964 passed, 16 failed** — identical to pre-migration baseline (all 16 failures are pre-existing behavioral/mock assertion failures unrelated to import paths, confirmed by running same tests against original `src/` paths).

## Outcome

- ✅ Impact: Clean maturity-tier architecture replacing flat src/skills/ layout; project now visually reflects the constitution's Bronze→Silver→Gold→Platinum progression
- 🧪 Tests: 964/980 pass; 16 pre-existing failures unchanged (browser HITL gate mock assertions, email/odoo security integration, ralph orchestrator dispatch)
- 📁 Files: 5 new tier dirs + 7 __init__.py stubs + conftest.py created; 12 test files updated; src/ deleted
- 🔁 Next prompts: Fix the 16 pre-existing test failures (HITL gate returns DENIED instead of PENDING_APPROVAL; security credential registration; ralph orchestrator dispatch)
- 🧠 Reflection: The critical insight was that all source files use relative imports — this made the structural migration clean with zero business logic changes. Only test files needed absolute import path updates.

## Evaluation notes (flywheel)

- Failure modes observed: Inline imports inside test methods (lines 300-800+) were not caught by top-of-file edit; required a second-pass sed sweep. Always grep for `from skills.` after initial edits.
- Graders run and results (PASS/FAIL): pytest tests/ — PASS (964 passing, 0 new failures introduced)
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): Add a pytest.ini with `pythonpath = .` to make the conftest.py path anchor redundant, then remove conftest.py
