---
id: "019"
title: "Facebook Instagram Chrome Crash Debug"
stage: green
date: "2026-03-23"
surface: agent
model: claude-sonnet-4-6
feature: gold-tier
branch: main
user: Syed Abdullah Zaidi
command: "debug facebook instagram selenium crash"
labels: ["gold-tier", "facebook", "instagram", "selenium", "debug", "crash", "windows"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - golden_tier_external_world/actions/facebook/poster.py
  - golden_tier_external_world/actions/instagram/poster.py
  - golden_tier_external_world/actions/twitter/poster.py
  - run_social_live.py
tests:
  - python -c "from golden_tier_external_world.actions.facebook.poster import SeleniumFacebookPoster"
  - Standalone fb_test.png saved (uc + window-size only) ✅
  - Standalone fb_selenium_test.png saved (regular selenium + window-size) ✅
  - Twitter X-LIVE-DEF19694 posted LIVE ✅
---

## Prompt

debug facebook instagram selenium crash — GetHandleVerifier crash when navigating to mbasic.facebook.com and instagram.com inside run_social_live.py. Works in standalone tests but crashes in the full script.

## Response

**Root cause identified:** Linux-style Chrome flags (`--no-sandbox`, `--disable-gpu`, `--disable-dev-shm-usage`) cause Chrome renderer crashes on Windows 10. Removed all Linux flags — only `--window-size=1366,768` used now.

**Key finding:** Standalone tests confirm both sites load correctly with simplified flags. Chrome crashes only when run inside `run_social_live.py` — suspected process isolation issue (lingering chromedriver processes from previous sessions interfering).

**Changes made:**
- `facebook/poster.py`: Switched from uc → regular selenium, removed all Linux flags, added anti-bot flags only
- `instagram/poster.py`: Same — regular selenium, window-size only + anti-bot
- `twitter/poster.py`: Simplified to window-size only (removed --no-sandbox etc.)
- `run_social_live.py`: Added `import time` + `time.sleep(5)` between each platform step

**Status at session end:**
- Twitter ✅ consistently working (X-LIVE-DEF19694 confirmed)
- Facebook ❌ still crashing inside script (works standalone)
- Instagram ❌ same pattern

**Next step to try:** Kill lingering `chromedriver.exe` processes at start of each `login()` call using `taskkill /F /IM chromedriver.exe` (safe — doesn't kill user's Chrome)
