#!/usr/bin/env python3
"""
Diagnostic test to understand WebSocket handler failure pattern
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import websockets
import uuid
from pathlib import Path
from datetime import datetime

# Add src to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'src'))

from loguru import logger

# Configure detailed logging
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>", level="DEBUG")

class DiagnosticTest:
    def __init__(self):
        self.ws_process = None
        self.ws_port = 8004
        self.ws_url = f"ws://localhost:{self.ws_port}/ws"
        
    async def start_handler(self):
        """Start WebSocket handler with detailed logging"""
        logger.info("Starting WebSocket handler...")
        
        # Kill any existing
        os.system('pkill -9 -f websocket_handler')
        os.system(f'lsof -ti:{self.ws_port} | xargs -r kill -9 2>/dev/null')
        await asyncio.sleep(2)
        
        # Setup environment
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.join(project_root, 'src')
        
        # CRITICAL: UNSET ANTHROPIC_API_KEY
        if 'ANTHROPIC_API_KEY' in env:
            del env['ANTHROPIC_API_KEY']
        
        # Start handler with output capture
        handler_path = os.path.join(project_root, 'src/cc_executor/core/websocket_handler.py')
        self.ws_process = subprocess.Popen(
            [sys.executable, handler_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            bufsize=1  # Line buffered
        )
        
        # Start output monitoring
        asyncio.create_task(self._monitor_handler_output())
        
        # Wait for startup
        await asyncio.sleep(3)
        
        # Test connection
        try:
            async with websockets.connect(self.ws_url, ping_timeout=5) as ws:
                await ws.close()
            logger.success(f"Handler started with PID: {self.ws_process.pid}")
            return True
        except Exception as e:
            logger.error(f"Failed to start handler: {e}")
            return False
    
    async def _monitor_handler_output(self):
        """Monitor handler stdout/stderr"""
        while self.ws_process and self.ws_process.poll() is None:
            try:
                # Check for output
                line = self.ws_process.stdout.readline()
                if line:
                    logger.debug(f"[HANDLER] {line.strip()}")
                    
                # Check stderr
                err_line = self.ws_process.stderr.readline() 
                if err_line:
                    logger.warning(f"[HANDLER ERR] {err_line.strip()}")
                    
                await asyncio.sleep(0.1)
            except:
                break
    
    async def test_connection_lifecycle(self):
        """Test what happens to connections during Claude execution"""
        
        logger.info("\n=== Testing Connection Lifecycle ===")
        
        # Test 1: Check active connections before any commands
        logger.info("\n1. Initial state - no commands run")
        await self._check_handler_state("initial")
        
        # Test 2: Simple echo command
        logger.info("\n2. After simple echo command")
        await self._execute_command('echo "test"', "echo_test")
        await asyncio.sleep(2)
        await self._check_handler_state("after_echo")
        
        # Test 3: First Claude command
        logger.info("\n3. After first Claude command")
        await self._execute_command(
            'claude -p "What is 2+2?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
            "first_claude"
        )
        await asyncio.sleep(2)
        await self._check_handler_state("after_first_claude")
        
        # Test 4: Second Claude command (expect failure)
        logger.info("\n4. Attempting second Claude command")
        await self._execute_command(
            'claude -p "What is 5+5?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
            "second_claude"
        )
        await asyncio.sleep(2)
        await self._check_handler_state("after_second_claude")
        
        # Test 5: Can we still do echo?
        logger.info("\n5. Testing echo after Claude failures")
        await self._execute_command('echo "still alive?"', "echo_after_claude")
        await self._check_handler_state("final_state")
    
    async def _execute_command(self, command, test_name):
        """Execute a command and log all details"""
        logger.info(f"Executing: {command[:50]}...")
        
        try:
            # Try to connect
            logger.debug("Attempting WebSocket connection...")
            async with websockets.connect(self.ws_url, ping_timeout=10, close_timeout=5) as ws:
                logger.debug(f"Connected to WebSocket")
                
                # Send command
                request = {
                    "jsonrpc": "2.0",
                    "method": "execute",
                    "params": {"command": command},
                    "id": str(uuid.uuid4())
                }
                
                await ws.send(json.dumps(request))
                logger.debug(f"Sent request with ID: {request['id']}")
                
                # Collect all responses
                responses = []
                start_time = time.time()
                timeout = 30
                
                while time.time() - start_time < timeout:
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        data = json.loads(response)
                        responses.append(data)
                        
                        method = data.get("method", "")
                        if method:
                            logger.debug(f"Received: {method}")
                        
                        if method == "process.completed":
                            exit_code = data.get("params", {}).get("exit_code")
                            logger.info(f"Command completed with exit code: {exit_code}")
                            break
                            
                    except asyncio.TimeoutError:
                        logger.debug("Waiting for more output...")
                        continue
                
                # Log summary
                logger.info(f"Test '{test_name}' received {len(responses)} messages")
                
        except Exception as e:
            logger.error(f"Test '{test_name}' failed: {type(e).__name__}: {e}")
    
    async def _check_handler_state(self, checkpoint):
        """Check handler process state"""
        logger.info(f"\n--- Handler State Check: {checkpoint} ---")
        
        # Check if process is alive
        if self.ws_process:
            poll_result = self.ws_process.poll()
            if poll_result is None:
                logger.info(f"✅ Handler process alive (PID: {self.ws_process.pid})")
                
                # Check open files/sockets
                try:
                    result = subprocess.run(
                        f"lsof -p {self.ws_process.pid} | grep -E 'TCP|PIPE|REG' | wc -l",
                        shell=True,
                        capture_output=True,
                        text=True
                    )
                    open_files = result.stdout.strip()
                    logger.info(f"Open files/sockets: {open_files}")
                except:
                    pass
                    
            else:
                logger.error(f"❌ Handler process DEAD (exit code: {poll_result})")
                # Get any remaining output
                stdout, stderr = self.ws_process.communicate()
                if stdout:
                    logger.error(f"Final stdout: {stdout[-500:]}")
                if stderr:
                    logger.error(f"Final stderr: {stderr[-500:]}")
        
        # Test WebSocket connectivity
        try:
            async with websockets.connect(self.ws_url, ping_timeout=2) as ws:
                await ws.close()
            logger.info("✅ WebSocket accepting connections")
        except Exception as e:
            logger.error(f"❌ WebSocket NOT accepting connections: {e}")
    
    async def test_token_sizes(self):
        """Test different response sizes to see if token count matters"""
        logger.info("\n=== Testing Different Output Sizes ===")
        
        test_cases = [
            ("Tiny (1 token)", 'claude -p "Reply with just the number 4" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
            ("Small (10 tokens)", 'claude -p "List 3 colors, one word each" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
            ("Medium (100 tokens)", 'claude -p "Write a 50 word paragraph about dogs" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
            ("Large (500 tokens)", 'claude -p "Write a 200 word essay about space" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
        ]
        
        for name, command in test_cases:
            logger.info(f"\n--- Testing {name} ---")
            await self._execute_command(command, name)
            await asyncio.sleep(3)
            
            # Check if handler is still alive
            if self.ws_process.poll() is not None:
                logger.error(f"Handler died after {name} test!")
                break
    
    async def run_diagnostics(self):
        """Run all diagnostic tests"""
        logger.info("=" * 60)
        logger.info("WEBSOCKET HANDLER DIAGNOSTIC TEST")
        logger.info("=" * 60)
        
        if not await self.start_handler():
            return
        
        try:
            # Test 1: Connection lifecycle
            await self.test_connection_lifecycle()
            
            # Restart for clean test
            logger.info("\n=== Restarting handler for token size tests ===")
            if self.ws_process:
                self.ws_process.terminate()
                await asyncio.sleep(2)
            
            if await self.start_handler():
                # Test 2: Token sizes
                await self.test_token_sizes()
            
        finally:
            if self.ws_process:
                logger.info("\nTerminating handler...")
                self.ws_process.terminate()

if __name__ == "__main__":
    test = DiagnosticTest()
    asyncio.run(test.run_diagnostics())