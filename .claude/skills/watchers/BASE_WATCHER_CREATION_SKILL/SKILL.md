# BASE_WATCHER_CREATION_SKILL

**Status**: Phase 1 Complete
**Category**: Watchers
**Tier**: 2 (Medium-risk)

## Purpose
Foundation framework for all event-monitoring watchers. Defines the BaseWatcher
abstract contract, event/state models, registry, dispatcher (with HITL routing),
file-based event store, vault logger, and WatcherSkill facade.

GMAIL_WATCHER and WHATSAPP_WATCHER extend BaseWatcher by implementing `poll()`
and `health_check()`. Everything else is provided by the framework.

## Usage
```python
from skills.watchers.base import WatcherSkill, BaseWatcher, WatcherConfig, make_event

class FileWatcher(BaseWatcher):
    def poll(self):
        return [make_event(self.config.watcher_id, "file_created", "fs:dir", tier=1)]
    def health_check(self):
        return True

config = WatcherConfig(watcher_id="vault-fs", watcher_type="filesystem",
                       vault_root="/vault")
skill  = WatcherSkill(vault_root="/vault")
skill.register_watcher(FileWatcher(config))
skill.register_handler("file_created", lambda e: print("New file:", e.payload))
skill.start_watcher("vault-fs")
result = skill.tick_watcher("vault-fs")
```

## CLI
```
python -m skills.watchers.base.cli --vault /vault list
python -m skills.watchers.base.cli --vault /vault status --id <id>
python -m skills.watchers.base.cli --vault /vault events --id <id> [--date YYYY-MM-DD]
```

## Phase 1 Modules
| Module | Responsibility |
|--------|---------------|
| `models.py` | WatcherConfig, WatcherEvent, WatcherState, WatcherTickResult, DispatchResult, EventType enums, make_event |
| `base.py` | BaseWatcher ABC: abstract poll/health_check; concrete tick/start/stop/state persistence |
| `registry.py` | WatcherRegistry: register, get, require, unregister, list_all, list_running |
| `dispatcher.py` | EventDispatcher: tier-based routing (0/1 direct, 2+ HITL), wildcard handlers, fail_open mode |
| `store.py` | EventStore: JSONL persistence in 70-LOGS/watchers/{id}/events/ |
| `logger.py` | WatcherLogger: append-only daily + error logs in 70-LOGS/watchers/{id}/ |
| `__init__.py` | WatcherSkill facade composing all modules |
| `cli.py` | CLI: list, status, events |

## Constitution Compliance
- [x] Follows Skill Design Rules (Section 9) — atomic, testable, composable
- [x] Logging implemented (Section 7) — daily + error logs in vault
- [x] Error handling defined (Principle VI) — tick() never raises; all errors captured
- [x] HITL integration (Section 3) — Tier 2+ events routed via EventDispatcher
- [x] Local-First (Principle I) — events and state persisted to Obsidian vault
