"""
EMAIL_MCP_ACTION_SKILL — Email Adapter
Phase 1: EmailAdapter ABC, MockEmailAdapter (no SMTP), RealEmailAdapter (Phase 2 stub).

Constitution compliance:
  - Principle I: Local-First — MockEmailAdapter requires no network
  - Section 8: Credential Storage — RealEmailAdapter never logs credentials
  - Principle VI: Fail Safe — health_check() never raises; send() never raises
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone

from .models import EmailActionStatus, EmailRequest, EmailResult


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class EmailAdapter(ABC):
    """
    Abstract contract for email sending.

    Phase 1 uses MockEmailAdapter.
    Phase 2 will provide RealEmailAdapter backed by smtplib or an email API.
    """

    @abstractmethod
    def send(self, request: EmailRequest) -> EmailResult:
        """
        Send an email. Returns EmailResult. Never raises.
        On failure, return EmailResult with status=FAILED and error message.
        """

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the adapter is ready to send. Never raises."""


# ---------------------------------------------------------------------------
# MockEmailAdapter — in-memory, no network, deterministic
# ---------------------------------------------------------------------------

class MockEmailAdapter(EmailAdapter):
    """
    In-memory email adapter for unit tests and local development.
    No SMTP connection is made; emails are captured in self._sent.

    Usage::

        adapter = MockEmailAdapter()
        result  = adapter.send(make_email_request(["alice@example.com"], "Hi", "Body"))
        assert result.status == EmailActionStatus.SENT
        assert adapter.send_count == 1
    """

    def __init__(self, healthy: bool = True, fail_send: bool = False) -> None:
        self._sent:       list[EmailResult] = []
        self._healthy:    bool              = healthy
        self._fail_send:  bool              = fail_send
        self._send_count: int               = 0

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def set_healthy(self, healthy: bool) -> None:
        self._healthy = healthy

    def set_fail_send(self, fail: bool) -> None:
        """Simulate send failures when True."""
        self._fail_send = fail

    def clear_sent(self) -> None:
        self._sent.clear()
        self._send_count = 0

    @property
    def sent(self) -> list[EmailResult]:
        """All results produced by this adapter (defensive copy)."""
        return list(self._sent)

    @property
    def send_count(self) -> int:
        return self._send_count

    # ------------------------------------------------------------------
    # EmailAdapter interface
    # ------------------------------------------------------------------

    def send(self, request: EmailRequest) -> EmailResult:
        self._send_count += 1
        if self._fail_send:
            result = EmailResult(
                request_id=request.request_id,
                status=EmailActionStatus.FAILED,
                error="MockEmailAdapter: simulated send failure",
                adapter="mock",
            )
            self._sent.append(result)
            return result

        result = EmailResult(
            request_id=request.request_id,
            status=EmailActionStatus.SENT,
            sent_at=datetime.now(tz=timezone.utc),
            adapter="mock",
        )
        self._sent.append(result)
        return result

    def health_check(self) -> bool:
        return self._healthy


# ---------------------------------------------------------------------------
# RealEmailAdapter — Gmail SMTP via smtplib + App Password
# ---------------------------------------------------------------------------

class RealEmailAdapter(EmailAdapter):
    """
    Live email adapter using Gmail SMTP (smtp.gmail.com:587 + STARTTLS).

    Requires a 16-digit Gmail App Password (same one used for IMAP).
    credential_token is stored only in memory; never logged.

    Usage::

        config  = EmailConfig(sender_address="you@gmail.com")
        adapter = RealEmailAdapter(config, credential_token="xxxx xxxx xxxx xxxx")
        result  = adapter.send(make_email_request(["friend@gmail.com"], "Hi", "Hello!"))
    """

    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 587

    def __init__(self, config: "EmailConfig", credential_token: str = "") -> None:  # noqa: F821
        self._config = config
        self._credential_token = credential_token.replace(" ", "")  # strip spaces
        self._has_token = bool(self._credential_token)

    def send(self, request: EmailRequest) -> EmailResult:
        """Send email via Gmail SMTP. Never raises."""
        if not self._has_token:
            return EmailResult(
                request_id=request.request_id,
                status=EmailActionStatus.FAILED,
                error="RealEmailAdapter: no credential_token provided",
                adapter="real_smtp",
            )
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            sender = request.sender or self._config.sender_address

            msg = MIMEMultipart("alternative")
            msg["Subject"] = request.subject
            msg["From"] = sender
            msg["To"] = ", ".join(request.to)
            if request.cc:
                msg["Cc"] = ", ".join(request.cc)

            msg.attach(MIMEText(request.body, "plain"))

            all_recipients = request.to + request.cc + request.bcc

            with smtplib.SMTP(self.SMTP_HOST, self.SMTP_PORT) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(self._config.sender_address, self._credential_token)
                smtp.sendmail(sender, all_recipients, msg.as_string())

            return EmailResult(
                request_id=request.request_id,
                status=EmailActionStatus.SENT,
                sent_at=datetime.now(tz=timezone.utc),
                adapter="real_smtp",
            )
        except Exception as exc:  # noqa: BLE001
            return EmailResult(
                request_id=request.request_id,
                status=EmailActionStatus.FAILED,
                error=str(exc),
                adapter="real_smtp",
            )

    def health_check(self) -> bool:
        """Try SMTP login; return True if credentials are valid. Never raises."""
        if not self._has_token:
            return False
        try:
            import smtplib
            with smtplib.SMTP(self.SMTP_HOST, self.SMTP_PORT) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(self._config.sender_address, self._credential_token)
                return True
        except Exception:  # noqa: BLE001
            return False
