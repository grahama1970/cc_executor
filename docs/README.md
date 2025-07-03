# CC Executor Documentation

Welcome to the CC Executor documentation. This guide helps you navigate the documentation structure and find the information you need.

## Quick Links

- [Quickstart Guide](quickstart.md) - Get up and running quickly
- [Operating the Service](guides/OPERATING_THE_SERVICE.md) - Production deployment guide
- [Troubleshooting](guides/troubleshooting.md) - Common issues and solutions
- [Prompt Best Practices](PROMPT_BEST_PRACTICES.md) - Guidelines for effective prompting

## Documentation Structure

### Core Documentation
- **[LESSONS_LEARNED.md](LESSONS_LEARNED.md)** - Critical operational insights from production experience
- **[KNOWN_ISSUES.md](KNOWN_ISSUES.md)** - Current issues and workarounds
- **[PROMPT_BEST_PRACTICES.md](PROMPT_BEST_PRACTICES.md)** - Essential prompting guidelines
- **[FAVORITES.md](FAVORITES.md)** - Quick reference links

### Architecture
Documentation about system design and implementation:
- **[Overview](architecture/how_claude_sees_code.md)** - Conceptual understanding
- **[WebSocket MCP Protocol](architecture/websocket_mcp_protocol.md)** - Complete protocol specification
- **[Orchestration Patterns](architecture/orchestration_control_patterns.md)** - Control flow patterns
- **[WebSocket Limitations](architecture/websocket_limitations.md)** - Known limitations

### Guides
Practical guides for users and developers:
- **[Operating the Service](guides/OPERATING_THE_SERVICE.md)** - Production deployment
- **[Troubleshooting](guides/troubleshooting.md)** - Debugging and problem solving
- **[VSCode Debugging](guides/vscode_debugging.md)** - Advanced debugging with VSCode
- **[Timeout Configuration](guides/timeout_configuration.md)** - Managing timeouts
- **[Development Workflow](guides/development_workflow.md)** - Development best practices

### Hook System
Complete documentation for the hook integration system:
- **[Hook System Overview](hooks/README.md)** - Comprehensive guide
- **[Usage Guide](hooks/usage_guide.md)** - How to use hooks
- **[Examples](hooks/examples.md)** - Practical hook examples
- **[Integration](hooks/integration_overview.md)** - Integration details
- **[Execution Flow](hooks/execution_flow.md)** - How hooks execute
- **[Reliability Patterns](hooks/reliability_patterns.md)** - Ensuring reliable hook execution

### Technical Reference
Deep technical documentation:
- **[Timeout Management](technical/timeout_management.md)** - Complete timeout handling guide
- **[Asyncio Timeout Guide](technical/asyncio_timeout_guide.md)** - Async-specific timeout handling
- **[Environment Variables](technical/environment_variables.md)** - Configuration options
- **[Logging Guide](technical/logging_guide.md)** - Comprehensive logging documentation
- **[Resource Monitoring](technical/resource_monitoring.md)** - System resource tracking
- **[Redis Integration](technical/redis_integration.md)** - Redis features and usage
- **[Transcript Limitations](technical/transcript_limitations.md)** - Known transcript issues

### Features
Documentation for specific features:
- **[Research Collaborator](features/research_collaborator.md)** - Research collaboration patterns
- **[Unified Research Architecture](features/unified_research_architecture.md)** - Research system design

### Templates
Prompt and code templates:
- **[Self-Improving Prompt Template](templates/SELF_IMPROVING_PROMPT_TEMPLATE.md)** - Template for self-improving prompts
- **[Prompt System Guidelines](templates/PROMPT_SYSTEM_GUIDELINES.md)** - Guidelines for prompt systems
- **[Review Template](templates/REVIEW_PROMPT_AND_CODE_TEMPLATE.md)** - Code review templates
- **[Reasonable Output Assessment](templates/REASONABLE_OUTPUT_ASSESSMENT.md)** - Output evaluation guide
- **[Task List Template](templates/SELF_IMPROVING_TASK_LIST_TEMPLATE.md)** - Task list patterns

### Reports
Test results and analyses:
- **[Full Stress Test Report](FULL_STRESS_TEST_REPORT_FINAL.md)** - Comprehensive stress test results
- **[Extended Stress Test Analysis](reports/extended_stress_test_timeout_analysis.md)** - Timeout analysis
- **[Matrix Multiplication Analysis](reports/matrix_multiplication_analysis_final.md)** - Performance benchmarks

## Getting Started

1. **New Users**: Start with the [Quickstart Guide](quickstart.md)
2. **Developers**: Read [Development Workflow](guides/development_workflow.md) and [Architecture Overview](architecture/how_claude_sees_code.md)
3. **Operations**: See [Operating the Service](guides/OPERATING_THE_SERVICE.md) and [Environment Variables](technical/environment_variables.md)
4. **Debugging**: Check [Troubleshooting](guides/troubleshooting.md) and [Logging Guide](technical/logging_guide.md)

## Key Concepts

### WebSocket-Based Architecture
CC Executor uses WebSocket connections for real-time command execution and streaming output. See the [WebSocket MCP Protocol](architecture/websocket_mcp_protocol.md) for details.

### Hook System
The hook system allows integration with Claude's execution lifecycle. See [Hook System Overview](hooks/README.md) for comprehensive documentation.

### Timeout Management
Proper timeout handling is critical for long-running operations. See [Timeout Management](technical/timeout_management.md) for strategies and best practices.

### Logging Strategy
Multi-layered logging captures different aspects of system operation. See [Logging Guide](technical/logging_guide.md) for details.

## Contributing

When adding new documentation:
1. Place it in the appropriate category directory
2. Update this README with a link
3. Include a "Last updated" date at the bottom
4. Follow the existing format and style

## Archive

Historical documentation is preserved in the `archive/` directory, organized by date. This includes:
- Implementation notes from development
- Superseded guides and solutions
- Research reports that have been incorporated into the codebase

Last updated: 2025-07-02