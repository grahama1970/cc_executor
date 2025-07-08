#!/usr/bin/env python3
import asyncio
from executor import cc_execute

async def main():
    print("Running simple cc_executor test...")
    print("=" * 60)
    
    # Test 1: Simple math
    result = await cc_execute(
        "What is 2 + 2?",
        stream=True,
        return_json=True,
        amend_prompt=True
    )
    print(f"\nTest 1 Result: {result}")
    
    # Test 2: Simple code generation  
    result = await cc_execute(
        "Write a Python function to add two numbers",
        stream=True,
        return_json=True,
        amend_prompt=True,
        generate_report=True
    )
    print(f"\nTest 2 Result: {result.get('summary') if isinstance(result, dict) else 'Failed'}")
    
    print("\n" + "=" * 60)
    print("Tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
