#!/usr/bin/env python3
"""
Test the local MCP server implementation for CC Executor.
"""

import asyncio
import subprocess
import json
import sys
from pathlib import Path

# Add to path for imports
sys.path.insert(0, str(Path(__file__).parent))


async def test_mcp_stdio():
    """Test MCP server via stdio protocol."""
    print("🧪 Testing CC Executor MCP Server via stdio...")
    
    # Start the MCP server as a subprocess
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "src.cc_executor.servers.mcp_cc_execute",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=Path(__file__).parent
    )
    
    try:
        # Test 1: Initialize request
        print("\n📤 Sending initialize request...")
        initialize_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "0.1.0",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            },
            "id": 1
        }
        
        # Send request
        proc.stdin.write((json.dumps(initialize_request) + "\n").encode())
        await proc.stdin.drain()
        
        # Read response
        response_line = await proc.stdout.readline()
        response = json.loads(response_line.decode())
        print(f"📥 Initialize response: {json.dumps(response, indent=2)}")
        
        # Test 2: List tools
        print("\n📤 Requesting tool list...")
        list_tools_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        }
        
        proc.stdin.write((json.dumps(list_tools_request) + "\n").encode())
        await proc.stdin.drain()
        
        response_line = await proc.stdout.readline()
        response = json.loads(response_line.decode())
        print(f"📥 Tools available:")
        if "result" in response and "tools" in response["result"]:
            for tool in response["result"]["tools"]:
                print(f"  - {tool['name']}: {tool['description'][:60]}...")
        
        # Test 3: Execute a simple task
        print("\n📤 Testing execute_task tool...")
        execute_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "execute_task",
                "arguments": {
                    "task": "What is 2+2?",
                    "json_mode": False,
                    "timeout": 30
                }
            },
            "id": 3
        }
        
        proc.stdin.write((json.dumps(execute_request) + "\n").encode())
        await proc.stdin.drain()
        
        # This might take a moment
        print("⏳ Waiting for execution (this may take 10-20 seconds)...")
        response_line = await asyncio.wait_for(proc.stdout.readline(), timeout=60)
        response = json.loads(response_line.decode())
        
        if "result" in response:
            result = response["result"]
            if isinstance(result, list) and len(result) > 0:
                content = result[0].get("content", {})
                print(f"📥 Execution result: {json.dumps(content, indent=2)}")
            else:
                print(f"📥 Result: {result}")
        elif "error" in response:
            print(f"❌ Error: {response['error']}")
        
        # Test 4: Get status
        print("\n📤 Getting executor status...")
        status_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "get_executor_status",
                "arguments": {}
            },
            "id": 4
        }
        
        proc.stdin.write((json.dumps(status_request) + "\n").encode())
        await proc.stdin.drain()
        
        response_line = await proc.stdout.readline()
        response = json.loads(response_line.decode())
        if "result" in response:
            result = response["result"]
            if isinstance(result, list) and len(result) > 0:
                content = result[0].get("content", {})
                print(f"📥 Status: {json.dumps(content, indent=2)}")
        
        print("\n✅ MCP server is working correctly!")
        
    except asyncio.TimeoutError:
        print("❌ Timeout waiting for response")
        # Check stderr for errors
        stderr = await proc.stderr.read()
        if stderr:
            print(f"Server errors:\n{stderr.decode()}")
    except Exception as e:
        print(f"❌ Error: {e}")
        # Check stderr
        stderr = await proc.stderr.read()
        if stderr:
            print(f"Server errors:\n{stderr.decode()}")
    finally:
        # Clean up
        proc.terminate()
        await proc.wait()


async def test_mcp_tools_directly():
    """Test MCP tools by importing and calling directly."""
    print("\n🧪 Testing MCP tools directly...")
    
    try:
        from src.cc_executor.servers.mcp_cc_execute import (
            execute_task, 
            get_executor_status,
            analyze_task_complexity
        )
        
        # Test 1: Status check
        print("\n📋 Checking executor status...")
        status = await get_executor_status()
        print(f"Status: {json.dumps(status, indent=2)}")
        
        # Test 2: Analyze complexity
        print("\n🔍 Analyzing task complexity...")
        complexity = await analyze_task_complexity("Write a Python function to calculate fibonacci numbers")
        print(f"Complexity: {json.dumps(complexity, indent=2)}")
        
        # Test 3: Execute simple task
        print("\n🚀 Executing simple task...")
        result = await execute_task(
            task="What is the capital of France?",
            json_mode=False,
            timeout=30
        )
        print(f"Result: {json.dumps(result, indent=2)}")
        
        print("\n✅ Direct tool tests passed!")
        
    except Exception as e:
        print(f"❌ Error testing tools directly: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all MCP tests."""
    print("=" * 60)
    print("CC Executor MCP Server Test")
    print("=" * 60)
    
    # Test stdio protocol
    await test_mcp_stdio()
    
    # Test tools directly
    await test_mcp_tools_directly()
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())