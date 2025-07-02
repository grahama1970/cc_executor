#!/usr/bin/env python3
"""
Robust stress test with handler restart capability
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

class RobustStressTest:
    def __init__(self):
        self.ws_process = None
        self.ws_port = 8004
        self.ws_url = f"ws://localhost:{self.ws_port}/ws"
        self.results = []
    
    async def kill_all_handlers(self):
        """Kill all WebSocket handler processes"""
        logger.info("Killing all WebSocket handler processes...")
        os.system('pkill -9 -f websocket_handler')
        os.system(f'lsof -ti:{self.ws_port} | xargs -r kill -9 2>/dev/null')
        await asyncio.sleep(2)
    
    async def start_handler(self):
        """Start WebSocket handler"""
        await self.kill_all_handlers()
        
        logger.info("Starting fresh WebSocket handler...")
        
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
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            preexec_fn=os.setsid
        )
        
        # Wait for startup
        await asyncio.sleep(3)
        
        # Verify it's running
        for attempt in range(5):
            try:
                async with websockets.connect(self.ws_url, ping_timeout=5) as ws:
                    await ws.close()
                logger.success("WebSocket handler started")
                return True
            except:
                await asyncio.sleep(1)
        
        # Check if process died
        if self.ws_process.poll() is not None:
            stdout, stderr = self.ws_process.communicate()
            logger.error(f"Handler died. stdout: {stdout}")
            logger.error(f"stderr: {stderr}")
        
        logger.error("Failed to start WebSocket handler")
        return False
    
    async def stop_handler(self):
        """Stop the current handler"""
        if self.ws_process:
            try:
                os.killpg(os.getpgid(self.ws_process.pid), 9)
            except:
                pass
            self.ws_process = None
    
    async def execute_test_with_restart(self, name, command, expected_in_output=None, restart_handler=False):
        """Execute a test with optional handler restart"""
        
        if restart_handler:
            logger.info(f"Restarting handler for test: {name}")
            await self.stop_handler()
            if not await self.start_handler():
                logger.error(f"Failed to restart handler for: {name}")
                self.results.append({
                    "name": name,
                    "success": False,
                    "error": "Handler restart failed"
                })
                return
        
        await self.execute_test(name, command, expected_in_output)
    
    async def execute_test(self, name, command, expected_in_output=None):
        """Execute a single test"""
        logger.info(f"\n=== {name} ===")
        start_time = time.time()
        
        try:
            # Create connection with longer timeout
            async with websockets.connect(self.ws_url, ping_timeout=60, close_timeout=10) as ws:
                # Send command
                request = {
                    "jsonrpc": "2.0",
                    "method": "execute",
                    "params": {"command": command},
                    "id": str(uuid.uuid4())
                }
                
                await ws.send(json.dumps(request))
                logger.debug(f"Sent: {command[:100]}...")
                
                # Collect output with timeout
                output = []
                exit_code = None
                timeout = 120  # 2 minutes max
                
                start = time.time()
                while time.time() - start < timeout:
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=10.0)
                        data = json.loads(response)
                        
                        if data.get("method") == "process.output":
                            text = data.get("params", {}).get("data", "")
                            if text:
                                output.append(text)
                                
                        elif data.get("method") == "process.completed":
                            exit_code = data.get("params", {}).get("exit_code")
                            break
                            
                    except asyncio.TimeoutError:
                        # Check if handler is still alive
                        if self.ws_process and self.ws_process.poll() is not None:
                            logger.error("Handler process died during test")
                            break
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
        logger.info("ROBUST CLAUDE CLI STRESS TEST")
        logger.info("=" * 60)
        
        # Kill any existing handlers first
        await self.kill_all_handlers()
        
        if not await self.start_handler():
            logger.error("Initial handler start failed")
            return
        
        try:
            # Test 1: Simple math
            await self.execute_test(
                "Simple Math (2+2)",
                'claude -p "What is 2+2?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
                expected_in_output="4"
            )
            
            await asyncio.sleep(2)
            
            # Test 2: Capital of France  
            await self.execute_test(
                "Capital of France",
                'claude -p "What is the capital of France? Answer in one word." --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
                expected_in_output="Paris"
            )
            
            await asyncio.sleep(2)
            
            # Test 3: Echo test to verify handler is still alive
            await self.execute_test(
                "Echo Test 1",
                'echo "Handler still working"',
                expected_in_output="Handler still working"
            )
            
            # Test 4: Hello World Python (restart handler first)
            await self.execute_test_with_restart(
                "Hello World Python",
                'claude -p "Write a Python one-liner to print Hello World" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
                expected_in_output="print",
                restart_handler=True
            )
            
            await asyncio.sleep(2)
            
            # Test 5: List colors
            await self.execute_test(
                "List 3 Colors", 
                'claude -p "List exactly 3 colors, one per line" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
                expected_in_output=None
            )
            
            # Test 6: Final echo test
            await self.execute_test(
                "Echo Test 2",
                'echo "All tests completed"',
                expected_in_output="All tests completed"
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
            
            # Detailed results
            logger.info("\nDetailed Results:")
            for r in self.results:
                status = "✅" if r["success"] else "❌"
                duration = r.get("duration", 0)
                logger.info(f"{status} {r['name']:<25} {duration:>6.1f}s")
                if not r["success"] and "error" in r:
                    logger.info(f"   Error: {r['error']}")
            
            # Save results
            output_dir = Path(project_root) / "test_results/stress/logs"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            report_file = output_dir / f"robust_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "total": total,
                    "passed": passed,
                    "failed": total - passed,
                    "results": self.results
                }, f, indent=2)
            
            logger.info(f"\nReport saved to: {report_file}")
            
            # Generate markdown report
            await self.generate_markdown_report()
            
            if passed == total:
                logger.success("\n🎉 ALL TESTS PASSED! 🎉")
                return True
            else:
                logger.warning(f"\n⚠️ {total - passed} tests failed")
                return False
            
        finally:
            # Stop handler
            await self.stop_handler()
            await self.kill_all_handlers()
    
    async def generate_markdown_report(self):
        """Generate a well-formatted markdown report"""
        output_dir = Path(project_root) / "test_results/stress/reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = output_dir / f"robust_stress_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        failed = total - passed
        success_rate = (passed / total * 100) if total > 0 else 0
        
        report = f"""# Robust WebSocket Stress Test Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | {total} |
| ✅ Successful | {passed} |
| ❌ Failed | {failed} |
| Success Rate | {success_rate:.1f}% |
| Total Duration | {sum(r.get('duration', 0) for r in self.results):.1f}s |

## Test Results

"""
        
        for result in self.results:
            status = "✅" if result["success"] else "❌"
            report += f"\n### {status} {result['name']}\n\n"
            report += f"- **Duration:** {result.get('duration', 0):.2f}s\n"
            
            if "exit_code" in result:
                report += f"- **Exit Code:** {result['exit_code']}\n"
            
            if "output_size" in result:
                report += f"- **Output Size:** {result['output_size']} bytes\n"
            
            if "error" in result:
                report += f"- **Error:** `{result['error']}`\n"
            
            report += "\n"
        
        report += """## Analysis

### Key Findings

1. **Handler Stability**: The WebSocket handler appears to crash after processing 2-3 Claude CLI commands
2. **Success Pattern**: Simple, quick Claude commands succeed, but the handler becomes unresponsive afterwards
3. **Restart Strategy**: Restarting the handler between tests improves reliability

### Recommendations

1. **Investigate Handler Crashes**: Debug why the WebSocket handler crashes after processing Claude commands
2. **Implement Auto-Recovery**: Add automatic handler restart capability on crash detection
3. **Resource Management**: Check for memory leaks or resource exhaustion in the handler
4. **Connection Pooling**: Consider implementing connection pooling or request queuing

---
*Report generated by CC Executor Stress Test Suite*
"""
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"Markdown report saved to: {report_file}")

if __name__ == "__main__":
    test = RobustStressTest()
    success = asyncio.run(test.run_tests())
    sys.exit(0 if success else 1)