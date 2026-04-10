---
id: 014
title: Implement Silver Tier Plan Loop Scheduler LinkedIn
stage: general
date: 2026-03-10
surface: agent
model: claude-sonnet-4-6
feature: silver-tier
branch: main
user: Computer Technology
command: manual prompt
labels: ["silver-tier", "plan-loop", "scheduler", "linkedin", "watcher", "implementation"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - silver_tier_core_autonomy/plan_loop/__init__.py
  - silver_tier_core_autonomy/plan_loop/models.py
  - silver_tier_core_autonomy/plan_loop/analyzer.py
  - silver_tier_core_autonomy/plan_loop/writer.py
  - silver_tier_core_autonomy/plan_loop/logger.py
  - silver_tier_core_autonomy/plan_loop/loop.py
  - silver_tier_core_autonomy/scheduler/__init__.py
  - silver_tier_core_autonomy/scheduler/models.py
  - silver_tier_core_autonomy/scheduler/registry.py
  - silver_tier_core_autonomy/scheduler/logger.py
  - silver_tier_core_autonomy/scheduler/runner.py
  - golden_tier_external_world/watchers/linkedin/__init__.py
  - golden_tier_external_world/watchers/linkedin/models.py
  - golden_tier_external_world/watchers/linkedin/client.py
  - golden_tier_external_world/watchers/linkedin/watcher.py
  - golden_tier_external_world/watchers/linkedin/logger.py
  - golden_tier_external_world/actions/linkedin/__init__.py
  - golden_tier_external_world/actions/linkedin/models.py
  - golden_tier_external_world/actions/linkedin/poster.py
  - golden_tier_external_world/actions/linkedin/logger.py
  - tests/test_plan_loop.py
  - tests/test_scheduler.py
  - tests/test_linkedin_watcher.py
tests:
  - pytest tests/test_plan_loop.py — 49 passed
  - pytest tests/test_scheduler.py — 38 passed
  - pytest tests/test_linkedin_watcher.py — 48 passed
  - pytest tests/ — 1115 passed (full suite)
---

## Prompt

Silver Tier implementation — follow suggested order:
1. Plan.md Reasoning Loop
2. Basic Scheduler
3. LinkedIn Watcher + Post Skill

Per hackathon document (Personal AI Employee Hackathon 0):
Silver Tier requires:
- Two or more Watcher scripts (Gmail + WhatsApp + LinkedIn)
- Automatically Post on LinkedIn about business to generate sales
- Claude reasoning loop that creates Plan.md files
- One working MCP server for external action (email already done)
- Human-in-the-loop approval workflow for sensitive actions (already done)
- Basic scheduling via cron or Task Scheduler
- All AI functionality as Agent Skills

## Response snapshot

Implemented all 4 missing Silver Tier features in suggested order:

**1. Plan.md Reasoning Loop** (`silver_tier_core_autonomy/plan_loop/`)
- PlanAnalyzer: rule-based extraction of action items, goals, tags from inbox items
- PlanWriter: atomic write (tmp→rename→verify) to vault Plans/ folder
- PlanLoop: scans Inbox/ and Needs_Action/, generates Plan.md, moves to Done/
- 49 tests — all pass

**2. Scheduler** (`silver_tier_core_autonomy/scheduler/`)
- JobRegistry: register/unregister/enable/disable jobs
- SchedulerRunner: wall-clock interval tracking, force_run, run_forever with SIGINT handling
- Exponential backoff retry (max 3 retries, max 30s cooldown)
- Rate limit safety: 5 posts/hour cap
- 38 tests — all pass

**3. LinkedIn Watcher** (`golden_tier_external_world/watchers/linkedin/`)
- LinkedInWatcher extends BaseWatcher — follows Gmail watcher pattern exactly
- MockLinkedInClient + RealLinkedInClient (stub, requires Browser MCP for production)
- Seen-IDs deduplication persisted to vault (same as Gmail watcher pattern)

**4. LinkedIn Post Action** (`golden_tier_external_world/actions/linkedin/`)
- LinkedInPoster: draft → approve (HITL Tier 2) → publish lifecycle
- Rate limiting (5 posts/hour), dry_run mode, audit logging for all publishes
- 48 tests — all pass

## Outcome

- ✅ Impact: Silver Tier complete — all 4 hackathon requirements implemented as Agent Skills
- 🧪 Tests: 1115/1115 pass (135 new tests added: 49 plan loop + 38 scheduler + 48 LinkedIn)
- 📁 Files: 20 new source files, 3 new test files
- 🔁 Next prompts: Gold Tier (Facebook/Instagram integration, Odoo accounting, Twitter/X)
- 🧠 Reflection: Pattern consistency was key — LinkedIn watcher followed Gmail watcher exactly, reducing bugs. The `make_event()` signature needed `source` parameter (caught by tests). WatcherTickResult uses `events_found` not `new_event_count`.

## Evaluation notes (flywheel)

- Failure modes observed: (1) `_parse_item` monkeypatch bypassed internal try-catch — fixed by wrapping `_collect_items` loop in outer try-except. (2) Test assumed `entry["message"]` contained job_id — it contains job name. (3) `make_event()` missing `source` argument. (4) `WatcherTickResult` field is `events_found` not `new_event_count`.
- Graders run and results (PASS/FAIL): pytest tests/ — PASS (1115 passing, 0 new failures)
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): Connect PlanLoop to SchedulerRunner (register plan_loop.run as a scheduled job every 15 minutes)
