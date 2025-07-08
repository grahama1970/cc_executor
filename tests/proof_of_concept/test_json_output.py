#!/usr/bin/env python3
"""Test JSON structured output from cc_execute."""
import asyncio
import json
from executor import cc_execute, CCExecutorConfig

async def test_json_output():
    """Test that cc_execute returns structured JSON."""
    
    print("Testing JSON output mode...")
    print("=" * 60)
    
    # Test simple task with JSON output
    result = await cc_execute(
        "Write a Python function to check if a number is prime",
        config=CCExecutorConfig(timeout=60),
        stream=False,
        return_json=True
    )
    
    print("\nResult type:", type(result))
    
    if isinstance(result, dict):
        print("\n✅ Successfully parsed JSON response!")
        print("\nStructured output:")
        print(f"- Summary: {result.get('summary', 'N/A')}")
        print(f"- Files created: {result.get('files_created', [])}")
        print(f"- Files modified: {result.get('files_modified', [])}")
        print(f"- Execution UUID: {result.get('execution_uuid', 'N/A')}")
        print(f"\nResult preview:")
        print(result.get('result', '')[:200] + "...")
        
        # Verify all required fields
        required_fields = ['result', 'summary', 'execution_uuid']
        missing = [f for f in required_fields if f not in result]
        if missing:
            print(f"\n⚠️  Missing required fields: {missing}")
        else:
            print("\n✅ All required fields present!")
            
    else:
        print("\n❌ Failed to parse JSON, got string:")
        print(result[:200] + "...")
        
async def test_complex_json_task():
    """Test JSON output with a complex task."""
    
    print("\n\nTesting complex task with JSON output...")
    print("=" * 60)
    
    result = await cc_execute(
        """Create a Python class for a binary search tree with the following methods:
        - insert(value)
        - search(value) 
        - delete(value)
        - inorder_traversal()
        Include proper error handling and docstrings.""",
        config=CCExecutorConfig(timeout=120),
        stream=False,
        return_json=True
    )
    
    if isinstance(result, dict):
        print("\n✅ Complex task returned JSON!")
        print(f"Summary: {result.get('summary', 'N/A')}")
        
        # Show the code structure
        code = result.get('result', '')
        if 'class' in code and 'def' in code:
            print("\n✅ Generated valid Python class structure")
            # Count methods
            method_count = code.count('def ')
            print(f"Methods defined: {method_count}")
    else:
        print("\n❌ Complex task failed to return JSON")

async def test_json_vs_string():
    """Compare JSON vs string output modes."""
    
    print("\n\nComparing JSON vs String output modes...")
    print("=" * 60)
    
    task = "Write a one-line Python function to reverse a string"
    
    # Get string output
    print("\n1. String mode:")
    string_result = await cc_execute(
        task,
        config=CCExecutorConfig(timeout=60),
        stream=False,
        return_json=False
    )
    print(f"Type: {type(string_result)}")
    print(f"Preview: {string_result[:100]}...")
    
    # Get JSON output
    print("\n2. JSON mode:")
    json_result = await cc_execute(
        task,
        config=CCExecutorConfig(timeout=60),
        stream=False,
        return_json=True
    )
    print(f"Type: {type(json_result)}")
    if isinstance(json_result, dict):
        print(f"Keys: {list(json_result.keys())}")
        print(f"Summary: {json_result.get('summary', 'N/A')}")

if __name__ == "__main__":
    print("Testing cc_execute JSON output functionality...")
    
    # Run all tests
    asyncio.run(test_json_output())
    asyncio.run(test_complex_json_task())
    asyncio.run(test_json_vs_string())