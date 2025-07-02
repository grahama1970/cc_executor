#!/usr/bin/env python3
"""Evaluate web project tasks with cc_execute pattern and show results."""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cc_executor.client.websocket_client_standalone import WebSocketClient

def parse_json_stream(output_data):
    """Parse JSON stream output to extract the actual response text."""
    content = []
    for line in output_data:
        try:
            data = json.loads(line)
            if data.get('type') == 'assistant' and 'text' in data.get('message', {}):
                content.append(data['message']['text'])
        except:
            pass
    return '\n'.join(content)

async def evaluate_task(task_name: str, prompt: str, criteria: list):
    """Execute and evaluate a single task."""
    print(f"\n{'='*60}")
    print(f"TASK: {task_name}")
    print(f"{'='*60}")
    
    client = WebSocketClient()
    
    # Add self-evaluation to prompt
    eval_prompt = f"""{prompt}

After providing your answer, evaluate it against these criteria:
{chr(10).join(f"{i+1}. {c}" for i, c in enumerate(criteria))}

If your response doesn't fully satisfy all criteria, provide an improved version.
Maximum self-improvements: 2"""
    
    cmd = f'claude -p "{eval_prompt}" --output-format stream-json --verbose --allowedTools none --dangerously-skip-permissions'
    
    try:
        print("Executing...")
        result = await client.execute_command(cmd, timeout=180)
        
        if result['success']:
            # Parse the actual content
            content = parse_json_stream(result.get('output_data', []))
            
            print(f"\n✅ SUCCESS! Duration: {result.get('duration', 0):.1f}s")
            print("\nOUTPUT:")
            print("-" * 40)
            # Show first 800 chars of actual content
            if len(content) > 800:
                print(content[:800] + "\n... [truncated]")
            else:
                print(content)
            print("-" * 40)
            
            # Evaluate criteria
            print("\nEVALUATION:")
            content_lower = content.lower()
            for criterion in criteria:
                # Simple keyword matching
                key_terms = [t for t in criterion.lower().split() if len(t) > 3]
                matched = any(term in content_lower for term in key_terms)
                print(f"  {'✅' if matched else '❌'} {criterion}")
            
            # Check for self-improvement
            if "improved response:" in content_lower:
                print("\n💡 Task performed self-improvement!")
                
        else:
            print(f"\n❌ FAILED: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

async def main():
    """Run and evaluate tasks."""
    
    tasks = [
        {
            "name": "Create Project Structure",
            "prompt": "What is a Python script that creates a web project directory structure with folders: templates, static, src, tests? Include the complete working code.",
            "criteria": [
                "Must use os.makedirs or Path.mkdir",
                "Creates all four directories",
                "Handles existing directories gracefully",
                "Includes main block for execution"
            ]
        },
        {
            "name": "FastAPI Health Endpoint", 
            "prompt": "What is a complete FastAPI application with a /health endpoint that returns JSON with status and timestamp? Show all imports and uvicorn run code.",
            "criteria": [
                "FastAPI import and app creation",
                "GET /health endpoint defined",
                "Returns JSON with status field",
                "Includes uvicorn.run in main block"
            ]
        },
        {
            "name": "SQLAlchemy Todo Model",
            "prompt": "What is a SQLAlchemy model for a Todo item? Include fields: id (Integer, primary key), title (String 200), description (Text), completed (Boolean, default False), created_at (DateTime, default now). Show all imports.",
            "criteria": [
                "SQLAlchemy imports included",
                "Todo class inherits from Base",
                "All five fields defined correctly",
                "Proper column types and constraints"
            ]
        },
        {
            "name": "Pytest API Tests",
            "prompt": "What is a pytest test suite for testing a FastAPI /todos endpoint? Include tests for GET (list), POST (create), and GET by id. Use TestClient and show all imports.",
            "criteria": [
                "TestClient imported from fastapi.testclient",
                "Test function for GET /todos",
                "Test function for POST /todos",
                "Uses proper assertions"
            ]
        },
        {
            "name": "Docker Configuration",
            "prompt": "What is a production-ready Dockerfile for a Python 3.10 FastAPI app? Include multi-stage build, non-root user, and healthcheck. Also show docker-compose.yml with postgres service.",
            "criteria": [
                "FROM python:3.10-slim base image",
                "Multi-stage build pattern",
                "Creates non-root user",
                "Includes HEALTHCHECK instruction",
                "docker-compose.yml with postgres"
            ]
        }
    ]
    
    print(f"Evaluating {len(tasks)} web project tasks with cc_execute pattern...")
    print("Each task includes self-evaluation and improvement capability.\n")
    
    results = []
    start_time = datetime.now()
    
    for i, task in enumerate(tasks):
        print(f"\n[{i+1}/{len(tasks)}] Starting: {task['name']}")
        await evaluate_task(task['name'], task['prompt'], task['criteria'])
        
        # Update progress
        elapsed = (datetime.now() - start_time).total_seconds()
        avg_time = elapsed / (i + 1)
        remaining = avg_time * (len(tasks) - i - 1)
        print(f"\nProgress: {i+1}/{len(tasks)} completed | Elapsed: {elapsed:.0f}s | Est. remaining: {remaining:.0f}s")
        
        if i < len(tasks) - 1:
            await asyncio.sleep(2)
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total tasks: {len(tasks)}")
    print(f"Total time: {(datetime.now() - start_time).total_seconds():.1f}s")
    print("\nAll tasks completed with self-evaluation!")

if __name__ == "__main__":
    asyncio.run(main())