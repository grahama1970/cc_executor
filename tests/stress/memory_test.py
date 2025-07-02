#!/usr/bin/env python3
"""
Test WebSocket handler memory usage
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import websockets
import uuid
import psutil
from pathlib import Path
from datetime import datetime

# Add src to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'src'))

from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")

class MemoryMonitorTest:
    def __init__(self):
        self.ws_process = None
        self.ws_port = 8004
        self.ws_url = f"ws://localhost:{self.ws_port}/ws"
        self.memory_samples = []
    
    async def start_handler(self):
        """Start WebSocket handler and return process"""
        logger.info("Starting WebSocket handler...")
        
        # Kill any existing processes
        os.system('pkill -9 -f websocket_handler')
        os.system(f'lsof -ti:{self.ws_port} | xargs -r kill -9 2>/dev/null')
        await asyncio.sleep(2)
        
        # Setup environment
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.join(project_root, 'src')
        
        # CRITICAL: UNSET ANTHROPIC_API_KEY
        if 'ANTHROPIC_API_KEY' in env:
            del env['ANTHROPIC_API_KEY']
        
        # Start handler
        handler_path = os.path.join(project_root, 'src/cc_executor/core/websocket_handler.py')
        self.ws_process = subprocess.Popen(
            [sys.executable, handler_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        # Wait for startup
        await asyncio.sleep(3)
        
        # Verify it's running
        try:
            async with websockets.connect(self.ws_url, ping_timeout=5) as ws:
                await ws.close()
            logger.success(f"WebSocket handler started with PID: {self.ws_process.pid}")
            return True
        except:
            logger.error("Failed to start WebSocket handler")
            return False
    
    def get_memory_usage(self):
        """Get memory usage of the WebSocket handler process"""
        if not self.ws_process or self.ws_process.poll() is not None:
            return None
        
        try:
            process = psutil.Process(self.ws_process.pid)
            # Get memory info
            mem_info = process.memory_info()
            return {
                "rss": mem_info.rss / 1024 / 1024,  # MB
                "vms": mem_info.vms / 1024 / 1024,  # MB
                "percent": process.memory_percent(),
                "timestamp": time.time()
            }
        except:
            return None
    
    async def monitor_memory(self, duration=5):
        """Monitor memory usage for a duration"""
        samples = []
        start = time.time()
        
        while time.time() - start < duration:
            mem = self.get_memory_usage()
            if mem:
                samples.append(mem)
            await asyncio.sleep(0.5)
        
        return samples
    
    async def execute_claude_command(self, command, monitor=True):
        """Execute a Claude command and monitor memory"""
        logger.info(f"Executing: {command[:50]}...")
        
        if monitor:
            # Start memory monitoring task
            monitor_task = asyncio.create_task(self.monitor_memory(30))
        
        try:
            async with websockets.connect(self.ws_url, ping_timeout=60) as ws:
                # Send command
                request = {
                    "jsonrpc": "2.0",
                    "method": "execute",
                    "params": {"command": command},
                    "id": str(uuid.uuid4())
                }
                
                await ws.send(json.dumps(request))
                
                # Wait for completion
                while True:
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        data = json.loads(response)
                        
                        if data.get("method") == "process.completed":
                            exit_code = data.get("params", {}).get("exit_code")
                            logger.info(f"Command completed with exit code: {exit_code}")
                            break
                    except asyncio.TimeoutError:
                        continue
                
                if monitor:
                    # Get memory samples
                    samples = await monitor_task
                    return samples
                
        except Exception as e:
            logger.error(f"Command failed: {e}")
            if monitor and not monitor_task.done():
                monitor_task.cancel()
            return []
    
    async def run_memory_test(self):
        """Run memory usage test"""
        logger.info("=" * 60)
        logger.info("WEBSOCKET HANDLER MEMORY TEST")
        logger.info("=" * 60)
        
        if not await self.start_handler():
            return
        
        try:
            # Get baseline memory
            logger.info("\n=== Baseline Memory Usage ===")
            baseline = self.get_memory_usage()
            if baseline:
                logger.info(f"Initial RSS: {baseline['rss']:.1f} MB")
                logger.info(f"Initial VMS: {baseline['vms']:.1f} MB")
                logger.info(f"Memory %: {baseline['percent']:.1f}%")
            
            await asyncio.sleep(2)
            
            # Test 1: Simple command
            logger.info("\n=== Test 1: Simple Command ===")
            samples1 = await self.execute_claude_command(
                'claude -p "What is 2+2?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'
            )
            
            if samples1:
                max_rss = max(s['rss'] for s in samples1)
                logger.info(f"Peak RSS during command: {max_rss:.1f} MB")
                logger.info(f"RSS increase: {max_rss - baseline['rss']:.1f} MB")
            
            # Check if process is still alive
            if self.ws_process.poll() is not None:
                stdout, stderr = self.ws_process.communicate()
                logger.error("Handler died after first command!")
                logger.error(f"stdout: {stdout[-1000:]}")  # Last 1000 chars
                logger.error(f"stderr: {stderr[-1000:]}")
                return
            
            await asyncio.sleep(5)
            
            # Test 2: Large output command
            logger.info("\n=== Test 2: Large Output Command ===")
            samples2 = await self.execute_claude_command(
                'claude -p "Write a 1000 word essay about space exploration" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'
            )
            
            if samples2:
                max_rss = max(s['rss'] for s in samples2)
                logger.info(f"Peak RSS during command: {max_rss:.1f} MB")
                logger.info(f"RSS increase from baseline: {max_rss - baseline['rss']:.1f} MB")
            
            # Check if process is still alive
            if self.ws_process.poll() is not None:
                stdout, stderr = self.ws_process.communicate()
                logger.error("Handler died after second command!")
                logger.error(f"stdout: {stdout[-1000:]}")
                logger.error(f"stderr: {stderr[-1000:]}")
                return
            
            await asyncio.sleep(5)
            
            # Test 3: Multiple quick commands
            logger.info("\n=== Test 3: Multiple Quick Commands ===")
            for i in range(5):
                logger.info(f"Command {i+1}/5...")
                await self.execute_claude_command(
                    f'echo "Test {i+1}"',
                    monitor=False
                )
                
                mem = self.get_memory_usage()
                if mem:
                    logger.info(f"RSS after command {i+1}: {mem['rss']:.1f} MB")
                
                if self.ws_process.poll() is not None:
                    logger.error(f"Handler died after command {i+1}")
                    break
                
                await asyncio.sleep(1)
            
            # Final memory check
            logger.info("\n=== Final Memory Status ===")
            final = self.get_memory_usage()
            if final and baseline:
                logger.info(f"Final RSS: {final['rss']:.1f} MB")
                logger.info(f"Total RSS increase: {final['rss'] - baseline['rss']:.1f} MB")
                logger.info(f"Memory %: {final['percent']:.1f}%")
            
            # Check system memory
            sys_mem = psutil.virtual_memory()
            logger.info(f"\nSystem Memory:")
            logger.info(f"Total: {sys_mem.total / 1024 / 1024 / 1024:.1f} GB")
            logger.info(f"Available: {sys_mem.available / 1024 / 1024 / 1024:.1f} GB")
            logger.info(f"Used %: {sys_mem.percent:.1f}%")
            
        finally:
            # Stop handler
            if self.ws_process:
                logger.info("\nStopping WebSocket handler...")
                self.ws_process.terminate()
                self.ws_process.wait(timeout=5)

if __name__ == "__main__":
    test = MemoryMonitorTest()
    asyncio.run(test.run_memory_test())