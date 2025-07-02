#!/usr/bin/env python3
"""
WebSocket client that connects to an existing server (doesn't manage its own).
This is the correct client to use when the server is already running.
"""
import asyncio
import json
import time
import uuid
import websockets
from typing import Dict, List, Tuple, Optional, Any, Union
from loguru import logger

class WebSocketClient:
    """WebSocket client for existing cc_executor server"""
    
    def __init__(self, host: str = "localhost", port: int = 8004):
        self.host = host
        self.port = port
        self.ws_url = f"ws://{host}:{port}/ws/mcp"
        
    async def execute_command(
        self, 
        command: str, 
        timeout: Optional[int] = None,
        restart_handler: bool = False  # Ignored - server manages its own lifecycle
    ) -> Dict[str, Any]:
        """
        Execute a command via WebSocket connection.
        
        Args:
            command: Command to execute
            timeout: Maximum time to wait for completion (seconds)
            restart_handler: Ignored (kept for compatibility)
        
        Returns:
            Dict with execution results
        """
        start_time = time.time()
        output_data = []
        
        try:
            async with websockets.connect(self.ws_url, ping_timeout=None) as ws:
                # Send execute request with optional timeout
                params = {"command": command}
                if timeout is not None:
                    params["timeout"] = timeout  # Only pass if specified
                
                request = {
                    "jsonrpc": "2.0",
                    "method": "execute",
                    "params": params,
                    "id": str(uuid.uuid4())
                }
                
                await ws.send(json.dumps(request))
                
                # Collect responses
                exit_code = None
                error = None
                
                while True:
                    try:
                        # Use a long default timeout for WebSocket communication
                        msg = await asyncio.wait_for(ws.recv(), timeout=timeout or 600)
                        data = json.loads(msg)
                        
                        # Handle different message types
                        if "result" in data:
                            # Initial response
                            if data.get("result", {}).get("status") == "started":
                                continue
                                
                        elif "method" in data:
                            # Notification
                            if data["method"] == "process.output":
                                output = data.get("params", {}).get("data", "")
                                if output:
                                    output_data.append(output)
                                    
                            elif data["method"] == "process.completed":
                                exit_code = data.get("params", {}).get("exit_code", 0)
                                break
                                
                            elif data["method"] == "process.failed":
                                error = data.get("params", {}).get("error", "Process failed")
                                break
                                
                        elif "error" in data:
                            # Error response
                            error = data["error"].get("message", "Unknown error")
                            break
                            
                    except asyncio.TimeoutError:
                        error = f"Command timed out after {timeout or 600}s"
                        break
                    except websockets.exceptions.ConnectionClosed:
                        error = "WebSocket connection closed unexpectedly"
                        break
                        
        except websockets.exceptions.WebSocketException as e:
            error = f"WebSocket error: {e}"
        except Exception as e:
            error = f"Unexpected error: {e}"
            
        duration = time.time() - start_time
        
        return {
            "success": error is None,
            "exit_code": exit_code if error is None else -1,
            "duration": duration,
            "restart_overhead": 0,  # No restart when using existing server
            "outputs": len(output_data),
            "output_data": output_data,
            "error": error
        }
    
    async def execute_batch(
        self, 
        tasks: List[Tuple[str, str, int]], 
        restart_per_task: bool = True, 
        restart_every_n: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple tasks.
        
        Args:
            tasks: List of (name, command, timeout) tuples
            restart_per_task: Ignored (kept for compatibility)
            restart_every_n: Ignored (kept for compatibility)
        
        Returns:
            List of execution results
        """
        results = []
        
        for i, (name, command, timeout) in enumerate(tasks):
            logger.info(f"[{i+1}/{len(tasks)}] Executing: {name}")
            
            result = await self.execute_command(command, timeout)
            result["task_name"] = name
            results.append(result)
            
            if result["success"]:
                logger.info(f"✓ Completed in {result['duration']:.1f}s")
            else:
                logger.error(f"✗ Failed: {result['error']}")
                
        return results
    
    async def cleanup(self):
        """Cleanup (no-op for standalone client)"""
        pass

# Also provide MinimalWebSocketClient alias for compatibility
MinimalWebSocketClient = WebSocketClient