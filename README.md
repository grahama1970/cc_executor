# CC-Executor

Model Context Protocol (MCP) WebSocket service for bidirectional communication with long-running Claude Code instances in Docker containers.

## Overview

CC-Executor solves the problem of reliable execution of complex tasks without timeouts, providing real-time control over process execution through:

- 🔌 **MCP WebSocket** - Bidirectional communication via JSON-RPC 2.0
- 🎮 **Process Control** - PAUSE/RESUME/CANCEL via OS signals
- 🛡️ **Back-Pressure Handling** - Prevents memory exhaustion from high-output processes
- 📊 **Gamification System** - Self-improving prompts with 10:1 success ratio requirement
- 🔍 **Anti-Hallucination** - Transcript verification for all executions

## Architecture

```
┌─────────────┐     WebSocket      ┌──────────────┐     Subprocess     ┌─────────────┐
│   Client    │ ◄─────────────────► │  MCP Service │ ◄─────────────────► │   Claude    │
│  (Claude)   │    JSON-RPC 2.0     │   (Python)   │    OS Signals      │    Code     │
└─────────────┘                     └──────────────┘                     └─────────────┘
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)
- uv package manager (optional)

### Running with Docker (Recommended)

```bash
# Clone repository
git clone <repository-url>
cd cc_executor/src/cc_executor

# Start the service
docker compose up -d

# Check health
curl http://localhost:8003/health

# View logs
docker logs -f cc_executor_mcp

# Test WebSocket connection
python -c "
import asyncio, websockets, json
async def test():
    async with websockets.connect('ws://localhost:8003/ws/mcp') as ws:
        print(json.loads(await ws.recv()))
asyncio.run(test())
"
```

### Running Locally (Development)

```bash
# Install dependencies
pip install -r src/cc_executor/requirements.txt

# Start MCP service
python src/cc_executor/core/implementation.py --port 8003
```

### Running Tests

```bash
# Run stress tests
cd src/cc_executor/tests/stress
python unified_stress_test_executor.py

# Run specific test category
python unified_stress_test_executor.py --categories simple parallel
```

## Project Structure

```
cc_executor/
├── src/                     # Core application source code
│   └── cc_executor/
│       ├── core/            # MCP WebSocket implementation
│       ├── tasks/           # Task implementations & workflows
│       │   ├── orchestrator/ # O3 reviews and fix tasks
│       │   └── executor/    # Claude's work in progress
│       ├── utils/           # Utility modules
│       ├── tests/stress/    # Stress tests
│       ├── prompts/         # Application prompts
│       ├── docs/            # Internal documentation
│       └── templates/       # Workflow templates
├── tests/                   # Standalone test files
├── scripts/                 # Utility and helper scripts
├── docs/                    # Project documentation
│   └── conversations/       # Important conversation logs
├── examples/                # Usage examples
├── prompts/                 # Self-improving prompts
├── logs/                    # Application logs (git-ignored)
├── test_outputs/            # Test run outputs (git-ignored)
├── archive/                 # Archived files (git-ignored)
├── CLAUDE.md               # Critical development rules
├── LOGGING.md              # Logging architecture
├── TRANSCRIPT_LOGGING.md   # Transcript logging solution
├── README.md               # This file
├── pyproject.toml          # Python project configuration
└── uv.lock                 # Dependency lock file
```

## Development Workflow

### For Implementers (Claude)

1. Read task from `docs/tasks/000_tasks_list.md`
2. Implement in `tasks/executor/`
3. Follow `templates/SELF_IMPROVING_PROMPT_TEMPLATE.md`
4. Test with usage functions and verify markers
5. Submit for review to `tasks/orchestrator/`

### For Reviewers (O3)

1. Read review request in `tasks/orchestrator/`
2. Execute implementation and verify functionality
3. Create structured feedback following `templates/REVIEW_PROMPT_AND_CODE_TEMPLATE.md`
4. Output fix tasks as JSON for Claude to implement

See `src/cc_executor/tasks/orchestrator/O3_REVIEW_CONTEXT.md` for detailed project context.

## Key Features

### Process Control
- Direct PAUSE/RESUME/CANCEL via OS signals (SIGSTOP/SIGCONT/SIGTERM)
- Process group management with `os.setsid()`
- Graceful cleanup on disconnection

### Back-Pressure Handling
- Configurable buffer limits (size and line count)
- Automatic dropping of old data when limits exceeded
- Metrics tracking for dropped data

### Security
- Command allow-list configuration
- Input validation on all requests
- Structured JSON logging with audit trail

## Task Status

### Completed
- ✅ T00 - Read & Understand
- ✅ T01 - Robust Logging
- ✅ T02 - Back-Pressure Handling
- ✅ T03 - WebSocket Stress Tests
- ✅ T05 - Security Pass
- ✅ 003 - WebSocket Reliability Fixes (All 6 critical fixes)
- ✅ Docker Deployment

### O3 Review Fixes Implemented
- ✅ Session Locking - Prevents race conditions
- ✅ Session Limit (100) - Prevents memory exhaustion
- ✅ Stream Timeout (5min) - Prevents hanging sessions
- ✅ Control Flow Bug - Fixed else block placement
- ✅ Partial Lines - Handles buffer overflow gracefully
- ✅ CancelledError - Allows proper cleanup

### Pending
- ⏳ T04 - CI Integration
- ⏳ T06 - Documentation Update (partially done)
- ⏳ T07 - Graduation Metrics
- ⏳ Code Refactoring (split 503-line implementation.py)

## Critical Notes

- **Reliability > Security** - Focus on robust long-running processes
- **No Heartbeat Needed** - Continuous streaming is implicit heartbeat
- **Verification Required** - All outputs must include traceable markers
- **10:1 Success Ratio** - Required for prompt graduation to production

## For Lost Context

If context is cleared, start with:
```bash
cat INSTRUCTIONS.md
```

This file contains complete recovery instructions and workflow guidelines.