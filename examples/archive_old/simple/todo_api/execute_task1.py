#!/usr/bin/env python3
"""
Execute Task 1 from the self-improving task list.
Tests the cc_execute.md WebSocket pattern.
"""

from pathlib import Path
from datetime import datetime
import json
import sys

# Add src to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from cc_executor.prompts.cc_execute_utils import execute_task_via_websocket

# Task 1 definition from self_improving_task_list.md
task = "What is the implementation of a FastAPI TODO application? Create folder todo_api/ with main.py containing GET /todos, POST /todos, and DELETE /todos/{id} endpoints. Use in-memory list storage where each todo has id (int), title (str), and completed (bool) fields."

print("📋 Executing Task 1: Create TODO API Structure")
print(f"Task: {task}")
print("-" * 80)

# Execute the task
result = execute_task_via_websocket(
    task=task,
    timeout=120,
    tools=["Write"]
)

# Save result to tmp/responses/
output_path = Path("tmp/responses") / f"task1_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, 'w') as f:
    json.dump(result, f, indent=2)

print(f"\n💾 Result saved to: {output_path}")

# Check if task was successful
if result.get("status") == "success":
    print("✅ Task 1 completed successfully!")
    
    # Verify the file was created
    expected_file = Path("todo_api/main.py")
    if expected_file.exists():
        print(f"✓ Verified: {expected_file} was created")
        print(f"  File size: {expected_file.stat().st_size} bytes")
    else:
        print(f"❌ Warning: Expected file {expected_file} not found")
else:
    print(f"❌ Task 1 failed: {result.get('error', 'Unknown error')}")