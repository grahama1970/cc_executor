#!/usr/bin/env python3
"""
Quickstart Example - Your first CC Executor task with JSON responses.

This example shows how to get structured JSON responses that can be
easily parsed and used in your Python code.
"""

import asyncio
import json
from cc_executor.client.cc_execute import cc_execute


async def main():
    print("🚀 CC Executor Quickstart Example")
    print("=" * 50)
    
    # Request a structured JSON response
    task = """Write a Python function to calculate fibonacci numbers with memoization.
    Return your response as JSON with this exact schema:
    {
        "function_name": "fibonacci",
        "description": "Calculate nth fibonacci number with memoization",
        "parameters": [
            {"name": "n", "type": "int", "description": "The position in sequence"}
        ],
        "returns": {"type": "int", "description": "The nth fibonacci number"},
        "code": "def fibonacci(n, memo={}):\\n    # function implementation here",
        "example_usage": "result = fibonacci(10)  # Returns 55",
        "time_complexity": "O(n)"
    }"""
    
    print(f"\n📋 Task: Requesting fibonacci function with JSON schema")
    print("\n⏳ Executing with json_mode=True...")
    
    # Execute with JSON mode
    result = await cc_execute(task, json_mode=True)
    
    print("\n✅ Raw Result:")
    print("-" * 50)
    print(json.dumps(result, indent=2))
    print("-" * 50)
    
    # Extract the actual response data
    if "result" in result and isinstance(result["result"], dict):
        func_data = result["result"]
        
        print("\n📊 Extracted Function Details:")
        print(f"Function Name: {func_data.get('function_name', 'N/A')}")
        print(f"Description: {func_data.get('description', 'N/A')}")
        print(f"Time Complexity: {func_data.get('time_complexity', 'N/A')}")
        
        # Save the code
        if "code" in func_data:
            with open("fibonacci_generated.py", "w") as f:
                f.write(func_data["code"])
                if "example_usage" in func_data:
                    f.write(f"\n\n# Example usage:\n# {func_data['example_usage']}")
            print("\n💾 Code saved to: fibonacci_generated.py")
    
    print("\n🎉 Done! The JSON response makes it easy to extract and use the generated code.")


if __name__ == "__main__":
    asyncio.run(main())