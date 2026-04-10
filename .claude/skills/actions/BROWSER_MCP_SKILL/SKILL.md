# BROWSER_MCP_SKILL

**Status**: Phase 1 Complete
**Category**: Actions
**Tier**: 2 (Medium-risk) — HITL required for all browser actions

## Purpose

MCP-style action skill for browser automation with HITL enforcement.
Phase 1 uses MockBrowserAdapter (no real browser). Phase 2 will plug in RealBrowserAdapter (Playwright or browser-automation MCP server).

## Supported Actions (Phase 1)

| Action         | Description                                  |
|----------------|----------------------------------------------|
| `open_url`     | Open a URL, return page title                |
| `extract_text` | Extract text from URL with optional selector |

## Architecture

```
src/skills/actions/browser/
    models.py    — BrowserRequest, BrowserResult, BrowserConfig, BrowserActionType, BrowserActionStatus
    adapter.py   — BrowserAdapter ABC, MockBrowserAdapter, RealBrowserAdapter (stub)
    action.py    — BrowserAction: validate → HITL gate → execute
    logger.py    — BrowserLogger: JSONL to 70-LOGS/browser/
    cli.py       — CLI: open, extract, status, logs
    __init__.py  — BrowserSkill facade
tests/test_browser_skill.py — 90 unit tests (all passing)
```

## Usage

```python
from skills.actions.browser import BrowserSkill, BrowserConfig

config = BrowserConfig(vault_root="/vault")
skill  = BrowserSkill(config)

# Tier 2 (default) — returns PENDING_APPROVAL when HITLSkill attached
result = skill.open_url("https://example.com")

# Tier 1 — executes immediately
result = skill.open_url("https://example.com", tier=1)
print(result.content)   # "[Mock] example.com — Home"

result = skill.extract_text("https://example.com", selector="h1", tier=1)
print(result.content)   # "[Mock extracted text from https://example.com (selector: 'h1')]"
```

## CLI

```bash
python -m skills.actions.browser.cli --vault /vault open --url https://example.com --tier 1
python -m skills.actions.browser.cli --vault /vault extract --url https://example.com --selector h1
python -m skills.actions.browser.cli --vault /vault status
python -m skills.actions.browser.cli --vault /vault logs [--date YYYY-MM-DD]
```

## Execution Flow

1. `execute(request)` → validate (empty URL, blank URL, unsupported action)
2. If `tier ≥ 2` and `hitl_skill` provided → submit to HITL queue
3. If `tier < 2` or no HITL skill → execute immediately via adapter
4. All outcomes logged to `70-LOGS/browser/YYYY-MM-DD.jsonl`

## Dependencies

- `HUMAN_IN_THE_LOOP_APPROVAL_SKILL` — HITL gate for tier ≥ 2
- `SECURITY_AND_CREDENTIAL_MANAGEMENT_SKILL` — credential spec registration
- `ORCHESTRATOR_SYSTEM_SKILL` — registers `browser.open_url` + `browser.extract_text`

## Integrations

- **Orchestrator**: registers `browser.open_url` and `browser.extract_text` in `SkillRegistry`
- **SecuritySkill**: registers `browser_credential` CredentialSpec (env var: `BROWSER_CREDENTIAL`)
- **HITLSkill**: submits `make_request(tier=2, operation=action, ...)` for human approval

## Constitution Compliance

- [x] Follows Skill Design Rules (Section 9) — atomic, composable, testable
- [x] Logging implemented (Section 7) — `70-LOGS/browser/`
- [x] Error handling defined (Principle VI) — never raises, errors in BrowserResult
- [x] HITL approval enforced (Section 3) — tier ≥ 2 requires HITLSkill

## Test Coverage

| Class                   | Tests |
|-------------------------|-------|
| TestBrowserActionType   | 1     |
| TestBrowserActionStatus | 1     |
| TestBrowserEventType    | 1     |
| TestBrowserRequest      | 6     |
| TestBrowserResult       | 3     |
| TestBrowserConfig       | 2     |
| TestFactories           | 4     |
| TestMockBrowserAdapter  | 15    |
| TestRealBrowserAdapter  | 2     |
| TestBrowserLogger       | 8     |
| TestValidation          | 5     |
| TestBrowserAction       | 11    |
| TestBrowserSkill        | 23    |
| TestCLI                 | 8     |
| **Total**               | **90** |
