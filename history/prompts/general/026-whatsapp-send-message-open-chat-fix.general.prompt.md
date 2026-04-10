---
name: WhatsApp send_message Open Chat fix
description: Fixed send_message() to handle WhatsApp Web "Open Chat" intermediate popup before sending
type: general
stage: green
date: 2026-03-29
---

## PROMPT_TEXT

meny ye command run ki python run_whatsapp_broadcast.py ( whatsapp login bhi ho gaya message load ho gy but message send nahi ho rahy message send hony sy pehly hi brower clase ho raha hai )

## RESPONSE_TEXT

Fixed `send_message()` in `client.py`:
- Added Step 1: detect and click "Open Chat" intermediate button (4 selectors tried)
- Added Step 2: wait for message input box before attempting send
- Increased timeouts: 4s page load, 3s after open chat, 1s input wait, 2s after send
- Added 4th send button selector `compose-btn-send`

## FILES_MODIFIED

- golden_tier_external_world/watchers/whatsapp/client.py (send_message method)

## ROOT_CAUSE

WhatsApp Web `/send?phone=...` URL shows an "Open Chat" intermediate popup. Code was skipping this step and looking for Send button immediately — not found — falling through to Enter key — browser closed.
