# ODOO_MCP_INTEGRATION_SKILL

**Status**: Phase 1 Complete
**Category**: Actions
**Tier**: 3 (High-risk — writes require HITL)

## Purpose

MCP-style integration skill for Odoo ERP. Exposes `create_record`, `update_record`, and
`fetch_record` as callable operations with HITL enforcement for write operations (tier ≥ 2),
Security credential management, Orchestrator registration, and append-only audit logging.

## Usage

```python
from skills.actions.odoo import OdooSkill, OdooConfig

config = OdooConfig(vault_root="/vault", odoo_url="https://myco.odoo.com", database="prod")
skill  = OdooSkill(config)

# Tier 3 write — goes to HITL when HITLSkill attached
result = skill.create_record("res.partner", {"name": "Alice", "email": "alice@example.com"})

# Tier 1 read — auto-executes
result = skill.fetch_record("res.partner", record_id=1)
print(result.record_data)
```

## Architecture

| File | Role |
|---|---|
| `models.py` | OdooRequest, OdooResult, OdooConfig, OdooOperation, OdooActionStatus, OdooEventType, factories |
| `adapter.py` | OdooAdapter ABC, MockOdooAdapter (in-memory), RealOdooAdapter (Phase 2 stub) |
| `logger.py` | OdooLogger → 70-LOGS/odoo/YYYY-MM-DD.jsonl |
| `action.py` | OdooAction — validate → HITL gate → execute |
| `__init__.py` | OdooSkill facade |
| `cli.py` | CLI: create, update, fetch, status, logs |

## Operations

| Operation | Default Tier | HITL Required |
|---|---|---|
| create_record | 3 | Yes (when HITLSkill attached) |
| update_record | 3 | Yes (when HITLSkill attached) |
| fetch_record | 1 | No (auto-approve) |

## Dependencies

- `HITLSkill` (optional) — required for Tier ≥ 2 enforcement
- `SecuritySkill` (optional) — registers `odoo_credential` CredentialSpec
- `OrchestratorSkill` (optional) — registers `odoo.create_record`, `odoo.update_record`, `odoo.fetch_record`

## Tests

| Class | Tests |
|---|---|
| TestOdooOperation | 1 |
| TestOdooActionStatus | 1 |
| TestOdooEventType | 1 |
| TestOperationDefaultTier | 2 |
| TestOdooRequest | 7 |
| TestOdooResult | 2 |
| TestOdooConfig | 2 |
| TestFactories | 4 |
| TestMockOdooAdapter | 20 |
| TestRealOdooAdapter | 2 |
| TestOdooLogger | 8 |
| TestValidation | 9 |
| TestOdooAction | 12 |
| TestOdooSkill | 21 |
| TestCLI | 10 |
| **Total** | **102** |

## Constitution Compliance

- [x] Follows Skill Design Rules (Section 9) — atomic, composable, testable
- [x] Logging implemented (Section 7) — 70-LOGS/odoo/YYYY-MM-DD.jsonl
- [x] Error handling defined (Principle VI) — execute() never raises; fail-safe DENIED
- [x] HITL approval required (Section 3) — Tier ≥ 2 gated; DENIED on HITL failure
- [x] No secrets in logs (Section 8) — OdooResult carries no credentials
