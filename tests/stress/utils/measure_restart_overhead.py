#!/usr/bin/env python3
"""
Measure actual WebSocket handler restart overhead
"""

import asyncio
import os
import subprocess
import sys
import time
import websockets

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'src'))

from loguru import logger
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss.SSS}</green> | <level>{message}</level>")

async def measure_restart_time():
    """Measure how long it takes to kill and restart the handler"""
    
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.join(project_root, 'src')
    if 'ANTHROPIC_API_KEY' in env:
        del env['ANTHROPIC_API_KEY']
    
    restart_times = []
    
    for i in range(5):
        logger.info(f"\n=== Measurement {i+1}/5 ===")
        
        # Time the kill operation
        kill_start = time.time()
        os.system('pkill -9 -f websocket_handler 2>/dev/null')
        os.system('lsof -ti:8004 | xargs -r kill -9 2>/dev/null')
        kill_time = time.time() - kill_start
        logger.info(f"Kill time: {kill_time*1000:.1f}ms")
        
        # Small delay to ensure process is dead
        await asyncio.sleep(0.1)
        
        # Time the startup
        start_time = time.time()
        handler = subprocess.Popen(
            [sys.executable, "-m", "cc_executor.core.websocket_handler"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=project_root
        )
        
        # Wait for handler to be ready
        ready = False
        while time.time() - start_time < 5:
            try:
                async with websockets.connect("ws://localhost:8004/ws", 
                                            open_timeout=0.1,
                                            close_timeout=0.1) as ws:
                    await ws.close()
                ready = True
                break
            except:
                await asyncio.sleep(0.05)
        
        startup_time = time.time() - start_time
        
        if ready:
            logger.success(f"Startup time: {startup_time*1000:.1f}ms")
            total_time = kill_time + startup_time + 0.1  # Include safety delay
            logger.info(f"Total restart time: {total_time*1000:.1f}ms")
            restart_times.append(total_time)
        else:
            logger.error("Failed to start")
        
        # Kill for next iteration
        handler.terminate()
        handler.wait()
        await asyncio.sleep(0.5)
    
    # Summary
    if restart_times:
        avg_time = sum(restart_times) / len(restart_times)
        min_time = min(restart_times)
        max_time = max(restart_times)
        
        logger.info("\n" + "="*50)
        logger.info("RESTART OVERHEAD SUMMARY")
        logger.info("="*50)
        logger.info(f"Average: {avg_time*1000:.1f}ms ({avg_time:.2f}s)")
        logger.info(f"Minimum: {min_time*1000:.1f}ms")
        logger.info(f"Maximum: {max_time*1000:.1f}ms")
        logger.info(f"\nFor 50 tasks: {avg_time * 50:.1f}s total overhead")
        
        if avg_time < 1.0:
            logger.success("\n✅ You're right! Restart overhead is less than 1 second!")
        else:
            logger.warning(f"\n⚠️ Restart overhead is {avg_time:.1f}s")

if __name__ == "__main__":
    asyncio.run(measure_restart_time())