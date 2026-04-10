---
id: 001
title: Create Personal AI Employee Constitution
stage: constitution
date: 2026-02-16
surface: agent
model: claude-sonnet-4-5-20250929
feature: none
branch: master
user: Computer Technology
command: /sp.constitution
labels: ["constitution", "governance", "hackathon-0", "bronze-tier", "hitl", "security"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - constitution.md
tests:
  - Manual validation of constitution structure
  - Compliance checklist verification
  - Bronze tier requirements coverage
---

## Prompt

You are a Senior AI Systems Architect designing governance for a Personal AI Employee.

Create a production-ready but hackathon-appropriate Constitution for my AI Employee system.

Context:
This is Hackathon 0 (Bronze Tier foundation).
The system uses:
- Claude Code as reasoning engine
- Obsidian as local-first vault
- Watchers (Python)
- MCP servers for actions
- Human-in-the-loop approval system
- Ralph Wiggum loop for persistence

Requirements:
- Save as: constitution.md
- This constitution file must be created inside the root project folder named Hackathon_0
- Clear professional markdown
- Simple but scalable
- Practical (not corporate overkill)
- Aligned with Bronze → Silver → Gold growth

Include:

1. System Purpose
2. Core Operating Principles
3. Human-in-the-Loop Governance Model
4. Safety & Risk Boundaries
5. Vault & File Governance Rules
6. MCP & External Action Control
7. Logging & Audit Requirements
8. Security & Credential Handling
9. Skill Design Rules (how future skills must be built)
10. Evolution Path (Bronze → Silver → Gold)

## Response snapshot

Created comprehensive Personal AI Employee System Constitution (v1.0.0) covering:

**Structure**:
- 10 major sections as requested
- 6 core operating principles (Local-First Sovereignty, Explicit Over Implicit, HITL by Default, Composability, Memory as Knowledge, Fail Safe/Visible)
- 5-tier approval system (Tier 0-4 from read-only to critical actions)
- Complete Bronze → Silver → Gold evolution path

**Key Features**:
- **HITL Governance**: Detailed approval workflow with SLA-based escalation, 5 risk tiers
- **Safety Boundaries**: Hard limits, operational boundaries per tier, circuit breakers
- **Vault Governance**: Immutable folder structure, strict naming conventions, atomic write operations
- **MCP Control**: Server registration requirements, approval matrix, health checks
- **Logging**: 5-level system (DEBUG → CRITICAL) with retention policies, immutable audit trails
- **Security**: Environment-based credential storage, access control per agent, incident response
- **Skill Design**: 5 principles (Single Responsibility, Idempotent, Fail Fast, Observable, Testable)
- **Evolution Path**: Clear Bronze → Silver → Gold progression with success metrics

**Governance**:
- Amendment process with impact analysis
- Semantic versioning (MAJOR.MINOR.PATCH)
- Review schedule (weekly/monthly/quarterly/annually)
- Compliance checklist for new capabilities

**Philosophy**:
- Hackathon-appropriate (practical, not corporate overkill)
- Production-ready (security, audit, compliance)
- Scalable (designed for growth from Bronze to Gold tier)
- Transparent (all actions logged and auditable)

## Outcome

- ✅ Impact: Foundation governance document for entire Personal AI Employee system. Establishes operational boundaries, security controls, and growth path.
- 🧪 Tests: Constitution structure validated, all 10 required sections included, Bronze tier requirements met
- 📁 Files: 1 file created (constitution.md in root Hackathon_0 folder)
- 🔁 Next prompts: Implement first skills following Skill Design Rules, set up HITL approval system, configure initial MCP servers
- 🧠 Reflection: Constitution strikes good balance between hackathon agility and production requirements. HITL tier system enables gradual automation. Bronze → Silver → Gold path provides clear evolution trajectory.

## Evaluation notes (flywheel)

- Failure modes observed: None. Constitution successfully created with comprehensive coverage.
- Graders run and results (PASS/FAIL):
  - ✅ PASS: All 10 required sections included
  - ✅ PASS: Professional markdown formatting
  - ✅ PASS: Simple but scalable structure
  - ✅ PASS: Practical (not corporate overkill)
  - ✅ PASS: Bronze → Silver → Gold alignment
- Prompt variant (if applicable): N/A - Initial constitution creation
- Next experiment (smallest change to try): Test constitution enforcement in first skill implementation to validate governance model works in practice

---

**Notes**:
- Constitution saved to root project folder as requested
- Version 1.0.0 establishes Bronze Tier baseline
- Ratification date: 2026-02-16
- Next review scheduled: 2026-03-16 (30 days)
- All dependent templates and artifacts should reference this constitution for compliance checks
