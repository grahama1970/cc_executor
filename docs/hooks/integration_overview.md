# Anthropic Hooks Integration for cc_executor

## Overview

This document describes the integration of Anthropic Claude Code hooks into the cc_executor system. Hooks provide deterministic control points during task execution, enabling better timeout prediction, sequential task management, automated code review, and self-reflection capabilities.

## Architecture

### Hook Types

1. **pre-edit**: Analyzes task complexity before execution
2. **post-edit**: Reviews code changes for quality and security  
3. **pre-tool**: Validates task dependencies and system state
4. **post-tool**: Updates task completion status
5. **post-output**: Records execution metrics and triggers reflection

### Integration Points

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Task List │────▶│  WebSocket   │────▶│   Claude    │
│             │     │   Handler    │     │  Instance   │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────▼───────┐
                    │    Hooks     │
                    │ Integration  │
                    └──────┬───────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼─────┐    ┌──────▼───────┐   ┌─────▼──────┐
   │  Redis   │    │  Perplexity  │   │   Static   │
   │ Timeout  │    │    Review    │   │  Analysis  │
   └──────────┘    └──────────────┘   └────────────┘
```

## Configuration

### `.claude-hooks.json`

```json
{
  "hooks": {
    "pre-edit": "python /path/to/analyze_task_complexity.py '$CLAUDE_FILE'",
    "post-edit": "python /path/to/review_code_changes.py '$CLAUDE_FILE' '$CLAUDE_DIFF'",
    "pre-tool": "python /path/to/check_task_dependencies.py '$CLAUDE_CONTEXT'",
    "post-tool": "python /path/to/update_task_status.py '$CLAUDE_TASK' '$CLAUDE_EXIT_CODE'",
    "post-output": "python /path/to/record_execution_metrics.py '$CLAUDE_OUTPUT' '$CLAUDE_DURATION' '$CLAUDE_TOKENS'"
  },
  "timeout": 60,
  "parallel": false,
  "env": {
    "REDIS_HOST": "localhost",
    "REDIS_PORT": "6379"
  }
}
```

## Hook Handlers

### 1. Task Complexity Analysis (`analyze_task_complexity.py`)

**Purpose**: Estimates task complexity and timeout requirements using BM25 similarity search.

**Features**:
- Extracts task descriptions from files
- Searches historical task data using BM25
- Provides complexity classification (simple/medium/complex)
- Suggests timeout based on similar tasks
- Falls back to keyword analysis if BM25 unavailable

**Output**:
```json
{
  "estimated_timeout": 120,
  "complexity": "medium",
  "based_on": "3 similar tasks",
  "confidence": 0.85
}
```

### 2. Task Dependency Checking (`check_task_dependencies.py`)

**Purpose**: Ensures task dependencies are met before execution.

**Features**:
- Validates previous tasks completed successfully
- Checks WebSocket handler readiness
- Monitors system resources (CPU, memory)
- Blocks execution if dependencies not met

**Exit Codes**:
- 0: All dependencies satisfied
- 1: Dependencies not met (blocks execution)

### 3. Task Status Updates (`update_task_status.py`)

**Purpose**: Records task completion and triggers improvements.

**Features**:
- Updates task status in Redis
- Calculates success rates
- Triggers self-improvement for failures
- Maps exit codes to improvement strategies

**Improvement Strategies**:
- Exit code 124 (timeout): Increase timeout or use cc_execute.md
- Exit code 137 (killed): Reduce complexity, check memory
- Token limit errors: Break into subtasks

### 4. Execution Metrics (`record_execution_metrics.py`)

**Purpose**: Analyzes output quality and performance.

**Features**:
- Quality scoring (0-1 scale)
- Error detection (token limits, syntax errors)
- Performance rating (fast/normal/slow)
- Triggers reflection for poor quality

**Metrics Collected**:
- Duration and token count
- Output completeness
- Error types
- Quality score

### 5. Code Review (`review_code_changes.py`)

**Purpose**: Automated code review using perplexity-ask.

**Features**:
- Security vulnerability detection
- Performance issue identification  
- Code quality checks
- Fallback static analysis

**Review Categories**:
- Security (command injection, hardcoded secrets)
- Correctness (logic errors, missing error handling)
- Performance (inefficient algorithms, blocking I/O)
- Code quality (idioms, naming, duplication)

## WebSocket Integration

### New Methods

1. **Hook Status Query**:
```json
{
  "jsonrpc": "2.0",
  "method": "hook_status",
  "id": 1
}
```

Response:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "enabled": true,
    "hooks_configured": ["pre-edit", "post-edit", "pre-tool", "post-tool", "post-output"],
    "recent_executions": [...],
    "statistics": {...}
  },
  "id": 1
}
```

### Enhanced Execution Flow

1. **Pre-execution**:
   - Hook-based complexity analysis
   - Dependency validation
   - Timeout estimation

2. **During execution**:
   - Output collection for hooks
   - Real-time error detection

3. **Post-execution**:
   - Metrics recording
   - Quality analysis
   - Self-improvement triggers

## Usage Examples

### 1. Simple Command Execution
```python
# WebSocket request
{
  "jsonrpc": "2.0",
  "method": "execute",
  "params": {
    "command": "echo 'Hello World'"
  },
  "id": 1
}

# Hooks automatically:
# - Analyze complexity (simple, 60s timeout)
# - Check dependencies
# - Record metrics
# - Skip code review (no file changes)
```

### 2. Complex Task Execution
```python
# Task list with cc_execute.md
"What is a FastAPI endpoint that handles file uploads with progress tracking?"

# Hooks automatically:
# - Detect complex task (300s timeout)
# - Validate WebSocket ready
# - Review generated code
# - Trigger improvements if needed
```

### 3. Failed Task Improvement
```python
# Task fails with timeout
Exit code: 124

# Hooks automatically:
# - Record failure metrics
# - Suggest: "Increase timeout or use cc_execute.md"
# - Update task list evolution history
# - Queue for retry with improvements
```

## Benefits

1. **Better Timeout Prediction**:
   - Historical data analysis
   - BM25 similarity matching
   - 50% buffer for safety

2. **Reliable Sequential Execution**:
   - Dependency validation
   - WebSocket status checks
   - Resource monitoring

3. **Automated Code Review**:
   - Security vulnerability detection
   - Performance analysis
   - Quality suggestions

4. **Self-Reflection**:
   - Quality scoring
   - Failure analysis
   - Improvement suggestions

5. **Deterministic Control**:
   - Shell commands for reliability
   - 60-second timeout per hook
   - Non-blocking execution

## Troubleshooting

### Hooks Not Executing

1. Check `.claude-hooks.json` exists in project root
2. Verify hook scripts are executable (`chmod +x`)
3. Check WebSocket logs for hook errors
4. Test hooks manually: `python analyze_task_complexity.py test.md`

### Timeout Estimation Issues

1. Ensure Redis is running
2. Check historical data exists: `redis-cli hgetall task:history`
3. Verify BM25 installed: `pip install rank-bm25`
4. Check fallback keyword analysis working

### Code Review Failures

1. Verify perplexity-ask MCP tool available
2. Check API limits not exceeded
3. Test static analysis fallback
4. Review logs at `/logs/code_reviews.log`

## Future Enhancements

1. **Parallel Hook Execution**: Run independent hooks concurrently
2. **Custom Hook Types**: User-defined lifecycle points
3. **Hook Chaining**: Output of one hook as input to another
4. **Visual Dashboard**: Real-time hook execution monitoring
5. **ML-Based Predictions**: Learn from hook data for better estimates