# FILESYSTEM_AUTOMATION_SKILL

**Status**: Specification Complete - Ready for Implementation
**Category**: Core
**Tier**: 1 (Low-risk writes within vault only)
**Version**: 1.0.0
**Owner**: AI Operations Team
**Last Updated**: 2026-02-16

---

## 1. Purpose

### Mission
Automate file organization, renaming, and classification within the Obsidian vault to maintain a clean, searchable, and well-structured knowledge base.

### What It Does
- **Organizes**: Moves files to correct folders based on naming conventions and content
- **Renames**: Standardizes file names according to vault conventions
- **Classifies**: Tags and categorizes files based on content analysis
- **Validates**: Ensures all files follow vault governance rules
- **Audits**: Generates reports on vault health and organization

### What It Doesn't Do
- ❌ Delete files (requires HITL Tier 3 approval)
- ❌ Modify file content (only metadata and location)
- ❌ Operate outside `obsidian-vault/` directory
- ❌ Touch system files or configuration files

### Why It Matters
A well-organized vault is essential for:
- AI agents to find information quickly
- Humans to navigate and maintain the system
- Compliance with naming conventions
- Auditability and version control

---

## 2. Capabilities

### 2.1 File Organization

#### Auto-Sort by Type
Moves files to appropriate sections based on patterns:

| File Pattern | Destination | Example |
|--------------|-------------|---------|
| `WF-*` | `20-PROCESSES/workflows/` | `WF-001-customer-onboarding.md` |
| `MCP-*` | `30-INTEGRATIONS/mcp-servers/` | `MCP-042-github.md` |
| `TPL-*` | `60-PROMPTS/templates/` | `TPL-023-email-response.md` |
| `EP-*` | `80-MEMORY/episodic/` | `EP-20260216-meeting.md` |
| `SM-*` | `80-MEMORY/semantic/` | `SM-015-policy.md` |
| `YYYY-MM-DD.md` | `70-LOGS/daily/` | `2026-02-16.md` |

#### Smart Folder Detection
Analyzes file content to determine correct section:
```yaml
Content Analysis:
  - Contains "agent profile" → 10-KNOWLEDGE/agents/
  - Contains "workflow steps" → 20-PROCESSES/workflows/
  - Contains "API endpoint" → 30-INTEGRATIONS/apis/
  - Contains "security policy" → 40-SECURITY/policies/
  - Contains "KPI" or "metric" → 50-BUSINESS/analytics/
```

### 2.2 File Renaming

#### Convention Enforcement
Automatically renames files to follow vault standards:

**Before**: `Customer Agent.md`
**After**: `001-customer-agent.md`

**Before**: `Email_Automation_Workflow.MD`
**After**: `WF-023-email-automation-workflow.md`

#### ID Assignment
Assigns next available sequence number in target folder:
```
Current files in 10-KNOWLEDGE/agents/:
  001-customer-agent.md
  002-sales-agent.md

New file: "support agent.md"
Result: 003-support-agent.md
```

### 2.3 File Classification

#### Metadata Enrichment
Adds/updates YAML frontmatter:
```yaml
---
id: auto-generated-if-missing
name: Extracted from title
type: Detected from content/location
status: draft (new files)
created: File creation timestamp
updated: Current timestamp
tags: [auto-generated, based-on-content]
---
```

#### Tag Suggestions
Analyzes content to suggest relevant tags:
- Keywords extraction (top 5 terms)
- Section-based tags (e.g., `#knowledge`, `#process`)
- Category detection (e.g., `#agent`, `#workflow`, `#integration`)

### 2.4 Validation & Health Checks

#### Pre-Flight Checks
Before any operation:
- ✅ File exists and is readable
- ✅ Target directory exists
- ✅ No name conflicts in destination
- ✅ File is valid markdown
- ✅ Within vault boundaries

#### Post-Operation Validation
After any operation:
- ✅ File successfully moved/renamed
- ✅ No broken links created
- ✅ Metadata properly formatted
- ✅ Naming convention followed
- ✅ Operation logged

#### Vault Health Audit
Periodic checks (manual trigger):
- Files in wrong locations
- Naming convention violations
- Missing metadata
- Broken internal links
- Orphaned files (no links to/from)

---

## 3. Usage Scenarios

### Scenario 1: Daily Vault Cleanup
**Trigger**: Manual command or scheduled (morning)
**Action**: Scan vault for misplaced files and rename violations
**Outcome**: Report of issues + auto-fix (Tier 1) or HITL request (Tier 2+)

```yaml
Command: /organize-vault --auto-fix tier-1
Process:
  1. Scan all folders for misnamed files
  2. Auto-fix: Rename to convention (logged)
  3. Auto-fix: Add missing frontmatter (logged)
  4. Report: Files that need manual review
  5. HITL: Request approval for risky moves
```

### Scenario 2: New File Import
**Trigger**: Human adds file with non-standard name
**Action**: Detect, analyze, suggest proper location and name
**Outcome**: File organized and renamed with audit trail

```yaml
Example:
  Input: "Meeting Notes.md" dropped in vault root
  Analysis:
    - Content: Meeting notes from 2026-02-16
    - Type: Episodic memory
  Suggestion:
    - Location: 80-MEMORY/episodic/
    - Name: EP-20260216-meeting-notes.md
    - Tags: [meeting, notes, 2026-02-16]
  Action: Move + Rename (with logging)
```

### Scenario 3: Bulk Organization
**Trigger**: Manual command after importing many files
**Action**: Process all unorganized files in staging area
**Outcome**: Vault organized, report generated

```yaml
Command: /organize-bulk --source vault/inbox/ --dry-run
Process:
  1. Scan inbox folder (staging area)
  2. Classify each file
  3. Generate plan with proposed moves
  4. Show plan to human
  5. Request approval
  6. Execute approved moves
  7. Generate completion report
```

### Scenario 4: Proactive Monitoring
**Trigger**: File watcher detects new/modified file
**Action**: Validate file follows conventions
**Outcome**: Auto-fix or notification

```yaml
Event: New file created "test.md" in 10-KNOWLEDGE/
Check:
  - Name follows NNN-descriptor.md? ❌
  - Frontmatter present? ❌
Action:
  - Log warning
  - Suggest fix: "001-test.md" with frontmatter
  - Offer one-click fix
```

---

## 4. Dependencies

### 4.1 Core Dependencies

#### Obsidian Vault Structure
- **Required**: Vault must follow `obsidian-vault/` structure
- **Validation**: Check vault structure before any operation
- **Fallback**: If structure invalid, report error and exit

#### File System Access
- **Required**: Read/write permissions on vault folder
- **Scope**: Limited to `obsidian-vault/` only
- **Safety**: Never operate outside vault boundaries

#### Naming Conventions
- **Required**: `NAMING-CONVENTIONS.md` must exist
- **Usage**: Parse convention rules for validation
- **Update**: Sync with any convention changes

### 4.2 External Dependencies

#### Python Libraries (for implementation)
```yaml
Required:
  - pathlib: File path operations
  - yaml: Frontmatter parsing
  - re: Pattern matching
  - shutil: Safe file operations
  - datetime: Timestamp handling

Optional:
  - watchdog: File system monitoring
  - hashlib: File integrity checks
```

#### MCP Servers
```yaml
Optional Integrations:
  - filesystem-mcp: Advanced file operations
  - obsidian-mcp: Obsidian-specific operations
  - git-mcp: Version control integration
```

### 4.3 Skill Dependencies

#### Prerequisites (must exist first)
```yaml
Required:
  - HUMAN_IN_THE_LOOP_APPROVAL_SKILL: For Tier 2+ operations
  - Logging system: 70-LOGS/ structure must exist

Recommended:
  - SECURITY_AND_CREDENTIAL_MANAGEMENT_SKILL: For safe operations
  - RALPH_WIGGUM_LOOP_SKILL: For scheduled execution
```

---

## 5. Logging & Auditability

### 5.1 Log Levels & Events

#### INFO: Normal Operations
```yaml
Level: INFO
Events:
  - File renamed successfully
  - File moved to correct location
  - Frontmatter updated
  - Validation passed
Format: "INFO: Renamed {old_path} → {new_path} | Duration: {ms}ms"
Location: 70-LOGS/daily/YYYY-MM-DD.md
```

#### WARN: Issues Detected
```yaml
Level: WARN
Events:
  - Naming convention violation detected
  - Missing frontmatter
  - File in wrong location
  - Potential duplicate
Format: "WARN: File {path} violates convention: {rule} | Suggestion: {fix}"
Location: 70-LOGS/warnings/YYYY-MM-DD.md
```

#### ERROR: Operation Failures
```yaml
Level: ERROR
Events:
  - File operation failed
  - Permission denied
  - Invalid file format
  - Validation failed
Format: "ERROR: Failed to move {path} | Reason: {error} | Rollback: {action}"
Location: 70-LOGS/errors/YYYY-MM-DD.md
```

### 5.2 Audit Trail

#### Operation Log Entry
Every file operation creates an audit entry:

```yaml
---
timestamp: 2026-02-16T14:30:45.123Z
operation: rename
file_before: vault/Meeting Notes.md
file_after: vault/80-MEMORY/episodic/EP-20260216-meeting-notes.md
reason: Convention enforcement
triggered_by: daily-cleanup
approved_by: auto (tier-1)
changes:
  - location: root → 80-MEMORY/episodic/
  - filename: "Meeting Notes.md" → "EP-20260216-meeting-notes.md"
  - frontmatter: added (id, created, tags)
result: success
duration_ms: 23
checksum_before: abc123...
checksum_after: abc123... (content unchanged)
---
```

#### Daily Summary Report
Generated at end of each day:

```markdown
# Filesystem Automation Report - 2026-02-16

## Summary
- Files Organized: 12
- Files Renamed: 8
- Metadata Updated: 15
- Errors: 0
- Warnings: 3

## Actions Taken
### Auto-Fixed (Tier 1)
- Renamed 8 files to follow conventions
- Moved 4 files to correct locations
- Added frontmatter to 7 files

### Warnings (Need Review)
- 3 files with ambiguous classification
- Located in: vault/inbox/

## Vault Health
- Convention Compliance: 98.5% (up from 96.2%)
- Missing Metadata: 2 files (down from 9)
- Misplaced Files: 3 (down from 7)

## Next Actions
- [ ] Review ambiguous files in inbox
- [ ] Consider adding new tags for emerging topics
```

### 5.3 Rollback Capability

#### Pre-Operation Snapshot
Before any operation:
```yaml
Create snapshot:
  - Record original file path
  - Record original file content hash
  - Record original metadata
  - Store in: 70-LOGS/operations/snapshots/
  - Retention: 7 days
```

#### Rollback Procedure
If operation needs reversal:
```yaml
Rollback steps:
  1. Read operation log entry
  2. Retrieve snapshot
  3. Restore file to original location
  4. Restore original filename
  5. Restore original metadata
  6. Verify checksum matches
  7. Log rollback action
```

---

## 6. Error Handling

### 6.1 Error Categories

#### Recoverable Errors
Errors that can be retried or worked around:

```python
# Pseudo-code example
try:
    rename_file(old_path, new_path)
except FileExistsError:
    # Recoverable: Suggest alternative name
    new_path = generate_unique_name(new_path)
    log.warn(f"Name conflict, using: {new_path}")
    rename_file(old_path, new_path)
except PermissionError:
    # Recoverable: Request elevated permission
    log.error("Permission denied, requesting HITL approval")
    request_approval(operation="rename", tier=2)
```

#### Non-Recoverable Errors
Errors that require human intervention:

```python
try:
    move_file(source, destination)
except VaultStructureInvalid:
    # Non-recoverable: Vault corrupted
    log.critical("Vault structure invalid, aborting")
    notify_human("Vault health check failed")
    exit_gracefully()
except OutsideVaultBoundary:
    # Non-recoverable: Security violation
    log.critical("Attempted operation outside vault")
    notify_security("Boundary violation attempt")
    exit_gracefully()
```

### 6.2 Error Handling Patterns

#### Try-Validate-Execute-Verify (TVEV)
```yaml
Pattern:
  1. Try: Validate pre-conditions
     - File exists
     - Target valid
     - Permissions OK
     - No conflicts

  2. Validate: Check operation safety
     - Within vault bounds
     - Follows conventions
     - No data loss risk

  3. Execute: Perform operation
     - Atomic file operations
     - Create backup first
     - Log every step

  4. Verify: Post-operation checks
     - File in expected location
     - Content integrity maintained
     - Links still valid
     - Log success
```

#### Fail-Fast Principle
```yaml
Rule: Detect problems early, don't propagate errors

Examples:
  - Invalid input → Reject immediately (don't attempt)
  - Missing dependency → Exit gracefully (don't fail halfway)
  - Vault corrupted → Stop all operations (don't make it worse)
  - Permission denied → Request approval (don't retry indefinitely)
```

### 6.3 Circuit Breaker

#### Purpose
Prevent cascade failures if filesystem becomes unstable

```yaml
Circuit Breaker Configuration:
  failure_threshold: 3 consecutive errors
  timeout: 5 minutes (pause operations)
  half_open_requests: 1 (test if recovered)

State Machine:
  CLOSED (Normal):
    - Operations proceed
    - Errors tracked
    - If threshold reached → OPEN

  OPEN (Failing):
    - All operations rejected
    - Return cached results or error
    - After timeout → HALF_OPEN

  HALF_OPEN (Testing):
    - Allow 1 test operation
    - If success → CLOSED
    - If failure → OPEN (reset timeout)
```

---

## 7. Security & Safety

### 7.1 Vault Boundary Enforcement

#### Path Validation
Every operation validates path is within vault:

```python
# Pseudo-code
def validate_path(path):
    """Ensure path is within vault boundaries"""
    vault_root = "/path/to/obsidian-vault"
    resolved_path = os.path.realpath(path)

    # Check 1: Must start with vault root
    if not resolved_path.startswith(vault_root):
        raise SecurityError("Path outside vault boundary")

    # Check 2: No symlinks that escape vault
    if os.path.islink(path):
        raise SecurityError("Symlinks not allowed")

    # Check 3: No parent directory traversal
    if ".." in path:
        raise SecurityError("Parent traversal not allowed")

    return resolved_path
```

#### Forbidden Paths
Never operate on these paths:

```yaml
Blacklist:
  - .git/: Version control files
  - .obsidian/: Obsidian configuration
  - .claude/: Skill files
  - .specify/: Spec artifacts
  - ../*: Anything outside vault
  - ~/*: User home directory
  - /: System root
```

### 7.2 Safe File Operations

#### Atomic Operations
Use atomic file operations to prevent corruption:

```python
# Pseudo-code
def rename_file_safely(source, destination):
    """Rename file atomically with rollback"""

    # Step 1: Validate
    if not os.path.exists(source):
        raise FileNotFoundError(source)

    # Step 2: Create backup
    backup_path = create_backup(source)

    try:
        # Step 3: Atomic rename
        os.rename(source, destination)

        # Step 4: Verify
        if not os.path.exists(destination):
            raise OperationFailed("Rename verification failed")

        # Step 5: Log success
        log.info(f"Renamed: {source} → {destination}")

        # Step 6: Clean backup after success
        os.remove(backup_path)

    except Exception as e:
        # Step 7: Rollback on failure
        restore_from_backup(backup_path, source)
        log.error(f"Rename failed, rolled back: {e}")
        raise
```

#### Content Integrity
Verify file content is unchanged after operations:

```python
# Pseudo-code
def verify_content_integrity(operation):
    """Ensure file content unchanged after move/rename"""

    # Before operation
    checksum_before = hash_file(operation.source)

    # Perform operation
    execute_operation(operation)

    # After operation
    checksum_after = hash_file(operation.destination)

    # Verify
    if checksum_before != checksum_after:
        rollback_operation(operation)
        raise IntegrityError("Content changed during operation")

    return True
```

### 7.3 HITL Integration

#### Tier 1: Auto-Approve (Current Scope)
Operations that can proceed without approval:

```yaml
Auto-Approved:
  - Rename within same folder (convention fixes)
  - Add/update frontmatter metadata
  - Move between valid vault folders
  - Tag suggestions (no execution)

Conditions:
  - Within obsidian-vault/ only
  - No content modification
  - Fully logged
  - Reversible
```

#### Tier 2: Require Approval (Future)
Operations that need human approval:

```yaml
Require HITL:
  - Bulk operations (>10 files)
  - Moving files to different sections
  - Renaming with semantic changes
  - Operations on files with links

Approval Flow:
  1. Log intent to 70-LOGS/hitl/pending/
  2. Notify human (desktop notification)
  3. Show preview of changes
  4. Wait for approval (4 hour SLA)
  5. Execute if approved
  6. Log outcome
```

#### Tier 3: Always Block (Out of Scope)
Operations never allowed by this skill:

```yaml
Blocked Operations:
  - File deletion (use dedicated deletion skill)
  - Content modification (use editor, not automation)
  - Binary file operations
  - Operations outside vault
  - Batch operations without review
```

---

## 8. Constitution Compliance

### ✅ Principle I: Local-First Sovereignty
**Requirement**: Vault is source of truth
**Compliance**:
- All operations logged to vault (`70-LOGS/`)
- No external database dependencies
- All state persists in markdown files
- Audit trail in vault history

### ✅ Principle II: Explicit Over Implicit
**Requirement**: Declare intent before action
**Compliance**:
- Every operation logged before execution
- Pre-flight checks declare assumptions
- Dry-run mode shows intent without executing
- All decisions traceable in logs

### ✅ Principle III: HITL by Default
**Requirement**: High-risk actions require approval
**Compliance**:
- Tier 1 operations only (low-risk writes)
- Bulk operations (>10 files) escalate to Tier 2
- HITL integration points defined
- Graceful degradation if approval system unavailable

### ✅ Principle IV: Composability Through Standards
**Requirement**: Skills are atomic and composable
**Compliance**:
- Single responsibility: filesystem organization only
- Clear input/output contract
- No dependencies on other business logic
- Can be called by orchestrator or manually

### ✅ Principle V: Memory as Knowledge
**Requirement**: Learn from every interaction
**Compliance**:
- Operation logs create episodic memory
- Common patterns stored as semantic memory
- Naming convention enforcement improves over time
- Vault health trends tracked

### ✅ Principle VI: Fail Safe, Fail Visible
**Requirement**: Errors logged, contained, never silent
**Compliance**:
- All errors logged to `70-LOGS/errors/`
- Circuit breaker prevents cascade failures
- Rollback mechanism for failed operations
- Health checks every iteration

### ✅ Section 5: Vault Governance
**Requirement**: Follow vault structure and naming
**Compliance**:
- Enforces folder structure from `obsidian-vault/`
- Validates against `NAMING-CONVENTIONS.md`
- Never modifies vault structure itself
- Reports violations, doesn't create them

### ✅ Section 7: Logging Requirements
**Requirement**: Comprehensive logging
**Compliance**:
- INFO logs for all operations
- WARN logs for detected issues
- ERROR logs for failures
- Structured format with timestamps, context
- Daily summary reports

### ✅ Section 9: Skill Design Rules
**Requirement**: Single responsibility, idempotent, observable, testable
**Compliance**:
- ✅ Single Responsibility: File organization only
- ✅ Idempotent: Running twice = same result
- ✅ Fail Fast: Validates before execution
- ✅ Observable: Comprehensive logging
- ✅ Testable: Dry-run mode, examples provided

---

## 9. Demo Scenario: Complete Walkthrough

### Scenario: Weekly Vault Cleanup

#### Setup
```yaml
Starting State:
  Vault Root:
    - "meeting notes.md" (misplaced, wrong name)
    - "agent_profile_sales.MD" (wrong extension, name)

  10-KNOWLEDGE/:
    - 001-customer-agent.md
    - 002-support-agent.md

  80-MEMORY/episodic/:
    - (empty)
```

#### Step 1: Trigger Cleanup
```bash
Command: /organize-vault --mode auto-fix --report detailed

Agent Response:
"Starting vault cleanup scan...
Found 2 issues. Running auto-fix for Tier 1 operations..."
```

#### Step 2: Issue Detection
```yaml
Issues Found:
  Issue 1:
    File: "meeting notes.md"
    Location: vault root
    Problems:
      - Wrong location (should be in 80-MEMORY/episodic/)
      - Wrong name format (missing EP- prefix and date)
      - Missing frontmatter

  Issue 2:
    File: "agent_profile_sales.MD"
    Location: vault root
    Problems:
      - Wrong location (should be in 10-KNOWLEDGE/agents/)
      - Wrong name format (underscore, wrong caps)
      - Wrong extension (.MD should be .md)
      - Missing frontmatter
```

#### Step 3: Analysis & Planning
```yaml
Issue 1 - Meeting Notes:
  Content Analysis:
    - Detected: Meeting notes content
    - Date mentioned: 2026-02-16
    - Type: Episodic memory

  Proposed Fix:
    - Target location: 80-MEMORY/episodic/
    - New name: EP-20260216-meeting-notes.md
    - Add frontmatter:
        id: EP-20260216-meeting-notes
        type: episodic-memory
        created: 2026-02-16T10:30:00Z
        tags: [meeting, notes, episodic]

  Tier: 1 (Auto-approve)

Issue 2 - Sales Agent Profile:
  Content Analysis:
    - Detected: Agent profile structure
    - Agent name: Sales Agent
    - Type: Knowledge article

  Proposed Fix:
    - Target location: 10-KNOWLEDGE/agents/
    - New name: 003-sales-agent.md (next ID)
    - Normalize extension: .MD → .md
    - Add frontmatter:
        id: sales-agent
        type: agent-profile
        created: 2026-02-16T14:20:00Z
        tags: [agent, sales, knowledge]

  Tier: 1 (Auto-approve)
```

#### Step 4: Execution (Issue 1)
```yaml
Operation: Fix Issue 1
Timestamp: 2026-02-16T14:25:30.123Z

Pre-Flight Checks:
  ✅ Source file exists
  ✅ Source file readable
  ✅ Target directory exists
  ✅ No name conflict in target
  ✅ Within vault boundaries

Create Backup:
  ✅ Backup created: .backups/meeting-notes-20260216T142530.md

Execute Move:
  ✅ Moved: vault/meeting-notes.md
      → vault/80-MEMORY/episodic/EP-20260216-meeting-notes.md

Add Frontmatter:
  ✅ Frontmatter added:
      ---
      id: EP-20260216-meeting-notes
      type: episodic-memory
      created: 2026-02-16T10:30:00Z
      updated: 2026-02-16T14:25:30Z
      tags: [meeting, notes, episodic]
      ---

Post-Operation Validation:
  ✅ File exists at new location
  ✅ Content integrity verified (checksum match)
  ✅ Frontmatter valid YAML
  ✅ Naming convention followed

Cleanup:
  ✅ Backup removed (operation successful)

Log Entry Created:
  Location: 70-LOGS/daily/2026-02-16.md
  Level: INFO
  Message: "Organized meeting-notes.md → EP-20260216-meeting-notes.md"
  Duration: 45ms
```

#### Step 5: Execution (Issue 2)
```yaml
Operation: Fix Issue 2
Timestamp: 2026-02-16T14:25:31.456Z

Pre-Flight Checks:
  ✅ Source file exists
  ✅ Source file readable
  ✅ Target directory exists
  ✅ Next ID available: 003
  ✅ Within vault boundaries

Create Backup:
  ✅ Backup created: .backups/agent_profile_sales-20260216T142531.md

Execute Operations:
  ✅ Moved: vault/agent_profile_sales.MD
      → vault/10-KNOWLEDGE/agents/003-sales-agent.md
  ✅ Extension normalized: .MD → .md
  ✅ Name standardized: underscores → hyphens, lowercase

Add Frontmatter:
  ✅ Frontmatter added:
      ---
      id: sales-agent
      type: agent-profile
      created: 2026-02-16T14:20:00Z
      updated: 2026-02-16T14:25:31Z
      tags: [agent, sales, knowledge]
      ---

Post-Operation Validation:
  ✅ File exists at new location
  ✅ Content integrity verified
  ✅ Follows naming convention
  ✅ ID sequence correct (003 after 002)

Cleanup:
  ✅ Backup removed

Log Entry Created:
  Location: 70-LOGS/daily/2026-02-16.md
  Level: INFO
  Message: "Organized agent_profile_sales.MD → 003-sales-agent.md"
  Duration: 38ms
```

#### Step 6: Report Generation
```markdown
# Filesystem Automation Report
**Date**: 2026-02-16
**Time**: 14:25:32
**Duration**: 83ms

## Summary
✅ **Success**: 2 files organized
❌ **Errors**: 0
⚠️ **Warnings**: 0

## Actions Taken

### File 1: Meeting Notes
- **Before**: `vault/meeting notes.md`
- **After**: `vault/80-MEMORY/episodic/EP-20260216-meeting-notes.md`
- **Changes**:
  - ✅ Moved to correct location
  - ✅ Renamed to convention
  - ✅ Added frontmatter
  - ✅ Added tags: [meeting, notes, episodic]
- **Tier**: 1 (Auto-approved)
- **Duration**: 45ms

### File 2: Sales Agent Profile
- **Before**: `vault/agent_profile_sales.MD`
- **After**: `vault/10-KNOWLEDGE/agents/003-sales-agent.md`
- **Changes**:
  - ✅ Moved to correct location
  - ✅ Renamed to convention (003 ID assigned)
  - ✅ Extension normalized (.MD → .md)
  - ✅ Added frontmatter
  - ✅ Added tags: [agent, sales, knowledge]
- **Tier**: 1 (Auto-approved)
- **Duration**: 38ms

## Vault Health Metrics

### Before Cleanup
- Files in wrong location: 2
- Naming violations: 2
- Missing frontmatter: 2
- Convention compliance: 97.3%

### After Cleanup
- Files in wrong location: 0 ✅
- Naming violations: 0 ✅
- Missing frontmatter: 0 ✅
- Convention compliance: 100% ✅

## Audit Trail
All operations logged to:
- `70-LOGS/daily/2026-02-16.md`
- `70-LOGS/operations/2026-02-16-cleanup.log`

## Next Actions
✅ No pending issues
✅ Vault is fully compliant
✅ All files properly organized

---
Generated by: FILESYSTEM_AUTOMATION_SKILL v1.0.0
Constitution Compliant: ✅ All principles followed
```

#### Step 7: Verification
```bash
Final Vault State:
  vault/
    ├── 10-KNOWLEDGE/agents/
    │   ├── 001-customer-agent.md
    │   ├── 002-support-agent.md
    │   └── 003-sales-agent.md ← Newly organized
    ├── 80-MEMORY/episodic/
    │   └── EP-20260216-meeting-notes.md ← Newly organized
    └── 70-LOGS/daily/
        └── 2026-02-16.md ← Contains audit trail

Human Review:
  ✅ Files in correct locations
  ✅ Names follow conventions
  ✅ Frontmatter present and valid
  ✅ Content unchanged (verified by checksum)
  ✅ Full audit trail available
```

---

## 10. Implementation Roadmap

### Phase 1: Core Functions (Week 1)
```yaml
Deliverables:
  - [ ] File validation engine
  - [ ] Naming convention parser
  - [ ] Safe rename function
  - [ ] Safe move function
  - [ ] Logging system integration
  - [ ] Unit tests (80% coverage)

Success Criteria:
  - Can rename single file safely
  - Can move single file safely
  - All operations logged
  - Rollback works
```

### Phase 2: Analysis & Classification (Week 2)
```yaml
Deliverables:
  - [ ] Content analyzer
  - [ ] Folder detection logic
  - [ ] ID assignment system
  - [ ] Frontmatter generator
  - [ ] Tag suggestion engine
  - [ ] Integration tests

Success Criteria:
  - Can classify file by content
  - Can suggest correct location
  - Can generate valid frontmatter
  - Suggestions are accurate (>90%)
```

### Phase 3: Batch Operations (Week 3)
```yaml
Deliverables:
  - [ ] Vault scanner
  - [ ] Batch processor
  - [ ] Progress reporting
  - [ ] HITL integration
  - [ ] Report generator
  - [ ] End-to-end tests

Success Criteria:
  - Can process 100+ files safely
  - HITL gates work correctly
  - Reports are accurate
  - No data loss
```

### Phase 4: Monitoring & Polish (Week 4)
```yaml
Deliverables:
  - [ ] File watcher integration
  - [ ] Proactive validation
  - [ ] Health check dashboard
  - [ ] Performance optimization
  - [ ] Documentation finalization
  - [ ] User acceptance testing

Success Criteria:
  - Real-time validation works
  - Performance acceptable (<100ms per file)
  - Documentation complete
  - Ready for Bronze Tier deployment
```

---

## 11. Testing Strategy

### Unit Tests
```yaml
Test Coverage:
  - validate_path(): Boundary enforcement
  - rename_file_safely(): Atomic operations
  - parse_naming_convention(): Convention rules
  - assign_next_id(): Sequence logic
  - generate_frontmatter(): Metadata creation

Test Cases: 50+ covering edge cases
```

### Integration Tests
```yaml
Test Scenarios:
  - Organize single file end-to-end
  - Batch process 10 files
  - Handle name conflicts
  - Rollback on failure
  - HITL approval flow

Test Environment: Isolated test vault
```

### Acceptance Tests
```yaml
Real-World Scenarios:
  - Weekly cleanup on actual vault
  - Import external files
  - Handle various file types
  - Stress test (1000 files)
  - Human usability testing

Success Criteria: All scenarios pass without errors
```

---

## 12. Success Metrics

### Performance Targets
- **Single File Operation**: < 100ms
- **Batch Operation (10 files)**: < 1 second
- **Vault Scan (1000 files)**: < 10 seconds
- **Memory Usage**: < 50MB

### Quality Targets
- **Accuracy**: 95%+ correct classifications
- **Reliability**: 99.9%+ operations succeed
- **Safety**: 0 data loss incidents
- **Compliance**: 100% constitution adherence

### User Experience Targets
- **Setup Time**: < 5 minutes
- **Learning Curve**: < 30 minutes
- **Manual Intervention**: < 1% of operations
- **User Satisfaction**: 4.5+ / 5.0

---

## 13. Troubleshooting Guide

### Common Issues

#### Issue: "Permission denied"
```yaml
Symptom: Cannot move/rename file
Cause: Insufficient file system permissions
Fix:
  1. Check file is not open in Obsidian
  2. Verify vault folder permissions
  3. Run with appropriate user permissions
  4. Check antivirus isn't blocking
```

#### Issue: "Name conflict detected"
```yaml
Symptom: Target filename already exists
Cause: Duplicate file name in destination
Fix:
  1. Skill auto-generates alternative: filename-2.md
  2. Or requests HITL decision
  3. Logs both files for human review
```

#### Issue: "Circuit breaker open"
```yaml
Symptom: All operations rejected
Cause: Multiple consecutive failures
Fix:
  1. Check vault health
  2. Review error logs
  3. Fix underlying issue
  4. Wait for cooldown (5 min)
  5. Retry operation
```

---

## 14. Future Enhancements (Silver/Gold Tier)

### Silver Tier Additions
- AI-powered content classification
- Smart tag generation using LLM
- Link preservation during moves
- Conflict resolution strategies
- Real-time file watching

### Gold Tier Additions
- Predictive organization (before human asks)
- Learning from human corrections
- Custom organization rules per user
- Multi-vault support
- Integration with external tools

---

## Approval & Sign-Off

**Specification Complete**: 2026-02-16
**Reviewed By**: [Human Operator Name]
**Approved For Implementation**: ⏳ Pending
**Target Completion**: Week 1-4 (Bronze Tier)

**Constitution Compliance**: ✅ All requirements met
**Security Review**: ✅ No vulnerabilities identified
**HITL Integration**: ✅ Tier 1 scoped appropriately

---

**Ready for Implementation**: Yes
**Blockers**: None
**Next Step**: Begin Phase 1 development
