---
id: 027
title: WhatsApp False Positive Tick Fix
stage: green
date: 2026-03-29
surface: agent
model: claude-sonnet-4-6
feature: whatsapp-broadcast
branch: main
user: Syed Abdullah Zaidi
command: manual debugging session
labels: ["whatsapp", "playwright", "bugfix", "broadcast"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - golden_tier_external_world/watchers/whatsapp/client.py
tests:
  - manual: python run_whatsapp_broadcast.py --numbers "+923162233896" --message "Test message" → PASSED, message received on phone
---

## Prompt

successfully Test pass kar gaya done

(Context: WhatsApp broadcast — terminal said 3/3 SENT but messages were not arriving on phones. Debug session resumed.)

## Response snapshot

Root cause identified and fixed:
- `_wait_for_tick()` was matching existing `div.message-out` DOM elements → false positive True
- Fix: snapshot count before send, use `input_el.press("Enter")` (element-bound), poll for count increase
- Replaced `_wait_for_tick()` with `_wait_for_new_message(count_before)` that returns False if count doesn't increase in 10s

## Outcome

- ✅ Impact: WhatsApp broadcast now delivers messages to recipient phones — false positive eliminated
- 🧪 Tests: Manual test with 1 number passed — message received on phone
- 📁 Files: client.py send_message() + _wait_for_new_message() rewritten
- 🔁 Next prompts: Gold Tier full run, Platinum Tier planning
- 🧠 Reflection: DOM count snapshot before/after is the reliable pattern for confirming Playwright form submissions

## Evaluation notes (flywheel)

- Failure modes observed: _wait_for_tick() matched pre-existing DOM elements → always True regardless of actual send
- Graders run and results (PASS/FAIL): manual test PASS
- Prompt variant (if applicable): null
- Next experiment: test with 3 numbers simultaneously to confirm no race conditions
