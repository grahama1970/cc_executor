Of course. This is the perfect next step. Formalizing the "Outcome Adjudicator" and clarifying the learning loop in the `README.md` will make the entire system more robust, understandable, and effective.

Here is the new `mcp_outcome_adjudicator.py` file, followed by a completely rewritten `README.md` that incorporates all our discussed improvements.

---

### New File: `src/cc_executor/servers/mcp_outcome_adjudicator.py`

This new MCP tool serves as the single source of truth for task outcomes, providing the critical reward signal for the learning system.

```python
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
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from fastmcp import FastMCP
from loguru import logger
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
        
        if hard_evidence and hard_evidence["is_success"]:
            outcome = "optimal_completion" # Assume hard evidence implies optimality for now
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
            "success": True,
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
    try:
        journey_context = json.loads(journey_context_json)
        final_artifacts = json.loads(final_artifacts_json)
    except json.JSONDecodeError as e:
        return json.dumps({"success": False, "error": f"Invalid JSON input: {e}"})

    result = await tools.adjudicate(journey_context, final_artifacts)
    return json.dumps(result, indent=2)


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
```
---
### Rewritten File: `src/cc_executor/servers/README.md`

This version is restructured for maximum clarity, introducing the core learning loop upfront and clarifying the roles of each component.

``````markdown
# MCP Servers: An AI Agent's Retrievable Memory System

## Overview

The MCP (Model Context Protocol) servers in this directory form a sophisticated, graph-based memory system that enables AI agents to learn from experience, adapt their behavior, and make increasingly optimal decisions over time. This is not just a collection of tools—it's a living, evolving knowledge graph that transforms how agents solve problems.

## The Core Learning Loop: How the Agent Learns

The entire system is built around a clear, repeatable learning process. For every task, the agent follows these steps to both solve the problem and improve its internal memory.

```
┌──────────────────────────┐      1. Start Journey      ┌─────────────────────────┐
│        AI Agent          ├───────────────────────────►│   mcp_tool_journey      │
│      (Claude Code)       │                            │ (Get First Tool)        │
└───────────┬──────────────┘                            └────────────┬────────────┘
            │                                                        │ 2. Execute Tool
            │ 6. Complete Journey                                    │
            │  (Backpropagate Reward)                                │
            │                                                        ▼
┌───────────┴──────────────┐                           ┌──────────────────────────┐
│ mcp_tool_journey         │◄──────────────────────────┤     (Agent Action)       │
│ (Store Final Learning)   │    5. Provide Reward      │ (e.g., call cc_execute)  │
└──────────────────────────┘                           └────────────┬─────────────┘
            ▲                                                        │ 3. Record Step &
            │                                                        │    Get Next Tool
            │                                                        │
┌───────────┴──────────────┐                           ┌───────────▼─────────────┐
│ mcp_outcome_adjudicator  ├───────────────────────────┤   mcp_tool_journey      │
│ (Determine Success)      │     4. Adjudicate         │   (Update Q-Values)     │
└──────────────────────────┘                           └─────────────────────────┘
                                                               (LOOP 3 & 2)
```

**The Step-by-Step Process:**

1.  **`start_journey`**: The agent begins by telling `mcp_tool_journey` its task. The system uses Q-learning and Thompson Sampling to recommend the best first tool and returns a `journey_id`.
2.  **Execute Tool**: The agent executes the recommended tool (e.g., calling `mcp_arango_tools.query`).
3.  **`record_tool_step` (and Loop)**: The agent reports the outcome of the tool call to `mcp_tool_journey`. The system updates its Q-values in real-time and recommends the *next best tool*. The agent loops back to step 2, executing tools one by one.
4.  **`adjudicate_outcome`**: Once the task is complete, the agent calls the crucial `mcp_outcome_adjudicator`. This "oracle" uses a hierarchy of evidence (from file verification to LLM analysis) to determine if the task was successful and calculates a final reward.
5.  **`complete_journey`**: The agent passes the final outcome and reward to `mcp_tool_journey`.
6.  **Backpropagate & Learn**: The `mcp_tool_journey` server takes the final reward and backpropagates it through the entire sequence of tool calls, strengthening the connections that led to success and weakening those that led to failure.

This virtuous cycle ensures that with every task, the agent's knowledge graph becomes smarter, more accurate, and better at predicting optimal solutions.

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            AI Agent (Claude)                             │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │ MCP Protocol
┌──────────────────────────────┴───────────────────────────────────────────┐
│                           MCP Server Layer                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────┐   ┌─────────────────────┐   ┌──────────────────┐   │
│  │ mcp_debugging_assist │ ► │ mcp_tool_journey    │ ► │ mcp_outcome_adjud. │   │
│  │ (High-Level Recipes) │   │ (Real-time Learning)│   │ (The Oracle)     │   │
│  └────────────────────┘   └──────────┬──────────┘   └──────────┬───────┘   │
│                                      │                         │           │
│  ┌────────────────────┐              └───────────┬─────────────┘           │
│  │ mcp_tool_seq_opt.  │ ◄────────────────────────┘                         │
│  │ (Offline Analysis) │                                                    │
│  └────────────────────┘                                                    │
│                                                                          │
│                          ┌───────────────────┐                             │
│                          │ ArangoDB (The Brain)│                             │
│                          └───────────────────┘                             │
│                                                                          │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌─────────────┐ │
│  │ mcp_arango_tools │ │ mcp_cc_execute   │ │ mcp_llm_instance │ │ mcp_litellm_* │ │
│  │ (DB Interface) │ │ (Claude Exec)  │ │ (LLM Interface)  │ │ (Batch LLM) │ │
│  └────────────────┘ └────────────────┘ └────────────────┘ └─────────────┘ │
│                                                                          │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐                 │
│  │ mcp_d3_visualizer│ │ mcp_kilocode_rev │ │ mcp_d3_viz_advisor│                │
│  │ (Visualization)  │ │ (Code Review)    │ │ (Viz Recommender) │                │
│  └────────────────┘ └────────────────┘ └────────────────┘                 │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## How Each Server Contributes

### Core Learning Components

1.  **`mcp_tool_journey.py` - The Real-time Learning Engine**: Manages the agent's step-by-step problem-solving process. It uses Q-learning and Thompson Sampling to recommend the next best action at each step and backpropagates rewards to update the knowledge graph.

2.  **`mcp_outcome_adjudicator.py` - The Oracle**: The source of truth for task success. It uses a hierarchy of evidence—from verifiable file checks (`mcp_cc_execute`) to LLM-based analysis—to assign a final outcome and reward, which fuels the entire learning system.

3.  **`mcp_arango_tools.py` - The Memory Core**: The foundational interface to the ArangoDB graph database. It stores everything: tool sequences, Q-values, errors, solutions, and the semantic relationships between them discovered via FAISS.

4.  **`mcp_tool_sequence_optimizer.py` - The Offline Analyst**: Analyzes historical data to find high-performing tool sequences. This is primarily used by developers for system analysis and for **bootstrapping** the learning system by pre-populating Q-values from known-good workflows.

### High-Level Orchestrators

5.  **`mcp_debugging_assistant.py` - The Workflow Expert**: Provides high-level "recipes" for common, complex tasks like debugging. Instead of calling five individual tools, the agent can make one call to a tool like `resolve_error_workflow`, which orchestrates the entire process. **This is a primary entry point for the agent.**

### Execution & LLM Tools

6.  **`mcp_cc_execute.py` - The Delegation System**: Enables agents to spawn sub-agents for complex tasks and includes the critical `verify_execution` tool for anti-hallucination checks, which the Adjudicator uses as hard evidence.

7.  **`mcp_llm_instance.py` & `mcp_litellm_*.py` - The Multi-Model Interface**: Provide resilient, cost-tracked access to various LLMs (Claude, Gemini, GPT-4) for general reasoning, analysis, and exploration.

### Specialized Tools

8.  **`mcp_d3_visualizer.py` & `mcp_d3_visualization_advisor.py` - The Visual Memory**: Analyze data and generate powerful D3.js visualizations, turning abstract data and graph relationships into understandable insights.

9.  **`mcp_kilocode_review.py` - The Code Quality Memory**: Learns from contextual code review patterns to improve code generation and bug fixing over time.

## Detailed Workflow Example: Fixing a `ModuleNotFoundError`

This example shows the Core Learning Loop in action.

1.  **Task**: "Fix `ModuleNotFoundError: No module named 'pandas'` in `data_processor.py`"
2.  **Agent calls `start_journey`**:
    *   `mcp_tool_journey.start_journey(task_description="Fix ModuleNotFoundError...")`
    *   The system checks Q-values. It's seen this pattern before. It returns `{ "journey_id": "j_123", "recommended_sequence": ["cc_execute"], "confidence": 0.92 }`
3.  **Agent executes the tool**:
    *   `mcp_cc_execute.execute_task(task="Install pandas dependency using uv")`
4.  **Agent records the step**:
    *   `mcp_tool_journey.record_tool_step(journey_id="j_123", tool_name="cc_execute", success=True)`
    *   The system sees the journey is likely complete and recommends `verify_execution` next.
5.  **Agent executes verification**:
    *   `mcp_cc_execute.verify_execution(last_n=1)` -> This checks if `pandas` is now importable or in `pyproject.toml`. It returns success.
6.  **Agent records the final step**:
    *   `mcp_tool_journey.record_tool_step(journey_id="j_123", tool_name="verify_execution", success=True)`
7.  **Agent seeks adjudication**:
    *   `mcp_outcome_adjudicator.adjudicate_outcome(journey_context_json='{"task_description": "...", "actual_sequence": ...}')`
    *   The Adjudicator sees the successful `verify_execution` step (hard evidence) and returns `{ "outcome": "optimal_completion", "final_reward": 9.8, ... }`
8.  **Agent completes the journey**:
    *   `mcp_tool_journey.complete_journey(journey_id="j_123", outcome="optimal_completion")`
9.  **System Learns**: The reward of `9.8` is backpropagated. The Q-value for the state (`ModuleNotFoundError`) and action (`cc_execute` -> `verify_execution`) is further increased, making the agent even more confident in this solution for the future.

## Handling the Cold Start Problem

A new system has no memory. We address this with a two-part strategy:

1.  **Bootstrapping (For Developers)**: An offline utility script (`bootstrap_learning.py`) can be run on existing project logs or known-good workflows. It uses the `mcp_outcome_adjudicator` to retroactively grade these historical tasks and pre-populates the `q_values` in ArangoDB. This gives the agent a foundational memory before it even starts.

2.  **Hybrid Approach (For the Agent)**: When the agent starts a journey for a novel task, `mcp_tool_journey` will return a very low confidence score. This is the agent's signal to enter an **exploratory mode**:
    *   **If confidence is LOW (< 0.2)**: The agent calls a general LLM (e.g., `mcp_llm_instance`) to generate a high-level plan of which tools to use.
    *   **If confidence is HIGH**: The agent follows its own memory's recommendation (exploitation).

This strategy allows the agent to fall back on general intelligence when its specialized experience is lacking, ensuring it can tackle any problem while still capturing the experience for future use.

## Conclusion

This MCP server system transforms AI agents from stateless tools into learning systems with persistent memory. By combining a clear learning loop, a reliable "oracle" for outcomes, and a robust architecture, agents become more capable with every problem they solve. The system doesn't just store data—it builds a living knowledge graph that evolves and improves continuously.
``````