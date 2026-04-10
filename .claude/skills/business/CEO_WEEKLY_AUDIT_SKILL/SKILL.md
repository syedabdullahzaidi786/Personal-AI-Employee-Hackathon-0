# CEO_WEEKLY_AUDIT_SKILL

**Status**: Phase 1 Complete
**Category**: Business
**Tier**: 0 (Read-only — no HITL required)

## Purpose

Read-only analytics skill that aggregates weekly KPIs from all skill log directories
and generates executive Markdown reports. Covers HITL approvals, orchestrator runs,
watcher events, and action skill activity.

## Usage

```python
from skills.business.ceo_audit import CeoAuditSkill

skill = CeoAuditSkill(vault_root="/vault")

# Current week
report, paths = skill.generate_and_save()

# Previous week
report, paths = skill.generate_and_save(week_offset=-1)

print(report.overall_health)        # "HEALTHY" | "DEGRADED" | "CRITICAL"
print(report.hitl.approval_rate)    # 0.0–1.0 or None
```

## Architecture

| File | Role |
|---|---|
| `models.py` | ReportPeriod, HITLStats, OrchestratorStats, WatcherStats, ActionStats, WeeklyReport, compute_health |
| `collector.py` | LogCollector — reads HITL JSON, Orchestrator MD, Watcher MD, Action JSONL |
| `reporter.py` | ReportGenerator — Markdown report + summary dict |
| `logger.py` | AuditSkillLogger → 70-LOGS/business/YYYY-MM-DD.jsonl |
| `__init__.py` | CeoAuditSkill facade |
| `cli.py` | CLI: generate-weekly-report |

## Log Sources

| Source | Format | Path |
|---|---|---|
| HITL pending | JSON | `70-LOGS/hitl/pending/*.json` |
| HITL completed | JSON | `70-LOGS/hitl/completed/*.json` |
| Orchestrator | Pipe-delimited MD | `70-LOGS/orchestrator/daily/YYYY-MM-DD-orchestrator.md` |
| Watchers | Pipe-delimited MD | `70-LOGS/watchers/{id}/daily/YYYY-MM-DD.md` |
| Actions (email/browser/odoo) | JSONL | `70-LOGS/{skill}/YYYY-MM-DD.jsonl` |

## Report Outputs

| File | Description |
|---|---|
| `50-BUSINESS/weekly/{slug}.md` | Human-readable Markdown executive report |
| `70-LOGS/business/YYYY-MM-DD.jsonl` | Machine-readable audit log of report generations |

## Tests

| Class | Tests |
|---|---|
| TestIsoWeekBounds | 5 |
| TestReportPeriod | 10 |
| TestCurrentWeekPeriod | 4 |
| TestHITLStats | 6 |
| TestOrchestratorStats | 4 |
| TestWatcherStats | 1 |
| TestActionStats | 4 |
| TestComputeHealth | 7 |
| TestWeeklyReport | 2 |
| TestLogCollectorHITL | 7 |
| TestLogCollectorOrchestrator | 8 |
| TestLogCollectorWatchers | 5 |
| TestLogCollectorActions | 10 |
| TestLogCollectorCollectAll | 4 |
| TestReportGenerator | 14 |
| TestAuditSkillLogger | 6 |
| TestCeoAuditSkill | 14 |
| TestCLI | 9 |
| **Total** | **125** |

## Constitution Compliance

- [x] Follows Skill Design Rules (Section 9) — atomic, composable, testable
- [x] Logging implemented (Section 7) — 70-LOGS/business/YYYY-MM-DD.jsonl
- [x] Generates reports (Section 7) — 50-BUSINESS/weekly/{slug}.md
- [x] Read-only — no system mutations; no HITL required (Tier 0)
- [x] Never reads credential values from vault (Section 8)
