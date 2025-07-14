#!/usr/bin/env python3
"""
Simple test to isolate the buffer issue
"""
import asyncio
import subprocess

async def test_buffer_with_python():
    """Test buffer handling with Python instead of Claude"""
    print("Testing buffer handling with Python subprocess...")
    
    # Create a Python command that outputs exactly 100KB
    python_cmd = [
        "python", "-c", 
        "print('A' * 100000, end='')"  # 100KB of 'A' without newline
    ]
    
    # Test with our async subprocess handling
    proc = await asyncio.create_subprocess_exec(
        *python_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    # Read in chunks
    chunks = []
    while True:
        chunk = await proc.stdout.read(8192)
        if not chunk:
            break
        chunks.append(chunk)
        print(f"Read chunk: {len(chunk)} bytes")
    
    output = b''.join(chunks)
    await proc.wait()
    
    print(f"\nTotal output: {len(output)} bytes")
    print(f"First 50 chars: {output[:50]}")
    print(f"Last 50 chars: {output[-50:]}")
    
    if len(output) == 100000 and output == b'A' * 100000:
        print("✅ Buffer handling works correctly!")
        return True
    else:
        print("❌ Buffer handling failed!")
        return False

async def test_with_shell():
    """Test with shell command"""
    print("\n" + "="*60)
    print("Testing with shell command...")
    
    # Use echo to generate large output
    result = subprocess.run(
        ["python", "-c", "print('B' * 100000)"],
        capture_output=True,
        text=True
    )
    
    print(f"Output length: {len(result.stdout)}")
    if len(result.stdout) == 100001:  # 100000 B's + newline
        print("✅ Shell test passed!")
        return True
    else:
        print("❌ Shell test failed!")
        return False

async def main():
    # Test 1: Async subprocess
    test1 = await test_buffer_with_python()
    
    # Test 2: Regular subprocess
    test2 = await test_with_shell()
    
    if test1 and test2:
        print("\n✅ All buffer tests passed! The issue is with Claude, not buffer handling.")
    else:
        print("\n❌ Buffer handling has issues.")

if __name__ == "__main__":
    asyncio.run(main())