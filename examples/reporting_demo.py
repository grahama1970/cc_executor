#!/usr/bin/env python3
"""
Demonstration of JSON-based reporting for CC Executor.

This example shows why JSON mode is REQUIRED for verifiable reporting:
1. JSON responses include the execution UUID
2. The UUID proves the execution actually happened
3. Reports can be generated from the structured JSON data
"""

import asyncio
import json
from pathlib import Path
from cc_executor.client.cc_execute import cc_execute
from cc_executor.reporting import generate_json_report, check_hallucination


async def main():
    print("🔐 CC Executor JSON Reporting Demo")
    print("=" * 60)
    
    # Example 1: WITHOUT JSON mode (NOT verifiable)
    print("\n❌ Example 1: Without JSON mode (NOT RECOMMENDED)")
    print("-" * 40)
    
    task1 = "What is 2 + 2?"
    result1 = await cc_execute(task1, json_mode=False)  # No JSON structure
    
    print(f"Task: {task1}")
    print(f"Result: {result1}")
    print("⚠️  Problem: No structured data, no UUID verification!")
    
    # Example 2: WITH JSON mode (Verifiable)
    print("\n✅ Example 2: With JSON mode (RECOMMENDED)")
    print("-" * 40)
    
    task2 = """What is 2 + 2? 
    Return JSON: {"calculation": "2 + 2", "result": 4, "explanation": "Basic addition"}"""
    
    result2 = await cc_execute(task2, json_mode=True)
    
    print(f"Task: {task2}")
    print(f"\nRaw Result:")
    print(json.dumps(result2, indent=2))
    
    # The result includes execution_uuid for verification
    if "result" in result2:
        print(f"\n📊 Parsed JSON Response:")
        print(json.dumps(result2["result"], indent=2))
    
    # Example 3: Complex task with JSON schema
    print("\n🎯 Example 3: Complex task with JSON schema")
    print("-" * 40)
    
    task3 = """Write a Python function to check if a number is prime.
    Return JSON with this schema:
    {
        "function_name": "is_prime",
        "parameters": [{"name": "n", "type": "int", "description": "Number to check"}],
        "code": "def is_prime(n):\\n    # implementation here",
        "test_cases": [
            {"input": 7, "expected": true},
            {"input": 10, "expected": false}
        ],
        "complexity": "O(sqrt(n))"
    }"""
    
    result3 = await cc_execute(task3, json_mode=True)
    
    if "result" in result3:
        # Extract the structured data
        from cc_executor.utils.json_utils import clean_json_string
        parsed = clean_json_string(result3["result"], return_dict=True)
        
        if isinstance(parsed, dict):
            print(f"Function Name: {parsed.get('function_name')}")
            print(f"Complexity: {parsed.get('complexity')}")
            
            # Save the generated code
            if "code" in parsed:
                with open("is_prime_generated.py", "w") as f:
                    f.write(parsed["code"])
                print("💾 Code saved to: is_prime_generated.py")
    
    # Verify executions
    print("\n🔍 Verification")
    print("-" * 40)
    
    # Check last 3 executions
    verification = check_hallucination(last_n=3, require_json=True)
    
    print(f"Verification Status: {verification['status']}")
    print(f"Files Checked: {verification.get('checked_files', 0)}")
    
    for v in verification.get('verifications', []):
        if 'error' in v:
            print(f"- {v['file']}: ❌ {v['error']}")
        else:
            print(f"- {v['file']}: ✅ Valid JSON: {v['json_valid']}, UUID Verified: {v.get('uuid_verified', False)}")
    
    # Generate JSON report
    print("\n📄 Generating JSON Report")
    print("-" * 40)
    
    try:
        report_path = generate_json_report(last_n=3)
        print(f"✅ Report generated: {report_path}")
        print(f"\nView the report to see:")
        print("- Structured JSON responses")
        print("- Execution UUIDs for verification")
        print("- Task inputs and outputs")
        print("- Independent verification instructions")
    except Exception as e:
        print(f"❌ Could not generate report: {e}")
    
    print("\n" + "=" * 60)
    print("🎓 Key Takeaways:")
    print("1. ALWAYS use json_mode=True for verifiable executions")
    print("2. JSON responses include execution_uuid for anti-hallucination")
    print("3. Structured data enables automated report generation")
    print("4. Reports can only be generated from JSON responses")


if __name__ == "__main__":
    asyncio.run(main())