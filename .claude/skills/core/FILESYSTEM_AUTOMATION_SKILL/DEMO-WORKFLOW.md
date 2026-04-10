# FILESYSTEM_AUTOMATION_SKILL - Demo Workflow

**Version**: 1.0.0
**Date**: 2026-02-16
**Purpose**: Step-by-step demonstration of filesystem automation capabilities
**Estimated Duration**: 30 minutes

---

## Prerequisites

### Setup Requirements
- [ ] Obsidian vault structure exists at `obsidian-vault/`
- [ ] Naming conventions documented in `NAMING-CONVENTIONS.md`
- [ ] Logging directories created (`70-LOGS/`)
- [ ] Constitution.md ratified
- [ ] Test environment isolated from production

### Test Data Preparation
Create these test files in vault root:

```bash
# Navigate to vault root
cd obsidian-vault/

# Create test files with intentional issues
echo "# Meeting with team" > "Meeting Notes Jan 15.md"
echo "# Sales agent profile" > "agent_Sales.MD"
echo "# Email workflow" > "workflow_email_automation.txt"
echo "# Customer data analysis" > "analysis.md"
```

---

## Demo 1: Single File Organization

### Objective
Demonstrate basic file organization for one misplaced file.

### Scenario
A meeting notes file is in the wrong location with incorrect naming.

### Setup
```yaml
Test File:
  Location: obsidian-vault/
  Name: "Meeting Notes Jan 15.md"
  Content: |
    # Meeting with team
    Date: 2026-01-15
    Attendees: Alice, Bob, Charlie

    Discussion:
    - Project timeline
    - Resource allocation
    - Next steps
```

### Expected Issues
1. ❌ File in root (should be in `80-MEMORY/episodic/`)
2. ❌ Wrong name format (spaces, no prefix, wrong date format)
3. ❌ Missing frontmatter
4. ❌ No tags

### Execution Steps

#### Step 1: Scan and Detect
```bash
Command: /filesystem-organize --scan --target "Meeting Notes Jan 15.md"

Expected Output:
┌─────────────────────────────────────────────────┐
│ File Analysis: Meeting Notes Jan 15.md         │
├─────────────────────────────────────────────────┤
│ Status: ⚠️  ISSUES DETECTED                     │
│                                                 │
│ Issues (4):                                     │
│ 1. Location: vault root → should be episodic   │
│ 2. Name: Missing EP- prefix                    │
│ 3. Name: Wrong date format (Jan 15 vs YYYYMMDD)│
│ 4. Metadata: Missing frontmatter               │
│                                                 │
│ Classification:                                 │
│ - Type: Episodic Memory (meeting notes)        │
│ - Date: 2026-01-15 (extracted from content)    │
│ - Confidence: 95%                               │
└─────────────────────────────────────────────────┘
```

#### Step 2: Generate Fix Plan
```bash
Command: /filesystem-organize --plan "Meeting Notes Jan 15.md"

Expected Output:
┌─────────────────────────────────────────────────┐
│ Organization Plan                               │
├─────────────────────────────────────────────────┤
│ Source:                                         │
│   obsidian-vault/Meeting Notes Jan 15.md       │
│                                                 │
│ Destination:                                    │
│   obsidian-vault/80-MEMORY/episodic/           │
│   EP-20260115-meeting-notes.md                 │
│                                                 │
│ Changes:                                        │
│   ✓ Move to correct folder                     │
│   ✓ Rename with EP- prefix                     │
│   ✓ Normalize date format (YYYYMMDD)           │
│   ✓ Add frontmatter                            │
│   ✓ Suggest tags: [meeting, team, episodic]    │
│                                                 │
│ Risk Assessment:                                │
│   Tier: 1 (Low-risk write)                     │
│   Approval: Auto (within vault, reversible)    │
│   Backup: Created before operation             │
│                                                 │
│ Approve? (y/n):                                 │
└─────────────────────────────────────────────────┘
```

#### Step 3: Execute (Dry Run)
```bash
Command: /filesystem-organize --execute --dry-run "Meeting Notes Jan 15.md"

Expected Output:
[DRY RUN MODE - No changes will be made]

[2026-02-16T10:30:00Z] INFO: Starting organization operation
[2026-02-16T10:30:00Z] INFO: Target: Meeting Notes Jan 15.md
[2026-02-16T10:30:00Z] INFO: Pre-flight checks...
  ✓ File exists and readable
  ✓ Target directory exists (80-MEMORY/episodic/)
  ✓ No name conflicts
  ✓ Within vault boundaries
  ✓ Valid markdown format

[2026-02-16T10:30:00Z] INFO: Would create backup at:
  .backups/meeting-notes-jan-15-20260216T103000.md

[2026-02-16T10:30:00Z] INFO: Would move:
  FROM: obsidian-vault/Meeting Notes Jan 15.md
  TO:   obsidian-vault/80-MEMORY/episodic/EP-20260115-meeting-notes.md

[2026-02-16T10:30:00Z] INFO: Would add frontmatter:
  ---
  id: EP-20260115-meeting-notes
  name: Meeting with team
  type: episodic-memory
  created: 2026-01-15T00:00:00Z
  updated: 2026-02-16T10:30:00Z
  tags: [meeting, team, episodic]
  ---

[2026-02-16T10:30:00Z] INFO: Dry run complete. No changes made.

Summary:
  Operations planned: 1
  Estimated duration: ~50ms
  Risk level: Tier 1 (Auto-approve)
```

#### Step 4: Execute (Real)
```bash
Command: /filesystem-organize --execute "Meeting Notes Jan 15.md"

Expected Output:
[LIVE MODE - Changes will be made]

[2026-02-16T10:31:00Z] INFO: Starting organization operation
[2026-02-16T10:31:00Z] INFO: Pre-flight checks passed
[2026-02-16T10:31:00Z] INFO: Creating backup...
  ✓ Backup created: .backups/meeting-notes-jan-15-20260216T103100.md

[2026-02-16T10:31:00Z] INFO: Moving file...
  ✓ Moved successfully (28ms)

[2026-02-16T10:31:00Z] INFO: Adding frontmatter...
  ✓ Frontmatter added (12ms)

[2026-02-16T10:31:00Z] INFO: Post-operation validation...
  ✓ File exists at destination
  ✓ Content integrity verified (checksum match)
  ✓ Frontmatter valid YAML
  ✓ Naming convention followed

[2026-02-16T10:31:00Z] INFO: Cleaning up backup...
  ✓ Backup removed (operation successful)

[2026-02-16T10:31:00Z] INFO: Logging to audit trail...
  ✓ Logged to: 70-LOGS/daily/2026-02-16.md

✅ SUCCESS: File organized in 45ms

  Before: obsidian-vault/Meeting Notes Jan 15.md
  After:  obsidian-vault/80-MEMORY/episodic/EP-20260115-meeting-notes.md
```

### Verification

#### Check 1: File Location
```bash
Command: ls -la obsidian-vault/80-MEMORY/episodic/

Expected:
EP-20260115-meeting-notes.md ✓
```

#### Check 2: File Content
```bash
Command: cat obsidian-vault/80-MEMORY/episodic/EP-20260115-meeting-notes.md

Expected:
---
id: EP-20260115-meeting-notes
name: Meeting with team
type: episodic-memory
created: 2026-01-15T00:00:00Z
updated: 2026-02-16T10:31:00Z
tags: [meeting, team, episodic]
---

# Meeting with team
Date: 2026-01-15
Attendees: Alice, Bob, Charlie

Discussion:
- Project timeline
- Resource allocation
- Next steps
```

#### Check 3: Audit Log
```bash
Command: cat obsidian-vault/70-LOGS/daily/2026-02-16.md

Expected Entry:
[2026-02-16T10:31:00Z] INFO: FILESYSTEM_AUTOMATION
  Operation: organize
  File: Meeting Notes Jan 15.md → EP-20260115-meeting-notes.md
  Location: root → 80-MEMORY/episodic/
  Changes: move, rename, add_frontmatter
  Tier: 1
  Duration: 45ms
  Status: success
  Checksum: abc123def456 (verified)
```

### Success Criteria
- [x] File moved to correct location
- [x] File renamed with proper convention
- [x] Frontmatter added with correct metadata
- [x] Content unchanged (verified by checksum)
- [x] Operation logged to audit trail
- [x] No errors or warnings
- [x] Backup created and cleaned up

---

## Demo 2: Batch Organization

### Objective
Demonstrate bulk processing of multiple misplaced files.

### Scenario
4 files with various issues need organization.

### Setup
```yaml
Test Files:
  1. "agent_Sales.MD"
     - Location: vault root
     - Issues: Wrong name, wrong extension, missing frontmatter
     - Target: 10-KNOWLEDGE/agents/003-sales-agent.md

  2. "workflow_email_automation.txt"
     - Location: vault root
     - Issues: Wrong name, wrong extension (.txt), missing prefix
     - Target: 20-PROCESSES/workflows/WF-004-email-automation.md

  3. "analysis.md"
     - Location: vault root
     - Issues: Vague name, missing metadata
     - Target: 50-BUSINESS/analytics/AN-001-customer-data-analysis.md

  4. "notes.md"
     - Location: vault root
     - Issues: Too generic, no context
     - Target: Needs human decision (ambiguous classification)
```

### Execution Steps

#### Step 1: Batch Scan
```bash
Command: /filesystem-organize --batch --scan obsidian-vault/

Expected Output:
┌─────────────────────────────────────────────────┐
│ Batch Scan Results                              │
├─────────────────────────────────────────────────┤
│ Scanned: 4 files                                │
│ Issues Found: 4 files                           │
│ Auto-Fixable: 3 files (Tier 1)                  │
│ Needs Review: 1 file (ambiguous)                │
│                                                 │
│ Auto-Fixable Files:                             │
│   1. agent_Sales.MD                             │
│      → 10-KNOWLEDGE/agents/003-sales-agent.md   │
│                                                 │
│   2. workflow_email_automation.txt              │
│      → 20-PROCESSES/workflows/WF-004-email...   │
│                                                 │
│   3. analysis.md                                │
│      → 50-BUSINESS/analytics/AN-001-customer... │
│                                                 │
│ Needs Human Review:                             │
│   1. notes.md                                   │
│      Reason: Ambiguous classification           │
│      Options:                                   │
│        a) Episodic memory                       │
│        b) General knowledge                     │
│        c) Task list                             │
│                                                 │
│ Proceed with auto-fix? (y/n):                  │
└─────────────────────────────────────────────────┘
```

#### Step 2: Execute Batch (Tier 1 only)
```bash
Command: /filesystem-organize --batch --execute --tier 1

Expected Output:
[BATCH MODE] Processing 3 files...

[1/3] Processing: agent_Sales.MD
  ✓ Analyzed: Agent profile detected
  ✓ Moved: 10-KNOWLEDGE/agents/003-sales-agent.md
  ✓ Duration: 42ms

[2/3] Processing: workflow_email_automation.txt
  ✓ Analyzed: Workflow detected
  ✓ Moved: 20-PROCESSES/workflows/WF-004-email-automation.md
  ✓ Extension normalized: .txt → .md
  ✓ Duration: 38ms

[3/3] Processing: analysis.md
  ✓ Analyzed: Business analytics detected
  ✓ Moved: 50-BUSINESS/analytics/AN-001-customer-data-analysis.md
  ✓ Duration: 41ms

✅ Batch Complete
  Processed: 3 files
  Success: 3 files
  Failed: 0 files
  Skipped: 1 file (needs review)
  Total Duration: 121ms

Report saved to: 70-LOGS/operations/batch-2026-02-16T103500.md
```

#### Step 3: Review Ambiguous File
```bash
Command: /filesystem-organize --review notes.md

Expected Output:
┌─────────────────────────────────────────────────┐
│ Manual Review Required: notes.md                │
├─────────────────────────────────────────────────┤
│ Content Preview:                                │
│ - Buy groceries                                 │
│ - Call dentist                                  │
│ - Finish report                                 │
│                                                 │
│ Classification Options:                         │
│ 1. Episodic Memory (daily notes)               │
│    → 80-MEMORY/episodic/EP-YYYYMMDD-notes.md   │
│                                                 │
│ 2. Task List                                    │
│    → 20-PROCESSES/tasks/TASK-001-personal.md   │
│                                                 │
│ 3. Delete (not relevant to vault)              │
│    → Requires Tier 3 approval                   │
│                                                 │
│ Your choice (1/2/3):                            │
└─────────────────────────────────────────────────┘

Human Input: 2

[HITL] Logging decision...
  ✓ Decision logged: 70-LOGS/hitl/completed/
  ✓ Moving to: 20-PROCESSES/tasks/TASK-001-personal.md
  ✓ Duration: 35ms

✅ File organized based on your decision
```

### Verification

#### Check 1: Batch Report
```bash
Command: cat obsidian-vault/70-LOGS/operations/batch-2026-02-16T103500.md

Expected:
# Batch Organization Report
Date: 2026-02-16T10:35:00Z
Duration: 121ms

## Summary
- Processed: 3 files
- Success: 3 files (100%)
- Failed: 0 files
- Skipped: 1 file (manual review required)

## Files Organized
1. agent_Sales.MD → 10-KNOWLEDGE/agents/003-sales-agent.md (42ms)
2. workflow_email_automation.txt → 20-PROCESSES/workflows/WF-004-email-automation.md (38ms)
3. analysis.md → 50-BUSINESS/analytics/AN-001-customer-data-analysis.md (41ms)

## Vault Health Improvement
Before: 4 files misplaced (100%)
After: 0 files misplaced (0%)
Compliance: 96.5% → 100%
```

#### Check 2: Verify All Files
```bash
# Check each file exists in correct location
ls -1 obsidian-vault/10-KNOWLEDGE/agents/003-sales-agent.md
ls -1 obsidian-vault/20-PROCESSES/workflows/WF-004-email-automation.md
ls -1 obsidian-vault/50-BUSINESS/analytics/AN-001-customer-data-analysis.md
ls -1 obsidian-vault/20-PROCESSES/tasks/TASK-001-personal.md

Expected: All files found ✓
```

### Success Criteria
- [x] 3 files auto-organized (Tier 1)
- [x] 1 file escalated to HITL (ambiguous)
- [x] All files in correct locations
- [x] Batch report generated
- [x] Vault compliance improved
- [x] No errors

---

## Demo 3: Proactive Monitoring

### Objective
Demonstrate real-time file validation as files are created.

### Scenario
File watcher detects new file and validates it immediately.

### Setup
```yaml
Monitoring Mode:
  Enabled: true
  Watch Directory: obsidian-vault/
  Check Interval: 1 second
  Auto-fix: Tier 1 only
```

### Execution Steps

#### Step 1: Start Monitoring
```bash
Command: /filesystem-watch --start

Expected Output:
[WATCHER] Starting filesystem monitor...
  ✓ Watching: obsidian-vault/
  ✓ Check interval: 1 second
  ✓ Auto-fix: Tier 1 enabled
  ✓ Status: Active

[WATCHER] Ready. Monitoring for new/modified files...
Press Ctrl+C to stop.
```

#### Step 2: Create File (Human Action)
```bash
# Human creates file with issues
echo "# Test Content" > obsidian-vault/test.md
```

#### Step 3: Watch Detection
```bash
Expected Output:
[WATCHER] New file detected: test.md
[WATCHER] Running validation...

Issues found:
  ❌ Name: Missing sequence number (NNN-)
  ❌ Name: Too generic ("test")
  ❌ Metadata: Missing frontmatter

Suggested fix:
  Location: 10-KNOWLEDGE/ (based on location)
  Name: 004-test.md
  Action: Add frontmatter

Auto-fix available? Yes (Tier 1)
Apply auto-fix? (y/n):
```

#### Step 4: Apply Fix
```bash
Human Input: y

[WATCHER] Applying auto-fix...
  ✓ Renamed: test.md → 004-test.md
  ✓ Added frontmatter
  ✓ Duration: 28ms

[WATCHER] File now compliant. Continuing monitoring...
```

### Success Criteria
- [x] Watcher detects new file immediately
- [x] Issues identified correctly
- [x] Auto-fix suggested
- [x] Human approval obtained
- [x] Fix applied successfully
- [x] Monitoring continues

---

## Demo 4: Error Recovery

### Objective
Demonstrate rollback when operation fails.

### Scenario
Simulate failure during file move and verify rollback works.

### Setup
```yaml
Test Scenario:
  File: "test-error.md"
  Simulate: Permission denied during move
  Expected: Rollback to original state
```

### Execution Steps

#### Step 1: Create Test File
```bash
echo "# Test Error Recovery" > obsidian-vault/test-error.md
```

#### Step 2: Simulate Failure
```bash
Command: /filesystem-organize --execute --simulate-error permission_denied test-error.md

Expected Output:
[2026-02-16T11:00:00Z] INFO: Starting organization operation
[2026-02-16T11:00:00Z] INFO: Pre-flight checks passed
[2026-02-16T11:00:00Z] INFO: Creating backup...
  ✓ Backup: .backups/test-error-20260216T110000.md

[2026-02-16T11:00:00Z] INFO: Moving file...
[2026-02-16T11:00:00Z] ERROR: Move operation failed
  Error: PermissionError: Permission denied
  File: test-error.md
  Target: 10-KNOWLEDGE/004-test-error.md

[2026-02-16T11:00:00Z] WARN: Initiating rollback...
  ✓ Restored from backup
  ✓ Original file intact at: obsidian-vault/test-error.md
  ✓ Backup preserved for investigation

[2026-02-16T11:00:00Z] ERROR: Operation failed but rolled back successfully
  Status: Original state restored
  Backup: .backups/test-error-20260216T110000.md
  Log: 70-LOGS/errors/2026-02-16.md

❌ OPERATION FAILED (but data preserved)
  Error logged for investigation
  File remains at original location
  No data loss
```

#### Step 3: Verify Rollback
```bash
# Check original file still exists
cat obsidian-vault/test-error.md

Expected:
# Test Error Recovery
```

#### Step 4: Check Error Log
```bash
Command: cat obsidian-vault/70-LOGS/errors/2026-02-16.md

Expected Entry:
[2026-02-16T11:00:00Z] ERROR: FILESYSTEM_AUTOMATION
  Operation: organize
  File: test-error.md
  Target: 10-KNOWLEDGE/004-test-error.md
  Error: PermissionError (Permission denied)
  Rollback: Success
  Status: Failed (data preserved)
  Backup: .backups/test-error-20260216T110000.md

  Action Required:
  - Investigate permission issue
  - Verify file system permissions
  - Retry when resolved
```

### Success Criteria
- [x] Error detected during operation
- [x] Rollback initiated automatically
- [x] Original file preserved
- [x] Backup retained
- [x] Error logged comprehensively
- [x] No data loss

---

## Demo 5: Health Check Report

### Objective
Generate comprehensive vault health report.

### Execution Steps

#### Step 1: Run Health Check
```bash
Command: /filesystem-health-check --comprehensive

Expected Output:
[HEALTH CHECK] Scanning vault...

Analyzing vault structure... ✓
Checking naming conventions... ✓
Validating metadata... ✓
Checking for broken links... ✓
Identifying orphaned files... ✓

Generating report...
```

#### Step 2: View Report
```bash
Expected Output:
┌─────────────────────────────────────────────────┐
│ Vault Health Report                             │
│ Date: 2026-02-16T11:30:00Z                      │
├─────────────────────────────────────────────────┤
│ Overall Health: 97.5% ✓                         │
│                                                 │
│ File Statistics:                                │
│   Total Files: 120                              │
│   Compliant: 117 (97.5%)                        │
│   Issues: 3 (2.5%)                              │
│                                                 │
│ Convention Compliance:                          │
│   ✓ Naming: 118/120 (98.3%)                     │
│   ✓ Location: 120/120 (100%)                    │
│   ✓ Metadata: 115/120 (95.8%)                   │
│   ✓ Tags: 110/120 (91.7%)                       │
│                                                 │
│ Issues Detected:                                │
│   1. Missing frontmatter (2 files)              │
│      - 10-KNOWLEDGE/old-note.md                 │
│      - 80-MEMORY/episodic/draft.md              │
│                                                 │
│   2. Naming violation (1 file)                  │
│      - 50-BUSINESS/report.md (missing ID)       │
│                                                 │
│ Recommendations:                                │
│   • Run auto-fix for 3 issues (Tier 1)         │
│   • Add tags to 10 under-tagged files           │
│   • Consider archiving 5 old files (6mo+)      │
│                                                 │
│ Vault Growth:                                   │
│   Files added this week: 8                      │
│   Average file age: 45 days                     │
│   Most active section: 10-KNOWLEDGE (35 files)  │
│                                                 │
│ Full report: 70-LOGS/health-checks/2026-02-16.md│
└─────────────────────────────────────────────────┘

Run auto-fix for detected issues? (y/n):
```

### Success Criteria
- [x] Comprehensive scan completed
- [x] Statistics accurate
- [x] Issues identified correctly
- [x] Recommendations actionable
- [x] Report saved to logs

---

## Summary of Demos

### Completed Demonstrations
1. ✅ Single File Organization - Basic organize, rename, metadata
2. ✅ Batch Organization - Multiple files, HITL for ambiguous
3. ✅ Proactive Monitoring - Real-time validation
4. ✅ Error Recovery - Rollback on failure
5. ✅ Health Check Report - Vault analysis

### Key Capabilities Demonstrated
- [x] File organization and renaming
- [x] Content classification
- [x] Metadata enrichment
- [x] Tier 1 auto-approval
- [x] HITL escalation
- [x] Comprehensive logging
- [x] Error handling and rollback
- [x] Batch processing
- [x] Real-time monitoring
- [x] Health reporting

### Constitution Compliance Verified
- [x] Local-first (all state in vault)
- [x] Explicit (all actions logged)
- [x] HITL by default (Tier 1 only)
- [x] Composable (standalone skill)
- [x] Memory building (logs create knowledge)
- [x] Fail safe (rollback works)

---

## Next Steps

1. **Implement Phase 1**: Core functions (Week 1)
2. **Run Test Plan**: Execute comprehensive test suite
3. **Iterate**: Fix issues, optimize performance
4. **Deploy**: Bronze Tier production deployment

---

**Demo Completion Checklist**:
- [ ] All 5 demos executed successfully
- [ ] No critical errors
- [ ] Performance within targets (<100ms per file)
- [ ] Constitution compliance verified
- [ ] Human operator trained
- [ ] Ready for Bronze Tier deployment

**Ready for Production**: ⏳ Pending demo execution
