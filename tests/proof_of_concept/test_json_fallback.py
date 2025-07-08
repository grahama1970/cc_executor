#!/usr/bin/env python3
"""Test JSON output with fallback conversion."""
import asyncio
from executor import cc_execute, CCExecutorConfig

async def test_with_json_request():
    """Test with explicit JSON request in prompt."""
    print("Test 1: With JSON request in prompt")
    print("=" * 60)
    
    result = await cc_execute(
        "What is 2+2?",
        config=CCExecutorConfig(timeout=60),
        stream=False,
        return_json=True  # This adds JSON schema to prompt
    )
    
    print(f"Type: {type(result)}")
    if isinstance(result, dict):
        print(f"Result: {result.get('result')}")
        print(f"Summary: {result.get('summary')}")
        print(f"UUID verified: {result.get('execution_uuid') is not None}")

async def test_without_json_request():
    """Test without JSON request - fallback conversion."""
    print("\n\nTest 2: Without JSON request (fallback conversion)")
    print("=" * 60)
    
    # First get the raw text response
    text_result = await cc_execute(
        "What is 2+2?",
        config=CCExecutorConfig(timeout=60),
        stream=False,
        return_json=False  # No JSON schema in prompt
    )
    
    print(f"Raw text response: {text_result}")
    
    # Now try the same with return_json=True but no schema in prompt
    # This simulates the fallback behavior
    print("\n\nTest 3: Text prompt but JSON return requested")
    print("=" * 60)
    
    # Temporarily override to not add schema
    import executor
    original_code = executor.cc_execute.__code__
    
    # Just call with return_json=True
    result = await cc_execute(
        "Write a function to calculate factorial and save it to factorial.py",
        config=CCExecutorConfig(timeout=60),
        stream=False,
        return_json=True
    )
    
    print(f"Type: {type(result)}")
    if isinstance(result, dict):
        print(f"\nJSON structure created:")
        print(f"- Summary: {result.get('summary')}")
        print(f"- Files created: {result.get('files_created')}")
        print(f"- Files modified: {result.get('files_modified')}")
        print(f"- Result preview: {result.get('result', '')[:100]}...")

async def test_recommendation():
    """Show the recommended approach."""
    print("\n\nRecommended Approach:")
    print("=" * 60)
    print("""
1. For simple Q&A: Use return_json=False (faster, simpler)
   - Example: "What is 2+2?"
   - Returns: Plain text answer

2. For code generation: Use return_json=True (structured output)
   - Example: "Create a REST API"
   - Returns: {"result": code, "files_created": [...], "summary": "..."}

3. For complex tasks: Always use return_json=True
   - Automatic file detection
   - Structured summary
   - UUID verification
""")

if __name__ == "__main__":
    print("Testing JSON output with fallback conversion...")
    
    asyncio.run(test_with_json_request())
    asyncio.run(test_without_json_request())
    asyncio.run(test_recommendation())