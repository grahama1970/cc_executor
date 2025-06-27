#!/usr/bin/env python3
"""Test WebSocket environment - diagnose why claude commands fail"""

import asyncio
import json
import websockets
import sys
import os

async def test_websocket_env():
    """Test what environment the WebSocket handler provides to subprocesses"""
    
    uri = "ws://localhost:8003/ws/mcp"  # Main server on port 8003 with /ws/mcp endpoint
    
    print("=" * 80)
    print("WEBSOCKET ENVIRONMENT DIAGNOSTIC")
    print("=" * 80)
    print(f"Connecting to: {uri}")
    print()
    
    try:
        async with websockets.connect(uri) as websocket:
            # Test 1: Check environment variables
            print("Test 1: Checking process environment...")
            request = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {"command": "env | sort"},
                "id": "env-test-1"
            }
            
            await websocket.send(json.dumps(request))
            
            env_output = []
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                
                if data.get("method") == "process.output":
                    output = data["params"]["data"].strip()
                    if output:
                        env_output.append(output)
                elif data.get("method") == "process.completed":
                    print(f"✓ Process completed with exit code: {data['params'].get('exit_code')}")
                    break
                elif data.get("error"):
                    print(f"✗ Error: {data['error']}")
                    break
            
            # Check for critical environment variables
            print("\nEnvironment Analysis:")
            print("-" * 40)
            
            env_dict = {}
            for line in env_output:
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_dict[key] = value
            
            # Check for API keys
            api_keys = ['ANTHROPIC_API_KEY', 'GITHUB_TOKEN', 'OPENAI_API_KEY']
            for key in api_keys:
                if key in env_dict:
                    print(f"✓ {key}: {'*' * 8} (present)")
                else:
                    print(f"✗ {key}: NOT FOUND")
            
            # Check PATH
            if 'PATH' in env_dict:
                print(f"\n✓ PATH: {env_dict['PATH'][:80]}...")
            else:
                print("\n✗ PATH: NOT FOUND")
            
            # Check PWD
            if 'PWD' in env_dict:
                print(f"✓ PWD: {env_dict['PWD']}")
            else:
                print("✗ PWD: NOT FOUND")
            
            print("\n" + "-" * 40)
            
            # Test 2: Check current working directory
            print("\nTest 2: Checking working directory...")
            request = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {"command": "pwd && ls -la .mcp.json 2>&1 || echo 'No .mcp.json found'"},
                "id": "pwd-test-2"
            }
            
            await websocket.send(json.dumps(request))
            
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                
                if data.get("method") == "process.output":
                    output = data["params"]["data"].strip()
                    if output:
                        print(f"Output: {output}")
                elif data.get("method") == "process.completed":
                    break
            
            # Test 3: Try to run claude with just --help
            print("\nTest 3: Testing claude --help...")
            request = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {"command": "claude --help 2>&1 || echo 'claude command not found'"},
                "id": "claude-help-test-3"
            }
            
            await websocket.send(json.dumps(request))
            
            claude_found = False
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                
                if data.get("method") == "process.output":
                    output = data["params"]["data"].strip()
                    if output:
                        if "claude command not found" in output:
                            print("✗ Claude command not found in PATH")
                        elif "usage:" in output.lower() or "claude" in output.lower():
                            claude_found = True
                            print("✓ Claude command is available")
                elif data.get("method") == "process.completed":
                    break
            
            # Test 4: Check which claude
            if claude_found:
                print("\nTest 4: Checking claude location...")
                request = {
                    "jsonrpc": "2.0",
                    "method": "execute",
                    "params": {"command": "which claude"},
                    "id": "which-claude-test-4"
                }
                
                await websocket.send(json.dumps(request))
                
                while True:
                    response = await websocket.recv()
                    data = json.loads(response)
                    
                    if data.get("method") == "process.output":
                        output = data["params"]["data"].strip()
                        if output:
                            print(f"Claude location: {output}")
                    elif data.get("method") == "process.completed":
                        break
            
            print("\n" + "=" * 80)
            print("DIAGNOSTIC SUMMARY:")
            print("=" * 80)
            
            # Summary
            missing_items = []
            if 'ANTHROPIC_API_KEY' not in env_dict:
                missing_items.append("ANTHROPIC_API_KEY")
            if not os.path.exists('.mcp.json'):
                missing_items.append(".mcp.json file")
            if not claude_found:
                missing_items.append("claude command in PATH")
            
            if missing_items:
                print("\n⚠️  Missing critical items:")
                for item in missing_items:
                    print(f"   - {item}")
                print("\nThese missing items explain why the claude command times out.")
                print("The process starts but exits immediately due to missing dependencies.")
            else:
                print("\n✓ All critical items appear to be present.")
                print("The timeout might be due to Claude taking a long time to generate the story.")
            
    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure the WebSocket server is running:")
        print("  python -m src.cc_executor.core.main")


if __name__ == "__main__":
    print("Running WebSocket environment diagnostic...")
    print("This will help identify why claude commands fail in the WebSocket handler.\n")
    asyncio.run(test_websocket_env())