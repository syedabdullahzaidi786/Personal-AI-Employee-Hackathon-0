# SECURITY_AND_CREDENTIAL_MANAGEMENT_SKILL

**Status**: Phase 1 Complete
**Category**: Safety
**Tier**: 4 (Critical)

## Purpose
Secure credential storage abstraction, secret redaction, access policy enforcement,
vault boundary scanning, and immutable audit logging for all credential operations.

## Usage
```python
from skills.safety.security import SecuritySkill, CredentialSpec, CredentialType

skill = SecuritySkill(vault_root="/path/to/obsidian-vault")
skill.register(CredentialSpec("gmail_key", env_key="GMAIL_API_KEY", cred_type=CredentialType.API_KEY))
skill.load_dotenv(".env")
skill.load_all()

skill.allow("gmail-watcher", "gmail_key", reason="Email watcher integration")
value = skill.get("gmail_key", agent_id="gmail-watcher")

safe_log = skill.redact("token=super_secret_value")
findings = skill.scan_vault()
```

## CLI
```
python -m skills.safety.security.cli --vault /vault verify
python -m skills.safety.security.cli --vault /vault scan-vault
python -m skills.safety.security.cli --vault /vault list-credentials
python -m skills.safety.security.cli --vault /vault rotate-reminder
python -m skills.safety.security.cli --vault /vault audit
```

## Dependencies
- Python stdlib only (no external packages)
- Obsidian vault directory (write access to 70-LOGS/security/)

## Phase 1 Modules
| Module | Responsibility |
|--------|---------------|
| `models.py` | CredentialSpec, PolicyRule, AuditEntry, ScanFinding, enums, factories |
| `redactor.py` | SecretRedactor: mask secrets from logs (known values + patterns) |
| `loader.py` | CredentialLoader + DotEnvParser: load from .env / os.environ |
| `policy.py` | AccessPolicy: default-deny, explicit allow/deny, wildcard rules |
| `store.py` | CredentialStore: in-memory registry, policy-enforced retrieval |
| `vault_guard.py` | VaultGuard: scan vault files for accidental secret exposure |
| `audit.py` | SecurityAuditLogger: append-only audit trail (markdown + JSONL) |
| `cli.py` | CLI: verify, scan-vault, list-credentials, rotate-reminder, audit |
| `__init__.py` | SecuritySkill facade composing all modules |

## Constitution Compliance
- [x] Follows Skill Design Rules (Section 9)
- [x] Implements security rules (Section 8) — no plaintext in vault, env vars only
- [x] Logging implemented (Section 7) — immutable audit trail in 70-LOGS/security/
- [x] HITL approval required (Section 3) — Tier 4, stub ready for Phase 2
- [x] Secrets never logged — SecretRedactor applied at all log boundaries
