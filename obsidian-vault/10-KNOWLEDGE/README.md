# 10-KNOWLEDGE: Domain Knowledge & Learning

## Purpose
Central repository for all domain knowledge, learning materials, and information used by AI agents to make decisions and perform tasks.

## Structure

```
10-KNOWLEDGE/
├── agents/              # Agent profiles and capabilities
├── domains/             # Business domain knowledge
│   ├── customer/        # Customer-related knowledge
│   ├── finance/         # Financial knowledge
│   ├── legal/           # Legal and compliance
│   ├── marketing/       # Marketing knowledge
│   ├── operations/      # Operations knowledge
│   └── technical/       # Technical documentation
├── graphs/              # Knowledge graphs and relationships
├── ontologies/          # Semantic models and taxonomies
├── reference/           # Reference materials and docs
├── skills/              # Agent skill definitions
└── training/            # Training materials and datasets
```

## Key Files

- **[[agents/index|Agent Index]]** - Directory of all agents and their knowledge domains
- **[[domains/index|Domain Index]]** - Map of business domain knowledge
- **[[graphs/main-graph|Main Knowledge Graph]]** - Visual relationship map
- **[[skills/skill-matrix|Skill Matrix]]** - Agent capabilities matrix

## Usage by AI Agents

### Knowledge Retrieval
```markdown
Query: "What are the customer onboarding steps?"
Path: 10-KNOWLEDGE/domains/customer/onboarding-process.md
```

### Skill Application
```markdown
Agent: customer-support-agent
Skills: 10-KNOWLEDGE/skills/customer-service.md
       10-KNOWLEDGE/skills/crm-management.md
```

### Graph Navigation
Agents traverse knowledge graphs to:
- Discover related concepts
- Find dependencies
- Identify patterns
- Make informed decisions

## Naming Conventions

### Files
- `NNN-topic-name.md` (e.g., `001-customer-segmentation.md`)
- Use lowercase with hyphens
- Start with 3-digit sequence number

### Tags
- `#knowledge/<domain>` - Domain category
- `#agent/<name>` - Agent that uses this knowledge
- `#skill/<name>` - Related skill
- `#updated/<YYYY-MM>` - Last update period

## Maintenance

### Daily
- [ ] Review new knowledge additions
- [ ] Update agent profiles with new learnings

### Weekly
- [ ] Audit knowledge graph connections
- [ ] Archive outdated information

### Monthly
- [ ] Comprehensive domain review
- [ ] Update skill matrices
- [ ] Refactor ontologies as needed

## Templates

- [[../90-TEMPLATES/knowledge-article|Knowledge Article]]
- [[../90-TEMPLATES/domain-map|Domain Map]]
- [[../90-TEMPLATES/skill-definition|Skill Definition]]

## Integration with Other Sections

- **20-PROCESSES**: Knowledge enables process execution
- **50-BUSINESS**: Business models inform knowledge structure
- **60-PROMPTS**: Prompts reference knowledge articles
- **80-MEMORY**: Long-term learning updates knowledge base

---

**Owned by**: Knowledge Management Agent
**Last Review**: 2026-02-16
**Next Review**: 2026-03-16
