#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp",
#     "loguru",
#     "python-dotenv"
# ]
# ///
"""
MCP Server for Kilocode Review - Provides an interface to the /review-contextual workflow.

This tool allows an AI agent to programmatically request a code review for a set of
files and then retrieve the structured results for analysis and self-correction.
"""

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastmcp import FastMCP
from loguru import logger
from dotenv import load_dotenv, find_dotenv

# Add MCP logger utility
# This assumes the utils directory is in the parent of the parent directory.
# Adjust the path if your project structure is different.
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.mcp_logger import MCPLogger, debug_tool

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

# Load environment variables
load_dotenv(find_dotenv())

# Initialize MCP server and logger
mcp = FastMCP("kilocode-review")
mcp_logger = MCPLogger("kilocode-review")


class KilocodeReviewTools:
    """Wraps the kilocode review CLI command for MCP."""

    def __init__(self):
        """Initializes the review tools."""
        # This tool is stateless, so no complex initialization is needed.
        pass

    async def _run_command(self, command: str) -> Dict[str, Any]:
        """
        Asynchronously runs a shell command and captures its output.

        Args:
            command: The full shell command to execute.

        Returns:
            A dictionary with the command's stdout, stderr, and return code.
        """
        logger.info(f"Executing command: {command}")
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        return {
            "stdout": stdout.decode().strip(),
            "stderr": stderr.decode().strip(),
            "returncode": process.returncode
        }

    async def run_review(self, files: List[str], focus: Optional[str] = None, severity: Optional[str] = None) -> Dict[str, Any]:
        """
        Constructs and runs the 'kilocode review-contextual' command.

        Args:
            files: A list of file paths to review.
            focus: Optional focus area (e.g., 'security', 'performance').
            severity: Optional minimum severity level (e.g., 'high').

        Returns:
            A dictionary containing the success status and review directory path or an error.
        """
        if not files:
            return {"success": False, "error": "No files provided for review."}

        # Base command
        command_parts = ["kilocode", "review-contextual"]
        command_parts.extend(files)

        # Add optional arguments
        if focus:
            command_parts.extend(["--focus", focus])
        if severity:
            command_parts.extend(["--severity", severity])

        command_str = " ".join(command_parts)
        result = await self._run_command(command_str)

        if result["returncode"] != 0:
            return {
                "success": False,
                "error": "Kilocode review command failed.",
                "details": result["stderr"]
            }

        # Parse the output to find the review directory
        match = re.search(r"Results saved to: (.+)", result["stdout"])
        if not match:
            return {
                "success": False,
                "error": "Could not parse review directory from Kilocode output.",
                "output": result["stdout"]
            }

        review_directory = match.group(1).strip()
        return {
            "success": True,
            "review_id": review_directory,
            "message": "Review started successfully. Use get_review_results with the review_id to fetch the summary."
        }

    def parse_review_results(self, review_directory: str) -> Dict[str, Any]:
        """
        Parses the output files from a completed Kilocode review.

        Args:
            review_directory: The path to the review output directory.

        Returns:
            A dictionary containing the structured review results.
        """
        review_path = Path(review_directory)
        if not review_path.is_dir():
            return {"success": False, "error": f"Review directory not found: {review_directory}"}

        results = {
            "summary": None,
            "actionable_fixes": None,
            "incompatible_suggestions": None,
            "context_applied": None
        }

        files_to_read = {
            "summary": "review_summary.md",
            "actionable_fixes": "actionable_fixes.md",
            "incompatible_suggestions": "incompatible_suggestions.md",
            "context_applied": "context_applied.md"
        }

        for key, filename in files_to_read.items():
            file_path = review_path / filename
            if file_path.exists():
                try:
                    results[key] = file_path.read_text()
                except Exception as e:
                    logger.warning(f"Could not read review file {file_path}: {e}")
                    results[key] = f"Error reading file: {e}"
            else:
                 logger.warning(f"Review file not found: {file_path}")


        return {"success": True, "results": results}


# Create a global instance of the tools
tools = KilocodeReviewTools()


@mcp.tool()
@debug_tool(mcp_logger)
async def start_review(files: str, focus: Optional[str] = None, severity: Optional[str] = None) -> str:
    """
    Starts a context-aware code review for a given set of files.

    This is a non-blocking, asynchronous call. It initiates the review process
    and returns immediately with a `review_id`. Use the `get_review_results`
    tool with the `review_id` to fetch the results once the review is complete.

    Args:
        files: A space-separated string of file paths to be reviewed.
        focus: Optional. Specific areas to focus on: `security`, `performance`, `maintainability`, `architecture`.
        severity: Optional. Minimum severity level: `low`, `medium`, `high`, `critical`. Default is `medium`.

    Returns:
        A JSON string containing the `review_id` (which is the path to the results directory)
        if successful, or an error message.
    """
    file_list = files.strip().split()
    result = await tools.run_review(file_list, focus, severity)
    return json.dumps(result, indent=2)


@mcp.tool()
@debug_tool(mcp_logger)
async def get_review_results(review_id: str) -> str:
    """
    Fetches and parses the results from a completed code review.

    Call this tool after `start_review` has completed. The underlying review process
    can take several minutes.

    Args:
        review_id: The `review_id` (directory path) returned by a successful `start_review` call.

    Returns:
        A JSON string containing the structured review results, including the summary,
        actionable fixes, and incompatible suggestions.
    """
    # This tool is synchronous from the agent's perspective, but the work it does (I/O) is fast.
    result = tools.parse_review_results(review_id)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("Testing Kilocode Review MCP server...")
        print(f"Tools instance: {tools}")
        print("This server provides 'start_review' and 'get_review_results' tools.")
        print("Server ready to start.")
    else:
        try:
            logger.info("Starting Kilocode Review MCP server")
            mcp.run()
        except Exception as e:
            logger.critical(f"MCP Server crashed: {e}", exc_info=True)
            mcp_logger.log_error(e, {"context": "server_startup"})
            sys.exit(1)