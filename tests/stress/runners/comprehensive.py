#!/usr/bin/env python3
"""
Comprehensive WebSocket Stress Test for cc_executor

This test script properly exercises the WebSocket handler with real Claude commands,
including all critical flags and proper JSON streaming validation.

Tests include:
- Simple prompts with proper flags
- Large output generation (5000 word essays)
- Self-reflection format prompts
- Timeout and recovery scenarios
- JSON streaming validation
- Buffer handling for large outputs
- Environment variable validation
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import signal
from pathlib import Path
from datetime import datetime
import websockets
from typing import Dict, List, Any, Optional
import uuid

# Add src to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(project_root, 'src'))

try:
    from loguru import logger
except ImportError:
    print("Please install loguru: pip install loguru")
    sys.exit(1)

# Configure logging
logger.remove()
logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>", level="INFO")

# Test output directory
TEST_OUTPUT_DIR = Path(project_root) / "test_results/stress/logs"
TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Log file for detailed debugging
logger.add(TEST_OUTPUT_DIR / f"stress_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", level="DEBUG")


class WebSocketStressTest:
    """Comprehensive stress test suite for WebSocket handler"""
    
    def __init__(self):
        self.ws_process = None
        self.ws_port = 8004
        self.ws_url = f"ws://localhost:{self.ws_port}/ws"
        self.results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "tests": []
        }
        self.test_start_time = datetime.now()
        
    async def start_websocket_handler(self) -> bool:
        """Start the WebSocket handler process"""
        logger.info("Starting WebSocket handler...")
        
        # Kill any existing WebSocket processes
        logger.info("Killing any existing WebSocket processes...")
        try:
            os.system('pkill -9 -f websocket_handler')
            os.system(f'lsof -ti:{self.ws_port} | xargs -r kill -9 2>/dev/null')
            await asyncio.sleep(2)
        except:
            pass
        
        # Set up environment
        env = os.environ.copy()
        # Critical: Use correct PYTHONPATH
        # Use the global project_root which points to cc_executor root
        global project_root
        env['PYTHONPATH'] = os.path.join(project_root, 'src')
        
        # CRITICAL: UNSET ANTHROPIC_API_KEY - Claude CLI hangs with it!
        if 'ANTHROPIC_API_KEY' in env:
            logger.warning("UNSETTING ANTHROPIC_API_KEY - Claude CLI hangs when it's set!")
            del env['ANTHROPIC_API_KEY']
        else:
            logger.info("ANTHROPIC_API_KEY not set - good for Claude CLI")
        
        # Check for .mcp.json
        mcp_config_path = os.path.join(project_root, '.mcp.json')
        if os.path.exists(mcp_config_path):
            logger.info(f"MCP config found at: {mcp_config_path}")
        else:
            logger.warning("No .mcp.json found - MCP tools won't be available")
        
        # Start the handler
        handler_path = os.path.join(project_root, 'src/cc_executor/core/websocket_handler.py')
        
        self.ws_process = subprocess.Popen(
            [sys.executable, str(handler_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Combine to avoid deadlocks
            text=True,
            env=env,
            preexec_fn=os.setsid  # Create new process group for proper cleanup
        )
        
        # Wait for server to be ready
        start_time = time.time()
        while time.time() - start_time < 10:
            if self.ws_process.poll() is not None:
                # Process died
                output, _ = self.ws_process.communicate()
                logger.error(f"WebSocket handler died: {output}")
                return False
            
            # Try to connect
            try:
                async with websockets.connect(self.ws_url, ping_timeout=None) as ws:
                    await ws.close()
                logger.success("WebSocket handler started successfully")
                return True
            except:
                await asyncio.sleep(0.5)
        
        logger.error("WebSocket handler startup timeout")
        return False
    
    def stop_websocket_handler(self):
        """Stop the WebSocket handler process"""
        if self.ws_process:
            logger.info("Stopping WebSocket handler...")
            try:
                # Kill entire process group
                os.killpg(os.getpgid(self.ws_process.pid), signal.SIGTERM)
                self.ws_process.wait(timeout=5)
            except:
                try:
                    os.killpg(os.getpgid(self.ws_process.pid), signal.SIGKILL)
                except:
                    pass
    
    async def execute_command(self, command: str, timeout: int = 120) -> Dict[str, Any]:
        """Execute a command via WebSocket and collect results"""
        result = {
            "command": command,
            "success": False,
            "exit_code": None,
            "output": [],
            "duration": 0,
            "error": None
        }
        
        start_time = time.time()
        
        try:
            async with websockets.connect(self.ws_url, ping_timeout=None) as websocket:
                # Send execute request
                request = {
                    "jsonrpc": "2.0",
                    "method": "execute",
                    "params": {"command": command},
                    "id": str(uuid.uuid4())
                }
                
                await websocket.send(json.dumps(request))
                logger.debug(f"Sent command: {command[:100]}...")
                
                # Collect responses
                output_lines = []
                last_activity = time.time()
                
                while True:
                    try:
                        # Wait for response with timeout
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        data = json.loads(response)
                        last_activity = time.time()
                        
                        # Handle different message types
                        if "error" in data:
                            result["error"] = data["error"]
                            logger.error(f"Server error: {data['error']}")
                            break
                        
                        elif data.get("method") == "process.output":
                            # Collect output
                            output = data.get("params", {}).get("data", "")
                            if output:
                                output_lines.append(output)
                                # Log large outputs
                                if len(output) > 1000:
                                    logger.info(f"Received large output: {len(output)} chars")
                        
                        elif data.get("method") == "process.completed":
                            # Process completed
                            result["exit_code"] = data.get("params", {}).get("exit_code", -1)
                            result["success"] = result["exit_code"] == 0
                            break
                        
                        elif data.get("method") == "connected":
                            # Connection confirmation
                            logger.debug("WebSocket connected")
                        
                        elif data.get("method") == "process.started":
                            # Process started
                            pid = data.get("params", {}).get("pid")
                            logger.debug(f"Process started with PID: {pid}")
                    
                    except asyncio.TimeoutError:
                        # Check for timeout or stall
                        elapsed = time.time() - start_time
                        inactive = time.time() - last_activity
                        
                        if elapsed > timeout:
                            logger.warning(f"Command timeout after {elapsed:.1f}s")
                            result["error"] = "Timeout"
                            break
                        
                        if inactive > 30:
                            logger.warning(f"No activity for {inactive:.1f}s")
                            result["error"] = "Stalled"
                            break
                        
                        continue
                
                # Store results
                result["output"] = output_lines
                result["duration"] = time.time() - start_time
                
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Command execution error: {e}")
        
        return result
    
    async def test_simple_prompt(self) -> Dict[str, Any]:
        """Test 1: Simple prompt with all required flags"""
        test_name = "Simple Prompt (2+2)"
        logger.info(f"\n=== Running: {test_name} ===")
        
        command = 'claude -p "What is 2+2?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'
        
        result = await self.execute_command(command, timeout=30)
        
        # Validate result
        success = (
            result["success"] and
            result["exit_code"] == 0 and
            any("4" in line or "four" in line.lower() for line in result["output"])
        )
        
        test_result = {
            "name": test_name,
            "success": success,
            "duration": result["duration"],
            "exit_code": result["exit_code"],
            "output_size": sum(len(line) for line in result["output"])
        }
        
        self._log_test_result(test_result)
        return test_result
    
    async def test_with_mcp_config(self) -> Dict[str, Any]:
        """Test 2: Command with MCP config and allowed tools"""
        test_name = "MCP Config Test"
        logger.info(f"\n=== Running: {test_name} ===")
        
        # Check if .mcp.json exists
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mcp_config_path = os.path.join(project_root, '.mcp.json')
        
        if not os.path.exists(mcp_config_path):
            logger.warning("Skipping MCP test - no .mcp.json found")
            return {
                "name": test_name,
                "success": True,  # Don't fail if MCP not configured
                "skipped": True,
                "reason": "No .mcp.json found"
            }
        
        command = (
            'claude -p "What is the capital of France?" '
            '--output-format stream-json --verbose '
            '--mcp-config .mcp.json '
            '--allowedTools "mcp__perplexity-ask mcp__brave-search" '
            '--dangerously-skip-permissions'
        )
        
        result = await self.execute_command(command, timeout=60)
        
        success = (
            result["success"] and
            result["exit_code"] == 0 and
            any("paris" in line.lower() for line in result["output"])
        )
        
        test_result = {
            "name": test_name,
            "success": success,
            "duration": result["duration"],
            "exit_code": result["exit_code"],
            "output_size": sum(len(line) for line in result["output"])
        }
        
        self._log_test_result(test_result)
        return test_result
    
    async def test_large_output(self) -> Dict[str, Any]:
        """Test 3: Large output generation (5000 word essay)"""
        test_name = "Large Output (5000 word essay)"
        logger.info(f"\n=== Running: {test_name} ===")
        
        command = (
            'claude -p "Write a 5000 word essay about the history and future of artificial intelligence. '
            'Include sections on early AI research, modern deep learning, and future possibilities." '
            '--output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'
        )
        
        result = await self.execute_command(command, timeout=300)
        
        # Count approximate words
        full_output = "\n".join(result["output"])
        word_count = len(full_output.split())
        
        success = (
            result["success"] and
            result["exit_code"] == 0 and
            word_count > 3000  # Allow some variance
        )
        
        test_result = {
            "name": test_name,
            "success": success,
            "duration": result["duration"],
            "exit_code": result["exit_code"],
            "output_size": len(full_output),
            "word_count": word_count
        }
        
        # Save large output
        output_file = TEST_OUTPUT_DIR / f"large_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(output_file, 'w') as f:
            f.write(f"Test: {test_name}\n")
            f.write(f"Word count: {word_count}\n")
            f.write(f"Duration: {result['duration']:.1f}s\n")
            f.write("=" * 80 + "\n")
            f.write(full_output)
        
        logger.info(f"Large output saved to: {output_file}")
        
        self._log_test_result(test_result)
        return test_result
    
    async def test_self_reflection_format(self) -> Dict[str, Any]:
        """Test 4: Self-reflection format prompt"""
        test_name = "Self-Reflection Format"
        logger.info(f"\n=== Running: {test_name} ===")
        
        command = (
            'claude -p "Explain recursion in programming. Format your response with: '
            '1) Initial explanation, 2) Code example, 3) Common pitfalls, 4) Best practices." '
            '--output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'
        )
        
        result = await self.execute_command(command, timeout=120)
        
        # Check for expected sections
        full_output = "\n".join(result["output"]).lower()
        has_sections = all([
            "explanation" in full_output or "recursion" in full_output,
            "example" in full_output or "def" in full_output,
            "pitfall" in full_output or "mistake" in full_output,
            "practice" in full_output or "tip" in full_output
        ])
        
        success = (
            result["success"] and
            result["exit_code"] == 0 and
            has_sections
        )
        
        test_result = {
            "name": test_name,
            "success": success,
            "duration": result["duration"],
            "exit_code": result["exit_code"],
            "output_size": len(full_output),
            "has_sections": has_sections
        }
        
        self._log_test_result(test_result)
        return test_result
    
    async def test_json_streaming_validation(self) -> Dict[str, Any]:
        """Test 5: Validate JSON streaming format"""
        test_name = "JSON Streaming Validation"
        logger.info(f"\n=== Running: {test_name} ===")
        
        command = (
            'claude -p "List 5 programming languages with their main use cases." '
            '--output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'
        )
        
        # For this test, we'll collect raw WebSocket messages
        json_lines = []
        
        try:
            async with websockets.connect(self.ws_url, ping_timeout=None) as websocket:
                request = {
                    "jsonrpc": "2.0",
                    "method": "execute",
                    "params": {"command": command},
                    "id": str(uuid.uuid4())
                }
                
                await websocket.send(json.dumps(request))
                
                start_time = time.time()
                while time.time() - start_time < 60:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        json_lines.append(response)
                        
                        data = json.loads(response)
                        if data.get("method") == "process.completed":
                            break
                    except asyncio.TimeoutError:
                        continue
        except Exception as e:
            logger.error(f"JSON validation error: {e}")
        
        # Validate JSON format
        valid_json_count = 0
        has_streaming_output = False
        
        for line in json_lines:
            try:
                data = json.loads(line)
                valid_json_count += 1
                
                # Check for streaming output
                if data.get("method") == "process.output":
                    output = data.get("params", {}).get("data", "")
                    if output and len(output) > 10:
                        has_streaming_output = True
            except:
                logger.warning(f"Invalid JSON line: {line[:100]}...")
        
        success = valid_json_count > 0 and has_streaming_output
        
        test_result = {
            "name": test_name,
            "success": success,
            "duration": time.time() - start_time,
            "valid_json_lines": valid_json_count,
            "total_lines": len(json_lines),
            "has_streaming": has_streaming_output
        }
        
        self._log_test_result(test_result)
        return test_result
    
    async def test_timeout_recovery(self) -> Dict[str, Any]:
        """Test 6: Timeout and recovery scenario"""
        test_name = "Timeout Recovery"
        logger.info(f"\n=== Running: {test_name} ===")
        
        # This command should timeout
        command = (
            'claude -p "Generate an infinite sequence of prime numbers, '
            'showing each one as you calculate it. Don\'t stop until told." '
            '--output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'
        )
        
        result = await self.execute_command(command, timeout=10)
        
        # We expect this to timeout
        success = (
            result["error"] == "Timeout" and
            result["duration"] >= 10
        )
        
        test_result = {
            "name": test_name,
            "success": success,
            "duration": result["duration"],
            "error": result["error"],
            "timed_out": result["error"] == "Timeout"
        }
        
        self._log_test_result(test_result)
        return test_result
    
    async def test_concurrent_requests(self) -> Dict[str, Any]:
        """Test 7: Multiple concurrent requests"""
        test_name = "Concurrent Requests"
        logger.info(f"\n=== Running: {test_name} ===")
        
        commands = [
            'claude -p "What is 5+5?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
            'claude -p "What is 10*10?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
            'claude -p "What is 100-50?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'
        ]
        
        # Note: WebSocket handler currently processes requests sequentially
        # This tests rapid sequential execution
        start_time = time.time()
        results = []
        
        for cmd in commands:
            result = await self.execute_command(cmd, timeout=30)
            results.append(result)
            # Small delay between requests
            await asyncio.sleep(0.5)
        
        total_duration = time.time() - start_time
        all_success = all(r["success"] for r in results)
        
        test_result = {
            "name": test_name,
            "success": all_success,
            "duration": total_duration,
            "requests": len(commands),
            "successful_requests": sum(1 for r in results if r["success"])
        }
        
        self._log_test_result(test_result)
        return test_result
    
    async def test_error_handling(self) -> Dict[str, Any]:
        """Test 8: Error handling for invalid commands"""
        test_name = "Error Handling"
        logger.info(f"\n=== Running: {test_name} ===")
        
        # Invalid command (nonexistent executable)
        command = 'nonexistent_command --help'
        
        result = await self.execute_command(command, timeout=10)
        
        # We expect this to fail with non-zero exit code
        success = (
            not result["success"] and
            result["exit_code"] != 0
        )
        
        test_result = {
            "name": test_name,
            "success": success,
            "duration": result["duration"],
            "exit_code": result["exit_code"],
            "handled_error": result["exit_code"] is not None
        }
        
        self._log_test_result(test_result)
        return test_result
    
    async def test_environment_validation(self) -> Dict[str, Any]:
        """Test 9: Validate environment variables are passed correctly"""
        test_name = "Environment Validation"
        logger.info(f"\n=== Running: {test_name} ===")
        
        # Command to check environment
        command = 'python -c "import os; print(\'PYTHONPATH:\', os.environ.get(\'PYTHONPATH\', \'NOT SET\')); print(\'Working Dir:\', os.getcwd())"'
        
        result = await self.execute_command(command, timeout=10)
        
        # Check output contains expected paths
        full_output = "\n".join(result["output"])
        has_pythonpath = "PYTHONPATH:" in full_output and "src" in full_output
        has_working_dir = "Working Dir:" in full_output
        
        success = (
            result["success"] and
            result["exit_code"] == 0 and
            has_pythonpath and
            has_working_dir
        )
        
        test_result = {
            "name": test_name,
            "success": success,
            "duration": result["duration"],
            "exit_code": result["exit_code"],
            "has_pythonpath": has_pythonpath,
            "has_working_dir": has_working_dir,
            "output": full_output
        }
        
        self._log_test_result(test_result)
        return test_result
    
    async def test_buffer_chunking(self) -> Dict[str, Any]:
        """Test 10: Test buffer chunking for very large outputs"""
        test_name = "Buffer Chunking"
        logger.info(f"\n=== Running: {test_name} ===")
        
        # Generate very large output (>64KB)
        command = (
            'python -c "print(\'A\' * 100000)"'  # 100KB of 'A's
        )
        
        result = await self.execute_command(command, timeout=10)
        
        # Check if we received the full output
        full_output = "".join(result["output"])
        expected_size = 100000
        actual_size = len(full_output.replace('\n', ''))
        
        # Allow for some newlines
        success = (
            result["success"] and
            result["exit_code"] == 0 and
            actual_size >= expected_size * 0.95  # 95% of expected
        )
        
        test_result = {
            "name": test_name,
            "success": success,
            "duration": result["duration"],
            "exit_code": result["exit_code"],
            "expected_size": expected_size,
            "actual_size": actual_size,
            "chunks": len(result["output"])
        }
        
        self._log_test_result(test_result)
        return test_result
    
    def _log_test_result(self, result: Dict[str, Any]):
        """Log and store test result"""
        status = "✅ PASSED" if result["success"] else "❌ FAILED"
        logger.info(f"{status} - {result['name']} ({result.get('duration', 0):.1f}s)")
        
        # Add to results
        self.results["total"] += 1
        if result["success"]:
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1
        
        self.results["tests"].append(result)
    
    async def run_all_tests(self):
        """Run all stress tests"""
        logger.info("=" * 80)
        logger.info("COMPREHENSIVE WEBSOCKET STRESS TEST")
        logger.info("=" * 80)
        
        # Check prerequisites
        if not await self._check_prerequisites():
            logger.error("Prerequisites check failed")
            return
        
        # Start WebSocket handler
        if not await self.start_websocket_handler():
            logger.error("Failed to start WebSocket handler")
            return
        
        try:
            # Run all tests
            tests = [
                self.test_simple_prompt,
                self.test_with_mcp_config,
                self.test_large_output,
                self.test_self_reflection_format,
                self.test_json_streaming_validation,
                self.test_timeout_recovery,
                self.test_concurrent_requests,
                self.test_error_handling,
                self.test_environment_validation,
                self.test_buffer_chunking,
            ]
            
            for test_func in tests:
                try:
                    await test_func()
                    # Delay between tests
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Test {test_func.__name__} crashed: {e}")
                    self._log_test_result({
                        "name": test_func.__name__,
                        "success": False,
                        "error": str(e),
                        "duration": 0
                    })
            
            # Generate final report
            self._generate_report()
            
        finally:
            self.stop_websocket_handler()
    
    async def _check_prerequisites(self) -> bool:
        """Check all prerequisites"""
        logger.info("Checking prerequisites...")
        
        # Check Claude CLI
        try:
            result = subprocess.run(
                ['which', 'claude'],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                logger.error("Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-cli")
                return False
            logger.success("✓ Claude CLI found")
        except Exception as e:
            logger.error(f"Error checking Claude CLI: {e}")
            return False
        
        # Check Python environment
        # project_root is already defined globally
        src_path = os.path.join(project_root, 'src')
        if not os.path.exists(src_path):
            logger.error(f"src directory not found at: {src_path}")
            return False
        logger.success("✓ Python environment configured")
        
        return True
    
    def _generate_report(self):
        """Generate comprehensive test report"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("=" * 80)
        
        # Summary
        total_duration = sum(t.get("duration", 0) for t in self.results["tests"])
        success_rate = (self.results["passed"] / max(1, self.results["total"])) * 100
        
        logger.info(f"Total Tests: {self.results['total']}")
        logger.info(f"Passed: {self.results['passed']} ({success_rate:.1f}%)")
        logger.info(f"Failed: {self.results['failed']}")
        logger.info(f"Total Duration: {total_duration:.1f}s")
        logger.info(f"Test Period: {self.test_start_time.strftime('%Y-%m-%d %H:%M:%S')} - {datetime.now().strftime('%H:%M:%S')}")
        
        # Detailed results
        logger.info("\nDETAILED RESULTS:")
        logger.info("-" * 80)
        
        for test in self.results["tests"]:
            status = "✅" if test["success"] else "❌"
            duration = test.get("duration", 0)
            logger.info(f"{status} {test['name']:<30} {duration:>6.1f}s")
            
            # Additional details for failed tests
            if not test["success"]:
                if "error" in test:
                    logger.info(f"   Error: {test['error']}")
                if "exit_code" in test:
                    logger.info(f"   Exit Code: {test['exit_code']}")
        
        # Save JSON report
        report_file = TEST_OUTPUT_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"\nDetailed report saved to: {report_file}")
        logger.info(f"Test outputs directory: {TEST_OUTPUT_DIR.absolute()}")
        
        # Log file location
        logger.info(f"\nFor debugging, check logs in: {TEST_OUTPUT_DIR}")
        
        # Success/failure message
        if self.results["failed"] == 0:
            logger.success("\n🎉 ALL TESTS PASSED! 🎉")
        else:
            logger.warning(f"\n⚠️  {self.results['failed']} tests failed. Check logs for details.")


async def main():
    """Main entry point"""
    tester = WebSocketStressTest()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())