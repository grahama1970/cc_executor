#!/usr/bin/env python3
"""
Simple orchestrator that sends tasks to Claude via WebSocket.
Each task tells Claude to use cc_execute.md.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cc_executor.client.websocket_client_standalone import WebSocketClient
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")


async def run_tasks():
    """Load and execute tasks via WebSocket."""
    
    # Load task list
    with open('setup_tasks.json') as f:
        data = json.load(f)
    
    tasks = data['task_list']['tasks']
    client = WebSocketClient(host="localhost", port=8004)
    
    logger.info(f"Orchestrator starting with {len(tasks)} tasks")
    logger.info("Each task will tell Claude to use cc_execute.md\n")
    
    results = []
    
    for i, task in enumerate(tasks):
        logger.info(f"{'='*60}")
        logger.info(f"Task {i+1}/{len(tasks)}: {task['name']}")
        logger.info(f"{'='*60}")
        
        # Build the full Claude command
        cmd = f'claude -p "{task["command"]}" --output-format stream-json --verbose --allowedTools all'
        
        logger.info("Sending to Claude via WebSocket...")
        logger.info("Claude will read cc_execute.md and execute the task")
        
        start_time = datetime.now()
        
        try:
            # Send to WebSocket - Claude will use cc_execute.md
            result = await client.execute_command(cmd, timeout=task.get('timeout', 300))
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if result['success']:
                logger.success(f"✅ Task completed in {duration:.1f}s")
                
                # Save output
                output_file = f"output_{task['id']}_{task['name'].lower().replace(' ', '_')}.json"
                with open(output_file, 'w') as f:
                    json.dump({
                        'task': task,
                        'result': result,
                        'duration': duration,
                        'timestamp': datetime.now().isoformat()
                    }, f, indent=2)
                
                logger.info(f"Output saved to {output_file}")
                
            else:
                logger.error(f"❌ Task failed: {result.get('error', 'Unknown error')}")
            
            results.append({
                'task': task['name'],
                'success': result['success'],
                'duration': duration
            })
            
        except Exception as e:
            logger.error(f"❌ Exception: {e}")
            results.append({
                'task': task['name'],
                'success': False,
                'error': str(e)
            })
        
        # Brief pause between tasks
        if i < len(tasks) - 1:
            logger.info("\nWaiting 3 seconds before next task...")
            await asyncio.sleep(3)
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("ORCHESTRATOR SUMMARY")
    logger.info(f"{'='*60}")
    
    successful = sum(1 for r in results if r.get('success', False))
    logger.info(f"Total tasks: {len(tasks)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {len(tasks) - successful}")
    
    for r in results:
        status = "✅" if r.get('success', False) else "❌"
        duration = f"{r.get('duration', 0):.1f}s" if 'duration' in r else "N/A"
        logger.info(f"{status} {r['task']} - {duration}")
    
    # Save summary
    with open('orchestrator_summary.json', 'w') as f:
        json.dump({
            'run_date': datetime.now().isoformat(),
            'total_tasks': len(tasks),
            'successful': successful,
            'failed': len(tasks) - successful,
            'results': results
        }, f, indent=2)
    
    logger.info(f"\nSummary saved to orchestrator_summary.json")


if __name__ == "__main__":
    logger.info("Starting Task Orchestrator")
    logger.info("This will send tasks to Claude via WebSocket")
    logger.info("Claude will use cc_execute.md to execute each task\n")
    
    asyncio.run(run_tasks())