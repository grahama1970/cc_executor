# CC Executor Tests

All test code for the CC Executor project, organized by test type.

## Structure

```
tests/
├── stress/         # Stress tests for WebSocket handler
├── unit/          # Unit tests (to be added)
└── integration/   # Integration tests (to be added)
```

## Test Results

All test outputs are saved to `/test_results/`:

```
test_results/
├── stress/
│   ├── reports/   # Formatted HTML/Markdown reports
│   ├── logs/      # Raw output logs
│   └── metrics/   # JSON metrics
│
└── archive/       # Old test results
```

## Running Tests

### All Tests
```bash
# Run all tests with pytest
uv run pytest

# Run with coverage
uv run pytest --cov=src/cc_executor --cov-report=html

# Run specific test categories
uv run pytest tests/unit/
uv run pytest tests/integration/
uv run pytest tests/stress/
```

### Stress Tests (Standalone)
```bash
cd tests/stress
python runners/adaptive.py  # Recommended - handles errors gracefully
```

### Unit Tests
```bash
# Run all unit tests
uv run pytest tests/unit/

# Run specific unit test
uv run pytest tests/unit/test_hook_integration_security.py -v
```

### Integration Tests
```bash
# Run all integration tests
uv run pytest tests/integration/

# Run specific integration test
uv run pytest tests/integration/test_websocket_fixed.py -v
```

## Key Features

- **Organized by Type**: Configs, runners, and prompts in separate directories
- **Consistent Naming**: Related files share base names (e.g., `adaptive.json`, `adaptive.py`)
- **Clean Separation**: Test code in `/tests/`, results in `/test_results/`
- **No Source Pollution**: `/src/` contains only production code

## Documentation

See README.md in each test type directory for specific instructions.