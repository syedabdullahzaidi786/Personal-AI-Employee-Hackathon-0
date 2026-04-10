"""
Platinum Tier — Cloud Agent
Runs on Oracle VM / Codespaces 24/7. Triages emails, drafts replies,
and creates draft Odoo invoices — all pending Local approval.
"""

import os
import json
import time
import shutil
import logging
import xmlrpc.client
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────────
VAULT = Path(__file__).parent / "vault"
NEEDS_ACTION    = VAULT / "Needs_Action"    / "email"
IN_PROGRESS     = VAULT / "In_Progress"     / "cloud_agent"
PLANS           = VAULT / "Plans"           / "email"
PENDING         = VAULT / "Pending_Approval" / "email"
PENDING_ODOO    = VAULT / "Pending_Approval" / "odoo"
UPDATES         = VAULT / "Updates"
DONE            = VAULT / "Done"

for p in [NEEDS_ACTION, IN_PROGRESS, PLANS, PENDING, PENDING_ODOO, UPDATES, DONE]:
    p.mkdir(parents=True, exist_ok=True)

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CLOUD] %(levelname)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(VAULT / "Updates" / "cloud_agent.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("cloud_agent")


# ── Gmail fetch ────────────────────────────────────────────────────────────────
def fetch_unread_emails() -> list[dict]:
    """Fetch unread emails via Gmail MCP / IMAP."""
    try:
        import imaplib, email as emaillib
        from email.header import decode_header

        host = os.getenv("GMAIL_IMAP_HOST", "imap.gmail.com")
        user = os.getenv("GMAIL_ADDRESS")
        pwd  = os.getenv("GMAIL_APP_PASSWORD")

        if not user or not pwd:
            log.warning("GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set — skipping fetch")
            return []

        mail = imaplib.IMAP4_SSL(host)
        mail.login(user, pwd)
        mail.select("inbox")

        _, data = mail.search(None, "UNSEEN")
        uids = data[0].split()
        emails = []

        for uid in uids[-10:]:  # max 10 at a time
            _, msg_data = mail.fetch(uid, "(RFC822)")
            msg = emaillib.message_from_bytes(msg_data[0][1])

            subject_raw, enc = decode_header(msg["Subject"] or "")[0]
            subject = subject_raw.decode(enc or "utf-8") if isinstance(subject_raw, bytes) else subject_raw
            sender  = msg.get("From", "unknown")

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

            emails.append({
                "uid": uid.decode(),
                "subject": subject,
                "sender": sender,
                "body": body[:1000],
                "received": datetime.utcnow().isoformat(),
            })

        mail.logout()
        log.info(f"Fetched {len(emails)} unread email(s)")
        return emails

    except Exception as e:
        log.error(f"Email fetch failed: {e}")
        return []


# ── Draft writer ───────────────────────────────────────────────────────────────
def draft_reply(email: dict) -> str:
    """Generate a draft reply using Groq API (free tier)."""
    try:
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        prompt = f"""You are an AI assistant drafting a professional email reply on behalf of the user.

Original email:
From: {email['sender']}
Subject: {email['subject']}
Body: {email['body']}

Write a concise, professional reply. Keep it under 150 words. Do not include subject line."""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        log.error(f"Draft generation failed: {e}")
        return f"[Auto-draft failed: {e}]\n\nPlease review and reply manually."


# ── Claim-by-move ──────────────────────────────────────────────────────────────
def claim_task(task_file: Path) -> bool:
    """Move task to In_Progress to claim it. Returns True if claimed."""
    target = IN_PROGRESS / task_file.name
    try:
        task_file.rename(target)
        log.info(f"Claimed: {task_file.name}")
        return True
    except FileNotFoundError:
        log.warning(f"Task already claimed by another agent: {task_file.name}")
        return False


# ── Write to Pending_Approval ──────────────────────────────────────────────────
def write_pending_approval(email: dict, draft: str) -> Path:
    """Write draft to Pending_Approval for Local agent to review."""
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}_{email['uid']}.md"
    path = PENDING / filename

    content = f"""# Email Draft — Pending Approval

## Original Email
- **From:** {email['sender']}
- **Subject:** {email['subject']}
- **Received:** {email['received']}

## Original Body
{email['body']}

---

## Proposed Reply (Cloud Agent Draft)
{draft}

---

## Action Required
Local agent: review and approve/reject.
- To approve: move this file to `Done/` and send the reply.
- To reject: delete this file or move to `Done/rejected_<filename>`.

**Status:** PENDING_APPROVAL
**Drafted by:** cloud_agent @ {datetime.utcnow().isoformat()}
"""
    path.write_text(content, encoding="utf-8")
    log.info(f"Written to Pending_Approval: {filename}")
    return path


# ── Odoo Integration ───────────────────────────────────────────────────────────
def odoo_connect():
    """Connect to Odoo via XML-RPC. Returns (models_proxy, uid) or (None, None)."""
    try:
        url  = os.getenv("ODOO_URL", "http://localhost:8069")
        db   = os.getenv("ODOO_DB", "odoo")
        user = os.getenv("ODOO_USERNAME", "admin")
        pwd  = os.getenv("ODOO_PASSWORD", "admin")

        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        uid = common.authenticate(db, user, pwd, {})
        if not uid:
            log.warning("Odoo auth failed — check ODOO_USER/ODOO_PASSWORD")
            return None, None
        models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
        log.info(f"Odoo connected (uid={uid})")
        return models, uid
    except Exception as e:
        log.error(f"Odoo connect failed: {e}")
        return None, None


def detect_invoice_intent(email: dict) -> bool:
    """Return True if email looks like it needs an invoice."""
    keywords = ["invoice", "payment", "bill", "charge", "quote", "order", "purchase"]
    text = (email.get("subject", "") + " " + email.get("body", "")).lower()
    return any(kw in text for kw in keywords)


def create_odoo_draft_invoice(email: dict) -> int | None:
    """Create a draft invoice in Odoo and write approval request to vault."""
    models, uid = odoo_connect()
    if not models:
        return None

    db  = os.getenv("ODOO_DB", "odoo")
    pwd = os.getenv("ODOO_PASSWORD", "admin")

    try:
        # Find or create partner from sender email
        import re as _re
        email_match = _re.search(r"<(.+?)>", email["sender"])
        sender_email = email_match.group(1) if email_match else email["sender"]
        sender_name  = email["sender"].split("<")[0].strip() or sender_email

        partner_ids = models.execute_kw(db, uid, pwd, "res.partner", "search",
            [[["email", "=", sender_email]]])
        if partner_ids:
            partner_id = partner_ids[0]
        else:
            partner_id = models.execute_kw(db, uid, pwd, "res.partner", "create", [{
                "name": sender_name,
                "email": sender_email,
            }])
            log.info(f"Created Odoo partner: {sender_name} <{sender_email}>")

        invoice_id = models.execute_kw(db, uid, pwd, "account.move", "create", [{
            "move_type": "out_invoice",
            "partner_id": partner_id,
            "ref": f"AI-Draft: {email['subject'][:50]}",
            "invoice_line_ids": [(0, 0, {
                "name": f"AI Service — re: {email['subject'][:60]}",
                "quantity": 1,
                "price_unit": 0.0,
            })],
        }])
        log.info(f"Odoo draft invoice created: ID={invoice_id}")

        # Write to Pending_Approval/odoo/
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = PENDING_ODOO / f"{ts}_invoice_{invoice_id}.md"
        path.write_text(f"""# Odoo Invoice — Pending Approval

## Trigger Email
- **From:** {email['sender']}
- **Subject:** {email['subject']}
- **Received:** {email['received']}

## Draft Invoice
- **Odoo Invoice ID:** {invoice_id}
- **Line:** AI Service — re: {email['subject'][:60]}
- **Price:** TBD (set before posting)
- **Status:** draft

## Action Required
Local agent: review and approve to POST this invoice in Odoo.
- To approve: update price if needed, then confirm posting.
- To reject: move to Done/rejected_*.

**Status:** PENDING_APPROVAL
**Drafted by:** cloud_agent @ {datetime.utcnow().isoformat()}
""", encoding="utf-8")
        log.info(f"Odoo approval request written: {path.name}")
        return invoice_id

    except Exception as e:
        log.error(f"Odoo draft invoice failed: {e}")
        return None


# ── Signal writer ──────────────────────────────────────────────────────────────
def write_signal(message: str):
    """Write a status signal for Local agent."""
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = UPDATES / f"signal_{ts}.md"
    path.write_text(f"# Cloud Agent Signal\n\n{message}\n\nTime: {datetime.utcnow().isoformat()}\n", encoding="utf-8")


# ── Main loop ──────────────────────────────────────────────────────────────────
def run_once():
    """Single triage cycle."""
    log.info("=== Cloud Agent triage cycle started ===")

    emails = fetch_unread_emails()
    if not emails:
        log.info("No new emails.")
        return

    for email in emails:
        # Write to Needs_Action
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        task_path = NEEDS_ACTION / f"{ts}_{email['uid']}.json"
        task_path.write_text(json.dumps(email, indent=2, ensure_ascii=False), encoding="utf-8")

        # Claim it
        if not claim_task(task_path):
            continue

        # Draft reply
        draft = draft_reply(email)

        # Write to Pending_Approval
        write_pending_approval(email, draft)

        # Signal
        write_signal(f"New draft ready for approval: {email['subject'][:60]}")

        # Odoo: create draft invoice if email looks invoice-related
        if detect_invoice_intent(email):
            inv_id = create_odoo_draft_invoice(email)
            if inv_id:
                write_signal(f"Odoo draft invoice created (ID={inv_id}) for: {email['subject'][:50]}")

    log.info("=== Triage cycle complete ===")


def main():
    interval = int(os.getenv("CLOUD_AGENT_INTERVAL", "300"))  # default 5 min
    log.info(f"Cloud Agent started. Poll interval: {interval}s")
    while True:
        run_once()
        time.sleep(interval)


if __name__ == "__main__":
    main()
