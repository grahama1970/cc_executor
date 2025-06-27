#!/usr/bin/env python3
"""
Concurrent Claude Executor with Response Evaluation.

This module provides a high-level interface for launching multiple Claude instances
concurrently and evaluating which response is best using various criteria.

Following Gemini's recommendations, this implementation focuses on simple,
objective evaluators first, avoiding brittle complexity.
"""

import asyncio
import websockets
import json
import time
import subprocess
import tempfile
import os
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import uuid
from loguru import logger


class EvaluationCriteria(Enum):
    """Criteria for evaluating Claude responses."""
    # Low-risk, high-value evaluators (implemented)
    FASTEST = "fastest"
    MOST_DETAILED = "most_detailed"
    HIGHEST_MODEL_TEMP = "highest_model_temp"  # Replaced MOST_CREATIVE
    
    # Advanced evaluators (for future implementation)
    BEST_CODE_QUALITY = "best_code_quality"  # Uses external linter
    CONSENSUS = "consensus"  # Deferred to v2
    LLM_JUDGE = "llm_judge"  # Deferred to v3


@dataclass
class ClaudeResponse:
    """Response from a Claude instance."""
    instance_id: str
    model: str
    temperature: float  # Replaced creativity with actual claude parameter
    prompt: str
    output: str
    execution_time: float
    exit_code: int
    timestamp: float
    metadata: Dict[str, Any] = None


class ConcurrentClaudeExecutor:
    """
    Manages concurrent Claude instance execution and response evaluation.
    
    This class provides a production-ready interface for running multiple
    Claude instances with different parameters and selecting the best response.
    """
    
    def __init__(self, websocket_uri: str = "ws://localhost:8003/ws/mcp"):
        self.websocket_uri = websocket_uri
        self.active_instances = {}
        self.completed_responses = []
        
    async def execute_claude_instance(
        self,
        instance_id: str,
        prompt: str,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 1.0,
        timeout: int = 300,
        additional_flags: str = ""
    ) -> ClaudeResponse:
        """Execute a single Claude instance and return the response."""
        
        start_time = time.time()
        output_buffer = []
        exit_code = -1
        
        try:
            async with websockets.connect(self.websocket_uri) as websocket:
                # Build Claude command with actual supported flags
                # Note: temperature is controlled by the model API, not CLI flags
                command = f'claude --model {model} {additional_flags} -p "{prompt}"'
                
                # Send execute command
                request = {
                    "jsonrpc": "2.0",
                    "method": "execute",
                    "params": {"command": command},
                    "id": instance_id
                }
                
                await websocket.send(json.dumps(request))
                logger.info(f"[{instance_id}] Started: model={model}, temperature={temperature}")
                
                # Set timeout
                timeout_task = asyncio.create_task(asyncio.sleep(timeout))
                
                # Collect output
                while True:
                    try:
                        # Wait for message with timeout
                        receive_task = asyncio.create_task(websocket.recv())
                        done, pending = await asyncio.wait(
                            {receive_task, timeout_task},
                            return_when=asyncio.FIRST_COMPLETED
                        )
                        
                        if timeout_task in done:
                            logger.warning(f"[{instance_id}] Timeout after {timeout}s")
                            break
                            
                        message = receive_task.result()
                        data = json.loads(message)
                        
                        # Handle streaming output
                        if data.get("method") == "process.output":
                            output_data = data.get("params", {}).get("data", "")
                            output_buffer.append(output_data)
                        
                        # Handle completion
                        elif data.get("method") == "process.exit":
                            exit_code = data.get("params", {}).get("exitCode", -1)
                            logger.info(f"[{instance_id}] Completed with exit code {exit_code}")
                            break
                            
                    except asyncio.CancelledError:
                        break
                        
        except Exception as e:
            logger.error(f"[{instance_id}] Error: {e}")
        
        execution_time = time.time() - start_time
        
        return ClaudeResponse(
            instance_id=instance_id,
            model=model,
            temperature=temperature,
            prompt=prompt,
            output="".join(output_buffer),
            execution_time=execution_time,
            exit_code=exit_code,
            timestamp=start_time
        )
    
    async def execute_concurrent(
        self,
        prompt: str,
        num_instances: int = 3,
        models: Optional[List[str]] = None,
        temperature_range: tuple = (0.5, 1.5),
        timeout: int = 300,
        parameter_sets: Optional[List[Dict]] = None
    ) -> List[ClaudeResponse]:
        """
        Execute multiple Claude instances concurrently.
        
        Args:
            prompt: The prompt to send to each instance
            num_instances: Number of instances to launch
            models: List of models to use (cycles through if fewer than instances)
            temperature_range: Range for temperature values (Note: temperature is model-side)
            timeout: Timeout for each instance
            parameter_sets: Optional list of specific parameter sets
            
        Returns:
            List of ClaudeResponse objects
        """
        
        tasks = []
        
        # Default models if none provided
        if models is None:
            models = ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"]
        
        if parameter_sets:
            # Use provided parameter sets
            for i, params in enumerate(parameter_sets):
                instance_id = f"instance_{i+1}_{uuid.uuid4().hex[:8]}"
                task = self.execute_claude_instance(
                    instance_id=instance_id,
                    prompt=prompt,
                    model=params.get("model", models[i % len(models)]),
                    temperature=params.get("temperature", 1.0),
                    timeout=timeout,
                    additional_flags=params.get("additional_flags", "")
                )
                tasks.append(task)
        else:
            # Generate parameters cycling through models
            import random
            for i in range(num_instances):
                instance_id = f"instance_{i+1}_{uuid.uuid4().hex[:8]}"
                model = models[i % len(models)]
                temperature = round(random.uniform(*temperature_range), 2)
                
                task = self.execute_claude_instance(
                    instance_id=instance_id,
                    prompt=prompt,
                    model=model,
                    temperature=temperature,
                    timeout=timeout
                )
                tasks.append(task)
        
        # Execute all instances concurrently
        responses = await asyncio.gather(*tasks)
        self.completed_responses.extend(responses)
        
        return responses
    
    def evaluate_responses(
        self,
        responses: List[ClaudeResponse],
        criteria: EvaluationCriteria = EvaluationCriteria.FASTEST,
        custom_evaluator: Optional[Callable] = None
    ) -> ClaudeResponse:
        """
        Evaluate responses and select the best one.
        
        Following Gemini's recommendations, we start with simple, objective evaluators.
        Advanced evaluators are marked for future implementation.
        
        Args:
            responses: List of ClaudeResponse objects
            criteria: Evaluation criteria to use
            custom_evaluator: Optional custom evaluation function
            
        Returns:
            The best ClaudeResponse according to the criteria
        """
        
        if not responses:
            return None
            
        if custom_evaluator:
            return custom_evaluator(responses)
        
        # Low-risk, high-value evaluators (implemented)
        if criteria == EvaluationCriteria.FASTEST:
            # Simple, objective: minimum execution time
            return min(responses, key=lambda r: r.execution_time)
            
        elif criteria == EvaluationCriteria.MOST_DETAILED:
            # Simple, objective: maximum output length
            return max(responses, key=lambda r: len(r.output))
            
        elif criteria == EvaluationCriteria.HIGHEST_MODEL_TEMP:
            # Simple, objective: highest temperature parameter (replaced MOST_CREATIVE)
            # Only consider successful runs
            valid_responses = [r for r in responses if r.exit_code == 0]
            if valid_responses:
                return max(valid_responses, key=lambda r: r.temperature)
            return responses[0]
            
        # Advanced evaluators (for future implementation)
        elif criteria == EvaluationCriteria.BEST_CODE_QUALITY:
            # Per Gemini: Use external linter instead of custom analysis
            logger.warning("BEST_CODE_QUALITY requires external linter integration. "
                         "Falling back to MOST_DETAILED for now.")
            return self.evaluate_responses(responses, EvaluationCriteria.MOST_DETAILED)
            
        elif criteria == EvaluationCriteria.CONSENSUS:
            # Deferred to v2 per Gemini's recommendation
            logger.warning("CONSENSUS evaluator deferred to v2. "
                         "Falling back to FASTEST.")
            return self.evaluate_responses(responses, EvaluationCriteria.FASTEST)
            
        elif criteria == EvaluationCriteria.LLM_JUDGE:
            # Deferred to v3 per Gemini's recommendation
            logger.warning("LLM_JUDGE evaluator deferred to v3. "
                         "Falling back to FASTEST.")
            return self.evaluate_responses(responses, EvaluationCriteria.FASTEST)
            
        return responses[0]  # Default fallback
    
    async def evaluate_code_quality_external(
        self, 
        response: ClaudeResponse,
        linter: str = "ruff"
    ) -> Dict[str, Any]:
        """
        Evaluate code quality using external linter (future implementation).
        
        Per Gemini's recommendation: offload complexity to battle-tested tools.
        
        Args:
            response: ClaudeResponse containing code
            linter: Which linter to use ('ruff', 'pylint', etc.)
            
        Returns:
            Dictionary with linter results
        """
        # Save code to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(response.output)
            temp_file = f.name
        
        try:
            if linter == "ruff":
                # Run ruff check
                result = subprocess.run(
                    ['ruff', 'check', '--select', 'I,F', '--quiet', temp_file],
                    capture_output=True,
                    text=True
                )
                return {
                    "linter": "ruff",
                    "exit_code": result.returncode,
                    "issues": result.stdout.count('\n') if result.stdout else 0,
                    "output": result.stdout
                }
            else:
                logger.warning(f"Linter {linter} not implemented yet")
                return {"error": "Linter not implemented"}
                
        finally:
            # Clean up
            os.unlink(temp_file)
    
    def get_summary_report(self, responses: List[ClaudeResponse]) -> Dict[str, Any]:
        """Generate a summary report of all responses."""
        
        if not responses:
            return {"error": "No responses to summarize"}
            
        successful = [r for r in responses if r.exit_code == 0]
        
        # Group by model
        model_stats = {}
        for r in responses:
            if r.model not in model_stats:
                model_stats[r.model] = {
                    "count": 0,
                    "successful": 0,
                    "total_time": 0,
                    "avg_output_length": 0
                }
            model_stats[r.model]["count"] += 1
            if r.exit_code == 0:
                model_stats[r.model]["successful"] += 1
            model_stats[r.model]["total_time"] += r.execution_time
            model_stats[r.model]["avg_output_length"] += len(r.output)
        
        # Calculate averages
        for model, stats in model_stats.items():
            stats["avg_time"] = stats["total_time"] / stats["count"]
            stats["avg_output_length"] = stats["avg_output_length"] / stats["count"]
            stats["success_rate"] = stats["successful"] / stats["count"] * 100
        
        return {
            "total_instances": len(responses),
            "successful_instances": len(successful),
            "failure_rate": f"{((len(responses) - len(successful)) / len(responses) * 100):.1f}%",
            "average_execution_time": f"{sum(r.execution_time for r in responses) / len(responses):.2f}s",
            "fastest_time": f"{min(r.execution_time for r in responses):.2f}s",
            "slowest_time": f"{max(r.execution_time for r in responses):.2f}s",
            "model_statistics": model_stats,
            "temperature_range": {
                "min": min(r.temperature for r in responses),
                "max": max(r.temperature for r in responses),
                "avg": sum(r.temperature for r in responses) / len(responses)
            },
            "average_output_length": sum(len(r.output) for r in responses) / len(responses)
        }


async def example_usage():
    """Example of using the concurrent executor with proper Claude parameters."""
    
    executor = ConcurrentClaudeExecutor()
    
    # Example 1: Simple concurrent execution with different models
    print("=== Example 1: Basic Concurrent Execution ===")
    responses = await executor.execute_concurrent(
        prompt="Write a function to calculate fibonacci numbers",
        num_instances=4,
        models=["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
        temperature_range=(0.7, 1.2)  # Note: temperature is model-side, not CLI
    )
    
    # Evaluate using simple, objective criteria (per Gemini's recommendation)
    fastest = executor.evaluate_responses(responses, EvaluationCriteria.FASTEST)
    most_detailed = executor.evaluate_responses(responses, EvaluationCriteria.MOST_DETAILED)
    
    print(f"\nFastest response: Instance {fastest.instance_id} ({fastest.execution_time:.2f}s)")
    print(f"Most detailed: Instance {most_detailed.instance_id} ({len(most_detailed.output)} chars)")
    
    # Example 2: Specific parameter sets with different models
    print("\n=== Example 2: Specific Parameter Sets ===")
    parameter_sets = [
        {"model": "claude-3-5-sonnet-20241022", "temperature": 0.5},
        {"model": "claude-3-5-haiku-20241022", "temperature": 1.0},
        {"model": "claude-3-5-sonnet-20241022", "temperature": 1.2},
        {"model": "claude-3-5-haiku-20241022", "temperature": 0.8}
    ]
    
    responses = await executor.execute_concurrent(
        prompt="Create a simple Python function to validate email addresses",
        parameter_sets=parameter_sets
    )
    
    # Use simple evaluator
    fastest = executor.evaluate_responses(responses, EvaluationCriteria.FASTEST)
    print(f"\nFastest implementation: {fastest.model} (temp={fastest.temperature})")
    
    # Generate summary report
    report = executor.get_summary_report(responses)
    print("\n=== Summary Report ===")
    print(json.dumps(report, indent=2))
    
    # Example 3: Demonstrate future code quality evaluation
    print("\n=== Example 3: Future Code Quality Evaluation ===")
    print("Note: Per Gemini's recommendation, code quality evaluation")
    print("will use external linters like 'ruff' instead of custom analysis.")
    
    # Example of how it would work (for demonstration)
    if fastest.output.strip():  # If we have code output
        quality_result = await executor.evaluate_code_quality_external(fastest, linter="ruff")
        print(f"\nExternal linter results for fastest response:")
        print(f"  Linter: {quality_result.get('linter', 'N/A')}")
        print(f"  Exit code: {quality_result.get('exit_code', 'N/A')}")
        print(f"  Issues found: {quality_result.get('issues', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(example_usage())