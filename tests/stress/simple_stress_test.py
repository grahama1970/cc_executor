#!/usr/bin/env python3
"""
Simple stress test to verify Claude CLI + WebSocket integration
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

# Configure logging
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")

class SimpleStressTest:
    def __init__(self):
        self.ws_process = None
        self.ws_port = 8004
        self.ws_url = f"ws://localhost:{self.ws_port}/ws"
        self.results = []
    
    async def start_handler(self):
        """Start WebSocket handler"""
        logger.info("Starting WebSocket handler...")
        
        # Kill any existing WebSocket processes
        logger.info("Killing any existing WebSocket processes...")
        os.system('pkill -9 -f websocket_handler')
        os.system(f'lsof -ti:{self.ws_port} | xargs -r kill -9 2>/dev/null')
        await asyncio.sleep(2)
        
        # Setup environment
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.join(project_root, 'src')
        
        # CRITICAL: UNSET ANTHROPIC_API_KEY
        if 'ANTHROPIC_API_KEY' in env:
            del env['ANTHROPIC_API_KEY']
            logger.warning("UNSET ANTHROPIC_API_KEY")
        
        # Start handler
        handler_path = os.path.join(project_root, 'src/cc_executor/core/websocket_handler.py')
        self.ws_process = subprocess.Popen(
            [sys.executable, handler_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            preexec_fn=os.setsid
        )
        
        # Wait for startup
        await asyncio.sleep(2)
        
        # Verify it's running
        try:
            async with websockets.connect(self.ws_url, ping_timeout=5) as ws:
                await ws.close()
            logger.success("WebSocket handler started")
            return True
        except:
            logger.error("Failed to start WebSocket handler")
            return False
    
    async def execute_test(self, name, command, expected_in_output=None):
        """Execute a single test"""
        logger.info(f"\n=== {name} ===")
        start_time = time.time()
        
        try:
            async with websockets.connect(self.ws_url, ping_timeout=30) as ws:
                # Send command
                request = {
                    "jsonrpc": "2.0",
                    "method": "execute",
                    "params": {"command": command},
                    "id": str(uuid.uuid4())
                }
                
                await ws.send(json.dumps(request))
                logger.debug(f"Sent: {command[:100]}...")
                
                # Collect output
                output = []
                exit_code = None
                
                while True:
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        data = json.loads(response)
                        
                        if data.get("method") == "process.output":
                            text = data.get("params", {}).get("data", "")
                            if text:
                                output.append(text)
                                
                        elif data.get("method") == "process.completed":
                            exit_code = data.get("params", {}).get("exit_code")
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                duration = time.time() - start_time
                full_output = "".join(output)
                
                # Check success
                success = exit_code == 0
                if expected_in_output and success:
                    success = expected_in_output.lower() in full_output.lower()
                
                result = {
                    "name": name,
                    "success": success,
                    "duration": duration,
                    "exit_code": exit_code,
                    "output_size": len(full_output)
                }
                
                self.results.append(result)
                
                status = "✅ PASSED" if success else "❌ FAILED"
                logger.info(f"{status} - {name} ({duration:.1f}s, {len(full_output)} chars)")
                
                if not success:
                    logger.error(f"Exit code: {exit_code}")
                    if len(full_output) < 1000:
                        logger.error(f"Output: {full_output}")
                
        except Exception as e:
            logger.error(f"Test failed with error: {e}")
            self.results.append({
                "name": name,
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e)
            })
    
    async def run_tests(self):
        """Run all tests"""
        logger.info("=" * 60)
        logger.info("SIMPLE CLAUDE CLI STRESS TEST")
        logger.info("=" * 60)
        
        if not await self.start_handler():
            return
        
        try:
            # Test 1: Simple math
            await self.execute_test(
                "Simple Math (2+2)",
                'claude -p "What is 2+2?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
                expected_in_output="4"
            )
            
            await asyncio.sleep(1)
            
            # Test 2: Short response
            await self.execute_test(
                "Capital of France",
                'claude -p "What is the capital of France? Answer in one word." --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
                expected_in_output="Paris"
            )
            
            await asyncio.sleep(1)
            
            # Test 3: Programming question
            await self.execute_test(
                "Hello World Python",
                'claude -p "Write a Python one-liner to print Hello World" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
                expected_in_output="print"
            )
            
            await asyncio.sleep(1)
            
            # Test 4: List generation
            await self.execute_test(
                "List 3 Colors",
                'claude -p "List exactly 3 colors, one per line" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
                expected_in_output=None  # Just check exit code
            )
            
            await asyncio.sleep(1)
            
            # Test 5: Echo command (non-Claude)
            await self.execute_test(
                "Echo Test",
                'echo "WebSocket handler is working"',
                expected_in_output="WebSocket handler is working"
            )
            
            # Summary
            logger.info("\n" + "=" * 60)
            logger.info("SUMMARY")
            logger.info("=" * 60)
            
            total = len(self.results)
            passed = sum(1 for r in self.results if r["success"])
            
            logger.info(f"Total Tests: {total}")
            logger.info(f"Passed: {passed} ({passed/total*100:.1f}%)")
            logger.info(f"Failed: {total - passed}")
            
            # Save results
            output_dir = Path(project_root) / "test_results/stress/logs"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            report_file = output_dir / f"simple_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "total": total,
                    "passed": passed,
                    "failed": total - passed,
                    "results": self.results
                }, f, indent=2)
            
            logger.info(f"\nReport saved to: {report_file}")
            
            if passed == total:
                logger.success("\n🎉 ALL TESTS PASSED! 🎉")
            else:
                logger.warning(f"\n⚠️ {total - passed} tests failed")
            
        finally:
            # Stop handler
            if self.ws_process:
                logger.info("\nStopping WebSocket handler...")
                os.killpg(os.getpgid(self.ws_process.pid), 9)

if __name__ == "__main__":
    test = SimpleStressTest()
    asyncio.run(test.run_tests())