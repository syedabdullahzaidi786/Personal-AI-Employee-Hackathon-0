"""
Facebook Post Action — PlaywrightFacebookPoster

Playwright Chromium use karta hai (Selenium/undetected_chromedriver nahi).
Chrome 146 crash fix — Playwright apna bundled Chromium manage karta hai.

Workflow:
  1. login()  → Chromium kholta hai, facebook.com/login pe credentials fill karta hai
  2. post()   → Feed pe "What's on your mind?" box mein text type karke post karta hai
  3. quit()   → Browser band karta hai

Constitution compliance:
  - Principle III: HITL — caller approve karta hai post ko publish se pehle
  - Principle VI: Fail Safe — post() never raises, errors dict mein return karta hai
  - Section 8: Credentials — sirf login mein use, kabhi log nahi hoti
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from golden_tier_external_world.actions.pw_browser import PlaywrightBrowser


class PlaywrightFacebookPoster(PlaywrightBrowser):
    """
    Playwright-based Facebook poster.

    Usage::

        poster = PlaywrightFacebookPoster(
            email="user@gmail.com",
            password="secret",
            headless=False,
        )
        if poster.login():
            result = poster.post("Hello from AI Agent!")
            poster.quit()
    """

    def __init__(
        self,
        email: str,
        password: str,
        headless: bool = False,
        log_dir: str = "obsidian-vault/70-LOGS",
    ) -> None:
        super().__init__(headless=headless, log_dir=log_dir)
        self._email     = email
        self._password  = password
        self._logged_in = False

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    # Session directory — project root/obsidian-vault/browser-sessions/facebook
    _SESSION_DIR = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "..",
        "obsidian-vault", "browser-sessions", "facebook",
    )

    def login(self) -> bool:
        """
        Persistent session se login karo.

        Pehli baar:
          - Browser khulta hai, manually login karo (2FA bhi)
          - Session automatically save ho jaati hai
        Agle runs:
          - Saved session se seedha logged in — koi input nahi chahiye
        """
        import os as _os
        session_dir = _os.path.normpath(self._SESSION_DIR)

        try:
            if not self._launch_persistent(session_dir):
                return False

            page = self._page
            print("   🌐 Facebook check kar raha hai...")
            page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_timeout(3_000)

            # Logged-in check — URL nahi, actual feed element dhundo
            # (Facebook logged-out homepage ka URL bhi facebook.com/ hota hai)
            already_in = page.query_selector(
                "div[aria-label=\"What's on your mind?\"], "
                "[data-pagelet='FeedUnit_0'], "
                "[aria-label='Create post']"
            )

            if already_in:
                self._logged_in = True
                print("   ✅ Already logged in via saved session!")
                return True

            # Pehli baar — manually login karo
            print()
            print("   " + "=" * 50)
            print("   🔐 FACEBOOK — PEHLI BAAR LOGIN")
            print("   " + "=" * 50)
            print("   Browser mein Facebook khul gayi hai.")
            print("   Abhi manually login karo:")
            print("     1. Email enter karo")
            print("     2. Password enter karo")
            print("     3. 2FA code enter karo (agar aaye)")
            print("     4. Facebook feed pe pohonch jao")
            print()
            print("   ⏳ 3 minutes tak wait kar raha hoon...")
            print("   " + "=" * 50)

            # Navigate to login page
            page.goto("https://www.facebook.com/login", wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_timeout(2_000)

            # Polling loop — har 5 sec mein check karo (max 3 min)
            import time as _time
            for _ in range(36):
                _time.sleep(5)
                current = page.url
                feed_el = page.query_selector(
                    "div[aria-label=\"What's on your mind?\"], "
                    "[data-pagelet='FeedUnit_0'], "
                    "[aria-label='Create post']"
                )
                if feed_el or (
                    "facebook.com" in current
                    and "login" not in current
                    and "two_step" not in current
                    and "checkpoint" not in current
                ):
                    self._logged_in = True
                    self._screenshot("facebook_login.png")
                    print("   ✅ Login ho gayi! Session save ho gayi — agle run mein auto-login hoga.")
                    return True

            print("   ❌ 3 minutes mein login nahi hua — dobara try karo.")
            return False

        except Exception as exc:
            print(f"   ❌ Login error: {exc}")
            return False

    # ------------------------------------------------------------------
    # Post
    # ------------------------------------------------------------------

    def post(self, text: str) -> dict:
        """
        Facebook timeline pe post karo.
        Returns dict: {success, post_id, posted_at, error}
        Never raises.
        """
        if not self._logged_in or self._page is None:
            return {"success": False, "error": "Not logged in"}

        try:
            page = self._page

            print("   🌐 Facebook feed pe ja raha hai...")
            page.goto(
                "https://www.facebook.com/",
                wait_until="domcontentloaded",
                timeout=30_000,
            )
            page.wait_for_timeout(4_000)
            self._screenshot("facebook_feed.png")

            # Koi bhi popup dismiss karo (Review audience, Reels, notifications, etc.)
            for dismiss in ["button:has-text('Close')", "button:has-text('Not Now')",
                            "button:has-text('Continue')", "[aria-label='Close']"]:
                try:
                    page.click(dismiss, timeout=2_000)
                    page.wait_for_timeout(1_000)
                except Exception:
                    pass

            # "What's on your mind?" compose box click karo
            print("   ✍️  Compose box dhund raha hai...")
            compose_clicked = False

            for selector in [
                "div[aria-label=\"What's on your mind?\"]",
                "div[aria-label*='mind']",
                "span:has-text(\"What's on your mind?\")",
                "div[role='button']:has-text(\"What's on your mind\")",
            ]:
                try:
                    page.click(selector, timeout=5_000)
                    compose_clicked = True
                    print("   ✅ Compose box clicked")
                    break
                except Exception:
                    pass

            if not compose_clicked:
                self._screenshot("facebook_no_compose.png")
                return {"success": False, "error": "Compose box nahi mila"}

            page.wait_for_timeout(2_000)
            self._screenshot("facebook_composer.png")

            # Modal text area mein type karo
            print(f"   ✍️  Text type kar raha hai ({len(text)} chars)...")
            typed = False

            for selector in [
                "div[contenteditable='true'][aria-label=\"What's on your mind?\"]",
                "div[contenteditable='true'][role='textbox']",
                "div[data-lexical-editor='true']",
                "div[contenteditable='true']",
            ]:
                try:
                    page.click(selector, timeout=3_000)
                    page.keyboard.type(text, delay=25)
                    typed = True
                    break
                except Exception:
                    pass

            if not typed:
                self._screenshot("facebook_no_textarea.png")
                return {"success": False, "error": "Text area nahi mila"}

            page.wait_for_timeout(2_000)
            self._screenshot("facebook_typed.png")

            # "Post" button click karo
            print("   🚀 Post button dhund raha hai...")
            posted = False

            for selector in [
                "div[aria-label='Post'][role='button']",
                "div[role='button']:has-text('Post')",
                "button:has-text('Post')",
            ]:
                try:
                    page.click(selector, timeout=5_000)
                    posted = True
                    print("   ✅ Post button clicked!")
                    break
                except Exception:
                    pass

            if not posted:
                self._screenshot("facebook_no_post_btn.png")
                return {"success": False, "error": "Post button nahi mila"}

            page.wait_for_timeout(5_000)
            self._screenshot("facebook_posted.png")

            post_id = f"FB-LIVE-{uuid.uuid4().hex[:8].upper()}"
            print(f"   🚀 Facebook post ho gayi! ID: {post_id}")
            return {
                "success": True,
                "post_id": post_id,
                "posted_at": datetime.now(tz=timezone.utc).isoformat(),
                "error": "",
            }

        except Exception as exc:
            return {"success": False, "error": f"{type(exc).__name__}: {exc}"}
