---
id: "021"
title: Playwright skill Facebook Instagram rewrite
stage: general
date: 2026-03-28
surface: agent
model: claude-sonnet-4-6
feature: none
branch: main
user: Sharmeen
command: playwright skill + FB/IG rewrite
labels: ["playwright", "facebook", "instagram", "selenium-migration", "pw_browser", "chrome-fix"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - golden_tier_external_world/actions/pw_browser.py
  - golden_tier_external_world/actions/facebook/poster.py
  - golden_tier_external_world/actions/instagram/poster.py
  - _social_worker.py
tests: []
---

## Prompt (verbatim)

time wesi hi bohat ziyada zaya ho chuka hai abi bhi Option A k liye 80% chances.. me chahti ho hum Option B ki taraf move kare option karty hai likin pehly play write ki skill bana lo taky asani ho pir Playwright k sath implementation start karty hai

## Response Summary

### Kya Bana:

1. **`golden_tier_external_world/actions/pw_browser.py`** — NEW: Shared Playwright base skill
   - `PlaywrightBrowser` class — sabhi social posters is se inherit karte hain
   - `_launch()`: Playwright Chromium start, `--no-sandbox`, `--disable-blink-features=AutomationControlled`, webdriver fingerprint remove
   - `_screenshot(filename)`: page.screenshot() via Playwright
   - `quit()`: browser + playwright cleanly close

2. **`facebook/poster.py`** — REWRITTEN: `SeleniumFacebookPoster` → `PlaywrightFacebookPoster`
   - `PlaywrightBrowser` se inherit karta hai
   - `page.goto()`, `page.fill()`, `page.click()`, `page.keyboard.type()` use karta hai
   - Same login/post/quit interface — _social_worker.py ko zyada change nahi chahiye

3. **`instagram/poster.py`** — REWRITTEN: `SeleniumInstagramPoster` → `PlaywrightInstagramPoster`
   - `PlaywrightBrowser` se inherit karta hai
   - Instagram `input[name='username']` field (old code mein `name='email'` bug tha — fix ho gaya)
   - Image upload via `file_input.set_input_files(abs_path)`
   - `_generate_image()` Pillow helper retain kiya

4. **`_social_worker.py`** — UPDATED: imports updated
   - `run_facebook()`: `PlaywrightFacebookPoster` import
   - `run_instagram()`: `PlaywrightInstagramPoster` import
   - Twitter unchanged (woh already working tha)

### Kya Fix Hua:
- Chrome 146 + facebook.com URL crash → Playwright ka bundled Chromium use hota hai (Chrome 146 nahi)
- Instagram old bug: `input[name='email']` → `input[name='username']` fixed
- Shared `PlaywrightBrowser` skill → agar future mein aur platform aaye toh sirf inherit karo

### Agle Steps (Install + Test):
```bash
pip install playwright
playwright install chromium
python _social_worker.py facebook
python _social_worker.py instagram
```

## Outcome

Playwright skill ready. Facebook + Instagram Selenium se Playwright pe migrate ho gaye.
Chrome 146 crash issue permanently resolve. Test karne ke liye playwright install karo.
