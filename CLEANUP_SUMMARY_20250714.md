# AssessComplexity Tool Cleanup Summary

## What We Started With
- Multiple overlapping tools created during iteration
- Confusing names: assess_complexity, assess_complexity_prompt, assess_complexity_via_prompt, python_call_graph_prompt
- Mixed approaches: some returning decisions, others returning prompts

## What We Have Now
**One tool**: `assess_complexity` that returns a prompt for Claude to reason with

## Key Design Principles
1. **The tool doesn't make decisions** - it returns a prompt for the agent to think with
2. **The agent (Claude) assesses complexity** - using its own reasoning, not string pattern matching
3. **Simple and clear** - one tool, one purpose

## How It Works
```python
# Agent calls the tool when encountering an error
prompt = await mcp__logger-tools__assess_complexity(
    error_type="TypeError",
    error_message="Object of type datetime is not JSON serializable",
    file_path="/path/to/file.py",
    stack_trace="..."
)

# Tool returns a prompt that guides reasoning
# Agent then decides: self-fix, research, fresh context, or comprehensive approach
```

## Files to Clean Up (can be deleted)
- `/src/cc_executor/tools/assess_complexity.py` (old decision-making version)
- `/src/cc_executor/tools/assess_complexity_v2.py` (intermediate version)
- `/src/cc_executor/tools/assess_complexity_prompt.py` (overly complex with AST)
- `/src/cc_executor/tools/assess_complexity_simple_prompt.py` (redundant)
- `/src/cc_executor/tools/assess_complexity_call_graph.py` (too specialized)

## The Single Source of Truth
- `/src/cc_executor/tools/assess_complexity_unified.py` - The ONE tool to use
- Exposed via MCP as `mcp__logger-tools__assess_complexity`

## Why This Matters
The user was right - we don't need multiple tools for the same purpose. The complexity assessment is something the agent does through reasoning, not something determined by code. The tool just provides a framework for that reasoning.
