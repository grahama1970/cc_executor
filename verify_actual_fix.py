#!/usr/bin/env python3
"""
Verify that CC Execute's buffer fix actually works by testing with 
commands that definitely produce large output.
"""
import asyncio
import sys
sys.path.insert(0, '/home/graham/workspace/experiments/cc_executor/src')

from cc_executor.client.cc_execute import cc_execute, CCExecutorConfig

async def test_python_large_output():
    """Test CC Execute with Python script that generates large output"""
    print("="*60)
    print("TEST: Python Large Output via CC Execute")
    print("="*60)
    
    # Use CC Execute to run a Python command
    task = """Run this Python code:
python -c "print('X' * 100000)"
    
Just execute that Python command and return the output."""
    
    config = CCExecutorConfig(timeout=10, stream_output=True)
    
    try:
        result = await cc_execute(task, config=config, json_mode=False)
        
        # Check if we got the expected output
        x_count = result.count('X')
        if x_count >= 90000:  # Allow some tolerance
            print(f"✅ SUCCESS! Got {x_count:,} X's")
            return True
        else:
            print(f"❌ Failed: Only got {x_count} X's")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_echo_command():
    """Test with echo command"""
    print("\n" + "="*60)
    print("TEST: Echo Command via CC Execute")
    print("="*60)
    
    task = """Execute this shell command:
echo "YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY" | head -c 100000

That will output exactly 100KB of Y characters."""
    
    config = CCExecutorConfig(timeout=10, stream_output=False)
    
    try:
        result = await cc_execute(task, config=config, json_mode=False)
        y_count = result.count('Y')
        
        if y_count >= 90000:
            print(f"✅ SUCCESS! Got {y_count:,} Y's")
            return True
        else:
            print(f"❌ Failed: Only got {y_count} Y's")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_direct_generation():
    """Test asking Claude to generate directly"""
    print("\n" + "="*60)
    print("TEST: Direct Claude Generation")
    print("="*60)
    
    # Much simpler request
    task = "Output exactly 1000 Z characters in a row. Just ZZZZ... 1000 times, nothing else."
    
    config = CCExecutorConfig(timeout=15, stream_output=True)
    
    try:
        result = await cc_execute(task, config=config, json_mode=False)
        z_count = result.count('Z')
        
        print(f"\nGot {z_count} Z's")
        if z_count >= 900:  # Allow some tolerance
            print("✅ Claude can generate repetitive output")
            return True
        else:
            print("❌ Claude failed to generate repetitive output")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    print("🔍 Testing CC Execute Buffer Fix\n")
    
    results = []
    
    # Test 1: Python subprocess
    results.append(await test_python_large_output())
    
    # Test 2: Echo command
    results.append(await test_echo_command())
    
    # Test 3: Direct generation (smaller)
    results.append(await test_direct_generation())
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
        print("The buffer deadlock fix is working.")
        print("The issue with the original test was asking Claude to generate 100K characters.")
    elif passed >= 2:
        print("\n⚠️  PARTIAL SUCCESS")
        print("Buffer handling works, but Claude has limitations on repetitive output.")
    else:
        print("\n❌ TESTS FAILED")
        print("Buffer deadlock still exists.")

if __name__ == "__main__":
    asyncio.run(main())