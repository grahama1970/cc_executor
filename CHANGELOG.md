# Changelog

All notable changes to CC Executor will be documented in this file.

## [1.3.1] - 2025-01-14

### Added
- **WebSocket Heartbeat Mechanism**: 30-second heartbeat interval to detect and close dead connections
- **Message Queuing**: Automatic queuing of up to 100 messages per session when client is temporarily disconnected
- **Connection Timeout**: 10-second timeout on WebSocket accept to prevent hanging connections
- **Reconnection Token Support**: Clients can reconnect and receive queued messages within 5 minutes
- **Enhanced Message Handling**: All send methods now queue messages on failure for better reliability
- **Pong Message Support**: Added "pong" method handling in the message router

### Changed
- **WebSocket Resilience**: Improved connection handling based on patterns from claude-flow analysis
- **Connection Info**: Initial handshake now includes capabilities array
- **Error Recovery**: All WebSocket send operations now have fallback to message queuing
- **Session Cleanup**: Enhanced to include heartbeat tasks, message queues, and pong timestamps

### Fixed
- **Dead Connection Detection**: Server now properly detects and closes stale connections
- **Message Loss Prevention**: Messages are no longer lost during temporary disconnections
- **Connection Hanging**: WebSocket accept no longer hangs indefinitely

### Technical Details
- Heartbeat interval: 30 seconds
- Heartbeat timeout: 60 seconds (2x interval)
- Message queue max size: 100 messages per session
- Reconnection token timeout: 300 seconds (5 minutes)
- Connection accept timeout: 10 seconds

## [1.2.0] - 2025-01-08

### Fixed
- **Docker WebSocket streaming**: Fixed missing constants that prevented real-time output streaming
- **Docker port conflicts**: Changed WebSocket port to 8004 to avoid conflicts with local services
- **Docker authentication**: Documented that Claude CLI uses OAuth from mounted ~/.claude directory

### Changed
- **Docker status**: Promoted from experimental to production-ready
- **Port configuration**: Docker WebSocket now on port 8004 (was 8003)
- **Documentation**: Updated all Docker references to reflect OAuth authentication method

### Discovered
- Claude CLI in Docker uses OAuth credentials from `~/.claude/.credentials.json`, not API keys
- ANTHROPIC_API_KEY is not needed for Claude CLI operation
- Performance: 5-8 second response time is normal for Claude API calls

## [1.1.0] - 2025-01-08

### Added
- **Industry-standard `json_mode` parameter**: Replaces `return_json` (deprecated) to match OpenAI/LiteLLM conventions
- **Robust JSON parsing**: Automatic handling of markdown-wrapped JSON and malformed responses
- **Validation feature**: `validation_prompt` parameter spawns fresh Claude instance to validate results
- **Comprehensive test suite**: New integration test demonstrating MCP and Python API usage
- **Changelog**: This file to track version changes
- **Validation examples**: `examples/validation_pattern.py` shows orchestrator-controlled retry patterns
- **Tool limitation docs**: Documented that Claude CLI lacks Task/Todo/UI tools in best practices guide
- **Workaround examples**: `examples/cli_tool_limitations_workaround.py` shows how to handle missing tools

### Changed
- **Non-blocking async execution**: All subprocess calls now use `asyncio.create_subprocess_exec` 
  - Fixed event loop blocking in WebSocket handler (3 locations)
  - Fixed async-safe hook execution in process_manager.py
- **Import paths**: Canonical import is now `from cc_executor.client.cc_execute import cc_execute`
- **Documentation**: Updated README and Quick Start Guide with clearer examples
- **Report generation**: Extracted to separate `report_generator.py` module (Single Responsibility)
- **Validation design**: No internal retry - orchestrator controls retry logic (avoids hidden complexity)

### Fixed
- **Event loop blocking**: WebSocket server no longer freezes during hook execution
- **Hook integration**: Re-enabled hooks that were disabled with `if False` condition
- **Async compatibility**: Created separate sync/async hook methods to prevent blocking

### Removed
- **43 unreferenced files**: Archived to `/archive/cleanup_20250708/`
- **Duplicate implementations**: Removed redundant cc_execute.py files
- **Empty directories**: Cleaned up 13 empty directories
- **Python cache**: Removed 324 `__pycache__` directories and 2,203 `.pyc` files

### Deprecated
- **`return_json` parameter**: Use `json_mode` instead (backward compatible with warning)

## [1.0.0] - 2025-01-04

### Initial Release
- Python client API for Claude Code execution
- MCP WebSocket server for AI agent orchestration
- Sequential task execution with fresh context
- Hook system for pre/post execution
- Redis-based timeout estimation
- Process control (PAUSE/RESUME/CANCEL)
- Real-time output streaming
- Anti-hallucination measures with UUID verification