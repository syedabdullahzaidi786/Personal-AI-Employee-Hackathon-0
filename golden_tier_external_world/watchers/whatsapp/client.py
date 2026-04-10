"""
WHATSAPP_WATCHER_SKILL — WhatsApp Client
Phase 1: WhatsAppClient ABC, MockWhatsAppClient (test/dev), RealWhatsAppClient (Phase 2 stub).

Adapter pattern: the watcher depends only on the abstract WhatsAppClient interface.
Phase 2 will provide a concrete implementation backed by WhatsApp Business API / Twilio / etc.

Constitution compliance:
  - Principle I: Local-First — MockWhatsAppClient requires no network
  - Section 8: Credential Storage — RealWhatsAppClient accepts token parameter, never logs it
  - Principle VI: Fail Safe — health_check() never raises; fetch errors surfaced, not hidden
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from typing import Optional

from .models import (
    WhatsAppChatType,
    WhatsAppConfig,
    WhatsAppMessage,
    make_whatsapp_message,
)


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class WhatsAppClient(ABC):
    """
    Abstract contract for WhatsApp message access.

    Phase 1 uses MockWhatsAppClient.
    Phase 2 will provide RealWhatsAppClient backed by a real API adapter.
    """

    @abstractmethod
    def fetch_messages(
        self,
        max_results: int = 20,
        filter_chat_types: Optional[list[str]] = None,
        filter_senders: Optional[list[str]] = None,
    ) -> list[WhatsAppMessage]:
        """
        Return up to *max_results* unread/pending messages.

        Filters:
          filter_chat_types: only return messages from these chat types (PRIVATE/GROUP).
          filter_senders:    only return messages from these phone numbers.
        Never raises.
        """

    @abstractmethod
    def send_read_receipt(self, message_id: str) -> bool:
        """Mark a message as read. Returns True on success."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the WhatsApp API / mock is reachable. Never raises."""


# ---------------------------------------------------------------------------
# MockWhatsAppClient — deterministic, in-memory, no network
# ---------------------------------------------------------------------------

class MockWhatsAppClient(WhatsAppClient):
    """
    In-memory WhatsApp client for unit tests and local development.

    Usage::

        client = MockWhatsAppClient()
        client.inject_message(make_whatsapp_message("+14155550100", "Hello!"))
        messages = client.fetch_messages(max_results=10)
    """

    def __init__(self, healthy: bool = True) -> None:
        self._inbox:        deque[WhatsAppMessage] = deque()
        self._receipts_sent: set[str]              = set()
        self._healthy:       bool                  = healthy
        self._fetch_count:   int                   = 0

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def inject_message(self, message: WhatsAppMessage) -> None:
        """Add a message to the mock inbox."""
        self._inbox.append(message)

    def set_healthy(self, healthy: bool) -> None:
        """Flip the health state."""
        self._healthy = healthy

    def clear_inbox(self) -> None:
        """Remove all messages from the mock inbox and receipt log."""
        self._inbox.clear()
        self._receipts_sent.clear()

    @property
    def fetch_count(self) -> int:
        """Total number of fetch_messages calls made."""
        return self._fetch_count

    @property
    def inbox_size(self) -> int:
        """Number of messages currently in the mock inbox."""
        return len(self._inbox)

    @property
    def receipts_sent(self) -> set[str]:
        """Set of message IDs for which read receipts were sent."""
        return set(self._receipts_sent)

    # ------------------------------------------------------------------
    # WhatsAppClient interface
    # ------------------------------------------------------------------

    def fetch_messages(
        self,
        max_results: int = 20,
        filter_chat_types: Optional[list[str]] = None,
        filter_senders: Optional[list[str]] = None,
    ) -> list[WhatsAppMessage]:
        self._fetch_count += 1
        results: list[WhatsAppMessage] = []

        # Normalise filters to lowercase sets for comparison
        chat_filter   = {ct.lower() for ct in filter_chat_types} if filter_chat_types else None
        sender_filter = {sp.strip() for sp in filter_senders}     if filter_senders    else None

        for msg in self._inbox:
            if msg.message_id in self._receipts_sent:
                continue
            if chat_filter and msg.chat_type.lower() not in chat_filter:
                continue
            if sender_filter and msg.sender_phone not in sender_filter:
                continue
            results.append(msg)
            if len(results) >= max_results:
                break

        return results

    def send_read_receipt(self, message_id: str) -> bool:
        self._receipts_sent.add(message_id)
        return True

    def health_check(self) -> bool:
        return self._healthy


# ---------------------------------------------------------------------------
# PlaywrightWhatsAppClient — WhatsApp Web Automation (no Twilio)
# ---------------------------------------------------------------------------

class PlaywrightWhatsAppClient(WhatsAppClient):
    """
    LIVE WhatsApp client via Playwright browser automation of WhatsApp Web.

    No Twilio. No API key. Uses YOUR own WhatsApp account via WhatsApp Web.

    First run  : browser opens, QR code dikhega — phone se scan karo.
    Next runs  : session wa_session/ folder mein save hoti hai — auto-login.

    Usage::

        config = WhatsAppConfig(phone_number="self", vault_root="/vault")
        client = PlaywrightWhatsAppClient(config, session_dir="wa_session")
        client.launch()
        client.open_wa_web()      # QR scan (first time only)
        client.send_message("+923001234567", "Hello!")
        client.close()
    """

    WA_WEB_URL = "https://web.whatsapp.com"

    def __init__(
        self,
        config: WhatsAppConfig,
        session_dir: str = "wa_session",
        headless: bool = False,
    ) -> None:
        self._config      = config
        self._session_dir = session_dir
        self._headless    = headless
        self._pw          = None
        self._context     = None   # BrowserContext (persistent)
        self._page        = None
        self._ready       = False  # True after open_wa_web() succeeds

    # ------------------------------------------------------------------
    # Setup / teardown
    # ------------------------------------------------------------------

    def launch(self) -> bool:
        """
        Launch Chromium with a persistent user-data-dir so the WhatsApp Web
        session is kept between runs.  Returns True on success.  Never raises.
        """
        try:
            from pathlib import Path
            from playwright.sync_api import sync_playwright

            Path(self._session_dir).mkdir(parents=True, exist_ok=True)
            self._pw = sync_playwright().start()
            self._context = self._pw.chromium.launch_persistent_context(
                user_data_dir=self._session_dir,
                headless=self._headless,
                args=["--no-sandbox", "--window-size=1366,768"],
            )
            pages = self._context.pages
            self._page = pages[0] if pages else self._context.new_page()
            return True
        except Exception:  # noqa: BLE001
            return False

    def open_wa_web(self) -> bool:
        """
        Navigate to WhatsApp Web and wait for login.

        - If session exists  → auto-login (no QR needed, < 15 s)
        - If no session      → QR code dikhega, user scans (up to 120 s)

        Returns True when chat list is visible (logged in).  Never raises.
        """
        if self._page is None:
            return False
        try:
            self._page.goto(self.WA_WEB_URL, wait_until="domcontentloaded", timeout=30_000)

            # Wait for chat list (logged in) — or QR code element
            # Multiple selectors for different WhatsApp Web versions
            self._page.wait_for_selector(
                '[data-testid="chat-list-search"], '
                'canvas[aria-label="Scan this QR code to link a device"], '
                '[data-testid="intro-title"], '
                '#side, '
                'div[data-tab="3"]',
                timeout=60_000,
            )

            # Check if we need QR scan
            qr = self._page.locator('canvas[aria-label="Scan this QR code to link a device"]')
            if qr.count() > 0:
                print("\n   📱 QR code dikh raha hai — apne phone se WhatsApp Web scan karo")
                print("   ⏳ 120 seconds wait kar raha hoon...")
                # Wait for chat list after QR scan
                self._page.wait_for_selector(
                    '[data-testid="chat-list-search"], #side, div[data-tab="3"]',
                    timeout=120_000,
                )

            # Extra wait for full page load
            self._page.wait_for_timeout(3_000)
            self._ready = True
            return True
        except Exception as e:  # noqa: BLE001
            print(f"\n   [DEBUG] open_wa_web error: {e}")
            return False

    def close(self) -> None:
        """Close browser and stop Playwright. Never raises."""
        try:
            if self._context:
                self._context.close()
            if self._pw:
                self._pw.stop()
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    # WhatsAppClient interface
    # ------------------------------------------------------------------

    def send_message(self, to_number: str, body: str) -> bool:
        """
        Send a WhatsApp message via WhatsApp Web URL approach.

        to_number : E.164, e.g. "+923001234567"
        body      : plain text message
        Returns True on success, False on failure.  Never raises.
        """
        if not self._ready or self._page is None:
            return False
        try:
            clean = to_number.lstrip("+").replace(" ", "").replace("-", "")
            url = f"{self.WA_WEB_URL}/send?phone={clean}"
            self._page.goto(url, wait_until="domcontentloaded", timeout=30_000)

            # Step 1: Wait for WhatsApp loading screen to finish
            try:
                self._page.wait_for_selector(
                    '#side, [data-testid="chat-list-search"]',
                    timeout=60_000,
                )
            except Exception:  # noqa: BLE001
                pass  # continue anyway

            # Step 2: Wait for chat input box to be ready
            input_el = None
            for input_sel in [
                'footer div[contenteditable="true"]',
                '[data-testid="conversation-compose-box-input"]',
                'div[title="Type a message"]',
            ]:
                try:
                    self._page.wait_for_selector(input_sel, timeout=30_000)
                    input_el = self._page.locator(input_sel).first
                    break
                except Exception:  # noqa: BLE001
                    pass

            if input_el is None:
                return False

            # Snapshot outgoing message count BEFORE send — real delivery check
            msg_count_before = self._page.locator("div.message-out").count()

            # Click to focus, then type
            input_el.click()
            self._page.wait_for_timeout(500)
            input_el.type(body, delay=10)
            self._page.wait_for_timeout(500)

            # Try Send button first
            sent_via_button = False
            for sel in [
                '[data-testid="send"]',
                'button[aria-label="Send"]',
                'span[data-icon="send"]',
                'button[data-testid="compose-btn-send"]',
            ]:
                btn = self._page.locator(sel)
                if btn.count() > 0:
                    btn.first.click()
                    sent_via_button = True
                    break

            if not sent_via_button:
                # Element-bound Enter — guarantees input box is focused, not global keyboard
                input_el.press("Enter")

            # Confirm a NEW outgoing message appeared in DOM (not old ones)
            return self._wait_for_new_message(msg_count_before)

        except Exception:  # noqa: BLE001
            return False

    def _wait_for_new_message(self, count_before: int) -> bool:
        """
        Poll until a new outgoing message appears (count_before → count_before+1).
        Returns True if new message confirmed within 10 s, False otherwise.
        Never raises.
        """
        if self._page is None:
            return False
        try:
            deadline_ms  = 10_000
            poll_step_ms = 500
            elapsed      = 0
            while elapsed < deadline_ms:
                self._page.wait_for_timeout(poll_step_ms)
                elapsed += poll_step_ms
                if self._page.locator("div.message-out").count() > count_before:
                    # Extra buffer for slow internet — server delivery
                    self._page.wait_for_timeout(3_000)
                    return True
            return False
        except Exception:  # noqa: BLE001
            return False

    def fetch_messages(
        self,
        max_results: int = 20,
        filter_chat_types: Optional[list[str]] = None,
        filter_senders: Optional[list[str]] = None,
    ) -> list[WhatsAppMessage]:
        """
        Incoming message watching via WhatsApp Web DOM is complex.
        Returns empty list — watcher uses MockWhatsAppClient for tests.
        """
        return []

    def send_read_receipt(self, message_id: str) -> bool:
        """WhatsApp Web does not expose per-message read receipt API."""
        return True

    def health_check(self) -> bool:
        """True if browser is open and WhatsApp Web is loaded. Never raises."""
        try:
            return self._page is not None and not self._page.is_closed()
        except Exception:  # noqa: BLE001
            return False
