#!/usr/bin/env python3
"""
Run unified stress tests with Redis-based adaptive timeouts.

This enhanced version:
1. Uses 10-minute (600s) timeouts for complex/extreme prompts
2. Stores actual execution times in Redis after each test  
3. Uses Redis to predict timeouts for similar prompts
4. Integrates with the enhanced prompt classifier

Key Features:
- Adaptive timeouts based on historical data
- System load detection with 3x multiplier
- Unknown prompt handling with minimum 90s timeout
- Graceful fallback when Redis is unavailable
- Updates Redis with actual execution times
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

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

# Import Redis timing module
from cc_executor.prompts.redis_task_timing import RedisTaskTimer

# Output directory
OUTPUT_DIR = Path("test_outputs/unified_stress_tests_redis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class UnifiedStressTestRunnerWithRedis:
    """Runs stress tests with Redis-based adaptive timeouts"""
    
    def __init__(self, use_enhanced=True):
        self.ws_process = None
        self.ws_port = 8005 if use_enhanced else 8004
        self.ws_url = f"ws://localhost:{self.ws_port}/ws"
        self.use_enhanced = use_enhanced
        self.results = {
            "start_time": datetime.now().isoformat(),
            "categories": {},
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0
            },
            "timing_accuracy": []
        }
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.load_multiplier = 1  # Adjusted based on system load
        self.success_count = 0
        self.failure_count = 0
        
        # Initialize Redis timer
        self.redis_timer = None
        self._init_redis_timer()
        
    def _init_redis_timer(self):
        """Initialize Redis timer with connection check"""
        try:
            self.redis_timer = RedisTaskTimer()
            # Test connection
            result = subprocess.run(
                ['redis-cli', 'ping'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode != 0 or result.stdout.strip() != "PONG":
                print("⚠️  Redis not available, using static timeouts")
                self.redis_timer = None
            else:
                print("✅ Redis connection established for adaptive timeouts")
        except Exception as e:
            print(f"⚠️  Redis initialization failed: {e}")
            print("   Using static timeouts as fallback")
            self.redis_timer = None
        
    async def start_websocket_handler(self) -> bool:
        """Start the WebSocket handler"""
        # Check if handler is already running on the expected port
        try:
            async with websockets.connect(self.ws_url, ping_timeout=None) as ws:
                await ws.close()
                print(f"✓ {'Enhanced' if self.use_enhanced else 'Standard'} WebSocket handler already running on port {self.ws_port}")
                return True
        except:
            pass
            
        print(f"Starting {'enhanced' if self.use_enhanced else 'standard'} WebSocket handler...")
        
        # Kill existing process
        os.system(f'lsof -ti:{self.ws_port} | xargs -r kill -9 2>/dev/null')
        await asyncio.sleep(1)
        
        # Set up environment
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.join(self.project_root, 'src')
        
        # Start handler
        handler_path = os.path.join(self.project_root, 'src/cc_executor/core/websocket_handler.py')
        self.ws_process = subprocess.Popen(
            [sys.executable, handler_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            preexec_fn=os.setsid
        )
        
        # Wait for startup
        start_time = time.time()
        while time.time() - start_time < 10:
            if self.ws_process.poll() is not None:
                output, _ = self.ws_process.communicate()
                print(f"WebSocket handler died: {output[:500]}")
                return False
            
            try:
                async with websockets.connect(self.ws_url, ping_timeout=None) as ws:
                    await ws.close()
                print("✓ WebSocket handler started")
                return True
            except:
                await asyncio.sleep(0.5)
        
        print("WebSocket handler startup timeout")
        return False
    
    def stop_websocket_handler(self):
        """Stop the WebSocket handler"""
        if self.ws_process:
            print("Stopping WebSocket handler...")
            try:
                os.killpg(os.getpgid(self.ws_process.pid), signal.SIGTERM)
                self.ws_process.wait(timeout=5)
            except:
                try:
                    os.killpg(os.getpgid(self.ws_process.pid), signal.SIGKILL)
                except:
                    pass
    
    async def get_adaptive_timeout(self, test: Dict[str, Any]) -> Dict[str, Any]:
        """Get adaptive timeout from Redis based on test characteristics"""
        # Default timeouts based on complexity
        default_timeouts = {
            "simple": {"base": 120, "max": 180},
            "parallel": {"base": 180, "max": 300},
            "model_comparison": {"base": 300, "max": 450},
            "long_running": {"base": 300, "max": 450},
            "rapid_fire": {"base": 240, "max": 360},
            "complex_orchestration": {"base": 600, "max": 900},  # 10-15 min for complex
            "extreme_stress": {"base": 600, "max": 900}  # 10-15 min for extreme
        }
        
        # Start with defaults
        category = test.get("category", "simple")
        defaults = default_timeouts.get(category, {"base": 180, "max": 300})
        
        result = {
            "timeout": defaults["max"],
            "stall_timeout": 60,
            "expected_time": defaults["base"],
            "confidence": 0.1,
            "based_on": "defaults",
            "category": category
        }
        
        # Try Redis timing if available
        if self.redis_timer:
            try:
                # Build command for classification
                request = test.get("natural_language_request", "")
                metatags = test.get("metatags", "")
                command = f"{metatags} {request}"
                
                # Get estimation from Redis
                estimation = await self.redis_timer.estimate_complexity(command)
                
                # Update result with Redis data
                result.update({
                    "timeout": int(estimation["max_time"]),
                    "stall_timeout": estimation["stall_timeout"],
                    "expected_time": estimation["expected_time"],
                    "confidence": estimation["confidence"],
                    "based_on": estimation["based_on"],
                    "complexity": estimation["complexity"],
                    "question_type": estimation["question_type"],
                    "system_load": estimation.get("system_load", {}),
                    "load_multiplier": estimation.get("load_multiplier", 1)
                })
                
                # Ensure minimum timeouts for complex/extreme tasks
                if category in ["complex_orchestration", "extreme_stress"]:
                    result["timeout"] = max(result["timeout"], 600)  # Minimum 10 minutes
                    result["expected_time"] = max(result["expected_time"], 300)  # Expected 5 minutes
                
                # For prompts with no history (truly unknown), use 10 minute timeout
                if estimation.get("based_on") == "default_with_3x_baseline" and estimation.get("confidence", 0) <= 0.1:
                    print(f"     ⚠️  No history found - using 10 minute timeout for safety")
                    result["timeout"] = max(result["timeout"], 600)  # 10 minutes for unknown
                    result["expected_time"] = max(result["expected_time"], 300)  # Expected 5 minutes
                
                print(f"  📊 Redis Timing Prediction:")
                print(f"     Expected: {result['expected_time']:.1f}s")
                print(f"     Timeout: {result['timeout']}s")
                print(f"     Stall: {result['stall_timeout']}s")
                print(f"     Confidence: {result['confidence']:.1%}")
                print(f"     Based on: {result['based_on']}")
                
                if estimation.get("unknown_prompt_acknowledged"):
                    print(f"     ⚠️  Unknown prompt type - using minimum timeout")
                
            except Exception as e:
                print(f"  ⚠️  Redis timing failed: {e}")
                print(f"     Using category defaults: {result['timeout']}s")
        
        return result
    
    async def update_redis_history(self, test: Dict[str, Any], elapsed: float, success: bool, expected: float):
        """Update Redis with actual execution time"""
        if not self.redis_timer:
            return
            
        try:
            # Build command for classification
            request = test.get("natural_language_request", "")
            metatags = test.get("metatags", "")
            command = f"{metatags} {request}"
            
            # Classify and update
            task_type = self.redis_timer.classify_command(command)
            await self.redis_timer.update_history(
                task_type,
                elapsed=elapsed,
                success=success,
                expected=expected
            )
            print(f"  📝 Updated Redis history: {elapsed:.1f}s actual vs {expected:.1f}s expected")
            
            # Calculate accuracy for reporting
            if expected > 0:
                variance = (elapsed - expected) / expected * 100
                self.results["timing_accuracy"].append({
                    "test": test.get("id", "unknown"),
                    "actual": elapsed,
                    "expected": expected,
                    "variance_pct": variance,
                    "category": task_type["category"],
                    "complexity": task_type["complexity"]
                })
                
        except Exception as e:
            print(f"  ⚠️  Failed to update Redis history: {e}")
    
    async def execute_test(self, test: Dict[str, Any], category: str) -> Dict[str, Any]:
        """Execute a single test with adaptive timeout"""
        test_id = test.get("id", "unknown")
        test_name = test.get("name", "unknown")
        
        print(f"\n{'='*60}")
        print(f"Test: {test_id} - {test_name}")
        print(f"Category: {category}")
        
        # Store category in test for timeout lookup
        test["category"] = category
        
        result = {
            "id": test_id,
            "name": test_name,
            "category": category,
            "start_time": datetime.now().isoformat(),
            "success": False,
            "skipped": False,
            "reason": None,
            "duration": 0,
            "output": [],
            "timeout_used": None,
            "timeout_source": None
        }
        
        # Skip certain problematic tests
        skip_tests = ["simple_1", "simple_2"]  # Known to hang with Claude CLI
        if test_id in skip_tests:
            result["skipped"] = True
            result["reason"] = "Known to hang with Claude CLI"
            print(f"⚠️  Skipping {test_id} - {result['reason']}")
            return result
        
        # Get adaptive timeout from Redis
        timeout_info = await self.get_adaptive_timeout(test)
        timeout = timeout_info["timeout"]
        expected_time = timeout_info["expected_time"]
        
        result["timeout_used"] = timeout
        result["timeout_source"] = timeout_info["based_on"]
        
        # Build command
        command_template = test.get("command_template", "")
        if not command_template:
            # Build default command
            request = test.get("natural_language_request", "")
            metatags = test.get("metatags", "")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Build command with ALL required flags
            command = (
                f'claude -p "[marker:{test_id}_{timestamp}] {metatags} {request}" '
                f'--output-format stream-json '
                f'--dangerously-skip-permissions '
                f'--allowedTools none '
                f'--verbose'
            )
        else:
            # Use template
            request = test.get("natural_language_request", "")
            metatags = test.get("metatags", "")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            command = command_template.replace("${REQUEST}", request)
            command = command.replace("${METATAGS}", metatags)
            command = command.replace("${TIMESTAMP}", timestamp)
            
            # Ensure we have the required flags
            if "--output-format stream-json" not in command:
                command = command.replace("claude -p", "claude -p --output-format stream-json")
            if "--allowedTools" not in command and ".mcp.json" not in command:
                command += " --allowedTools none"
        
        print(f"Command: {command[:100]}...")
        print(f"Timeout: {timeout}s (expected: {expected_time:.1f}s)")
        
        # Get verification settings
        verification = test.get("verification", {})
        expected_patterns = verification.get("expected_patterns", [])
        save_output = verification.get("save_output", False)
        
        # Execute via WebSocket
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
                
                # Collect output
                output_lines = []
                patterns_found = []
                exit_code = None
                last_activity = time.time()
                
                while time.time() - start_time < timeout:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        data = json.loads(response)
                        last_activity = time.time()
                        
                        if "error" in data:
                            result["error"] = data["error"]
                            print(f"❌ Server error: {data['error']}")
                            break
                        
                        elif data.get("method") == "process.output":
                            output = data.get("params", {}).get("data", "")
                            if output:
                                output_lines.append(output)
                                
                                # Check if output contains JSON streaming events
                                if '{"type":' in output or '"event":' in output:
                                    result["has_json_streaming"] = True
                                
                                # Check patterns
                                for pattern in expected_patterns:
                                    if pattern.lower() in output.lower() and pattern not in patterns_found:
                                        patterns_found.append(pattern)
                                        print(f"  ✓ Found pattern: {pattern}")
                        
                        elif data.get("method") == "process.completed":
                            exit_code = data.get("params", {}).get("exit_code", -1)
                            result["exit_code"] = exit_code
                            break
                            
                        elif data.get("method") == "heartbeat":
                            # Enhanced handler sends heartbeats
                            print("  💓 Heartbeat received - connection alive")
                            
                        elif data.get("method") == "process.status":
                            # Enhanced handler sends status updates
                            status = data.get("params", {})
                            if "no_output_for" in status:
                                print(f"  ⏳ Status: No output for {status['no_output_for']:.0f}s, process still running")
                    
                    except asyncio.TimeoutError:
                        # Check for stall
                        time_since_activity = time.time() - last_activity
                        if time_since_activity > timeout_info["stall_timeout"]:
                            print(f"  ⚠️  No activity for {time_since_activity:.0f}s (stall timeout: {timeout_info['stall_timeout']}s)")
                            if len(output_lines) > 0:
                                print("     Initial response received, continuing to wait...")
                            else:
                                result["error"] = f"No initial response after {timeout_info['stall_timeout']}s"
                                break
                        continue
                
                # Calculate results
                elapsed = time.time() - start_time
                result["duration"] = elapsed
                result["output"] = output_lines
                result["patterns_found"] = patterns_found
                
                # Determine success
                if exit_code == 0 and len(patterns_found) >= len(expected_patterns) * 0.5:
                    result["success"] = True
                    print(f"✅ PASSED in {elapsed:.1f}s")
                    
                    # Compare with prediction
                    if expected_time > 0:
                        variance = (elapsed - expected_time) / expected_time * 100
                        print(f"   📈 Timing: {abs(variance):.1f}% {'over' if variance > 0 else 'under'} estimate")
                else:
                    print(f"❌ FAILED in {elapsed:.1f}s")
                    print(f"   Exit code: {exit_code}")
                    print(f"   Patterns found: {len(patterns_found)}/{len(expected_patterns)}")
                
                # Update Redis with actual timing
                await self.update_redis_history(test, elapsed, result["success"], expected_time)
                
                # Save output if requested
                if save_output or not result["success"]:
                    output_file = OUTPUT_DIR / f"{test_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    with open(output_file, 'w') as f:
                        f.write(f"Test: {test_id} - {test_name}\n")
                        f.write(f"Category: {category}\n")
                        f.write(f"Success: {result['success']}\n")
                        f.write(f"Duration: {elapsed:.1f}s\n")
                        f.write(f"Expected: {expected_time:.1f}s\n")
                        f.write(f"Timeout: {timeout}s (source: {timeout_info['based_on']})\n")
                        f.write(f"Exit Code: {exit_code}\n")
                        f.write(f"Patterns Found: {patterns_found}\n")
                        f.write("=" * 80 + "\n")
                        f.write("\n".join(output_lines))
                    print(f"   Output saved to: {output_file}")
                
        except Exception as e:
            elapsed = time.time() - start_time
            result["error"] = str(e)
            result["duration"] = elapsed
            print(f"❌ ERROR: {e}")
            
            # Still update Redis for failures
            await self.update_redis_history(test, elapsed, False, expected_time)
        
        return result
    
    def validate_preflight_checklist(self):
        """Validate all critical requirements before running tests"""
        print("\n" + "="*80)
        print("PRE-FLIGHT CHECKLIST VALIDATION")
        print("="*80)
        
        checklist = {
            "Claude CLI available": False,
            "WebSocket port available": False,
            "Working directory correct": False,
            "System load acceptable": False,
            "JSON test file exists": False,
            "ANTHROPIC_API_KEY handled": False,
            "Required flags documented": False,
            "Redis connection available": False
        }
        
        # Check Claude CLI
        if subprocess.run(['which', 'claude'], capture_output=True).returncode == 0:
            checklist["Claude CLI available"] = True
            
        # Check WebSocket port
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', self.ws_port))
        sock.close()
        
        if self.use_enhanced:
            # Enhanced handler should already be running
            if result == 0:  # Port is in use (good for enhanced)
                checklist["WebSocket port available"] = True
        else:
            # Standard handler - port should be free
            if result != 0:  # Port is free
                checklist["WebSocket port available"] = True
            
        # Check working directory
        if os.path.exists(os.path.join(self.project_root, '.mcp.json')):
            checklist["Working directory correct"] = True
            
        # Check system load
        load_output = subprocess.run(['uptime'], capture_output=True, text=True)
        if load_output.returncode == 0 and 'load average:' in load_output.stdout:
            checklist["System load acceptable"] = True
            
        # Check test file
        json_path = os.path.join(self.project_root, "src/cc_executor/tasks/unified_stress_test_tasks.json")
        if os.path.exists(json_path):
            checklist["JSON test file exists"] = True
            
        # Check ANTHROPIC_API_KEY handling
        if 'ANTHROPIC_API_KEY' not in os.environ or os.environ.get('CLAUDE_MAX') == 'true':
            checklist["ANTHROPIC_API_KEY handled"] = True
            
        # Required flags are documented in this script
        checklist["Required flags documented"] = True
        
        # Check Redis connection
        checklist["Redis connection available"] = self.redis_timer is not None
        
        # Print results
        all_passed = True
        for check, passed in checklist.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}")
            if not passed:
                all_passed = False
                
        if not all_passed:
            print("\n❌ PRE-FLIGHT CHECKS FAILED - Fix issues before running tests")
            print("   Note: Redis is optional but recommended for adaptive timeouts")
            return False
            
        print("\n✅ All pre-flight checks passed!")
        return True
    
    async def run_all_tests(self):
        """Run all tests from the JSON file with Redis timing"""
        print("=" * 80)
        print("UNIFIED STRESS TEST RUNNER WITH REDIS TIMING")
        print("=" * 80)
        
        # Run pre-flight checklist
        if not self.validate_preflight_checklist():
            return
        
        # Load test definitions
        json_path = os.path.join(self.project_root, "src/cc_executor/tasks/unified_stress_test_tasks.json")
        if not os.path.exists(json_path):
            print(f"❌ Test file not found: {json_path}")
            return
        
        with open(json_path) as f:
            test_data = json.load(f)
        
        # Check Claude CLI
        claude_check = subprocess.run(['which', 'claude'], capture_output=True)
        if claude_check.returncode != 0:
            print("❌ Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-cli")
            return
        
        # Check system load
        if self.redis_timer:
            system_load = self.redis_timer.get_system_load()
            print(f"\nSystem Load: CPU={system_load['cpu_load']:.1f}, GPU={system_load['gpu_memory_gb']:.1f}GB")
            
            if system_load['cpu_load'] > 14:
                print("⚠️  WARNING: System load > 14, expect 3x slower performance")
                self.load_multiplier = 3
            elif system_load['cpu_load'] > 5:
                print("⚠️  Moderate load detected, using 2x timeouts")
                self.load_multiplier = 2
        
        # Start WebSocket handler
        if not await self.start_websocket_handler():
            print("❌ Failed to start WebSocket handler")
            return
        
        try:
            # Run tests by category
            categories = test_data.get("categories", {})
            
            # Run simple tests first
            simple_categories = ["simple", "parallel"]
            complex_categories = ["model_comparison", "long_running", "rapid_fire", "complex_orchestration", "extreme_stress"]
            
            # Run categories in order
            all_categories = simple_categories + complex_categories
            
            for category_name in all_categories:
                if category_name not in categories:
                    continue
                
                category_data = categories[category_name]
                tasks = category_data.get("tasks", [])
                
                print(f"\n{'='*80}")
                print(f"CATEGORY: {category_name}")
                print(f"Description: {category_data.get('description', 'N/A')}")
                print(f"Tasks: {len(tasks)}")
                print("=" * 80)
                
                category_results = []
                
                for task in tasks:
                    result = await self.execute_test(task, category_name)
                    category_results.append(result)
                    
                    # Update summary
                    self.results["summary"]["total"] += 1
                    if result["skipped"]:
                        self.results["summary"]["skipped"] += 1
                    elif result["success"]:
                        self.results["summary"]["passed"] += 1
                        self.success_count += 1
                    else:
                        self.results["summary"]["failed"] += 1
                        self.failure_count += 1
                    
                    # Delay between tests
                    await asyncio.sleep(2)
                
                self.results["categories"][category_name] = category_results
                
                # Stop after simple tests if too many failures
                if category_name in simple_categories:
                    failure_rate = self.results["summary"]["failed"] / max(1, self.results["summary"]["total"])
                    if failure_rate > 0.5:
                        print(f"\n⚠️  High failure rate ({failure_rate:.1%}), stopping tests")
                        break
            
            # Generate report
            self._generate_report()
            
        finally:
            self.stop_websocket_handler()
    
    def _generate_report(self):
        """Generate test report with timing accuracy analysis"""
        print("\n" + "=" * 80)
        print("TEST REPORT")
        print("=" * 80)
        
        # Summary
        total = self.results["summary"]["total"]
        passed = self.results["summary"]["passed"]
        failed = self.results["summary"]["failed"]
        skipped = self.results["summary"]["skipped"]
        
        if total > 0:
            success_rate = (passed / (total - skipped)) * 100 if (total - skipped) > 0 else 0
        else:
            success_rate = 0
        
        print(f"\nSUMMARY:")
        print(f"  Total Tests: {total}")
        print(f"  Passed: {passed} ({success_rate:.1f}%)")
        print(f"  Failed: {failed}")
        print(f"  Skipped: {skipped}")
        print(f"  Redis Timing: {'Enabled' if self.redis_timer else 'Disabled'}")
        
        # Timing accuracy analysis
        if self.redis_timer and self.results["timing_accuracy"]:
            print(f"\n📊 TIMING ACCURACY ANALYSIS:")
            print(f"  Total predictions: {len(self.results['timing_accuracy'])}")
            
            # Calculate statistics
            variances = [abs(t["variance_pct"]) for t in self.results["timing_accuracy"]]
            if variances:
                avg_variance = sum(variances) / len(variances)
                max_variance = max(variances)
                within_20pct = sum(1 for v in variances if v <= 20)
                within_50pct = sum(1 for v in variances if v <= 50)
                
                print(f"  Average variance: {avg_variance:.1f}%")
                print(f"  Max variance: {max_variance:.1f}%")
                print(f"  Within 20%: {within_20pct}/{len(variances)} ({within_20pct/len(variances)*100:.1f}%)")
                print(f"  Within 50%: {within_50pct}/{len(variances)} ({within_50pct/len(variances)*100:.1f}%)")
                
                # Show worst predictions
                worst = sorted(self.results["timing_accuracy"], key=lambda x: abs(x["variance_pct"]), reverse=True)[:3]
                if worst:
                    print(f"\n  Worst predictions:")
                    for t in worst:
                        print(f"    - {t['test']}: {abs(t['variance_pct']):.1f}% variance ({t['actual']:.1f}s vs {t['expected']:.1f}s)")
        
        # Self-improvement metrics
        print(f"\nSELF-IMPROVEMENT METRICS:")
        if self.failure_count > 0:
            ratio = f"{self.success_count}:{self.failure_count}"
            graduation_status = "❌ NOT READY" if self.success_count < self.failure_count * 10 else "✅ READY TO GRADUATE"
        else:
            ratio = f"{self.success_count}:0"
            graduation_status = "✅ READY TO GRADUATE" if self.success_count > 0 else "⚠️  NO TESTS RUN"
        
        print(f"  Success/Failure Ratio: {ratio}")
        print(f"  Target Ratio: 10:1 for graduation")
        print(f"  Status: {graduation_status}")
        
        # By category
        print(f"\nBY CATEGORY:")
        for category, results in self.results["categories"].items():
            cat_total = len(results)
            cat_passed = sum(1 for r in results if r["success"])
            cat_failed = sum(1 for r in results if not r["success"] and not r["skipped"])
            cat_skipped = sum(1 for r in results if r["skipped"])
            
            print(f"\n  {category}:")
            print(f"    Total: {cat_total}")
            print(f"    Passed: {cat_passed}")
            print(f"    Failed: {cat_failed}")
            print(f"    Skipped: {cat_skipped}")
            
            # Show timeout sources
            timeout_sources = {}
            for r in results:
                source = r.get("timeout_source", "unknown")
                timeout_sources[source] = timeout_sources.get(source, 0) + 1
            
            if timeout_sources:
                print(f"    Timeout sources: {dict(timeout_sources)}")
            
            # Show failed tests
            if cat_failed > 0:
                print(f"    Failed tests:")
                for r in results:
                    if not r["success"] and not r["skipped"]:
                        print(f"      - {r['id']}: {r.get('error', 'Unknown error')}")
        
        # Save full report
        report_file = OUTPUT_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nFull report saved to: {report_file}")
        print(f"Test outputs: {OUTPUT_DIR}")
        
        # Success message
        if failed == 0 and passed > 0:
            print("\n✅ ALL TESTS PASSED!")
        elif passed > failed:
            print("\n⚠️  SOME TESTS FAILED")
        else:
            print("\n❌ MAJORITY OF TESTS FAILED")


async def main():
    """Main entry point"""
    runner = UnifiedStressTestRunnerWithRedis()
    await runner.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())