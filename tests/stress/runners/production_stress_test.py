#!/usr/bin/env python3
"""
Production-ready stress test with per-task WebSocket handler restart
This implements the recommended approach for handling 40-50 sequential Claude tasks
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import websockets
import uuid
from datetime import datetime

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'src'))

from loguru import logger
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

class ProductionWebSocketTest:
    def __init__(self):
        self.project_root = project_root
        self.ws_port = 8004
        self.ws_url = f"ws://localhost:{self.ws_port}/ws"
        self.results = []
        
    async def kill_handler(self):
        """Kill any existing WebSocket handler processes"""
        os.system('pkill -9 -f websocket_handler 2>/dev/null')
        os.system(f'lsof -ti:{self.ws_port} | xargs -r kill -9 2>/dev/null')
        await asyncio.sleep(1)
        
    async def start_handler(self):
        """Start a fresh WebSocket handler"""
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.join(self.project_root, 'src')
        # Critical: Remove API key for Claude CLI
        if 'ANTHROPIC_API_KEY' in env:
            del env['ANTHROPIC_API_KEY']
        
        handler = subprocess.Popen(
            [sys.executable, "-m", "cc_executor.core.websocket_handler"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            cwd=self.project_root,
            preexec_fn=os.setsid
        )
        
        # Wait for startup
        start_time = time.time()
        while time.time() - start_time < 10:
            if handler.poll() is not None:
                output, _ = handler.communicate()
                logger.error(f"Handler died during startup: {output}")
                return None
            
            # Check if port is listening
            try:
                async with websockets.connect(self.ws_url, ping_timeout=None) as ws:
                    await ws.close()
                return handler
            except:
                await asyncio.sleep(0.5)
        
        logger.error("Handler failed to start within 10s")
        handler.terminate()
        return None
        
    async def execute_task(self, task_name, command, timeout=120):
        """Execute a single task via WebSocket"""
        try:
            async with websockets.connect(self.ws_url, ping_timeout=None) as ws:
                request = {
                    "jsonrpc": "2.0",
                    "method": "execute",
                    "params": {"command": command},
                    "id": str(uuid.uuid4())
                }
                
                await ws.send(json.dumps(request))
                
                start_time = time.time()
                output_count = 0
                
                while True:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        data = json.loads(msg)
                        
                        if data.get("method") == "process.output":
                            output_count += 1
                        elif data.get("method") == "process.completed":
                            exit_code = data.get("params", {}).get("exit_code", -1)
                            duration = time.time() - start_time
                            return {
                                "success": True,
                                "exit_code": exit_code,
                                "duration": duration,
                                "outputs": output_count
                            }
                    except asyncio.TimeoutError:
                        if time.time() - start_time > timeout:
                            return {
                                "success": False,
                                "error": "Timeout",
                                "duration": time.time() - start_time,
                                "outputs": output_count
                            }
                        continue
                        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": 0,
                "outputs": 0
            }
    
    async def execute_task_with_restart(self, task_name, command, timeout=120):
        """Execute task with handler restart (production approach)"""
        logger.info(f"[RESTART] Killing existing handler...")
        await self.kill_handler()
        
        logger.info(f"[RESTART] Starting fresh handler...")
        handler = await self.start_handler()
        
        if not handler:
            return {
                "task": task_name,
                "success": False,
                "error": "Failed to start handler",
                "duration": 0,
                "restart_overhead": 0
            }
        
        restart_time = time.time()
        
        logger.info(f"[EXECUTE] Running: {task_name}")
        result = await self.execute_task(task_name, command, timeout)
        
        result["task"] = task_name
        result["restart_overhead"] = time.time() - restart_time - result["duration"]
        
        # Clean shutdown
        handler.terminate()
        handler.wait()
        
        return result
    
    async def run_production_test(self):
        """Run production stress test with restart strategy"""
        logger.info("=" * 80)
        logger.info("PRODUCTION WEBSOCKET STRESS TEST WITH PER-TASK RESTART")
        logger.info("=" * 80)
        
        # Define test tasks similar to production workload
        tasks = [
            ("Simple Math", 'claude -p "What is 2+2?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 30),
            ("List Generation", 'claude -p "List 10 programming languages" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 30),
            ("Code Generation", 'claude -p "Write a Python function to calculate factorial" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 60),
            ("Essay Writing", 'claude -p "Write a 1000 word essay about WebSockets" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 120),
            ("JSON Output", 'claude -p "Output a JSON object with 5 fields" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 30),
            ("Complex Analysis", 'claude -p "Analyze the pros and cons of microservices architecture" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 90),
            ("Simple Echo", 'echo "Testing handler stability"', 5),
            ("Final Math", 'claude -p "Calculate 100 * 50" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 30),
        ]
        
        start_time = time.time()
        
        for i, (name, command, timeout) in enumerate(tasks):
            logger.info(f"\n{'='*60}")
            logger.info(f"Task {i+1}/{len(tasks)}: {name}")
            logger.info(f"{'='*60}")
            
            result = await self.execute_task_with_restart(name, command, timeout)
            self.results.append(result)
            
            if result["success"]:
                logger.success(f"✅ PASSED in {result['duration']:.1f}s (restart overhead: {result['restart_overhead']:.1f}s)")
            else:
                logger.error(f"❌ FAILED: {result.get('error', 'Unknown error')}")
            
            # Small delay between tasks
            await asyncio.sleep(1)
        
        total_time = time.time() - start_time
        self.generate_report(total_time)
    
    def generate_report(self, total_time):
        """Generate comprehensive test report"""
        logger.info("\n" + "=" * 80)
        logger.info("PRODUCTION TEST REPORT")
        logger.info("=" * 80)
        
        # Calculate statistics
        successful = sum(1 for r in self.results if r["success"])
        failed = len(self.results) - successful
        success_rate = (successful / len(self.results)) * 100
        
        # Timing statistics
        total_execution = sum(r["duration"] for r in self.results)
        total_overhead = sum(r.get("restart_overhead", 0) for r in self.results)
        avg_overhead = total_overhead / len(self.results)
        
        logger.info(f"\nTest Summary:")
        logger.info(f"  Total Tasks: {len(self.results)}")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Failed: {failed}")
        logger.info(f"  Success Rate: {success_rate:.1f}%")
        
        logger.info(f"\nTiming Analysis:")
        logger.info(f"  Total Time: {total_time:.1f}s")
        logger.info(f"  Execution Time: {total_execution:.1f}s")
        logger.info(f"  Restart Overhead: {total_overhead:.1f}s")
        logger.info(f"  Average Overhead per Task: {avg_overhead:.1f}s")
        
        logger.info(f"\nDetailed Results:")
        for r in self.results:
            status = "✅" if r["success"] else "❌"
            overhead = f"(+{r.get('restart_overhead', 0):.1f}s restart)" if r.get('restart_overhead') else ""
            error = f" - {r.get('error', '')}" if not r["success"] else ""
            logger.info(f"  {status} {r['task']:<30} {r['duration']:6.1f}s {overhead}{error}")
        
        # Save report
        report_path = os.path.join(self.project_root, "production_test_report.md")
        with open(report_path, "w") as f:
            f.write(f"# Production WebSocket Test Report\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Summary\n\n")
            f.write(f"- **Total Tasks**: {len(self.results)}\n")
            f.write(f"- **Success Rate**: {success_rate:.1f}%\n")
            f.write(f"- **Total Time**: {total_time:.1f}s\n")
            f.write(f"- **Average Restart Overhead**: {avg_overhead:.1f}s per task\n\n")
            f.write(f"## Results\n\n")
            f.write(f"| Task | Status | Duration | Restart Overhead | Notes |\n")
            f.write(f"|------|--------|----------|------------------|-------|\n")
            for r in self.results:
                status = "✅ PASS" if r["success"] else "❌ FAIL"
                notes = r.get('error', '-') if not r["success"] else '-'
                overhead = f"{r.get('restart_overhead', 0):.1f}s"
                f.write(f"| {r['task']} | {status} | {r['duration']:.1f}s | {overhead} | {notes} |\n")
            f.write(f"\n## Conclusion\n\n")
            if success_rate == 100:
                f.write(f"✅ **Production Ready**: All tasks completed successfully with the per-task restart strategy.\n")
            elif success_rate >= 90:
                f.write(f"⚠️ **Nearly Ready**: {success_rate:.1f}% success rate. Minor issues to address.\n")
            else:
                f.write(f"❌ **Not Ready**: Only {success_rate:.1f}% success rate. Significant issues remain.\n")
        
        logger.success(f"\nReport saved to: {report_path}")
        
        if success_rate == 100:
            logger.success("\n🎉 PRODUCTION READY! The per-task restart strategy ensures 100% reliability.")
        else:
            logger.warning(f"\n⚠️ Success rate: {success_rate:.1f}% - further investigation needed.")

if __name__ == "__main__":
    test = ProductionWebSocketTest()
    asyncio.run(test.run_production_test())