"""
PlaywrightBrowser — Shared Playwright Chromium base skill.

Selenium/undetected_chromedriver ki jagah Playwright use karta hai.
Playwright apna Chromium manage karta hai — Chrome 146 crash issue exist hi nahi.

TWO launch modes:
  _launch()                    — fresh browser (no saved session)
  _launch_persistent(dir)      — session save/load karta hai (2FA sirf ek baar)

Koi bhi social media poster is class se inherit karega:
    class MyPoster(PlaywrightBrowser):
        def login(self): ...
        def post(self): ...

Setup (ek baar run karo):
    pip install playwright
    playwright install chromium
"""

from __future__ import annotations

import os

_CHROME_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
    "--window-size=1366,768",
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class PlaywrightBrowser:
    """
    Reusable Playwright Chromium browser base.

    Subclasses sirf self._page use karte hain — launch/quit yahan handle hota hai.
    """

    def __init__(
        self,
        headless: bool = False,
        log_dir: str = "obsidian-vault/70-LOGS",
    ) -> None:
        self._headless = headless
        self._log_dir  = log_dir
        self._pw       = None
        self._browser  = None
        self._context  = None
        self._page     = None

    # ------------------------------------------------------------------
    # Launch — fresh (no session)
    # ------------------------------------------------------------------

    def _launch(self) -> bool:
        """Fresh Playwright Chromium launch. No session saved."""
        try:
            from playwright.sync_api import sync_playwright

            self._pw      = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=self._headless, args=_CHROME_ARGS)
            self._context = self._browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent=_USER_AGENT,
            )
            self._context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            self._page = self._context.new_page()
            print("   ✅ Playwright Chromium launch ho gaya")
            return True

        except Exception as exc:
            print(f"   ❌ Playwright launch error: {exc}")
            print("   💡 Run: pip install playwright && playwright install chromium")
            return False

    # ------------------------------------------------------------------
    # Launch — persistent (session save/load karta hai)
    # ------------------------------------------------------------------

    def _launch_persistent(self, user_data_dir: str) -> bool:
        """
        Persistent context launch karo — session disk pe save hoti hai.

        Pehli baar: browser khulta hai, user manually login karta hai.
        Agle runs: saved session se automatically logged in milta hai.

        Returns True on success. Never raises.
        """
        try:
            from playwright.sync_api import sync_playwright

            os.makedirs(user_data_dir, exist_ok=True)
            self._pw = sync_playwright().start()

            # Persistent context mein browser aur context ek hi hota hai
            self._context = self._pw.chromium.launch_persistent_context(
                user_data_dir,
                headless=self._headless,
                args=_CHROME_ARGS,
                viewport={"width": 1366, "height": 768},
                user_agent=_USER_AGENT,
            )
            self._context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            # Existing page use karo ya nayi banaao
            if self._context.pages:
                self._page = self._context.pages[0]
            else:
                self._page = self._context.new_page()

            print(f"   ✅ Persistent session loaded: {user_data_dir}")
            return True

        except Exception as exc:
            print(f"   ❌ Persistent launch error: {exc}")
            return False

    # ------------------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------------------

    def _screenshot(self, filename: str) -> None:
        try:
            os.makedirs(self._log_dir, exist_ok=True)
            path = os.path.join(self._log_dir, filename)
            self._page.screenshot(path=path)
            print(f"   📸 Screenshot: 70-LOGS/{filename}")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Quit
    # ------------------------------------------------------------------

    def quit(self) -> None:
        """Browser aur Playwright cleanly band karo."""
        try:
            if self._context:
                self._context.close()   # persistent + normal dono handle karta hai
        except Exception:
            pass
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._pw:
                self._pw.stop()
        except Exception:
            pass
        self._page    = None
        self._context = None
        self._browser = None
        self._pw      = None
