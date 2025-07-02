#!/usr/bin/env python3
"""
Smart Comprehensive Stress Test with Retry Logic
Tests the fixed WebSocket handler and retries when Claude gives short responses
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
import websockets
from typing import Dict, List, Any, Optional, Tuple
import uuid

# Add src to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'src'))

from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>", level="INFO")

# Test output directory
TEST_OUTPUT_DIR = Path(project_root) / "test_results/stress/smart_test"
TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logger.add(TEST_OUTPUT_DIR / f"smart_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", level="DEBUG")


class SmartStressTest:
    """Smart stress test that retries when Claude gives inadequate responses"""
    
    def __init__(self):
        self.ws_process = None
        self.ws_port = 8004
        self.ws_url = f"ws://localhost:{self.ws_port}/ws"
        self.results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "retries": 0,
            "tests": []
        }
        self.test_start_time = datetime.now()
        
    async def start_websocket_handler(self) -> bool:
        """Start the WebSocket handler process"""
        logger.info("Starting WebSocket handler with fixes...")
        
        # Kill any existing processes
        os.system('pkill -9 -f websocket_handler')
        os.system(f'lsof -ti:{self.ws_port} | xargs -r kill -9 2>/dev/null')
        await asyncio.sleep(2)
        
        # Set up environment
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.join(project_root, 'src')
        
        # CRITICAL: UNSET ANTHROPIC_API_KEY
        if 'ANTHROPIC_API_KEY' in env:
            del env['ANTHROPIC_API_KEY']
            logger.warning("UNSET ANTHROPIC_API_KEY")
        
        # Start the handler
        handler_path = os.path.join(project_root, 'src/cc_executor/core/websocket_handler.py')
        
        self.ws_process = subprocess.Popen(
            [sys.executable, str(handler_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            preexec_fn=os.setsid
        )
        
        # Wait for server to be ready
        start_time = time.time()
        while time.time() - start_time < 10:
            if self.ws_process.poll() is not None:
                output, _ = self.ws_process.communicate()
                logger.error(f"WebSocket handler died: {output}")
                return False
            
            try:
                async with websockets.connect(self.ws_url, ping_timeout=None) as ws:
                    await ws.close()
                logger.success("WebSocket handler started successfully")
                return True
            except:
                await asyncio.sleep(0.5)
        
        logger.error("WebSocket handler startup timeout")
        return False
    
    async def execute_command(self, command: str, timeout: int = 120) -> Tuple[bool, Dict[str, Any]]:
        """Execute a command and return (success, result_data)"""
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
                request = {
                    "jsonrpc": "2.0",
                    "method": "execute",
                    "params": {"command": command},
                    "id": str(uuid.uuid4())
                }
                
                await websocket.send(json.dumps(request))
                logger.debug(f"Sent command: {command[:100]}...")
                
                output_lines = []
                
                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        data = json.loads(response)
                        
                        if "error" in data:
                            result["error"] = data["error"]
                            logger.error(f"Server error: {data['error']}")
                            break
                        
                        elif data.get("method") == "process.output":
                            output = data.get("params", {}).get("data", "")
                            if output:
                                output_lines.append(output)
                        
                        elif data.get("method") == "process.completed":
                            result["exit_code"] = data.get("params", {}).get("exit_code", -1)
                            result["success"] = result["exit_code"] == 0
                            break
                    
                    except asyncio.TimeoutError:
                        continue
                
                result["output"] = output_lines
                result["duration"] = time.time() - start_time
                
        except Exception as e:
            result["error"] = str(e)
            result["duration"] = time.time() - start_time
            logger.error(f"Command execution error: {e}")
        
        return result["success"], result
    
    def analyze_claude_response(self, output: List[str], expected_type: str) -> Tuple[bool, str]:
        """Analyze if Claude's response is adequate"""
        full_output = "\n".join(output)
        
        # Parse Claude's JSON output
        claude_response = ""
        for line in output:
            if '"type":"assistant"' in line:
                try:
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", [])
                    if content and isinstance(content, list):
                        claude_response = content[0].get("text", "")
                except:
                    pass
        
        if expected_type == "essay":
            word_count = len(claude_response.split())
            if word_count < 500:  # Expect at least 500 words for an essay
                return False, f"Too short: only {word_count} words (expected 500+)"
            return True, f"Good: {word_count} words"
        
        elif expected_type == "list":
            lines = claude_response.strip().split('\n')
            if len(lines) < 3:  # Expect at least 3 items in a list
                return False, f"Too few items: only {len(lines)} (expected 3+)"
            return True, f"Good: {len(lines)} items"
        
        elif expected_type == "calculation":
            # Just check if there's a numeric answer
            if any(char.isdigit() for char in claude_response):
                return True, "Contains numeric answer"
            return False, "No numeric answer found"
        
        # Default: check if response is substantive
        if len(claude_response) < 50:
            return False, f"Too short: only {len(claude_response)} chars"
        return True, "Adequate response"
    
    async def execute_with_retry(self, test_name: str, command: str, expected_type: str, max_retries: int = 2) -> Dict[str, Any]:
        """Execute command with retry logic for inadequate responses"""
        logger.info(f"\n=== Running: {test_name} ===")
        
        for attempt in range(max_retries + 1):
            if attempt > 0:
                logger.info(f"Retry attempt {attempt}/{max_retries}")
                # Modify prompt to be more explicit
                if attempt == 1:
                    command = command.replace('" --output', ' Please provide the complete response." --output')
                elif attempt == 2:
                    command = command.replace('Please provide the complete response." --output', 
                                            'DO NOT just say you will do it, actually do it now." --output')
            
            success, result = await self.execute_command(command)
            
            if success and result["output"]:
                # Analyze the response
                adequate, reason = self.analyze_claude_response(result["output"], expected_type)
                
                if adequate:
                    logger.success(f"✅ {test_name} - {reason}")
                    result["adequate"] = True
                    result["attempts"] = attempt + 1
                    return result
                else:
                    logger.warning(f"❌ Inadequate response - {reason}")
                    if attempt < max_retries:
                        self.results["retries"] += 1
                        await asyncio.sleep(2)
                        continue
            
            if not success:
                logger.error(f"❌ {test_name} - Command failed")
                break
        
        # Failed after all retries
        result["adequate"] = False
        result["attempts"] = max_retries + 1
        return result
    
    async def run_all_tests(self):
        """Run comprehensive stress tests with retry logic"""
        logger.info("=" * 80)
        logger.info("SMART COMPREHENSIVE STRESS TEST WITH RETRY LOGIC")
        logger.info("=" * 80)
        
        if not await self.start_websocket_handler():
            logger.error("Failed to start WebSocket handler")
            return
        
        try:
            # Define test cases
            test_cases = [
                # Basic tests
                ("Simple Math", 
                 'claude -p "What is 2+2?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
                 "calculation"),
                
                ("Word List",
                 'claude -p "List 5 colors, one per line" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
                 "list"),
                
                # Essay test (this is where it often fails)
                ("Short Essay",
                 'claude -p "Write a 500 word essay about the benefits of automated testing" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
                 "essay"),
                
                # More complex tests
                ("Code Example",
                 'claude -p "Write a Python function to calculate fibonacci numbers with comments" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
                 "code"),
                
                ("Large Essay",
                 'claude -p "Write a 1000 word essay about space exploration" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
                 "essay"),
                
                # Sequential math tests
                ("Math Series 1",
                 'claude -p "What is 10*10?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
                 "calculation"),
                
                ("Math Series 2",
                 'claude -p "What is 50-25?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
                 "calculation"),
                
                # Non-Claude test
                ("Echo Test",
                 'echo "WebSocket handler still working"',
                 "echo"),
            ]
            
            # Run all tests
            for test_name, command, expected_type in test_cases:
                if expected_type == "echo":
                    # Simple execution for non-Claude commands
                    success, result = await self.execute_command(command, timeout=10)
                    result["adequate"] = success
                    result["attempts"] = 1
                else:
                    # Smart execution with retry for Claude commands
                    result = await self.execute_with_retry(test_name, command, expected_type)
                
                # Record result
                test_result = {
                    "name": test_name,
                    "success": result.get("adequate", False),
                    "attempts": result.get("attempts", 1),
                    "duration": result.get("duration", 0),
                    "exit_code": result.get("exit_code"),
                    "error": result.get("error")
                }
                
                self.results["total"] += 1
                if test_result["success"]:
                    self.results["passed"] += 1
                else:
                    self.results["failed"] += 1
                
                self.results["tests"].append(test_result)
                
                # Brief pause between tests
                await asyncio.sleep(2)
            
            # Generate report
            self._generate_report()
            
        finally:
            # Stop handler
            if self.ws_process:
                logger.info("\nStopping WebSocket handler...")
                os.killpg(os.getpgid(self.ws_process.pid), 9)
    
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
        logger.info(f"Total Retries: {self.results['retries']}")
        logger.info(f"Total Duration: {total_duration:.1f}s")
        
        # Detailed results
        logger.info("\nDETAILED RESULTS:")
        logger.info("-" * 80)
        
        for test in self.results["tests"]:
            status = "✅" if test["success"] else "❌"
            attempts = f" (attempts: {test['attempts']})" if test['attempts'] > 1 else ""
            duration = test.get("duration", 0)
            logger.info(f"{status} {test['name']:<25} {duration:>6.1f}s{attempts}")
        
        # Save results
        report_file = TEST_OUTPUT_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"\nReport saved to: {report_file}")
        
        # Generate markdown report
        self._generate_markdown_report()
        
        if self.results["failed"] == 0:
            logger.success("\n🎉 ALL TESTS PASSED! 🎉")
            logger.info("The WebSocket handler fix is working correctly!")
        else:
            logger.warning(f"\n⚠️  {self.results['failed']} tests failed even with retries")
    
    def _generate_markdown_report(self):
        """Generate markdown report"""
        report_file = TEST_OUTPUT_DIR / f"smart_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        total = self.results["total"]
        passed = self.results["passed"]
        failed = self.results["failed"]
        retries = self.results["retries"]
        success_rate = (passed / total * 100) if total > 0 else 0
        
        report = f"""# Smart Stress Test Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | {total} |
| ✅ Passed | {passed} |
| ❌ Failed | {failed} |
| 🔄 Total Retries | {retries} |
| Success Rate | {success_rate:.1f}% |

## Key Findings

1. **WebSocket Handler Fix**: {"✅ Working" if success_rate > 80 else "❌ Still has issues"}
2. **Claude Response Quality**: {retries} retries needed for adequate responses
3. **Sequential Execution**: All tests run without handler restart

## Test Results

| Test | Status | Duration | Attempts |
|------|--------|----------|----------|
"""
        
        for test in self.results["tests"]:
            status = "✅" if test["success"] else "❌"
            attempts = test.get('attempts', 1)
            duration = test.get('duration', 0)
            report += f"| {test['name']} | {status} | {duration:.1f}s | {attempts} |\n"
        
        report += f"""

## Conclusion

The WebSocket handler with the timeout fix is {"working correctly" if success_rate > 80 else "still experiencing issues"}.
{"No handler restarts were needed." if success_rate > 80 else "Some tests still failed even with retries."}

---
*Smart Stress Test Suite with Retry Logic*
"""
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"Markdown report saved to: {report_file}")


async def main():
    """Main entry point"""
    tester = SmartStressTest()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())