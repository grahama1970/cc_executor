#!/usr/bin/env python3
"""
MCP Client utilities for calling MCP tools from within Python code.

This provides a simple interface to call MCP server tools programmatically.
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger


async def call_mcp_tool(server: str, tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call an MCP tool and return the result.
    
    Args:
        server: Name of the MCP server (e.g., 'litellm_request', 'llm_instance')
        tool: Name of the tool to call
        args: Arguments to pass to the tool
        
    Returns:
        Result dictionary from the tool
    """
    try:
        # Find the MCP server script
        server_paths = [
            Path(__file__).parent.parent / "servers" / f"mcp_{server}.py",
            Path(__file__).parent.parent / "servers" / f"{server}.py",
            Path(__file__).parent.parent.parent / "resume" / "servers" / f"mcp_{server}.py",
        ]
        
        server_path = None
        for path in server_paths:
            if path.exists():
                server_path = path
                break
                
        if not server_path:
            logger.error(f"MCP server not found: {server}")
            return {"success": False, "error": f"MCP server not found: {server}"}
            
        # Try direct Python import first (faster)
        try:
            return await _call_mcp_direct(server_path, tool, args)
        except Exception as e:
            logger.warning(f"Direct call failed, trying subprocess: {e}")
            return await _call_mcp_subprocess(server_path, tool, args)
            
    except Exception as e:
        logger.error(f"MCP call failed: {e}")
        return {"success": False, "error": str(e)}


async def _call_mcp_direct(server_path: Path, tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Try to call MCP tool directly by importing the module."""
    # Add server directory to path
    sys.path.insert(0, str(server_path.parent))
    
    try:
        # Import the module
        module_name = server_path.stem
        module = __import__(module_name)
        
        # Look for the tool function
        tool_func = None
        
        # Check if it's using FastMCP
        if hasattr(module, 'mcp'):
            mcp = module.mcp
            if hasattr(mcp, '_tools'):
                for t in mcp._tools:
                    if t.name == tool:
                        tool_func = t.fn
                        break
                        
        # Fallback to direct function lookup
        if not tool_func:
            tool_func = getattr(module, tool, None)
            
        if not tool_func:
            raise ValueError(f"Tool '{tool}' not found in {module_name}")
            
        # Call the tool
        if asyncio.iscoroutinefunction(tool_func):
            result = await tool_func(**args)
        else:
            result = tool_func(**args)
            
        # Convert result to dict if it's a string
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except:
                result = {"result": result}
                
        return result
        
    finally:
        # Remove from path
        if str(server_path.parent) in sys.path:
            sys.path.remove(str(server_path.parent))


async def _call_mcp_subprocess(server_path: Path, tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Call MCP tool via subprocess as a fallback."""
    # Create a test script that imports and calls the tool
    test_script = f"""
import asyncio
import json
import sys
sys.path.insert(0, "{server_path.parent}")

async def main():
    from {server_path.stem} import {tool}
    
    args = {json.dumps(args)}
    
    # Call the tool
    if asyncio.iscoroutinefunction({tool}):
        result = await {tool}(**args)
    else:
        result = {tool}(**args)
        
    # Output result as JSON
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except:
            result = {{"result": result}}
            
    print(json.dumps(result))

asyncio.run(main())
"""
    
    # Run the script
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        test_script,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await proc.communicate()
    
    if proc.returncode != 0:
        return {"success": False, "error": stderr.decode()}
        
    # Parse result
    try:
        return json.loads(stdout.decode())
    except Exception as e:
        return {"success": False, "error": f"Failed to parse result: {e}"}


# Convenience functions for specific MCP servers
async def call_litellm(model: str, messages: list, **kwargs) -> Dict[str, Any]:
    """Call LiteLLM for language model requests."""
    return await call_mcp_tool(
        "litellm_request",
        "process_single_request",
        {
            "model": model,
            "messages": json.dumps(messages),
            **kwargs
        }
    )


async def call_llm_instance(model: str, prompt: str, **kwargs) -> Dict[str, Any]:
    """Call LLM instance for CLI-based models."""
    return await call_mcp_tool(
        "llm_instance",
        "execute_llm",
        {
            "model": model,
            "prompt": prompt,
            **kwargs
        }
    )


class MCPClient:
    """Client for interacting with MCP servers"""
    
    def __init__(self):
        self.initialized = False
        
    async def initialize(self):
        """Initialize the MCP client"""
        self.initialized = True
        logger.info("MCP client initialized")
        
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool and return the result
        
        Args:
            tool_name: Full tool name (e.g., "mcp__arango-tools__insert")
            parameters: Tool parameters as a dictionary
            
        Returns:
            Dictionary with 'success' and 'data' keys
        """
        if not self.initialized:
            await self.initialize()
            
        try:
            # Parse tool name
            parts = tool_name.split("__")
            if len(parts) != 3 or parts[0] != "mcp":
                raise ValueError(f"Invalid tool name format: {tool_name}")
                
            server_name = parts[1].replace("-", "_")
            method_name = parts[2]
            
            # Call the MCP tool
            result = await call_mcp_tool(server_name, method_name, parameters)
            
            return {
                "success": True,
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": {}
            }
    
    async def cleanup(self):
        """Clean up resources"""
        self.initialized = False
        logger.info("MCP client cleaned up")


if __name__ == "__main__":
    # Test the MCP client
    async def test():
        print("=== MCP Client Test ===\n")
        
        # Test with MCPClient class
        client = MCPClient()
        await client.initialize()
        
        # Test LiteLLM call
        print("1. Testing LiteLLM call via MCPClient:")
        result = await client.call_tool(
            "mcp__litellm-request__process_single_request",
            {
                "model": "gpt-4",
                "messages": json.dumps([{"role": "user", "content": "Say 'Hello from MCP client test'"}]),
                "max_tokens": 50
            }
        )
        print(f"   Result: {result}")
        
        # Test direct functions
        print("\n2. Testing direct call_litellm:")
        result = await call_litellm(
            "gpt-4",
            [{"role": "user", "content": "Say 'Hello from MCP client test'"}],
            max_tokens=50
        )
        print(f"   Result: {result.get('status', 'unknown')}")
        
        await client.cleanup()
        print("\n=== Test Complete ===")
        
    asyncio.run(test())