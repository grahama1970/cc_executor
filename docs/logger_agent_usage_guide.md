# Logger Agent Complete Usage Guide

## Overview
The Logger Agent is a centralized logging system that helps agents learn from past experiences, find solutions to recurring errors, and build a knowledge base of fixes. This guide shows you EXACTLY how to use it effectively.

## Core Concepts

### 1. Every Error Gets Assessed and Logged
When you encounter an error, ALWAYS:
1. Use `assess_complexity` to analyze it (this automatically logs the assessment)
2. Search for similar errors to find previous fixes
3. Log the successful fix when you resolve it

### 2. Building Knowledge Through Logging
Every fix you log helps future agents (including yourself) solve similar problems faster.

## Essential Logger Agent Patterns

### Pattern 1: Assessing an Error
```python
# When you encounter an error, ALWAYS assess it first
result = await mcp__logger-tools__assess_complexity({
    "error_type": "ModuleNotFoundError",
    "error_message": "No module named 'requests'",
    "file_path": "/path/to/script.py",
    "stack_trace": "File script.py, line 5, in <module>\n    import requests"
})

# The result includes:
# - Similar errors from history
# - Previous fixes that worked
# - An assessment_id for linking the fix later
```

### Pattern 2: Searching for Previous Fixes
```python
# Search for how similar errors were fixed before
fixes = await mcp__logger-tools__search_error_fixes({
    "error_type": "ModuleNotFoundError",
    "error_message": "requests",
    "limit": 5
})

# Returns:
# {
#   "fixes": [
#     {
#       "error_type": "ModuleNotFoundError",
#       "original_error": "No module named 'requests'",
#       "fix_description": "Added 'uv add requests' to install missing package",
#       "file_path": "/other/project/main.py",
#       "score": 0.95
#     }
#   ]
# }
```

### Pattern 3: Logging a Successful Fix
```python
# CRITICAL: After fixing an error, ALWAYS log it!
fix_result = await mcp__logger-tools__log_successful_fix({
    "error_type": "ModuleNotFoundError",
    "error_message": "No module named 'requests'",
    "file_path": "/path/to/script.py",
    "fix_description": "Installed requests package with 'uv add requests'",
    "assessment_id": "assessment_12345"  # From the original assessment
})
```

## Complete Workflow Example

### Step 1: Encounter an Error
```python
# You try to run a script and get:
ModuleNotFoundError: No module named 'pandas'
```

### Step 2: Assess the Error
```python
assessment = await mcp__logger-tools__assess_complexity({
    "error_type": "ModuleNotFoundError",
    "error_message": "No module named 'pandas'",
    "file_path": "/workspace/data_analysis.py",
    "stack_trace": "File data_analysis.py, line 3, in <module>\n    import pandas as pd"
})

# Extract the assessment ID
assessment_id = "assessment_67890"  # From the response
```

### Step 3: Review Similar Errors
The assessment already shows similar errors, but you can search for more:
```python
similar_fixes = await mcp__logger-tools__search_error_fixes({
    "error_type": "ModuleNotFoundError",
    "error_message": "pandas",
    "limit": 10
})
```

### Step 4: Apply the Fix
Based on the similar fixes, you know to:
```bash
uv add pandas
```

### Step 5: Verify the Fix Works
Run the script again to ensure it works.

### Step 6: Log the Successful Fix
```python
await mcp__logger-tools__log_successful_fix({
    "error_type": "ModuleNotFoundError",
    "error_message": "No module named 'pandas'",
    "file_path": "/workspace/data_analysis.py",
    "fix_description": "Installed pandas with 'uv add pandas'",
    "assessment_id": assessment_id
})
```

## Advanced Usage

### 1. BM25 Full-Text Search
```python
# Search across all logs for specific patterns
results = await mcp__logger-tools__query_agent_logs({
    "action": "search",
    "query": "TypeError string concatenation",
    "limit": 20
})
```

### 2. Error Pattern Analysis
```python
# Find recurring error patterns
patterns = await mcp__logger-tools__get_error_patterns({
    "time_range": "7d",  # Last 7 days
    "min_occurrences": 3  # At least 3 times
})

# Returns patterns like:
# {
#   "patterns": [
#     {
#       "error_type": "ImportError",
#       "pattern": "No module named 'N'",
#       "count": 15,
#       "common_fixes": ["uv add package", "check sys.path"]
#     }
#   ]
# }
```

### 3. Graph Traversal for Related Errors
```python
# Find errors related by causality
related = await mcp__logger-tools__query_agent_logs({
    "action": "find_related",
    "session_id": "session_123",
    "tool_name": "graph_traversal"
})
```

## Logger Integration in Your Scripts

### In Python Scripts
```python
# At the top of every Python script that might have errors
import sys
from pathlib import Path

# Add logger agent to path if available
try:
    sys.path.insert(0, str(Path(__file__).parent.parent / "logger_agent" / "src"))
    from agent_log_manager import get_log_manager
    LOGGER_AVAILABLE = True
except ImportError:
    LOGGER_AVAILABLE = False

async def log_error_and_fix(error_type, error_msg, fix_desc):
    """Helper to log errors and fixes"""
    if not LOGGER_AVAILABLE:
        return
    
    manager = await get_log_manager()
    
    # Log the error
    error_log = await manager.log_event(
        level="ERROR",
        message=f"{error_type}: {error_msg}",
        script_name=Path(__file__).name,
        execution_id=f"exec_{datetime.now().timestamp()}",
        extra_data={"error_type": error_type},
        tags=["error", error_type.lower()]
    )
    
    # Log the fix
    fix_log = await manager.log_event(
        level="SUCCESS",
        message=f"Fixed: {fix_desc}",
        script_name=Path(__file__).name,
        execution_id=f"exec_{datetime.now().timestamp()}",
        extra_data={
            "fix_description": fix_desc,
            "original_error_id": error_log.get("_id")
        },
        tags=["fix", "success"]
    )
    
    return fix_log
```

### In Test Functions
```python
async def working_usage():
    """Test function with logger integration"""
    logger.info("Starting test...")
    
    try:
        # Your test code here
        result = await some_function()
        
        # Log success
        if LOGGER_AVAILABLE:
            await log_event("SUCCESS", "Test passed", tags=["test", "success"])
        
    except Exception as e:
        # Log the error
        if LOGGER_AVAILABLE:
            await log_event("ERROR", str(e), tags=["test", "failure"])
        
        # Fix it and log the fix
        fix_applied = await fix_the_error(e)
        if fix_applied and LOGGER_AVAILABLE:
            await log_error_and_fix(
                type(e).__name__, 
                str(e), 
                fix_applied
            )
```

## Best Practices

### 1. Always Use Assessment First
```python
# ✅ GOOD: Assess first, then fix
assessment = await assess_complexity(error_info)
# Apply fix based on assessment
await log_successful_fix(fix_info)

# ❌ BAD: Fix without assessment
# Just fixing without logging means lost knowledge
```

### 2. Be Descriptive in Fix Descriptions
```python
# ✅ GOOD: Detailed fix description
"Fixed ModuleNotFoundError by adding 'uv add pandas==2.0.1' and updating imports to use 'pd' alias"

# ❌ BAD: Vague description
"Fixed import error"
```

### 3. Link Assessments to Fixes
```python
# ✅ GOOD: Include assessment_id
await log_successful_fix({
    # ... other fields ...
    "assessment_id": assessment_id_from_earlier
})

# This creates a knowledge graph linking problems to solutions
```

### 4. Search Before Solving
```python
# ✅ GOOD: Check if this was solved before
similar_errors = await search_error_fixes({
    "error_type": "TypeError",
    "error_message": "unsupported operand"
})

if similar_errors["fixes"]:
    # Try the most successful fix first
    best_fix = similar_errors["fixes"][0]
```

## Common Error Patterns and Fixes

### ModuleNotFoundError
```python
# Assessment will show:
# - Missing module name
# - Whether it's installed
# - Similar import errors

# Common fixes logged:
# 1. "uv add [module]"
# 2. "Add sys.path.insert(0, parent_dir)"
# 3. "Change relative import to absolute"
```

### TypeError
```python
# Assessment will show:
# - Variable types involved
# - Method signatures
# - Type conversion options

# Common fixes logged:
# 1. "Added str() conversion for string concatenation"
# 2. "Changed to f-string formatting"
# 3. "Added type checking before operation"
```

### AttributeError
```python
# Assessment will show:
# - Available attributes
# - Class hierarchy
# - Similar attribute names

# Common fixes logged:
# 1. "Fixed typo in attribute name"
# 2. "Added hasattr() check before access"
# 3. "Initialized attribute in __init__"
```

## Debugging with Logger

### Find All Errors in a Session
```python
session_errors = await query_agent_logs({
    "action": "search",
    "session_id": "current_session_id",
    "event_type": "error",
    "limit": 100
})
```

### Track Fix Success Rate
```python
# Get all fixes in the last week
fixes = await search_error_fixes({
    "limit": 100
})

# Analyze which fixes work most often
fix_patterns = {}
for fix in fixes["fixes"]:
    key = f"{fix['error_type']}:{fix['fix_description'][:50]}"
    fix_patterns[key] = fix_patterns.get(key, 0) + 1
```

## Integration Checklist

When working on any Python project:

- [ ] Import logger agent at the top of scripts
- [ ] Use assess_complexity for EVERY error
- [ ] Search for similar errors before attempting fixes
- [ ] Log EVERY successful fix with clear descriptions
- [ ] Link fixes to assessments using assessment_id
- [ ] Use descriptive tags for better searchability
- [ ] Include file paths and error types in all logs
- [ ] Test logger integration in working_usage functions

## Summary

The Logger Agent is your knowledge base. Every error assessed and every fix logged makes you smarter. Use it consistently and descriptively to build a powerful problem-solving system.

Remember: **Assess → Search → Fix → Log → Learn**