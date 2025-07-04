# CC Executor Examples

This directory contains examples demonstrating how to use CC Executor effectively.

## Overview

CC Executor provides flexible task execution with two main patterns:

1. **Direct execution**: For simple tasks that don't need isolation
2. **cc_execute pattern**: For complex tasks needing fresh context, long-running support, and anti-hallucination verification

## Examples

### 1. Basic Usage (`basic_usage/`)

Demonstrates simple sequential task execution using cc_execute for all tasks.

**What it shows:**
- Sequential task execution 
- Building a TODO API step by step
- Automatic UUID4 verification
- Files building on previous outputs

**When to use this pattern:**
- Learning CC Executor
- Simple workflows where all tasks need isolation
- When you want automatic verification for everything

**Run it:**
```bash
cd basic_usage
python run_example.py
```

### 2. Advanced Usage (`advanced_usage/`)

Demonstrates the advanced patterns from the README, showing when to use cc_execute vs direct execution.

**What it shows:**
- Mixed execution patterns (direct + cc_execute)
- MCP tool integration (perplexity-ask)
- External model verification (gemini via LiteLLM)
- Complex sequential workflows
- Tool selection based on task needs

**When to use this pattern:**
- Production workflows
- Complex orchestration scenarios
- When you need to optimize execution
- Integrating multiple tools and models

**Run it:**
```bash
cd advanced_usage
python run_example.py
```

## Key Concepts

### When to Use cc_execute

Use cc_execute when you need:
- **Fresh 200K context**: Task requires full token window
- **Isolation**: No pollution from previous tasks
- **Long-running support**: Tasks over 1 minute
- **Complex generation**: Multi-file creation, architecture design
- **Anti-hallucination**: Automatic UUID4 verification

### When to Use Direct Execution

Use direct execution for:
- **Simple tool calls**: MCP tools like perplexity-ask
- **Quick queries**: Under 30 seconds
- **No isolation needed**: Task doesn't need fresh context
- **Chained operations**: When context accumulation is desired

## Features Comparison

| Feature | Direct Execution | cc_execute Pattern |
|---------|-----------------|-------------------|
| Fresh Context | ❌ | ✅ (200K tokens) |
| UUID4 Verification | ❌ | ✅ (automatic) |
| Long-running Support | ❌ | ✅ (WebSocket) |
| Error Recovery | ❌ | ✅ (3 retries) |
| Execution Speed | Fast | Slower (startup overhead) |
| Best For | Simple tasks | Complex generation |

## Architecture

All cc_execute features are automatic:
- **Pre-hooks**: Inject UUID4 requirements transparently
- **WebSocket**: Keeps connection alive for long tasks
- **Post-hooks**: Verify UUID4 presence in outputs
- **Error recovery**: Automatic retries for transient failures

## Tips

1. **Start Simple**: Use basic_usage to understand the flow
2. **Optimize Later**: Move to mixed patterns when needed
3. **Let CC Executor Handle Details**: UUID4, retries, etc. are automatic
4. **Choose the Right Tool**: Not every task needs cc_execute

## Common Patterns

### Research → Implementation → Review
```
1. Direct: Use perplexity-ask for research
2. cc_execute: Generate implementation with fresh context
3. cc_execute: Review with external model (fresh perspective)
```

### Parallel → Sequential Analysis
```
1. Direct: Spawn parallel simple tasks
2. cc_execute: Analyze results with full context
3. cc_execute: Generate report or documentation
```

### Build → Test → Deploy
```
1. cc_execute: Build application (needs isolation)
2. Direct: Run tests (simple commands)
3. cc_execute: Generate deployment configs
```

## Directory Structure

```
examples/
├── README.md                    # This file
├── basic_usage/                 # Simple sequential execution
│   ├── README.md               # Example documentation
│   ├── task_list.md            # Task definitions
│   └── run_example.py          # Execution script
├── advanced_usage/              # Mixed patterns & tool integration
│   ├── README.md
│   ├── task_list.md
│   └── run_example.py
└── archive_redundant/           # Old examples (deprecated)
    ├── 02_with_error_recovery/  # Error recovery is now built-in
    ├── 03_with_hooks/           # Hooks are now automatic
    └── 04_with_uuid_verification/ # UUID4 is now automatic
```

## Output Organization

Each example creates:
- `tmp/responses/` - JSON execution results with UUID verification
- Generated files as specified in tasks
- Detailed logs showing execution flow

All outputs are gitignored by default.

## Best Practices

1. **Start with basic_usage**: Understand the fundamentals
2. **Study advanced_usage**: Learn when to optimize
3. **Check JSON outputs**: Verify UUID4 presence at end
4. **Monitor execution times**: Decide if cc_execute is needed

## Migration from Old Examples

The old examples (02, 03, 04) demonstrated features that are now automatic:
- **Error recovery**: Built into cc_execute (3 retries)
- **Hooks**: Automatically applied for UUID4 verification
- **UUID verification**: Always enabled with cc_execute

You no longer need to configure these manually!

## Troubleshooting

### Task Fails UUID Verification
- This is rare - cc_execute handles it automatically
- Check the task generates JSON output
- Ensure task uses cc_execute pattern

### Task Times Out
- Increase timeout in run_example.py
- cc_execute supports up to 10 minutes
- WebSocket keeps connection alive

### Wrong Execution Mode
- Simple tasks → direct execution
- Complex tasks → cc_execute
- Check task requirements

## Next Steps

1. Run both examples to understand patterns
2. Create your own task lists
3. Mix execution modes for efficiency
4. Build complex workflows with confidence