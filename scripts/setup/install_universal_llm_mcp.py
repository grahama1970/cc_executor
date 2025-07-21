#!/usr/bin/env python3
"""
Install the Universal LLM Executor MCP server configuration.

This script adds the universal-llm-executor to your MCP configuration.
"""

import json
import sys
from pathlib import Path
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="INFO")


def add_mcp_config():
    """Add universal-llm-executor to MCP configuration."""
    # Define the new server config
    new_server = {
        "universal-llm-executor": {
            "command": "uv",
            "args": [
                "--directory",
                "/home/graham/workspace/experiments/cc_executor",
                "run",
                "--script",
                "src/cc_executor/servers/mcp_universal_llm_executor.py"
            ],
            "env": {
                "PYTHONPATH": "/home/graham/workspace/experiments/cc_executor/src",
                "UV_PROJECT_ROOT": "/home/graham/workspace/experiments/cc_executor",
                "LLM_OUTPUT_DIR": "/tmp/llm_outputs",
                "REDIS_HOST": "localhost",
                "REDIS_PORT": "6379"
            }
        }
    }
    
    # Check Claude config
    claude_config_path = Path.home() / ".claude" / "claude_code" / ".mcp.json"
    if claude_config_path.exists():
        logger.info(f"Found Claude MCP config at: {claude_config_path}")
        
        # Load existing config
        with open(claude_config_path, 'r') as f:
            config = json.load(f)
        
        # Check if already exists
        if "universal-llm-executor" in config.get("mcpServers", {}):
            logger.warning("universal-llm-executor already exists in Claude config")
        else:
            # Add new server
            if "mcpServers" not in config:
                config["mcpServers"] = {}
            config["mcpServers"]["universal-llm-executor"] = new_server["universal-llm-executor"]
            
            # Write back
            with open(claude_config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.success("✓ Added universal-llm-executor to Claude MCP config")
    else:
        logger.error(f"Claude MCP config not found at: {claude_config_path}")
    
    # Check Gemini config (if exists)
    gemini_config_path = Path.home() / ".gemini" / ".mcp.json"
    if gemini_config_path.exists():
        logger.info(f"Found Gemini MCP config at: {gemini_config_path}")
        # Similar process for Gemini...
    else:
        logger.info("No Gemini MCP config found (this is normal)")
    
    # Print usage instructions
    logger.info("\n=== Usage Instructions ===")
    logger.info("The Universal LLM Executor is now available as an MCP tool!")
    logger.info("\nAvailable tools:")
    logger.info("- execute_llm: Execute any LLM CLI with a prompt")
    logger.info("- concatenate_files: Concatenate files with smart chunking")
    logger.info("- detect_llms: Detect available LLM CLIs")
    logger.info("- estimate_tokens: Estimate token count for text")
    logger.info("- parse_llm_output: Parse JSON from LLM output")
    logger.info("\nExample usage in Claude:")
    logger.info('mcp__universal-llm-executor__execute_llm("gemini", "Explain recursion")')
    logger.info('mcp__universal-llm-executor__concatenate_files(\'["file1.py", "file2.py"]\')')


if __name__ == "__main__":
    add_mcp_config()