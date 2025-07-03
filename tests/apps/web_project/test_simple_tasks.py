#!/usr/bin/env python3
"""Simple test of web project tasks using cc_execute pattern."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cc_executor.core.client import WebSocketClient

async def test_task(task_name: str, prompt: str):
    """Execute a single task and display results."""
    print(f"\n{'='*60}")
    print(f"TASK: {task_name}")
    print(f"{'='*60}")
    
    client = WebSocketClient()
    
    # Build command following CLAUDE_CODE_PROMPT_RULES.md
    cmd = f'claude -p "{prompt}" --output-format stream-json --verbose --allowedTools none --dangerously-skip-permissions'
    
    try:
        result = await client.execute_command(cmd, timeout=120)
        
        if result['success']:
            output = '\n'.join(result.get('output_data', []))
            print("SUCCESS! Output preview:")
            print("-" * 40)
            # Show first 500 chars
            print(output[:500] + "..." if len(output) > 500 else output)
            print("-" * 40)
            print(f"Duration: {result.get('duration', 0):.1f}s")
        else:
            print(f"FAILED: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        pass  # Client cleanup handled internally

async def main():
    """Run a few simple test tasks."""
    
    tasks = [
        ("Create Directories", 
         "What is a Python script that creates directories named templates, static, and src? Include the complete code with imports."),
        
        ("FastAPI Health", 
         "What is a minimal FastAPI application with a /health endpoint that returns {'status': 'ok'}? Show the complete code."),
        
        ("Todo Model",
         "What is a SQLAlchemy model for a Todo item with fields: id (integer primary key), title (string), completed (boolean)? Include all imports."),
        
        ("Simple Dockerfile",
         "What is a Dockerfile for a Python 3.10 FastAPI application that runs on port 8000? Include the complete Dockerfile content."),
        
        ("Basic Test",
         "What is a pytest test function that tests a FastAPI /health endpoint using TestClient? Show the complete test code.")
    ]
    
    print("Running simple web project tasks...")
    print(f"Total tasks: {len(tasks)}")
    
    for task_name, prompt in tasks:
        await test_task(task_name, prompt)
        await asyncio.sleep(2)  # Brief pause between tasks
    
    print("\n" + "="*60)
    print("All tasks completed!")

if __name__ == "__main__":
    asyncio.run(main())