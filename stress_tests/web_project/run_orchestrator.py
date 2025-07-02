#!/usr/bin/env python3
"""Simple orchestrator that sends tasks to Claude via WebSocket."""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cc_executor.client.websocket_client_standalone import WebSocketClient

async def main():
    # Load tasks
    with open('orchestrator_tasks.json') as f:
        data = json.load(f)
    
    tasks = data['task_list']['tasks']
    client = WebSocketClient()
    
    print(f"Running {len(tasks)} tasks via WebSocket...")
    print("Each task will use cc_execute.md pattern\n")
    
    for i, task in enumerate(tasks):
        print(f"\n{'='*60}")
        print(f"Task {i+1}/{len(tasks)}: {task['name']}")
        print(f"{'='*60}")
        
        # Send the prompt that tells Claude to use cc_execute.md
        cmd = f'claude -p "{task["prompt"]}" --output-format stream-json --verbose --allowedTools all'
        
        start = datetime.now()
        result = await client.execute_command(cmd, timeout=300)
        duration = (datetime.now() - start).total_seconds()
        
        if result['success']:
            print(f"✅ Task completed in {duration:.1f}s")
            # Save output
            output_file = f"output_{task['id']}.txt"
            with open(output_file, 'w') as f:
                f.write('\n'.join(result.get('output_data', [])))
            print(f"   Output saved to {output_file}")
        else:
            print(f"❌ Task failed: {result.get('error', 'Unknown error')}")
        
        print(f"\nTask {i+1} complete.")
    
    print(f"\n{'='*60}")
    print("All tasks completed!")

if __name__ == "__main__":
    asyncio.run(main())