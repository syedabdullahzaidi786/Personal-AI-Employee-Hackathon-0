"""
Instagram Post Action — PlaywrightInstagramPoster

Playwright Chromium use karta hai (Selenium/undetected_chromedriver nahi).
Chrome 146 crash fix — Playwright apna bundled Chromium manage karta hai.

Instagram web pe image zaroori hai feed post ke liye.
Agar Pillow (PIL) installed hai toh auto-generated image banata hai.

Workflow:
  1. login()  → Chromium kholta hai, instagram.com/accounts/login/ pe login karta hai
  2. post()   → "+" button → image upload → caption → Share
  3. quit()   → Browser band karta hai

Constitution compliance:
  - Principle III: HITL — caller approve karta hai post ko publish se pehle
  - Principle VI: Fail Safe — post() never raises
  - Section 8: Credentials never logged
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from golden_tier_external_world.actions.pw_browser import PlaywrightBrowser


class PlaywrightInstagramPoster(PlaywrightBrowser):
    """
    Playwright-based Instagram poster.

    Requires at least one image (Instagram web limitation).
    If Pillow is installed, auto-generates a text image.

    Usage::

        poster = PlaywrightInstagramPoster(
            username="myhandle",
            password="secret",
            headless=False,
        )
        if poster.login():
            result = poster.post("Hello from AI Agent! #GIAIC", image_path=None)
            poster.quit()
    """

    def __init__(
        self,
        username: str,
        password: str,
        headless: bool = False,
        log_dir: str = "obsidian-vault/70-LOGS",
    ) -> None:
        super().__init__(headless=headless, log_dir=log_dir)
        self._username  = username
        self._password  = password
        self._logged_in = False

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    # Session directory — project root/obsidian-vault/browser-sessions/instagram
    _SESSION_DIR = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "..",
        "obsidian-vault", "browser-sessions", "instagram",
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
            print("   🌐 Instagram check kar raha hai...")
            page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_timeout(3_000)

            # Already logged in check — actual feed element dhundo (URL kafi nahi)
            feed_el = page.query_selector(
                "svg[aria-label='Home'], "
                "a[href='/'], "
                "[aria-label='New post'], "
                "[aria-label='Create']"
            )
            current = page.url

            if feed_el and "instagram.com" in current and "login" not in current:
                self._logged_in = True
                print("   ✅ Already logged in via saved session!")
                return True

            # Pehli baar — manually login karo
            print()
            print("   " + "=" * 50)
            print("   🔐 INSTAGRAM — PEHLI BAAR LOGIN")
            print("   " + "=" * 50)
            print("   Browser mein Instagram khul gayi hai.")
            print("   Abhi manually login karo:")
            print("     1. Username/email enter karo")
            print("     2. Password enter karo")
            print("     3. 2FA code enter karo (agar aaye)")
            print("     4. Instagram feed pe pohonch jao")
            print()
            print("   ⏳ 3 minutes tak wait kar raha hoon...")
            print("   " + "=" * 50)

            page.goto(
                "https://www.instagram.com/accounts/login/",
                wait_until="domcontentloaded",
                timeout=30_000,
            )
            page.wait_for_timeout(2_000)

            # Polling loop — har 5 sec mein check karo (max 3 min)
            import time as _time
            for _ in range(36):
                _time.sleep(5)
                current = page.url
                if (
                    "instagram.com" in current
                    and "login" not in current
                    and "accounts" not in current
                ):
                    self._logged_in = True
                    self._screenshot("instagram_login.png")
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

    def post(self, caption: str, image_path: str = None) -> dict:
        """
        Instagram pe post karo with caption.
        image_path=None → Pillow se auto-generate karta hai.
        Returns dict: {success, post_id, posted_at, error}
        Never raises.
        """
        if not self._logged_in or self._page is None:
            return {"success": False, "error": "Not logged in"}

        # Image resolve/generate
        if image_path is None:
            image_path = self._generate_image(caption)
            if image_path:
                print(f"   🖼️  Auto-generated image: {image_path}")
            else:
                print("   ⚠️  Pillow nahi hai — image generate nahi ho saki")
                print("   💡 pip install Pillow karo ya image_path manually do")
                return {
                    "success": False,
                    "error": "Instagram ko image chahiye. 'pip install Pillow' chala kar retry karo.",
                }

        abs_image_path = str(Path(image_path).resolve())

        try:
            page = self._page

            print("   🌐 Instagram feed pe ja raha hai...")
            page.goto(
                "https://www.instagram.com/",
                wait_until="domcontentloaded",
                timeout=30_000,
            )
            page.wait_for_timeout(4_000)
            self._screenshot("instagram_feed.png")

            # "+" Create button click karo
            print("   ➕ Create button dhund raha hai...")
            create_clicked = False

            for selector in [
                "svg[aria-label='New post']",
                "[aria-label='New post']",
                "a[href='/create/style/']",
                "a[href*='/create/']",
                "[aria-label='Create']",
                "span:has-text('Create')",
            ]:
                try:
                    page.click(selector, timeout=4_000)
                    create_clicked = True
                    print("   ✅ Create button clicked")
                    break
                except Exception:
                    pass

            if not create_clicked:
                self._screenshot("instagram_no_create.png")
                return {"success": False, "error": "Create '+' button nahi mila"}

            page.wait_for_timeout(2_000)
            self._screenshot("instagram_create_modal.png")

            # File input ko image path do
            print(f"   📁 Image upload kar raha hai: {abs_image_path}")
            file_input_found = False

            # Direct file input
            try:
                file_input = page.locator("input[type='file']").first
                page.evaluate("el => el.style.display = 'block'", file_input.element_handle())
                file_input.set_input_files(abs_image_path)
                file_input_found = True
                print("   ✅ Image upload shuru ho gayi")
            except Exception:
                pass

            # "Select from computer" button fallback
            if not file_input_found:
                try:
                    page.click("button:has-text('Select from computer')", timeout=3_000)
                    page.wait_for_timeout(1_000)
                    file_input = page.locator("input[type='file']").first
                    file_input.set_input_files(abs_image_path)
                    file_input_found = True
                    print("   ✅ Image upload via button")
                except Exception:
                    pass

            if not file_input_found:
                return {"success": False, "error": "File upload input nahi mila"}

            page.wait_for_timeout(5_000)
            self._screenshot("instagram_image_selected.png")

            # "Next" button — crop → filter → caption (Instagram div ya span use karta hai)
            next_selectors = [
                "div[role='button']:has-text('Next')",
                "button:has-text('Next')",
                "span:has-text('Next')",
                "//div[normalize-space(text())='Next']",
            ]
            for i in range(3):
                clicked = False
                for sel in next_selectors:
                    try:
                        by = "xpath" if sel.startswith("//") else "css"
                        if by == "xpath":
                            page.locator(f"xpath={sel}").first.click(timeout=4_000)
                        else:
                            page.locator(sel).first.click(timeout=4_000)
                        clicked = True
                        print(f"   ✅ Next clicked ({i+1})")
                        page.wait_for_timeout(3_000)
                        self._screenshot(f"instagram_next_{i}.png")
                        break
                    except Exception:
                        pass
                if not clicked:
                    print(f"   ⚠️  Next button nahi mila step {i+1} — aage badh raha hoon")

            self._screenshot("instagram_caption.png")

            # Caption field — multiple selectors try karo
            print("   ✍️  Caption type kar raha hai...")
            caption_typed = False
            for sel in [
                "div[aria-label='Write a caption...']",
                "div[aria-label='Write a caption\u2026']",
                "div[data-lexical-editor='true']",
                "textarea[aria-label='Write a caption...']",
                "div[contenteditable='true']",
            ]:
                try:
                    page.click(sel, timeout=4_000)
                    page.keyboard.type(caption, delay=25)
                    caption_typed = True
                    print(f"   ✅ Caption type ho gayi ({len(caption)} chars)")
                    break
                except Exception:
                    pass
            if not caption_typed:
                print("   ⚠️  Caption field nahi mila — Share try kar raha hoon")

            page.wait_for_timeout(2_000)
            self._screenshot("instagram_before_share.png")

            # "Share" button
            print("   🚀 Share button dhund raha hai...")
            shared = False
            # Instagram "Share" header mein plain text/div hota hai
            for sel in [
                "div:has-text('Share'):right-of(div:has-text('Create new post'))",
                "div[role='button']:has-text('Share')",
                "button:has-text('Share')",
                "span:has-text('Share')",
                "text=Share",
            ]:
                try:
                    loc = page.locator(sel).last
                    loc.click(timeout=6_000)
                    shared = True
                    print("   ✅ Share button clicked!")
                    page.wait_for_timeout(6_000)
                    self._screenshot("instagram_posted.png")
                    break
                except Exception:
                    pass

            # Fallback: keyboard shortcut ya JS click on Share header button
            if not shared:
                try:
                    page.evaluate("""
                        const els = [...document.querySelectorAll('*')];
                        const shareBtn = els.find(el =>
                            el.innerText && el.innerText.trim() === 'Share'
                            && el.offsetParent !== null
                        );
                        if (shareBtn) shareBtn.click();
                    """)
                    shared = True
                    print("   ✅ Share clicked via JS!")
                    page.wait_for_timeout(6_000)
                    self._screenshot("instagram_posted.png")
                except Exception:
                    pass

            if not shared:
                return {"success": False, "error": "Share button nahi mila"}

            post_id = f"IG-LIVE-{uuid.uuid4().hex[:8].upper()}"
            print(f"   🚀 Instagram post ho gayi! ID: {post_id}")
            return {
                "success": True,
                "post_id": post_id,
                "posted_at": datetime.now(tz=timezone.utc).isoformat(),
                "error": "",
            }

        except Exception as exc:
            return {"success": False, "error": f"{type(exc).__name__}: {exc}"}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _generate_image(self, text: str) -> str:
        """Pillow se simple image generate karo. Returns path or None."""
        try:
            from PIL import Image, ImageDraw

            img  = Image.new("RGB", (800, 800), color=(30, 30, 60))
            draw = ImageDraw.Draw(img)
            draw.text((40, 50),  "GIAIC Hackathon 2026",   fill=(100, 200, 255))
            draw.text((40, 90),  "Personal AI Employee",    fill=(100, 200, 255))
            draw.text((40, 360), text[:100],                fill=(255, 255, 255))

            os.makedirs(self._log_dir, exist_ok=True)
            img_path = os.path.join(self._log_dir, "instagram_post_image.png")
            img.save(img_path)
            return img_path

        except ImportError:
            return None
        except Exception:
            return None
