# Logger Agent Quick Reference Card

## 🚀 Most Common Operations

### 1. When You Hit an Error
```python
# ALWAYS do this first!
assessment = await mcp__logger-tools__assess_complexity({
    "error_type": "ModuleNotFoundError",
    "error_message": "No module named 'pandas'",
    "file_path": "/path/to/file.py",
    "stack_trace": "full stack trace here"
})
# Save the assessment_id from the response!
```

### 2. After Fixing an Error
```python
# ALWAYS log successful fixes!
await mcp__logger-tools__log_successful_fix({
    "error_type": "ModuleNotFoundError",
    "error_message": "No module named 'pandas'",
    "file_path": "/path/to/file.py",
    "fix_description": "Installed pandas with 'uv add pandas'",
    "assessment_id": "assessment_12345"  # From step 1
})
```

### 3. Search for Previous Fixes
```python
# Find how others fixed similar errors
fixes = await mcp__logger-tools__search_error_fixes({
    "error_type": "TypeError",
    "error_message": "unsupported operand",
    "limit": 5
})
```

### 4. Find Error Patterns
```python
# See what errors keep happening
patterns = await mcp__logger-tools__get_error_patterns({
    "time_range": "7d",
    "min_occurrences": 2
})
```

## 📝 In Your Python Scripts

### Add to Every Script
```python
# At the top of your scripts
import sys
from pathlib import Path
from loguru import logger

# Quick logger for debugging
async def log_debug(message, level="INFO"):
    """Quick debug logging to logger agent"""
    try:
        from agent_log_manager import get_log_manager
        manager = await get_log_manager()
        await manager.log_event(
            level=level,
            message=message,
            script_name=Path(__file__).name,
            execution_id=f"debug_{datetime.now().timestamp()}"
        )
    except:
        logger.info(message)  # Fallback to console
```

### In working_usage()
```python
async def working_usage():
    """Your test function"""
    await log_debug("Starting working_usage test")
    
    try:
        # Your test code
        result = await your_function()
        await log_debug(f"Success: {result}", "SUCCESS")
        
    except Exception as e:
        # Log the error
        await log_debug(f"Error: {e}", "ERROR")
        
        # Assess it
        assessment = await mcp__logger-tools__assess_complexity({
            "error_type": type(e).__name__,
            "error_message": str(e),
            "file_path": __file__
        })
        
        # Fix it
        # ... your fix code ...
        
        # Log the fix
        await mcp__logger-tools__log_successful_fix({
            "error_type": type(e).__name__,
            "error_message": str(e),
            "file_path": __file__,
            "fix_description": "How you fixed it"
        })
```

## 🔍 Search Patterns

### Basic Search
```python
# Search everything
results = await mcp__logger-tools__query_agent_logs({
    "action": "search",
    "query": "your search terms",
    "limit": 20
})
```

### Search by Error Type
```python
# Find all TypeErrors
results = await mcp__logger-tools__query_agent_logs({
    "action": "search",
    "query": "TypeError",
    "event_type": "error",
    "limit": 50
})
```

### Search in Time Range
```python
# Last 24 hours
results = await mcp__logger-tools__query_agent_logs({
    "action": "search",
    "query": "failed",
    "time_range_hours": 24,
    "limit": 100
})
```

## 🏷️ Important Tags

Always use these tags for better searchability:
- `error` - For any error
- `fix` - For any fix
- `success` - For successful operations
- `import-error` - For import issues
- `type-error` - For type issues
- `config` - For configuration issues
- Error type in lowercase (e.g., `modulenotfounderror`)

## 💡 Pro Tips

1. **Always link fixes to assessments** - Use the assessment_id
2. **Be specific in fix descriptions** - "Added X to Y" not just "fixed"
3. **Search before solving** - Someone probably fixed it before
4. **Log partial fixes too** - Even failed attempts teach us
5. **Use consistent tags** - Makes searching much easier

## 🎯 Complete Workflow

```python
# 1. Hit error → Assess it
assessment = await assess_complexity(error_details)
assessment_id = extract_id(assessment)

# 2. Search for existing fixes
fixes = await search_error_fixes(error_details)

# 3. Apply best fix from history OR create new fix
if fixes["fixes"]:
    apply_fix(fixes["fixes"][0])
else:
    create_new_fix()

# 4. Test the fix works
verify_fix()

# 5. Log the successful fix
await log_successful_fix(fix_details, assessment_id)
```

## 🚨 Remember

**Every error is a learning opportunity!**
- Assess it ✓
- Search for it ✓
- Fix it ✓
- Log it ✓
- Next time will be faster! 🚀