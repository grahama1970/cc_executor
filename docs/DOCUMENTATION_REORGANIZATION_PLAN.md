# Documentation Reorganization Plan for CC Executor

## Analysis Date: 2025-07-02

After thoroughly reviewing all documentation files, here's a comprehensive reorganization plan:

## 1. Files to Archive (Outdated/Superseded)

### Research Reports (Move to `archive/2025-06/docs/research_iterations/`)
- **async_await_research_report.md** - Duplicate of python_async_await_research_report.md
- **python_async_await_research_report.md** - Research notes incorporated into guides
- **arxiv_mcp_extraction_methods.md** - Planning doc, now implemented
- **arxiv_mcp_server_summary.md** - Implementation summary, superseded by UNIFIED_RESEARCH_ARCHITECTURE.md

### Implementation Summaries (Move to `archive/2025-06/docs/implementation_notes/`)
- **015b_implementation_summary.md** - Code review implementation notes
- **REORGANIZATION_SUMMARY.md** - Old reorganization notes
- **process_tracking_improvements.md** - Implementation notes, now in code
- **load_aware_timeout_implementation.md** - Implementation notes, now in code
- **websocket_enhancements.md** - Old enhancement notes
- **websocket_large_output_fix_summary.md** - Fix already applied

### Old Guides (Move to `archive/2025-06/docs/old_guides/`)
- **asyncio_subprocess_timeout_solution.md** - Superseded by comprehensive guide
- **SELF_REFLECTION_IMPLEMENTATION.md** - Implementation notes, now in prompts
- **TASK_LIST_TEMPLATE_GUIDE.md** - Superseded by prompt templates
- **LEARNING_FROM_FAILURES_SUMMARY.md** - Incorporated into CLAUDE_CODE_PROMPT_RULES.md
- **REDIS_TIMEOUT_INTEGRATION_COMPLETE.md** - Implementation complete, notes obsolete

## 2. Files to Keep and Reorganize

### Core Documentation (Keep in `docs/`)
- **README.md** (Create new) - Project overview and quick start
- **CLAUDE_CODE_PROMPT_RULES.md** - Essential rules (consider renaming to PROMPT_BEST_PRACTICES.md)
- **LESSONS_LEARNED.md** - Valuable insights (trim to most relevant)
- **KNOWN_ISSUES.md** - Current operational issues
- **FAVORITES.md** - Quick reference links

### Architecture Documentation (Move to `docs/architecture/`)
- All files currently in architecture/ subdirectory (keep as-is)
- **WEBSOCKET_REALITY_CHECK.md** - Move here as websocket_architecture_notes.md

### Guides (Keep in `docs/guides/`)
- **OPERATING_THE_SERVICE.md** - Essential operations guide
- **TROUBLESHOOTING.md** - Essential debugging guide
- **DEBUGGING_GUIDE.md** - Merge with TROUBLESHOOTING.md
- **VSCODE_DEBUG_STANDARD.md** - Move to guides/vscode_debugging.md
- **AGENT_TIMEOUT_GUIDE.md** - Move to guides/timeout_configuration.md

### Hook System Documentation (Create `docs/hooks/`)
- **HOOK_SYSTEM_COMPREHENSIVE_GUIDE.md** - Rename to README.md in hooks/
- **HOOKS_USAGE_GUIDE.md** - Rename to usage_guide.md
- **HOOK_USAGE_EXAMPLES.md** - Rename to examples.md
- **ANTHROPIC_HOOKS_INTEGRATION.md** - Rename to integration_overview.md
- **CLAUDE_SPAWNING_FLOW_WITH_HOOKS.md** - Rename to execution_flow.md
- **CLAUDE_INSTANCE_RELIABILITY.md** - Move to hooks/reliability_enforcement.md

### Reports (Keep in `docs/reports/`)
- **FULL_STRESS_TEST_REPORT_FINAL.md** - Keep as final stress test report
- Create reports/README.md explaining report structure

### Technical Guides (Create `docs/technical/`)
- **asyncio_timeout_comprehensive_guide.md** - Rename to asyncio_timeout_guide.md
- **ENVIRONMENT_VARIABLES.md** - Move here
- **LOGGING.md** & **LOGS.md** - Merge into single logging_guide.md
- **RESOURCE_MONITORING.md** - Move here
- **REDIS_TIMING_INTEGRATION.md** - Rename to redis_integration.md
- **ACK_LAST_LINE_OF_DEFENSE.md** - Move to technical/timeout_patterns.md

### New Additions (Create in `docs/`)
- **UNIFIED_RESEARCH_ARCHITECTURE.md** - Keep as-is (recent addition)
- **RESEARCH_COLLABORATOR_COMPLETE_SUMMARY.md** - Move to docs/features/
- **TRANSCRIPT_LIMITATIONS.md** - Move to technical/
- **NEW_FINDINGS.md** - Review and merge relevant parts into other docs
- **REVIEW_WORKFLOW.md** - Move to guides/development_workflow.md

## 3. Content to Merge/Consolidate

### Logging Documentation
Merge these into single `docs/technical/logging_guide.md`:
- LOGGING.md (application logging)
- LOGS.md (appears corrupted, extract useful parts)

### Debugging Documentation  
Merge these into enhanced `docs/guides/troubleshooting.md`:
- TROUBLESHOOTING.md (current guide)
- DEBUGGING_GUIDE.md (VSCode specific parts to vscode_debugging.md)

### Timeout Documentation
Create comprehensive `docs/technical/timeout_management.md` from:
- AGENT_TIMEOUT_GUIDE.md
- ACK_LAST_LINE_OF_DEFENSE.md
- Parts of asyncio_timeout_comprehensive_guide.md

## 4. Files Needing Content Updates

### High Priority Updates
1. **KNOWN_ISSUES.md** - Review and update status of all issues
2. **LESSONS_LEARNED.md** - Trim to most valuable insights, remove redundancy
3. **CLAUDE_CODE_PROMPT_RULES.md** - Update with latest learnings
4. **FAVORITES.md** - Verify all links still valid

### Documentation to Create
1. **docs/README.md** - Main documentation index
2. **docs/quickstart.md** - Getting started guide
3. **docs/api/README.md** - API documentation
4. **docs/development/README.md** - Development guide

## 5. Proposed New Structure

```
docs/
├── README.md                    # Documentation index
├── quickstart.md               # Getting started
├── CLAUDE_CODE_PROMPT_RULES.md # Prompt best practices
├── LESSONS_LEARNED.md          # Key insights
├── KNOWN_ISSUES.md            # Current issues
├── FAVORITES.md               # Quick references
│
├── architecture/              # System architecture
│   ├── README.md
│   ├── how_claude_sees_code.md
│   ├── websocket_mcp_protocol.md
│   └── ... (existing files)
│
├── guides/                    # User guides
│   ├── README.md
│   ├── OPERATING_THE_SERVICE.md
│   ├── troubleshooting.md    # Merged guide
│   ├── vscode_debugging.md
│   ├── timeout_configuration.md
│   └── development_workflow.md
│
├── hooks/                     # Hook system docs
│   ├── README.md             # Comprehensive guide
│   ├── usage_guide.md
│   ├── examples.md
│   ├── integration_overview.md
│   ├── execution_flow.md
│   └── reliability_enforcement.md
│
├── technical/                 # Technical references
│   ├── README.md
│   ├── asyncio_timeout_guide.md
│   ├── environment_variables.md
│   ├── logging_guide.md      # Merged
│   ├── resource_monitoring.md
│   ├── redis_integration.md
│   ├── timeout_management.md # Merged
│   └── transcript_limitations.md
│
├── features/                  # Feature documentation
│   ├── README.md
│   ├── research_collaborator.md
│   └── unified_research_architecture.md
│
├── reports/                   # Test reports
│   ├── README.md
│   ├── stress_test_final.md
│   └── ... (existing reports)
│
└── api/                      # API documentation
    └── README.md
```

## 6. Action Items

1. **Create archive directories** for obsolete documentation
2. **Move files** according to the plan above
3. **Merge duplicate content** as specified
4. **Create missing README files** for each directory
5. **Update cross-references** in moved documents
6. **Remove corrupted content** (LOGS.md appears damaged)
7. **Create new index files** for better navigation

## 7. Documentation Quality Standards

Going forward, all documentation should:
- Have clear headers and purpose statements
- Include last updated dates
- Reference related documentation
- Avoid duplication
- Be placed in the appropriate subdirectory
- Follow consistent formatting