# 90-TEMPLATES: Markdown Templates

## Purpose
Standardized markdown templates for creating consistent documentation, ensuring all required fields are captured, and accelerating content creation across the vault.

## Available Templates

### Core System Templates
| Template | Purpose | Usage Frequency |
|----------|---------|-----------------|
| [[agent-profile\|Agent Profile]] | Define new agent capabilities | Weekly |
| [[process-sop\|Process SOP]] | Document standard procedures | Weekly |
| [[mcp-integration\|MCP Integration]] | Configure MCP servers | Monthly |
| [[api-integration\|API Integration]] | External API setup | Monthly |

### Knowledge Templates
| Template | Purpose | Usage Frequency |
|----------|---------|-----------------|
| [[knowledge-article\|Knowledge Article]] | Domain knowledge | Daily |
| [[domain-map\|Domain Map]] | Knowledge area overview | Monthly |
| [[skill-definition\|Skill Definition]] | Agent skill specification | Weekly |

### Process Templates
| Template | Purpose | Usage Frequency |
|----------|---------|-----------------|
| [[workflow-definition\|Workflow Definition]] | Automated workflows | Weekly |
| [[hitl-gate\|HITL Gate]] | Human approval checkpoint | Monthly |
| [[playbook\|Scenario Playbook]] | Situation handling | Monthly |

### Business Templates
| Template | Purpose | Usage Frequency |
|----------|---------|-----------------|
| [[business-model\|Business Model]] | Business framework | Quarterly |
| [[kpi-definition\|KPI Definition]] | Metric specification | Monthly |
| [[business-rule\|Business Rule]] | Business logic | Weekly |
| [[analytics-report\|Analytics Report]] | Data analysis | Daily |

### Prompt Templates
| Template | Purpose | Usage Frequency |
|----------|---------|-----------------|
| [[prompt-template\|Prompt Template]] | AI prompt structure | Daily |
| [[chain-definition\|Chain Definition]] | Multi-step prompts | Weekly |
| [[prompt-evaluation\|Prompt Evaluation]] | Performance tracking | Weekly |

### Memory Templates
| Template | Purpose | Usage Frequency |
|----------|---------|-----------------|
| [[episodic-memory\|Episodic Memory]] | Event recording | Daily |
| [[semantic-memory\|Semantic Memory]] | Fact documentation | Weekly |
| [[procedural-memory\|Procedural Memory]] | Skill documentation | Monthly |
| [[context-profile\|Context Profile]] | Entity context | Daily |

### Security Templates
| Template | Purpose | Usage Frequency |
|----------|---------|-----------------|
| [[security-policy\|Security Policy]] | Policy documentation | Quarterly |
| [[role-definition\|Role Definition]] | RBAC configuration | Monthly |
| [[incident-report\|Incident Report]] | Security incident | As needed |
| [[compliance-checklist\|Compliance Checklist]] | Regulatory checks | Monthly |

### Logging Templates
| Template | Purpose | Usage Frequency |
|----------|---------|-----------------|
| [[log-entry\|Log Entry]] | Structured logging | Continuous |
| [[error-report\|Error Report]] | Error documentation | As needed |
| [[daily-summary\|Daily Summary]] | Daily operations log | Daily |

### Collaboration Templates
| Template | Purpose | Usage Frequency |
|----------|---------|-----------------|
| [[decision-log\|Decision Log]] | Record decisions | Weekly |
| [[meeting-note\|Meeting Note]] | Meeting documentation | Weekly |
| [[project-brief\|Project Brief]] | Project overview | Monthly |

## Using Templates

### In Obsidian
1. Install "Templater" plugin (recommended) or use core Templates plugin
2. Configure template folder to point to `90-TEMPLATES/`
3. Use hotkey or command palette to insert template
4. Fill in placeholders (marked with `{{}}` or `[...]`)

### Template Syntax
- **Variables**: `{{variable_name}}` - Replace with actual value
- **Optional**: `[OPTIONAL: description]` - Can be removed if not needed
- **Required**: `[REQUIRED: description]` - Must be filled
- **Instructions**: Italic text starting with "*Note:*" - Delete after reading

### Example Usage
```markdown
Creating a new agent profile:
1. Open Obsidian
2. Navigate to: 10-KNOWLEDGE/agents/
3. Insert template: agent-profile
4. Replace {{agent_name}} with actual name
5. Fill all REQUIRED fields
6. Complete OPTIONAL fields if applicable
7. Delete instruction notes
8. Save file with naming convention: NNN-agent-name.md
```

## Template Standards

### Front Matter
All templates should include:
```yaml
---
id: [Auto-generated or specified]
name: [Human-readable name]
type: [Template category]
status: [draft | active | deprecated]
version: [Semantic version]
created: [YYYY-MM-DD]
updated: [YYYY-MM-DD]
tags: [relevant, tags, here]
---
```

### Structure
1. **Header**: Title and purpose
2. **Metadata**: Front matter and key info
3. **Core Content**: Main template body
4. **Related**: Links to related documents
5. **Changelog**: Version history (for critical templates)

### Placeholders
- Use `{{snake_case}}` for variables
- Use `[ALL_CAPS: description]` for required fields
- Use `[OPTIONAL: description]` for optional fields
- Use `*Note:* ...` for instructions to be deleted

## Maintenance

### Adding New Templates
1. Create template file in appropriate subfolder
2. Follow naming convention: `template-name.md`
3. Include all standard sections
4. Add to this README index
5. Test template creation process
6. Document in related section READMEs

### Updating Templates
1. Increment version number
2. Document changes in changelog
3. Update related documentation
4. Notify agents of changes
5. Archive old version if breaking changes

### Deprecating Templates
1. Mark status as "deprecated"
2. Add deprecation notice at top
3. Link to replacement template
4. Set removal date (minimum 90 days)
5. Archive after removal date

## Quality Checklist

When creating/updating templates:
- [ ] Front matter complete and valid
- [ ] All placeholders clearly marked
- [ ] Instructions in italics
- [ ] Required vs optional fields distinguished
- [ ] Related links included
- [ ] Examples provided (where applicable)
- [ ] Validation criteria included
- [ ] Follows naming conventions
- [ ] Added to this index
- [ ] Tested in practice

## Template Categories

### By Complexity
- **Simple**: < 50 lines, few fields (e.g., log-entry)
- **Medium**: 50-200 lines, structured sections (e.g., agent-profile)
- **Complex**: > 200 lines, multiple components (e.g., business-model)

### By Usage Pattern
- **Frequent**: Daily/Weekly use (e.g., knowledge-article, log-entry)
- **Regular**: Monthly use (e.g., process-sop, security-policy)
- **Occasional**: Quarterly/As-needed (e.g., incident-report)

## Best Practices

### For Template Creators
1. **Start Simple**: Begin with minimal required fields
2. **Add Instructions**: Clear guidance for each section
3. **Provide Examples**: Show what good looks like
4. **Test Thoroughly**: Use template yourself first
5. **Gather Feedback**: Iterate based on user input
6. **Version Control**: Track changes over time
7. **Document Why**: Explain purpose and decisions

### For Template Users
1. **Read Instructions**: Don't skip the guidance
2. **Fill All Required**: Never leave required fields blank
3. **Delete Instructions**: Remove notes after reading
4. **Follow Conventions**: Use naming and tagging standards
5. **Link Related**: Connect to relevant documents
6. **Update Regularly**: Keep information current
7. **Share Improvements**: Suggest template enhancements

## Integration

Templates integrate with:
- **10-KNOWLEDGE**: Knowledge article templates
- **20-PROCESSES**: Workflow and SOP templates
- **30-INTEGRATIONS**: Integration configuration templates
- **40-SECURITY**: Security and compliance templates
- **50-BUSINESS**: Business and analytics templates
- **60-PROMPTS**: Prompt engineering templates
- **70-LOGS**: Logging and reporting templates
- **80-MEMORY**: Memory entry templates

## Advanced Features

### Templater Scripts (Optional)
If using Templater plugin, templates can include:
- Dynamic dates: `<% tp.date.now("YYYY-MM-DD") %>`
- User input prompts: `<% tp.system.prompt("Agent name?") %>`
- File operations: Auto-naming, folder selection
- Custom JavaScript: Advanced automation

### Template Chaining
Some templates reference others:
```markdown
Example: agent-profile template includes:
- Skills from: skill-definition template
- Prompts from: prompt-template template
- Memory config from: context-profile template
```

## Support

### Template Issues
If a template is:
- **Missing fields**: Submit enhancement request
- **Confusing**: Request clarification
- **Broken**: Report bug
- **Outdated**: Flag for update

### Getting Help
- Check: [[../00-INDEX/000-HOME|Vault Home]]
- Review: Section-specific READMEs
- Search: Existing examples in vault
- Ask: Human-in-the-loop for guidance

---

**Maintained by**: Documentation Agent
**Last Review**: 2026-02-16
**Next Review**: 2026-03-16
**Total Templates**: 30+
**Most Used**: knowledge-article, log-entry, prompt-template
