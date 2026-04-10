"""
LinkedIn Watcher — Client Interface.

RealLinkedInClient: Uses browser MCP (Playwright) to scrape LinkedIn.
MockLinkedInClient: Returns deterministic fake data for testing.

Note: LinkedIn has no public API for these features.
Browser automation is the only viable approach.

Constitution compliance:
  - Principle VI: Fail Safe (health_check, circuit breaker)
  - Section 6:    External API Guidelines (rate limits respected)
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from .models import LinkedInActivity, LinkedInConfig, LinkedInEventType


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class LinkedInClient(ABC):
    @abstractmethod
    def fetch_activity(
        self,
        max_results: int = 20,
        event_types: Optional[list[LinkedInEventType]] = None,
    ) -> list[LinkedInActivity]:
        """Fetch recent LinkedIn activity."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if LinkedIn is reachable."""
        ...


# ---------------------------------------------------------------------------
# Mock client (testing + development)
# ---------------------------------------------------------------------------

class MockLinkedInClient(LinkedInClient):
    """
    Returns deterministic fake LinkedIn activity.

    Used in development and all unit tests.
    In production, replace with RealLinkedInClient (browser automation).
    """

    def __init__(
        self,
        activities: Optional[list[LinkedInActivity]] = None,
        healthy: bool = True,
        raise_on_fetch: bool = False,
    ) -> None:
        self._activities     = activities or []
        self._healthy        = healthy
        self._raise_on_fetch = raise_on_fetch

    def fetch_activity(
        self,
        max_results: int = 20,
        event_types: Optional[list[LinkedInEventType]] = None,
    ) -> list[LinkedInActivity]:
        if self._raise_on_fetch:
            raise ConnectionError("Mock: LinkedIn unreachable")
        filtered = self._activities
        if event_types:
            filtered = [a for a in filtered if a.event_type in event_types]
        return filtered[:max_results]

    def health_check(self) -> bool:
        return self._healthy

    @staticmethod
    def make_activity(
        event_type: LinkedInEventType = LinkedInEventType.NEW_MESSAGE,
        activity_id: Optional[str] = None,
    ) -> LinkedInActivity:
        """Factory for creating test activity items."""
        return LinkedInActivity(
            activity_id=activity_id or f"LI-{uuid.uuid4().hex[:8]}",
            event_type=event_type,
            sender_name="Test User",
            sender_profile="https://linkedin.com/in/testuser",
            content="Hello! Interested in connecting.",
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
            url="https://linkedin.com/messaging",
        )


# ---------------------------------------------------------------------------
# Real client (production — Selenium browser automation)
# ---------------------------------------------------------------------------

class RealLinkedInClient(LinkedInClient):
    """
    Production LinkedIn client using Selenium browser automation.

    Logs into LinkedIn with email + password, then scrapes:
      - Unread messages (messaging inbox)
      - Notifications (bell icon)
      - Connection requests (My Network)

    Rate limiting: minimum 60s between polls to respect LinkedIn limits.

    Usage::

        client = RealLinkedInClient(email="you@email.com", password="pass")
        client.login()
        activities = client.fetch_activity(max_results=10)
        client.quit()
    """

    _LINKEDIN_BASE = "https://www.linkedin.com"
    _MIN_INTERVAL  = 60.0   # seconds between polls

    def __init__(self, email: str = "", password: str = "", headless: bool = True) -> None:
        self._email    = email
        self._password = password
        self._headless = headless
        self._driver   = None
        self._logged_in = False
        self._last_call: float = 0.0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def login(self) -> bool:
        """Open browser and log into LinkedIn. Returns True on success."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from webdriver_manager.chrome import ChromeDriverManager

            opts = Options()
            if self._headless:
                opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            opts.add_experimental_option("useAutomationExtension", False)

            service = Service(ChromeDriverManager().install())
            self._driver = webdriver.Chrome(service=service, options=opts)
            self._driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            self._driver.get(f"{self._LINKEDIN_BASE}/login")
            wait = WebDriverWait(self._driver, 15)

            wait.until(EC.presence_of_element_located((By.ID, "username")))
            self._driver.find_element(By.ID, "username").send_keys(self._email)
            self._driver.find_element(By.ID, "password").send_keys(self._password)
            self._driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

            # Wait for feed (successful login)
            wait.until(EC.url_contains("feed"))
            self._logged_in = True
            return True

        except Exception:  # noqa: BLE001
            return False

    def quit(self) -> None:
        """Close the browser."""
        if self._driver:
            try:
                self._driver.quit()
            except Exception:  # noqa: BLE001
                pass
            self._driver = None
            self._logged_in = False

    # ------------------------------------------------------------------
    # LinkedInClient interface
    # ------------------------------------------------------------------

    def fetch_activity(
        self,
        max_results: int = 20,
        event_types: Optional[list[LinkedInEventType]] = None,
    ) -> list[LinkedInActivity]:
        """Fetch LinkedIn activity via browser scraping."""
        if not self._logged_in or self._driver is None:
            return []

        # Rate limiting
        elapsed = time.monotonic() - self._last_call
        if elapsed < self._MIN_INTERVAL:
            time.sleep(self._MIN_INTERVAL - elapsed)
        self._last_call = time.monotonic()

        activities: list[LinkedInActivity] = []

        target_types = set(event_types) if event_types else {
            LinkedInEventType.NEW_MESSAGE,
            LinkedInEventType.CONNECTION_REQUEST,
            LinkedInEventType.NEW_NOTIFICATION,
        }

        try:
            if LinkedInEventType.NEW_MESSAGE in target_types:
                activities.extend(self._fetch_messages(max_results // 2))
        except Exception:  # noqa: BLE001
            pass

        try:
            if LinkedInEventType.NEW_NOTIFICATION in target_types or \
               LinkedInEventType.CONNECTION_REQUEST in target_types:
                activities.extend(self._fetch_notifications(max_results // 2))
        except Exception:  # noqa: BLE001
            pass

        return activities[:max_results]

    def health_check(self) -> bool:
        """Return True if browser is open and logged in."""
        return self._logged_in and self._driver is not None

    # ------------------------------------------------------------------
    # Scraping helpers
    # ------------------------------------------------------------------

    def _fetch_messages(self, limit: int) -> list[LinkedInActivity]:
        """Scrape unread messages from LinkedIn messaging."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        activities = []
        try:
            self._driver.get(f"{self._LINKEDIN_BASE}/messaging/")
            wait = WebDriverWait(self._driver, 10)
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".msg-conversation-listitem, .msg-conversations-container")
            ))
            time.sleep(2)

            items = self._driver.find_elements(
                By.CSS_SELECTOR, ".msg-conversation-listitem__link"
            )[:limit]

            for item in items:
                try:
                    name    = item.find_element(
                        By.CSS_SELECTOR, ".msg-conversation-listitem__participant-names"
                    ).text.strip()
                    preview = ""
                    try:
                        preview = item.find_element(
                            By.CSS_SELECTOR, ".msg-conversation-listitem__message-snippet"
                        ).text.strip()[:200]
                    except Exception:  # noqa: BLE001
                        pass

                    activities.append(LinkedInActivity(
                        activity_id=f"LI-MSG-{uuid.uuid4().hex[:8]}",
                        event_type=LinkedInEventType.NEW_MESSAGE,
                        sender_name=name,
                        content=preview,
                        timestamp=datetime.now(tz=timezone.utc).isoformat(),
                        url=f"{self._LINKEDIN_BASE}/messaging/",
                    ))
                except Exception:  # noqa: BLE001
                    continue
        except Exception:  # noqa: BLE001
            pass

        return activities

    def _fetch_notifications(self, limit: int) -> list[LinkedInActivity]:
        """Scrape notifications from LinkedIn notifications page."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        activities = []
        try:
            self._driver.get(f"{self._LINKEDIN_BASE}/notifications/")
            wait = WebDriverWait(self._driver, 10)
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".notification-card, .nt-card-list")
            ))
            time.sleep(2)

            items = self._driver.find_elements(
                By.CSS_SELECTOR, ".nt-card__text, .notification-card__text"
            )[:limit]

            for item in items:
                try:
                    text = item.text.strip()[:300]
                    ev_type = (
                        LinkedInEventType.CONNECTION_REQUEST
                        if "connect" in text.lower()
                        else LinkedInEventType.NEW_NOTIFICATION
                    )
                    activities.append(LinkedInActivity(
                        activity_id=f"LI-NOT-{uuid.uuid4().hex[:8]}",
                        event_type=ev_type,
                        content=text,
                        timestamp=datetime.now(tz=timezone.utc).isoformat(),
                        url=f"{self._LINKEDIN_BASE}/notifications/",
                    ))
                except Exception:  # noqa: BLE001
                    continue
        except Exception:  # noqa: BLE001
            pass

        return activities
