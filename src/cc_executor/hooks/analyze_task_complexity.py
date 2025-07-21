#!/usr/bin/env python3
"""
Analyze task complexity using BM25 similarity search against historical tasks.
This hook runs before task execution to estimate timeout requirements.
"""

import sys
import os
import json
from typing import Dict, Optional
from loguru import logger

# Import Redis directly
import redis


from rank_bm25 import BM25Okapi

def extract_task_from_file(file_path: str) -> Optional[str]:
    """Extract task description from a file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Look for task definitions in markdown
        if file_path.endswith('.md'):
            # Extract first question (task definition)
            for line in content.split('\n'):
                if '?' in line and not line.startswith('#'):
                    return line.strip()
                    
        # For Python files, look for docstrings or comments
        elif file_path.endswith('.py'):
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'task:' in line.lower() or 'todo:' in line.lower():
                    return line.split(':', 1)[1].strip()
                    
        # Default: use first 200 chars
        return content[:200].replace('\n', ' ').strip()
        
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None

def estimate_complexity(task_text: str) -> Dict[str, any]:
    """Estimate task complexity using historical data."""
    try:
        # Connect to Redis
        r = redis.Redis(decode_responses=True)
        
        # Get historical tasks with timing data
        historical_tasks = r.hgetall("task:history") or {}
        
        if not historical_tasks:
            logger.info("No historical data, using default complexity")
            return {
                "estimated_timeout": 120,
                "complexity": "unknown",
                "based_on": "default",
                "confidence": 0.0
            }
        
        # BM25 similarity search
        task_ids = list(historical_tasks.keys())
        task_texts = list(historical_tasks.values())
        
        # Tokenize for BM25
        tokenized_tasks = [text.lower().split() for text in task_texts]
        tokenized_query = task_text.lower().split()
        
        bm25 = BM25Okapi(tokenized_tasks)
        scores = bm25.get_scores(tokenized_query)
        
        # Get top 3 matches
        top_indices = scores.argsort()[-3:][::-1]
        
        # Calculate weighted average timeout
        total_weight = 0
        weighted_timeout = 0
        
        for idx in top_indices:
            if scores[idx] > 0:
                task_id = task_ids[idx]
                timing_data = r.hget("task:timing", task_id)
                
                if timing_data:
                    timing = json.loads(timing_data)
                    weight = scores[idx]
                    weighted_timeout += timing.get('duration', 120) * weight
                    total_weight += weight
        
        if total_weight > 0:
            estimated = int(weighted_timeout / total_weight)
            # Add 50% buffer for safety
            estimated = int(estimated * 1.5)
            
            # Determine complexity level
            if estimated < 30:
                complexity = "simple"
            elif estimated < 120:
                complexity = "medium"
            else:
                complexity = "complex"
                
            return {
                "estimated_timeout": min(estimated, 600),  # Cap at 10 minutes
                "complexity": complexity,
                "based_on": f"{len(top_indices)} similar tasks",
                "confidence": float(scores[top_indices[0]])
            }
        
        return estimate_simple_complexity(task_text)
        
    except Exception as e:
        logger.error(f"Error estimating complexity: {e}")
        return {
            "estimated_timeout": 120,
            "complexity": "unknown",
            "based_on": "error",
            "confidence": 0.0
        }

def estimate_simple_complexity(task_text: str) -> Dict[str, any]:
    """Simple keyword-based complexity estimation."""
    task_lower = task_text.lower()
    
    # Complexity indicators
    complex_keywords = ['analyze', 'refactor', 'implement', 'design', 'architecture', 
                       'concurrent', 'async', 'websocket', 'database', 'api']
    medium_keywords = ['create', 'update', 'modify', 'test', 'validate', 'endpoint']
    simple_keywords = ['add', 'fix', 'rename', 'move', 'delete', 'check']
    
    # Count keyword matches
    complex_count = sum(1 for kw in complex_keywords if kw in task_lower)
    medium_count = sum(1 for kw in medium_keywords if kw in task_lower)
    simple_count = sum(1 for kw in simple_keywords if kw in task_lower)
    
    # Determine complexity
    if complex_count >= 2 or 'concurrent' in task_lower:
        return {
            "estimated_timeout": 300,
            "complexity": "complex",
            "based_on": "keyword analysis",
            "confidence": 0.6
        }
    elif medium_count >= 2 or complex_count >= 1:
        return {
            "estimated_timeout": 120,
            "complexity": "medium", 
            "based_on": "keyword analysis",
            "confidence": 0.5
        }
    else:
        return {
            "estimated_timeout": 60,
            "complexity": "simple",
            "based_on": "keyword analysis",
            "confidence": 0.4
        }

def main():
    """Main hook entry point."""
    if len(sys.argv) < 2:
        logger.error("Usage: analyze_task_complexity.py <file_path>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    
    # Extract task from file
    task_text = extract_task_from_file(file_path)
    
    if not task_text:
        logger.warning(f"Could not extract task from {file_path}")
        sys.exit(0)
        
    # Estimate complexity
    complexity = estimate_complexity(task_text)
    
    # Store in Redis
    try:
        # Store in Redis for WebSocket handler to read
        r = redis.Redis(decode_responses=True)
        
        # Use file path as key for current task
        key = f"task:current:{os.path.basename(file_path)}"
        r.setex(key, 300, json.dumps(complexity))  # 5 minute TTL
        
        # Also store in task complexity history
        task_id = f"task_{int(os.path.getmtime(file_path))}"
        r.hset("task:complexity", task_id, json.dumps(complexity))
        
        logger.info(f"Task complexity: {complexity['complexity']} "
                   f"(timeout: {complexity['estimated_timeout']}s, "
                   f"confidence: {complexity['confidence']:.2f})")
                   
    except Exception as e:
        logger.error(f"Error storing complexity data: {e}")
        logger.info(f"Task complexity (no storage): {complexity['complexity']} "
                   f"(timeout: {complexity['estimated_timeout']}s)")
        
    # Exit successfully - hook should not block execution
    sys.exit(0)

if __name__ == "__main__":
    # Usage example for testing
    if "--test" in sys.argv:
        # Test mode - demonstrate functionality
        print("\n=== Task Complexity Analyzer Test ===\n")
        
        # Test cases
        test_tasks = [
            "Add a simple print statement to hello.py",
            "Implement a concurrent websocket handler with async processing",
            "Create a REST API endpoint for user authentication",
            "Fix typo in README.md",
            "Refactor the database connection pool to handle concurrent requests",
            "Analyze performance bottlenecks in the async task queue"
        ]
        
        print("Testing complexity estimation for various tasks:\n")
        
        for task in test_tasks:
            complexity = estimate_complexity(task)
            print(f"Task: {task[:60]}...")
            print(f"  Complexity: {complexity['complexity']}")
            print(f"  Timeout: {complexity['estimated_timeout']}s")
            print(f"  Based on: {complexity['based_on']}")
            print(f"  Confidence: {complexity['confidence']:.2f}")
            print()
        
        # Test file extraction
        print("\nTesting file extraction:")
        
        # Create test files
        test_md = "/tmp/test_task.md"
        with open(test_md, 'w') as f:
            f.write("# Task\n\nCan you implement a websocket handler?\n\nDetails here...")
        
        test_py = "/tmp/test_task.py"
        with open(test_py, 'w') as f:
            f.write('"""Task: Create a function to calculate fibonacci numbers"""\n\ndef fib(n):\n    pass')
        
        for test_file in [test_md, test_py]:
            task_text = extract_task_from_file(test_file)
            print(f"\nFile: {test_file}")
            print(f"Extracted: {task_text}")
            if task_text:
                complexity = estimate_complexity(task_text)
                print(f"Complexity: {complexity}")
        
        # Cleanup
        os.remove(test_md)
        os.remove(test_py)
        
        print("\n=== Test Complete ===")
    else:
        # Normal hook mode
        main()