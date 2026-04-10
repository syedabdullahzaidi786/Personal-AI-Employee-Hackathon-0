# EMAIL_MCP_ACTION_SKILL

**Status**: Phase 1 Complete
**Category**: Actions
**Tier**: 3 (High-risk) — HITL required for all sends

## Purpose

MCP-style action skill for sending emails through a composable, testable interface.
Phase 1 uses a MockEmailAdapter (no real SMTP). Phase 2 will plug in RealEmailAdapter.

## Architecture

```
src/skills/actions/email/
    models.py    — EmailRequest, EmailResult, EmailConfig, EmailActionStatus
    adapter.py   — EmailAdapter ABC, MockEmailAdapter, RealEmailAdapter (stub)
    action.py    — EmailAction: validate → HITL gate → send
    logger.py    — EmailActionLogger: JSONL to 70-LOGS/email/
    cli.py       — CLI: send, status, logs
    __init__.py  — EmailActionSkill facade
tests/test_email_action.py — 75 unit tests (all passing)
```

## Usage

```python
from skills.actions.email import EmailActionSkill, EmailConfig

config = EmailConfig(sender_address="agent@company.com", vault_root="/vault")
skill  = EmailActionSkill(config)

# Tier 3 (default) — returns PENDING_APPROVAL (HITL required)
result = skill.send(to=["user@example.com"], subject="Hello", body="Hi!")

# Tier 1 — sends immediately
result = skill.send(to=["user@example.com"], subject="Low risk", body="Hi!", tier=1)
```

## CLI

```bash
python -m skills.actions.email.cli --vault /vault --sender agent@company.com send \
    --to alice@example.com --subject "Hello" --body "Hi!" --tier 1

python -m skills.actions.email.cli --vault /vault --sender agent@company.com status
python -m skills.actions.email.cli --vault /vault --sender agent@company.com logs
```

## Send Flow

1. `submit(request)` → validate (empty `to`, blank subject, max recipients)
2. If `tier ≥ 2` and `hitl_skill` provided → submit to HITL queue
3. If `tier < 2` or no HITL skill → send immediately via adapter
4. All outcomes logged to `70-LOGS/email/YYYY-MM-DD.jsonl`

## Dependencies

- `HUMAN_IN_THE_LOOP_APPROVAL_SKILL` — HITL gate for tier ≥ 2
- `SECURITY_AND_CREDENTIAL_MANAGEMENT_SKILL` — credential spec registration
- `ORCHESTRATOR_SYSTEM_SKILL` — registers `email.send` in SkillRegistry

## Integrations

- **Orchestrator**: registers `email.send` handler via `SkillRegistry`
- **SecuritySkill**: registers `smtp_credential` CredentialSpec (env var: `SMTP_CREDENTIAL`)
- **HITLSkill**: submits `make_request(tier=3, operation="send_email", ...)` for human approval

## Constitution Compliance

- [x] Follows Skill Design Rules (Section 9) — atomic, composable, testable
- [x] Logging implemented (Section 7) — `70-LOGS/email/`
- [x] Error handling defined (Principle VI) — never raises, errors in EmailResult
- [x] HITL approval enforced (Section 3) — tier ≥ 2 requires HITLSkill
- [x] No secrets in code or logs (Section 8) — credentials_name is a reference only

## Test Coverage

| Class                  | Tests |
|------------------------|-------|
| TestEmailActionStatus  | 1     |
| TestEmailEventType     | 1     |
| TestEmailRequest       | 8     |
| TestEmailConfig        | 2     |
| TestMakeEmailRequest   | 4     |
| TestEmailResult        | 2     |
| TestMockEmailAdapter   | 9     |
| TestRealEmailAdapter   | 2     |
| TestEmailActionLogger  | 8     |
| TestValidation         | 5     |
| TestEmailAction        | 9     |
| TestEmailActionSkill   | 14    |
| TestCLI                | 6     |
| **Total**              | **75** |
