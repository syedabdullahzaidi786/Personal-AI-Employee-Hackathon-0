<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=30&duration=3000&pause=1000&color=A855F7&center=true&vCenter=true&width=700&lines=Personal+AI+Employee+%F0%9F%A4%96;GIAIC+Hackathon+0+%F0%9F%9A%80;Platinum+Tier+%F0%9F%92%8E+COMPLETE" alt="Typing SVG" />

<br/>

![Version](https://img.shields.io/badge/Version-5.0.0-a855f7?style=for-the-badge&logo=semver&logoColor=white)
![Tier](https://img.shields.io/badge/Tier-Platinum_💎-e879f9?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-COMPLETE_✅-22c55e?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-3b82f6?style=for-the-badge&logo=python&logoColor=white)
![Claude AI](https://img.shields.io/badge/Claude-AI_Engine-f97316?style=for-the-badge&logo=anthropic&logoColor=white)
![License](https://img.shields.io/badge/License-Personal_Project-64748b?style=for-the-badge)

<br/>

> **A local-first, autonomous Personal AI Employee** that monitors Gmail, LinkedIn, WhatsApp,  
> manages Odoo ERP, posts on Facebook, Instagram & Twitter, and generates CEO audit reports —  
> all with **Human-in-the-Loop approval** for every critical action.

<br/>

**Author**: [Syed Abdullah Zaidi](https://github.com/syedabdullahzaidi786) &nbsp;|&nbsp; **Hackathon**: GIAIC Q4 Hackathon 0 &nbsp;|&nbsp; **Last Updated**: 2026-04-10

</div>

---

## 📑 Table of Contents

- [🏆 Tier Progress](#-tier-progress)
- [💎 Platinum Tier](#-platinum-tier--always-on-cloud--local-executive)
- [⚡ Gold Tier Features](#-gold-tier--complete-feature-list)
- [🥈 Silver Tier](#-silver-tier)
- [📁 Project Structure](#-project-structure)
- [🚀 Quick Start](#-quick-start)
- [🔐 HITL Approval System](#-hitl-approval-tiers)
- [🛠️ Technical Highlights](#%EF%B8%8F-key-technical-highlights)
- [📊 Full Status Dashboard](#-gold-tier--full-status)
- [🔒 Security](#-security)

---

## 🏆 Tier Progress

<div align="center">

| Tier | Badge | Status | Description |
|:----:|:-----:|:------:|:------------|
| 🥉 **Bronze** | ![Bronze](https://img.shields.io/badge/Bronze-Complete-cd7f32?style=flat-square) | ✅ | Core skills, HITL governance, vault, file watchers, Agent Skills |
| 🥈 **Silver** | ![Silver](https://img.shields.io/badge/Silver-Complete-c0c0c0?style=flat-square) | ✅ | Gmail + LinkedIn LIVE, Plan.md loop, Email MCP, HITL workflow |
| 🥇 **Gold** | ![Gold](https://img.shields.io/badge/Gold-Complete-ffd700?style=flat-square) | ✅ | WhatsApp + Odoo + FB + IG + Twitter + MCP Servers + CEO Audit |
| 💎 **Platinum** | ![Platinum](https://img.shields.io/badge/Platinum-Complete-a855f7?style=flat-square) | ✅ | Cloud Agent 24/7 + Local Agent + Vault Sync + Odoo Cloud + Invoice Approval |

</div>

---

## 💎 Platinum Tier — Always-On Cloud + Local Executive

### 🏗️ Architecture

```
┌──────────────────────────────────────┐        ┌───────────────────────────────────────┐
│  ☁️  CLOUD  (GitHub Codespaces)       │        │  💻  LOCAL PC                          │
│                                      │        │                                       │
│  📧 Gmail IMAP fetch (real-time)     │        │  📬 Reads Pending_Approval/ folder    │
│  🤖 Groq AI drafts reply             │───────▶│  👤 Human approves / rejects / edits  │
│  📝 Writes vault .md files           │  Git   │  📤 Gmail SMTP sends approved email   │
│  🔄 Runs 24/7 always-on              │  Sync  │  📋 Logs decisions to vault/Done/     │
│                                      │        │                                       │
└──────────────────────────────────────┘        └───────────────────────────────────────┘
              │                                               │
              └─────────────── 🔁 Git Sync ──────────────────┘
                          (vault/ excluded — secrets safe)
```

### ✅ Platinum Features

<div align="center">

| Feature | Status |
|:--------|:------:|
| Cloud Agent 24/7 (GitHub Codespaces) | ✅ **LIVE** |
| Email fetch via Gmail IMAP (Cloud) | ✅ **LIVE** |
| AI draft via Groq API (llama-3.1-8b-instant) | ✅ **LIVE** |
| Vault sync — Git-based | ✅ **LIVE** |
| Pending_Approval / Done / In_Progress folders | ✅ **LIVE** |
| Claim-by-move rule (anti double-work) | ✅ **LIVE** |
| Local Agent — Human Approval Flow | ✅ **LIVE** |
| Email send via Gmail SMTP (Local) | ✅ **LIVE** |
| Security — `.env` never synced, vault gitignored | ✅ **LIVE** |
| Odoo Community on Cloud (Docker + Codespaces) | ✅ **LIVE** |
| Cloud Agent → Odoo draft invoice (XML-RPC) | ✅ **LIVE** |
| Local Agent → Approve → Post invoice to Odoo | ✅ **LIVE** |

</div>

### 🔄 Minimum Passing Gate — PROVEN

```
📧 Email arrives
   └──▶ ☁️ Cloud Agent fetches via IMAP
         └──▶ 🤖 Groq drafts reply
               └──▶ 💾 Saved to vault/Pending_Approval/email/
                     └──▶ 💻 Local Agent reads draft → 👤 Human approves [A]
                           └──▶ 📤 Gmail SMTP sends email → 📋 Logged to vault/Done/

📄 Invoice email arrives
   └──▶ ☁️ Cloud Agent detects intent
         └──▶ 🗂️ Creates draft invoice in Odoo (XML-RPC)
               └──▶ 💾 Saved to vault/Pending_Approval/odoo/
                     └──▶ 💻 Local Agent shows invoice → 👤 Human approves [A]
                           └──▶ ✅ Invoice posted in Odoo → 📋 Logged to vault/Done/
```

### ▶️ Run Platinum Tier

```bash
# ☁️  On GitHub Codespaces (Cloud):
cd platinum_tier_business_layer
python cloud_agent.py        # Always-on email triage + Groq drafts

# 💻 On Local PC:
cd platinum_tier_business_layer
python local_agent.py        # Review drafts → Approve / Edit / Reject
```

### 🔑 Environment Variables (Codespaces Secrets)

```env
GROQ_API_KEY=your_groq_key          # console.groq.com — free, no card
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

---

## ⚡ Gold Tier — Complete Feature List

### 📱 1. WhatsApp Broadcast *(Playwright — No Twilio)*

> Uses **your own WhatsApp** account via WhatsApp Web automation. No Twilio, no costs.

- 🔐 QR scan once → session saved → auto-login every future run
- 📡 Broadcasts to multiple numbers in sequence
- ✅ **Real delivery confirmation** — counts DOM `message-out` nodes before/after send

```bash
python run_whatsapp_broadcast.py
python run_whatsapp_broadcast.py --numbers "+923001234567" --message "Hello!"
```

---

### 🏢 2. Odoo ERP Integration *(XML-RPC + Visual Browser)*

> Full ERP control from Python — create contacts, draft invoices, post to Odoo.

- 🔗 Connects to Odoo Community (Docker, local) via XML-RPC
- 👁️ Visual browser mode — Playwright opens and shows live Odoo UI
- 🛡️ Full HITL approval before any write operation
- 📸 Screenshots auto-saved to `70-LOGS/`

---

### 📘 3. Facebook Auto-Post *(Playwright)*

- 🔐 Persistent browser session — login once, auto-login forever
- 📝 Opens feed → finds composer → types post → clicks Post
- 🧹 Handles popups automatically
- ✅ Post confirmed LIVE on Facebook

---

### 📸 4. Instagram Auto-Post *(Playwright)*

- 🔐 Persistent browser session
- 🖼️ Auto-generates post image via Pillow — no manual image needed
- 📤 Uploads image → adds caption → clicks Share → LIVE on Instagram

---

### 🐦 5. Twitter / X Auto-Post *(Playwright)*

- 🔑 Full login flow (email → password → unusual activity bypass)
- 🎯 Finds tweet compose box via `data-testid` selectors
- 📝 Types tweet + hashtags → clicks Post → LIVE on X/Twitter

---

### 🔌 6. MCP Servers *(Model Context Protocol)*

> Two real MCP servers so **Claude can use Email and Odoo as native tools**.

**📧 Email MCP Server** — `mcp_servers/email_mcp_server.py`

| Tool | Description |
|:-----|:------------|
| `send_email(to, subject, body)` | Sends email via Gmail SMTP |
| `email_health()` | Checks SMTP connection status |

**🏢 Odoo MCP Server** — `mcp_servers/odoo_mcp_server.py`

| Tool | Description |
|:-----|:------------|
| `create_odoo_contact(...)` | Creates `res.partner` record |
| `fetch_odoo_contact(id)` | Reads a contact by ID |
| `list_odoo_contacts(limit)` | Lists recent contacts |
| `update_odoo_contact(id, ...)` | Updates existing contact |
| `odoo_health()` | Checks Odoo XML-RPC connection |

> 📄 Register in `claude_desktop_config.json` — see `mcp_servers/claude_desktop_config_snippet.json`

---

### 📊 7. CEO Weekly Audit + Briefing

- 📂 Reads all skill logs from `70-LOGS/` (HITL, Orchestrator, Watchers, Actions)
- 📝 Generates professional Markdown CEO briefing report
- 💾 Saved to `obsidian-vault/50-BUSINESS/weekly/`
- 📈 Shows HITL approval rates, orchestrator success, watcher events, action KPIs
- 🚦 Overall health: **HEALTHY** / **DEGRADED** / **CRITICAL**

```bash
python run_ceo_audit.py             # Current week report
python run_ceo_audit.py --print     # Also print full report to terminal
```

---

### 🔁 8. Ralph Wiggum Loop *(Autonomous Orchestrator)*

- 🤖 Autonomous multi-step task completion loop
- 📁 Located in `silver_tier_core_autonomy/ralph/`
- 📋 Runs tasks from queue, logs each step, supports HITL gates
- 💪 Health monitoring + failure recovery built-in

---

### 🧩 9. Everything as Agent Skills

Every feature is a composable, reusable Agent Skill:

```
EmailAction  •  OdooAction  •  BrowserAction  •  CeoAuditSkill  •  RalphRunner  •  HITLSkill
```

---

## 🥈 Silver Tier

| Feature | Description |
|:--------|:------------|
| **Gmail Auto-Send (HITL)** | Draft → Human Approves → SMTP → Delivered |
| **Gmail IMAP Watcher** | Fetches unread emails, parses subject/sender/attachments |
| **LinkedIn Auto-Post** | Shadow DOM traversal + React event dispatch |
| **Plan.md Loop** | Claude reasoning loop creating `Plans/` files |
| **Task Scheduler** | Cron-style scheduler in `silver_tier_core_autonomy/scheduler/` |

---

## 📁 Project Structure

```
Personal-AI-Employee-Hackathon-0/
│
├── 📂 mcp_servers/                     # 🔌 MCP Servers (Gold Tier)
│   ├── email_mcp_server.py             #    Gmail SMTP as MCP tool
│   ├── odoo_mcp_server.py              #    Odoo ERP as MCP tool
│   └── claude_desktop_config_snippet.json
│
├── 📂 golden_tier_external_world/
│   ├── watchers/
│   │   ├── gmail/                      #    Gmail IMAP watcher
│   │   ├── linkedin/                   #    LinkedIn watcher
│   │   └── whatsapp/                   #    WhatsApp Playwright client
│   └── actions/
│       ├── facebook/                   #    PlaywrightFacebookPoster
│       ├── instagram/                  #    PlaywrightInstagramPoster
│       ├── twitter/                    #    PlaywrightTwitterPoster
│       ├── email/                      #    EmailAction + RealEmailAdapter
│       ├── linkedin/                   #    LinkedInPoster
│       ├── odoo/                       #    Odoo XML-RPC Action
│       └── whatsapp/                   #    WhatsApp Broadcast Action
│
├── 📂 platinum_tier_business_layer/
│   ├── cloud_agent.py                  #    ☁️  Always-on cloud email triage
│   ├── local_agent.py                  #    💻 Human approval terminal UI
│   └── ceo_audit/                      #    CEO Weekly Audit Skill
│       ├── collector.py                #       Log aggregator
│       ├── reporter.py                 #       Markdown report generator
│       └── __init__.py
│
├── 📂 silver_tier_core_autonomy/
│   ├── ralph/                          #    Ralph Wiggum autonomous loop
│   ├── plan_loop/                      #    Plan.md generator
│   └── scheduler/                      #    Task scheduler
│
├── 📂 bronze_tier_governance/
│   └── hitl/                           #    Human-in-the-Loop (Tiers 0–4)
│
├── 📂 obsidian-vault/
│   ├── 50-BUSINESS/weekly/             #    CEO briefing reports
│   ├── Pending_Approval/               #    HITL queue
│   ├── Done/                           #    Completed tasks
│   ├── Plans/                          #    AI-generated plans
│   └── 70-LOGS/                        #    All logs + screenshots
│
├── 📂 history/prompts/                 # Prompt History Records (PHRs)
│
├── 🚀 run_gold_live.py                 # WhatsApp + Odoo LIVE (visual)
├── 🚀 run_social_live.py               # Facebook + Instagram + Twitter LIVE
├── 🚀 run_silver_live.py               # LinkedIn + Gmail LIVE
├── 🚀 run_whatsapp_broadcast.py        # WhatsApp Broadcast
├── 🚀 run_ceo_audit.py                 # CEO Weekly Audit Report
└── 🔒 .env                             # Credentials (gitignored — never commit)
```

---

## 🚀 Quick Start

### Step 1 — Install Dependencies

```bash
pip install playwright selenium webdriver-manager python-dotenv pillow mcp
playwright install chromium
```

### Step 2 — Configure Credentials

Copy `.env.example` → `.env` and fill in your credentials:

```env
# 📧 Gmail
GMAIL_ACCOUNT_EMAIL=your@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
EMAIL_RECIPIENTS=friend@gmail.com

# 💼 LinkedIn
LINKEDIN_EMAIL=your@gmail.com
LINKEDIN_PASSWORD=yourpassword
LINKEDIN_PROFILE_URL=https://www.linkedin.com/in/your-name/

# 🐦 Twitter/X
TWITTER_EMAIL=your@gmail.com
TWITTER_PASSWORD=yourpassword
TWITTER_USERNAME=your_handle

# 📘 Facebook
FACEBOOK_EMAIL=your@gmail.com
FACEBOOK_PASSWORD=yourpassword

# 📸 Instagram
INSTAGRAM_USERNAME=your_handle
INSTAGRAM_PASSWORD=yourpassword

# 📱 WhatsApp Broadcast
WA_BROADCAST_NUMBERS=+923001234567,+923009876543
WA_SESSION_DIR=wa_session

# 🏢 Odoo ERP
ODOO_URL=http://localhost:8069
ODOO_DB=mycompany
ODOO_USERNAME=admin
ODOO_PASSWORD=admin
```

### Step 3 — Run Odoo via Docker *(one-time setup)*

```bash
docker run -d --name odoo17 -p 8069:8069 odoo:17
# Open http://localhost:8069 → create database → login
```

### Step 4 — Run Any Tier

```bash
# ⚡ Gold Tier
python run_gold_live.py           # WhatsApp + Odoo (visual browser)
python run_social_live.py         # Facebook + Instagram + Twitter
python run_ceo_audit.py           # CEO Weekly Audit Report
python run_whatsapp_broadcast.py  # WhatsApp Broadcast only

# 🥈 Silver Tier
python run_silver_live.py         # LinkedIn + Gmail LIVE

# 💎 Platinum Tier
python platinum_tier_business_layer/cloud_agent.py   # ☁️  Cloud (Codespaces)
python platinum_tier_business_layer/local_agent.py    # 💻 Local PC
```

### Step 5 — Register MCP Servers with Claude Desktop

```bash
python mcp_servers/email_mcp_server.py
python mcp_servers/odoo_mcp_server.py
```

> See `mcp_servers/claude_desktop_config_snippet.json` for Claude Desktop registration config.

---

## 🔐 HITL Approval Tiers

<div align="center">

| Tier | Risk Level | Approval Required | Examples |
|:----:|:----------:|:-----------------:|:---------|
| **0** | 🟢 Read-only | Auto-approved | Log reads, health checks |
| **1** | 🟡 Low | Auto-approved | Draft creation, local writes |
| **2** | 🟠 Medium | 👤 Human required | Send email, post to social |
| **3** | 🔴 High | 👤 Human required | Delete records, bulk actions |
| **4** | ⛔ Critical | 👤 Human + full audit | Financial operations, billing |

</div>

> 🛡️ All social media posts, emails, and Odoo writes run through HITL **before** executing.

---

## 🛠️ Key Technical Highlights

| Feature | Technical Detail |
|:--------|:----------------|
| **MCP Protocol** | Real Model Context Protocol servers — Claude calls Email & Odoo as native tools |
| **Playwright Sessions** | Login once per platform, sessions saved to disk, auto-login forever |
| **DOM Verification** | WhatsApp confirmed by counting `div.message-out` nodes before/after send |
| **CEO Audit** | Reads JSONL + pipe-delimited logs, aggregates weekly KPIs, exports Markdown |
| **Ralph Loop** | Autonomous multi-step orchestrator with HITL gates + step-level logging |
| **Shadow DOM** | LinkedIn post editor traversed via JS `createTreeWalker` |
| **Auto Image Gen** | Instagram requires image — Pillow generates branded post image automatically |
| **Fail-Safe Design** | Every skill returns structured result, never raises exceptions at boundary |
| **Git Sync** | Cloud vault syncs via Git; `.env` and sessions always excluded from commits |

---

## 📊 Gold Tier — Full Status

<div align="center">

| Component | Status | Notes |
|:----------|:------:|:------|
| Gmail IMAP Watcher | ✅ **LIVE** | Real IMAP SSL |
| Gmail SMTP Sender | ✅ **LIVE** | App Password auth |
| Email MCP Server | ✅ **LIVE** | MCP protocol — Claude native tool |
| LinkedIn Auto-Post | ✅ **LIVE** | Shadow DOM + React events |
| WhatsApp Broadcast | ✅ **LIVE** | Playwright Web, no Twilio |
| Odoo ERP (XML-RPC) | ✅ **LIVE** | Docker local instance |
| Odoo MCP Server | ✅ **LIVE** | MCP protocol — Claude native tool |
| Twitter/X Post | ✅ **LIVE** | Playwright — tweets working |
| Facebook Post | ✅ **LIVE** | Playwright — persistent session |
| Instagram Post | ✅ **LIVE** | Playwright — auto image gen |
| CEO Weekly Audit | ✅ **LIVE** | Markdown briefing to vault |
| Ralph Wiggum Loop | ✅ **Complete** | Autonomous multi-step tasks |
| HITL System | ✅ **Complete** | Tiers 0–4 |
| Audit Logging | ✅ **Complete** | JSONL per skill per day |

</div>

---

## 📸 Live Evidence

Screenshots are auto-saved to `obsidian-vault/70-LOGS/`:

| Screenshot | What it proves |
|:-----------|:--------------|
| `facebook_posted.png` | 📘 Facebook post LIVE |
| `instagram_posted.png` | 📸 Instagram post LIVE |
| `twitter_posted.png` | 🐦 Tweet posted on X |
| `odoo_contact_created.png` | 🏢 Odoo record created |
| `odoo_contact_updated.png` | 🏢 Odoo record updated |

> CEO reports saved in `obsidian-vault/50-BUSINESS/weekly/`

---

## 🔒 Security

- 🔑 All credentials in `.env` only — never hardcoded, never committed to Git
- 🚫 `.gitignore` excludes `.env`, `wa_session/`, all browser session folders
- 🛡️ HITL gates prevent autonomous execution of high-risk actions
- 🔐 Credential tokens passed via parameter — never logged or printed
- ☁️ Cloud vault sync excludes all secrets — vault folder in `.gitignore`

---

## 📝 License

Personal project for GIAIC Q4 Hackathon 0. All rights reserved.

---

<div align="center">

**Built with ❤️ by [Syed Abdullah Zaidi](https://github.com/syedabdullahzaidi786)**

![Made with Python](https://img.shields.io/badge/Made%20with-Python-3b82f6?style=for-the-badge&logo=python&logoColor=white)
![Powered by Claude](https://img.shields.io/badge/Powered%20by-Claude%20AI-f97316?style=for-the-badge&logo=anthropic&logoColor=white)
![GIAIC](https://img.shields.io/badge/GIAIC-Hackathon%200-a855f7?style=for-the-badge)

*Platinum Tier 💎 — COMPLETE ✅ — Cloud+Local Flow LIVE + Odoo Invoice Approval LIVE*

</div>
