#!/usr/bin/env python3
"""
Execute the basic TODO API example using cc_executor.
"""
import sys
from pathlib import Path
import json
from datetime import datetime

# Add project to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from cc_executor.prompts.cc_execute_utils import execute_task_via_websocket

def main():
    """Execute the basic task list."""
    print("="*60)
    print("CC Executor - Basic Usage Example")
    print("Building a TODO API in 3 sequential tasks")
    print("="*60)
    
    # Define tasks
    tasks = [
        {
            'num': 1,
            'name': 'Create API',
            'desc': '''What is the implementation of a FastAPI TODO application? Create folder todo_api/ with main.py containing:
- GET /todos - list all todos
- POST /todos - create a new todo  
- DELETE /todos/{id} - delete a todo
Use in-memory storage with a simple list.''',
            'timeout': 90
        },
        {
            'num': 2,
            'name': 'Write Tests',
            'desc': 'What tests are needed for the TODO API in todo_api/main.py? Read the implementation and create todo_api/test_api.py with pytest tests covering all three endpoints.',
            'timeout': 90
        },
        {
            'num': 3,
            'name': 'Add Update Feature',
            'desc': 'How can I add update functionality to the TODO API? Read todo_api/main.py and todo_api/test_api.py, then add PUT /todos/{id} endpoint with corresponding tests.',
            'timeout': 120
        }
    ]
    
    # Execute each task
    results = []
    for task in tasks:
        print(f"\n{'='*60}")
        print(f"Task {task['num']}: {task['name']}")
        print(f"{'='*60}")
        print(f"{task['desc']}")
        print(f"\nExecuting with {task['timeout']}s timeout...")
        
        result = execute_task_via_websocket(
            task=task['desc'],
            timeout=task['timeout'],
            tools=["Read", "Write", "Edit"]
        )
        
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
            'attempts': attempts
        })
        
        print(f"\n{'✅' if success else '❌'} Task completed: {status} (attempts: {attempts})")
        print(f"   Output saved to: {output_file}")
        
        if status != 'success':
            print(f"\n❌ Task failed. Check output file for details.")
            break
    
    # Summary
    print(f"\n{'='*60}")
    print("EXECUTION SUMMARY")
    print(f"{'='*60}")
    for i, r in enumerate(results, 1):
        status_icon = "✅" if r['status'] == 'success' else "❌"
        verify_icon = "🔐" if r['verification'] else "⚠️"
        print(f"{status_icon} Task {i}: {r['task']} - {r['status']} {verify_icon} (attempts: {r['attempts']})")
    
    # Verify outputs
    if all(r['status'] == 'success' for r in results):
        print(f"\n{'='*60}")
        print("VERIFICATION")
        print(f"{'='*60}")
        
        api_file = Path("todo_api/main.py")
        test_file = Path("todo_api/test_api.py")
        
        if api_file.exists():
            print("✅ API file created: todo_api/main.py")
        else:
            print("❌ API file missing")
            
        if test_file.exists():
            print("✅ Test file created: todo_api/test_api.py")
        else:
            print("❌ Test file missing")
        
        print("\nTo test the API:")
        print("  cd todo_api && uvicorn main:app --reload")
        print("\nTo run tests:")
        print("  cd todo_api && pytest test_api.py -v")

if __name__ == "__main__":
    main()