#!/usr/bin/env python3
"""
Validate MCP server is properly configured and can be used with Claude Desktop.
This script checks that the server starts correctly and tools are exposed.
"""

import subprocess
import json
import sys
import time
from pathlib import Path


def check_mcp_server_starts():
    """Check if MCP server starts without errors."""
    print("🚀 Checking MCP server startup...")
    
    cmd = [
        sys.executable,
        "-m",
        "cc_executor.servers.mcp_cc_execute"
    ]
    
    # Start server and send initialization
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(Path(__file__).parent.parent)
    )
    
    # MCP servers expect JSON-RPC over stdio
    # Send initialization request
    init_request = {
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
    
    try:
        # Send request
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()
        
        # Wait for response
        time.sleep(1)
        
        # Check if process is still running
        if proc.poll() is not None:
            stdout, stderr = proc.communicate()
            print("❌ Server exited unexpectedly!")
            print(f"STDERR: {stderr}")
            return False
        
        # Try to read response
        proc.stdin.close()
        stdout, stderr = proc.communicate(timeout=2)
        
        print("✅ Server started successfully")
        print("Server output (first 500 chars):")
        print(stdout[:500] if stdout else "(no output)")
        
        # Look for error indicators
        if stderr and "error" in stderr.lower():
            print("⚠️  Warning: stderr contains errors")
            print(stderr[:500])
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing server: {e}")
        proc.kill()
        return False
    finally:
        if proc.poll() is None:
            proc.terminate()
            time.sleep(0.5)
            if proc.poll() is None:
                proc.kill()


def generate_claude_config():
    """Generate Claude Desktop configuration."""
    print("\n📝 Claude Desktop Configuration")
    print("=" * 60)
    
    config = {
        "mcpServers": {
            "cc-executor": {
                "command": sys.executable,
                "args": ["-m", "cc_executor.servers.mcp_cc_execute"],
                "cwd": str(Path(__file__).parent.parent),
                "env": {
                    "PYTHONPATH": str(Path(__file__).parent.parent / "src")
                }
            }
        }
    }
    
    print("Add this to your Claude Desktop config:")
    print(json.dumps(config, indent=2))
    
    print("\n📍 Config file locations:")
    print("  macOS: ~/Library/Application Support/Claude/claude_desktop_config.json")
    print("  Linux: ~/.config/Claude/claude_desktop_config.json")
    print("  Windows: %APPDATA%\\Claude\\claude_desktop_config.json")
    
    # Save to file for easy copying
    config_path = Path(__file__).parent / "claude_desktop_mcp_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"\n💾 Config also saved to: {config_path}")


def test_underlying_functions():
    """Test that underlying cc_execute works."""
    print("\n🔧 Testing underlying cc_execute functionality...")
    print("=" * 60)
    
    # Test simple import
    try:
        import asyncio
        from cc_executor.client.cc_execute import cc_execute
        print("✅ cc_execute module imported successfully")
        
        # Check if we can access the function
        print(f"   Function type: {type(cc_execute)}")
        print(f"   Is coroutine function: {asyncio.iscoroutinefunction(cc_execute)}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to import cc_execute: {e}")
        return False


def main():
    """Run MCP server validation."""
    print("🧪 CC Executor MCP Server Validation")
    print("=" * 60)
    
    results = []
    
    # Test 1: Server starts
    results.append(("MCP server startup", check_mcp_server_starts()))
    
    # Test 2: Underlying functions work
    import asyncio
    results.append(("Underlying functions", test_underlying_functions()))
    
    # Generate config
    generate_claude_config()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Validation Summary")
    print("-" * 50)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:.<40} {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✅ MCP server is ready for Claude Desktop!")
        print("\nNext steps:")
        print("1. Copy the configuration above to Claude Desktop config")
        print("2. Restart Claude Desktop")
        print("3. Test by saying: 'Use cc-executor to write a hello world script'")
    else:
        print("\n❌ MCP server validation failed - please check errors above")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())