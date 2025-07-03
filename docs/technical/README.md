# Technical Reference Documentation

This directory contains in-depth technical documentation for CC Executor components and subsystems.

## Timeout and Async Operations

- **[timeout_management.md](timeout_management.md)** - Complete guide to timeout handling
  - Network, process, and application timeouts
  - ACK pattern implementation
  - Dynamic timeout adjustment
  - Production recommendations

- **[asyncio_timeout_guide.md](asyncio_timeout_guide.md)** - Asyncio-specific timeout handling
  - Stream timeout patterns
  - Subprocess management
  - Error recovery strategies

## Configuration and Monitoring

- **[environment_variables.md](environment_variables.md)** - All configuration options
  - Required variables
  - Optional settings
  - Performance tuning

- **[logging_guide.md](logging_guide.md)** - Comprehensive logging documentation
  - Multi-layer logging strategy
  - Log locations and formats
  - Transcript logging
  - Debug techniques

- **[resource_monitoring.md](resource_monitoring.md)** - System resource tracking
  - Memory usage patterns
  - CPU monitoring
  - Connection limits

## Integration

- **[redis_integration.md](redis_integration.md)** - Redis features and usage
  - Timeout coordination
  - Metrics storage
  - Session management

- **[transcript_limitations.md](transcript_limitations.md)** - Known transcript issues
  - Claude UI truncation
  - Workarounds
  - Full output capture

## Key Technical Concepts

### Stream Processing
How CC Executor handles large outputs:
- Chunked reading with configurable buffers
- Progress indicators for long operations
- Automatic truncation detection

### Process Management
Subprocess execution patterns:
- Proper stdin handling to prevent deadlocks
- Process group management for cleanup
- Signal handling for control operations

### Connection Stability
Maintaining stable WebSocket connections:
- Ping/pong frame handling
- Automatic reconnection logic
- Timeout cascade strategies

Last updated: 2025-07-02