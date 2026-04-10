"""
Odoo MCP Server — Personal AI Employee (Gold Tier)
===================================================
Exposes Odoo Community ERP operations as MCP tools so Claude can
manage business contacts, customers, and records autonomously.

Tools provided:
  - create_odoo_contact  → create a new contact/customer in Odoo
  - fetch_odoo_contact   → retrieve a contact by ID
  - list_odoo_contacts   → list recent contacts
  - update_odoo_contact  → update an existing contact
  - odoo_health          → check Odoo connection

Credentials from .env:
  ODOO_URL      = http://localhost:8069
  ODOO_DB       = mycompany
  ODOO_USERNAME = admin@mycompany.com
  ODOO_PASSWORD = admin123

Run this server:
  python mcp_servers/odoo_mcp_server.py

Register in claude_desktop_config.json:
  {
    "mcpServers": {
      "odoo": {
        "command": "python",
        "args": ["mcp_servers/odoo_mcp_server.py"]
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

mcp = FastMCP("odoo-mcp-server")

VAULT         = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "obsidian-vault")
ODOO_URL      = os.environ.get("ODOO_URL",      "http://localhost:8069").strip()
ODOO_DB       = os.environ.get("ODOO_DB",       "mycompany").strip()
ODOO_USERNAME = os.environ.get("ODOO_USERNAME", "admin").strip()
ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD", "admin").strip()


def _make_adapter():
    from golden_tier_external_world.actions.odoo.adapter import RealOdooAdapter, MockOdooAdapter
    from golden_tier_external_world.actions.odoo.models import OdooConfig

    config = OdooConfig(
        odoo_url=ODOO_URL,
        database=ODOO_DB,
        vault_root=VAULT,
    )
    if ODOO_URL and ODOO_DB and ODOO_USERNAME and ODOO_PASSWORD:
        return RealOdooAdapter(config, username=ODOO_USERNAME, credential_token=ODOO_PASSWORD)
    return MockOdooAdapter()


# ── Tools ────────────────────────────────────────────────────────────────────

@mcp.tool()
def create_odoo_contact(name: str, email: str = "", phone: str = "", company: str = "") -> str:
    """
    Create a new contact or customer in Odoo ERP.

    Args:
        name:    Full name of the contact (required).
        email:   Email address (optional).
        phone:   Phone number (optional).
        company: Company name (optional).

    Returns:
        "CREATED: record_id=<id>" or "FAILED: <reason>"
    """
    from golden_tier_external_world.actions.odoo.models import make_create_request

    fields: dict = {"name": name}
    if email:
        fields["email"] = email
    if phone:
        fields["phone"] = phone
    if company:
        fields["company_name"] = company

    adapter = _make_adapter()
    request = make_create_request(model="res.partner", fields=fields)
    result  = adapter.execute(request)

    if result.status == "SUCCESS" and result.record_id:
        return f"CREATED: record_id={result.record_id} — name={name!r}"
    return f"FAILED: {result.error or result.status}"


@mcp.tool()
def fetch_odoo_contact(record_id: int) -> str:
    """
    Fetch a contact from Odoo ERP by record ID.

    Args:
        record_id: The Odoo res.partner record ID (integer).

    Returns:
        Contact details as text or "FAILED: <reason>"
    """
    from golden_tier_external_world.actions.odoo.models import make_fetch_request

    adapter = _make_adapter()
    request = make_fetch_request(model="res.partner", record_id=record_id)
    result  = adapter.execute(request)

    if result.status == "SUCCESS" and result.data:
        data = result.data
        lines = [f"Contact ID: {record_id}"]
        for key in ("name", "email", "phone", "company_name", "street", "city"):
            val = data.get(key)
            if val:
                lines.append(f"  {key}: {val}")
        return "\n".join(lines)
    return f"FAILED: {result.error or result.status}"


@mcp.tool()
def list_odoo_contacts(limit: int = 10) -> str:
    """
    List recent contacts from Odoo ERP.

    Args:
        limit: Number of contacts to return (default 10, max 50).

    Returns:
        Formatted list of contacts or "FAILED: <reason>"
    """
    limit = min(max(1, limit), 50)

    try:
        import xmlrpc.client

        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        uid    = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
        if not uid:
            return "FAILED: Odoo authentication failed."

        models  = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
        records = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            "res.partner", "search_read",
            [[]],
            {"fields": ["id", "name", "email", "phone"], "limit": limit, "order": "id desc"},
        )

        if not records:
            return "No contacts found in Odoo."

        lines = [f"Odoo Contacts (latest {limit}):"]
        for r in records:
            email = r.get("email") or "—"
            phone = r.get("phone") or "—"
            lines.append(f"  [{r['id']}] {r['name']}  email={email}  phone={phone}")
        return "\n".join(lines)

    except Exception as exc:  # noqa: BLE001
        return f"FAILED: {exc}"


@mcp.tool()
def update_odoo_contact(record_id: int, name: str = "", email: str = "", phone: str = "") -> str:
    """
    Update an existing contact in Odoo ERP.

    Args:
        record_id: The Odoo res.partner record ID to update.
        name:      New name (optional — leave blank to keep existing).
        email:     New email (optional).
        phone:     New phone (optional).

    Returns:
        "UPDATED: record_id=<id>" or "FAILED: <reason>"
    """
    from golden_tier_external_world.actions.odoo.models import make_update_request

    fields: dict = {}
    if name:
        fields["name"] = name
    if email:
        fields["email"] = email
    if phone:
        fields["phone"] = phone

    if not fields:
        return "FAILED: No fields provided to update."

    adapter = _make_adapter()
    request = make_update_request(model="res.partner", record_id=record_id, fields=fields)
    result  = adapter.execute(request)

    if result.status == "SUCCESS":
        return f"UPDATED: record_id={record_id} — fields={list(fields.keys())}"
    return f"FAILED: {result.error or result.status}"


@mcp.tool()
def odoo_health() -> str:
    """
    Check if the Odoo MCP server can connect to the Odoo instance.

    Returns:
        "HEALTHY: Odoo vX.Y connected" or "FAILED: <reason>"
    """
    try:
        import xmlrpc.client
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        info   = common.version()
        ver    = info.get("server_version", "unknown")
        uid    = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
        if uid:
            return f"HEALTHY: Odoo v{ver} connected — uid={uid} db={ODOO_DB}"
        return f"DEGRADED: Odoo reachable but authentication failed — check credentials"
    except Exception as exc:  # noqa: BLE001
        return f"FAILED: Cannot connect to Odoo at {ODOO_URL} — {exc}"


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
