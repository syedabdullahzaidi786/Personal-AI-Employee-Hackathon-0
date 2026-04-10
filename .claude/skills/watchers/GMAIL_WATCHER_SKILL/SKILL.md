# GMAIL_WATCHER_SKILL

**Status**: Phase 1 Complete
**Category**: Watchers
**Tier**: 2 (Medium-risk)

## Purpose
Extends the BaseWatcher framework to monitor a Gmail account for new messages.
Phase 1 uses a mockable GmailClient interface — no real API calls.
Phase 2 will plug in RealGmailClient backed by the Google Gmail API with
credentials loaded from SecuritySkill.

## Usage
```python
from skills.watchers.gmail import GmailWatcherSkill, GmailConfig, make_gmail_message

config = GmailConfig(account_email="you@gmail.com", vault_root="/vault")
skill  = GmailWatcherSkill(config)

# Register handlers
skill.register_handler("gmail_new_message", lambda e: print(e.payload["subject"]))

# Run
skill.start()
result = skill.tick()
print(result.events_found)

# Testing: inject messages without a real API
skill.inject_message(make_gmail_message("Hello", "alice@example.com"))
```

## CLI
```
python -m skills.watchers.gmail.cli --vault /vault --account you@gmail.com status
python -m skills.watchers.gmail.cli --vault /vault --account you@gmail.com tick
python -m skills.watchers.gmail.cli --vault /vault --account you@gmail.com events [--date YYYY-MM-DD]
python -m skills.watchers.gmail.cli --vault /vault --account you@gmail.com inject --subject "Hi" --sender alice@example.com
```

## Phase 1 Modules
| Module | Responsibility |
|--------|---------------|
| `models.py` | GmailMessage, GmailConfig, GmailEventType constants, make_gmail_message factory |
| `client.py` | GmailClient ABC, MockGmailClient (in-memory/testable), RealGmailClient (Phase 2 stub) |
| `watcher.py` | GmailWatcher(BaseWatcher): poll/health_check + seen-IDs deduplication |
| `handlers.py` | make_log_handler, make_orchestrator_handler, make_filter_handler, make_sender_filter |
| `cli.py` | CLI: status, tick, events, inject |
| `__init__.py` | GmailWatcherSkill facade composing watcher + dispatcher |

## Key Design Decisions
- **Mockable client**: GmailClient ABC separates interface from implementation — tests run with zero network
- **Seen-IDs deduplication**: Persisted to `70-LOGS/watchers/{id}/seen-ids.json` — survives process restarts
- **Attachment detection**: Emits `gmail_attachment_received` event type when `has_attachments=True`
- **No secrets in payload**: GmailMessage.to_dict() contains only safe metadata fields
- **fail_open=True**: EventDispatcher defaults to direct dispatch in dev (no HITL blocking)

## Constitution Compliance
- [x] Follows Skill Design Rules (Section 9) — atomic, testable, composable
- [x] Logging implemented (Section 7) — daily + error logs via WatcherLogger
- [x] Error handling defined (Principle VI) — tick() never raises (BaseWatcher guarantee)
- [x] HITL integration (Section 3) — Tier 2 events routed via EventDispatcher
- [x] Local-First (Principle I) — events + seen-IDs + state persisted to vault
- [x] Credential Storage (Section 8) — credentials_name is a reference, never the value
