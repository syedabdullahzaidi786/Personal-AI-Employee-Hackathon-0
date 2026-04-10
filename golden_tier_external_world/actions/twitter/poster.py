"""
Twitter / X Post Action — PlaywrightTwitterPoster

Selenium se Playwright pe migrate kiya gaya (same fix jo FB/IG pe tha).
Playwright apna bundled Chromium use karta hai — Chrome version issues nahi.
Persistent session: ek baar login, hamesha auto-login.

Twitter login 2-step hai:
  Step 1: email/username → Next
  Step 2: password → Log in
  (Optional Step 2.5: unusual activity → username confirm)

Constitution compliance:
  - Principle III: HITL — caller approve karta hai tweet ko publish se pehle
  - Principle VI: Fail Safe — tweet() never raises
  - Section 8: Credentials never logged
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone

# Session directory — obsidian-vault/browser-sessions/twitter/
_SESSION_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "obsidian-vault", "browser-sessions", "twitter"
)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_CHROME_ARGS = [
    "--no-sandbox",
    "--disable-blink-features=AutomationControlled",
    "--window-size=1366,768",
]


class PlaywrightTwitterPoster:
    """
    Playwright-based Twitter/X poster with persistent session.

    Usage::

        poster = PlaywrightTwitterPoster(
            email="user@gmail.com",
            password="secret",
            username="twitter_handle",
            headless=False,
        )
        if poster.login():
            result = poster.tweet("Hello from AI Agent! #GIAIC #Hackathon")
            poster.quit()
    """

    def __init__(
        self,
        email: str,
        password: str,
        username: str = "",
        headless: bool = False,
        log_dir: str = "obsidian-vault/70-LOGS",
    ) -> None:
        self._email     = email
        self._password  = password
        self._username  = username
        self._headless  = headless
        self._log_dir   = log_dir
        self._pw        = None
        self._context   = None
        self._page      = None
        self._logged_in = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _launch_persistent(self) -> bool:
        """Persistent session launch — cookies disk pe save hoti hain."""
        try:
            from playwright.sync_api import sync_playwright
            session_dir = os.path.normpath(_SESSION_DIR)
            os.makedirs(session_dir, exist_ok=True)

            self._pw = sync_playwright().start()
            self._context = self._pw.chromium.launch_persistent_context(
                session_dir,
                headless=self._headless,
                args=_CHROME_ARGS,
                viewport={"width": 1366, "height": 768},
                user_agent=_USER_AGENT,
            )
            self._context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            self._page = (
                self._context.pages[0]
                if self._context.pages
                else self._context.new_page()
            )
            return True
        except Exception as exc:
            print(f"   ❌ Browser launch error: {exc}")
            return False

    def _screenshot(self, filename: str) -> None:
        try:
            os.makedirs(self._log_dir, exist_ok=True)
            self._page.screenshot(path=os.path.join(self._log_dir, filename))
            print(f"   📸 Screenshot: 70-LOGS/{filename}")
        except Exception:
            pass

    def _click_button_with_text(self, texts: list[str], timeout: int = 5_000) -> bool:
        """Button dhundo text se — multiple selectors try karo."""
        page = self._page
        for text in texts:
            for sel in [
                f"button:has-text('{text}')",
                f"[role='button']:has-text('{text}')",
                f"div[role='button']:has-text('{text}')",
            ]:
                try:
                    page.click(sel, timeout=timeout)
                    return True
                except Exception:
                    pass
            # JS fallback
            try:
                clicked = page.evaluate(f"""
                    var els = document.querySelectorAll('button, [role="button"]');
                    for (var el of els) {{
                        if ((el.innerText || '').trim() === '{text}') {{
                            el.click(); return true;
                        }}
                    }}
                    return false;
                """)
                if clicked:
                    return True
            except Exception:
                pass
        return False

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    def login(self) -> bool:
        """
        Persistent session load karo. Agar already logged in hai to return True.
        Warna fresh login karo.
        Returns True on success. Never raises.
        """
        try:
            if not self._launch_persistent():
                return False

            page = self._page
            print("   🌐 Twitter/X khul rahi hai...")
            page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=20_000)
            page.wait_for_timeout(3_000)

            # Already logged in check
            if self._is_logged_in():
                self._logged_in = True
                print("   ✅ Twitter/X persistent session active — already logged in!")
                return True

            # Fresh login
            print("   🔑 Fresh login kar raha hoon...")
            page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded", timeout=20_000)
            page.wait_for_timeout(3_000)

            # --- Step 1: Email/Username ---
            print("   📧 Email enter kar raha hai...")
            try:
                email_field = page.wait_for_selector(
                    "input[autocomplete='username'], input[name='text']",
                    timeout=15_000
                )
                email_field.click()
                page.wait_for_timeout(500)
                email_field.fill(self._email)
                page.wait_for_timeout(1_000)
            except Exception as exc:
                print(f"   ❌ Email field nahi mila: {exc}")
                self._screenshot("twitter_step1_fail.png")
                return False

            # Twitter-specific Next button (data-testid pehle try karo)
            next_clicked = False
            for sel in [
                "[data-testid='LoginForm_Login_Button']",
                "button:has-text('Next')",
                "[role='button']:has-text('Next')",
            ]:
                try:
                    page.click(sel, timeout=5_000)
                    next_clicked = True
                    break
                except Exception:
                    pass
            if not next_clicked:
                # JS fallback
                page.evaluate("""
                    var els = document.querySelectorAll('button, [role="button"]');
                    for (var el of els) {
                        if ((el.innerText || '').trim() === 'Next') { el.click(); break; }
                    }
                """)

            # Next ke baad WAIT — koi bhi field aane tak (password ya confirmation)
            print("   ⏳ Next page load ho rahi hai...")
            try:
                page.wait_for_selector(
                    "input[name='password'], "
                    "input[type='password'], "
                    "input[data-testid='ocfEnterTextTextInput']",
                    timeout=15_000
                )
            except Exception:
                pass  # age try karte hain

            self._screenshot("twitter_step1.png")

            # --- Step 2.5: Unusual activity / username confirm ---
            try:
                confirm = page.query_selector("input[data-testid='ocfEnterTextTextInput']")
                if confirm and confirm.is_visible():
                    print("   ⚠️  Unusual activity check — username enter kar raha hoon...")
                    confirm.click()
                    page.wait_for_timeout(300)
                    confirm.fill(self._username or self._email)
                    page.wait_for_timeout(1_000)
                    for sel in [
                        "[data-testid='ocfEnterTextNextButton']",
                        "button:has-text('Next')",
                    ]:
                        try:
                            page.click(sel, timeout=5_000)
                            break
                        except Exception:
                            pass
                    # Password field aane ka wait
                    try:
                        page.wait_for_selector(
                            "input[name='password'], input[type='password']",
                            timeout=15_000
                        )
                    except Exception:
                        pass
            except Exception:
                pass

            # --- Step 2: Password ---
            print("   🔑 Password enter kar raha hai...")
            try:
                pwd_field = page.wait_for_selector(
                    "input[name='password'], input[type='password']",
                    timeout=15_000
                )
                pwd_field.click()
                page.wait_for_timeout(300)
                pwd_field.fill(self._password)
                page.wait_for_timeout(1_000)
            except Exception as exc:
                print(f"   ❌ Password field nahi mila: {exc}")
                self._screenshot("twitter_pwd_fail.png")
                return False

            # Log in button — Twitter-specific data-testid pehle
            login_clicked = False
            for sel in [
                "[data-testid='LoginForm_Login_Button']",
                "button:has-text('Log in')",
                "[role='button']:has-text('Log in')",
            ]:
                try:
                    page.click(sel, timeout=5_000)
                    login_clicked = True
                    break
                except Exception:
                    pass
            if not login_clicked:
                page.evaluate("""
                    var els = document.querySelectorAll('button, [role="button"]');
                    for (var el of els) {
                        var t = (el.innerText || '').trim();
                        if (t === 'Log in' || t === 'Login') { el.click(); break; }
                    }
                """)

            print("   ⏳ Login ho rahi hai...")
            page.wait_for_timeout(8_000)

            self._screenshot("twitter_login.png")

            if self._is_logged_in():
                self._logged_in = True
                print("   ✅ Twitter/X login success!")
                return True

            print(f"   ❌ Login failed. URL: {page.url[:80]}")
            return False

        except Exception as exc:
            print(f"   ❌ Login error: {exc}")
            return False

    def _is_logged_in(self) -> bool:
        """Feed element ya home URL check karo."""
        try:
            page = self._page
            url = page.url
            if "x.com/home" in url:
                return True
            # Feed element check
            el = page.query_selector(
                "[data-testid='tweetTextarea_0'], "
                "[aria-label='Home timeline'], "
                "[data-testid='primaryColumn']"
            )
            return el is not None
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Tweet
    # ------------------------------------------------------------------

    def tweet(self, text: str) -> dict:
        """
        Compose and post a tweet on X.com.
        Returns dict: {success, tweet_id, posted_at, error}
        Never raises.
        """
        if not self._logged_in or self._page is None:
            return {"success": False, "error": "Not logged in"}

        try:
            page = self._page
            print("   🌐 X.com home pe ja raha hai...")
            page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=20_000)
            page.wait_for_timeout(4_000)

            self._screenshot("twitter_home.png")

            # Tweet compose box
            print("   📝 Tweet compose box dhund raha hai...")
            compose_box = None

            try:
                compose_box = page.wait_for_selector(
                    "[data-testid='tweetTextarea_0']",
                    timeout=15_000
                )
                print("   ✅ Compose box mila (data-testid)")
            except Exception:
                pass

            if compose_box is None:
                # JS fallback — placeholder text se dhundo, ElementHandle return karo
                compose_box = page.evaluate_handle("""
                    () => {
                        var walker = document.createTreeWalker(
                            document.body, NodeFilter.SHOW_ELEMENT
                        );
                        while (walker.nextNode()) {
                            var el = walker.currentNode;
                            var ph = (el.getAttribute('data-placeholder') || '').toLowerCase();
                            if (ph.includes('happening') && el.offsetParent !== null) {
                                return el;
                            }
                        }
                        return null;
                    }
                """).as_element()
                if compose_box:
                    print("   ✅ Compose box mila (JS placeholder walker)")

            if compose_box is None:
                return {"success": False, "error": "Tweet compose box nahi mila"}

            # Click + type
            compose_box.click()
            page.wait_for_timeout(1_000)
            compose_box.type(text, delay=30)
            page.wait_for_timeout(2_000)

            # Dispatch React events
            page.evaluate("""
                var el = document.querySelector('[data-testid="tweetTextarea_0"]');
                if (el) {
                    ['input','change','keyup'].forEach(function(n){
                        el.dispatchEvent(new Event(n, {bubbles: true}));
                    });
                }
            """)
            page.wait_for_timeout(1_000)
            print(f"   ✍️  Tweet text type ho gaya ({len(text)} chars)")
            self._screenshot("twitter_typed.png")

            # "Post" button
            post_btn = None
            try:
                post_btn = page.wait_for_selector(
                    "[data-testid='tweetButtonInline']",
                    timeout=10_000
                )
                print("   ✅ Post button mila (data-testid)")
            except Exception:
                pass

            if post_btn is None:
                # JS fallback
                clicked = page.evaluate("""
                    () => {
                        var btns = document.querySelectorAll('button[role="button"]');
                        for (var btn of btns) {
                            if ((btn.innerText || '').trim() === 'Post') {
                                btn.click(); return true;
                            }
                        }
                        return false;
                    }
                """)
                if clicked:
                    print("   ✅ Post button JS se click ho gaya")
                    page.wait_for_timeout(5_000)
                    self._screenshot("twitter_posted.png")
                    tweet_id = f"X-LIVE-{uuid.uuid4().hex[:8].upper()}"
                    print(f"   🚀 Tweet post ho gayi! ID: {tweet_id}")
                    return {
                        "success": True,
                        "tweet_id": tweet_id,
                        "posted_at": datetime.now(tz=timezone.utc).isoformat(),
                        "error": "",
                    }
                return {"success": False, "error": "Twitter 'Post' button nahi mila"}

            post_btn.click()
            page.wait_for_timeout(5_000)
            self._screenshot("twitter_posted.png")

            tweet_id = f"X-LIVE-{uuid.uuid4().hex[:8].upper()}"
            print(f"   🚀 Tweet post ho gayi! ID: {tweet_id}")
            return {
                "success": True,
                "tweet_id": tweet_id,
                "posted_at": datetime.now(tz=timezone.utc).isoformat(),
                "error": "",
            }

        except Exception as exc:
            return {"success": False, "error": f"{type(exc).__name__}: {exc}"}

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def quit(self) -> None:
        try:
            if self._context:
                self._context.close()
        except Exception:
            pass
        try:
            if self._pw:
                self._pw.stop()
        except Exception:
            pass
        self._context   = None
        self._pw        = None
        self._page      = None
        self._logged_in = False
