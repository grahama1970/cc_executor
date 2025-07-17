# Lessons Learned: AssessComplexity MCP Tool

## Overview
The AssessComplexity MCP tool evolved from a simple error categorization tool to a sophisticated prompt-generation system that helps agents make informed decisions about how to fix code issues. This document captures the lessons learned during its development and testing with the logger_agent project.

## Key Philosophical Shifts

### 1. From Decision-Making to Prompt Generation
**Initial Approach**: Tool attempted to make decisions using string pattern matching
```python
# WRONG - Tool making decisions
if "import" in error_type.lower():
    return "use_perplexity"
```

**Improved Approach**: Tool generates prompts with metrics for agent reasoning
```python
# RIGHT - Tool provides information for agent reasoning
prompt = f"""
## Error Analysis: {error_type}
Tree-sitter found {import_count} imports...
NetworkX detected {circular_deps} circular dependencies...
YOU must assess complexity and choose the appropriate fix method.
"""
```

**Lesson**: Tools should provide information and context, not make decisions. The agent's reasoning capabilities should determine the appropriate action based on the provided metrics.

### 2. Error-Specific Analysis Strategies
**Discovery**: Different error types require different analysis approaches

```python
ERROR_STRATEGIES = {
    'ModuleNotFoundError': {
        'focus': ['import_paths', 'project_structure'],
        'skip': ['call_graph', 'coupling_metrics'],  # These aren't relevant
        'analyzer': 'analyze_import_error'
    },
    'TypeError': {
        'focus': ['variable_types', 'method_signatures'],
        'skip': ['import_analysis'],
        'analyzer': 'analyze_type_error'
    }
}
```

**Lesson**: Contextual analysis is crucial. Running full analysis for every error type wastes resources and clutters the output with irrelevant information.

### 3. Integration of Static Analysis Tools
**Tree-sitter Integration**: Provides AST-level analysis
- Function/class counts
- Import analysis
- Code structure metrics

**NetworkX Integration**: Provides dependency analysis
- Call graphs
- Circular dependency detection
- Module coupling metrics

**Lesson**: Static analysis tools provide objective metrics that help assess complexity without executing code.

## Critical Improvements Made

### 1. Project Root Detection
**Before**: Brittle parent directory traversal
```python
project_root = file_path_obj.parent.parent.parent
```

**After**: Elegant python-dotenv integration
```python
try:
    from dotenv import find_dotenv
    dotenv_path = find_dotenv(str(file_path_obj))
    if dotenv_path:
        project_root = Path(dotenv_path).parent
except ImportError:
    pass
```

### 2. Clear Complexity Indicators
Added explicit complexity assessment section:
```python
if complexity_indicators:
    prompt += "\n## 🚨 Complexity Assessment\n"
    if "circular_deps" in complexity_indicators:
        prompt += "- **TOO COMPLEX FOR SELF-FIX**: Circular dependencies require architectural analysis\n"
```

### 3. MCP Tool Recommendations
Integrated clear recommendations for available MCP tools:
- **Self-fix**: For simple, localized issues
- **context7**: For documentation lookups
- **perplexity-ask**: For best practices and API research
- **cc_execute**: For fresh context on complex issues
- **send_to_gemini**: For architectural problems

### 4. Error Context Preservation
Added comprehensive error context:
```python
{
    "error_type": error_type,
    "error_message": error_message,
    "file_path": file_path,
    "stack_trace": stack_trace,
    "previous_attempts": previous_attempts
}
```

## Testing Insights

### 1. Real-World Testing Revealed Gaps
Testing with logger_agent exposed several issues:
- Import errors were common but initially poorly analyzed
- Relative vs absolute import confusion
- Missing sys.path manipulations

### 2. Working Usage Functions Are Critical
**Key Discovery**: Using `working_usage()` functions to verify fixes is more reliable than creating separate test files.

**Implementation**:
```python
async def working_usage():
    """
    CRITICAL FOR AGENTS:
    - This function MUST verify that the script produces expected results
    - Use assertions to validate outputs match expectations
    - Return True only if ALL tests pass
    - This is how agents verify the script actually works
    """
```

### 3. Agent Instructions Must Be Explicit
Added explicit instructions to every Python file:
```python
"""
=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python {filename}          # Runs working_usage() - stable, known to work
  python {filename} debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
"""
```

## Common Pitfalls Discovered

### 1. Import Path Issues
- **Problem**: ModuleNotFoundError due to incorrect sys.path
- **Solution**: Add sys.path manipulation at module level
- **Better Solution**: Use proper package structure with __init__.py files

### 2. Async/Await Confusion
- **Problem**: Missing await keywords or incorrect async context
- **Solution**: Clear async/await patterns in all database operations

### 3. Test Database Cleanup
- **Problem**: Test databases not being cleaned up
- **Solution**: Proper try/finally blocks in test utilities

## Recommendations for Future Improvements

### 1. Enhanced Metrics
- Add cyclomatic complexity analysis
- Include test coverage metrics
- Measure code duplication

### 2. Learning System
- Store successful fixes for similar errors
- Build a knowledge base of error patterns
- Track fix success rates

### 3. Better Integration
- Direct integration with pytest for test verification
- Integration with code formatters (black, ruff)
- Git integration for tracking changes

### 4. Performance Optimization
- Cache tree-sitter parse results
- Lazy load analysis tools
- Parallel analysis for large codebases

## Usage Patterns

### Effective Usage
```python
# 1. Assess complexity first
assessment = await mcp__logger-tools__assess_complexity({
    "error_type": "ModuleNotFoundError",
    "error_message": "No module named 'utils'",
    "file_path": "agent_graph_builder.py"
})

# 2. Review the generated prompt
# 3. Make informed decision based on metrics
# 4. Use appropriate tool for the fix
# 5. Verify with working_usage()
```

### Anti-Patterns to Avoid
1. Don't skip the assessment for "simple" errors
2. Don't ignore the complexity indicators
3. Don't create external test files
4. Don't trust fixes without verification

## Conclusion

The AssessComplexity tool evolved from a simple categorization tool to a sophisticated analysis system that empowers agents to make informed decisions. The key insight is that tools should provide rich context and metrics, not make decisions. The combination of static analysis, error-specific strategies, and clear prompt generation creates a powerful system for code issue resolution.

The most important lesson: **Let agents think, let tools inform.**