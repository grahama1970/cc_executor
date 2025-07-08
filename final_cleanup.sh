#!/bin/bash
# Final cleanup - remove empty directories and archive duplicate cc_execute files

set -e

echo "=== Final Cleanup ==="
echo

# Archive duplicate cc_execute files
ARCHIVE_DIR="/home/graham/workspace/experiments/cc_executor/archive/cleanup_20250708/duplicate_cc_execute"
mkdir -p "$ARCHIVE_DIR"

echo "=== Archiving Duplicate cc_execute.py Files ==="
echo "The canonical version is: src/cc_executor/client/cc_execute.py"
echo

if [ -f "src/cc_executor/prompts/cc_execute.py" ]; then
    echo "Moving duplicate: src/cc_executor/prompts/cc_execute.py"
    mv "src/cc_executor/prompts/cc_execute.py" "$ARCHIVE_DIR/"
fi

if [ -f "src/cc_executor/prompts/commands/cc_execute.py" ]; then
    echo "Moving duplicate: src/cc_executor/prompts/commands/cc_execute.py"
    mv "src/cc_executor/prompts/commands/cc_execute.py" "$ARCHIVE_DIR/"
fi

echo
echo "=== Removing Empty Directories ==="
# Remove empty directories
find src/cc_executor -type d -empty -print -delete

echo
echo "=== Checking for More Cleanup Opportunities ==="

# Check for __pycache__ directories
PYCACHE_COUNT=$(find . -name "__pycache__" -type d | wc -l)
if [ $PYCACHE_COUNT -gt 0 ]; then
    echo "Found $PYCACHE_COUNT __pycache__ directories"
    echo "Run: find . -name '__pycache__' -type d -exec rm -rf {} +"
fi

# Check for .pyc files
PYC_COUNT=$(find . -name "*.pyc" | wc -l)
if [ $PYC_COUNT -gt 0 ]; then
    echo "Found $PYC_COUNT .pyc files"
    echo "Run: find . -name '*.pyc' -delete"
fi

echo
echo "=== Creating Project Structure Documentation ==="

# Create updated project structure
cat > "PROJECT_STRUCTURE.md" << 'EOF'
# CC Executor Project Structure

Updated: $(date)

## Core Directories

```
cc_executor/
├── src/cc_executor/
│   ├── __init__.py          # Main package entry point
│   ├── client/              # Python client API
│   │   ├── cc_execute.py    # Main execution interface (CANONICAL)
│   │   └── README.md        # Client documentation
│   ├── core/                # Core execution engine
│   │   ├── executor.py      # Core executor logic
│   │   ├── process_manager.py # Process management
│   │   ├── session_manager.py # Session handling
│   │   └── websocket_handler.py # WebSocket interface
│   ├── hooks/               # Hook system
│   │   └── hook_integration.py # Hook integration logic
│   ├── prompts/             # Prompt handling
│   │   └── redis_task_timing.py # Task timing with Redis
│   ├── servers/             # MCP servers
│   │   └── mcp_cc_execute_enhanced.py # Enhanced MCP server
│   └── utils/               # Utilities
│       ├── json_utils.py    # JSON parsing utilities
│       └── prompt_amender.py # Prompt amendment logic
├── tests/                   # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   ├── proof_of_concept/   # POC tests
│   ├── stress/             # Stress testing framework
│   └── apps/               # Test applications
├── docs/                    # Documentation
├── deployment/              # Deployment configurations
└── archive/                 # Archived/deprecated files
```

## Key Files

- **Main Entry Point**: `src/cc_executor/__init__.py`
- **Python API**: `src/cc_executor/client/cc_execute.py`
- **Core Engine**: `src/cc_executor/core/executor.py`
- **WebSocket Handler**: `src/cc_executor/core/websocket_handler.py`
- **Hook System**: `src/cc_executor/hooks/hook_integration.py`

## Archived Files

All deprecated and unreferenced files have been moved to:
- `/archive/cleanup_20250708/` - Contains 43 archived files

## Testing

- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- Stress tests: `tests/stress/`
- Test apps: `tests/apps/`
EOF

echo
echo "✅ Final cleanup complete!"
echo
echo "Summary:"
echo "- Archived duplicate cc_execute.py files"
echo "- Removed empty directories"
echo "- Created PROJECT_STRUCTURE.md"
echo
echo "Recommended next steps:"
echo "1. Remove __pycache__ directories: find . -name '__pycache__' -type d -exec rm -rf {} +"
echo "2. Remove .pyc files: find . -name '*.pyc' -delete"
echo "3. Review and commit: git add -A && git commit -m 'Complete project cleanup: archive deprecated files and remove duplicates'"
echo "4. Run tests to ensure everything still works: cd tests && python -m pytest"