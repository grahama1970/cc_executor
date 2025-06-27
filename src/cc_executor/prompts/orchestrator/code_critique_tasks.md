# Code Critique Tasks for CC-Executor

## 🔴 SELF-IMPROVEMENT RULES
This prompt MUST follow the self-improvement protocol:
1. Every failure updates metrics immediately
2. Every failure fixes the root cause
3. Every failure adds a recovery test
4. Every change updates evolution history

## 🎮 GAMIFICATION METRICS
- **Success**: 0
- **Failure**: 0
- **Total Executions**: 0
- **Last Updated**: 2025-06-26
- **Success Ratio**: N/A (need 10:1 to graduate)

## Evolution History
- v1: Initial implementation of code critique tasks

## PURPOSE
Provide comprehensive code critique tasks for the CC-Executor codebase to test:
1. Code analysis capabilities
2. Security review features
3. Performance optimization suggestions
4. Architecture improvements
5. Best practices enforcement

## TASK LIST

```json
{
  "task_list_id": "CODE_CRITIQUE_TASKS_20250626",
  "description": "Code critique and analysis tasks for cc-executor",
  "endpoint": "/ws/mcp",
  "categories": {
    "security_review": {
      "description": "Security-focused code analysis",
      "tasks": [
        {
          "id": "sec_1",
          "name": "command_injection_check",
          "request": "Review /home/graham/workspace/experiments/cc_executor/src/cc_executor/core/process_manager.py for command injection vulnerabilities. Check how user input is handled in execute_command method.",
          "expected_findings": [
            "subprocess usage",
            "shell=False",
            "command validation",
            "ALLOWED_COMMANDS"
          ]
        },
        {
          "id": "sec_2",
          "name": "websocket_auth_review",
          "request": "Analyze the WebSocket authentication in /home/graham/workspace/experiments/cc_executor/src/cc_executor/core/websocket_handler.py. Are there any security concerns with the current implementation?",
          "expected_findings": [
            "authentication",
            "session management",
            "origin validation",
            "rate limiting"
          ]
        },
        {
          "id": "sec_3",
          "name": "path_traversal_check",
          "request": "Check for path traversal vulnerabilities in the codebase. Focus on any file operations or path handling.",
          "expected_findings": [
            "path validation",
            "directory traversal",
            "../",
            "absolute paths"
          ]
        }
      ]
    },
    "performance_analysis": {
      "description": "Performance and optimization reviews",
      "tasks": [
        {
          "id": "perf_1",
          "name": "stream_buffer_analysis",
          "request": "Analyze the stream buffering implementation in /home/graham/workspace/experiments/cc_executor/src/cc_executor/core/stream_handler.py. Are there potential memory leaks or performance bottlenecks?",
          "expected_findings": [
            "buffer size",
            "memory management",
            "cleanup",
            "MAX_BUFFER_SIZE"
          ]
        },
        {
          "id": "perf_2",
          "name": "async_optimization",
          "request": "Review the async/await usage across the codebase. Are there any blocking operations that should be made async? Check for proper async patterns.",
          "expected_findings": [
            "asyncio",
            "await",
            "blocking operations",
            "concurrent execution"
          ]
        },
        {
          "id": "perf_3",
          "name": "session_scalability",
          "request": "Evaluate the session management scalability in session_manager.py. How many concurrent sessions can it handle? What are the bottlenecks?",
          "expected_findings": [
            "MAX_SESSIONS",
            "memory per session",
            "cleanup strategy",
            "concurrent limits"
          ]
        }
      ]
    },
    "architecture_review": {
      "description": "Architecture and design pattern analysis",
      "tasks": [
        {
          "id": "arch_1",
          "name": "dependency_analysis",
          "request": "Analyze the module dependencies in the cc_executor/core directory. Are there any circular dependencies or tight coupling issues?",
          "expected_findings": [
            "import structure",
            "circular imports",
            "coupling",
            "dependency injection"
          ]
        },
        {
          "id": "arch_2",
          "name": "error_handling_patterns",
          "request": "Review error handling patterns across all modules. Is error handling consistent? Are errors properly propagated to clients?",
          "expected_findings": [
            "try/except",
            "error propagation",
            "client notification",
            "error types"
          ]
        },
        {
          "id": "arch_3",
          "name": "testability_assessment",
          "request": "Assess the testability of the codebase. Which modules are hardest to test and why? Suggest improvements.",
          "expected_findings": [
            "mocking points",
            "dependency injection",
            "test coverage",
            "integration points"
          ]
        }
      ]
    },
    "code_quality": {
      "description": "General code quality and best practices",
      "tasks": [
        {
          "id": "qual_1",
          "name": "type_hints_review",
          "request": "Check type hint coverage across the codebase. Which functions are missing type hints? Are the existing type hints accurate?",
          "expected_findings": [
            "missing type hints",
            "-> None",
            "Dict[str, Any]",
            "Optional"
          ]
        },
        {
          "id": "qual_2",
          "name": "docstring_quality",
          "request": "Evaluate the docstring quality in main.py and process_manager.py. Do they follow Google/NumPy style? Are examples provided?",
          "expected_findings": [
            "Args:",
            "Returns:",
            "Example:",
            "docstring format"
          ]
        },
        {
          "id": "qual_3",
          "name": "logging_consistency",
          "request": "Review logging practices across all modules. Is logging consistent? Are log levels appropriate? Any sensitive data being logged?",
          "expected_findings": [
            "logger.info",
            "logger.error",
            "log levels",
            "sensitive data"
          ]
        }
      ]
    },
    "refactoring_opportunities": {
      "description": "Identify refactoring opportunities",
      "tasks": [
        {
          "id": "refactor_1",
          "name": "duplicate_code_detection",
          "request": "Find duplicate code patterns across the codebase. Which code blocks could be extracted into shared functions?",
          "expected_findings": [
            "similar patterns",
            "repeated logic",
            "extraction opportunities",
            "DRY principle"
          ]
        },
        {
          "id": "refactor_2",
          "name": "complex_function_analysis",
          "request": "Identify the most complex functions in the codebase (high cyclomatic complexity). Which functions should be broken down?",
          "expected_findings": [
            "nested conditions",
            "long functions",
            "multiple responsibilities",
            "complexity metrics"
          ]
        },
        {
          "id": "refactor_3",
          "name": "naming_conventions",
          "request": "Review naming conventions across the codebase. Are variable/function names clear and consistent? Any misleading names?",
          "expected_findings": [
            "snake_case",
            "descriptive names",
            "consistency",
            "clarity"
          ]
        }
      ]
    }
  },
  "execution_config": {
    "timeout_per_task": 300,
    "max_retries": 2,
    "verification_enabled": true
  }
}
```

## USAGE

```bash
# Extract and run code critique tasks
cd /home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/orchestrator

# Generate unique marker for verification
MARKER="CODE_CRITIQUE_$(date +%Y%m%d_%H%M%S)"
echo "$MARKER"

# Run a specific security review task
python -c "
import json
with open('code_critique_tasks.md', 'r') as f:
    content = f.read()
    json_str = content.split('\`\`\`json')[1].split('\`\`\`')[0]
    tasks = json.loads(json_str)
    
# Example: Run command injection check
task = tasks['categories']['security_review']['tasks'][0]
print(f\"Task: {task['name']}\")
print(f\"Request: {task['request']}\")
"

# Verify execution
python /home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/commands/transcript_helper.py "$MARKER"
```

## EXPECTED INSIGHTS

Each task should produce:
1. **Specific findings** with file locations and line numbers
2. **Risk assessment** (Critical/High/Medium/Low)
3. **Recommended fixes** with code examples
4. **Best practice references** when applicable

## VERIFICATION APPROACH

Since these are code analysis tasks, verification involves:
1. Checking that files were actually read
2. Verifying specific patterns were found
3. Ensuring recommendations are actionable
4. Confirming no hallucinated file contents

## INTEGRATION WITH STRESS TESTS

These tasks can be integrated into the stress test framework by:
1. Converting requests to WebSocket messages
2. Capturing full analysis responses
3. Verifying against expected findings
4. Measuring analysis depth and accuracy