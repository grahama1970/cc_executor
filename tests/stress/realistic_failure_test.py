#!/usr/bin/env python3
"""
Realistic test to reproduce the exact failure pattern from comprehensive tests
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import websockets
import uuid

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'src'))

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

class RealisticTest:
    def __init__(self):
        self.ws_process = None
        self.ws_port = 8004
        self.ws_url = f"ws://localhost:{self.ws_port}/ws"
    
    async def start_handler(self):
        """Start handler exactly like comprehensive test"""
        # Kill any existing
        os.system('pkill -9 -f websocket_handler')
        os.system(f'lsof -ti:{self.ws_port} | xargs -r kill -9 2>/dev/null')
        await asyncio.sleep(2)
        
        # Setup environment
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.join(project_root, 'src')
        if 'ANTHROPIC_API_KEY' in env:
            del env['ANTHROPIC_API_KEY']
        
        handler_path = os.path.join(project_root, 'src/cc_executor/core/websocket_handler.py')
        self.ws_process = subprocess.Popen(
            [sys.executable, "-m", "cc_executor.core.websocket_handler"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            cwd=project_root,  # Run from project root
            preexec_fn=os.setsid  # Same as comprehensive test
        )
        
        # Wait for startup
        start_time = time.time()
        while time.time() - start_time < 10:
            if self.ws_process.poll() is not None:
                output, _ = self.ws_process.communicate()
                logger.error(f"Handler died: {output}")
                return False
            
            try:
                async with websockets.connect(self.ws_url, ping_timeout=None) as ws:
                    await ws.close()
                logger.success("Handler started")
                return True
            except:
                await asyncio.sleep(0.5)
        
        return False
    
    async def execute_command(self, command, timeout=120):
        """Execute exactly like comprehensive test"""
        try:
            async with websockets.connect(self.ws_url, ping_timeout=None) as websocket:
                request = {
                    "jsonrpc": "2.0",
                    "method": "execute",
                    "params": {"command": command},
                    "id": str(uuid.uuid4())
                }
                
                await websocket.send(json.dumps(request))
                logger.debug(f"Sent: {command[:50]}...")
                
                output_lines = []
                last_activity = time.time()
                start_time = time.time()
                
                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        data = json.loads(response)
                        last_activity = time.time()
                        
                        if data.get("method") == "process.output":
                            output = data.get("params", {}).get("data", "")
                            if output:
                                output_lines.append(output)
                                
                        elif data.get("method") == "process.completed":
                            exit_code = data.get("params", {}).get("exit_code", -1)
                            logger.info(f"Command completed with exit code: {exit_code}")
                            return True, exit_code, output_lines
                    
                    except asyncio.TimeoutError:
                        elapsed = time.time() - start_time
                        inactive = time.time() - last_activity
                        
                        if elapsed > timeout:
                            logger.warning(f"Timeout after {elapsed:.1f}s")
                            return False, None, output_lines
                        
                        if inactive > 30:
                            logger.warning(f"No activity for {inactive:.1f}s - stalled")
                            return False, None, output_lines
                        
                        continue
                
        except Exception as e:
            logger.error(f"Execute failed: {type(e).__name__}: {e}")
            return False, None, []
    
    async def run_test_sequence(self):
        """Run the exact sequence that fails"""
        logger.info("=" * 60)
        logger.info("REALISTIC FAILURE REPRODUCTION TEST")
        logger.info("=" * 60)
        
        if not await self.start_handler():
            return
        
        # Test 1: Simple prompt (always works)
        logger.info("\n=== Test 1: Simple prompt ===")
        success, exit_code, output = await self.execute_command(
            'claude -p "What is 2+2?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
            timeout=30
        )
        logger.info(f"Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
        
        # Only 1 second delay like comprehensive test
        await asyncio.sleep(1)
        
        # Test 2: Large output (this is where it fails)
        logger.info("\n=== Test 2: Large output request ===")
        success, exit_code, output = await self.execute_command(
            'claude -p "Write a 5000 word essay about artificial intelligence" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
            timeout=300
        )
        
        if success:
            word_count = len(" ".join(output).split())
            logger.info(f"Result: ✅ SUCCESS - Generated {word_count} words")
        else:
            logger.info(f"Result: ❌ FAILED - Only got {len(output)} output lines")
        
        # Check what actually happened
        if output:
            logger.info("\nActual output received:")
            for i, line in enumerate(output):
                logger.info(f"  Line {i+1}: {line[:200]}...")
                
            # Parse the Claude response
            if len(output) > 1:
                try:
                    assistant_msg = json.loads(output[1])
                    if assistant_msg.get("type") == "assistant":
                        content = assistant_msg.get("message", {}).get("content", [])
                        if content and isinstance(content, list):
                            text = content[0].get("text", "")
                            logger.info(f"\nClaude's actual response: '{text}'")
                            logger.info(f"Response length: {len(text)} characters")
                except:
                    pass
        
        await asyncio.sleep(1)
        
        # Test 3: Try another command (expect failure)
        logger.info("\n=== Test 3: Third command (expect failure) ===")
        success, exit_code, output = await self.execute_command(
            'claude -p "What is 5+5?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
            timeout=30
        )
        logger.info(f"Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
        
        # Analysis
        logger.info("\n=== ANALYSIS ===")
        if self.ws_process.poll() is None:
            logger.info("Handler process is still running")
        else:
            logger.info("Handler process has died")
            
        logger.info("\nThe issue appears to be:")
        logger.info("1. Claude starts generating a large response")
        logger.info("2. But stops early (possibly hitting a limit)")
        logger.info("3. The WebSocket handler gets stuck waiting for more output")
        logger.info("4. Subsequent connections timeout")

if __name__ == "__main__":
    test = RealisticTest()
    asyncio.run(test.run_test_sequence())