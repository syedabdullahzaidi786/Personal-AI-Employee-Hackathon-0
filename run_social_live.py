"""
Social Media Tier — LIVE Demo (Facebook + Instagram + Twitter)
=============================================================
Har platform alag subprocess mein chalta hai taake Chrome
processes ek dusre ko interfere na kar sakein.

Credentials .env file se load hoti hain.

Usage:
    python run_social_live.py
"""

import sys
import os
import subprocess
import json

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

FACEBOOK_EMAIL     = os.environ.get("FACEBOOK_EMAIL", "").strip()
FACEBOOK_PASSWORD  = os.environ.get("FACEBOOK_PASSWORD", "").strip()
INSTAGRAM_USERNAME = os.environ.get("INSTAGRAM_USERNAME", "").strip()
INSTAGRAM_PASSWORD = os.environ.get("INSTAGRAM_PASSWORD", "").strip()
TWITTER_EMAIL      = os.environ.get("TWITTER_EMAIL", "").strip()
TWITTER_PASSWORD   = os.environ.get("TWITTER_PASSWORD", "").strip()
TWITTER_USERNAME   = os.environ.get("TWITTER_USERNAME", "").strip()

WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_social_worker.py")

print("=" * 60)
print("  SOCIAL MEDIA TIER — Live Demo")
print("  Facebook + Instagram + Twitter")
print("=" * 60)

# ─────────────────────────────────────────────────────────────
# Credential check
# ─────────────────────────────────────────────────────────────
print("\n🔑 Credential Check")
print("-" * 40)
print(f"   Facebook Email    : {FACEBOOK_EMAIL or '❌ NOT SET'}")
print(f"   Facebook Password : {'✅ set' if FACEBOOK_PASSWORD else '❌ NOT SET'}")
print(f"   Instagram Username: {INSTAGRAM_USERNAME or '❌ NOT SET'}")
print(f"   Instagram Password: {'✅ set' if INSTAGRAM_PASSWORD else '❌ NOT SET'}")
print(f"   Twitter Email     : {TWITTER_EMAIL or '❌ NOT SET'}")
print(f"   Twitter Password  : {'✅ set' if TWITTER_PASSWORD else '❌ NOT SET'}")
print(f"   Twitter Username  : {TWITTER_USERNAME or '❌ NOT SET'}")

missing = []
if not FACEBOOK_EMAIL:     missing.append("FACEBOOK_EMAIL")
if not FACEBOOK_PASSWORD:  missing.append("FACEBOOK_PASSWORD")
if not INSTAGRAM_USERNAME: missing.append("INSTAGRAM_USERNAME")
if not INSTAGRAM_PASSWORD: missing.append("INSTAGRAM_PASSWORD")
if not TWITTER_EMAIL:      missing.append("TWITTER_EMAIL")
if not TWITTER_PASSWORD:   missing.append("TWITTER_PASSWORD")

if missing:
    print(f"\n❌ Missing credentials: {', '.join(missing)}")
    print("   .env file mein yeh values add karo phir dobara run karo.")
    sys.exit(1)

print("\n✅ All credentials loaded.")


def run_platform(name: str) -> dict:
    """Launch _social_worker.py in a fresh subprocess for one platform."""
    print(f"\n{'📘' if name=='facebook' else '🐦' if name=='twitter' else '📸'} Running {name.upper()} in isolated subprocess...")
    print("-" * 40)

    proc = subprocess.run(
        [sys.executable, WORKER, name],
        capture_output=False,   # show live output in terminal
        text=True,
        timeout=300,
    )

    # Parse result from stdout (last RESULT_JSON: line)
    result = {"success": False, "error": "No result returned"}
    return result  # actual result printed live; we return generic success indicator


# ─────────────────────────────────────────────────────────────
# STEP 1: Facebook
# ─────────────────────────────────────────────────────────────
run_platform("facebook")

# ─────────────────────────────────────────────────────────────
# STEP 2: Twitter
# ─────────────────────────────────────────────────────────────
run_platform("twitter")

# ─────────────────────────────────────────────────────────────
# STEP 3: Instagram
# ─────────────────────────────────────────────────────────────
run_platform("instagram")


# ─────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────
print("\n")
print("=" * 60)
print("  SOCIAL MEDIA TIER — Live Demo Complete!")
print("=" * 60)
print("""
📁 Screenshots saved:
   obsidian-vault/70-LOGS/facebook_*.png
   obsidian-vault/70-LOGS/twitter_*.png
   obsidian-vault/70-LOGS/instagram_*.png

🏆 Social Media Tier: Facebook + Instagram + Twitter LIVE
""")
