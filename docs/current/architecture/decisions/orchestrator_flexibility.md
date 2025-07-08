# Orchestrator Tool Flexibility Without Brittleness

## The Challenge

You want the orchestrator to flexibly use different tools:
- Claude Task Tool
- Perplexity-ask (MCP)
- cc_execute (prompt-based)

But only if it doesn't add brittleness or complexity.

## The Solution: Unified Tool Interface

Based on perplexity-ask research and best practices, the answer is a **minimal unified wrapper interface** - think "Lego blocks" where each tool has the same connection interface.

### Why This Works

1. **No Added Complexity** - The wrapper is so thin it's just an interface
2. **Maintains Reliability** - cc_execute continues using its proven prompt-based approach
3. **Flexibility** - Orchestrator can choose tools without knowing implementation details
4. **Extensibility** - Adding new tools is just implementing the interface

### Implementation Pattern

```python
# Each tool implements the same simple interface
class ToolInterface(Protocol):
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool and return results."""
        ...

# cc_execute wrapper - adds NO complexity
class CCExecuteTool:
    def __init__(self):
        from prompts.cc_execute_utils import execute_task_via_websocket
        self.execute_func = execute_task_via_websocket
    
    async def execute(self, task: str, **kwargs) -> Dict[str, Any]:
        # Just calls the proven implementation
        return self.execute_func(task=task, **kwargs)
```

### Orchestrator Usage

```python
orchestrator = UnifiedToolOrchestrator()

# Choose tool based on task type
if task_needs_fresh_context:
    result = await orchestrator.execute_tool(
        "cc_execute",
        task="Create a complex application",
        timeout=600
    )
elif task_needs_research:
    result = await orchestrator.execute_tool(
        "perplexity_ask",
        query="Latest best practices for X"
    )
elif task_needs_analysis:
    result = await orchestrator.execute_tool(
        "claude_task",
        description="Analyze this code"
    )
```

## Why NOT Use MCP for cc_execute

From the perplexity-ask research on MCP brittleness:

1. **Additional abstraction layers** - Protocol handling, serialization
2. **Asynchronous complexity** - Event loops, potential deadlocks
3. **Error handling indirection** - Subprocess errors marshaled through protocol
4. **Known issues** - FastMCP servers can "lock" with hanging calls
5. **Resource conflicts** - MCP timeouts may not match subprocess needs

## Benefits of This Approach

✅ **Reliability** - cc_execute keeps its 10:1 success ratio  
✅ **Flexibility** - Orchestrator can use any tool through same interface  
✅ **Simplicity** - No complex protocols or servers  
✅ **Extensibility** - Easy to add new tools  
✅ **Best Practice** - Follows orchestration patterns from major frameworks  

## When to Use MCP

Only use MCP when you actually need its features:
- Tool discovery
- Structured schemas
- Integration with MCP ecosystem

For cc_execute, these aren't needed - it's just spawning Claude instances.

## Example: Multi-Tool Orchestration

```python
async def build_web_app():
    """Example orchestrating multiple tools for a complex task."""
    
    # 1. Research best practices
    research = await orchestrator.execute_tool(
        "perplexity_ask",
        query="Best practices for FastAPI apps in 2025"
    )
    
    # 2. Generate code with fresh context
    code = await orchestrator.execute_tool(
        "cc_execute",
        task=f"Create a FastAPI app following these practices: {research['response']}",
        timeout=300,
        tools=["Write", "Edit"]
    )
    
    # 3. Analyze the generated code
    analysis = await orchestrator.execute_tool(
        "claude_task",
        description="Code review",
        prompt="Review the FastAPI app for security and performance"
    )
    
    return {
        "research": research,
        "code": code,
        "analysis": analysis
    }
```

## Conclusion

The unified interface pattern gives you:
- **Tool flexibility** for the orchestrator
- **Zero added brittleness** for cc_execute  
- **Clean architecture** that scales

This is the "Lego blocks" approach - reliable, flexible, and simple.