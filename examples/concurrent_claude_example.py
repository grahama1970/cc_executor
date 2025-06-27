#!/usr/bin/env python3
"""
Example of launching multiple Claude instances concurrently and selecting the best response.

This demonstrates a common pattern where multiple Claude instances are launched
with different parameters, and the best response is selected based on various criteria.
"""

import asyncio
import sys
import os

# Add the core module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'cc_executor', 'core'))

from concurrent_executor import ConcurrentClaudeExecutor, EvaluationCriteria


async def main():
    """Main example demonstrating concurrent Claude execution."""
    
    # Initialize the executor
    executor = ConcurrentClaudeExecutor()
    
    # Define the task
    prompt = """Create a Python function that efficiently checks if a number is prime. 
    Include error handling, type hints, and a docstring. Make it as optimized as possible."""
    
    print("=== Concurrent Claude Execution Example ===\n")
    print(f"Prompt: {prompt}\n")
    print("Launching 5 Claude instances with different creativity levels...\n")
    
    # Launch multiple instances with different models
    responses = await executor.execute_concurrent(
        prompt=prompt,
        num_instances=5,
        models=["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
        temperature_range=(0.7, 1.3),
        timeout=120
    )
    
    print(f"\nReceived {len(responses)} responses")
    
    # Evaluate using different criteria
    print("\n=== Evaluation Results ===")
    
    # 1. Fastest response (simple, objective)
    fastest = executor.evaluate_responses(responses, EvaluationCriteria.FASTEST)
    print(f"\n1. FASTEST Response:")
    print(f"   - Instance: {fastest.instance_id}")
    print(f"   - Time: {fastest.execution_time:.2f}s")
    print(f"   - Model: {fastest.model}")
    print(f"   - Temperature: {fastest.temperature}")
    
    # 2. Most detailed response (simple, objective)
    detailed = executor.evaluate_responses(responses, EvaluationCriteria.MOST_DETAILED)
    print(f"\n2. MOST DETAILED Response:")
    print(f"   - Instance: {detailed.instance_id}")
    print(f"   - Output length: {len(detailed.output)} chars")
    print(f"   - Model: {detailed.model}")
    print(f"   - Temperature: {detailed.temperature}")
    
    # 3. Highest temperature (simple version of "most creative")
    highest_temp = executor.evaluate_responses(responses, EvaluationCriteria.HIGHEST_MODEL_TEMP)
    print(f"\n3. HIGHEST TEMPERATURE (proxy for creativity):")
    print(f"   - Instance: {highest_temp.instance_id}")
    print(f"   - Model: {highest_temp.model}")
    print(f"   - Temperature: {highest_temp.temperature}")
    
    # Note about deferred evaluators
    print(f"\n4. ADVANCED EVALUATORS (deferred per Gemini's recommendation):")
    print(f"   - BEST_CODE_QUALITY: Will use external linter (ruff) in v2")
    print(f"   - CONSENSUS: Complex pattern matching deferred to v2")
    print(f"   - LLM_JUDGE: Expensive external calls deferred to v3")
    
    # Generate summary report
    report = executor.get_summary_report(responses)
    print("\n=== Summary Report ===")
    print(f"Total instances: {report['total_instances']}")
    print(f"Success rate: {100 - float(report['failure_rate'].rstrip('%')):.1f}%")
    print(f"Average execution time: {report['average_execution_time']}")
    print(f"Time range: {report['fastest_time']} - {report['slowest_time']}")
    print(f"Average output length: {report['average_output_length']:.0f} chars")
    
    print("\nModel statistics:")
    for model, stats in report['model_statistics'].items():
        print(f"  {model}:")
        print(f"    - Count: {stats['count']}")
        print(f"    - Success rate: {stats['success_rate']:.1f}%")
        print(f"    - Avg time: {stats['avg_time']:.2f}s")
        print(f"    - Avg output: {stats['avg_output_length']:.0f} chars")
    
    # Show the selected best response
    print("\n=== Selected Best Response (Fastest) ===")
    print(f"Instance: {fastest.instance_id}")
    print(f"Model: {fastest.model}")
    print(f"Temperature: {fastest.temperature}")
    print(f"Execution time: {fastest.execution_time:.2f}s")
    print("\nOutput preview (first 500 chars):")
    print("-" * 50)
    print(fastest.output[:500])
    if len(fastest.output) > 500:
        print(f"\n... (truncated, total {len(fastest.output)} chars)")
    print("-" * 50)
    
    # Custom evaluation example
    print("\n=== Custom Evaluation Example ===")
    
    def custom_evaluator(responses):
        """Custom evaluator that prefers sonnet model with moderate temperature."""
        # Filter successful responses
        valid = [r for r in responses if r.exit_code == 0]
        if not valid:
            return responses[0]
        
        # Score based on model preference and moderate temperature
        def score(r):
            model_score = 10 if "sonnet" in r.model else 5
            # Prefer temperatures around 1.0
            temp_score = 5 - abs(r.temperature - 1.0) * 2
            time_score = 5 / (1 + r.execution_time)  # Lower time = higher score
            return model_score + temp_score + time_score
        
        return max(valid, key=score)
    
    custom_best = executor.evaluate_responses(responses, custom_evaluator=custom_evaluator)
    print(f"Custom evaluation selected: {custom_best.instance_id}")
    print(f"  - Model: {custom_best.model}")
    print(f"  - Temperature: {custom_best.temperature} (preferred: 1.0)")
    print(f"  - Execution time: {custom_best.execution_time:.2f}s")
    
    print("\n✅ Example completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())