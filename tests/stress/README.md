# CC Executor Stress Tests

Comprehensive stress testing framework for CC Executor with tests organized by complexity and category.

## Directory Structure

```
tests/stress/
├── configs/          # JSON test configurations
│   ├── simple_stress_tests.json     # Quick tests (5-30s)
│   ├── medium_stress_tests.json     # Moderate tests (30-90s)
│   ├── complex_stress_tests.json    # Long tests (90-300s)
│   ├── all_stress_tests.json        # Complete suite (all categories)
│   └── [legacy configs...]          # Previous test configurations
│
├── prompts/          # Self-improving prompt templates
│   ├── simple_stress_tests_prompt.md
│   ├── medium_stress_tests_prompt.md
│   ├── complex_stress_tests_prompt.md
│   ├── all_stress_tests_prompt.md
│   └── [legacy prompts...]          # Previous prompt templates
│
├── runners/          # Python execution scripts
│   ├── run_simple_stress_tests.py
│   ├── run_medium_stress_tests.py
│   ├── run_complex_stress_tests.py
│   ├── run_all_stress_tests.py
│   └── [legacy runners...]          # Previous test runners
│
├── reports/          # Generated test reports
│   ├── simple_stress_tests_report.md
│   ├── medium_stress_tests_report.md
│   ├── complex_stress_tests_report.md
│   └── all_stress_tests_report.md
│
└── utils/            # Shared utilities
```

## NEW: Categorized Test Suites

### By Complexity

| Suite | Config | Runner | Prompt | Tests | Timeout | Duration |
|-------|--------|--------|--------|-------|---------|----------|
| **Simple** | `simple_stress_tests.json` | `run_simple_stress_tests.py` | `simple_stress_tests_prompt.md` | 5 | 120s | 5-10 min |
| **Medium** | `medium_stress_tests.json` | `run_medium_stress_tests.py` | `medium_stress_tests_prompt.md` | 7 | 180s | 10-15 min |
| **Complex** | `complex_stress_tests.json` | `run_complex_stress_tests.py` | `complex_stress_tests_prompt.md` | 7 | 300s | 15-25 min |
| **All** | `all_stress_tests.json` | `run_all_stress_tests.py` | `all_stress_tests_prompt.md` | 22+ | Varies | 30-40 min |

### Test Categories in "All" Suite
- **Simple**: Basic arithmetic, echo, date commands
- **Medium**: Code generation, creative writing, recipes
- **Complex**: Long essays, technical guides, architecture docs
- **Edge Cases**: Unicode, empty responses, boundary conditions
- **Stress**: Concurrent operations, system design tasks

## Legacy Test Suites

| Suite | Config | Runner | Prompt | Description |
|-------|--------|--------|--------|-------------|
| **adaptive** | `configs/adaptive.json` | `runners/adaptive.py` | - | Intelligent retry on token/rate limits |
| **basic** | `configs/basic.json` | `runners/basic.py` | `prompts/main.md` | Standard test execution |
| **extended** | `configs/extended.json` | `runners/final.py` | `prompts/extended.md` | Extended test scenarios |
| **safe** | `configs/safe.json` | - | - | Conservative tests avoiding limits |
| **minimal** | `configs/minimal.json` | - | - | Quick validation tests |

## Running Tests

### Prerequisites
1. Ensure cc_executor server is running:
   ```bash
   cd /home/graham/workspace/experiments/cc_executor
   source .venv/bin/activate
   python -m cc_executor.main
   ```

2. In another terminal, navigate to the project:
   ```bash
   cd /home/graham/workspace/experiments/cc_executor
   source .venv/bin/activate
   ```

### Run NEW Categorized Test Suites

```bash
# Simple tests only (5-10 minutes)
python tests/stress/runners/run_simple_stress_tests.py

# Medium tests only (10-15 minutes)
python tests/stress/runners/run_medium_stress_tests.py

# Complex tests only (15-25 minutes)
python tests/stress/runners/run_complex_stress_tests.py

# All tests (30-40 minutes)
python tests/stress/runners/run_all_stress_tests.py

# Verify configuration only (no tests run)
python tests/stress/runners/run_simple_stress_tests.py --verify-only
```

### Run Legacy Test Suites

```bash
cd tests/stress

# Run adaptive tests (recommended for legacy)
python runners/adaptive.py

# Run basic tests
python runners/basic.py

# Run with specific config
python runners/adaptive.py --config configs/safe.json
```

## Test Results

### NEW Categorized Tests
Reports are saved directly in the `tests/stress/reports/` directory:
- `simple_stress_tests_report.md` - Results from simple test suite
- `medium_stress_tests_report.md` - Results from medium test suite  
- `complex_stress_tests_report.md` - Results from complex test suite
- `all_stress_tests_report.md` - Comprehensive results from all categories

Each report includes:
- Executive summary with success rates
- Individual test results with timings
- Pattern matching results
- Error details for failures
- Performance statistics
- Resource usage (complex/all tests only)

### Legacy Tests
All legacy results are saved to `/test_results/stress/`:
- `reports/` - HTML/Markdown formatted reports
- `logs/` - Raw output logs
- `metrics/` - JSON metrics and summaries

## Configuration Files

### configs/
- **adaptive.json** - Standard suite for adaptive runner (not used yet - uses basic.json)
- **basic.json** - Standard test suite with various complexities
- **safe.json** - Conservative tests that avoid rate limits
- **extended.json** - Extended comprehensive test suite
- **minimal.json** - Minimal tests for quick validation
- **compliant.json** - Tests following strict compliance rules
- **self_reflecting.json** - Tests with self-reflection patterns

## Runners

### runners/
- **adaptive.py** - Detects errors and retries with modified prompts
- **basic.py** - Standard test execution
- **redis.py** - Test runner with Redis timing integration
- **comprehensive.py** - Full WebSocket stress test suite
- **final.py** - Final validation runner

## Prompts

### prompts/
- **main.md** - Primary stress test prompt template
- **extended.md** - Extended test scenarios
- **recovery.md** - Tests with recovery mechanisms
- **self_reflecting_patterns.md** - Template patterns for self-reflection
- **timeout_recovery_patterns.md** - Patterns for handling timeouts

## Key Features

### Token Limit Detection
The WebSocket handler detects token limit errors and sends notifications:
```json
{
  "method": "error.token_limit_exceeded",
  "params": {
    "limit": 32000,
    "message": "Claude's output exceeded 32000 token limit",
    "suggestion": "Retry with a more concise prompt"
  }
}
```

### Adaptive Retry
The adaptive runner automatically retries with:
1. "Please be concise" addition
2. Specific word limits
3. Request for outline/summary only

## Utilities

### utils/
- **websocket_validator.py** - Validate WebSocket connections
- **markdown_report_generator.py** - Generate formatted reports
- **enhanced_handler_test.py** - Test enhanced features
- **quick_test.py** - Quick validation checks

## Best Practices

1. **Use Adaptive Runner**: Handles errors gracefully (for legacy tests)
2. **Start with Simple Tests**: Verify basic functionality first
3. **Check Reports**: Review markdown reports in `tests/stress/reports/`
4. **Monitor Resources**: Complex tests use psutil for resource tracking
5. **Use Execution Markers**: Each run has unique ID for transcript verification

## Example Test Content

### Simple Tests (5-30s each)
- "What is 2+2?"
- "What is the 10th Fibonacci number?"
- Basic echo and date commands

### Medium Tests (30-90s each)
- "What is a Python function to reverse a string?"
- "What is a collection of 5 haikus about programming?"
- "What is a quick chicken and rice recipe that takes 30 minutes?"

### Complex Tests (90-300s each)
- "What is a 500-word checklist for Python best practices in production?"
- "What is a 2000 word essay about the history of programming languages?"
- "What is a comprehensive guide to async/await in Python with 5 examples?"

## Troubleshooting

### Common Issues
1. **Connection refused**: Ensure cc_executor is running on localhost:8000
2. **Timeouts**: Complex tests may timeout on slower systems - increase timeout in JSON
3. **Pattern matching failures**: Check if Claude's output format has changed
4. **Resource errors**: Install psutil: `pip install psutil`

### Debugging Tips
- Progress updates shown every 10s for long tests
- Check execution markers in transcripts for verification
- Use `--verify-only` flag to validate configs without running tests
- Review individual category results before running all tests