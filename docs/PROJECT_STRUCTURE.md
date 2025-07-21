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
