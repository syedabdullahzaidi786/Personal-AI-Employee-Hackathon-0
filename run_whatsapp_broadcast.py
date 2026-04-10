"""
WhatsApp Broadcast Runner — Playwright WhatsApp Web
====================================================
Twilio ke baghair apne WhatsApp se multiple numbers ko ek saath message bhejo.
Browser ek baar khulega, QR scan karo (sirf pehli baar), phir session save ho ga.

.env setup:
    WA_BROADCAST_NUMBERS=+923162233896,+923001234567,+923009876543
    WA_SESSION_DIR=wa_session   (optional — default: wa_session/)

Usage:
    python run_whatsapp_broadcast.py
    python run_whatsapp_broadcast.py --message "Aaj ki meeting 3 baje hai"
    python run_whatsapp_broadcast.py --numbers "+923001234567,+923009876543"
    python run_whatsapp_broadcast.py --numbers "+923001234567" --message "Hello!"
"""

import sys
import os
import time
import argparse

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# ── Config from .env ────────────────────────────────────────────
NUMBERS_ENV = os.environ.get("WA_BROADCAST_NUMBERS", "").strip()
SESSION_DIR = os.environ.get("WA_SESSION_DIR", "wa_session").strip()
VAULT       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "obsidian-vault")


# ── Helpers ─────────────────────────────────────────────────────

def ticker(msg: str, delay: float = 0.04):
    """Character-by-character print for live feel."""
    for ch in msg:
        print(ch, end="", flush=True)
        time.sleep(delay)
    print()


def step_header(title: str):
    print()
    print("┌" + "─" * 60 + "┐")
    print(f"│  {title:<58}│")
    print("└" + "─" * 60 + "┘")


def parse_numbers(raw: str) -> list[str]:
    return [n.strip() for n in raw.split(",") if n.strip()]


# ════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="WhatsApp Broadcast — Playwright Web Automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--numbers", default="",
        help="Comma-separated E.164 numbers, e.g. +923001234567,+923009876543"
    )
    parser.add_argument(
        "--message", default="",
        help="Message to broadcast (default: demo message)"
    )
    args = parser.parse_args()

    # ── Resolve numbers ─────────────────────────────────────────
    numbers_raw = args.numbers.strip() or NUMBERS_ENV
    numbers     = parse_numbers(numbers_raw)

    # ── Resolve message ─────────────────────────────────────────
    message = args.message.strip() or (
        "Hello,\n\n"
        "This is an automated message sent on behalf of Sharmeen Fatima.\n\n"
        "I hope this message finds you well. Sharmeen wanted to reach out to you "
        "regarding the GIAIC Hackathon 2026. As part of the Personal AI Employee "
        "project, this communication has been dispatched automatically by her AI Agent.\n\n"
        "Should you have any questions or wish to get in touch, please reply directly "
        "to this message and Sharmeen will respond at her earliest convenience.\n\n"
        "Best regards,\n"
        "AI Agent — Personal AI Employee\n"
        "On behalf of Sharmeen Fatima"
    )

    # ── Header ──────────────────────────────────────────────────
    print()
    print("╔" + "═" * 60 + "╗")
    print("║   WhatsApp Broadcast — Playwright Web Automation          ║")
    print("║   Twilio-free: apne phone ka WhatsApp use hoga            ║")
    print("╚" + "═" * 60 + "╝")

    step_header("📋 BROADCAST DETAILS")

    if not numbers:
        print("   ❌ Koi number nahi mila!")
        print()
        print("   Option 1 — .env mein add karo:")
        print("      WA_BROADCAST_NUMBERS=+923001234567,+923009876543")
        print()
        print("   Option 2 — --numbers flag use karo:")
        print('      python run_whatsapp_broadcast.py --numbers "+923001234567,+923009876543"')
        sys.exit(1)

    print(f"   Numbers ({len(numbers)}):")
    for n in numbers:
        print(f"      → {n}")

    print()
    print(f"   Message preview:")
    print(f"   ┌─────────────────────────────────────────────────────┐")
    for line in message.split("\n"):
        print(f"   │ {line:<53}│")
    print(f"   └─────────────────────────────────────────────────────┘")

    print()
    print("   ⏎  Press Enter to continue, Ctrl+C to cancel...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n   Cancelled.")
        sys.exit(0)

    # ── Launch Playwright WhatsApp Client ────────────────────────
    step_header("🌐 STEP 1: WhatsApp Web Browser Launch")

    from golden_tier_external_world.watchers.whatsapp.models import WhatsAppConfig
    from golden_tier_external_world.watchers.whatsapp.client import PlaywrightWhatsAppClient

    wa_config = WhatsAppConfig(phone_number="self", vault_root=VAULT)
    client    = PlaywrightWhatsAppClient(wa_config, session_dir=SESSION_DIR)

    ticker("   🖥️  Chromium browser launch ho raha hai...")
    if not client.launch():
        print("   ❌ Browser launch failed!")
        print("   💡 Playwright install check: playwright install chromium")
        sys.exit(1)

    ticker("   📲 WhatsApp Web khul raha hai...")
    if not client.open_wa_web():
        print("   ❌ WhatsApp Web load nahi hua ya login timeout ho gaya.")
        print("   💡 Browser manually check karo aur QR scan karo.")
        client.close()
        sys.exit(1)

    ticker("   ✅ WhatsApp Web ready!")

    # ── Send to All Numbers ──────────────────────────────────────
    step_header(f"📤 STEP 2: {len(numbers)} number(s) ko message bhej raha hoon")

    sent_ok:   list[str] = []
    sent_fail: list[str] = []

    for i, number in enumerate(numbers, 1):
        print()
        ticker(f"   [{i}/{len(numbers)}] Bhej raha hoon → {number}...")
        ok = client.send_message(number, message)
        if ok:
            sent_ok.append(number)
            ticker(f"   ✅ SENT! → {number}")
        else:
            sent_fail.append(number)
            print(f"   ❌ Send failed → {number}")

        if i < len(numbers):
            time.sleep(2)   # brief pause between sends

    # ── Close Browser ────────────────────────────────────────────
    print()
    ticker("   🔒 Browser band ho raha hai...")
    client.close()

    # ── Summary ──────────────────────────────────────────────────
    print()
    print("╔" + "═" * 60 + "╗")
    print("║   WhatsApp Broadcast — Complete!                          ║")
    print("╚" + "═" * 60 + "╝")
    print()
    print(f"   ✅ Successfully sent : {len(sent_ok)}/{len(numbers)}")
    for n in sent_ok:
        print(f"      → {n}")
    if sent_fail:
        print(f"   ❌ Failed           : {len(sent_fail)}")
        for n in sent_fail:
            print(f"      → {n}")
    print()
    if sent_ok:
        print(f"   🏆 Broadcast done! {len(sent_ok)} number(s) pe message pohonch gaya.")
    else:
        print("   ⚠️  Koi message send nahi hua. Numbers aur WhatsApp Web connection check karo.")


if __name__ == "__main__":
    main()
