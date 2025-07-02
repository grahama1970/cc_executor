#!/usr/bin/env python3
"""
Update task status after execution.
Records completion status, exit codes, and triggers self-improvement if needed.
"""

import sys
import os
import json
import redis
import time
from typing import Dict, Optional
from loguru import logger

def parse_task_info(task_str: str) -> Dict[str, any]:
    """Parse task information from string."""
    try:
        # Handle different task formats
        if task_str.startswith('{'):
            # JSON format
            return json.loads(task_str)
        else:
            # Simple string format "Task N: description"
            import re
            match = re.match(r'Task (\d+):\s*(.+)', task_str)
            if match:
                return {
                    "number": int(match.group(1)),
                    "description": match.group(2).strip()
                }
            else:
                return {
                    "number": 0,
                    "description": task_str
                }
    except Exception as e:
        logger.error(f"Error parsing task info: {e}")
        return {"number": 0, "description": str(task_str)}

def determine_improvement_needed(exit_code: int, task_info: Dict) -> Optional[Dict]:
    """Determine if task needs improvement based on exit code."""
    if exit_code == 0:
        return None  # Success, no improvement needed
        
    # Map exit codes to improvement strategies
    improvements = {
        1: {
            "type": "general_failure",
            "strategy": "Add more explicit instructions and examples",
            "retry": True
        },
        124: {
            "type": "timeout",
            "strategy": "Increase timeout or use cc_execute.md for complex tasks",
            "retry": True
        },
        137: {
            "type": "killed",
            "strategy": "Check memory usage, reduce task complexity",
            "retry": True
        },
        -15: {
            "type": "terminated",
            "strategy": "Task was cancelled, check if it was taking too long",
            "retry": False
        }
    }
    
    # Special handling for token limit errors
    if task_info.get("description", "").lower().count("token") > 0:
        return {
            "type": "token_limit",
            "strategy": "Break into smaller subtasks or request more concise output",
            "retry": True
        }
        
    return improvements.get(exit_code, {
        "type": "unknown_failure",
        "strategy": f"Investigate exit code {exit_code}",
        "retry": True
    })

def update_task_metrics(task_info: Dict, exit_code: int, duration: Optional[float] = None):
    """Update task execution metrics in Redis."""
    try:
        r = redis.Redis(decode_responses=True)
        
        task_key = f"task_{task_info['number']}"
        
        # Update status
        status = "completed" if exit_code == 0 else "failed"
        r.hset("task:status", task_key, status)
        
        # Store detailed execution record
        execution_record = {
            "task_number": task_info['number'],
            "description": task_info['description'],
            "exit_code": exit_code,
            "status": status,
            "timestamp": time.time(),
            "duration": duration
        }
        
        # Add to execution history
        r.lpush("task:execution_history", json.dumps(execution_record))
        r.ltrim("task:execution_history", 0, 999)  # Keep last 1000 executions
        
        # Update task timing if successful
        if exit_code == 0 and duration:
            timing_data = {
                "duration": duration,
                "timestamp": time.time(),
                "task": task_info['description']
            }
            r.hset("task:timing", task_key, json.dumps(timing_data))
            
            # Also add to BM25 corpus for future similarity searches
            r.hset("task:history", task_key, task_info['description'])
            
        # Calculate success rate
        history = r.lrange("task:execution_history", 0, 99)
        successes = sum(1 for h in history if json.loads(h)['status'] == 'completed')
        success_rate = (successes / len(history) * 100) if history else 0
        
        r.set("task:success_rate", f"{success_rate:.1f}")
        
        logger.info(f"Task {task_info['number']} {status} "
                   f"(exit code: {exit_code}, success rate: {success_rate:.1f}%)")
                   
    except Exception as e:
        logger.error(f"Error updating metrics: {e}")

def trigger_self_improvement(task_info: Dict, improvement: Dict):
    """Trigger self-improvement for failed tasks."""
    try:
        r = redis.Redis(decode_responses=True)
        
        # Create improvement suggestion
        suggestion = {
            "task_number": task_info['number'],
            "original": task_info['description'],
            "failure_type": improvement['type'],
            "strategy": improvement['strategy'],
            "should_retry": improvement['retry'],
            "timestamp": time.time()
        }
        
        # Store in improvement queue
        r.lpush("task:improvement_queue", json.dumps(suggestion))
        
        # Also store as pending improvement
        r.hset("task:improvements", f"task_{task_info['number']}", json.dumps(suggestion))
        
        logger.info(f"Self-improvement triggered for Task {task_info['number']}: "
                   f"{improvement['strategy']}")
                   
        # If this is a task list, update the template
        if "task_list" in os.environ.get('CLAUDE_CONTEXT', '').lower():
            update_task_list_template(task_info, suggestion)
            
    except Exception as e:
        logger.error(f"Error triggering improvement: {e}")

def update_task_list_template(task_info: Dict, suggestion: Dict):
    """Update task list template with improvement."""
    try:
        # Find task list file
        context = os.environ.get('CLAUDE_CONTEXT', '')
        
        import re
        file_match = re.search(r'(/[^\s]+task_list\.md)', context)
        if not file_match:
            return
            
        file_path = file_match.group(1)
        
        if os.path.exists(file_path):
            logger.info(f"Updating task list template: {file_path}")
            
            # This would normally update the evolution history
            # For now, just log the suggestion
            logger.info(f"Suggested improvement: {suggestion['strategy']}")
            
    except Exception as e:
        logger.error(f"Error updating template: {e}")

def main():
    """Main hook entry point."""
    if len(sys.argv) < 3:
        logger.error("Usage: update_task_status.py <task_info> <exit_code>")
        sys.exit(1)
        
    task_str = sys.argv[1]
    exit_code = int(sys.argv[2])
    
    # Parse task information
    task_info = parse_task_info(task_str)
    
    # Calculate duration if available
    duration = None
    if 'CLAUDE_DURATION' in os.environ:
        try:
            duration = float(os.environ['CLAUDE_DURATION'])
        except:
            pass
            
    # Update metrics
    update_task_metrics(task_info, exit_code, duration)
    
    # Check if improvement needed
    if exit_code != 0:
        improvement = determine_improvement_needed(exit_code, task_info)
        if improvement:
            trigger_self_improvement(task_info, improvement)
            
    # Don't block execution
    sys.exit(0)

if __name__ == "__main__":
    # Usage example for testing
    if "--test" in sys.argv:
        print("\n=== Task Status Update Hook Test ===\n")
        
        # Test task info parsing
        print("1. Testing task info parsing:\n")
        
        test_tasks = [
            'Task 1: Create a hello world function',
            '{"number": 2, "description": "Implement WebSocket handler"}',
            'Task 5: Test all endpoints',
            'Some random task description without number',
            '{"number": 3, "description": "Deploy to production", "priority": "high"}'
        ]
        
        for task_str in test_tasks:
            parsed = parse_task_info(task_str)
            print(f"Input: {task_str[:50]}...")
            print(f"Parsed: {parsed}")
            print()
        
        # Test improvement determination
        print("\n2. Testing improvement strategies:\n")
        
        test_cases = [
            (0, {"number": 1, "description": "Successful task"}),
            (1, {"number": 2, "description": "Failed task"}),
            (124, {"number": 3, "description": "Task that timed out"}),
            (137, {"number": 4, "description": "Task killed by OOM"}),
            (-15, {"number": 5, "description": "Task terminated by user"}),
            (255, {"number": 6, "description": "Unknown error"}),
            (1, {"number": 7, "description": "Hit token limit error"})
        ]
        
        for exit_code, task_info in test_cases:
            improvement = determine_improvement_needed(exit_code, task_info)
            print(f"Task {task_info['number']} (exit {exit_code}):")
            if improvement:
                print(f"  Type: {improvement['type']}")
                print(f"  Strategy: {improvement['strategy']}")
                print(f"  Retry: {improvement['retry']}")
            else:
                print("  ✓ Success - no improvement needed")
            print()
        
        # Test Redis metrics update
        print("\n3. Testing metrics update (if Redis available):\n")
        
        try:
            r = redis.Redis(decode_responses=True)
            r.ping()
            
            # Update some test tasks
            test_executions = [
                ({"number": 1, "description": "Setup environment"}, 0, 5.5),
                ({"number": 2, "description": "Create API endpoint"}, 0, 45.2),
                ({"number": 3, "description": "Complex websocket task"}, 124, 300.0),
                ({"number": 4, "description": "Run tests"}, 1, 12.3),
                ({"number": 5, "description": "Deploy"}, 0, 120.5)
            ]
            
            for task_info, exit_code, duration in test_executions:
                update_task_metrics(task_info, exit_code, duration)
            
            # Check stored metrics
            print("Task statuses:")
            statuses = r.hgetall("task:status")
            for task, status in statuses.items():
                print(f"  {task}: {status}")
            
            # Check success rate
            success_rate = r.get("task:success_rate")
            if success_rate:
                print(f"\nOverall success rate: {success_rate}%")
            
            # Check execution history
            history = r.lrange("task:execution_history", 0, 4)
            if history:
                print(f"\nRecent executions: {len(history)}")
                latest = json.loads(history[0])
                print(f"  Latest: Task {latest['task_number']} - {latest['status']}")
            
            # Cleanup test data
            for i in range(1, 6):
                r.hdel("task:status", f"task_{i}")
                r.hdel("task:timing", f"task_{i}")
                r.hdel("task:history", f"task_{i}")
            
        except Exception as e:
            print(f"✗ Redis test skipped: {e}")
        
        # Test self-improvement triggering
        print("\n\n4. Testing self-improvement system:\n")
        
        failed_task = {"number": 10, "description": "Create complex async handler"}
        improvement = {
            "type": "timeout",
            "strategy": "Break into smaller subtasks",
            "retry": True
        }
        
        print(f"Failed task: {failed_task['description']}")
        print(f"Improvement: {improvement['strategy']}")
        
        try:
            r = redis.Redis(decode_responses=True)
            r.ping()
            
            # Trigger improvement
            trigger_self_improvement(failed_task, improvement)
            
            # Check improvement queue
            queue = r.lrange("task:improvement_queue", 0, 0)
            if queue:
                suggestion = json.loads(queue[0])
                print(f"\n✓ Improvement queued:")
                print(f"  Task: {suggestion['task_number']}")
                print(f"  Failure type: {suggestion['failure_type']}")
                print(f"  Strategy: {suggestion['strategy']}")
                print(f"  Should retry: {suggestion['should_retry']}")
            
            # Check improvements hash
            stored = r.hget("task:improvements", "task_10")
            if stored:
                print(f"\n✓ Improvement stored for future reference")
            
            # Cleanup
            r.delete("task:improvement_queue")
            r.hdel("task:improvements", "task_10")
            
        except Exception as e:
            print(f"✗ Redis improvement test skipped: {e}")
        
        # Demonstrate full workflow
        print("\n\n5. Full workflow demonstration:\n")
        
        # Simulate a task execution
        demo_task = "Task 15: Implement real-time data synchronization"
        demo_exit_code = 124  # Timeout
        demo_duration = 300.0
        
        print(f"Executing: {demo_task}")
        print(f"Result: Exit code {demo_exit_code} (timeout)")
        print(f"Duration: {demo_duration}s")
        
        # Parse task
        task_info = parse_task_info(demo_task)
        print(f"\nParsed task info: {task_info}")
        
        # Determine improvement
        improvement = determine_improvement_needed(demo_exit_code, task_info)
        if improvement:
            print(f"\nImprovement needed:")
            print(f"  Type: {improvement['type']}")
            print(f"  Strategy: {improvement['strategy']}")
            print(f"  Should retry: {improvement['retry']}")
        
        # Would update metrics and trigger improvement
        print("\nIn production, this would:")
        print("1. Update task status to 'failed'")
        print("2. Record execution in history")
        print("3. Update success rate metrics")
        print("4. Queue improvement suggestion")
        print("5. Potentially update task template")
        
        # Test edge cases
        print("\n\n6. Testing edge cases:\n")
        
        edge_cases = [
            ("Empty task", "", 1),
            ("Very long task", "A" * 500, 0),
            ("Special characters", "Task $%: Do @#! stuff", 1),
            ("JSON in description", '{"task": "nested", "exit": 0}', 0)
        ]
        
        for name, task_str, exit_code in edge_cases:
            print(f"{name}:")
            try:
                parsed = parse_task_info(task_str)
                print(f"  Parsed: number={parsed['number']}, desc={parsed['description'][:30]}...")
            except Exception as e:
                print(f"  Error: {e}")
        
        print("\n=== Test Complete ===")
    else:
        # Normal hook mode
        main()