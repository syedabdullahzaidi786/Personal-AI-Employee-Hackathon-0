---
id: "020"
title: Facebook Instagram full debug session
stage: general
date: 2026-03-25
surface: agent
model: claude-sonnet-4-6
feature: none
branch: main
user: Sharmeen
command: resume + fix FB/IG crash
labels: ["facebook", "instagram", "selenium", "crash-fix", "chromedriver", "appcontainer", "subprocess"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - golden_tier_external_world/actions/facebook/poster.py
  - golden_tier_external_world/actions/instagram/poster.py
  - golden_tier_external_world/actions/twitter/poster.py
  - _social_worker.py
  - run_social_live.py
tests: []
---

## Prompt (verbatim)

history read karo or abi hum yaha sy start kary gy or jo bhi aj kaam ho sb ko history me save kar lyna
history k hisab sy hume ye kaam karna hai aj:
- ✅ Twitter — fully working
- ✅ WhatsApp + Odoo — run_gold_live.py working
- ❌ Facebook — Chrome crashes inside script (works standalone)
- ❌ Instagram — same crash pattern
tum kud run karo kud dekho pehly
abi sari history save kar lo or aj ka sara work bhi or kal ab yehi sy continue kare gy theek hai

## Response Summary

### Root Causes Found (in order of discovery):
1. **Multiple zombie Chrome processes** — 11 orphaned chrome.exe from previous test runs causing AppContainer namespace conflicts → Killed all with Python subprocess taskkill
2. **ChromeDriver version mismatch** — Chrome 146 installed but uc.Chrome() was downloading ChromeDriver 147 → Fixed with `version_main=146`
3. **AppContainer crash on fresh Chrome** — Chrome 146 crashes when `--no-sandbox` is missing → Added `--no-sandbox` to all uc.Chrome() calls
4. **Facebook URL-specific crash** — Chrome 146 crashes specifically on `www.facebook.com/login` but works on `x.com` and `google.com` → ROOT CAUSE UNRESOLVED (needs Chrome update)

### What Was Fixed:
- **Twitter**: Now works reliably with subprocess isolation + `--no-sandbox` + `version_main=146`
- **Architecture**: Created `_social_worker.py` — each platform runs in isolated subprocess
- **run_social_live.py**: Rewritten to use subprocess approach
- **Facebook post()**: Updated for www.facebook.com (not mbasic which redirects now)
- **Facebook login()**: Added `two_step_verification` URL check

### Still Failing:
- **Facebook**: Chrome 146 renderer crash on facebook.com URL (not Chrome setup, URL-specific)
- **Instagram**: Not tested (same Chrome issue expected)

### What To Try Tomorrow:
1. Update Chrome to v147 (most likely fix)
2. Playwright as alternative
3. Facebook Graph API as last resort

## Outcome

Twitter ✅ working. Facebook/Instagram ❌ Chrome 146 + facebook.com URL incompatibility.
Kal chrome update karke test karenge.
