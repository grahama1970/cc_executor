# Usage Response Saving Guide

## Purpose
Every Python file in core/ MUST have an `if __name__ == "__main__":` block that saves its output as prettified JSON. This allows the self-improving prompt to verify actual execution vs hallucination.

## Implementation Status

### ✅ Completed Files (with response saving)
1. **config.py** - Uses manual capture but saves clean JSON (no .txt)
2. **models.py** - Uses OutputCapture helper ✅
3. **process_manager.py** - Uses OutputCapture helper ✅
4. **resource_monitor.py** - Uses OutputCapture helper ✅
5. **usage_helper.py** - Has functioning demo block ✅
6. **simple_example.py** - Demo file using OutputCapture ✅

### ⏳ Files Needing Update
1. **session_manager.py** - Has old pattern with .txt saving (needs OutputCapture)
2. **stream_handler.py** - Has old pattern with .txt saving (needs OutputCapture)
3. **main.py** - Need to check if it's a service or has demo block
4. **websocket_handler.py** - Has demo but needs response saving added

## Pattern to Use

### For Synchronous Code:
```python
if __name__ == "__main__":
    """Description of what this demonstrates."""
    from usage_helper import OutputCapture
    
    with OutputCapture(__file__) as capture:
        print("=== Module Name Usage Example ===")
        # All your demo code here
        print("✅ Demo completed!")
```

### For Async Code (like session_manager.py):
```python
if __name__ == "__main__":
    """Description of what this demonstrates."""
    import asyncio
    from usage_helper import OutputCapture
    
    async def main():
        # Async demo code here
        pass
    
    # Wrap the entire execution
    with OutputCapture(__file__) as capture:
        asyncio.run(main())
```

## Benefits
1. **Clean Code** - No manual buffer management
2. **Consistent Format** - All files save the same JSON structure
3. **No Duplicates** - Only JSON files, no redundant .txt files
4. **Automatic Metadata** - Timestamp, duration, success status
5. **Verification** - Self-improving prompt can check actual vs claimed output

## Directory Structure
```
core/
├── tmp/
│   ├── responses/          # All JSON response files
│   ├── scripts_generated/  # Generated helper scripts
│   └── broken_files/       # Backup of files before fixes
└── *.py                    # Core Python files with demos
```

## JSON Response Format
```json
{
    "filename": "module_name",
    "module": "cc_executor.core.module_name",
    "timestamp": "20250703_094753",
    "execution_time": "2025-07-03 09:47:53",
    "duration_seconds": 0.123,
    "output": "Full captured output...",
    "line_count": 42,
    "success": true,
    "has_error": false,
    "exit_status": "completed"
}
```

## Next Steps
1. Update session_manager.py to use OutputCapture
2. Update stream_handler.py to use OutputCapture
3. Check if main.py needs a demo block
4. Add response saving to websocket_handler.py's existing demo