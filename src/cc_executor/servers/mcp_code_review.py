#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp",
#     "loguru",
#     "python-dotenv",
#     "mcp-logger-utils>=0.1.5",
#     "aiofiles"
# ]
# ///
"""
MCP Server for Code Review - Uses multiple free tools for comprehensive analysis.

This server provides code review functionality using:
1. Ruff - Python linting and formatting
2. ESLint - JavaScript/TypeScript linting (if installed)
3. Custom pattern analysis for common issues

=== MCP DEBUGGING NOTES (2025-01-20) ===

COMMON MCP USAGE PITFALLS:
1. Files parameter must be space-separated list of paths
2. Focus parameter is optional: 'security', 'performance', 'style'
3. Severity parameter filters results: 'low', 'medium', 'high', 'critical'
4. Review results are saved to /tmp/code_reviews/

HOW TO DEBUG THIS MCP SERVER:

1. TEST LOCALLY (QUICKEST):
   ```bash
   # Test if server can start
   python src/cc_executor/servers/mcp_code_review.py test
   
   # Check available tools
   python src/cc_executor/servers/mcp_code_review.py test
   ```

2. CHECK MCP LOGS:
   - Startup log: ~/.claude/mcp_logs/code-review_startup.log
   - Debug log: ~/.claude/mcp_logs/code-review_debug.log
   - Calls log: ~/.claude/mcp_logs/code-review_calls.jsonl

3. COMMON ISSUES & FIXES:
   
   a) No tools available:
      - Error: All tools show ✗
      - Fix: Install ruff, eslint, or other tools
      - Install: pip install ruff, npm install -g eslint
   
   b) Timeout errors:
      - Error: "Command timed out"
      - Fix: Increase CODE_REVIEW_TIMEOUT env var
      - Default: 300 seconds
   
   c) File not found:
      - Error: "File not found"
      - Fix: Use absolute paths or verify working directory
      - Check: pwd and file existence

4. ENVIRONMENT VARIABLES:
   - PYTHONPATH=/home/graham/workspace/experiments/cc_executor/src
   - CODE_REVIEW_TIMEOUT=300 (seconds, default)

5. CURRENT STATUS:
   - ✅ All imports working
   - ✅ Multiple tool support
   - ✅ Security pattern detection
   - ⚠️ Tools must be installed separately

=== END DEBUGGING NOTES ===

The original mcp_kilocode_review.py expected a 'kilocode review-contextual' command
that doesn't exist. This replacement provides real, working code review functionality.
"""

import os
import asyncio
import json
import sys
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import tempfile

from fastmcp import FastMCP
from loguru import logger

# Import standardized response utilities
sys.path.insert(0, str(Path(__file__).parent))
from utils.response_utils import create_success_response, create_error_response
from dotenv import load_dotenv, find_dotenv

# Import from our shared PyPI package
from mcp_logger_utils import MCPLogger, debug_tool

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

# Load environment variables
load_dotenv(find_dotenv())

# Initialize MCP server and logger
mcp = FastMCP("code-review")
mcp_logger = MCPLogger("code-review")


class CodeReviewTools:
    """Unified Code Review tools using free, available tools."""
    
    def __init__(self):
        """Initialize the review tools."""
        self.timeout = int(os.getenv("CODE_REVIEW_TIMEOUT", "300"))  # 5 minutes default
        self.available_tools = self._check_available_tools()
        
    def _check_available_tools(self) -> Dict[str, bool]:
        """Check which review tools are available."""
        tools = {
            "ruff": False,
            "eslint": False,
            "flake8": False,
            "mypy": False,
            "pylint": False,
            "black": False
        }
        
        for tool in tools:
            try:
                result = subprocess.run([tool, "--version"], capture_output=True, text=True)
                tools[tool] = result.returncode == 0
                if tools[tool]:
                    logger.info(f"✓ {tool} is available")
            except:
                pass
                
        return tools
    
    async def _run_command(self, command: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        """Run a command asynchronously."""
        logger.info(f"Executing: {command}")
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=self.timeout
            )
            
            return {
                "stdout": stdout.decode().strip(),
                "stderr": stderr.decode().strip(),
                "returncode": process.returncode
            }
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return {
                "stdout": "",
                "stderr": f"Command timed out after {self.timeout} seconds",
                "returncode": -1
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }
    
    async def review_python_file(self, file_path: str) -> Dict[str, Any]:
        """Review a Python file using available tools."""
        issues = []
        
        # Ruff check
        if self.available_tools.get("ruff"):
            result = await self._run_command(f"ruff check {file_path} --output-format json")
            if result["stdout"]:
                try:
                    ruff_issues = json.loads(result["stdout"])
                    for issue in ruff_issues:
                        issues.append({
                            "tool": "ruff",
                            "severity": "medium",
                            "line": issue.get("location", {}).get("row", 0),
                            "column": issue.get("location", {}).get("column", 0),
                            "message": issue.get("message", ""),
                            "code": issue.get("code", "")
                        })
                except:
                    pass
        
        # Flake8 check
        if self.available_tools.get("flake8"):
            result = await self._run_command(f"flake8 {file_path} --format='%(path)s:%(row)d:%(col)d: %(code)s %(text)s'")
            if result["stdout"]:
                for line in result["stdout"].split("\n"):
                    if ":" in line:
                        parts = line.split(":", 3)
                        if len(parts) >= 4:
                            issues.append({
                                "tool": "flake8",
                                "severity": "medium",
                                "line": int(parts[1]) if parts[1].isdigit() else 0,
                                "column": int(parts[2]) if parts[2].isdigit() else 0,
                                "message": parts[3].strip()
                            })
        
        # Custom checks
        with open(file_path, 'r') as f:
            content = f.read()
            lines = content.split('\n')
            
        # Check for common issues
        for i, line in enumerate(lines, 1):
            # SQL injection risk
            if "f\"SELECT" in line or "f'SELECT" in line:
                issues.append({
                    "tool": "security-check",
                    "severity": "critical",
                    "line": i,
                    "column": 0,
                    "message": "Potential SQL injection risk - use parameterized queries"
                })
            
            # Hardcoded secrets
            if any(secret in line.lower() for secret in ["password =", "api_key =", "secret ="]):
                if not "os.getenv" in line and not "environ" in line:
                    issues.append({
                        "tool": "security-check",
                        "severity": "critical",
                        "line": i,
                        "column": 0,
                        "message": "Potential hardcoded secret - use environment variables"
                    })
        
        return {"file": file_path, "issues": issues}
    
    async def review_javascript_file(self, file_path: str) -> Dict[str, Any]:
        """Review a JavaScript/TypeScript file."""
        issues = []
        
        if self.available_tools.get("eslint"):
            result = await self._run_command(f"eslint {file_path} --format json")
            if result["stdout"]:
                try:
                    eslint_output = json.loads(result["stdout"])
                    for file_result in eslint_output:
                        for message in file_result.get("messages", []):
                            issues.append({
                                "tool": "eslint",
                                "severity": message.get("severity", 1) == 2 and "high" or "medium",
                                "line": message.get("line", 0),
                                "column": message.get("column", 0),
                                "message": message.get("message", ""),
                                "rule": message.get("ruleId", "")
                            })
                except:
                    pass
        
        return {"file": file_path, "issues": issues}
    
    async def run_comprehensive_review(self, files: List[str], focus: Optional[str] = None, severity: Optional[str] = None) -> Dict[str, Any]:
        """Run comprehensive code review on multiple files."""
        all_results = []
        
        for file_path in files:
            if not Path(file_path).exists():
                all_results.append({
                    "file": file_path,
                    "error": "File not found"
                })
                continue
            
            # Determine file type and review accordingly
            if file_path.endswith('.py'):
                result = await self.review_python_file(file_path)
            elif file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                result = await self.review_javascript_file(file_path)
            else:
                result = {"file": file_path, "issues": []}
            
            # Filter by severity if requested
            if severity and result.get("issues"):
                severity_map = {"low": 0, "medium": 1, "high": 2, "critical": 3}
                min_severity = severity_map.get(severity, 0)
                
                filtered_issues = []
                for issue in result["issues"]:
                    issue_severity = severity_map.get(issue.get("severity", "low"), 0)
                    if issue_severity >= min_severity:
                        filtered_issues.append(issue)
                result["issues"] = filtered_issues
            
            # Filter by focus area if requested
            if focus and result.get("issues"):
                if focus == "security":
                    result["issues"] = [i for i in result["issues"] if "security" in i.get("tool", "") or "injection" in i.get("message", "").lower()]
                elif focus == "performance":
                    result["issues"] = [i for i in result["issues"] if "performance" in i.get("message", "").lower()]
            
            all_results.append(result)
        
        # Create review report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        review_dir = Path(f"/tmp/code_reviews/review_{timestamp}")
        review_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate summary
        total_issues = sum(len(r.get("issues", [])) for r in all_results)
        critical_count = sum(1 for r in all_results for i in r.get("issues", []) if i.get("severity") == "critical")
        high_count = sum(1 for r in all_results for i in r.get("issues", []) if i.get("severity") == "high")
        
        summary = f"""# Code Review Summary

**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Files Reviewed**: {len(files)}
**Total Issues**: {total_issues}
**Critical**: {critical_count}
**High**: {high_count}

## Available Tools
"""
        for tool, available in self.available_tools.items():
            summary += f"- {tool}: {'✓' if available else '✗'}\n"
        
        (review_dir / "review_summary.md").write_text(summary)
        
        # Generate detailed results
        details = "# Detailed Review Results\n\n"
        for result in all_results:
            details += f"## {result['file']}\n\n"
            if result.get("error"):
                details += f"Error: {result['error']}\n\n"
            elif result.get("issues"):
                for issue in result["issues"]:
                    details += f"- **{issue.get('severity', 'info').upper()}** "
                    details += f"[{issue.get('tool', 'check')}] "
                    details += f"Line {issue.get('line', '?')}: "
                    details += f"{issue.get('message', 'No message')}\n"
            else:
                details += "No issues found.\n"
            details += "\n"
        
        (review_dir / "detailed_results.md").write_text(details)
        
        # Save JSON results
        with open(review_dir / "results.json", 'w') as f:
            json.dump({
                "summary": {
                    "total_issues": total_issues,
                    "critical": critical_count,
                    "high": high_count,
                    "files_reviewed": len(files)
                },
                "results": all_results
            }, f, indent=2)
        
        return {
            "review_id": str(review_dir),
            "summary": {
                "total_issues": total_issues,
                "critical": critical_count,
                "high": high_count
            }
        }


# Create global instance
tools = CodeReviewTools()


@mcp.tool()
@debug_tool(mcp_logger)
async def start_review(files: str, focus: Optional[str] = None, severity: Optional[str] = None) -> str:
    """
    Start a code review for the specified files.
    
    Args:
        files: Space-separated list of file paths to review
        focus: Optional focus area ('security', 'performance', 'style')
        severity: Optional minimum severity ('low', 'medium', 'high', 'critical')
    
    Returns:
        JSON with review_id and summary
    """
    start_time = time.time()
    try:
        file_list = files.strip().split()
        result = await tools.run_comprehensive_review(file_list, focus, severity)
        return create_success_response(
            data=result,
            tool_name="start_review",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="start_review",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def get_review_results(review_id: str) -> str:
    """
    Get the results of a completed review.
    
    Args:
        review_id: The review directory path returned by start_review
    
    Returns:
        JSON with review results
    """
    start_time = time.time()
    try:
        review_path = Path(review_id)
        
        if not review_path.exists():
            return create_error_response(
                error="Review not found",
                tool_name="get_review_results",
                start_time=start_time
            )
        
        results = {}
        
        # Read summary
        summary_file = review_path / "review_summary.md"
        if summary_file.exists():
            results["summary"] = summary_file.read_text()
        
        # Read detailed results
        details_file = review_path / "detailed_results.md"
        if details_file.exists():
            results["details"] = details_file.read_text()
        
        # Read JSON results
        json_file = review_path / "results.json"
        if json_file.exists():
            with open(json_file) as f:
                results["data"] = json.load(f)
        
        return create_success_response(
            data={"success": True, "results": results},
            tool_name="get_review_results",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="get_review_results",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def list_available_tools() -> str:
    """
    List which code review tools are available on the system.
    
    Returns:
        JSON with available tools and their status
    """
    start_time = time.time()
    try:
        return create_success_response(
            data={
                "available_tools": tools.available_tools,
                "timeout": tools.timeout
            },
            tool_name="list_available_tools",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="list_available_tools",
            start_time=start_time
        )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            # Quick test mode
            print(f"✓ {Path(__file__).name} can start successfully!")
            print("=" * 50)
            print("\nAvailable tools:")
            for tool, available in tools.available_tools.items():
                print(f"  {tool}: {'✓' if available else '✗'}")
            print("\nServer ready.")
            sys.exit(0)
        elif sys.argv[1] == "debug":
            # Debug mode - could add debug function if needed
            pass
        elif sys.argv[1] == "working":
            # Could add working_usage function if needed
            pass
    else:
        # Run the MCP server
        try:
            logger.info("Starting Code Review MCP server")
            mcp.run()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.critical(f"MCP server crashed: {e}", exc_info=True)
            if mcp_logger:
                mcp_logger.log_error({"error": str(e), "context": "server_startup"})
            sys.exit(1)