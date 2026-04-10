---
id: "016"
title: "Gmail SMTP Auto-Send Integration"
stage: general
date: 2026-03-20
surface: agent
model: claude-sonnet-4-6
feature: silver-tier
branch: main
user: syedabdullahzaidi
command: "gmail smtp auto-send like linkedin"
labels: ["gmail", "smtp", "auto-send", "silver-tier", "email-action"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - golden_tier_external_world/actions/email/adapter.py
  - run_silver_live.py
  - .env
tests: []
---

## Prompt

history read karo or linkdin complete hogaya hai meny test bhi kar liya hai ab gmail sy emails jani chahiye jin ko me share karo pehly me gmail address do k in ko email baj do or pir automatic jisy linkdin par post hoi wesy hi gmail send ho jai.

## Response

Implemented Gmail SMTP auto-send feature (STEP 4) mirroring LinkedIn auto-post flow:

1. **`RealEmailAdapter.send()`** — implemented using `smtplib` + Gmail SMTP (smtp.gmail.com:587 STARTTLS + App Password). Previously a stub raising `NotImplementedError`.

2. **`RealEmailAdapter.health_check()`** — SMTP login test, same pattern as `RealGmailClient.health_check()`.

3. **`run_silver_live.py` STEP 4** — Added Gmail Auto-Send step:
   - Draft email with same content as LinkedIn post
   - Simulated HITL approval (like LinkedIn)
   - Send via Gmail SMTP to `EMAIL_RECIPIENTS`
   - Result logged in summary

4. **`.env`** — Added `EMAIL_RECIPIENTS` field (comma-separated, placeholder — user must fill in).

## Outcome

- User must fill `EMAIL_RECIPIENTS=email1@gmail.com,email2@gmail.com` in `.env`
- Then run: `python run_silver_live.py`
- STEP 4 will send email automatically after HITL approval
