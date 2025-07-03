# User and Developer Guides

This directory contains practical guides for operating, developing, and troubleshooting CC Executor.

## For Operators

- **[OPERATING_THE_SERVICE.md](OPERATING_THE_SERVICE.md)** - Complete guide for production deployment
  - System requirements
  - Installation steps
  - Configuration options
  - Monitoring and maintenance

- **[troubleshooting.md](troubleshooting.md)** - Comprehensive troubleshooting guide
  - Common issues and solutions
  - Debug techniques
  - Log analysis
  - Performance optimization

## For Developers

- **[development_workflow.md](development_workflow.md)** - Development best practices
  - Code review process
  - Testing strategies
  - Contributing guidelines

- **[vscode_debugging.md](vscode_debugging.md)** - Advanced debugging with VSCode
  - Launch configurations
  - Breakpoint strategies
  - Debug console usage

- **[timeout_configuration.md](timeout_configuration.md)** - Managing timeouts
  - Agent-specific configuration
  - Dynamic timeout adjustment
  - ACK pattern implementation

## Quick Reference

### Most Common Issues
1. Process hanging → See troubleshooting.md #stdin-deadlock
2. WebSocket drops → See troubleshooting.md #connection-timeouts
3. Large output issues → See timeout_configuration.md #buffer-management

### Essential Commands
```bash
# Start server
python core/websocket_handler.py --serve

# Enable debug logging
LOG_LEVEL=DEBUG python core/websocket_handler.py --serve

# Run tests
python core/websocket_handler.py --serve --auto-demo --test-case simple
```

Last updated: 2025-07-02