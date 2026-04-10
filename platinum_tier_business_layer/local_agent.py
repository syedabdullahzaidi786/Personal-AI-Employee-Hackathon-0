"""
Platinum Tier — Local Agent
Runs on Local PC. Reads Pending_Approval drafts, gets human approval, sends emails.
"""

import os
import shutil
import smtplib
import logging
import re
import xmlrpc.client
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────────
VAULT         = Path(__file__).parent / "vault"
PENDING       = VAULT / "Pending_Approval" / "email"
PENDING_ODOO  = VAULT / "Pending_Approval" / "odoo"
DONE          = VAULT / "Done"
DASHBOARD     = VAULT / "Dashboard.md"  # written by Local ONLY

DONE.mkdir(parents=True, exist_ok=True)
PENDING_ODOO.mkdir(parents=True, exist_ok=True)

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [LOCAL] %(levelname)s — %(message)s",
)
log = logging.getLogger("local_agent")


# ── Send email ─────────────────────────────────────────────────────────────────
def send_email(to: str, subject: str, body: str) -> bool:
    """Send email via Gmail SMTP."""
    try:
        gmail_user = os.getenv("GMAIL_ADDRESS")
        gmail_pass = os.getenv("GMAIL_APP_PASSWORD")

        msg = MIMEMultipart()
        msg["From"]    = gmail_user
        msg["To"]      = to
        msg["Subject"] = f"Re: {subject}"
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_pass)
            server.send_message(msg)

        log.info(f"Email sent to {to} | Subject: {subject}")
        return True
    except Exception as e:
        log.error(f"Send failed: {e}")
        return False


# ── Parse draft file ───────────────────────────────────────────────────────────
def parse_draft(path: Path) -> dict:
    """Extract key fields from a Pending_Approval markdown file."""
    text = path.read_text(encoding="utf-8")

    def extract(label):
        match = re.search(rf"\*\*{label}:\*\*\s*(.+)", text)
        return match.group(1).strip() if match else ""

    # Extract proposed reply block
    reply_match = re.search(
        r"## Proposed Reply \(Cloud Agent Draft\)\n(.+?)---",
        text, re.DOTALL
    )
    draft_body = reply_match.group(1).strip() if reply_match else ""

    return {
        "sender":  extract("From"),
        "subject": extract("Subject"),
        "draft":   draft_body,
    }


# ── Update dashboard ───────────────────────────────────────────────────────────
def update_dashboard(entry: str):
    """Append an entry to Dashboard.md — Local writes ONLY."""
    ts = datetime.utcnow().isoformat()
    line = f"- [{ts}] {entry}\n"
    with open(DASHBOARD, "a", encoding="utf-8") as f:
        f.write(line)


# ── Process one draft ──────────────────────────────────────────────────────────
def process_draft(path: Path):
    """Show draft to human, get approval, send if approved."""
    info = parse_draft(path)

    print("\n" + "="*60)
    print(f"📧 NEW DRAFT FOR APPROVAL")
    print(f"   From:    {info['sender']}")
    print(f"   Subject: {info['subject']}")
    print(f"\n--- Draft Reply ---\n{info['draft']}\n---")
    print("="*60)
    print("\n[A] Approve & Send   [E] Edit draft   [R] Reject")

    choice = input("Your choice: ").strip().upper()

    if choice == "A":
        # Extract sender email
        sender_match = re.search(r"<(.+?)>", info["sender"])
        to_email = sender_match.group(1) if sender_match else info["sender"]

        success = send_email(to_email, info["subject"], info["draft"])
        if success:
            done_path = DONE / f"approved_{path.name}"
            shutil.move(str(path), str(done_path))
            update_dashboard(f"APPROVED & SENT — {info['subject'][:50]} → {to_email}")
            print("✅ Sent and logged to Done/")
        else:
            print("❌ Send failed — check logs")

    elif choice == "E":
        print("Enter your edited reply (press Enter twice when done):")
        lines = []
        while True:
            line = input()
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
        edited = "\n".join(lines[:-1])

        sender_match = re.search(r"<(.+?)>", info["sender"])
        to_email = sender_match.group(1) if sender_match else info["sender"]

        success = send_email(to_email, info["subject"], edited)
        if success:
            done_path = DONE / f"edited_{path.name}"
            shutil.move(str(path), str(done_path))
            update_dashboard(f"EDITED & SENT — {info['subject'][:50]} → {to_email}")
            print("✅ Edited reply sent and logged.")

    elif choice == "R":
        done_path = DONE / f"rejected_{path.name}"
        shutil.move(str(path), str(done_path))
        update_dashboard(f"REJECTED — {info['subject'][:50]}")
        print("❌ Draft rejected and moved to Done/rejected_*")

    else:
        print("Invalid choice — skipping.")


# ── Odoo Integration ───────────────────────────────────────────────────────────
def odoo_connect():
    """Connect to Odoo via XML-RPC. Returns (models_proxy, uid, db, pwd) or None."""
    try:
        url  = os.getenv("ODOO_URL", "http://localhost:8069")
        db   = os.getenv("ODOO_DB", "odoo")
        user = os.getenv("ODOO_USERNAME", "admin")
        pwd  = os.getenv("ODOO_PASSWORD", "admin")

        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        uid = common.authenticate(db, user, pwd, {})
        if not uid:
            print("❌ Odoo auth failed — check ODOO_USER/ODOO_PASSWORD in .env")
            return None
        models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
        return models, uid, db, pwd
    except Exception as e:
        print(f"❌ Odoo connect failed: {e}")
        return None


def process_odoo_draft(path: Path):
    """Show Odoo draft invoice to human, get approval, post if approved."""
    text = path.read_text(encoding="utf-8")

    # Extract invoice ID
    id_match = re.search(r"\*\*Odoo Invoice ID:\*\*\s*(\d+)", text)
    invoice_id = int(id_match.group(1)) if id_match else None

    subject_match = re.search(r"\*\*Subject:\*\*\s*(.+)", text)
    subject = subject_match.group(1).strip() if subject_match else "Unknown"

    print("\n" + "="*60)
    print(f"🧾 ODOO INVOICE — PENDING APPROVAL")
    print(f"   Invoice ID : {invoice_id}")
    print(f"   Re email   : {subject}")
    print("="*60)
    print("\n[A] Approve & Post to Odoo   [R] Reject")

    choice = input("Your choice: ").strip().upper()

    if choice == "A":
        if not invoice_id:
            print("❌ Could not extract Invoice ID from file.")
            return

        conn = odoo_connect()
        if not conn:
            return
        models, uid, db, pwd = conn

        try:
            # Set a price before posting (ask user)
            price_input = input("Enter invoice amount (press Enter for 100.0): ").strip()
            price = float(price_input) if price_input else 100.0

            # Update line price
            invoice_data = models.execute_kw(db, uid, pwd, "account.move", "read",
                [[invoice_id]], {"fields": ["invoice_line_ids"]})
            line_ids = invoice_data[0]["invoice_line_ids"]
            if line_ids:
                models.execute_kw(db, uid, pwd, "account.move.line", "write",
                    [line_ids, {"price_unit": price}])

            # Post/confirm invoice
            models.execute_kw(db, uid, pwd, "account.move", "action_post", [[invoice_id]])
            print(f"✅ Invoice #{invoice_id} posted in Odoo! Amount: {price}")

            done_path = DONE / f"approved_odoo_{path.name}"
            shutil.move(str(path), str(done_path))
            update_dashboard(f"ODOO INVOICE POSTED — ID={invoice_id}, Amount={price}")

        except Exception as e:
            print(f"❌ Odoo post failed: {e}")

    elif choice == "R":
        done_path = DONE / f"rejected_odoo_{path.name}"
        shutil.move(str(path), str(done_path))
        update_dashboard(f"ODOO INVOICE REJECTED — ID={invoice_id}")
        print("❌ Invoice rejected.")
    else:
        print("Invalid choice — skipping.")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    log.info("Local Agent started — scanning Pending_Approval/")

    email_drafts = sorted(PENDING.glob("*.md"))
    odoo_drafts  = sorted(PENDING_ODOO.glob("*.md"))

    if not email_drafts and not odoo_drafts:
        print("✅ No pending approvals right now.")
        return

    if email_drafts:
        print(f"\n📧 {len(email_drafts)} email draft(s) waiting for approval.\n")
        for draft_path in email_drafts:
            process_draft(draft_path)

    if odoo_drafts:
        print(f"\n🧾 {len(odoo_drafts)} Odoo invoice(s) waiting for approval.\n")
        for draft_path in odoo_drafts:
            process_odoo_draft(draft_path)

    total = len(email_drafts) + len(odoo_drafts)
    print("\n✅ All drafts processed.")
    update_dashboard(f"Local Agent session complete — {total} draft(s) reviewed")


if __name__ == "__main__":
    main()
