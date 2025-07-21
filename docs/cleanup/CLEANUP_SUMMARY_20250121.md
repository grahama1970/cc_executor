# CC Executor Cleanup Summary - January 21, 2025

## Overview

The cc_executor project requires significant cleanup and reorganization. This summary provides specific actionable items based on a thorough analysis of the project structure.

## Critical Issues Found

### 1. Root Directory Pollution
- **97 files** in the root directory (should be ~15)
- **45 test files** that belong in `/tests/`
- **15 JSON output files** from old test runs
- **7 fix scripts** and **4 update scripts** that should be organized

### 2. Documentation Chaos
- **49 markdown files** scattered in `/src/cc_executor/servers/docs/`
- Multiple overlapping MCP guides and test reports
- Documentation mixed with source code
- 3 different README files for MCP servers alone

### 3. Test Organization
- Test files scattered across:
  - Root directory (45 files)
  - `/tests/` directory (proper location)
  - `/src/cc_executor/servers/tests/` (wrong location)
- Many obsolete test files from development iterations

### 4. MCP Server Documentation
- Documentation lives in code directory instead of `/docs/`
- Test scenarios mixed with server implementations
- Usage guides scattered across multiple locations

## Immediate Actions Required

### Phase 1: Emergency Cleanup (Do First)
1. **Run the cleanup script in dry-run mode**:
   ```bash
   python scripts/reorganize_project.py
   ```
   
2. **Review the output** and ensure no critical files will be affected

3. **Execute the cleanup**:
   ```bash
   python scripts/reorganize_project.py --execute
   ```

### Phase 2: Manual Review (Do Second)
1. **Check for sensitive files**:
   - Move `vertex_ai_service_account.json` to secure location
   - Add to `.gitignore`

2. **Consolidate MCP documentation**:
   - Move all 49 files from `/src/cc_executor/servers/docs/` to `/docs/mcp_servers/`
   - Create single authoritative MCP guide

3. **Archive old test results**:
   - All `test_run_*/` directories
   - JSON output files with timestamps

### Phase 3: Documentation Update (Do Third)
1. Update main README.md with new structure
2. Create `/docs/README.md` as documentation index
3. Update all internal links to reflect new locations

## Files Requiring Special Attention

### Sensitive Files
```
vertex_ai_service_account.json - Contains service account credentials
.env files (if any) - May contain API keys
```

### Recently Modified Important Files
```
/src/cc_executor/servers/README.md - Main MCP documentation (keep updated)
/src/cc_executor/servers/docs/MCP_CHECKLIST.md - Critical for MCP development
```

### Active Test Files (Do Not Archive)
```
/tests/test_mcp_tools_directly.py - Recently updated (Jan 19)
/tests/test_mcp_tools_comprehensive.py - Active comprehensive test suite
```

## Proposed Final Structure

```
cc_executor/
├── README.md
├── pyproject.toml
├── setup.py
├── .gitignore
├── .mcp.json
├── requirements.txt
├── docs/
│   ├── README.md (index)
│   ├── architecture/
│   ├── guides/
│   ├── mcp_servers/
│   └── reference/
├── src/
│   └── cc_executor/
│       ├── cli/
│       ├── core/
│       ├── servers/ (only .py files)
│       └── utils/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── mcp_servers/
├── scripts/
│   ├── setup/
│   ├── debug/
│   └── analysis/
├── config/
│   └── (all .json config files)
└── archive/
    ├── old_tests/
    ├── outputs/
    └── docs/
```

## Metrics

### Before Cleanup
- Root directory files: 97
- Scattered test files: 45+
- Documentation files in wrong location: 49
- Obsolete output files: 15+

### After Cleanup (Expected)
- Root directory files: ~15
- All tests in `/tests/`: ✓
- All docs in `/docs/`: ✓
- No output files in root: ✓

## Next Steps

1. **Execute cleanup script** (created at `/scripts/reorganize_project.py`)
2. **Run tests** to ensure nothing broke
3. **Update CI/CD** to enforce new structure
4. **Add pre-commit hooks** to prevent future pollution

## Long-term Maintenance

### Monthly Reviews
- Check for new files in root
- Archive old test outputs
- Update documentation index

### Automated Checks
- Pre-commit hook to block test files in root
- CI check for proper file organization
- Automated archival of old outputs

## Notes

- The `/src/resume/` directory appears to be a separate project and may need its own repository
- Many test files test the same functionality - consolidation opportunity
- Consider adopting a monorepo tool like Nx or Lerna for better organization