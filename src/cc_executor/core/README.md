# Core Module - CC Executor WebSocket MCP Service

## Overview
The core module contains the essential components of the CC Executor WebSocket service. This service provides a WebSocket-based interface for executing commands with intelligent timeout management, process control, and stream handling.

## Architecture
```
core/
├── main.py                 # FastAPI WebSocket service entry point
├── config.py              # Configuration and environment variables
├── models.py              # Pydantic models for JSON-RPC protocol
├── session_manager.py     # WebSocket session lifecycle management
├── process_manager.py     # Process execution and control (SIGSTOP/SIGCONT/SIGTERM)
├── stream_handler.py      # Output streaming with back-pressure handling
├── websocket_handler.py   # WebSocket protocol and request routing
├── resource_monitor.py    # CPU/GPU monitoring for dynamic timeout adjustment
└── usage_helper.py        # Helper for capturing outputs (prevents AI hallucination)
```

## Key Features
1. **WebSocket MCP Protocol** - JSON-RPC 2.0 over WebSocket for tool communication
2. **Process Management** - Execute commands in isolated process groups with full control
3. **Stream Handling** - Real-time stdout/stderr streaming with proper buffering
4. **Dynamic Timeouts** - Adjusts timeouts based on system load (3x multiplier at 14% CPU/GPU)
5. **Session Management** - Thread-safe session tracking with automatic cleanup
6. **Response Saving** - All modules save execution outputs as JSON for verification

## Critical Design Decisions

### Response Saving Pattern
Every Python file MUST have an `if __name__ == "__main__":` block that:
1. Demonstrates the module's functionality
2. Saves output as prettified JSON (not plain text)
3. Uses `OutputCapture` helper for consistency
4. Enables self-improving prompts to verify execution

### Hook Integration
- Hooks from `../hooks/` are integrated at the subprocess level
- Manual workaround implemented for Claude Code (Anthropic hooks are broken)
- Environment setup happens before command execution

### Process Groups
- All processes run in separate process groups (os.setsid)
- Enables clean termination of entire process trees
- Prevents zombie processes

## Usage

### Starting the Service
```bash
python -m cc_executor.core.main
# or
python main.py
```

### Testing Individual Components
Each module can be tested independently:
```bash
python models.py          # Test data models
python process_manager.py # Test process control
python resource_monitor.py # Test resource monitoring
```

All outputs are saved to `tmp/responses/` as JSON files.

## Directory Structure
```
core/
├── docs/                   # All core documentation
│   ├── assessment/         # Self-assessment system docs
│   ├── architecture/       # System design documents
│   ├── guides/            # Development guides
│   └── api/               # API documentation
├── prompts/               # Self-assessment implementation
│   ├── ASSESS_ALL_CORE_USAGE.md  # Self-improving prompt
│   ├── scripts/                   # Assessment scripts
│   └── reports/                   # Assessment reports
├── tmp/
│   ├── responses/          # JSON outputs from module demos
│   ├── scripts_generated/  # Generated helper scripts
│   └── broken_files/       # Backup files from fixes
├── *.py                   # Core Python modules
└── README.md              # This file
```

## Documentation
For comprehensive documentation, see the [`docs/`](docs/) directory:
- [Assessment System](docs/assessment/README.md) - How self-assessment works
- [Architecture](docs/architecture/) - System design
- [Guides](docs/guides/) - Development patterns
- [API Reference](docs/api/) - Protocol documentation

## Integration Points
- **Hooks**: `../hooks/` - Pre/post execution hooks
- **Utilities**: `../utils/` - Shared utilities
- **Client**: `../client/` - WebSocket client implementation
- **Examples**: `../examples/` - Usage examples

## Testing
The self-improving prompt system (`prompts/ASSESS_ALL_CORE_USAGE.md`) tests all components by:
1. Running each module's `__main__` block
2. Reading saved JSON responses
3. Assessing output reasonableness
4. Tracking success/failure ratios

## Known Issues
1. Anthropic's subprocess hooks don't trigger (GitHub issue #2891)
2. Claude Max uses OAuth tokens, not API keys (SDK incompatible)
3. WebSocket handler requires manual hook setup for Claude commands

## Future Improvements
1. Complete migration to `OutputCapture` for all modules
2. Add WebSocket client reconnection logic
3. Implement distributed timeout estimation
4. Add metrics collection for performance monitoring