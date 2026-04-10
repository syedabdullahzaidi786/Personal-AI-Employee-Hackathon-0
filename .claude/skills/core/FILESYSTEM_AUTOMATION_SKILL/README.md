# FILESYSTEM_AUTOMATION_SKILL - Quick Reference

**Status**: ✅ Specification Complete - Ready for Implementation
**Version**: 1.0.0
**Category**: Core Skill
**Tier**: 1 (Low-risk writes)

---

## 📚 Documentation Index

| Document | Purpose | Read Time |
|----------|---------|-----------|
| **[SKILL.md](./SKILL.md)** | Complete specification (14 sections) | 45 min |
| **[DEMO-WORKFLOW.md](./DEMO-WORKFLOW.md)** | 5 practical demos with examples | 30 min |
| **[TEST-PLAN.md](./TEST-PLAN.md)** | Comprehensive test strategy | 30 min |
| **[README.md](./README.md)** | This quick reference | 5 min |

---

## 🎯 What This Skill Does

### Core Functions
- **Organizes**: Moves files to correct vault sections based on content and naming patterns
- **Renames**: Enforces naming conventions (IDs, lowercase, hyphens)
- **Classifies**: Analyzes content to determine file type and destination
- **Validates**: Pre-flight and post-operation safety checks
- **Audits**: Generates reports on vault health and compliance

### Example
```
Before: vault/Meeting Notes.md (root, wrong name, no metadata)
After:  vault/80-MEMORY/episodic/EP-20260216-meeting-notes.md
        (organized, renamed, frontmatter added, logged)
```

---

## ⚡ Quick Start

### 1. Read the Specification
```bash
# Read core specification
open SKILL.md

Key sections:
  - Section 1: Purpose (what it does)
  - Section 2: Capabilities (features)
  - Section 9: Demo Scenario (walkthrough)
```

### 2. Run Demo Workflow
```bash
# Follow step-by-step demo
open DEMO-WORKFLOW.md

5 Demos:
  1. Single File Organization (basic)
  2. Batch Organization (multiple files)
  3. Proactive Monitoring (real-time)
  4. Error Recovery (rollback)
  5. Health Check Report (audit)
```

### 3. Execute Tests
```bash
# Follow test plan
open TEST-PLAN.md

Test phases:
  - Unit Tests (Day 1)
  - Integration Tests (Day 2)
  - System Tests (Days 3-4)
  - Acceptance Tests (Days 5-7)
```

---

## 📋 Implementation Checklist

### Phase 1: Core Functions (Week 1)
- [ ] File validation engine
- [ ] Naming convention parser
- [ ] Safe rename function
- [ ] Safe move function
- [ ] Logging system integration
- [ ] Unit tests (80% coverage)

### Phase 2: Analysis & Classification (Week 2)
- [ ] Content analyzer
- [ ] Folder detection logic
- [ ] ID assignment system
- [ ] Frontmatter generator
- [ ] Tag suggestion engine
- [ ] Integration tests

### Phase 3: Batch Operations (Week 3)
- [ ] Vault scanner
- [ ] Batch processor
- [ ] Progress reporting
- [ ] HITL integration
- [ ] Report generator
- [ ] End-to-end tests

### Phase 4: Monitoring & Polish (Week 4)
- [ ] File watcher integration
- [ ] Proactive validation
- [ ] Health check dashboard
- [ ] Performance optimization
- [ ] Documentation finalization
- [ ] User acceptance testing

---

## 🔐 Safety & Constitution

### What Makes It Safe
✅ **Vault Boundary**: Never operates outside `obsidian-vault/`
✅ **Atomic Operations**: All file ops are atomic with backups
✅ **Rollback**: Failed operations restore to original state
✅ **Logging**: Every action logged with full context
✅ **HITL**: Tier 1 only (low-risk, auto-approve)
✅ **No Deletion**: Cannot delete files (Tier 3 only)
✅ **Content Preservation**: Never modifies file content
✅ **Circuit Breaker**: Stops after 3 consecutive errors

### Constitution Compliance
- [x] **Principle I**: Local-First (all state in vault)
- [x] **Principle II**: Explicit (all actions logged)
- [x] **Principle III**: HITL by Default (Tier 1 scoped)
- [x] **Principle IV**: Composable (standalone skill)
- [x] **Principle V**: Memory Building (learns from ops)
- [x] **Principle VI**: Fail Safe (rollback works)

---

## 📊 Success Metrics

### Performance Targets
| Operation | Target | Critical |
|-----------|--------|----------|
| Single File | < 100ms | < 500ms |
| Batch (10) | < 1s | < 5s |
| Batch (100) | < 10s | < 30s |
| Memory | < 50MB | < 200MB |

### Quality Targets
| Metric | Target | Critical |
|--------|--------|----------|
| Accuracy | > 95% | > 85% |
| Reliability | > 99.9% | > 99% |
| Data Loss | 0 | 0 |
| Constitution | 100% | 100% |

---

## 🛠️ Common Commands

### Development
```bash
# Set up test environment
./setup-test-environment.sh

# Run unit tests
pytest tests/unit/ -v --cov

# Run integration tests
pytest tests/integration/ -v

# Run all tests with coverage
pytest tests/ -v --cov --cov-report=html
```

### Usage (After Implementation)
```bash
# Scan for issues
/filesystem-organize --scan

# Organize single file
/filesystem-organize --execute "filename.md"

# Organize batch (dry run first)
/filesystem-organize --batch --dry-run

# Organize batch (real)
/filesystem-organize --batch --execute --tier 1

# Generate health report
/filesystem-health-check --comprehensive

# Start file watcher
/filesystem-watch --start
```

---

## 🐛 Troubleshooting

### Issue: "Permission denied"
**Cause**: File open in Obsidian or insufficient permissions
**Fix**: Close file, check folder permissions, run with correct user

### Issue: "Circuit breaker open"
**Cause**: Multiple consecutive failures
**Fix**: Check error logs, fix underlying issue, wait 5 min cooldown

### Issue: "Name conflict detected"
**Cause**: Target filename already exists
**Fix**: Skill auto-generates alternative (filename-2.md) or requests HITL

### Issue: Performance slow
**Cause**: Large vault or many files
**Fix**: Use batch mode with smaller chunks, check for file system issues

---

## 📖 Key Concepts

### Tier System
```yaml
Tier 0: Read-only (auto-approve)
Tier 1: Low-risk writes (auto-approve) ← This skill
Tier 2: Medium-risk (4h SLA approval)
Tier 3: High-risk (1h SLA approval)
Tier 4: Critical (immediate, 2FA)
```

### File Organization Logic
```yaml
Step 1: Detect file and issues
Step 2: Classify by content analysis
Step 3: Generate fix plan
Step 4: Validate safety
Step 5: Create backup
Step 6: Execute move/rename
Step 7: Add/update metadata
Step 8: Verify integrity
Step 9: Log operation
Step 10: Clean up backup
```

### HITL Integration
```yaml
Auto-Approve (Tier 1):
  - Rename within vault
  - Move between valid folders
  - Add/update frontmatter
  - Classification with high confidence

Require Approval (Tier 2):
  - Bulk operations (> 10 files)
  - Ambiguous classification
  - Semantic name changes
  - Files with many links
```

---

## 🎓 Learning Path

### Beginner (Day 1)
1. Read: SKILL.md sections 1-3 (Purpose, Capabilities, Usage)
2. Run: Demo 1 (Single File Organization)
3. Understand: Safety mechanisms and logging

### Intermediate (Days 2-3)
1. Read: SKILL.md sections 4-7 (Dependencies, Logging, Errors, Security)
2. Run: Demos 2-3 (Batch + Monitoring)
3. Practice: Create test files and organize them

### Advanced (Days 4-7)
1. Read: SKILL.md sections 8-14 (Constitution, Implementation, Testing)
2. Run: Demos 4-5 (Error Recovery + Health Check)
3. Execute: Full test plan
4. Review: All documentation

---

## 🚀 Deployment Readiness

### Bronze Tier Checklist
- [ ] All documentation complete
- [ ] Test plan executed (100% pass rate)
- [ ] Demo workflow validated
- [ ] Performance within targets
- [ ] Security tests pass
- [ ] Constitution compliance verified
- [ ] User training completed
- [ ] Monitoring configured
- [ ] Rollback plan documented
- [ ] Sign-off obtained

### Pre-Deployment
```yaml
Required:
  - Code review complete
  - All tests pass
  - 0 critical bugs
  - < 3 high priority bugs
  - Code coverage > 80%
  - Documentation reviewed

Recommended:
  - Staging environment testing
  - Load testing with real data
  - User acceptance testing
  - Disaster recovery drill
```

---

## 📞 Support & Resources

### Documentation
- **Specification**: [SKILL.md](./SKILL.md) - Complete technical spec
- **Demo**: [DEMO-WORKFLOW.md](./DEMO-WORKFLOW.md) - Practical examples
- **Testing**: [TEST-PLAN.md](./TEST-PLAN.md) - QA strategy
- **Constitution**: [../../../constitution.md](../../../constitution.md) - Governance rules
- **Naming**: [../../../obsidian-vault/NAMING-CONVENTIONS.md](../../../obsidian-vault/NAMING-CONVENTIONS.md) - Standards

### Quick Links
- Constitution: `constitution.md`
- Vault Structure: `obsidian-vault/README.md`
- Naming Conventions: `obsidian-vault/NAMING-CONVENTIONS.md`
- Other Skills: `.claude/skills/`

### Getting Help
1. Check troubleshooting section in SKILL.md
2. Review error logs in `70-LOGS/errors/`
3. Consult test plan for similar scenarios
4. Review constitution for governance rules

---

## 📈 Project Status

| Component | Status | Progress |
|-----------|--------|----------|
| Specification | ✅ Complete | 100% |
| Demo Workflow | ✅ Complete | 100% |
| Test Plan | ✅ Complete | 100% |
| Implementation | ⏳ Pending | 0% |
| Unit Tests | ⏳ Pending | 0% |
| Integration Tests | ⏳ Pending | 0% |
| Documentation | ✅ Complete | 100% |

**Overall**: Specification Phase Complete ✅
**Next Phase**: Begin Phase 1 Implementation (Week 1)

---

## 🎯 Next Steps

1. **Review All Documentation**
   - Read SKILL.md (45 min)
   - Read DEMO-WORKFLOW.md (30 min)
   - Read TEST-PLAN.md (30 min)

2. **Set Up Development Environment**
   - Run `setup-test-environment.sh`
   - Verify test vault structure
   - Configure testing tools

3. **Begin Phase 1 Implementation**
   - Implement file validation
   - Implement naming convention parser
   - Implement safe rename/move
   - Write unit tests

4. **Iterate**
   - Test frequently
   - Fix bugs immediately
   - Document decisions
   - Update constitution if needed

---

**Last Updated**: 2026-02-16
**Version**: 1.0.0
**Ready for**: Phase 1 Implementation

*For questions or clarifications, refer to the complete specification in SKILL.md*
