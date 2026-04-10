"""
Email MCP Server — Personal AI Employee (Gold Tier)
====================================================
Exposes Gmail SMTP email sending as MCP tools so Claude can
send emails on behalf of Sharmeen Fatima autonomously.

Tools provided:
  - send_email        → send an email via Gmail SMTP
  - email_health      → check if SMTP credentials are configured

Credentials from .env:
  GMAIL_ADDRESS     = your Gmail address
  GMAIL_APP_PASSWORD = 16-digit App Password (Google Account → Security → App Passwords)

Run this server:
  python mcp_servers/email_mcp_server.py

Register in claude_desktop_config.json:
  {
    "mcpServers": {
      "email": {
        "command": "python",
        "args": ["mcp_servers/email_mcp_server.py"]
      }
    }
  }
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("email-mcp-server")

VAULT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "obsidian-vault")
GMAIL_ADDRESS      = os.environ.get("GMAIL_ACCOUNT_EMAIL", "").strip()
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "").strip()


def _make_adapter():
    from golden_tier_external_world.actions.email.adapter import RealEmailAdapter, MockEmailAdapter
    from golden_tier_external_world.actions.email.models import EmailConfig

    if GMAIL_ADDRESS and GMAIL_APP_PASSWORD:
        config = EmailConfig(sender_address=GMAIL_ADDRESS, vault_root=VAULT)
        return RealEmailAdapter(config, credential_token=GMAIL_APP_PASSWORD), config
    else:
        config = EmailConfig(sender_address="mock@example.com", vault_root=VAULT)
        return MockEmailAdapter(), config


# ── Tools ────────────────────────────────────────────────────────────────────

@mcp.tool()
def send_email(to: str, subject: str, body: str) -> str:
    """
    Send an email on behalf of Sharmeen Fatima via Gmail SMTP.

    Args:
        to:      Recipient email address (e.g. "someone@gmail.com").
                 Multiple addresses: separate with comma.
        subject: Email subject line.
        body:    Plain-text email body.

    Returns:
        Status string — "SENT", "FAILED: <reason>", or "PENDING_APPROVAL".
    """
    from golden_tier_external_world.actions.email.models import EmailRequest

    recipients = [addr.strip() for addr in to.split(",") if addr.strip()]
    if not recipients:
        return "FAILED: No valid recipient address provided."

    adapter, config = _make_adapter()
    request = EmailRequest(
        to=recipients,
        subject=subject,
        body=body,
        sender=GMAIL_ADDRESS or "mock@example.com",
        tier=1,
    )

    result = adapter.send(request)

    if result.status == "SENT":
        return f"SENT: Email delivered to {', '.join(recipients)} — Subject: {subject!r}"
    else:
        return f"FAILED: {result.error or result.status}"


@mcp.tool()
def email_health() -> str:
    """
    Check if the Email MCP server is configured and SMTP credentials are set.

    Returns:
        "HEALTHY: Gmail SMTP ready" or "DEGRADED: no credentials — running in mock mode"
    """
    if GMAIL_ADDRESS and GMAIL_APP_PASSWORD:
        return f"HEALTHY: Gmail SMTP ready — sender={GMAIL_ADDRESS}"
    return "DEGRADED: GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set — running in mock mode"


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
