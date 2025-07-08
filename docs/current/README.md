# CC Executor Documentation

Welcome to the CC Executor documentation. This directory contains all technical documentation, guides, and architectural decisions for the project.

## Quick Links

- **Getting Started**: [quickstart.md](quickstart.md)
- **Architecture Overview**: [architecture/README.md](architecture/README.md)
- **User Guides**: [guides/README.md](guides/README.md)
- **Hook System**: [hooks/README.md](hooks/README.md)

## Documentation Structure

### 📚 Core Documentation

- **[quickstart.md](quickstart.md)** - Get up and running quickly
- **[GAMIFICATION_EXPLAINED.md](GAMIFICATION_EXPLAINED.md)** - Understanding self-improving features
- **[LESSONS_LEARNED.md](LESSONS_LEARNED.md)** - Key insights from development
- **[KNOWN_ISSUES.md](KNOWN_ISSUES.md)** - Current limitations and workarounds
- **[MEMORY_OPTIMIZATION.md](MEMORY_OPTIMIZATION.md)** - Memory usage strategies
- **[FAVORITES.md](FAVORITES.md)** - Quick reference links

### 🏗️ Architecture (`architecture/`)

Technical architecture and design decisions:
- **[architecture/README.md](architecture/README.md)** - Architecture overview
- **[architecture/decisions/](architecture/decisions/)** - Key architectural decisions
  - `cc_execute_pattern.md` - The cc_execute pattern (like numpy vs math)
  - `mcp_evaluation.md` - Why prompts over MCP
  - `MCP_ARCHITECTURE_DECISION.md` - MCP integration analysis
  - `orchestrator_flexibility.md` - Tool integration patterns
- **Core Architecture Docs**:
  - `how_claude_sees_code.md` - Conceptual understanding
  - `websocket_mcp_protocol.md` - Protocol specification
  - `orchestration_control_patterns.md` - Control patterns
  - `websocket_limitations.md` - Known limitations

### 📖 Guides (`guides/`)

How-to guides and best practices:
- **[project_setup.md](guides/project_setup.md)** - Setting up new Python projects
- **[OPERATING_THE_SERVICE.md](guides/OPERATING_THE_SERVICE.md)** - Production deployment
- **[development_workflow.md](guides/development_workflow.md)** - Development process
- **[prompt_best_practices.md](guides/prompt_best_practices.md)** - Writing effective prompts
- **[troubleshooting.md](guides/troubleshooting.md)** - Common issues and solutions
- **[vscode_debugging.md](guides/vscode_debugging.md)** - Debugging with VS Code
- **[timeout_configuration.md](guides/timeout_configuration.md)** - Timeout management

### 🎯 Features (`features/`)

Feature-specific documentation:
- **[research_collaborator.md](features/research_collaborator.md)** - Research integration
- **[unified_research_architecture.md](features/unified_research_architecture.md)** - Research patterns

### 🪝 Hooks (`hooks/`)

Hook system documentation:
- **[hooks/README.md](hooks/README.md)** - Hook system overview
- **[UUID_VERIFICATION_HOOK.md](hooks/UUID_VERIFICATION_HOOK.md)** - UUID4 anti-hallucination
- **[uuid4_implementation_update.md](hooks/uuid4_implementation_update.md)** - Latest UUID4 updates
- **[execution_flow.md](hooks/execution_flow.md)** - How hooks execute
- **[usage_guide.md](hooks/usage_guide.md)** - Using hooks effectively
- **[reliability_patterns.md](hooks/reliability_patterns.md)** - Reliable execution

### 🔧 Technical (`technical/`)

Deep technical documentation:
- **[asyncio_timeout_guide.md](technical/asyncio_timeout_guide.md)** - Async timeout patterns
- **[redis_integration.md](technical/redis_integration.md)** - Redis usage
- **[timeout_management.md](technical/timeout_management.md)** - Timeout strategies
- **[resource_monitoring.md](technical/resource_monitoring.md)** - Resource tracking
- **[environment_variables.md](technical/environment_variables.md)** - Configuration
- **[logging_guide.md](technical/logging_guide.md)** - Logging system
- **[transcript_limitations.md](technical/transcript_limitations.md)** - Transcript issues

### 📝 Templates (`templates/`)

Reusable templates and patterns:
- **[task_list_guide.md](templates/task_list_guide.md)** - Creating task lists
- **[TEMPLATES_README.md](templates/TEMPLATES_README.md)** - Template overview
- Various code and prompt templates

### 📊 Reports (`reports/`)

Assessment and test reports:
- **[reports/README.md](reports/README.md)** - Report index
- **[FULL_STRESS_TEST_REPORT_FINAL.md](FULL_STRESS_TEST_REPORT_FINAL.md)** - Stress test results
- Comprehensive assessment reports
- Performance analyses

### 📦 Archive (`archive/`)

Historical documentation:
- **`2025-06/`** - June 2025 development history
- **`2025-07/`** - July 2025 updates
- **`deprecated/`** - Deprecated approaches and decisions
  - Old SDK comparisons
  - Superseded integration approaches
  - Historical architecture decisions

## Key Concepts

### The cc_execute Pattern

CC Executor provides an optional execution pattern for complex tasks. Think of it like numpy vs math:
- Use **direct execution** for simple tasks (like using Python's math module)
- Use **cc_execute** for complex tasks needing fresh context (like using numpy for matrices)

See [architecture/decisions/cc_execute_pattern.md](architecture/decisions/cc_execute_pattern.md) for details.

### Automatic Features

When using cc_execute, you get:
- **UUID4 verification** - Anti-hallucination hooks (always enabled)
- **Error recovery** - Automatic retries (3 attempts)
- **WebSocket reliability** - Long-running task support
- **Fresh context** - 200K tokens per task

## Recent Updates

- **2025-07-04**: Documentation reorganization for clarity
- **2025-07-04**: Simplified examples to basic/advanced patterns
- **2025-07-03**: Integrated automatic UUID4 hooks
- **2025-06-27**: WebSocket architecture finalized

## Finding Information

### By Topic
- **Installation & Setup** → [quickstart.md](quickstart.md)
- **Creating new projects** → [guides/project_setup.md](guides/project_setup.md)
- **How cc_execute works** → [architecture/](architecture/)
- **Writing task lists** → [templates/task_list_guide.md](templates/task_list_guide.md)
- **Debugging issues** → [guides/troubleshooting.md](guides/troubleshooting.md)
- **Hook system** → [hooks/](hooks/)

### By User Type
- **New Users** → Start with [quickstart.md](quickstart.md)
- **Developers** → See [guides/development_workflow.md](guides/development_workflow.md)
- **Architects** → Review [architecture/decisions/](architecture/decisions/)
- **Contributors** → Check [templates/](templates/) for patterns

## Contributing to Docs

When adding documentation:
1. Place it in the appropriate subdirectory
2. Update this README with a link
3. Follow existing naming conventions
4. Include practical examples
5. Save any outputs to prevent hallucination

## Questions?

- For bugs/issues → [KNOWN_ISSUES.md](KNOWN_ISSUES.md)
- For architecture → [architecture/README.md](architecture/README.md)
- For development → [guides/development_workflow.md](guides/development_workflow.md)

Last updated: 2025-07-04