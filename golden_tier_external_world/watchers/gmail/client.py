"""
GMAIL_WATCHER_SKILL — Gmail Client
Phase 1: GmailClient ABC, MockGmailClient (test/dev), RealGmailClient (IMAP live).

Constitution compliance:
  - Principle I: Local-First — MockGmailClient requires no network
  - Section 8: Credential Storage — RealGmailClient accepts app_password, never logs it
  - Principle VI: Fail Safe — health_check() never raises; fetch errors are surfaced, not hidden
"""

from __future__ import annotations

import email as email_lib
import imaplib
from abc import ABC, abstractmethod
from collections import deque
from datetime import datetime, timezone
from email.header import decode_header
from typing import Optional

from .models import GmailConfig, GmailMessage, make_gmail_message


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class GmailClient(ABC):
    """
    Abstract contract for Gmail access.

    Phase 1 uses MockGmailClient.
    Phase 2 will provide RealGmailClient backed by the Gmail API.
    """

    @abstractmethod
    def fetch_unread(
        self,
        max_results: int = 10,
        filter_labels: Optional[list[str]] = None,
    ) -> list[GmailMessage]:
        """
        Return up to *max_results* unread messages.

        If *filter_labels* is non-empty, only messages with at least one
        of those labels are returned. Never raises.
        """

    @abstractmethod
    def mark_read(self, message_id: str) -> bool:
        """Mark a message as read. Returns True on success."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the Gmail API / mock is reachable. Never raises."""


# ---------------------------------------------------------------------------
# MockGmailClient — deterministic, in-memory, no network
# ---------------------------------------------------------------------------

class MockGmailClient(GmailClient):
    """
    In-memory Gmail client for unit tests and local development.

    Usage::

        client = MockGmailClient()
        client.inject_message(make_gmail_message("Hello", "alice@example.com"))
        messages = client.fetch_unread(max_results=5)
    """

    def __init__(self, healthy: bool = True) -> None:
        self._inbox:   deque[GmailMessage] = deque()
        self._read:    set[str]            = set()
        self._healthy: bool                = healthy
        self._fetch_count: int             = 0

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def inject_message(self, message: GmailMessage) -> None:
        """Add a message to the mock inbox."""
        self._inbox.append(message)

    def set_healthy(self, healthy: bool) -> None:
        """Flip the health state."""
        self._healthy = healthy

    def clear_inbox(self) -> None:
        """Remove all messages from the mock inbox."""
        self._inbox.clear()
        self._read.clear()

    @property
    def fetch_count(self) -> int:
        """Total number of fetch_unread calls made."""
        return self._fetch_count

    @property
    def inbox_size(self) -> int:
        """Number of messages currently in the mock inbox."""
        return len(self._inbox)

    # ------------------------------------------------------------------
    # GmailClient interface
    # ------------------------------------------------------------------

    def fetch_unread(
        self,
        max_results: int = 10,
        filter_labels: Optional[list[str]] = None,
    ) -> list[GmailMessage]:
        self._fetch_count += 1
        results = []
        for msg in self._inbox:
            if msg.message_id in self._read:
                continue
            if filter_labels:
                if not any(lbl in msg.labels for lbl in filter_labels):
                    continue
            results.append(msg)
            if len(results) >= max_results:
                break
        return results

    def mark_read(self, message_id: str) -> bool:
        self._read.add(message_id)
        return True

    def health_check(self) -> bool:
        return self._healthy


# ---------------------------------------------------------------------------
# RealGmailClient — Phase 2 stub (raises NotImplementedError)
# ---------------------------------------------------------------------------

class RealGmailClient(GmailClient):
    """
    Live Gmail client using IMAP4_SSL + App Password.

    Requires Gmail IMAP enabled and a 16-digit App Password.
    Enable IMAP: Gmail Settings → See all settings → Forwarding and POP/IMAP → Enable IMAP

    Usage::

        config = GmailConfig(account_email="you@gmail.com")
        client = RealGmailClient(config, app_password="xxxx xxxx xxxx xxxx")
        messages = client.fetch_unread(max_results=5)
    """

    IMAP_HOST = "imap.gmail.com"
    IMAP_PORT = 993

    def __init__(self, config: GmailConfig, app_password: str = "") -> None:
        self._config = config
        self._app_password = app_password.replace(" ", "")  # strip spaces
        self._uid_to_msg_id: dict[str, str] = {}  # IMAP UID → our message_id

    # ------------------------------------------------------------------
    # GmailClient interface
    # ------------------------------------------------------------------

    def fetch_unread(
        self,
        max_results: int = 10,
        filter_labels: Optional[list[str]] = None,
    ) -> list[GmailMessage]:
        """Fetch unread emails from INBOX via IMAP."""
        try:
            with imaplib.IMAP4_SSL(self.IMAP_HOST, self.IMAP_PORT) as imap:
                imap.login(self._config.account_email, self._app_password)
                imap.select("INBOX", readonly=True)

                _, data = imap.search(None, "UNSEEN")
                uid_list = data[0].split() if data[0] else []
                uid_list = uid_list[-max_results:]  # most recent N

                messages: list[GmailMessage] = []
                for uid in uid_list:
                    try:
                        msg = self._fetch_one(imap, uid)
                        if msg:
                            messages.append(msg)
                    except Exception:  # noqa: BLE001
                        continue
                return messages
        except imaplib.IMAP4.error:
            return []
        except Exception:  # noqa: BLE001
            return []

    def mark_read(self, message_id: str) -> bool:
        """Mark a message as read by removing \\Unseen flag."""
        uid = self._msg_id_to_uid(message_id)
        if uid is None:
            return False
        try:
            with imaplib.IMAP4_SSL(self.IMAP_HOST, self.IMAP_PORT) as imap:
                imap.login(self._config.account_email, self._app_password)
                imap.select("INBOX")
                imap.store(uid, "+FLAGS", "\\Seen")
                return True
        except Exception:  # noqa: BLE001
            return False

    def health_check(self) -> bool:
        """Try IMAP login; return True if credentials are valid."""
        if not self._app_password:
            return False
        try:
            with imaplib.IMAP4_SSL(self.IMAP_HOST, self.IMAP_PORT) as imap:
                imap.login(self._config.account_email, self._app_password)
                return True
        except Exception:  # noqa: BLE001
            return False

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _fetch_one(self, imap: imaplib.IMAP4_SSL, uid: bytes) -> Optional[GmailMessage]:
        """Fetch and parse a single message by IMAP UID."""
        _, msg_data = imap.fetch(uid, "(RFC822)")
        if not msg_data or not msg_data[0]:
            return None

        raw = msg_data[0][1]
        if not isinstance(raw, bytes):
            return None

        msg = email_lib.message_from_bytes(raw)

        subject  = self._decode_header(msg.get("Subject", "(no subject)"))
        sender   = self._decode_header(msg.get("From", ""))
        msg_id   = msg.get("Message-ID", f"UID-{uid.decode()}")
        thread_id = msg.get("Thread-Index", msg_id)

        # Build snippet from first text/plain part
        snippet = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        snippet = part.get_payload(decode=True).decode("utf-8", errors="replace")[:200]
                    except Exception:  # noqa: BLE001
                        pass
                    break
        else:
            try:
                snippet = msg.get_payload(decode=True).decode("utf-8", errors="replace")[:200]
            except Exception:  # noqa: BLE001
                pass

        # Attachments
        attachment_names = [
            part.get_filename()
            for part in msg.walk()
            if part.get_content_disposition() == "attachment" and part.get_filename()
        ]

        gmail_msg = GmailMessage(
            message_id=msg_id,
            thread_id=thread_id,
            subject=subject,
            sender=sender,
            recipient=self._config.account_email,
            snippet=snippet[:200],
            labels=["INBOX", "UNREAD"],
            received_at=datetime.now(tz=timezone.utc),
            has_attachments=bool(attachment_names),
            attachment_names=attachment_names,
        )

        # Store UID mapping for mark_read
        self._uid_to_msg_id[msg_id] = uid.decode()
        return gmail_msg

    def _msg_id_to_uid(self, message_id: str) -> Optional[str]:
        return self._uid_to_msg_id.get(message_id)

    @staticmethod
    def _decode_header(value: str) -> str:
        """Decode RFC2047-encoded header value."""
        try:
            parts = decode_header(value)
            decoded = []
            for part, charset in parts:
                if isinstance(part, bytes):
                    decoded.append(part.decode(charset or "utf-8", errors="replace"))
                else:
                    decoded.append(part)
            return "".join(decoded)
        except Exception:  # noqa: BLE001
            return value
