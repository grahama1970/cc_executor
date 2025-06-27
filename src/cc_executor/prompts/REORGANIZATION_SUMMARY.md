# Prompts Directory Reorganization Summary

## Date: 2025-06-27 (Updated)

## Actions Taken

### 1. Moved Shell Scripts to scripts/
- ✅ `prompts/commands/check_hallucination.sh` → `scripts/check_hallucination.sh`
- ✅ `prompts/commands/verify` → `scripts/verify.sh`

### 2. Created Archive Directory
- ✅ Created `prompts/archive/` for debugging artifacts

### 3. Archived Debugging Prompts
Moved the following debugging artifacts to `prompts/archive/`:
- ✅ `anti_hallucination_verification.md` - Debugging methodology
- ✅ `hallucination_checker.md` - Hallucination detection prompt
- ✅ `stress_test_validator.md` - Validation artifact
- ✅ `output_analyzer.md` - Output analysis prompt
- ✅ `output_analyzer.py` - Output analysis tool
- ✅ `track_execution_times.md` - Performance debugging
- ✅ `redis_task_timing.md` - Redis timing prompt
- ✅ `redis_task_timing.py` - Redis timing tool

## Current Structure

### prompts/ (Root)
High-level meta prompts and orchestration:
- `claude_runner.md` - Local runner stress test (0:0 ratio, needs work)
- `cc_executor_mcp.md` - MCP integration
- `master_test_executor.md` - Test orchestration
- `unified_stress_test.md` - Comprehensive stress testing (0:3 ratio, needs fixing)
- `websocket_stress_test.md` - WebSocket testing

### prompts/commands/
Graduated and functioning command prompts:
- `ask-gemini-cli.md` - Gemini CLI integration (12:0 ratio ✅)
- `ask-litellm.md` - LiteLLM queries
- `marker-to-arangodb.md` - ArangoDB marker storage
- `check_file_rules.py` - File rule checking
- `transcript_helper.py` - Transcript operations
- `verify_marker.py` - Marker verification

### prompts/archive/
Debugging artifacts preserved for historical reference

### prompts/executor/ & prompts/orchestrator/
Context and documentation files remain in place

## Recommendations

### High Priority Reviews Needed:
1. **claude_runner.md** (0:0) - Needs execution to start improving
2. **unified_stress_test.md** (0:3) - Has failures that need fixing
3. **websocket_stress_test.md** - Review if still relevant with new architecture

### Consider Moving:
- Graduated `.py` files might belong in the main source tree
- Some meta prompts with poor ratios might need complete rewrites

## Latest Updates (2025-06-27 Afternoon)

### New Stress Test Prompts Created
Created three tiered stress test prompts in `stress_tests/`:
- `stress_test_local.md` - Direct websocket_handler.py testing
- `stress_test_fastapi.md` - FastAPI local server testing  
- `stress_test_docker.md` - Docker container testing

### Additional Reorganization
- ✅ Moved `run_stress_tests_with_full_capture.md` → `stress_tests/`
- ✅ Archived redundant stress tests superseded by 3-tier approach:
  - `master_test_executor.md/py` → `archive/`
  - `unified_stress_test_executor.md/py` → `archive/`
  - `unified_stress_test.md` → `archive/`
  - `unified_stress_test_summary.md` → `archive/`

## Next Steps
1. Execute and improve prompts with 0:0 ratios
2. Fix prompts with poor success ratios (like 0:3)
3. Consider promoting well-performing graduated .py files to the main codebase
4. Update README.md to reflect new organization
5. Run the three new stress test prompts to validate all JSON test nodes