#!/usr/bin/env python3
"""
Execute blog platform example with pre-flight and post-execution hooks.
"""
import sys
from pathlib import Path
import json
from datetime import datetime
import subprocess
import os

# Add project to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from cc_executor.prompts.cc_execute_utils import execute_task_via_websocket

def run_preflight_check():
    """Run the pre-flight assessment hook."""
    print("="*60)
    print("RUNNING PRE-FLIGHT ASSESSMENT")
    print("="*60)
    
    env = os.environ.copy()
    env['CLAUDE_FILE'] = str(Path(__file__).parent / 'task_list.md')
    
    hook_script = project_root / 'src/cc_executor/hooks/task_list_preflight_check.py'
    
    result = subprocess.run(
        [sys.executable, str(hook_script)],
        env=env,
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)
    
    return result.returncode == 0

def run_completion_report(session_id: str):
    """Run the post-execution report hook."""
    print("\n" + "="*60)
    print("GENERATING COMPLETION REPORT")
    print("="*60)
    
    env = os.environ.copy()
    env['CLAUDE_TASK_LIST_FILE'] = str(Path(__file__).parent / 'task_list.md')
    env['CLAUDE_SESSION_ID'] = session_id
    
    hook_script = project_root / 'src/cc_executor/hooks/task_list_completion_report.py'
    
    # Create reports directory
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    result = subprocess.run(
        [sys.executable, str(hook_script)],
        env=env,
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent)
    )
    
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)

def main():
    """Execute blog platform with hooks."""
    print("="*60)
    print("CC Executor - Hooks Example")
    print("Building Blog Platform with Quality Assurance")
    print("="*60)
    
    # Create blog platform directory
    blog_dir = Path("blog_platform")
    blog_dir.mkdir(exist_ok=True)
    (blog_dir / "routers").mkdir(exist_ok=True)
    (blog_dir / "tests").mkdir(exist_ok=True)
    
    # Run pre-flight check
    if not run_preflight_check():
        response = input("\nPre-flight check raised concerns. Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Execution cancelled.")
            return
    
    # Generate session ID
    session_id = f"blog_platform_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Define tasks
    tasks = [
        {
            'num': 1,
            'name': 'Create Database Models',
            'desc': 'What database models are needed for a blog platform? Create blog_platform/models.py with SQLAlchemy models for User (id, username, email, created_at) and Post (id, title, content, author_id, created_at, updated_at).',
            'timeout': 60
        },
        {
            'num': 2,
            'name': 'Create FastAPI Application',
            'desc': 'How do I create a FastAPI application for the blog? Read blog_platform/models.py and create blog_platform/main.py with FastAPI app initialization, database setup, and CORS middleware configuration.',
            'timeout': 90
        },
        {
            'num': 3,
            'name': 'Implement User Endpoints',
            'desc': 'What REST endpoints are needed for user management? Read existing files in blog_platform/ and create blog_platform/routers/users.py with POST /users (create user), GET /users/{id} (get user), and GET /users (list users) endpoints.',
            'timeout': 120
        },
        {
            'num': 4,
            'name': 'Implement Post Endpoints',
            'desc': 'How can I add blog post functionality? Read the models and existing routers, then create blog_platform/routers/posts.py with full CRUD endpoints: POST /posts, GET /posts, GET /posts/{id}, PUT /posts/{id}, DELETE /posts/{id}.',
            'timeout': 120
        },
        {
            'num': 5,
            'name': 'Write Integration Tests',
            'desc': 'How do I test the blog API endpoints? Read all files in blog_platform/ and create blog_platform/tests/test_api.py with pytest tests covering user creation, post CRUD operations, and authentication flows.',
            'timeout': 150
        }
    ]
    
    # Execute each task
    results = []
    all_outputs = {}
    
    for task in tasks:
        print(f"\n{'='*60}")
        print(f"Task {task['num']}: {task['name']}")
        print(f"{'='*60}")
        print(f"Executing with {task['timeout']}s timeout...")
        
        start_time = datetime.now()
        
        result = execute_task_via_websocket(
            task=task['desc'],
            timeout=task['timeout'],
            tools=["Read", "Write", "Edit"]
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Save result
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path("tmp/responses")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"{session_id}_task_{task['num']}_{timestamp}.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        status = result.get('status', 'unknown')
        
        # Store for report
        all_outputs[f"task_{task['num']}"] = {
            'name': task['name'],
            'status': status,
            'duration': duration,
            'output': result
        }
        
        results.append({
            'task': task['name'],
            'status': status,
            'duration': duration
        })
        
        print(f"\n✅ Task completed: {status} ({duration:.1f}s)")
        print(f"   Output saved to: {output_file}")
        
        if status != 'success':
            print(f"\n❌ Task failed. Check output file for details.")
            # Continue anyway to demonstrate partial completion
    
    # Save all outputs for report
    session_file = Path("tmp/responses") / f"{session_id}_all_outputs.json"
    with open(session_file, 'w') as f:
        json.dump(all_outputs, f, indent=2)
    
    # Summary
    print(f"\n{'='*60}")
    print("EXECUTION SUMMARY")
    print(f"{'='*60}")
    for i, r in enumerate(results, 1):
        status_icon = "✅" if r['status'] == 'success' else "❌"
        print(f"{status_icon} Task {i}: {r['task']} - {r['status']} ({r['duration']:.1f}s)")
    
    # Generate completion report
    run_completion_report(session_id)
    
    # Final verification
    print(f"\n{'='*60}")
    print("FILE VERIFICATION")
    print(f"{'='*60}")
    
    expected_files = [
        "blog_platform/models.py",
        "blog_platform/main.py",
        "blog_platform/routers/users.py",
        "blog_platform/routers/posts.py",
        "blog_platform/tests/test_api.py"
    ]
    
    for file_path in expected_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - Missing")
    
    print(f"\nReports generated in: reports/")
    print(f"Session outputs in: tmp/responses/{session_id}_*.json")

if __name__ == "__main__":
    main()