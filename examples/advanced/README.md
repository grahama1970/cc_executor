# Advanced Usage Example

This example demonstrates the advanced patterns from the main README - mixed execution modes and tool integration.

## What This Example Does

Creates a quantum computing tutorial through a sophisticated workflow:

1. **Research** (Direct) - Uses perplexity-ask MCP tool
2. **Tutorial Creation** (cc_execute) - Needs fresh context for generation
3. **External Review** (cc_execute) - Uses gemini via LiteLLM for verification
4. **Interactive Exercises** (cc_execute) - Creates Jupyter notebook

## Key Patterns Demonstrated

### 1. Mixed Execution Modes
- **Direct**: Simple tool calls that don't need isolation
- **cc_execute**: Complex generation requiring fresh context

### 2. Tool Integration
- MCP tools (perplexity-ask) for external data
- LiteLLM for multi-model verification
- Standard Claude tools (Read, Write, Edit)

### 3. Sequential Dependencies
- Each task builds on previous outputs
- Research informs tutorial
- Review improves exercises

## Running the Example

```bash
# From this directory
python run_example.py

# Or from project root
python examples/advanced_usage/run_example.py
```

## Expected Output

```
================================================================================
CC Executor - Advanced Usage Example
Tool Integration & External Verification Pattern
================================================================================

This example demonstrates:
- Direct MCP tool usage (Task 1)
- cc_execute for complex tasks (Tasks 2-4)
- External model verification (Task 3)
- Sequential dependencies
- Automatic UUID4 verification when using cc_execute

================================================================================
Task 1: Research Quantum Entanglement
Execution Mode: DIRECT
================================================================================
📡 Executing directly (no cc_execute needed)...

✅ Task Result:
  Status: success
  Duration: 2.1s
  Expected output: quantum_research.md (Would create)

================================================================================
Task 2: Create Tutorial
Execution Mode: CC_EXECUTE
================================================================================
🔄 Executing via cc_execute (complex task, needs fresh context)...
🔐 Pre-hook: Generated execution UUID: b5e6d3e2-...

UUID Verification: 🔐 VERIFIED

✅ Task Result:
  Status: success
  Duration: 45.3s
  Expected output: quantum_tutorial.md (Would create)
  UUID Verification: 🔐 VERIFIED
```

## Understanding the Execution Flow

### Task 1: Direct Execution
- No cc_execute overhead
- Quick MCP tool call
- No UUID verification needed
- Results available for next task

### Tasks 2-4: cc_execute Pattern
- Fresh 200K context each
- Automatic UUID4 injection
- WebSocket keeps alive for long tasks
- Verification proves execution

## Files Created (Simulated)

```
quantum_research.md       # MCP research results
quantum_tutorial.md       # Comprehensive tutorial
review_feedback.md        # External model review
quantum_exercises.ipynb   # Interactive notebook
```

## Performance Insights

The execution summary shows:
- Direct tasks: ~2-5 seconds
- cc_execute tasks: ~30-300 seconds

This demonstrates why mixing patterns is important for efficiency.

## Key Takeaways

1. **Not everything needs cc_execute** - Use it judiciously
2. **Tool selection matters** - MCP for data, cc_execute for generation
3. **Verification is automatic** - UUID4 when using cc_execute
4. **Sequential power** - Tasks build on each other effectively

## Customizing This Example

1. Replace quantum computing with your domain
2. Use different MCP tools (GitHub, web search, etc.)
3. Try different external models for review
4. Add more complex sequential dependencies

## Next Steps

- Study the task execution patterns
- Create your own mixed workflows
- Optimize between direct and cc_execute
- Build production-ready orchestrations