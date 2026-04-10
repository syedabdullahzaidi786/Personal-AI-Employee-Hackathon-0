"""
BROWSER_MCP_SKILL — Browser Adapter
Phase 1: BrowserAdapter ABC, MockBrowserAdapter (no real automation),
         RealBrowserAdapter (Phase 2 stub).

Constitution compliance:
  - Principle I: Local-First — MockBrowserAdapter requires no network
  - Section 8: Credential Storage — RealBrowserAdapter never logs credentials
  - Principle VI: Fail Safe — execute() and health_check() never raise
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from urllib.parse import urlparse

from .models import (
    BrowserActionStatus,
    BrowserActionType,
    BrowserRequest,
    BrowserResult,
)


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class BrowserAdapter(ABC):
    """
    Abstract contract for browser automation.

    Phase 1 uses MockBrowserAdapter.
    Phase 2 will provide RealBrowserAdapter backed by Playwright or similar.
    """

    @abstractmethod
    def execute(self, request: BrowserRequest) -> BrowserResult:
        """
        Execute a browser action. Returns BrowserResult. Never raises.
        On failure, return BrowserResult with status=FAILED and error message.
        """

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the adapter is ready. Never raises."""


# ---------------------------------------------------------------------------
# MockBrowserAdapter — in-memory, no network, deterministic
# ---------------------------------------------------------------------------

class MockBrowserAdapter(BrowserAdapter):
    """
    In-memory browser adapter for unit tests and local development.
    No real browser or network is used.

    Behaviour:
      - open_url   → returns a synthetic page with derived title and status 200
      - extract_text → returns synthetic extracted text based on URL + selector
      - inject_page() / inject_content() allow tests to control responses

    Usage::

        adapter = MockBrowserAdapter()
        result  = adapter.execute(make_open_url_request("https://example.com"))
        assert result.status == BrowserActionStatus.SUCCESS
        assert result.status_code == 200
    """

    def __init__(self, healthy: bool = True, fail_execute: bool = False) -> None:
        self._results:       list[BrowserResult] = []
        self._healthy:       bool                = healthy
        self._fail_execute:  bool                = fail_execute
        self._execute_count: int                 = 0
        # Optional per-url overrides (url → content string)
        self._content_map:   dict[str, str]      = {}
        self._title_map:     dict[str, str]      = {}

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def set_healthy(self, healthy: bool) -> None:
        self._healthy = healthy

    def set_fail_execute(self, fail: bool) -> None:
        """Simulate execution failures when True."""
        self._fail_execute = fail

    def inject_page(self, url: str, title: str) -> None:
        """Pre-register a title for a URL (used by open_url mock)."""
        self._title_map[url] = title

    def inject_content(self, url: str, content: str) -> None:
        """Pre-register extracted content for a URL (used by extract_text mock)."""
        self._content_map[url] = content

    def clear(self) -> None:
        self._results.clear()
        self._execute_count = 0
        self._content_map.clear()
        self._title_map.clear()

    @property
    def results(self) -> list[BrowserResult]:
        """All results produced by this adapter (defensive copy)."""
        return list(self._results)

    @property
    def execute_count(self) -> int:
        return self._execute_count

    # ------------------------------------------------------------------
    # BrowserAdapter interface
    # ------------------------------------------------------------------

    def execute(self, request: BrowserRequest) -> BrowserResult:
        self._execute_count += 1

        if self._fail_execute:
            result = BrowserResult(
                request_id=request.request_id,
                action=request.action,
                status=BrowserActionStatus.FAILED,
                url=request.url,
                error="MockBrowserAdapter: simulated execution failure",
                adapter="mock",
            )
            self._results.append(result)
            return result

        if request.action == BrowserActionType.OPEN_URL:
            result = self._open_url(request)
        elif request.action == BrowserActionType.EXTRACT_TEXT:
            result = self._extract_text(request)
        else:
            result = BrowserResult(
                request_id=request.request_id,
                action=request.action,
                status=BrowserActionStatus.FAILED,
                url=request.url,
                error=f"Unknown action: {request.action!r}",
                adapter="mock",
            )

        self._results.append(result)
        return result

    def health_check(self) -> bool:
        return self._healthy

    # ------------------------------------------------------------------
    # Internal action handlers
    # ------------------------------------------------------------------

    def _open_url(self, request: BrowserRequest) -> BrowserResult:
        """Simulate opening a URL: returns a synthetic page title."""
        title = self._title_map.get(
            request.url,
            self._derive_title(request.url),
        )
        return BrowserResult(
            request_id=request.request_id,
            action=request.action,
            status=BrowserActionStatus.SUCCESS,
            url=request.url,
            content=title,
            status_code=200,
            adapter="mock",
            executed_at=datetime.now(tz=timezone.utc),
        )

    def _extract_text(self, request: BrowserRequest) -> BrowserResult:
        """Simulate extracting text from a URL + optional selector."""
        content = self._content_map.get(
            request.url,
            self._derive_content(request.url, request.selector),
        )
        # Cap content length
        content = content[: request.max_content_len]
        return BrowserResult(
            request_id=request.request_id,
            action=request.action,
            status=BrowserActionStatus.SUCCESS,
            url=request.url,
            content=content,
            status_code=200,
            adapter="mock",
            executed_at=datetime.now(tz=timezone.utc),
        )

    @staticmethod
    def _derive_title(url: str) -> str:
        """Derive a synthetic page title from the URL."""
        try:
            parsed = urlparse(url)
            host = parsed.netloc or url
            path = parsed.path.strip("/").replace("/", " › ") or "Home"
            return f"[Mock] {host} — {path}"
        except Exception:  # noqa: BLE001
            return f"[Mock] Page: {url[:80]}"

    @staticmethod
    def _derive_content(url: str, selector: str) -> str:
        """Derive synthetic extracted text from URL + selector."""
        sel_info = f" (selector: {selector!r})" if selector else ""
        return f"[Mock extracted text from {url}{sel_info}]"


# ---------------------------------------------------------------------------
# RealBrowserAdapter — Phase 2 stub (raises NotImplementedError)
# ---------------------------------------------------------------------------

class RealBrowserAdapter(BrowserAdapter):
    """
    Phase 2 stub.  Will wrap Playwright or a browser-automation MCP server.

    Accepts credential_token so callers can pass the secret from
    SecuritySkill without this class ever storing or logging it.
    """

    def __init__(self, config: "BrowserConfig", credential_token: str = "") -> None:  # noqa: F821
        # credential_token intentionally not stored persistently
        self._has_token = bool(credential_token)

    def execute(self, request: BrowserRequest) -> BrowserResult:
        raise NotImplementedError(
            "RealBrowserAdapter is a Phase 2 stub. Use MockBrowserAdapter for now."
        )

    def health_check(self) -> bool:
        return False  # Not healthy until Phase 2
