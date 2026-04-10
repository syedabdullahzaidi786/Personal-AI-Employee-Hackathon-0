"""
Social Media Worker — runs ONE platform in isolation.
Called by run_social_live.py as a subprocess so each browser
gets a fresh Python process with no shared Chrome state.

Usage:
    python _social_worker.py facebook
    python _social_worker.py twitter
    python _social_worker.py instagram
"""

import sys
import os
import json
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

VAULT   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "obsidian-vault")
LOG_DIR = os.path.join(VAULT, "70-LOGS")

POST_CONTENT = (
    "🚀 Introducing our GIAIC Hackathon 2026 Project — Personal AI Employee! 🤖\n"
    "We built an AI agent that monitors Gmail, LinkedIn & WhatsApp, "
    "manages Odoo ERP, and posts on social media — "
    "all with Human-in-the-Loop approval. "
    "Built with Python + Playwright + Claude AI. "
    "The future of work is Human + AI collaboration! "
    "#AI #GIAIC #Hackathon #Pakistan #FutureOfWork #AIEmployee #ClaudeAI"
)

IG_CAPTION = (
    "🚀 GIAIC Hackathon 2026 — Personal AI Employee!\n"
    "AI agent that monitors Gmail, LinkedIn & WhatsApp\n"
    "and manages Odoo ERP automatically.\n"
    "Built with Python + Playwright + Claude AI 🤖\n"
    "#AI #GIAIC #Hackathon #Pakistan #FutureOfWork #AIEmployee"
)


def run_facebook():
    from golden_tier_external_world.actions.facebook.poster import PlaywrightFacebookPoster
    email    = os.environ.get("FACEBOOK_EMAIL", "").strip()
    password = os.environ.get("FACEBOOK_PASSWORD", "").strip()

    poster = PlaywrightFacebookPoster(email=email, password=password, headless=False, log_dir=LOG_DIR)
    logged_in = poster.login()
    if not logged_in:
        poster.quit()
        return {"success": False, "error": "Login failed"}

    result = poster.post(POST_CONTENT)
    poster.quit()
    return result


def run_twitter():
    from golden_tier_external_world.actions.twitter.poster import PlaywrightTwitterPoster
    email    = os.environ.get("TWITTER_EMAIL", "").strip()
    password = os.environ.get("TWITTER_PASSWORD", "").strip()
    username = os.environ.get("TWITTER_USERNAME", "").strip()

    poster = PlaywrightTwitterPoster(
        email=email, password=password, username=username,
        headless=False, log_dir=LOG_DIR,
    )
    logged_in = poster.login()
    if not logged_in:
        poster.quit()
        return {"success": False, "error": "Login failed"}

    tweet_text = POST_CONTENT[:275] + "..." if len(POST_CONTENT) > 280 else POST_CONTENT
    result = poster.tweet(tweet_text)
    poster.quit()
    return result


def run_instagram():
    from golden_tier_external_world.actions.instagram.poster import PlaywrightInstagramPoster
    username = os.environ.get("INSTAGRAM_USERNAME", "").strip()
    password = os.environ.get("INSTAGRAM_PASSWORD", "").strip()

    poster = PlaywrightInstagramPoster(username=username, password=password, headless=False, log_dir=LOG_DIR)
    logged_in = poster.login()
    if not logged_in:
        poster.quit()
        return {"success": False, "error": "Login failed"}

    result = poster.post(IG_CAPTION, image_path=None)
    poster.quit()
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "platform argument missing"}))
        sys.exit(1)

    platform = sys.argv[1].lower()

    if platform == "facebook":
        result = run_facebook()
    elif platform == "twitter":
        result = run_twitter()
    elif platform == "instagram":
        result = run_instagram()
    else:
        result = {"success": False, "error": f"Unknown platform: {platform}"}

    # Print JSON result so parent process can parse it
    print("RESULT_JSON:" + json.dumps(result))
