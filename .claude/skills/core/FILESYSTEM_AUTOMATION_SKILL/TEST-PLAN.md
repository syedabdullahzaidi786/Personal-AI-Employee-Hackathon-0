# FILESYSTEM_AUTOMATION_SKILL - Test Plan

**Version**: 1.0.0
**Date**: 2026-02-16
**Owner**: QA Team
**Test Environment**: Isolated test vault
**Estimated Duration**: 8-16 hours

---

## Test Strategy

### Testing Approach
- **Bottom-Up**: Unit tests → Integration tests → System tests
- **Risk-Based**: Focus on safety-critical operations first
- **Automated**: 80% automated, 20% manual verification
- **Continuous**: CI/CD integration for regression testing

### Test Levels
1. **Unit Tests**: Individual functions (80% coverage minimum)
2. **Integration Tests**: Component interactions
3. **System Tests**: End-to-end workflows
4. **Acceptance Tests**: Real-world scenarios
5. **Performance Tests**: Speed and resource usage
6. **Security Tests**: Boundary enforcement and safety

---

## Test Environment Setup

### Prerequisites
```yaml
Environment:
  OS: Windows 10+, macOS 10.15+, or Linux
  Python: 3.9+
  Obsidian: Latest stable
  Git: For version control

Test Vault Structure:
  Location: ./test-vault/
  Structure: Mirrors obsidian-vault/
  Data: 100 test files (various formats)
  Isolation: Completely separate from production

Dependencies:
  - pytest: Test framework
  - pytest-cov: Coverage reporting
  - mock: Mocking file operations
  - watchdog: File system monitoring
```

### Setup Script
```bash
#!/bin/bash
# setup-test-environment.sh

# Create test vault
mkdir -p test-vault
cd test-vault

# Create folder structure
mkdir -p {00-INDEX,10-KNOWLEDGE/{agents,domains},20-PROCESSES/{workflows,hitl}}
mkdir -p {30-INTEGRATIONS/{mcp-servers,apis},40-SECURITY/policies}
mkdir -p {50-BUSINESS/{analytics,rules},60-PROMPTS/templates}
mkdir -p {70-LOGS/{daily,errors,warnings},80-MEMORY/{episodic,semantic}}
mkdir -p {90-TEMPLATES,.backups}

# Create test files
echo "# Test Agent" > "test_agent.md"
echo "# Meeting" > "meeting notes.txt"
echo "# Workflow" > "WF_001_test.MD"
echo "# Analysis" > "analysis data.md"

# Copy constitution and naming conventions
cp ../constitution.md .
cp ../NAMING-CONVENTIONS.md .

echo "✓ Test environment ready"
```

---

## Unit Tests

### UT-001: Path Validation
```python
"""Test vault boundary enforcement"""

def test_path_within_vault():
    """Valid paths inside vault should pass"""
    assert validate_path("test-vault/10-KNOWLEDGE/test.md") == True

def test_path_outside_vault():
    """Paths outside vault should be rejected"""
    with pytest.raises(SecurityError):
        validate_path("/etc/passwd")

def test_path_with_traversal():
    """Path traversal attempts should be rejected"""
    with pytest.raises(SecurityError):
        validate_path("test-vault/../../../etc/passwd")

def test_symlink_escape():
    """Symlinks pointing outside vault should be rejected"""
    os.symlink("/tmp", "test-vault/escape")
    with pytest.raises(SecurityError):
        validate_path("test-vault/escape/file.md")

def test_forbidden_paths():
    """Blacklisted paths should be rejected"""
    forbidden = [".git/", ".obsidian/", ".claude/", ".specify/"]
    for path in forbidden:
        with pytest.raises(SecurityError):
            validate_path(f"test-vault/{path}config")

# Expected: All tests pass
# Coverage: Path validation logic
```

### UT-002: Naming Convention Parser
```python
"""Test naming convention validation and parsing"""

def test_valid_convention():
    """Files following convention should validate"""
    valid_names = [
        "001-test-file.md",
        "WF-042-workflow-name.md",
        "MCP-023-github-integration.md",
        "EP-20260216-meeting-notes.md"
    ]
    for name in valid_names:
        assert is_valid_name(name) == True

def test_invalid_convention():
    """Files violating convention should fail"""
    invalid_names = [
        "test.md",  # Missing ID
        "Test File.md",  # Spaces
        "001_test.md",  # Underscore
        "001-Test.md",  # Uppercase
        "001-test.MD"  # Wrong extension
    ]
    for name in invalid_names:
        assert is_valid_name(name) == False

def test_extract_id():
    """ID extraction should work correctly"""
    assert extract_id("001-test.md") == 1
    assert extract_id("WF-042-name.md") == 42
    assert extract_id("no-id.md") == None

def test_suggest_fix():
    """Convention fix suggestions should be correct"""
    assert suggest_fix("Test File.md") == "001-test-file.md"
    assert suggest_fix("001_test.MD") == "001-test.md"

# Expected: All tests pass
# Coverage: Naming convention logic
```

### UT-003: File Classification
```python
"""Test content analysis and classification"""

def test_classify_agent_profile():
    """Agent profiles should be classified correctly"""
    content = "# Agent Profile\n\n## Purpose\nCustomer service..."
    classification = classify_file(content)
    assert classification.type == "agent-profile"
    assert classification.target_folder == "10-KNOWLEDGE/agents/"
    assert classification.confidence > 0.9

def test_classify_workflow():
    """Workflows should be classified correctly"""
    content = "# Workflow\n\n## Steps\n1. First\n2. Second..."
    classification = classify_file(content)
    assert classification.type == "workflow"
    assert classification.target_folder == "20-PROCESSES/workflows/"

def test_classify_episodic_memory():
    """Meeting notes should be classified as episodic"""
    content = "# Meeting\nDate: 2026-02-16\nAttendees: Alice, Bob"
    classification = classify_file(content)
    assert classification.type == "episodic-memory"
    assert classification.target_folder == "80-MEMORY/episodic/"
    assert "2026-02-16" in classification.suggested_name

def test_classify_ambiguous():
    """Ambiguous files should request human input"""
    content = "- Task 1\n- Task 2\n- Task 3"
    classification = classify_file(content)
    assert classification.confidence < 0.7
    assert classification.requires_hitl == True

# Expected: All tests pass
# Coverage: Content classification
```

### UT-004: Frontmatter Generation
```python
"""Test metadata generation"""

def test_generate_frontmatter():
    """Frontmatter should have required fields"""
    fm = generate_frontmatter(
        file_name="001-test.md",
        file_type="knowledge",
        tags=["test", "demo"]
    )

    assert "id" in fm
    assert "created" in fm
    assert "updated" in fm
    assert "tags" in fm
    assert fm["tags"] == ["test", "demo"]

def test_frontmatter_yaml_valid():
    """Generated frontmatter should be valid YAML"""
    fm = generate_frontmatter("test.md", "knowledge", [])
    yaml_str = yaml.dump(fm)
    parsed = yaml.safe_load(yaml_str)
    assert parsed == fm

def test_update_existing_frontmatter():
    """Updating frontmatter should preserve other fields"""
    existing = {
        "id": "test",
        "created": "2026-01-01",
        "custom": "value"
    }
    updated = update_frontmatter(existing, tags=["new"])
    assert updated["id"] == "test"
    assert updated["created"] == "2026-01-01"
    assert updated["custom"] == "value"
    assert updated["tags"] == ["new"]

# Expected: All tests pass
# Coverage: Metadata generation
```

### UT-005: Safe File Operations
```python
"""Test atomic file operations"""

def test_rename_atomic():
    """Rename should be atomic (no partial states)"""
    create_test_file("test.md", "content")
    rename_file_safely("test.md", "renamed.md")

    assert not os.path.exists("test.md")
    assert os.path.exists("renamed.md")
    assert read_file("renamed.md") == "content"

def test_rename_with_backup():
    """Backup should be created before rename"""
    create_test_file("test.md", "important")

    # Simulate failure after backup
    with mock.patch('os.rename', side_effect=OSError):
        with pytest.raises(OSError):
            rename_file_safely("test.md", "new.md")

    # Original should still exist
    assert os.path.exists("test.md")
    assert read_file("test.md") == "important"

def test_content_integrity():
    """Content should be unchanged after move"""
    content = "Test content " * 1000
    create_test_file("test.md", content)
    checksum_before = hash_file("test.md")

    move_file("test.md", "subfolder/test.md")
    checksum_after = hash_file("subfolder/test.md")

    assert checksum_before == checksum_after

# Expected: All tests pass
# Coverage: File operations safety
```

---

## Integration Tests

### IT-001: End-to-End Organization
```python
"""Test complete organization workflow"""

def test_organize_single_file():
    """Complete workflow for one file"""
    # Setup
    create_test_file("Meeting Notes.md", "# Meeting\nDate: 2026-02-16")

    # Execute
    result = organize_file("Meeting Notes.md", auto_approve=True)

    # Verify
    assert result.success == True
    expected_path = "80-MEMORY/episodic/EP-20260216-meeting-notes.md"
    assert os.path.exists(expected_path)

    # Check frontmatter
    content = read_file(expected_path)
    assert "---" in content
    assert "id: EP-20260216-meeting-notes" in content

    # Check logging
    assert log_exists("daily/2026-02-16.md")
    assert "Meeting Notes.md" in read_log("daily/2026-02-16.md")

# Expected: Pass
# Duration: ~100ms
```

### IT-002: Batch Processing
```python
"""Test batch organization of multiple files"""

def test_batch_organize():
    """Organize 10 files in batch"""
    # Setup
    files = create_test_files(10, with_issues=True)

    # Execute
    results = organize_batch(files, tier=1, auto_approve=True)

    # Verify
    assert results.total == 10
    assert results.success >= 8  # Allow 2 to need HITL
    assert results.failed == 0

    # Check report
    report = read_file("70-LOGS/operations/batch-*.md")
    assert "Processed: 10" in report
    assert "Duration:" in report

# Expected: Pass
# Duration: ~1 second
```

### IT-003: HITL Integration
```python
"""Test human-in-the-loop workflow"""

def test_hitl_approval_required():
    """Ambiguous files should trigger HITL"""
    # Setup
    create_test_file("ambiguous.md", "Some unclear content")

    # Execute
    with mock.patch('request_approval') as mock_approval:
        mock_approval.return_value = {
            "approved": True,
            "target": "10-KNOWLEDGE/004-ambiguous.md"
        }
        result = organize_file("ambiguous.md")

    # Verify HITL was called
    mock_approval.assert_called_once()
    assert result.hitl_required == True
    assert result.success == True

def test_hitl_approval_denied():
    """Denied approvals should be logged"""
    create_test_file("test.md", "content")

    with mock.patch('request_approval', return_value={"approved": False}):
        result = organize_file("test.md")

    assert result.success == False
    assert result.hitl_denied == True
    # File should remain in original location
    assert os.path.exists("test.md")

# Expected: Pass
```

### IT-004: Error Handling and Rollback
```python
"""Test error recovery mechanisms"""

def test_rollback_on_failure():
    """Failed operations should rollback"""
    # Setup
    create_test_file("test.md", "important data")
    original_content = read_file("test.md")

    # Simulate failure during move
    with mock.patch('os.rename', side_effect=PermissionError):
        with pytest.raises(PermissionError):
            organize_file("test.md")

    # Verify rollback
    assert os.exists("test.md")  # Original still exists
    assert read_file("test.md") == original_content

    # Check error log
    assert "PermissionError" in read_log("errors/2026-02-16.md")

def test_circuit_breaker():
    """Circuit breaker should open after threshold"""
    # Cause 3 consecutive failures
    for i in range(3):
        with mock.patch('os.rename', side_effect=OSError):
            try:
                organize_file(f"test{i}.md")
            except CircuitBreakerOpen:
                pass

    # 4th attempt should be rejected immediately
    with pytest.raises(CircuitBreakerOpen):
        organize_file("test4.md")

    # Verify circuit is open
    assert get_circuit_state() == "OPEN"

# Expected: Pass
```

---

## System Tests

### ST-001: Real Vault Cleanup
```yaml
Test: Weekly vault cleanup scenario
Files: 50 test files with various issues
Duration: 30 minutes

Steps:
  1. Create messy test vault (50 files)
  2. Run: /organize-vault --batch --auto-fix tier-1
  3. Verify all Tier 1 issues fixed
  4. Verify HITL requests for ambiguous files
  5. Check vault health improves
  6. Verify all operations logged

Success Criteria:
  - 90%+ of issues auto-fixed
  - 0 data loss
  - All operations logged
  - Vault compliance > 95%
  - Completion time < 5 seconds
```

### ST-002: Continuous Monitoring
```yaml
Test: 24-hour monitoring test
Duration: 24 hours (automated)

Steps:
  1. Start file watcher
  2. Simulate human activity (create 100 files randomly)
  3. Verify each detected and validated
  4. Check auto-fixes applied where appropriate
  5. Verify no false positives

Success Criteria:
  - 100% detection rate
  - Auto-fix accuracy > 95%
  - No crashes or hangs
  - Memory usage < 100MB
  - CPU usage < 5% average
```

### ST-003: Stress Test
```yaml
Test: Large vault processing
Files: 10,000 files
Duration: 1 hour

Steps:
  1. Create vault with 10,000 files
  2. Run batch organization
  3. Monitor performance
  4. Verify all processed
  5. Check for memory leaks

Success Criteria:
  - Process all 10,000 files
  - Average time < 50ms per file
  - Total time < 10 minutes
  - Memory usage < 500MB
  - No crashes or hangs
  - 0 data loss
```

---

## Acceptance Tests

### AT-001: User Workflow Scenario
```yaml
Test: New team member onboarding
Persona: Junior developer, first time using skill
Duration: 1 hour

Scenario:
  User receives vault with 20 misorganized files.
  They need to clean it up using the skill.

Steps:
  1. User reads README and DEMO-WORKFLOW
  2. User runs health check
  3. User reviews issues found
  4. User runs auto-fix with dry-run
  5. User approves and runs real fix
  6. User verifies results
  7. User reviews audit logs

Success Criteria:
  - User completes task in < 1 hour
  - User understands what skill does
  - User feels confident using skill
  - All files organized correctly
  - User can find audit trail
  - User satisfaction rating: 4+/5
```

### AT-002: Production Readiness
```yaml
Test: Bronze Tier deployment simulation
Environment: Production-like
Duration: 1 week

Steps:
  1. Deploy to staging environment
  2. Process real (anonymized) data
  3. Monitor for 1 week
  4. Collect metrics
  5. Review incidents
  6. User feedback

Success Criteria:
  - Uptime > 99.9%
  - Error rate < 0.1%
  - Performance within targets
  - 0 critical incidents
  - 0 data loss
  - Constitution compliance: 100%
  - User satisfaction: 4.5+/5
```

---

## Performance Tests

### PT-001: Single File Performance
```yaml
Test: Measure single file operation speed
Iterations: 1000

Metrics:
  - P50 (median): < 50ms
  - P95: < 100ms
  - P99: < 200ms
  - Max: < 500ms

Test Cases:
  - Small file (< 1KB)
  - Medium file (10KB)
  - Large file (100KB)
  - With/without classification
  - With/without frontmatter addition
```

### PT-002: Batch Performance
```yaml
Test: Measure batch operation scaling
Scenarios:
  - 10 files
  - 100 files
  - 1000 files
  - 10000 files

Metrics:
  - Linear scaling: Time should scale linearly
  - Memory: Should not grow beyond 500MB
  - CPU: Should utilize available cores
  - Throughput: > 20 files/second
```

### PT-003: Memory Profiling
```yaml
Test: Detect memory leaks
Duration: 4 hours continuous operation

Metrics:
  - Initial memory: Baseline
  - After 1 hour: < 120% of baseline
  - After 2 hours: < 125% of baseline
  - After 4 hours: < 130% of baseline
  - No memory leaks detected
```

---

## Security Tests

### SEC-001: Boundary Enforcement
```yaml
Test: Attempt to escape vault boundaries
Attempts: 50 different techniques

Test Cases:
  - Absolute paths (/etc/passwd)
  - Relative traversal (../../)
  - Symlinks pointing outside
  - Unicode tricks
  - Null bytes
  - Path normalization bypass

Success Criteria:
  - All attempts blocked
  - All attempts logged as CRITICAL
  - No data accessed outside vault
  - No crashes or exceptions
```

### SEC-002: Permission Testing
```yaml
Test: Verify file permissions respected
Scenarios:
  - Read-only files
  - Write-protected folders
  - Permission denied scenarios

Success Criteria:
  - Permissions respected
  - Graceful error handling
  - No permission escalation
  - User notified appropriately
```

### SEC-003: Malicious Content
```yaml
Test: Handle malicious file content safely
Test Cases:
  - Very long filenames (> 255 chars)
  - Binary data in .md files
  - Malformed YAML frontmatter
  - Script injection attempts
  - Path injection in content

Success Criteria:
  - No code execution
  - No crashes
  - All attempts logged
  - Safe fallback behavior
```

---

## Test Data Sets

### Dataset 1: Clean Files
```yaml
Purpose: Baseline testing
Count: 20 files
Characteristics:
  - All follow naming conventions
  - All have frontmatter
  - All in correct locations

Expected: No changes needed
```

### Dataset 2: Messy Files
```yaml
Purpose: Organization testing
Count: 50 files
Issues:
  - Wrong names: 20 files
  - Wrong locations: 15 files
  - Missing frontmatter: 30 files
  - Wrong extensions: 10 files

Expected: All issues auto-fixed (Tier 1)
```

### Dataset 3: Ambiguous Files
```yaml
Purpose: HITL testing
Count: 10 files
Characteristics:
  - Unclear classification
  - Requires human decision
  - Multiple valid destinations

Expected: HITL requests generated
```

### Dataset 4: Edge Cases
```yaml
Purpose: Robustness testing
Count: 30 files
Cases:
  - Empty files
  - Binary files (.png, .pdf)
  - Very large files (> 10MB)
  - Special characters in names
  - Unicode filenames
  - Duplicate names

Expected: Graceful handling, no crashes
```

---

## Test Execution Schedule

### Phase 1: Unit Tests (Day 1)
```yaml
Duration: 4 hours
Tests: 50+ unit tests
Target Coverage: 80%

Checklist:
  - [ ] Path validation (UT-001)
  - [ ] Naming conventions (UT-002)
  - [ ] Classification (UT-003)
  - [ ] Frontmatter (UT-004)
  - [ ] File operations (UT-005)
  - [ ] Coverage report generated
```

### Phase 2: Integration Tests (Day 2)
```yaml
Duration: 4 hours
Tests: 20+ integration tests

Checklist:
  - [ ] End-to-end organization (IT-001)
  - [ ] Batch processing (IT-002)
  - [ ] HITL integration (IT-003)
  - [ ] Error recovery (IT-004)
  - [ ] Component interactions verified
```

### Phase 3: System Tests (Days 3-4)
```yaml
Duration: 2 days
Tests: Real vault scenarios

Checklist:
  - [ ] Vault cleanup (ST-001)
  - [ ] Continuous monitoring (ST-002)
  - [ ] Stress test (ST-003)
  - [ ] Performance profiling
```

### Phase 4: Acceptance Tests (Days 5-7)
```yaml
Duration: 3 days
Tests: User scenarios

Checklist:
  - [ ] User workflow (AT-001)
  - [ ] Production readiness (AT-002)
  - [ ] User feedback collected
  - [ ] Documentation validated
```

---

## Bug Tracking

### Bug Report Template
```yaml
Bug ID: BUG-{NNN}
Title: [Brief description]
Severity: Critical | High | Medium | Low
Priority: P0 | P1 | P2 | P3

Description:
  [Detailed description of bug]

Steps to Reproduce:
  1. [Step 1]
  2. [Step 2]
  ...

Expected Behavior:
  [What should happen]

Actual Behavior:
  [What actually happens]

Environment:
  - OS: [Windows/Mac/Linux]
  - Python: [Version]
  - Skill Version: [Version]

Logs:
  [Attach relevant logs]

Impact:
  [Who/what is affected]

Fix Priority:
  [When should this be fixed]
```

### Critical Bug Criteria
```yaml
Immediate Fix Required:
  - Data loss
  - Security breach
  - Operations outside vault boundary
  - Constitution violation
  - Complete skill failure

Acceptable Workaround:
  - Can be manually fixed
  - Doesn't block testing
  - Documented in known issues
```

---

## Test Metrics & Reporting

### Required Metrics
```yaml
Coverage Metrics:
  - Code coverage: > 80%
  - Branch coverage: > 75%
  - Function coverage: > 90%

Quality Metrics:
  - Tests passed: 100%
  - Critical bugs: 0
  - High bugs: < 3
  - Medium bugs: < 10

Performance Metrics:
  - Single file: < 100ms (P95)
  - Batch (10): < 1s
  - Batch (100): < 10s
  - Memory: < 500MB

Safety Metrics:
  - Data loss incidents: 0
  - Security violations: 0
  - Rollback success rate: 100%
  - Constitution compliance: 100%
```

### Test Report Template
```markdown
# Test Execution Report
Date: YYYY-MM-DD
Version: X.Y.Z
Tester: [Name]

## Summary
- Total Tests: [count]
- Passed: [count] ([percentage]%)
- Failed: [count] ([percentage]%)
- Skipped: [count]
- Duration: [time]

## Coverage
- Line Coverage: [percentage]%
- Branch Coverage: [percentage]%
- Function Coverage: [percentage]%

## Performance
- Average File Time: [ms]
- Batch Processing (100 files): [seconds]
- Memory Usage: [MB]

## Issues Found
### Critical (P0)
[List of critical issues]

### High (P1)
[List of high priority issues]

### Medium (P2)
[List of medium priority issues]

## Constitution Compliance
- [ ] Local-First Sovereignty
- [ ] Explicit Over Implicit
- [ ] HITL by Default
- [ ] Composability
- [ ] Memory as Knowledge
- [ ] Fail Safe, Fail Visible

## Recommendations
[Recommendations for improvement]

## Sign-Off
- [ ] All critical issues resolved
- [ ] Performance within targets
- [ ] Security tests passed
- [ ] Ready for deployment

Tester: ________________
Date: __________________
```

---

## Acceptance Criteria

### Bronze Tier Readiness
```yaml
Required for Deployment:
  - [ ] All unit tests pass (100%)
  - [ ] All integration tests pass (100%)
  - [ ] System tests complete (3/3)
  - [ ] At least 1 acceptance test pass
  - [ ] Performance within targets
  - [ ] Security tests pass (100%)
  - [ ] Code coverage > 80%
  - [ ] 0 critical bugs
  - [ ] < 3 high priority bugs
  - [ ] Documentation complete
  - [ ] Demo workflow executable
  - [ ] Constitution compliance verified
  - [ ] User training completed
```

### Sign-Off Checklist
```yaml
Technical Sign-Off:
  - [ ] Developer: Tests pass, code reviewed
  - [ ] QA: Test plan executed, issues documented
  - [ ] Security: Security tests pass, no vulnerabilities
  - [ ] Performance: Meets all performance targets

Governance Sign-Off:
  - [ ] Architect: Follows constitution, design approved
  - [ ] Human Operator: Comfortable using skill, trained
  - [ ] Product: Meets requirements, ready for users

Final Approval:
  - [ ] All sign-offs obtained
  - [ ] Deployment plan ready
  - [ ] Rollback plan documented
  - [ ] Monitoring configured
  - [ ] Ready for Bronze Tier deployment
```

---

**Test Plan Version**: 1.0.0
**Status**: Ready for Execution
**Next Step**: Execute Phase 1 (Unit Tests)
