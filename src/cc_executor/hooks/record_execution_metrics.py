#!/usr/bin/env python3
"""
Record execution metrics after task completion.
Analyzes output quality, performance, and triggers reflection if needed.
"""

import sys
import os
import json
import redis
import time
import re
from typing import Dict, List, Optional
from loguru import logger

def analyze_output_quality(output: str) -> Dict[str, any]:
    """Analyze the quality of task output."""
    quality_metrics = {
        "length": len(output),
        "has_error": False,
        "error_type": None,
        "completeness": "unknown",
        "has_code": False,
        "has_verification": False,
        "token_limit_hit": False,
        "quality_score": 0.0
    }
    
    output_lower = output.lower()
    
    # Check for errors
    error_patterns = {
        "token_limit": ["token limit", "exceeded.*token", "output token maximum"],
        "rate_limit": ["rate limit", "too many requests", "429"],
        "timeout": ["timeout", "timed out", "deadline exceeded"],
        "syntax_error": ["syntaxerror", "syntax error", "invalid syntax"],
        "import_error": ["importerror", "modulenotfounderror", "no module named"],
        "connection": ["connection refused", "connection error", "econnrefused"]
    }
    
    for error_type, patterns in error_patterns.items():
        if any(p in output_lower for p in patterns):
            quality_metrics["has_error"] = True
            quality_metrics["error_type"] = error_type
            if error_type == "token_limit":
                quality_metrics["token_limit_hit"] = True
            break
            
    # Check for code blocks
    quality_metrics["has_code"] = "```" in output or "def " in output or "class " in output
    
    # Check for verification
    verification_keywords = ["verified", "confirmed", "tested", "✓", "success", "passed"]
    quality_metrics["has_verification"] = any(kw in output_lower for kw in verification_keywords)
    
    # Estimate completeness
    if quality_metrics["has_error"]:
        quality_metrics["completeness"] = "incomplete"
    elif "wip" in output_lower or "todo" in output_lower:
        quality_metrics["completeness"] = "partial"
    elif quality_metrics["has_verification"]:
        quality_metrics["completeness"] = "complete"
        
    # Calculate quality score (0-1)
    score = 1.0
    if quality_metrics["has_error"]:
        score -= 0.5
    if quality_metrics["completeness"] == "incomplete":
        score -= 0.3
    elif quality_metrics["completeness"] == "partial":
        score -= 0.1
    if not quality_metrics["has_verification"] and quality_metrics["has_code"]:
        score -= 0.1
        
    quality_metrics["quality_score"] = max(0.0, score)
    
    return quality_metrics

def extract_task_context(output: str) -> Optional[Dict]:
    """Extract task context from output."""
    try:
        # Look for task execution markers
        task_match = re.search(r'(?:Task|TASK)\s+(\d+):\s*(.+?)(?:\n|$)', output)
        if task_match:
            return {
                "number": int(task_match.group(1)),
                "description": task_match.group(2).strip()
            }
            
        # Look for cc_execute markers
        if "cc_execute" in output:
            exec_match = re.search(r'Executing task:\s*(.+?)(?:\n|$)', output)
            if exec_match:
                return {
                    "number": 0,
                    "description": exec_match.group(1).strip()
                }
                
        return None
        
    except Exception as e:
        logger.error(f"Error extracting context: {e}")
        return None

def calculate_performance_metrics(duration: float, tokens: int, output_length: int) -> Dict:
    """Calculate performance metrics."""
    metrics = {
        "duration_seconds": duration,
        "total_tokens": tokens,
        "output_length": output_length,
        "tokens_per_second": tokens / duration if duration > 0 else 0,
        "chars_per_token": output_length / tokens if tokens > 0 else 0,
        "performance_rating": "normal"
    }
    
    # Rate performance
    if duration < 10:
        metrics["performance_rating"] = "fast"
    elif duration > 120:
        metrics["performance_rating"] = "slow"
    elif metrics["tokens_per_second"] < 10:
        metrics["performance_rating"] = "very_slow"
        
    return metrics

def should_trigger_reflection(quality: Dict, performance: Dict) -> bool:
    """Determine if self-reflection should be triggered."""
    triggers = []
    
    # Quality triggers
    if quality["quality_score"] < 0.5:
        triggers.append("low_quality")
    if quality["token_limit_hit"]:
        triggers.append("token_limit")
    if quality["has_error"] and quality["error_type"] in ["syntax_error", "import_error"]:
        triggers.append("code_error")
        
    # Performance triggers  
    if performance["performance_rating"] in ["slow", "very_slow"]:
        triggers.append("slow_performance")
    if performance["duration_seconds"] > 300:  # 5 minutes
        triggers.append("excessive_duration")
        
    return len(triggers) > 0, triggers

def store_metrics(metrics: Dict):
    """Store execution metrics in Redis."""
    try:
        r = redis.Redis(decode_responses=True)
        
        # Create metric key
        timestamp = time.time()
        metric_key = f"metrics:{int(timestamp)}"
        
        # Store full metrics
        r.setex(metric_key, 86400, json.dumps(metrics))  # 24 hour TTL
        
        # Update aggregated metrics
        r.hincrby("metrics:aggregate", "total_executions", 1)
        r.hincrbyfloat("metrics:aggregate", "total_duration", metrics["performance"]["duration_seconds"])
        r.hincrby("metrics:aggregate", "total_tokens", metrics["performance"]["total_tokens"])
        
        if metrics["quality"]["has_error"]:
            r.hincrby("metrics:aggregate", f"errors:{metrics['quality']['error_type']}", 1)
            
        # Update rolling average quality score
        r.lpush("metrics:quality_scores", metrics["quality"]["quality_score"])
        r.ltrim("metrics:quality_scores", 0, 99)  # Keep last 100
        
        # Calculate and store average
        scores = [float(s) for s in r.lrange("metrics:quality_scores", 0, -1)]
        if scores:
            avg_quality = sum(scores) / len(scores)
            r.set("metrics:average_quality", f"{avg_quality:.2f}")
            
        logger.info(f"Stored metrics: quality={metrics['quality']['quality_score']:.2f}, "
                   f"duration={metrics['performance']['duration_seconds']:.1f}s")
                   
    except Exception as e:
        logger.error(f"Error storing metrics: {e}")

def trigger_reflection(task_context: Dict, triggers: List[str], metrics: Dict):
    """Trigger self-reflection based on metrics."""
    try:
        r = redis.Redis(decode_responses=True)
        
        reflection = {
            "task": task_context,
            "triggers": triggers,
            "metrics": metrics,
            "timestamp": time.time(),
            "suggestions": []
        }
        
        # Generate improvement suggestions
        if "token_limit" in triggers:
            reflection["suggestions"].append(
                "Consider breaking the task into smaller subtasks or "
                "requesting more concise output"
            )
            
        if "slow_performance" in triggers:
            reflection["suggestions"].append(
                "Use cc_execute.md for complex tasks or increase timeout"
            )
            
        if "code_error" in triggers:
            reflection["suggestions"].append(
                "Add more explicit code examples and import statements"
            )
            
        if "low_quality" in triggers:
            reflection["suggestions"].append(
                "Improve task clarity with specific requirements and examples"
            )
            
        # Store reflection
        r.lpush("reflections:queue", json.dumps(reflection))
        r.ltrim("reflections:queue", 0, 99)  # Keep last 100
        
        logger.info(f"Triggered reflection for: {triggers}")
        logger.info(f"Suggestions: {reflection['suggestions']}")
        
    except Exception as e:
        logger.error(f"Error triggering reflection: {e}")

def main():
    """Main hook entry point."""
    if len(sys.argv) < 4:
        logger.error("Usage: record_execution_metrics.py <output> <duration> <tokens>")
        sys.exit(1)
        
    output = sys.argv[1]
    
    try:
        duration = float(sys.argv[2])
        tokens = int(sys.argv[3])
    except ValueError:
        logger.error("Invalid duration or token count")
        sys.exit(1)
        
    # Analyze output quality
    quality_metrics = analyze_output_quality(output)
    
    # Calculate performance metrics
    performance_metrics = calculate_performance_metrics(
        duration, tokens, len(output)
    )
    
    # Extract task context
    task_context = extract_task_context(output) or {
        "number": 0,
        "description": "Unknown task"
    }
    
    # Combine all metrics
    full_metrics = {
        "task": task_context,
        "quality": quality_metrics,
        "performance": performance_metrics,
        "timestamp": time.time()
    }
    
    # Store metrics
    store_metrics(full_metrics)
    
    # Check if reflection needed
    should_reflect, triggers = should_trigger_reflection(
        quality_metrics, performance_metrics
    )
    
    if should_reflect:
        trigger_reflection(task_context, triggers, full_metrics)
        
    # Log summary
    logger.info(f"Execution metrics: quality={quality_metrics['quality_score']:.2f}, "
                f"duration={duration:.1f}s, tokens={tokens}, "
                f"performance={performance_metrics['performance_rating']}")
                
    # Don't block execution
    sys.exit(0)

if __name__ == "__main__":
    # Usage example for testing
    if "--test" in sys.argv:
        print("\n=== Execution Metrics Recorder Test ===\n")
        
        # Test output quality analysis
        print("1. Testing output quality analysis:\n")
        
        test_outputs = [
            {
                "name": "Complete successful task",
                "output": """Task 1: Create a fibonacci function
                
```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

Tested the function:
✓ fibonacci(10) = 55
✓ All tests passed

The function is verified and working correctly."""
            },
            {
                "name": "Token limit error",
                "output": "I was creating the implementation but hit the output token maximum. The task is incomplete..."
            },
            {
                "name": "Syntax error in code",
                "output": """Created the function but got an error:
                
```python
def calculate(x
    return x * 2
```

SyntaxError: invalid syntax on line 1"""
            },
            {
                "name": "Partial implementation",
                "output": """Started implementing the API:

```python
@app.post("/users")
def create_user():
    # TODO: Add validation
    # TODO: Hash password
    pass
```

Still WIP - need to complete the implementation."""
            }
        ]
        
        for test in test_outputs:
            print(f"{test['name']}:")
            quality = analyze_output_quality(test['output'])
            print(f"  Quality score: {quality['quality_score']:.2f}")
            print(f"  Completeness: {quality['completeness']}")
            print(f"  Has error: {quality['has_error']}")
            if quality['has_error']:
                print(f"  Error type: {quality['error_type']}")
            print(f"  Has code: {quality['has_code']}")
            print(f"  Has verification: {quality['has_verification']}")
            print()
        
        # Test performance metrics
        print("\n2. Testing performance metrics:\n")
        
        test_cases = [
            {"duration": 5.2, "tokens": 150, "output_length": 500},
            {"duration": 45.0, "tokens": 1200, "output_length": 4000},
            {"duration": 180.0, "tokens": 2000, "output_length": 8000},
            {"duration": 2.0, "tokens": 50, "output_length": 200}
        ]
        
        for i, test in enumerate(test_cases, 1):
            perf = calculate_performance_metrics(**test)
            print(f"Test {i}:")
            print(f"  Duration: {perf['duration_seconds']}s")
            print(f"  Tokens/sec: {perf['tokens_per_second']:.1f}")
            print(f"  Performance: {perf['performance_rating']}")
            print()
        
        # Test reflection triggers
        print("\n3. Testing reflection triggers:\n")
        
        reflection_tests = [
            {
                "name": "High quality, fast",
                "quality": {"quality_score": 0.9, "has_error": False, "token_limit_hit": False},
                "performance": {"performance_rating": "fast", "duration_seconds": 5}
            },
            {
                "name": "Low quality, slow",
                "quality": {"quality_score": 0.3, "has_error": True, "error_type": "syntax_error", "token_limit_hit": False},
                "performance": {"performance_rating": "slow", "duration_seconds": 150}
            },
            {
                "name": "Token limit hit",
                "quality": {"quality_score": 0.5, "has_error": True, "error_type": "token_limit", "token_limit_hit": True},
                "performance": {"performance_rating": "normal", "duration_seconds": 30}
            }
        ]
        
        for test in reflection_tests:
            should_reflect, triggers = should_trigger_reflection(test['quality'], test['performance'])
            print(f"{test['name']}:")
            print(f"  Should reflect: {should_reflect}")
            if triggers:
                print(f"  Triggers: {triggers}")
            print()
        
        # Test Redis storage (if available)
        print("\n4. Testing metrics storage:\n")
        
        try:
            r = redis.Redis(decode_responses=True)
            r.ping()
            
            # Create test metrics
            test_metrics = {
                "task": {"number": 1, "description": "Test task"},
                "quality": analyze_output_quality(test_outputs[0]['output']),
                "performance": calculate_performance_metrics(10.5, 250, 1000),
                "timestamp": time.time()
            }
            
            # Store metrics
            store_metrics(test_metrics)
            print("✓ Metrics stored successfully")
            
            # Retrieve aggregate metrics
            aggregate = r.hgetall("metrics:aggregate")
            if aggregate:
                print("\nAggregate metrics:")
                for key, value in aggregate.items():
                    print(f"  {key}: {value}")
            
            # Check average quality
            avg_quality = r.get("metrics:average_quality")
            if avg_quality:
                print(f"\nAverage quality score: {avg_quality}")
            
            # Test reflection trigger
            should_reflect, triggers = should_trigger_reflection(
                {"quality_score": 0.3, "has_error": True, "error_type": "syntax_error", "token_limit_hit": False},
                {"performance_rating": "slow", "duration_seconds": 150}
            )
            
            if should_reflect:
                trigger_reflection(
                    {"number": 2, "description": "Failed task"},
                    triggers,
                    test_metrics
                )
                print("\n✓ Reflection triggered")
                
                # Check reflection queue
                reflections = r.lrange("reflections:queue", 0, 0)
                if reflections:
                    latest = json.loads(reflections[0])
                    print(f"  Triggers: {latest['triggers']}")
                    print(f"  Suggestions: {latest['suggestions']}")
            
        except Exception as e:
            print(f"✗ Redis test skipped: {e}")
        
        # Demonstrate full workflow
        print("\n\n5. Full workflow demonstration:\n")
        
        # Simulate a complete execution
        sample_output = """Task 5: Implement user authentication

Created authentication module:

```python
def authenticate_user(username, password):
    # Implementation here
    return True
```

✓ Tests passed
✓ Authentication working correctly"""
        
        duration = 25.5
        tokens = 450
        
        print(f"Output preview: {sample_output[:100]}...")
        print(f"Duration: {duration}s")
        print(f"Tokens: {tokens}")
        
        # Analyze
        quality = analyze_output_quality(sample_output)
        performance = calculate_performance_metrics(duration, tokens, len(sample_output))
        
        print(f"\nAnalysis:")
        print(f"  Quality score: {quality['quality_score']:.2f}")
        print(f"  Performance: {performance['performance_rating']}")
        print(f"  Tokens/sec: {performance['tokens_per_second']:.1f}")
        
        should_reflect, triggers = should_trigger_reflection(quality, performance)
        print(f"  Needs reflection: {should_reflect}")
        
        print("\n=== Test Complete ===")
    else:
        # Normal hook mode
        main()