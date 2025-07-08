#!/usr/bin/env python3
"""
Test streaming JSON output from cc_execute.
"""

import asyncio
import json
from executor import cc_execute

async def test_streaming_json():
    """Test that we get proper streaming JSON output."""
    print("Testing streaming JSON output...")
    print("=" * 60)
    
    task = "What is 2 + 2?"
    
    # Run with streaming JSON
    result = await cc_execute(
        task,
        stream=True,
        return_json=True,
        amend_prompt=True
    )
    
    print(f"\nResult type: {type(result)}")
    print(f"\nRaw result:")
    print(result)
    
    if isinstance(result, dict):
        print(f"\nParsed JSON result:")
        print(json.dumps(result, indent=2))
        
        # Check expected fields
        print(f"\nJSON fields present:")
        for field in ['result', 'files_created', 'files_modified', 'summary', 'execution_uuid']:
            print(f"  - {field}: {'✓' if field in result else '✗'}")
    else:
        print(f"\nResult is string, length: {len(result)}")
        # Try to parse as JSON
        try:
            parsed = json.loads(result)
            print(f"\nString contains valid JSON:")
            print(json.dumps(parsed, indent=2))
        except:
            print("\nString is not valid JSON")

if __name__ == "__main__":
    asyncio.run(test_streaming_json())
