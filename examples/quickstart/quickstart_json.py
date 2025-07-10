#!/usr/bin/env python3
"""
Quickstart Example with JSON Response - Your first CC Executor task.

This example shows how to use json_mode=True to get structured responses
that can be easily parsed by Python code.
"""

import asyncio
import json
from cc_executor.client.cc_execute import cc_execute


async def main():
    print("🚀 CC Executor Quickstart Example (JSON Mode)")
    print("=" * 50)
    
    # Execute a single task with JSON response
    task = """Write a Python function to calculate fibonacci numbers with memoization.
    Return a JSON response with this schema:
    {
        "function_name": "string",
        "description": "string", 
        "code": "string (the complete function code)",
        "example_usage": "string (how to use it)",
        "time_complexity": "string (e.g. O(n))"
    }"""
    
    print(f"\n📋 Task: {task}")
    print("\n⏳ Executing with json_mode=True...")
    
    # Get structured JSON response
    result = await cc_execute(task, json_mode=True)
    
    print("\n✅ JSON Response:")
    print("-" * 50)
    print(json.dumps(result, indent=2))
    print("-" * 50)
    
    # Extract fields from the response
    if "result" in result:
        data = result["result"]
        print("\n📊 Extracted Fields:")
        print(f"Function Name: {data.get('function_name', 'N/A')}")
        print(f"Description: {data.get('description', 'N/A')}")
        print(f"Time Complexity: {data.get('time_complexity', 'N/A')}")
        
        # Save the code to a file
        if "code" in data:
            with open("fibonacci_generated.py", "w") as f:
                f.write(data["code"])
            print("\n💾 Code saved to: fibonacci_generated.py")
    
    print("\n🎉 Done! Check out the other examples to learn more.")


if __name__ == "__main__":
    asyncio.run(main())