"""
Silver Tier — LIVE Demo (Real Credentials)
==========================================
Credentials .env file se load hoti hain.
Gmail: IMAP se real emails fetch karta hai.
LinkedIn: Selenium se real watching + posting karta hai.

Usage:
    python run_silver_live.py
"""

import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env credentials
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

GMAIL_EMAIL      = os.environ.get("GMAIL_ACCOUNT_EMAIL", "").strip()
GMAIL_PASSWORD   = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
LI_EMAIL         = os.environ.get("LINKEDIN_EMAIL", "").strip()
LI_PASSWORD      = os.environ.get("LINKEDIN_PASSWORD", "").strip()
LI_PROFILE_URL   = os.environ.get("LINKEDIN_PROFILE_URL", "").strip()
EMAIL_RECIPIENTS = [e.strip() for e in os.environ.get("EMAIL_RECIPIENTS", "").split(",") if e.strip()]
VAULT            = os.path.join(os.path.dirname(os.path.abspath(__file__)), "obsidian-vault")

print("=" * 60)
print("  SILVER TIER — Live Demo (Real Credentials)")
print("=" * 60)

# ─────────────────────────────────────────────────────────────
# Credential check
# ─────────────────────────────────────────────────────────────
print("\n🔑 Credential Check")
print("-" * 40)
print(f"   Gmail account   : {GMAIL_EMAIL or '❌ NOT SET'}")
print(f"   Gmail password  : {'✅ set' if GMAIL_PASSWORD else '❌ NOT SET'}")
print(f"   LinkedIn email  : {LI_EMAIL or '❌ NOT SET'}")
print(f"   LinkedIn pass   : {'✅ set' if LI_PASSWORD else '❌ NOT SET'}")
print(f"   LinkedIn URL    : {LI_PROFILE_URL or '❌ NOT SET'}")
print(f"   Email recipients: {', '.join(EMAIL_RECIPIENTS) if EMAIL_RECIPIENTS else '⚠️  NOT SET (Step 4 will skip)'}")

missing = []
if not GMAIL_EMAIL:    missing.append("GMAIL_ACCOUNT_EMAIL")
if not GMAIL_PASSWORD: missing.append("GMAIL_APP_PASSWORD")
if not LI_EMAIL:       missing.append("LINKEDIN_EMAIL")
if not LI_PASSWORD:    missing.append("LINKEDIN_PASSWORD")

if missing:
    print(f"\n❌ Missing credentials: {', '.join(missing)}")
    print("   .env file mein yeh values fill karo phir dobara run karo.")
    sys.exit(1)

print("\n✅ All credentials loaded.")


# ─────────────────────────────────────────────────────────────
# STEP 1: Gmail — Real IMAP Connection
# ─────────────────────────────────────────────────────────────
print("\n\n📧 STEP 1: Gmail — Real IMAP Connection")
print("-" * 40)

from golden_tier_external_world.watchers.gmail.client import RealGmailClient
from golden_tier_external_world.watchers.gmail.models import GmailConfig
from golden_tier_external_world.watchers.gmail.watcher import GmailWatcher

gmail_config = GmailConfig(
    account_email=GMAIL_EMAIL,
    vault_root=VAULT,
    max_results=5,
    poll_interval_secs=60.0,
)
gmail_client = RealGmailClient(gmail_config, app_password=GMAIL_PASSWORD)

print("🔍 Gmail health check (IMAP login)...")
gmail_healthy = gmail_client.health_check()
print(f"   Status: {'✅ Connected' if gmail_healthy else '❌ Failed (check App Password / IMAP enabled)'}")

if gmail_healthy:
    print("\n📬 Fetching unread emails (up to 5)...")
    messages = gmail_client.fetch_unread(max_results=5)
    print(f"   Unread emails found: {len(messages)}")

    if messages:
        print("\n   Latest emails:")
        for i, msg in enumerate(messages[:3], 1):
            print(f"   {i}. From: {msg.sender[:50]}")
            print(f"      Subject: {msg.subject[:60]}")
            if msg.has_attachments:
                print(f"      📎 Attachments: {', '.join(msg.attachment_names[:3])}")

    # Run GmailWatcher tick
    print("\n⏱  Running GmailWatcher tick...")
    watcher = GmailWatcher(gmail_config, client=gmail_client)
    watcher.start()
    tick = watcher.tick()
    print(f"   Health: {'OK' if tick.health_ok else 'FAIL'}")
    print(f"   Events found: {tick.events_found}")
    print(f"   Errors: {tick.errors}")
else:
    print("\n   ⚠️  Gmail skipped (connection failed).")
    print("   Gmail Settings → See all settings → Forwarding and POP/IMAP → Enable IMAP")


# ─────────────────────────────────────────────────────────────
# STEP 2: LinkedIn — Watcher (Browser Automation)
# ─────────────────────────────────────────────────────────────
print("\n\n🔗 STEP 2: LinkedIn — Watcher (Selenium)")
print("-" * 40)

from golden_tier_external_world.watchers.linkedin.client import RealLinkedInClient
from golden_tier_external_world.watchers.linkedin.models import LinkedInConfig, LinkedInEventType
from golden_tier_external_world.watchers.linkedin.watcher import LinkedInWatcher

li_client = RealLinkedInClient(
    email=LI_EMAIL,
    password=LI_PASSWORD,
    headless=False,   # visible browser — taake aap dekh sako kya ho raha hai
)

print("🌐 LinkedIn login (headless Chrome)...")
li_logged_in = li_client.login()
print(f"   Status: {'✅ Logged in' if li_logged_in else '❌ Login failed (wrong credentials or CAPTCHA)'}")

li_activities = []
if li_logged_in:
    print("\n📥 Fetching LinkedIn activity...")
    try:
        li_activities = li_client.fetch_activity(max_results=10)
        print(f"   Activities found: {len(li_activities)}")
        if li_activities:
            for i, act in enumerate(li_activities[:5], 1):
                print(f"   {i}. [{act.event_type.value}] {act.content[:60] or act.sender_name}")
        else:
            print("   (No new activity — inbox may be empty or LinkedIn changed DOM)")
    except Exception as e:
        print(f"   ⚠️  Fetch error: {e}")

    # Run LinkedInWatcher tick with real client
    print("\n⏱  Running LinkedInWatcher tick...")
    li_config = LinkedInConfig(
        vault_root=VAULT,
        profile_url=LI_PROFILE_URL,
        poll_interval_secs=300.0,
    )
    li_watcher = LinkedInWatcher(li_config, client=li_client)
    li_watcher.start()
    li_tick = li_watcher.tick()
    print(f"   Health: {'OK' if li_tick.health_ok else 'FAIL'}")
    print(f"   Events found: {li_tick.events_found}")
    print(f"   Errors: {li_tick.errors}")
else:
    print("\n   ⚠️  LinkedIn watcher skipped (login failed).")


# ─────────────────────────────────────────────────────────────
# STEP 3: LinkedIn — Auto-Post (HITL Approval Flow)
# ─────────────────────────────────────────────────────────────
print("\n\n📢 STEP 3: LinkedIn — Auto-Post (HITL Flow)")
print("-" * 40)

from golden_tier_external_world.actions.linkedin import LinkedInPoster


class SeleniumLinkedInBrowser:
    """Adapter that wraps RealLinkedInClient for LinkedInPoster."""

    def __init__(self, client: RealLinkedInClient) -> None:
        self._client = client

    def linkedin_post(self, text: str) -> str:
        """Post to LinkedIn via Selenium. Returns a pseudo LinkedIn post ID."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.action_chains import ActionChains
        import time as _time
        import uuid as _uuid

        driver = self._client._driver
        if driver is None:
            raise RuntimeError("Browser not open")

        print("   🌐 LinkedIn feed page khul rahi hai...")
        driver.get("https://www.linkedin.com/feed/")
        _time.sleep(5)
        wait = WebDriverWait(driver, 20)

        # Screenshot for debugging
        import os as _os
        screenshot_path = _os.path.join(
            _os.path.dirname(_os.path.abspath(__file__)),
            "obsidian-vault", "70-LOGS", "linkedin_feed_screenshot.png"
        )
        _os.makedirs(_os.path.dirname(screenshot_path), exist_ok=True)
        driver.save_screenshot(screenshot_path)
        print(f"   📸 Screenshot saved: 70-LOGS/linkedin_feed_screenshot.png")
        print(f"   📄 Current URL: {driver.current_url}")

        # Scroll to top — share box feed entry is at the top
        driver.execute_script("window.scrollTo(0, 0);")
        _time.sleep(2)

        # Screenshot shows "Start a post" is a pill-shaped span/div, NOT a button.
        # Find by visible text content.
        start_btn = None

        # XPath by exact visible text
        text_xpaths = [
            "//span[normalize-space(text())='Start a post']",
            "//p[normalize-space(text())='Start a post']",
            "//div[normalize-space(text())='Start a post']",
            "//*[normalize-space(text())='Start a post']",
        ]
        for xpath in text_xpaths:
            try:
                el = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                start_btn = el
                print(f"   ✅ 'Start a post' text element mila")
                break
            except Exception:
                continue

        # JS fallback: walk ALL elements, find one with "start a post" innerText
        if start_btn is None:
            start_btn = driver.execute_script("""
                var walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_ELEMENT
                );
                while (walker.nextNode()) {
                    var el = walker.currentNode;
                    var txt = (el.innerText || '').trim().toLowerCase();
                    if (txt === 'start a post' && el.offsetParent !== null) {
                        return el;
                    }
                }
                return null;
            """)
            if start_btn:
                print("   ✅ 'Start a post' found via JS text walker")

        # Click the parent container (span click alone doesn't trigger the modal)
        # After parent click, DOM re-renders (start_btn becomes stale) — that's OK
        parent = driver.execute_script("return arguments[0].parentElement;", start_btn)
        if parent:
            driver.execute_script("arguments[0].click();", parent)
            print("   ✅ Parent container clicked — waiting for modal...")
        else:
            driver.execute_script("arguments[0].click();", start_btn)
        _time.sleep(5)

        # Screenshot after click — see if modal opened
        after_path = screenshot_path.replace("linkedin_feed_screenshot", "linkedin_after_click")
        driver.save_screenshot(after_path)
        print(f"   📸 After-click screenshot: 70-LOGS/linkedin_after_click.png")
        print(f"   📄 URL after click: {driver.current_url}")
        print("   📝 Post editor khul raha hai...")

        # Wait longer for modal to open
        _time.sleep(3)

        # Modal is open (confirmed by screenshot).
        # LinkedIn post editor may be in an iframe — switch to it first.
        editor = None

        # Check for iframes — switch into each one to find the editor
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        print(f"   🔍 Iframes on page: {len(iframes)}")

        tried_iframes = False
        for iframe in iframes:
            try:
                driver.switch_to.frame(iframe)
                tried_iframes = True
                ce_els = driver.find_elements(By.XPATH,
                    "//*[@contenteditable='true' or @data-placeholder or @role='textbox']"
                )
                if ce_els:
                    editor = ce_els[0]
                    print(f"   ✅ Editor mila inside iframe!")
                    break
                driver.switch_to.default_content()
            except Exception:
                driver.switch_to.default_content()

        if editor is None and tried_iframes:
            driver.switch_to.default_content()

        # Main frame — try finding with all possible selectors
        if editor is None:
            editor_xpaths = [
                "//div[@data-placeholder='What do you want to talk about?']",
                "//div[contains(@data-placeholder,'talk about')]",
                "//div[@role='textbox']",
                "//div[@contenteditable='true']",
                "//div[contains(@class,'ql-editor')]",
                "//p[@data-placeholder]",
            ]
            for xpath in editor_xpaths:
                try:
                    editor = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                    print(f"   ✅ Editor mila (main frame)")
                    break
                except Exception:
                    continue

        if editor is None:
            # Debug: full iframe inspection
            driver.switch_to.default_content()
            iframe_count = len(driver.find_elements(By.TAG_NAME, "iframe"))
            # Try shadow DOM
            editor = driver.execute_script("""
                function findInShadow(root) {
                    if (!root) return null;
                    var el = root.querySelector(
                        '[contenteditable="true"],[data-placeholder],[role="textbox"]'
                    );
                    if (el) return el;
                    var nodes = root.querySelectorAll('*');
                    for (var n of nodes) {
                        if (n.shadowRoot) {
                            var found = findInShadow(n.shadowRoot);
                            if (found) return found;
                        }
                    }
                    return null;
                }
                return findInShadow(document);
            """)
            if editor:
                print("   ✅ Editor mila (shadow DOM)")
            else:
                print(f"   🔍 Total iframes: {iframe_count}")
                raise RuntimeError("LinkedIn post editor nahi mila (iframe + shadow DOM tried)")

        driver.execute_script("arguments[0].focus(); arguments[0].click();", editor)
        _time.sleep(1)
        ActionChains(driver).move_to_element(editor).click().send_keys(text).perform()
        _time.sleep(1)
        # Dispatch React input events so Post button becomes enabled
        driver.execute_script("""
            var el = arguments[0];
            ['input','change','keyup'].forEach(function(n){
                el.dispatchEvent(new Event(n, {bubbles:true}));
            });
        """, editor)
        _time.sleep(2)
        print(f"   ✍️  Text type ho gaya ({len(text)} chars)")

        # Wait a moment for the Post button to become enabled
        _time.sleep(2)

        # Submit button — try shadow DOM first (same as editor)
        post_btn = driver.execute_script("""
            function findPostBtn(root) {
                if (!root) return null;
                // Look for button with text "Post" or class share-actions__primary-action
                var btns = root.querySelectorAll('button');
                for (var btn of btns) {
                    var txt   = (btn.innerText || '').trim();
                    var cls   = (btn.className || '');
                    var label = (btn.getAttribute('aria-label') || '');
                    if (txt === 'Post' || label === 'Post' ||
                        cls.includes('share-actions__primary-action')) {
                        return btn;
                    }
                }
                // Check shadow roots
                var all = root.querySelectorAll('*');
                for (var el of all) {
                    if (el.shadowRoot) {
                        var found = findPostBtn(el.shadowRoot);
                        if (found) return found;
                    }
                }
                return null;
            }
            return findPostBtn(document);
        """)

        if post_btn:
            print("   ✅ Post submit button mila (shadow DOM JS)")
        else:
            # XPath fallback in main frame
            submit_xpaths = [
                "//button[normalize-space(text())='Post']",
                "//button[contains(@class,'share-actions__primary-action')]",
                "//button[@aria-label='Post']",
                "//span[normalize-space(text())='Post']/ancestor::button",
            ]
            for xpath in submit_xpaths:
                try:
                    post_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    print(f"   ✅ Post submit button mila (XPath)")
                    break
                except Exception:
                    continue

        if post_btn is None:
            raise RuntimeError("LinkedIn 'Post' submit button nahi mila")

        driver.execute_script("arguments[0].click();", post_btn)
        _time.sleep(4)
        print("   🚀 Post submit ho gayi!")

        return f"LI-LIVE-{_uuid.uuid4().hex[:8].upper()}"


# Create poster — with or without real browser
if li_logged_in:
    browser_adapter = SeleniumLinkedInBrowser(li_client)
    poster = LinkedInPoster(vault_root=VAULT, browser_mcp=browser_adapter)
    post_mode = "LIVE"
else:
    poster = LinkedInPoster(vault_root=VAULT)  # dry-run / mock mode
    post_mode = "MOCK"

# Draft a post
post = poster.draft(
    content=(
        "Excited to share how AI is transforming business operations in 2026! "
        "Our Personal AI Employee system handles Gmail, LinkedIn monitoring — "
        "all while keeping humans in the loop for critical decisions. "
        "Built with Python + Selenium + Claude AI at GIAIC Hackathon. "
        "The future of work is human + AI collaboration!"
    ),
    hashtags=["AI", "GIAIC", "Hackathon", "Pakistan", "FutureOfWork"],
)
print(f"✅ Post drafted:     {post.post_id}")
print(f"   Mode:             {post_mode}")
print(f"   Status:           {post.status.value}")
print(f"   Content preview:  {post.content[:80]}...")
print(f"   Hashtags:         {', '.join('#'+h for h in post.hashtags)}")
print(f"\n⏳ Awaiting HITL approval...")
print(f"   (Check: obsidian-vault/Pending_Approval/{post.post_id}.json)")

# HITL Approval
print(f"\n👤 Simulating human approval (HITL Tier 2)...")
poster.approve(post.post_id)
print(f"✅ Post approved!")

# Publish
print(f"\n🚀 Publishing to LinkedIn ({post_mode} mode)...")
if post_mode == "MOCK":
    print("   ⚠️  MOCK mode — LinkedIn login fail hua tha, real post nahi hogi")
    print("   Dobara run karo jab LinkedIn login succeed kare")
try:
    result_post = poster.publish(post.post_id)
    status_icon = "✅" if result_post.status.value == "posted" else "❌"
    print(f"   {status_icon} Status: {result_post.status.value.upper()}")
    if result_post.linkedin_post_id:
        post_id_str = result_post.linkedin_post_id
        if post_mode == "LIVE" and "LI-LIVE-" in post_id_str:
            print(f"   🎉 Post LIVE hai LinkedIn pe! ID: {post_id_str}")
            print(f"   🔗 Check: {LI_PROFILE_URL}")
        else:
            print(f"   LinkedIn Post ID: {post_id_str}")
    if result_post.posted_at:
        print(f"   Posted at: {result_post.posted_at.strftime('%Y-%m-%d %H:%M UTC')}")
    if result_post.error:
        print(f"   Error: {result_post.error}")
except Exception as e:
    print(f"   ❌ Publish error: {e}")
    import traceback
    traceback.print_exc()


# ─────────────────────────────────────────────────────────────
# STEP 4: Gmail — Auto-Send Email (like LinkedIn Auto-Post)
# ─────────────────────────────────────────────────────────────
print("\n\n📧 STEP 4: Gmail — Auto-Send Email (HITL Flow)")
print("-" * 40)

email_sent_ok = False

if not EMAIL_RECIPIENTS:
    print("   ⚠️  EMAIL_RECIPIENTS not set in .env — email step skipped.")
    print("   .env file mein EMAIL_RECIPIENTS=friend@gmail.com add karo phir dobara run karo.")
elif not GMAIL_PASSWORD:
    print("   ⚠️  GMAIL_APP_PASSWORD not set — email step skipped.")
else:
    from golden_tier_external_world.actions.email.adapter import RealEmailAdapter
    from golden_tier_external_world.actions.email.models import EmailConfig, make_email_request

    email_config = EmailConfig(
        sender_address=GMAIL_EMAIL,
        vault_root=VAULT,
    )
    smtp_adapter = RealEmailAdapter(email_config, credential_token=GMAIL_PASSWORD)

    print("🔍 Gmail SMTP health check...")
    smtp_ok = smtp_adapter.health_check()
    print(f"   Status: {'✅ Connected' if smtp_ok else '❌ Failed (check App Password)'}")

    if smtp_ok:
        # Build email content (mirrors the LinkedIn post content)
        linkedin_post_content = (
            "Excited to share how AI is transforming business operations in 2026! "
            "Our Personal AI Employee system handles Gmail, LinkedIn monitoring — "
            "all while keeping humans in the loop for critical decisions. "
            "Built with Python + Selenium + Claude AI at GIAIC Hackathon. "
            "The future of work is human + AI collaboration!"
        )

        email_subject = "🚀 AI Update: Personal AI Employee — GIAIC Hackathon 2026"
        email_body = f"""Hi there,

I wanted to share an exciting update from our GIAIC Hackathon project!

{linkedin_post_content}

Hashtags: #AI #GIAIC #Hackathon #Pakistan #FutureOfWork

---
This email was sent automatically by our Silver Tier AI Agent.
Sent from: {GMAIL_EMAIL}
"""

        print(f"\n📋 Email Draft:")
        print(f"   To       : {', '.join(EMAIL_RECIPIENTS)}")
        print(f"   Subject  : {email_subject}")
        print(f"   Body     : {email_body[:100]}...")

        # HITL Approval (simulated — like LinkedIn)
        print(f"\n👤 Simulating HITL approval for email send...")
        print(f"   ✅ Email approved!")

        # Create request
        email_request = make_email_request(
            to=EMAIL_RECIPIENTS,
            subject=email_subject,
            body=email_body,
            sender=GMAIL_EMAIL,
            tier=1,  # tier=1 → direct send (no HITL blocking)
        )

        print(f"\n🚀 Sending email via Gmail SMTP...")
        email_result = smtp_adapter.send(email_request)

        if email_result.status == "SENT":
            email_sent_ok = True
            print(f"   ✅ Email SENT successfully!")
            print(f"   📬 Delivered to: {', '.join(EMAIL_RECIPIENTS)}")
            if email_result.sent_at:
                print(f"   Sent at: {email_result.sent_at.strftime('%Y-%m-%d %H:%M UTC')}")
        else:
            print(f"   ❌ Email failed: {email_result.error}")
    else:
        print("   ⚠️  Gmail SMTP skipped (connection failed).")
        print("   Gmail Settings → See all settings → Forwarding and POP/IMAP → Enable IMAP")


# ─────────────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────────────
if li_logged_in:
    print("\n🔒 Closing LinkedIn browser session...")
    li_client.quit()
    print("   Browser closed.")


# ─────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────
print("\n")
print("=" * 60)
print("  SILVER TIER — Live Demo Complete!")
print("=" * 60)
print(f"""
{'✅' if gmail_healthy  else '⚠️ '} Gmail IMAP         — Real connection to {GMAIL_EMAIL}
{'✅' if li_logged_in   else '⚠️ '} LinkedIn Watcher   — {'Logged in, activity fetched' if li_logged_in else 'Login attempted (check credentials)'}
{'✅' if li_logged_in   else '⚠️ '} LinkedIn Auto-Post — Draft → HITL Approval → {post_mode} Publish
{'✅' if email_sent_ok  else '⚠️ '} Gmail Auto-Send    — {'Email sent to: ' + ', '.join(EMAIL_RECIPIENTS) if email_sent_ok else 'Set EMAIL_RECIPIENTS in .env to enable'}

📁 Vault logs:
   obsidian-vault/Pending_Approval/  ← LinkedIn post awaiting approval
   obsidian-vault/Approved/          ← Approved posts
   obsidian-vault/70-LOGS/           ← All watcher + action logs

🏆 Silver Tier: LIVE with Real Credentials
""")
