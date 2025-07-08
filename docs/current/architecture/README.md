# Architecture Documentation

This directory contains documentation about the system architecture and design of CC Executor.

## Overview

CC Executor uses a WebSocket-based architecture to provide real-time command execution and streaming output. The system is designed to handle long-running Claude operations while maintaining connection stability and providing progress feedback.

## Documents

- **[how_claude_sees_code.md](how_claude_sees_code.md)** - Conceptual overview of how the system processes and executes commands
- **[websocket_mcp_protocol.md](websocket_mcp_protocol.md)** - Complete WebSocket Model Context Protocol specification
- **[orchestration_control_patterns.md](orchestration_control_patterns.md)** - Patterns for controlling execution flow
- **[orchestrator_decision_flow.md](orchestrator_decision_flow.md)** - Decision logic for orchestration
- **[orchestrator_websocket_usage.md](orchestrator_websocket_usage.md)** - WebSocket integration with orchestrator
- **[websocket_commands_detailed.md](websocket_commands_detailed.md)** - Detailed command reference
- **[websocket_limitations.md](websocket_limitations.md)** - Known limitations and workarounds

## Key Concepts

### WebSocket Model Context Protocol (MCP)
The core protocol that enables:
- Real-time bidirectional communication
- Streaming command output
- Process control (pause/resume/cancel)
- Session management

### Orchestration Patterns
Strategies for managing complex multi-step operations:
- Sequential execution
- Parallel task management
- Error recovery
- Progress tracking

### Connection Management
How the system maintains stable connections:
- WebSocket ping/pong for keepalive
- Automatic reconnection
- Timeout handling
- Buffer management

Last updated: 2025-07-02