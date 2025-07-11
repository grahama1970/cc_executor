#!/usr/bin/env python3
"""
Test script to verify all 4 fixes for CC Execute issues.

Tests:
1. Output buffer deadlock fix
2. Execution time improvements (progress monitoring)
3. Partial results on timeout
4. JSON mode parsing robustness
"""

import asyncio
import time
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cc_executor.core.executor import cc_execute, CCExecutorConfig

async def test_buffer_deadlock():
    """Test Fix 1: Output buffer deadlock with large output."""
    print("\n" + "="*60)
    print("TEST 1: Output Buffer Deadlock Fix")
    print("="*60)
    
    # Task that generates >64KB of output
    task = """Generate 100 paragraphs of Lorem Ipsum text.
Each paragraph should be at least 200 words long.
Start each paragraph with a number (1, 2, 3, etc.)"""
    
    try:
        start = time.time()
        result = await cc_execute(
            task,
            config=CCExecutorConfig(timeout=60),
            stream=True
        )
        elapsed = time.time() - start
        
        print(f"\n✅ SUCCESS: Task completed in {elapsed:.1f}s")
        print(f"Output size: {len(result)} characters")
        print(f"First 200 chars: {result[:200]}...")
        return True
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        return False

async def test_execution_time():
    """Test Fix 2: Execution time monitoring."""
    print("\n" + "="*60)
    print("TEST 2: Execution Time Monitoring")
    print("="*60)
    
    # Simple task to test timing
    task = "What is 2+2? Answer in one line."
    
    try:
        start = time.time()
        
        # Test with progress monitoring
        print("Testing execution with progress monitoring...")
        result = await cc_execute(
            task,
            config=CCExecutorConfig(timeout=30),
            stream=True
        )
        elapsed = time.time() - start
        
        print(f"\n✅ SUCCESS: Simple task completed in {elapsed:.1f}s")
        print(f"Result: {result.strip()}")
        
        # Should be much faster than 60s
        if elapsed < 15:
            print("✅ Performance is good (<15s for simple task)")
            return True
        else:
            print(f"⚠️  Performance needs improvement ({elapsed:.1f}s > 15s)")
            return False
            
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        return False

async def test_partial_results():
    """Test Fix 3: Partial results on timeout."""
    print("\n" + "="*60)
    print("TEST 3: Partial Results on Timeout")
    print("="*60)
    
    # Task that will timeout but should return partial results
    task = """Process these 10 items one by one, taking 5 seconds each:
1. Calculate fibonacci(10)
2. Calculate factorial(20)
3. List prime numbers up to 100
4. Generate 10 random UUIDs
5. Create a multiplication table 10x10
6. List perfect squares up to 1000
7. Calculate powers of 2 up to 2^20
8. Generate the alphabet backwards
9. Count from 100 to 1
10. Say "DONE!"

For each item, print "Processing item X..." then the result."""
    
    try:
        start = time.time()
        result = await cc_execute(
            task,
            config=CCExecutorConfig(timeout=15),  # Will timeout before completing all
            stream=True
        )
        elapsed = time.time() - start
        
        print(f"\n✅ Partial results returned after {elapsed:.1f}s timeout")
        print(f"Result type: {type(result)}")
        print(f"Result length: {len(str(result))} characters")
        
        # Check if we got partial results
        if "[TIMEOUT:" in str(result) or "partial" in str(result).lower():
            print("✅ Timeout marker found in results")
            lines = str(result).split('\n')
            completed_items = sum(1 for line in lines if "Processing item" in line)
            print(f"✅ Completed {completed_items} items before timeout")
            return True
        else:
            print("⚠️  No timeout marker found")
            return False
            
    except TimeoutError:
        print("\n❌ FAILED: Got TimeoutError instead of partial results")
        return False
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        return False

async def test_json_parsing():
    """Test Fix 4: Robust JSON parsing."""
    print("\n" + "="*60)
    print("TEST 4: JSON Mode Parsing Robustness")
    print("="*60)
    
    # Test various JSON response formats
    test_cases = [
        # Case 1: Clean JSON
        {
            "name": "Clean JSON",
            "task": "Return exactly this JSON: {\"result\": \"test\", \"value\": 42}"
        },
        # Case 2: JSON in markdown block
        {
            "name": "Markdown JSON",
            "task": """Return this JSON in a markdown code block:
```json
{
  "result": "Hello World",
  "numbers": [1, 2, 3]
}
```"""
        },
        # Case 3: JSON with extra text
        {
            "name": "JSON with text",
            "task": """First say "Here's the JSON response:" then return:
{"result": "mixed content", "status": "ok"}
Then say "That's all!"."""
        }
    ]
    
    all_passed = True
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        try:
            result = await cc_execute(
                test_case['task'],
                config=CCExecutorConfig(timeout=30),
                json_mode=True,
                stream=False
            )
            
            if isinstance(result, dict):
                print(f"✅ Successfully parsed JSON: {result}")
                if 'result' in result:
                    print(f"   Result field: {result['result']}")
            else:
                print(f"❌ Expected dict, got {type(result)}")
                all_passed = False
                
        except Exception as e:
            print(f"❌ Failed to parse: {e}")
            all_passed = False
    
    return all_passed

async def main():
    """Run all tests and report results."""
    print("\n🧪 CC EXECUTE FIXES TEST SUITE")
    print("Testing all 4 critical fixes...")
    
    results = []
    
    # Test 1: Buffer deadlock
    try:
        passed = await test_buffer_deadlock()
        results.append(("Buffer Deadlock Fix", passed))
    except Exception as e:
        results.append(("Buffer Deadlock Fix", False))
        print(f"Exception in test 1: {e}")
    
    # Test 2: Execution time
    try:
        passed = await test_execution_time()
        results.append(("Execution Time", passed))
    except Exception as e:
        results.append(("Execution Time", False))
        print(f"Exception in test 2: {e}")
    
    # Test 3: Partial results
    try:
        passed = await test_partial_results()
        results.append(("Partial Results", passed))
    except Exception as e:
        results.append(("Partial Results", False))
        print(f"Exception in test 3: {e}")
    
    # Test 4: JSON parsing
    try:
        passed = await test_json_parsing()
        results.append(("JSON Parsing", passed))
    except Exception as e:
        results.append(("JSON Parsing", False))
        print(f"Exception in test 4: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! Fixes are working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)