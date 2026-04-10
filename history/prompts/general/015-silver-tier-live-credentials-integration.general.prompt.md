---
id: "015"
title: "Silver Tier Live Credentials Integration"
stage: general
date: 2026-03-19
surface: agent
model: claude-sonnet-4-6
feature: silver-tier-live
branch: main
user: operator
command: "Silver Tier implement with real Gmail + LinkedIn credentials"
labels: ["silver-tier", "gmail", "linkedin", "selenium", "imap", "credentials", "live"]
links:
  spec: "null"
  ticket: "null"
  adr: "null"
  pr: "null"
files_modified:
  - .env
  - golden_tier_external_world/watchers/gmail/client.py
  - golden_tier_external_world/watchers/linkedin/client.py
  - run_silver_live.py
tests_run:
  - Gmail IMAP health_check (import verified)
  - RealLinkedInClient import verified
  - LinkedInPoster import verified
  - All Silver Tier module imports: OK
---

## Prompt

User ne Silver Tier k liye Gmail + LinkedIn real credentials provide kiye.
- Gmail App Password (16 digit)
- LinkedIn email, password, profile URL
Request: .env structure banao, credentials fill karo, Silver Tier implement karo.

## Response

1. `.env` file banai with structure for GMAIL_ACCOUNT_EMAIL, GMAIL_APP_PASSWORD, LINKEDIN_EMAIL, LINKEDIN_PASSWORD, LINKEDIN_PROFILE_URL.
2. User ne credentials fill kiye.
3. Spaces fixed in .env values.
4. `RealGmailClient` implemented using `imaplib.IMAP4_SSL` — fetches real unread emails from Gmail inbox.
5. `RealLinkedInClient` implemented using Selenium + webdriver-manager — headless Chrome login, message scraping, notification scraping.
6. `SeleniumLinkedInBrowser` adapter created in `run_silver_live.py` to wire Selenium into `LinkedInPoster`.
7. `run_silver_live.py` created — loads .env, tests Gmail health, runs Gmail watcher tick, LinkedIn login + watcher tick + post draft/approve/publish.
8. selenium + webdriver-manager installed via pip.

## Known Issue

Gmail IMAP returning `[AUTHENTICATIONFAILED] Invalid credentials`.
Likely cause: IMAP not enabled in Gmail settings.
Fix: Gmail → Settings → See all settings → Forwarding and POP/IMAP → Enable IMAP → Save.
After enabling, run `python run_silver_live.py`.
