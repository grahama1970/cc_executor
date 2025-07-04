#!/usr/bin/env python3
"""
Execute TODO API example with error recovery and retry logic.
"""
import sys
from pathlib import Path
import json
from datetime import datetime
import time
from typing import Dict, Any, List

# Add project to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from cc_executor.prompts.cc_execute_utils import execute_task_via_websocket

class ErrorRecoveryExecutor:
    """Executor with error tracking and recovery."""
    
    def __init__(self):
        self.error_db_path = Path(".error_recovery.json")
        self.errors = self.load_error_db()
        
    def load_error_db(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load error history from file."""
        if self.error_db_path.exists():
            with open(self.error_db_path, 'r') as f:
                return json.load(f)
        return {}
    
    def save_error_db(self):
        """Save error history to file."""
        with open(self.error_db_path, 'w') as f:
            json.dump(self.errors, f, indent=2)
    
    def record_error(self, task_name: str, error: str, fix_applied: str = None):
        """Record an error and potential fix."""
        if task_name not in self.errors:
            self.errors[task_name] = []
        
        self.errors[task_name].append({
            'timestamp': datetime.now().isoformat(),
            'error': error,
            'fix_applied': fix_applied
        })
        self.save_error_db()
    
    def get_known_fixes(self, task_name: str) -> List[str]:
        """Get known fixes for a task."""
        if task_name not in self.errors:
            return []
        
        fixes = []
        for error_record in self.errors[task_name]:
            if error_record.get('fix_applied'):
                fixes.append(error_record['fix_applied'])
        return list(set(fixes))  # Unique fixes
    
    def execute_with_retry(self, task: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        """Execute a task with retry logic."""
        backoff_times = [5, 10, 20]  # Exponential backoff
        
        for attempt in range(max_retries + 1):
            print(f"\nAttempt {attempt + 1}/{max_retries + 1}")
            
            # Apply known fixes if this is a retry
            task_desc = task['desc']
            if attempt > 0:
                fixes = self.get_known_fixes(task['name'])
                if fixes:
                    print(f"Applying known fixes: {fixes}")
                    task_desc += "\n\nIMPORTANT FIXES TO APPLY:\n" + "\n".join(f"- {fix}" for fix in fixes)
            
            # Execute task
            result = execute_task_via_websocket(
                task=task_desc,
                timeout=task['timeout'],
                tools=["Read", "Write", "Edit"]
            )
            
            # Check result
            if result.get('success', False):
                return result
            
            # Record error
            error_msg = result.get('stderr', result.get('error', 'Unknown error'))
            print(f"\n❌ Task failed: {error_msg}")
            
            # Try to extract fix from error
            fix = None
            if "Import" in error_msg:
                fix = "Ensure all necessary imports are included"
            elif "not found" in error_msg:
                fix = "Check file paths and module names"
            elif "timeout" in error_msg:
                fix = "Increase timeout or optimize code"
                task['timeout'] = int(task['timeout'] * 1.5)  # Increase timeout
            
            self.record_error(task['name'], error_msg, fix)
            
            # Wait before retry
            if attempt < max_retries:
                wait_time = backoff_times[min(attempt, len(backoff_times)-1)]
                print(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
        
        return result  # Return last failed result

def main():
    """Execute task list with error recovery."""
    print("="*60)
    print("CC Executor - Error Recovery Example")
    print("Building TODO API with automatic error recovery")
    print("="*60)
    
    executor = ErrorRecoveryExecutor()
    
    # Define tasks with error recovery info
    tasks = [
        {
            'num': 1,
            'name': 'Create API with Error Handling',
            'desc': '''What is the implementation of a FastAPI TODO application with proper error handling? Create folder todo_api/ with main.py containing GET /todos, POST /todos, and DELETE /todos/{id} endpoints using in-memory storage.

IMPORTANT: Include these imports to avoid errors:
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional''',
            'timeout': 120
        },
        {
            'num': 2,
            'name': 'Write Comprehensive Tests',
            'desc': '''What tests are needed for the TODO API including error cases? Read todo_api/main.py and create todo_api/test_api.py with pytest tests covering all endpoints and error scenarios.

IMPORTANT: Use these imports:
from fastapi.testclient import TestClient
from main import app  # Not from todo_api.main''',
            'timeout': 120
        },
        {
            'num': 3,
            'name': 'Add Update with Validation',
            'desc': '''How can I add a robust update endpoint? Read existing files and add PUT /todos/{id} with:
- Request validation
- 404 for missing IDs  
- Partial updates support
- Comprehensive tests

Use Optional fields for partial updates.''',
            'timeout': 150
        }
    ]
    
    # Execute tasks with retry logic
    results = []
    for task in tasks:
        print(f"\n{'='*60}")
        print(f"Task {task['num']}: {task['name']}")
        print(f"{'='*60}")
        
        result = executor.execute_with_retry(task)
        
        # Save result
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path("tmp/responses")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"task_{task['num']}_{timestamp}.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        success = result.get('success', False)
        status = 'success' if success else 'failed'
        attempts = result.get('attempts', 1)
        
        # Check hook verification
        verification_passed = False
        if 'hook_verification' in result:
            verification_passed = result['hook_verification'].get('verification_passed', False)
            print(f"\n🔐 UUID Verification: {'PASSED' if verification_passed else 'FAILED'}")
        
        results.append({
            'task': task['name'],
            'status': status,
            'success': success,
            'verification': verification_passed,
            'attempts': attempts,
            'retries': len(executor.errors.get(task['name'], []))
        })
        
        print(f"\n{'✅' if success else '❌'} Task completed: {status} (attempts: {attempts})")
        if results[-1]['retries'] > 0:
            print(f"   Required {results[-1]['retries']} retries")
        print(f"   Output saved to: {output_file}")
        
        if status != 'success':
            print(f"\n❌ Task failed after all retries. Check error log.")
            break
    
    # Summary
    print(f"\n{'='*60}")
    print("EXECUTION SUMMARY")
    print(f"{'='*60}")
    for i, r in enumerate(results, 1):
        status_icon = "✅" if r['status'] == 'success' else "❌"
        retry_info = f" ({r['retries']} retries)" if r['retries'] > 0 else ""
        print(f"{status_icon} Task {i}: {r['task']} - {r['status']} ({r['duration']:.1f}s){retry_info}")
    
    # Error summary
    if executor.errors:
        print(f"\n{'='*60}")
        print("ERROR RECOVERY LOG")
        print(f"{'='*60}")
        for task_name, errors in executor.errors.items():
            print(f"\n{task_name}:")
            for err in errors[-3:]:  # Show last 3 errors
                print(f"  - {err['error'][:80]}...")
                if err.get('fix_applied'):
                    print(f"    Fix: {err['fix_applied']}")
    
    # Verify outputs
    if all(r['status'] == 'success' for r in results):
        print(f"\n{'='*60}")
        print("VERIFICATION")
        print(f"{'='*60}")
        
        api_file = Path("todo_api/main.py")
        test_file = Path("todo_api/test_api.py")
        
        if api_file.exists():
            print("✅ API file created: todo_api/main.py")
            # Check for error handling
            with open(api_file, 'r') as f:
                content = f.read()
                if 'HTTPException' in content:
                    print("✅ Error handling included")
                else:
                    print("⚠️  Warning: No HTTPException found")
        
        if test_file.exists():
            print("✅ Test file created: todo_api/test_api.py")
            # Check for error tests
            with open(test_file, 'r') as f:
                content = f.read()
                if '404' in content or 'not found' in content.lower():
                    print("✅ Error cases tested")
                else:
                    print("⚠️  Warning: No error tests found")

if __name__ == "__main__":
    main()