# WHATSAPP_WATCHER_SKILL

**Status**: Phase 1 Complete
**Category**: Watchers
**Tier**: 2 (Medium-risk)

## Purpose
Extends the BaseWatcher framework to monitor a WhatsApp account for incoming messages.
Phase 1 uses a mockable WhatsAppClient adapter interface — no real API calls.
Phase 2 will plug in RealWhatsAppClient backed by WhatsApp Business API / Twilio / Meta Cloud API.

Tier ≥ 2 events are enforced through EventDispatcher; attaching HITLSkill via `set_hitl()`
routes all Tier 2+ messages through the HITL approval queue before handlers fire.

## Usage
```python
from skills.watchers.whatsapp import WhatsAppWatcherSkill, WhatsAppConfig, make_whatsapp_message

config = WhatsAppConfig(phone_number="+14155552671", vault_root="/vault")
skill  = WhatsAppWatcherSkill(config)

# Register handlers (use "*" to catch all types)
skill.register_handler("whatsapp_new_text_message",  lambda e: print(e.payload["message_body"]))
skill.register_handler("whatsapp_new_group_message", lambda e: print(e.payload["group_name"]))

# Attach HITL for Tier ≥ 2 approval
# skill.set_hitl(hitl_skill)

# Run
skill.start()
result = skill.tick()
print(result.events_found)

# Testing: inject messages without a real API
skill.inject_message(make_whatsapp_message("+19175550100", "Hello!"))
```

## CLI
```
python -m skills.watchers.whatsapp.cli --vault /vault --phone +14155552671 status
python -m skills.watchers.whatsapp.cli --vault /vault --phone +14155552671 tick
python -m skills.watchers.whatsapp.cli --vault /vault --phone +14155552671 events [--date YYYY-MM-DD]
python -m skills.watchers.whatsapp.cli --vault /vault --phone +14155552671 inject --sender +19175550100 --body "Hi"
python -m skills.watchers.whatsapp.cli --vault /vault --phone +14155552671 inject --sender +19175550100 --body "Group!" --group-id grp001 --group-name "Team"
```

## Phase 1 Modules
| Module | Responsibility |
|--------|---------------|
| `models.py` | WhatsAppMessage, WhatsAppConfig, WhatsAppEventType/MessageType/ChatType constants, make_whatsapp_message |
| `client.py` | WhatsAppClient ABC, MockWhatsAppClient (in-memory/testable), RealWhatsAppClient (Phase 2 stub) |
| `watcher.py` | WhatsAppWatcher(BaseWatcher): poll/health_check + event-type mapping + seen-IDs deduplication |
| `handlers.py` | make_log_handler, make_orchestrator_handler, make_filter_handler, make_group_filter, make_private_filter, make_sender_filter, make_media_filter |
| `cli.py` | CLI: status, tick, events, inject (private + group) |
| `__init__.py` | WhatsAppWatcherSkill facade composing watcher + dispatcher |

## Event Type Mapping
| Message condition | Event type |
|-------------------|-----------|
| Group chat (any type) | `whatsapp_new_group_message` |
| Private + LOCATION | `whatsapp_new_location_message` |
| Private + CONTACT | `whatsapp_contact_received` |
| Private + media (image/audio/video/document/sticker) | `whatsapp_new_media_message` |
| Private + TEXT (default) | `whatsapp_new_text_message` |

## Key Design Decisions
- **Adapter pattern**: WhatsAppClient ABC decouples watcher from any specific API — tests run with zero network
- **Seen-IDs deduplication**: Persisted to `70-LOGS/watchers/{id}/seen-ids.json` — idempotent across restarts; capped at 5000 entries
- **No media bytes in payload**: Only safe metadata (filename, mime_type, size_bytes) — no raw content stored
- **HITL enforcement**: EventDispatcher routes Tier ≥ 2 events; `set_hitl()` enables HITL queue
- **credentials_name is reference only**: Actual API token managed by SecuritySkill

## Constitution Compliance
- [x] Follows Skill Design Rules (Section 9) — atomic, testable, composable
- [x] Logging implemented (Section 7) — daily + error logs via WatcherLogger in 70-LOGS/watchers/
- [x] Error handling defined (Principle VI) — tick() never raises (BaseWatcher guarantee)
- [x] HITL integration (Section 3) — Tier 2+ events enforced via EventDispatcher; set_hitl() supported
- [x] Local-First (Principle I) — events + seen-IDs + state persisted to vault
- [x] Credential Storage (Section 8) — credentials_name is a reference, never the value
