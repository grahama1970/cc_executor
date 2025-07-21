# CC Executor Project Reorganization Plan - January 2025

## Executive Summary

After a thorough analysis of the cc_executor project, significant cleanup and reorganization is needed. The project has accumulated many temporary files, obsolete tests, and redundant documentation from various development phases.

## 1. Root Directory Cleanup

### Files to Archive/Remove

#### Test Files (Move to `/archive/old_tests/`)
```
test_*.py files in root:
- test_arango_*.py (6 files)
- test_gemini_*.py 
- test_gpu_*.py (2 files)
- test_hello_universal_llm.py
- test_infrastructure_readiness.py
- test_kilocode_*.py (6 files)
- test_llm_*.py (7 files)
- test_mcp_*.py (5 files)
- test_posthook.py
- test_qlearning_integration.py
- test_review_non_interactive.py
- test_scenario_16_pattern_discovery.py
- test_single_file_review.py
- test_two_level_review.py
- test_universal_llm.py
```

#### Fix/Update Scripts (Move to `/scripts/fixes/`)
```
- fix_*.py (7 files)
- update_*.py (4 files)
- verify_*.py (3 files)
```

#### Scenario Files (Move to `/archive/scenarios/`)
```
- scenario_*.py (4 files)
- create_test_data_scenarios_9_10.py
- execute_scenario_16.py
```

#### Debug Scripts (Move to `/scripts/debug/`)
```
- debug_*.py (3 files)
- diagnose_mcp_issues.py
```

#### Old Output Files (Delete)
```
- gemini_output_*.json (15 files) - These are test outputs from July 2025
- raw_output.txt
- test_results_*.json (2 files)
```

#### Installation Scripts (Move to `/scripts/setup/`)
```
- install_universal_llm_mcp.py
- create_mcp_logger_package.py
```

### Files to Keep in Root
```
Essential files only:
- .claude-hooks*.json (2 files)
- .env.example
- .gitignore
- .mcp.json
- CHANGELOG.md
- LICENSE
- pyproject.toml
- README.md
- requirements.txt
- setup.py
- uv.lock
- vertex_ai_service_account.json (sensitive - consider moving to secrets/)
```

## 2. Documentation Reorganization

### Current Issues
- Multiple overlapping guides in `/docs/`
- Archived content mixed with current docs
- Redundant MCP documentation across multiple locations

### Proposed Structure
```
/docs/
├── README.md (index of all docs)
├── QUICK_START.md
├── architecture/
│   ├── overview.md
│   ├── mcp_integration.md
│   └── websocket_protocol.md
├── guides/
│   ├── deployment/
│   ├── development/
│   └── operations/
├── reference/
│   ├── api/
│   ├── cli/
│   └── configuration/
├── mcp_servers/
│   ├── README.md (from src/cc_executor/servers/README.md)
│   ├── checklist.md
│   └── individual_server_docs/
└── archive/
    └── [organized by date]
```

### Documentation to Consolidate/Archive

#### Redundant MCP Docs (Consolidate into `/docs/mcp_servers/`)
- Multiple MCP test reports and summaries
- Scattered MCP debugging guides
- Various MCP tool status files

#### Old Implementation Notes (Archive)
- Files with dates in names (e.g., `*_20250709.md`)
- Superseded guides and summaries

## 3. Test Directory Cleanup (`/tests/`)

### Issues Found
- Many ad-hoc test files in root
- Obsolete test directories
- Redundant stress test results

### Proposed Cleanup
```
/tests/
├── unit/          # Keep existing unit tests
├── integration/   # Keep integration tests
├── mcp_servers/   # Consolidate all MCP tests here
├── fixtures/      # Test data and fixtures
└── archive/       # Old/obsolete tests
```

### Tests to Archive/Remove
- `test_project/` and `test_project_alt/` - Empty test directories
- Old stress test results in `stress_test_results/`
- Duplicate comprehensive test files

## 4. Source Code Organization

### `/src/cc_executor/servers/`

#### Issues
- Mixed documentation in code directory
- Unorganized test scenarios
- Utils mixed with server implementations

#### Proposed Changes
1. Move all docs from `/src/cc_executor/servers/docs/` to `/docs/mcp_servers/`
2. Keep only actual MCP server implementations in this directory
3. Move test scenarios to `/tests/mcp_servers/scenarios/`

### `/src/resume/`
- This appears to be a separate project/module
- Consider moving to its own repository or clearly documenting its purpose

## 5. Scripts and Tools Organization

Create organized script directories:
```
/scripts/
├── setup/         # Installation and setup scripts
├── debug/         # Debugging utilities
├── fixes/         # One-time fix scripts (archive after use)
├── analysis/      # Analysis and reporting tools
└── mcp/          # MCP-specific utilities
```

## 6. Priority Actions

### Immediate (High Priority)
1. **Clean root directory** - Move all test files and scripts
2. **Archive old outputs** - Remove JSON outputs and temporary files
3. **Consolidate MCP docs** - Single source of truth for MCP documentation

### Short Term (Medium Priority)
1. **Reorganize tests** - Create proper test structure
2. **Update README** - Reflect new organization
3. **Archive obsolete code** - Move deprecated implementations

### Long Term (Low Priority)
1. **Refactor prompts** - Review and consolidate prompt directories
2. **Documentation overhaul** - Complete rewrite with new structure
3. **CI/CD integration** - Add automated cleanup checks

## 7. Files Requiring Special Attention

### Sensitive Files
- `vertex_ai_service_account.json` - Should be in `.gitignore` and moved to secure location
- Any API keys or credentials in config files

### Configuration Files
- Multiple `.claude-hooks*.json` files - Consolidate if possible
- Various config JSONs in root - Move to `/config/` directory

### Generated Files
- Ensure all generated reports and outputs have a designated directory
- Add to `.gitignore` if appropriate

## 8. Implementation Checklist

- [ ] Create archive directories
- [ ] Move test files from root
- [ ] Archive old output files
- [ ] Reorganize documentation
- [ ] Consolidate MCP documentation
- [ ] Clean up test directory
- [ ] Organize scripts
- [ ] Update README with new structure
- [ ] Update .gitignore
- [ ] Create migration script for easy rollback

## 9. Post-Cleanup Verification

After reorganization:
1. All tests still pass
2. MCP servers still function
3. Documentation is accessible
4. No broken imports
5. Git history preserved for important files

## 10. Maintenance Guidelines

Going forward:
1. No test files in root directory
2. All outputs go to designated directories
3. Documentation follows the new structure
4. Regular cleanup reviews (monthly)
5. Automated checks for organization standards