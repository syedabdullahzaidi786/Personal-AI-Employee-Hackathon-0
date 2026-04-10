# Personal AI Employee — GIAIC Hackathon 0

**Status**: Platinum Tier — COMPLETE ✅ 💎
**Version**: 5.0.0
**Tier**: Platinum 💎
**Author**: Sharmeen Fatima — Creative Coderr

---

## 🎯 Project Overview

A local-first, autonomous **Personal AI Employee** system that monitors Gmail, LinkedIn, WhatsApp, manages Odoo ERP, posts on Facebook, Instagram & Twitter, generates CEO weekly audit reports — all with Human-in-the-Loop approval for every critical action.

Built for GIAIC Hackathon 0 using:
- **Claude AI** as reasoning engine
- **MCP Servers** (Model Context Protocol) for Email + Odoo tool integration
- **Playwright** for WhatsApp Web, Facebook & Instagram automation
- **Odoo XML-RPC** for ERP contact/record management
- **Gmail SMTP/IMAP** for real email integration
- **Obsidian Vault** as local-first knowledge store
- **Human-in-the-Loop (HITL)** approval system (Tier 0–4)
- **Ralph Wiggum Loop** for autonomous multi-step task completion

---

## 🏆 Tier Progress

| Tier | Status | Description |
|------|--------|-------------|
| 🥉 Bronze | ✅ Complete | Core skills, HITL, vault, file watchers, Agent Skills |
| 🥈 Silver | ✅ Complete | Gmail + LinkedIn LIVE, Plan.md loop, Email MCP, HITL workflow |
| 🥇 Gold | ✅ Complete | WhatsApp + Odoo + FB + IG + Twitter + MCP Servers + CEO Audit |
| 💎 Platinum | ✅ Complete | Cloud Agent (24/7) + Local Agent + Vault Sync + Odoo Cloud + Invoice Approval |

---

## 💎 Platinum Tier — Always-On Cloud + Local Executive

### Architecture
```
┌─────────────────────────────┐     ┌──────────────────────────────┐
│   ☁️  CLOUD (GitHub Codespaces) │     │   💻 LOCAL (PC)              │
│                             │     │                              │
│  cloud_agent.py             │────▶│  local_agent.py              │
│  - Gmail IMAP fetch         │     │  - Reads Pending_Approval/   │
│  - Groq AI draft replies    │     │  - Human approves/rejects    │
│  - Writes vault/.md files   │     │  - Gmail SMTP send           │
│  - 24/7 always running      │     │  - Logs to Done/             │
└─────────────────────────────┘     └──────────────────────────────┘
           │                                      │
           └──────────── Git Sync ────────────────┘
                    (vault/ excluded — secrets safe)
```

### ✅ Platinum Features Complete

| Feature | Status |
|---------|--------|
| Cloud Agent 24/7 (GitHub Codespaces) | ✅ LIVE |
| Email fetch via Gmail IMAP (Cloud) | ✅ LIVE |
| AI draft via Groq API (llama-3.1-8b-instant) | ✅ LIVE |
| Vault sync — Git-based | ✅ LIVE |
| Pending_Approval / Done / In_Progress folders | ✅ LIVE |
| Claim-by-move rule (anti double-work) | ✅ LIVE |
| Local Agent — Human Approval Flow | ✅ LIVE |
| Email send via Gmail SMTP (Local) | ✅ LIVE |
| Security — .env never synced, vault gitignored | ✅ LIVE |
| Odoo Community on Cloud (Docker + Codespaces) | ✅ LIVE |
| Cloud Agent → Odoo draft invoice (XML-RPC) | ✅ LIVE |
| Local Agent → Approve → Post invoice to Odoo | ✅ LIVE |

### Minimum Passing Gate — PROVEN ✅
```
Email arrives → Cloud Agent fetches → Groq drafts reply
→ Saved to vault/Pending_Approval/email/
→ Local Agent reads draft → Human approves [A]
→ Gmail SMTP sends email → Logged to vault/Done/

Invoice email arrives → Cloud Agent detects intent
→ Creates draft invoice in Odoo (XML-RPC)
→ Saved to vault/Pending_Approval/odoo/
→ Local Agent shows invoice → Human approves [A]
→ Invoice posted in Odoo → Logged to vault/Done/
```

### Run Platinum Tier
```bash
# On GitHub Codespaces (Cloud):
cd platinum_tier_business_layer
python cloud_agent.py       # Always-on email triage + Groq drafts

# On Local PC:
cd platinum_tier_business_layer
python local_agent.py       # Review drafts → Approve/Edit/Reject
```

### Environment Variables (Codespaces Secrets)
```env
GROQ_API_KEY=your_groq_key        # console.groq.com — free, no card
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

---

## ⚡ Gold Tier — Complete Feature List

### ✅ 1. WhatsApp Broadcast (Playwright — No Twilio)
- Uses your own WhatsApp account via WhatsApp Web automation
- QR scan once → session saved → auto-login every future run
- Broadcasts to multiple numbers in sequence
- **Real delivery confirmation** — counts DOM message nodes before/after send
- No Twilio account needed

```bash
python run_whatsapp_broadcast.py
python run_whatsapp_broadcast.py --numbers "+923001234567" --message "Hello!"
```

### ✅ 2. Odoo ERP Integration (XML-RPC + Visual Browser)
- Connects to Odoo Community (Docker, local)
- Create, Fetch, Update contacts/records via XML-RPC API
- Visual browser mode — Playwright browser opens and shows live Odoo UI
- Full HITL approval before any write operation
- Screenshots saved to `70-LOGS/`

### ✅ 3. Facebook Auto-Post (Playwright)
- Persistent browser session (login once, auto-login forever)
- Opens Facebook feed → finds composer → types post → clicks Post
- Handles popups automatically
- Post confirmed LIVE on Facebook

### ✅ 4. Instagram Auto-Post (Playwright)
- Persistent browser session
- Auto-generates post image via Pillow (no manual image needed)
- Uploads image → adds caption → clicks Share → LIVE on Instagram

### ✅ 5. Twitter/X Auto-Post (Playwright)
- Full login flow (email → password → unusual activity bypass)
- Finds tweet compose box via data-testid selectors
- Types tweet + hashtags → clicks Post → LIVE on X/Twitter

### ✅ 6. MCP Servers (Model Context Protocol)
Two real MCP servers so Claude can use Email and Odoo as native tools:

**Email MCP Server** (`mcp_servers/email_mcp_server.py`):
- `send_email(to, subject, body)` — sends via Gmail SMTP
- `email_health()` — checks SMTP connection

**Odoo MCP Server** (`mcp_servers/odoo_mcp_server.py`):
- `create_odoo_contact(name, email, phone, company)` — creates res.partner
- `fetch_odoo_contact(record_id)` — reads a contact
- `list_odoo_contacts(limit)` — lists recent contacts
- `update_odoo_contact(record_id, ...)` — updates a contact
- `odoo_health()` — checks Odoo connection

Register in `claude_desktop_config.json` — see `mcp_servers/claude_desktop_config_snippet.json`.

### ✅ 7. CEO Weekly Audit + Briefing
- Reads all skill logs from `70-LOGS/` (HITL, Orchestrator, Watchers, Actions)
- Generates professional Markdown CEO briefing report
- Saved to `obsidian-vault/50-BUSINESS/weekly/`
- Shows HITL approval rates, orchestrator success rate, watcher events, action skill KPIs
- Overall health: HEALTHY / DEGRADED / CRITICAL

```bash
python run_ceo_audit.py            # current week
python run_ceo_audit.py --print    # also print full report to terminal
```

### ✅ 8. Error Recovery & Graceful Degradation
- Every skill has `health_check()` — never raises
- All operations wrapped in try/except — errors surface as structured results
- Failed operations logged to `70-LOGS/` with full context

### ✅ 9. Comprehensive Audit Logging
- `70-LOGS/email/YYYY-MM-DD.jsonl` — email action events
- `70-LOGS/odoo/YYYY-MM-DD.jsonl` — Odoo action events
- `70-LOGS/hitl/pending/` + `completed/` — HITL request JSON files
- `70-LOGS/orchestrator/daily/` — orchestrator run logs
- `70-LOGS/watchers/<id>/daily/` — per-watcher poll logs

### ✅ 10. Ralph Wiggum Loop
- Autonomous multi-step task completion loop
- Located in `silver_tier_core_autonomy/ralph/`
- Runs tasks from queue, logs each step, supports HITL gates
- Health monitoring + failure recovery built-in

### ✅ 11. All AI Functionality as Agent Skills
Every feature is implemented as a composable Agent Skill:
`EmailAction`, `OdooAction`, `BrowserAction`, `CeoAuditSkill`, `RalphRunner`, `HITLSkill`

---

## 🥈 Silver Tier (included in Gold)

### ✅ Gmail Auto-Send (HITL Flow)
```
Draft Email → Human Approves → Gmail SMTP → Delivered
```

### ✅ Gmail IMAP Watcher
- Fetches unread emails, parses subject/sender/attachments

### ✅ LinkedIn Auto-Post
- Shadow DOM traversal for post editor
- React event dispatch to enable Post button

### ✅ Plan.md Loop + Scheduling
- Claude reasoning loop that creates `Plans/` files
- Task scheduler in `silver_tier_core_autonomy/scheduler/`

---

## 📁 Project Structure

```
Hackathon_0/
├── mcp_servers/                    # 🆕 MCP Servers (Gold Tier)
│   ├── email_mcp_server.py         #   Gmail SMTP as MCP tool
│   ├── odoo_mcp_server.py          #   Odoo ERP as MCP tool
│   └── claude_desktop_config_snippet.json
│
├── golden_tier_external_world/
│   ├── watchers/
│   │   ├── gmail/                  # Gmail IMAP watcher
│   │   ├── linkedin/               # LinkedIn watcher
│   │   └── whatsapp/               # WhatsApp Playwright client (no Twilio)
│   └── actions/
│       ├── facebook/               # PlaywrightFacebookPoster
│       ├── instagram/              # PlaywrightInstagramPoster
│       ├── twitter/                # PlaywrightTwitterPoster
│       ├── email/                  # EmailAction + RealEmailAdapter (SMTP)
│       ├── linkedin/               # LinkedInPoster
│       ├── odoo/                   # Odoo XML-RPC Action
│       └── whatsapp/               # WhatsApp Broadcast Action
│
├── platinum_tier_business_layer/
│   └── ceo_audit/                  # CEO Weekly Audit Skill
│       ├── collector.py            #   Log aggregator
│       ├── reporter.py             #   Markdown report generator
│       └── __init__.py             #   CeoAuditSkill facade
│
├── silver_tier_core_autonomy/
│   ├── ralph/                      # Ralph Wiggum autonomous loop
│   ├── plan_loop/                  # Plan.md generator
│   └── scheduler/                  # Task scheduler
│
├── bronze_tier_governance/
│   └── hitl/                       # Human-in-the-Loop (Tiers 0–4)
│
├── obsidian-vault/
│   ├── 50-BUSINESS/weekly/         # CEO briefing reports
│   ├── Pending_Approval/           # HITL queue
│   ├── Done/                       # Completed tasks
│   ├── Plans/                      # AI-generated plans
│   └── 70-LOGS/                    # All logs + screenshots
│
├── history/prompts/                # Prompt History Records (PHRs)
│
├── run_gold_live.py                # 🚀 WhatsApp + Odoo LIVE (visual mode)
├── run_social_live.py              # 🚀 Facebook + Instagram + Twitter LIVE
├── run_silver_live.py              # 🚀 LinkedIn + Gmail LIVE
├── run_whatsapp_broadcast.py       # 🚀 WhatsApp Broadcast
├── run_ceo_audit.py                # 🚀 CEO Weekly Audit Report
└── .env                            # Credentials (gitignored — never commit)
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install playwright selenium webdriver-manager python-dotenv pillow mcp
playwright install chromium
```

### 2. Configure Credentials
Copy `.env.example` to `.env` and fill in:
```env
# Gmail
GMAIL_ACCOUNT_EMAIL=your@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
EMAIL_RECIPIENTS=friend@gmail.com

# LinkedIn
LINKEDIN_EMAIL=your@gmail.com
LINKEDIN_PASSWORD=yourpassword
LINKEDIN_PROFILE_URL=https://www.linkedin.com/in/your-name/

# Twitter/X
TWITTER_EMAIL=your@gmail.com
TWITTER_PASSWORD=yourpassword
TWITTER_USERNAME=your_handle

# Facebook
FACEBOOK_EMAIL=your@gmail.com
FACEBOOK_PASSWORD=yourpassword

# Instagram
INSTAGRAM_USERNAME=your_handle
INSTAGRAM_PASSWORD=yourpassword

# WhatsApp Broadcast
WA_BROADCAST_NUMBERS=+923001234567,+923009876543
WA_SESSION_DIR=wa_session

# Odoo ERP
ODOO_URL=http://localhost:8069
ODOO_DB=mycompany
ODOO_USERNAME=admin
ODOO_PASSWORD=admin
```

### 3. Run Odoo (Docker — one time setup)
```bash
docker run -d --name odoo17 -p 8069:8069 odoo:17
# Open http://localhost:8069 → create database → login
```

### 4. Run Gold Tier
```bash
# WhatsApp + Odoo (visual browser)
python run_gold_live.py

# Facebook + Instagram + Twitter
python run_social_live.py

# CEO Weekly Audit Report
python run_ceo_audit.py

# WhatsApp Broadcast only
python run_whatsapp_broadcast.py
```

### 5. Run MCP Servers (for Claude Desktop)
```bash
python mcp_servers/email_mcp_server.py
python mcp_servers/odoo_mcp_server.py
```
See `mcp_servers/claude_desktop_config_snippet.json` for Claude Desktop registration.

---

## 🔐 HITL Approval Tiers

| Tier | Risk Level | Approval |
|------|-----------|---------|
| 0 | Read-only | Auto-approved |
| 1 | Low risk | Auto-approved |
| 2 | Medium risk | Human required |
| 3 | High risk | Human required |
| 4 | Critical | Human + full audit |

All social media posts, emails, and Odoo writes run through HITL before executing.

---

## 🛠️ Key Technical Highlights

- **MCP Protocol** — Real Model Context Protocol servers so Claude can call Email and Odoo as native tools, not just Python functions
- **Playwright persistent sessions** — Login once per platform, sessions saved to disk, auto-login on every future run
- **DOM count verification** — WhatsApp send is confirmed by counting `div.message-out` nodes before and after — no false positives
- **CEO Audit** — Reads JSONL + pipe-delimited logs from all skills, aggregates weekly KPIs, generates executive Markdown briefing
- **Ralph Wiggum Loop** — Autonomous multi-step orchestrator with HITL gates, failure recovery, and step-level logging
- **Shadow DOM traversal** — LinkedIn post editor is inside Shadow DOM; traversed via JS `createTreeWalker`
- **Auto-image generation** — Instagram requires an image; Pillow generates branded post image automatically
- **Fail-safe architecture** — Every skill returns structured result, never raises exceptions at boundary

---

## 📊 Gold Tier — Full Status

| Component | Status | Notes |
|-----------|--------|-------|
| Gmail IMAP Watcher | ✅ LIVE | Real IMAP SSL |
| Gmail SMTP Sender | ✅ LIVE | App Password auth |
| Email MCP Server | ✅ LIVE | MCP protocol — Claude tool |
| LinkedIn Auto-Post | ✅ LIVE | Shadow DOM + React events |
| WhatsApp Broadcast | ✅ LIVE | Playwright Web, no Twilio |
| Odoo ERP (XML-RPC) | ✅ LIVE | Docker local instance |
| Odoo MCP Server | ✅ LIVE | MCP protocol — Claude tool |
| Twitter/X Post | ✅ LIVE | Playwright — tweets working |
| Facebook Post | ✅ LIVE | Playwright — persistent session |
| Instagram Post | ✅ LIVE | Playwright — auto image |
| CEO Weekly Audit | ✅ LIVE | Markdown briefing to vault |
| Ralph Wiggum Loop | ✅ Complete | Autonomous multi-step tasks |
| HITL System | ✅ Complete | Tiers 0–4 |
| Audit Logging | ✅ Complete | JSONL per skill per day |

---

## 📸 Live Evidence

Screenshots auto-saved in `obsidian-vault/70-LOGS/`:
- `facebook_posted.png` — Facebook post LIVE
- `instagram_posted.png` — Instagram post LIVE
- `twitter_posted.png` — Tweet posted on X
- `odoo_contact_created.png` — Odoo record created
- `odoo_contact_updated.png` — Odoo record updated

CEO Reports saved in `obsidian-vault/50-BUSINESS/weekly/`

---

## 🔒 Security

- All credentials stored in `.env` only — never hardcoded, never committed
- `.gitignore` excludes `.env`, `wa_session/`, browser session folders
- HITL gates prevent autonomous execution of high-risk actions
- Credential tokens passed via parameter, never logged

---

## 📝 License

Personal project for GIAIC Hackathon 0.

---

**Last Updated**: 2026-04-09
**Tier**: Platinum 💎 — COMPLETE ✅ (Cloud+Local Flow LIVE + Odoo Invoice Approval LIVE)
**Author**: Sharmeen Fatima — Creative Coderr
"# Personal-AI-Employee-Hackathon-0" 
