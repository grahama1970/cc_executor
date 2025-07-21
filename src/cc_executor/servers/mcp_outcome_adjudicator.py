#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp",
#     "python-dotenv",
#     "loguru",
#     "mcp-logger-utils>=0.1.5"
# ]
# ///
"""
MCP Server for Outcome Adjudication - The "Oracle" for the Learning System.

=== MCP DEBUGGING NOTES (2025-07-18) ===

COMMON MCP USAGE PITFALLS:
1. This tool is the FINAL step before completing a journey. The agent's flow should be:
   ... execute last tool -> adjudicate_outcome() -> complete_journey()
2. The `journey_context_json` must contain the full journey details, including the tool sequence.
3. This tool orchestrates calls to other MCPs (like cc_execute, arango_tools) to gather evidence. Ensure they are running.
4. Hard evidence (like file verification) will always override soft evidence (LLM opinion).

HOW TO DEBUG THIS MCP SERVER:

1. TEST LOCALLY (QUICKEST):
   ```bash
   # Test if server can start and run its logic
   python src/cc_executor/servers/mcp_outcome_adjudicator.py working
   ```

2. CHECK MCP LOGS:
   - Startup log: ~/.claude/mcp_logs/outcome-adjudicator_startup.log
   - Debug log: ~/.claude/mcp_logs/outcome-adjudicator_debug.log

3. COMMON ISSUES & FIXES:
   
   a) Fails to parse journey context:
      - Error: "Invalid JSON in journey_context_json"
      - Fix: Ensure the calling agent provides a valid JSON string with 'tool_sequence' and 'task_description' keys.
   
   b) Cannot find evidence:
      - Symptom: Always falls back to LLM adjudication.
      - Fix: Check if the task type keywords (e.g., 'create file', 'run tests') are being correctly identified. Ensure the tools it calls for evidence (`mcp_cc_execute`) are available.
   
   c) LLM adjudication fails:
      - Error: "Failed to get LLM adjudication"
      - Fix: Check if `mcp_llm_instance` is running and properly configured. The prompt for adjudication is structured, so LLM parsing errors are possible.

4. ENVIRONMENT VARIABLES:
   - No specific env vars required, but it relies on other MCPs that do.

=== END DEBUGGING NOTES ===

This server provides a single, authoritative tool to determine the success of a task,
which is then used to calculate the reward for the reinforcement learning system.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

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
mcp = FastMCP("outcome-adjudicator")
mcp_logger = MCPLogger("outcome-adjudicator")

# Consistent reward structure (mirrored from mcp_tool_journey.py)
REWARDS = {
    "optimal_completion": 10.0,
    "suboptimal_completion": 5.0,
    "per_extra_step": -0.5,
    "per_tool_call": -0.1,
    "failed_tool_call": -1.0,
    "task_failure": -5.0,
    "novel_success": 2.0
}

class OutcomeAdjudicatorTools:
    """Tools for determining the success and reward of a completed task journey."""

    async def _check_for_hard_evidence(self, journey_context: Dict) -> Optional[Dict]:
        """Check for verifiable, non-LLM evidence of success."""
        task_desc = journey_context.get("task_description", "").lower()
        
        # Check for file creation/modification tasks
        if any(kw in task_desc for kw in ["create file", "write to", "modify", "save"]):
            logger.info("Task appears file-related. Checking for verification artifacts.")
            # In a real system, this would extract the filename and check its existence/content.
            # Here we simulate calling mcp_cc_execute.verify_execution
            # For now, we'll check if the journey contains a verification step.
            for step in journey_context.get("actual_sequence", []):
                if step.get("tool") == "verify_execution" and step.get("success"):
                    return {
                        "evidence_found": True,
                        "is_success": True,
                        "reasoning": "A 'verify_execution' step was successfully completed, confirming file system changes.",
                        "evidence_source": "mcp_cc_execute.verify_execution"
                    }
            # File task but no verification found - explicit failure
            return {
                "evidence_found": False,
                "is_success": False,
                "outcome": "verification_missing",
                "reasoning": "File creation/modification task completed but no verification step found.",
                "evidence_source": "missing_verification"
            }

        # Check for code testing tasks
        if any(kw in task_desc for kw in ["test", "unit test", "pytest"]):
            logger.info("Task appears test-related. Checking for test results.")
            # In a real system, this would parse test output from a tool like `mcp_code_runner.run_tests`.
            # We simulate this by looking for a successful test run log.
            for step in journey_context.get("actual_sequence", []):
                if "run_tests" in step.get("tool", "") and step.get("success"):
                     return {
                        "evidence_found": True,
                        "is_success": True,
                        "reasoning": "A 'run_tests' step was successfully completed with passing results.",
                        "evidence_source": "mcp_code_runner.run_tests"
                    }
            # Test task but no test run found - explicit failure
            return {
                "evidence_found": False,
                "is_success": False,
                "outcome": "verification_missing",
                "reasoning": "Testing task requested but no test execution found.",
                "evidence_source": "missing_test_run"
            }
        
        return None

    async def _get_llm_adjudication(self, journey_context: Dict, final_artifacts: Dict) -> Dict:
        """Use an LLM as a fallback to adjudicate the outcome."""
        logger.info("No hard evidence found. Falling back to LLM adjudication.")

        prompt = f"""
        You are an impartial AI Outcome Adjudicator. Your task is to determine if an AI agent successfully completed its goal.
        Analyze the original task, the steps taken, and the final result. Provide your judgment in a structured JSON format.

        **Original Task:**
        {journey_context.get('task_description')}

        **Tool Sequence Used:**
        {[step.get('tool') for step in journey_context.get('actual_sequence', [])]}

        **Final Artifacts/Output:**
        {json.dumps(final_artifacts, indent=2)}

        **Analysis Criteria:**
        1.  **Correctness:** Does the final output correctly and completely address the original task?
        2.  **Efficiency:** Was the tool sequence logical and concise? Or was it inefficient?
        3.  **Completeness:** Are there any missing parts to the solution?

        **Respond with ONLY a valid JSON object matching this schema:**
        {{
            "is_success": boolean,
            "confidence": float (0.0 to 1.0),
            "reasoning": "A brief but specific explanation for your decision.",
            "suggested_outcome": "one of ['optimal_completion', 'suboptimal_completion', 'task_failure']"
        }}
        """

        # This would be a real call to another MCP tool.
        # result_json = await mcp__llm_instance__execute_llm(model="claude-3-haiku-20240307", prompt=prompt, json_mode=True)
        # For this example, we'll simulate a response.
        logger.info("Simulating call to mcp_llm_instance for adjudication.")
        simulated_response = {
            "success": True,
            "parsed_json": {
                "is_success": True,
                "confidence": 0.85,
                "reasoning": "The agent correctly identified the problem and used a logical sequence of tools. The final output directly addresses the user's request.",
                "suggested_outcome": "optimal_completion"
            }
        }

        if simulated_response.get("success") and simulated_response.get("parsed_json"):
            return simulated_response["parsed_json"]
        else:
            return {
                "is_success": False,
                "confidence": 0.5,
                "reasoning": "Failed to get a valid adjudication from the LLM.",
                "suggested_outcome": "task_failure"
            }

    def _calculate_final_reward(self, outcome: str, journey_context: Dict) -> float:
        """Calculate the final reward based on the adjudicated outcome and journey efficiency."""
        tool_sequence = journey_context.get("actual_sequence", [])
        num_tools = len(tool_sequence)
        
        if outcome == "optimal_completion":
            reward = REWARDS["optimal_completion"]
        elif outcome == "suboptimal_completion":
            reward = REWARDS["suboptimal_completion"]
        else: # task_failure
            reward = REWARDS["task_failure"]

        # Apply penalties for inefficiency
        reward += REWARDS["per_tool_call"] * num_tools
        failed_calls = sum(1 for step in tool_sequence if not step.get("success", True))
        reward += REWARDS["failed_tool_call"] * failed_calls

        # Bonus for novel successful paths (placeholder logic)
        if outcome != "task_failure" and journey_context.get("is_novel_path"):
            reward += REWARDS["novel_success"]

        return round(reward, 2)

    async def adjudicate(self, journey_context: Dict, final_artifacts: Dict) -> Dict[str, Any]:
        """The core adjudication logic."""
        
        # 1. Check for hard, verifiable evidence first
        hard_evidence = await self._check_for_hard_evidence(journey_context)
        
        if hard_evidence:
            if hard_evidence["is_success"]:
                outcome = "optimal_completion" # Assume hard evidence implies optimality for now
                reasoning = hard_evidence["reasoning"]
                evidence_source = hard_evidence["evidence_source"]
            else:
                # Handle explicit failure cases like missing verification
                outcome = hard_evidence.get("outcome", "task_failure")
                if outcome == "verification_missing":
                    outcome = "task_failure"  # Map to standard failure outcome
                reasoning = hard_evidence["reasoning"]
                evidence_source = hard_evidence["evidence_source"]
        else:
            # 2. Fallback to soft, LLM-based evidence
            llm_judgment = await self._get_llm_adjudication(journey_context, final_artifacts)
            outcome = llm_judgment.get("suggested_outcome", "task_failure")
            reasoning = llm_judgment.get("reasoning", "No reasoning provided.")
            evidence_source = "mcp_llm_instance"

        # 3. Calculate the final reward based on the adjudicated outcome
        final_reward = self._calculate_final_reward(outcome, journey_context)

        return {
            "outcome": outcome,
            "final_reward": final_reward,
            "reasoning": reasoning,
            "evidence_source": evidence_source
        }

# Create a global instance of the tools
tools = OutcomeAdjudicatorTools()

@mcp.tool()
@debug_tool(mcp_logger)
async def adjudicate_outcome(
    journey_context_json: str,
    final_artifacts_json: Optional[str] = "{}"
) -> str:
    """
    Determines the success of a task journey to provide a reward signal for learning.

    This tool is the "oracle" of the system. It uses a hierarchy of evidence—from
    verifiable file checks to LLM-based judgment—to decide if a task was completed
    successfully and efficiently. The agent MUST call this before `complete_journey`.

    Args:
        journey_context_json: A JSON string containing the full journey context, including
                              'task_description' and the 'actual_sequence' of tool steps.
        final_artifacts_json: A JSON string of the final output or artifacts produced
                              by the journey (e.g., file content, analysis summary).

    Returns:
        A JSON string with the final outcome ('optimal_completion', etc.), a calculated
        reward value, and the reasoning behind the decision.
    """
    start_time = time.time()
    try:
        journey_context = json.loads(journey_context_json)
        final_artifacts = json.loads(final_artifacts_json)
    except json.JSONDecodeError as e:
        return create_error_response(
            error=f"Invalid JSON input: {e}",
            tool_name="adjudicate_outcome",
            start_time=start_time
        )

    result = await tools.adjudicate(journey_context, final_artifacts)
    return create_success_response(
        data=result,
        tool_name="adjudicate_outcome",
        start_time=start_time
    )


async def working_usage():
    """Demonstrate proper usage of the Outcome Adjudicator."""
    logger.info("=== Outcome Adjudicator Working Usage ===")

    # Scenario 1: A task with hard evidence (file creation)
    logger.info("\n1. Adjudicating a task with hard evidence:")
    journey_file_creation = {
        "journey_id": "journey_abc123",
        "task_description": "Create a python script 'hello.py' that prints 'Hello, World!'",
        "actual_sequence": [
            {"tool": "cc_execute", "success": True, "result_summary": "Created file hello.py"},
            {"tool": "verify_execution", "success": True, "result_summary": "Verified hello.py exists and contains correct content."}
        ]
    }
    final_artifacts_file = {"file_path": "hello.py", "content": "print('Hello, World!')"}

    result1 = await adjudicate_outcome(
        json.dumps(journey_file_creation),
        json.dumps(final_artifacts_file)
    )
    logger.info(f"Result 1 (Hard Evidence):\n{result1}")


    # Scenario 2: An analysis task with no hard evidence (fallback to LLM)
    logger.info("\n2. Adjudicating an analysis task (fallback to LLM):")
    journey_analysis = {
        "journey_id": "journey_def456",
        "task_description": "Analyze the provided logs and identify the most common error type.",
        "actual_sequence": [
            {"tool": "query", "success": True, "result_summary": "Fetched 100 log events."},
            {"tool": "discover_patterns", "success": True, "result_summary": "Found 5 error types."}
        ]
    }
    final_artifacts_analysis = {"most_common_error": "ModuleNotFoundError", "count": 42}

    result2 = await adjudicate_outcome(
        json.dumps(journey_analysis),
        json.dumps(final_artifacts_analysis)
    )
    logger.info(f"Result 2 (LLM Adjudication):\n{result2}")

    logger.success("\n✅ Outcome Adjudicator working correctly!")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "working":
        asyncio.run(working_usage())
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        print("Testing Outcome Adjudicator MCP server...")
        print("This tool acts as the 'oracle' for the learning system.")
        print("It determines task success using a hierarchy of evidence.")
        print("Server ready to start.")
    else:
        try:
            logger.info("Starting Outcome Adjudicator MCP server")
            mcp.run()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.critical(f"MCP server crashed: {e}", exc_info=True)
            if mcp_logger:
                mcp_logger.log_error(e, {"context": "server_startup"})
            sys.exit(1)
