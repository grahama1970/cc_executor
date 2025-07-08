# CC Executor Tests Directory Structure

## Overview

This directory contains all tests for the cc_executor project, organized by test type and purpose.

## Directory Structure

```
tests/
├── unit/                      # Unit tests for individual components
├── integration/               # Integration tests for system components
├── proof_of_concept/          # POC tests for new features
├── stress/                    # Stress testing framework
├── apps/                      # Test applications for integration testing
├── test_results/              # Test execution results and archives
└── archive_old_tests.sh       # Script to archive old test results
```

## Active Test Categories

### 1. Unit Tests (`/unit/`)
- **Purpose**: Test individual components in isolation
- **Key Files**:
  - `test_hook_integration_security.py` - Security tests for hook integration
  - `test_websocket_error_propagation.py` - WebSocket error handling tests
  - `run_security_tests.py` - Security test runner

### 2. Integration Tests (`/integration/`)
- **Purpose**: Test interaction between system components
- **Recent Tests** (July 2025):
  - `test_cc_execute_full_flow.py` - Full execution flow testing
  - `test_claude_streaming.py` - Streaming output tests
  - `test_hook_integration.py` - Hook system integration
  - `test_websocket_*.py` - WebSocket functionality tests
  - `test_orchestrator_pattern.py` - Orchestration pattern tests

### 3. Proof of Concept Tests (`/proof_of_concept/`)
- **Purpose**: Validate new features and approaches
- **Active POCs** (Updated July 7, 2025):
  - `test_executor.py` - Core executor functionality
  - `test_json_output.py` - JSON output mode testing
  - `test_streaming_json.py` - Streaming JSON responses
  - `test_timeout_debug*.py` - Timeout handling improvements
  - `test_report_generation.py` - Assessment report generation
  - `test_game_engine_stress.py` - Game engine stress testing

### 4. Stress Tests (`/stress/`)
- **Purpose**: Load testing and performance validation
- **Structure**:
  - `configs/` - Test configuration files
  - `prompts/` - Stress test prompts
  - `runners/` - Test execution runners
  - `utils/` - Testing utilities
  - `tasks/` - Task definitions

### 5. Test Applications (`/apps/`)
- **Purpose**: Real-world application scenarios for testing
- **Applications**:
  - `data_pipeline/` - Data processing pipeline tests
  - `fastapi_project/` - FastAPI service implementation tests
  - `web_project/` - Web application project tests
  - `todo-app/` - Full-stack todo application
  - `advanced_workflows/` - Complex workflow scenarios

## Test Results and Archives

### Current Results Location
- Active test results: Generated in respective test directories
- Archived results: `/test_results/archive/`

### Archive Structure
```
test_results/archive/
├── old_stress_tests_structure/     # Pre-June 2025 structure
├── old_test_outputs/               # June 27-30, 2025 outputs
├── stress_test_outputs_20250629/   # Specific test run
└── stress_tests_june_2025/         # June 2025 stress tests
```

## Running Tests

### Unit Tests
```bash
cd tests/unit
python -m pytest
```

### Integration Tests
```bash
cd tests/integration
python test_cc_execute_full_flow.py
```

### Stress Tests
```bash
cd tests/stress
python runners/run_simple_stress_tests.py
```

## Maintenance

### Archiving Old Results
Use the provided script to archive old test results:
```bash
cd tests
./archive_old_tests.sh
```

### .gitignore Patterns
The following patterns should be in .gitignore:
- `node_modules/` - Node.js dependencies
- `*.log` - Log files
- `test_outputs/` - Generated test outputs
- `__pycache__/` - Python cache files

## Best Practices

1. **Organization**: Keep test files organized by type and purpose
2. **Naming**: Use descriptive names that indicate what is being tested
3. **Cleanup**: Archive old test results regularly to keep the directory clean
4. **Documentation**: Update this file when adding new test categories

## Recent Updates

- **July 8, 2025**: Archived June 2025 stress test results
- **July 7, 2025**: Updated all POC tests for new features
- **July 1-6, 2025**: Added FastAPI project tests
- **June 26-30, 2025**: Comprehensive stress testing phase