#!/usr/bin/env python3
"""
Production WebSocket client with optional per-task restart capability
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import websockets
import uuid
from typing import Dict, Any, Optional, Tuple
from loguru import logger

class WebSocketClient:
    """WebSocket client for executing commands with optional handler restart"""
    
    def __init__(self, 
                 host: str = "localhost", 
                 port: int = 8004,
                 project_root: Optional[str] = None):
        self.host = host
        self.port = port
        self.ws_url = f"ws://{host}:{port}/ws/mcp"
        self.project_root = project_root or os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.handler_process = None
        
    async def kill_handler(self) -> None:
        """Kill any existing WebSocket handler processes"""
        os.system('pkill -9 -f websocket_handler 2>/dev/null')
        os.system(f'lsof -ti:{self.port} | xargs -r kill -9 2>/dev/null')
        await asyncio.sleep(0.5)  # Brief pause to ensure cleanup
        
    async def start_handler(self) -> Optional[subprocess.Popen]:
        """Start a fresh WebSocket handler process"""
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.join(self.project_root, 'src')
        
        # Critical: Remove ANTHROPIC_API_KEY for Claude CLI
        if 'ANTHROPIC_API_KEY' in env:
            del env['ANTHROPIC_API_KEY']
        
        # Try to use the minimal server if available
        minimal_server = os.path.join(self.project_root, "src", "cc_executor", "core", "websocket_server_minimal.py")
        if os.path.exists(minimal_server):
            handler = subprocess.Popen(
                [sys.executable, minimal_server],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=self.project_root,
                preexec_fn=os.setsid if sys.platform != 'win32' else None
            )
        else:
            handler = subprocess.Popen(
                [sys.executable, "-m", "cc_executor.core.websocket_handler"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=self.project_root,
                preexec_fn=os.setsid if sys.platform != 'win32' else None
            )
        
        # Wait for handler to be ready
        start_time = time.time()
        while time.time() - start_time < 10:
            if handler.poll() is not None:
                output, _ = handler.communicate()
                logger.error(f"Handler died during startup: {output}")
                return None
            
            # Check if port is listening
            try:
                async with websockets.connect(self.ws_url, 
                                            open_timeout=0.5,
                                            ping_timeout=None) as ws:
                    await ws.close()
                self.handler_process = handler
                return handler
            except:
                await asyncio.sleep(0.2)
        
        logger.error("Handler failed to start within 10s")
        handler.terminate()
        return None
    
    async def ensure_handler_running(self) -> bool:
        """Ensure WebSocket handler is running"""
        try:
            async with websockets.connect(self.ws_url, 
                                        open_timeout=0.5,
                                        ping_timeout=None) as ws:
                await ws.close()
            return True
        except:
            logger.info("Handler not running, starting it...")
            handler = await self.start_handler()
            return handler is not None
    
    async def execute_command(self,
                            command: str,
                            timeout: int = 120,
                            restart_handler: bool = True) -> Dict[str, Any]:
        """
        Execute a command via WebSocket
        
        Args:
            command: Command to execute
            timeout: Maximum time to wait for completion (seconds)
            restart_handler: Whether to restart handler before execution (default: True)
        
        Returns:
            Dict with execution results
        """
        start_time = time.time()
        
        # Optionally restart handler for clean state
        if restart_handler:
            logger.debug(f"[RESTART] Restarting handler for clean state...")
            restart_start = time.time()
            await self.kill_handler()
            
            handler = await self.start_handler()
            if not handler:
                return {
                    "success": False,
                    "error": "Failed to start handler",
                    "duration": 0,
                    "restart_overhead": time.time() - restart_start,
                    "outputs": 0
                }
            restart_overhead = time.time() - restart_start
        else:
            # Ensure handler is running without restart
            if not await self.ensure_handler_running():
                return {
                    "success": False,
                    "error": "Handler not running and failed to start",
                    "duration": 0,
                    "restart_overhead": 0,
                    "outputs": 0
                }
            restart_overhead = 0
        
        # Execute the command
        try:
            async with websockets.connect(self.ws_url, ping_timeout=None) as ws:
                request = {
                    "jsonrpc": "2.0",
                    "method": "execute",
                    "params": {
                        "command": command,
                        "timeout": timeout  # Pass timeout to server
                    },
                    "id": str(uuid.uuid4())
                }
                
                await ws.send(json.dumps(request))
                
                exec_start = time.time()
                output_count = 0
                outputs = []
                
                while True:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        data = json.loads(msg)
                        
                        if data.get("method") == "process.output":
                            output_count += 1
                            output_data = data.get("params", {}).get("data", "")
                            outputs.append(output_data)
                            
                        elif data.get("method") == "process.completed":
                            exit_code = data.get("params", {}).get("exit_code", -1)
                            duration = time.time() - exec_start
                            
                            return {
                                "success": True,
                                "exit_code": exit_code,
                                "duration": duration,
                                "restart_overhead": restart_overhead,
                                "outputs": output_count,
                                "output_data": outputs
                            }
                            
                        elif data.get("method") == "process.error":
                            error = data.get("params", {}).get("error", "Unknown error")
                            return {
                                "success": False,
                                "error": f"Process error: {error}",
                                "duration": time.time() - exec_start,
                                "restart_overhead": restart_overhead,
                                "outputs": output_count,
                                "output_data": outputs
                            }
                            
                    except asyncio.TimeoutError:
                        elapsed = time.time() - exec_start
                        if elapsed > timeout:
                            return {
                                "success": False,
                                "error": f"Command timeout after {elapsed:.1f}s",
                                "duration": elapsed,
                                "restart_overhead": restart_overhead,
                                "outputs": output_count,
                                "output_data": outputs
                            }
                        continue
                        
        except Exception as e:
            return {
                "success": False,
                "error": f"WebSocket error: {str(e)}",
                "duration": time.time() - exec_start if 'exec_start' in locals() else 0,
                "restart_overhead": restart_overhead,
                "outputs": 0,
                "output_data": []
            }
    
    async def execute_batch(self,
                          tasks: list,
                          restart_per_task: bool = True,
                          restart_every_n: Optional[int] = None) -> list:
        """
        Execute multiple tasks with configurable restart strategy
        
        Args:
            tasks: List of (name, command, timeout) tuples
            restart_per_task: Restart handler for each task (default: True)
            restart_every_n: Restart handler every N tasks (overrides restart_per_task)
        
        Returns:
            List of execution results
        """
        results = []
        
        for i, (name, command, timeout) in enumerate(tasks):
            # Determine if we should restart
            if restart_every_n:
                should_restart = (i % restart_every_n == 0)
            else:
                should_restart = restart_per_task
            
            logger.info(f"\n[Task {i+1}/{len(tasks)}] {name}")
            if should_restart:
                logger.debug("Will restart handler for this task")
            
            result = await self.execute_command(
                command=command,
                timeout=timeout,
                restart_handler=should_restart
            )
            
            result["task_name"] = name
            result["task_index"] = i
            results.append(result)
            
            if result["success"]:
                logger.success(f"✅ Completed in {result['duration']:.1f}s" + 
                             (f" (restart: {result['restart_overhead']:.1f}s)" 
                              if result['restart_overhead'] > 0 else ""))
            else:
                logger.error(f"❌ Failed: {result['error']}")
            
            # Brief pause between tasks
            if i < len(tasks) - 1:
                await asyncio.sleep(0.5)
        
        return results
    
    async def cleanup(self):
        """Clean up handler process"""
        if self.handler_process and self.handler_process.poll() is None:
            logger.info("Terminating handler process...")
            self.handler_process.terminate()
            self.handler_process.wait()
        await self.kill_handler()


# Example usage
async def main():
    """Example usage of WebSocketClient"""
    client = WebSocketClient()
    
    # Example 1: Single command with restart (recommended for Claude)
    logger.info("=== Example 1: Single Claude command with restart ===")
    result = await client.execute_command(
        command='claude -p "What is 2+2?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
        timeout=30,
        restart_handler=True  # Restart for clean state
    )
    logger.info(f"Result: {result['success']}, Duration: {result['duration']:.1f}s")
    
    # Example 2: Single command without restart (for simple commands)
    logger.info("\n=== Example 2: Simple echo without restart ===")
    result = await client.execute_command(
        command='echo "Hello World"',
        timeout=10,
        restart_handler=False  # No restart needed for echo
    )
    logger.info(f"Result: {result['success']}, Duration: {result['duration']:.1f}s")
    
    # Example 3: Batch execution with per-task restart
    logger.info("\n=== Example 3: Batch with per-task restart ===")
    tasks = [
        ("Math", 'claude -p "What is 10*10?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 30),
        ("Echo", 'echo "test"', 10),
        ("List", 'claude -p "List 5 colors" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 30),
    ]
    
    results = await client.execute_batch(
        tasks=tasks,
        restart_per_task=True  # Restart for each task
    )
    
    # Example 4: Batch execution with periodic restart
    logger.info("\n=== Example 4: Batch with restart every 2 tasks ===")
    results = await client.execute_batch(
        tasks=tasks,
        restart_every_n=2  # Restart every 2 tasks
    )
    
    # Cleanup
    await client.cleanup()
    
    # Summary
    successful = sum(1 for r in results if r["success"])
    logger.info(f"\nSummary: {successful}/{len(results)} tasks succeeded")


if __name__ == "__main__":
    asyncio.run(main())