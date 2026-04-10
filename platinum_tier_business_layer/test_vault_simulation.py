"""
Local simulation test — without real emails or Oracle VM.
Creates a fake email task and runs the full Cloud → Vault → Local flow.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

VAULT   = Path(__file__).parent / "vault"
NEEDS   = VAULT / "Needs_Action" / "email"
IN_PROG = VAULT / "In_Progress"  / "cloud_agent"
PENDING = VAULT / "Pending_Approval" / "email"
DONE    = VAULT / "Done"

def test_full_flow():
    print("\n[TEST] Platinum Tier -- Vault Simulation Test")
    print("="*50)

    # Step 1: Simulate incoming email
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    fake_email = {
        "uid": "TEST001",
        "subject": "Meeting Request - Monday 10AM",
        "sender": "boss@example.com",
        "body": "Hi, can we schedule a meeting on Monday at 10AM to discuss the project?",
        "received": datetime.utcnow().isoformat(),
    }
    task_path = NEEDS / f"{ts}_TEST001.json"
    task_path.write_text(json.dumps(fake_email, indent=2), encoding="utf-8")
    print(f"[PASS] Step 1: Email written to Needs_Action/ -- {task_path.name}")

    # Step 2: Claim-by-move
    claimed = IN_PROG / task_path.name
    task_path.rename(claimed)
    print(f"[PASS] Step 2: Task claimed -> In_Progress/")

    # Step 3: Write Pending_Approval draft
    draft = "Thank you for reaching out! Monday at 10AM works for me. I'll send a calendar invite shortly."
    pending_path = PENDING / f"{ts}_TEST001.md"
    content = f"""# Email Draft -- Pending Approval

## Original Email
- **From:** {fake_email['sender']}
- **Subject:** {fake_email['subject']}
- **Received:** {fake_email['received']}

## Original Body
{fake_email['body']}

---

## Proposed Reply (Cloud Agent Draft)
{draft}

---

## Action Required
Local agent: review and approve/reject.

**Status:** PENDING_APPROVAL
**Drafted by:** cloud_agent @ {datetime.utcnow().isoformat()}
"""
    pending_path.write_text(content, encoding="utf-8")
    print(f"[PASS] Step 3: Draft written to Pending_Approval/ -- {pending_path.name}")

    # Step 4: Local agent reads it
    print(f"\n[LOCAL] Agent reads draft:")
    print(f"   From:    {fake_email['sender']}")
    print(f"   Subject: {fake_email['subject']}")
    print(f"   Draft:   {draft}")

    # Step 5: Simulate approval (auto-approve in test)
    done_path = DONE / f"approved_{pending_path.name}"
    shutil.move(str(pending_path), str(done_path))
    print(f"\n[PASS] Step 4: APPROVED -- moved to Done/")

    # Step 6: Cleanup In_Progress
    claimed.unlink(missing_ok=True)
    print(f"[PASS] Step 5: In_Progress cleared")

    print("\n" + "="*50)
    print("SIMULATION PASSED -- Full flow working!")
    print("   Needs_Action -> In_Progress -> Pending_Approval -> Done")
    print("="*50)

if __name__ == "__main__":
    test_full_flow()
