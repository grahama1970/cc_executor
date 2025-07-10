#!/usr/bin/env python3
"""
Test MCP server functionality for CC Executor.
This verifies that the MCP tools are working correctly.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp.client.stdio import StdioServerConnection
from mcp.client import Client
from mcp import ClientSession


async def test_mcp_server():
    """Test MCP server functionality."""
    print("🧪 Testing CC Executor MCP Server...")
    print("=" * 60)
    
    # Create connection to MCP server
    server = StdioServerConnection(
        command="python",
        args=["-m", "cc_executor.servers.mcp_cc_execute"],
        cwd=str(Path(__file__).parent.parent)
    )
    
    async with server:
        client = Client(server)
        
        # Initialize client
        session = await client.initialize_session(
            client_info={
                "name": "test-client",
                "version": "1.0.0"
            }
        )
        
        print("✅ Connected to MCP server")
        print(f"Server: {session.server_info.name} v{session.server_info.version}")
        
        # List available tools
        print("\n📋 Available Tools:")
        print("-" * 40)
        
        tools = await client.list_tools()
        for tool in tools:
            print(f"  • {tool.name}: {tool.description}")
        
        # Test 1: Execute a simple task
        print("\n🔧 Test 1: Simple cc_execute call")
        print("-" * 40)
        
        try:
            result = await client.call_tool(
                "cc_execute",
                {
                    "task": "Calculate 2 + 2 and return JSON: {\"calculation\": \"2 + 2\", \"result\": 4}",
                    "json_mode": True,
                    "timeout": 30
                }
            )
            print(f"✅ Result: {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 2: Verify execution
        print("\n🔧 Test 2: Verify last execution")
        print("-" * 40)
        
        try:
            verification = await client.call_tool(
                "verify_execution",
                {
                    "last_n": 1,
                    "generate_report": False
                }
            )
            print(f"✅ Verification: {json.dumps(verification, indent=2)}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 3: Generate report
        print("\n🔧 Test 3: Generate anti-hallucination report")
        print("-" * 40)
        
        try:
            report = await client.call_tool(
                "verify_execution",
                {
                    "last_n": 1,
                    "generate_report": True
                }
            )
            print(f"✅ Report generated: {report.get('report_path', 'N/A')}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("\n" + "=" * 60)
        print("✅ MCP Server Tests Complete!")


async def test_mcp_resources():
    """Test MCP resource functionality."""
    print("\n📚 Testing MCP Resources...")
    print("=" * 60)
    
    server = StdioServerConnection(
        command="python",
        args=["-m", "cc_executor.servers.mcp_cc_execute"],
        cwd=str(Path(__file__).parent.parent)
    )
    
    async with server:
        client = Client(server)
        await client.initialize_session(
            client_info={
                "name": "test-client",
                "version": "1.0.0"
            }
        )
        
        # List resources
        resources = await client.list_resources()
        
        print(f"Found {len(resources)} resources:")
        for resource in resources[:5]:  # Show first 5
            print(f"  • {resource.uri}: {resource.name}")
        
        if resources:
            # Read first resource
            print(f"\n📖 Reading resource: {resources[0].uri}")
            content = await client.read_resource(resources[0].uri)
            print(f"Content preview: {str(content)[:200]}...")


async def main():
    """Run all MCP tests."""
    try:
        await test_mcp_server()
        await test_mcp_resources()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)