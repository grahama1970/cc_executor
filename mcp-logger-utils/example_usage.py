#!/usr/bin/env python3
"""
Example usage of mcp-logger-utils following CLAUDE.md standards.

=== USAGE INSTRUCTIONS FOR AGENTS ===
Run this script directly to test:
  python example_usage.py          # Runs working_usage() - stable, known to work
  python example_usage.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug function!
"""

import asyncio
import sys
from pathlib import Path

# Import from the installed package (after pip install mcp-logger-utils)
from mcp_logger_utils import MCPLogger, debug_tool, repair_and_parse_json


async def working_usage():
    """Demonstrate proper usage of mcp-logger-utils.
    
    AGENT: Run this for stable, production-ready example.
    This function is known to work and should not be modified.
    """
    # 1. Create a logger instance
    logger = MCPLogger("production-server")
    print(f"✓ Logger initialized. Logs in: {logger.log_dir}")
    
    # 2. Define a tool function with debug decorator
    @debug_tool(logger)
    async def fetch_user_data(user_id: int) -> dict:
        """Simulates fetching user data."""
        if user_id < 1:
            raise ValueError("User ID must be positive")
        
        # Simulate async operation
        await asyncio.sleep(0.1)
        
        return {
            "id": user_id,
            "name": f"User {user_id}",
            "embeddings": list(range(100)),  # Will be truncated in logs
            "profile_image": "data:image/png;base64," + "A" * 500  # Will be truncated
        }
    
    # 3. Use the tool
    print("\nFetching user data...")
    result = await fetch_user_data(123)
    print(f"✓ Success: Got user {result['name']}")
    
    # 4. Demonstrate JSON repair
    print("\nTesting JSON repair...")
    messy_json = '''
    ```json
    {
        "status": "success",
        "data": {
            "count": 42,
            "active": true, // This comment would break normal JSON parsing
        }
    }
    ```
    '''
    
    cleaned = repair_and_parse_json(messy_json, logger_instance=logger.logger)
    print(f"✓ Repaired JSON: {cleaned}")
    
    print("\n✅ Working usage complete!")
    return True


async def debug_function():
    """Debug function for testing new ideas and troubleshooting.
    
    AGENT: Use this function for experimenting! Rewrite freely.
    This is constantly rewritten to test different things.
    """
    print("=== DEBUG MODE ===")
    
    # Currently testing: Custom truncation limits and error handling
    custom_logger = MCPLogger(
        "debug-server",
        max_log_str_len=100,  # Shorter strings
        max_log_list_len=5    # Fewer list items
    )
    
    @debug_tool(custom_logger, catch_exceptions=False)  # Let exceptions bubble up
    async def test_edge_cases(data: dict) -> dict:
        """Test various edge cases."""
        # Test with different data types
        result = {
            "huge_string": "X" * 200,
            "big_list": list(range(50)),
            "nested": {
                "embeddings": [0.1] * 1000,
                "metadata": {"test": True}
            }
        }
        
        # Simulate an error condition
        if data.get("force_error"):
            raise RuntimeError("Forced error for testing")
            
        return result
    
    # Test 1: Normal operation
    print("\nTest 1: Normal operation")
    try:
        result = await test_edge_cases({"test": True})
        print(f"✓ Got result with {len(result)} keys")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
    
    # Test 2: Error handling (should raise)
    print("\nTest 2: Error handling")
    try:
        result = await test_edge_cases({"force_error": True})
        print("✗ Should have raised an error!")
    except RuntimeError as e:
        print(f"✓ Caught expected error: {e}")
    
    # Test 3: JSON repair edge cases
    print("\nTest 3: JSON repair edge cases")
    test_cases = [
        "not json at all",
        '{"incomplete": ',
        '[1, 2, 3,]',  # Trailing comma
        '{"key": undefined}',  # JavaScript-style undefined
    ]
    
    for i, test in enumerate(test_cases):
        result = repair_and_parse_json(test, logger_instance=custom_logger.logger)
        print(f"  Case {i+1}: {type(result).__name__} - {str(result)[:30]}...")
    
    print("\n✅ Debug tests complete!")


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    if mode == "debug":
        print("Running debug mode...")
        asyncio.run(debug_function())
    else:
        print("Running working usage mode...")
        asyncio.run(working_usage())