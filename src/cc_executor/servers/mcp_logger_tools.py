#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp",
#     "python-dotenv",
#     "uv",
#     "fastapi",
#     "litellm",
#     "loguru",
#     "redis",
#     "uvicorn",
#     "google-auth"
# ]
# ///
"""
MCP server for Logger Agent tools

This server exposes all the logger agent tools (AssessComplexity, ExtractGeminiCode, etc.)
as proper MCP tools that can be used with Claude Code.
"""

import asyncio
import json
import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv, find_dotenv
from loguru import logger

from fastmcp import FastMCP

# Add utils to path for MCP logger
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.mcp_logger import MCPLogger, debug_tool

# Get the project root directory dynamically
env_path = find_dotenv()
if env_path:
    PROJECT_ROOT = Path(env_path).parent
else:
    # Fallback - traverse up to find project root
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Load environment variables
load_dotenv(env_path)

TOOLS_DIR = PROJECT_ROOT / "src" / "cc_executor" / "tools"

# Create the MCP server and logger
mcp = FastMCP("LoggerTools")
mcp_logger = MCPLogger("logger-tools")


async def run_tool(tool_path: Path, arguments: dict) -> str:
    """Run a tool script and return its output"""
    try:
        # Convert arguments to JSON string
        args_json = json.dumps(arguments)
        
        # Run the tool using uv
        cmd = ["uv", "run", str(tool_path), args_json]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(PROJECT_ROOT)
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            return json.dumps({
                "error": f"Tool execution failed: {error_msg}",
                "exit_code": proc.returncode
            })
        
        # Try to parse as JSON, otherwise return as text
        output = stdout.decode()
        try:
            return json.dumps(json.loads(output), indent=2)
        except json.JSONDecodeError:
            return output
            
    except Exception as e:
        return json.dumps({"error": f"Failed to run tool: {str(e)}"})


@mcp.tool()
@debug_tool(mcp_logger)
async def assess_complexity(
    error_type: str,
    error_message: str, 
    file_path: str,
    stack_trace: Optional[str] = None,
    previous_attempts: int = 0
) -> str:
    """Generate a prompt to assess error complexity and determine fix strategy.
    
    This tool returns a prompt that guides your reasoning about error complexity
    and the appropriate fix approach. It does not make decisions for you - instead
    it provides a framework for YOU to assess the situation.
    
    The prompt will help you consider:
    - Error clarity and specificity
    - Scope (localized vs system-wide)
    - Whether you've seen this pattern before
    - External dependencies involved
    
    Based on YOUR assessment, you can then choose:
    - Self-fix: You know the exact solution
    - Research (perplexity-ask): Need best practices or API details
    - Fresh context (cc_execute): Need a fresh perspective
    - Comprehensive (Gemini): Architectural or multi-file issues
    """
    
    tool_script = TOOLS_DIR / "assess_complexity.py"
    arguments = {
        "error_type": error_type,
        "error_message": error_message,
        "file_path": file_path,
        "stack_trace": stack_trace,
        "previous_attempts": previous_attempts
    }
    
    return await run_tool(tool_script, arguments)


@mcp.tool()
@debug_tool(mcp_logger)
async def extract_gemini_code(
    markdown_file: str,
    output_dir: Optional[str] = None
) -> str:
    """Extracts code from a Gemini markdown response file into tmp/ directory."""
    
    tool_script = TOOLS_DIR / "extract_gemini_code.py"
    arguments = {
        "markdown_file": markdown_file,
        "output_dir": output_dir
    }
    
    return await run_tool(tool_script, arguments)


@mcp.tool()
@debug_tool(mcp_logger)
async def send_to_gemini(
    issue_file: str,
    output_file: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 16000
) -> str:
    """Sends a complete issue report to Gemini Flash for resolution."""
    
    tool_script = TOOLS_DIR / "send_to_gemini.py"
    arguments = {
        "issue_file": issue_file,
        "output_file": output_file,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    return await run_tool(tool_script, arguments)


@mcp.tool()
@debug_tool(mcp_logger)
async def send_to_gemini_batch(
    issue_report_file: str,
    files_to_fix: list[str],
    output_dir: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 7500
) -> str:
    """Sends multiple files to Gemini for fixing, one at a time."""
    
    tool_script = TOOLS_DIR / "send_to_gemini_batch.py"
    arguments = {
        "issue_report_file": issue_report_file,
        "files_to_fix": files_to_fix,
        "output_dir": output_dir,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    return await run_tool(tool_script, arguments)


@mcp.tool()
@debug_tool(mcp_logger)
async def query_agent_logs(
    action: str,
    query: Optional[str] = None,
    session_id: Optional[str] = None,
    tool_name: Optional[str] = None,
    event_type: Optional[str] = None,
    time_range_hours: int = 24,
    limit: int = 50
) -> str:
    """Query and search agent logs stored in ArangoDB."""
    
    tool_script = TOOLS_DIR / "query_agent_logs.py"
    arguments = {
        "action": action,
        "query": query,
        "session_id": session_id,
        "tool_name": tool_name,
        "event_type": event_type,
        "time_range_hours": time_range_hours,
        "limit": limit
    }
    
    return await run_tool(tool_script, arguments)


@mcp.tool()
@debug_tool(mcp_logger)
async def analyze_agent_performance(
    analysis_type: str,
    hours: int = 24
) -> str:
    """Analyze agent performance metrics and patterns from logs."""
    
    tool_script = TOOLS_DIR / "analyze_agent_performance.py"
    arguments = {
        "analysis_type": analysis_type,
        "hours": hours
    }
    
    return await run_tool(tool_script, arguments)


@mcp.tool()
@debug_tool(mcp_logger)
async def inspect_arangodb_schema(
    host: str = "localhost",
    port: int = 8529,
    username: str = "root", 
    password: str = "",
    db_name: str = "logger_agent"
) -> str:
    """Inspect the logger agent database schema using async client.
    
    Returns a comprehensive schema report with sample documents showing:
    - Collections and their document structure
    - Graph definitions and edge collections  
    - Views and their configurations
    - Sample queries for common operations
    
    This helps agents understand the actual structure of the logger database
    so they can construct proper queries.
    """
    
    tool_script = TOOLS_DIR / "inspect_arangodb_schema.py"
    arguments = {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "db_name": db_name
    }
    
    return await run_tool(tool_script, arguments)


@mcp.tool()
@debug_tool(mcp_logger)
async def query_converter(
    natural_query: str,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
    file_path: Optional[str] = None,
    error_id: Optional[str] = None,
    include_schema_info: bool = True
) -> str:
    """Convert natural language queries to AQL and provide reasoning prompts.
    
    This tool converts natural language queries about debugging history into proper
    ArangoDB Query Language (AQL) queries. It returns a prompt that helps you
    understand how to query the logger database.
    
    Example queries it can handle:
    - "Find all similar functions to the one I'm debugging that were resolved"
    - "Show me ModuleNotFoundError fixes from the last week"
    - "What functions are related to data_processor.py by 2 hops?"
    - "Find all errors caused by missing imports that got fixed"
    
    The returned prompt includes:
    - Query intent explanation
    - Generated AQL query with bind variables
    - Execution code examples
    - Result processing patterns
    
    Note: This tool automatically retrieves the latest database schema from
    the logger agent cache for accurate query generation.
    """
    
    tool_script = TOOLS_DIR / "query_converter.py"
    arguments = {
        "natural_query": natural_query,
        "error_type": error_type,
        "error_message": error_message,
        "file_path": file_path,
        "error_id": error_id,
        "include_schema_info": include_schema_info
    }
    
    return await run_tool(tool_script, arguments)


@mcp.tool()
@debug_tool(mcp_logger)
async def cache_db_schema(
    force_refresh: bool = False,
    cache_duration_hours: int = 24
) -> str:
    """Cache the database schema in logger agent for quick retrieval.
    
    This tool inspects the ArangoDB schema and stores it in the logger agent
    database with proper categorization for easy retrieval. This enables
    efficient natural language to AQL conversion without repeated inspections.
    
    The cached schema includes:
    - Collections and their document structure
    - Graph definitions and edge collections
    - Views and their configurations
    - Sample queries for common operations
    - Generated agent prompts
    
    Args:
        force_refresh: Force a fresh schema inspection even if cache exists
        cache_duration_hours: How long to consider the cache valid (default: 24)
        
    Returns:
        Cache metadata including document IDs and expiration time
    """
    
    tool_script = TOOLS_DIR / "cache_db_schema.py"
    arguments = {
        "force_refresh": force_refresh,
        "cache_duration_hours": cache_duration_hours
    }
    
    return await run_tool(tool_script, arguments)


if __name__ == "__main__":
    # Run the server with graceful error handling
    try:
        logger.info("Starting MCP Logger Tools server")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.critical(f"MCP server crashed: {e}", exc_info=True)
        mcp_logger.log_error(e, {"context": "server_startup"})
        sys.exit(1)