#!/usr/bin/env python3
"""
Adaptive stress test runner that handles errors gracefully.

This enhanced version:
1. Detects token limit and rate limit errors via WebSocket notifications
2. Automatically retries with more concise prompts
3. Splits large requests into smaller chunks
4. Implements exponential backoff for rate limits
"""

import asyncio
import json
import os
import sys
import time
import uuid
import websockets
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(project_root, 'src'))

# Import Redis timing module
from cc_executor.prompts.redis_task_timing import RedisTaskTimer


class AdaptiveStressTestRunner:
    """Runs stress tests with adaptive error handling"""
    
    def __init__(self, use_token_aware=True):
        self.ws_port = 8006 if use_token_aware else 8005
        self.ws_url = f"ws://localhost:{self.ws_port}/ws"
        self.use_token_aware = use_token_aware
        self.results = []
        self.retry_strategies = {
            "token_limit": self._handle_token_limit,
            "rate_limit": self._handle_rate_limit,
            "auth_error": self._handle_auth_error,
            "service_error": self._handle_service_error
        }
        
    async def run_test_with_retry(self, test: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        """Run a test with intelligent retry logic."""
        
        test_id = test.get("id", "unknown")
        test_name = test.get("name", "unknown")
        original_request = test.get("natural_language_request", "")
        
        print(f"\n{'='*60}")
        print(f"Test: {test_id} - {test_name}")
        print(f"Original request: {original_request[:100]}...")
        
        # Track attempts
        attempts = []
        current_request = original_request
        retry_count = 0
        
        while retry_count <= max_retries:
            print(f"\n📝 Attempt {retry_count + 1}/{max_retries + 1}")
            
            # Build command
            command = self._build_command(test, current_request)
            
            # Execute and monitor
            result = await self._execute_with_monitoring(
                test_id=test_id,
                command=command,
                expected_patterns=test.get("verification", {}).get("expected_patterns", [])
            )
            
            # Record attempt
            attempt = {
                "attempt_number": retry_count + 1,
                "request": current_request,
                "result": result,
                "duration": result.get("duration", 0),
                "success": result.get("success", False),
                "error_type": result.get("error_type"),
                "error_message": result.get("error_message")
            }
            attempts.append(attempt)
            
            # Check if successful
            if result["success"]:
                print(f"✅ Test passed on attempt {retry_count + 1}")
                break
                
            # Check if we should retry
            error_type = result.get("error_type")
            if error_type and error_type in self.retry_strategies and retry_count < max_retries:
                print(f"\n🔄 Applying retry strategy for {error_type}")
                
                # Apply appropriate retry strategy
                strategy = self.retry_strategies[error_type]
                new_request = await strategy(
                    original_request=original_request,
                    current_request=current_request,
                    error_data=result.get("error_data", {}),
                    attempt_number=retry_count + 1
                )
                
                if new_request != current_request:
                    current_request = new_request
                    retry_count += 1
                    
                    # Add delay between retries
                    delay = min(2 ** retry_count, 30)  # Exponential backoff, max 30s
                    print(f"⏳ Waiting {delay}s before retry...")
                    await asyncio.sleep(delay)
                else:
                    print("❌ No retry strategy produced a different request")
                    break
            else:
                print(f"❌ No retry strategy available for error type: {error_type}")
                break
                
        # Compile final result
        final_result = {
            "test_id": test_id,
            "test_name": test_name,
            "original_request": original_request,
            "attempts": attempts,
            "total_attempts": len(attempts),
            "final_success": attempts[-1]["success"] if attempts else False,
            "total_duration": sum(a["duration"] for a in attempts),
            "retry_strategies_used": [a.get("error_type") for a in attempts[:-1] if a.get("error_type")]
        }
        
        return final_result
    
    def _build_command(self, test: Dict[str, Any], request: str) -> str:
        """Build Claude command with current request."""
        metatags = test.get("metatags", "")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        command = (
            f'claude -p "[marker:{test["id"]}_{timestamp}] {metatags} {request}" '
            f'--output-format stream-json '
            f'--dangerously-skip-permissions '
            f'--allowedTools none '
            f'--verbose'
        )
        
        return command
    
    async def _execute_with_monitoring(
        self, 
        test_id: str, 
        command: str, 
        expected_patterns: List[str]
    ) -> Dict[str, Any]:
        """Execute command and monitor for errors via WebSocket."""
        
        result = {
            "success": False,
            "duration": 0,
            "output": [],
            "patterns_found": [],
            "error_type": None,
            "error_message": None,
            "error_data": {}
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
                print(f"📤 Command sent (length: {len(command)})")
                
                # Monitor for responses and errors
                output_lines = []
                patterns_found = []
                error_detected = False
                
                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=600.0)
                        data = json.loads(response)
                        
                        method = data.get("method", "")
                        
                        # Handle different notification types
                        if method == "heartbeat":
                            print("💓 Heartbeat received")
                            
                        elif method == "process.output":
                            output = data.get("params", {}).get("data", "")
                            if output:
                                output_lines.append(output)
                                
                                # Check patterns
                                for pattern in expected_patterns:
                                    if pattern.lower() in output.lower() and pattern not in patterns_found:
                                        patterns_found.append(pattern)
                                        print(f"  ✓ Found pattern: {pattern}")
                                        
                        elif method.startswith("error."):
                            # Error detected via WebSocket notification
                            error_detected = True
                            error_params = data.get("params", {})
                            
                            if method == "error.token_limit_exceeded":
                                result["error_type"] = "token_limit"
                                result["error_message"] = error_params.get("message", "Token limit exceeded")
                                result["error_data"] = error_params
                                print(f"🚨 Token limit exceeded: {error_params.get('limit', 'unknown')} tokens")
                                
                            elif method == "error.rate_limit_exceeded":
                                result["error_type"] = "rate_limit"
                                result["error_message"] = error_params.get("message", "Rate limit exceeded")
                                result["error_data"] = error_params
                                print(f"🚨 Rate limit exceeded: {error_params.get('error_type', 'unknown')}")
                                
                            elif method == "error.authentication_failed":
                                result["error_type"] = "auth_error"
                                result["error_message"] = error_params.get("message", "Authentication failed")
                                result["error_data"] = error_params
                                print(f"🚨 Authentication error")
                                
                            elif method == "error.service_unavailable":
                                result["error_type"] = "service_error"
                                result["error_message"] = error_params.get("message", "Service unavailable")
                                result["error_data"] = error_params
                                print(f"🚨 Service unavailable")
                                
                        elif method == "process.completed":
                            exit_code = data.get("params", {}).get("exit_code", -1)
                            status = data.get("params", {}).get("status", "unknown")
                            
                            result["exit_code"] = exit_code
                            result["status"] = status
                            
                            # Success if exit code 0 and enough patterns found
                            if exit_code == 0 and not error_detected:
                                if len(expected_patterns) == 0 or len(patterns_found) >= len(expected_patterns) * 0.5:
                                    result["success"] = True
                                    
                            print(f"📊 Process completed: {status} (exit code: {exit_code})")
                            break
                            
                    except asyncio.TimeoutError:
                        print("⏱️ Timeout waiting for response")
                        result["error_type"] = "timeout"
                        result["error_message"] = "Process timed out"
                        break
                        
                # Calculate final metrics
                result["duration"] = time.time() - start_time
                result["output"] = output_lines
                result["patterns_found"] = patterns_found
                
        except Exception as e:
            result["duration"] = time.time() - start_time
            result["error_type"] = "exception"
            result["error_message"] = str(e)
            print(f"❌ Exception: {e}")
            
        return result
    
    # Retry strategies for different error types
    
    async def _handle_token_limit(
        self, 
        original_request: str, 
        current_request: str, 
        error_data: Dict[str, Any],
        attempt_number: int
    ) -> str:
        """Handle token limit by making request more concise."""
        
        limit = error_data.get("limit", 32000)
        estimated_tokens = error_data.get("estimated_tokens", 0)
        
        print(f"\n📝 Token limit strategy:")
        print(f"   Limit: {limit:,} tokens")
        print(f"   Estimated used: {estimated_tokens:,} tokens")
        
        # Progressive strategies based on attempt number
        if attempt_number == 1:
            # First retry: Ask for a more concise version
            print("   Strategy: Request concise version")
            return f"{current_request} Please be concise and limit your response to essential information only."
            
        elif attempt_number == 2:
            # Second retry: Specify exact limits
            target_words = (limit // 5)  # Rough estimate: 1 token ≈ 0.75 words
            print(f"   Strategy: Specify word limit ({target_words:,} words)")
            return f"{original_request} Please limit your response to approximately {target_words} words."
            
        elif attempt_number == 3:
            # Third retry: Request summary or outline only
            print("   Strategy: Request outline/summary only")
            if "guide" in original_request.lower() or "comprehensive" in original_request.lower():
                return f"Create a detailed outline (not full content) for: {original_request}"
            elif "story" in original_request.lower():
                return f"Write a 500-word summary of: {original_request}"
            else:
                return f"Provide a brief summary of: {original_request}"
                
        return current_request
    
    async def _handle_rate_limit(
        self, 
        original_request: str, 
        current_request: str, 
        error_data: Dict[str, Any],
        attempt_number: int
    ) -> str:
        """Handle rate limit - usually just need to wait."""
        
        error_type = error_data.get("error_type", "rate_limit")
        
        print(f"\n⏳ Rate limit strategy:")
        print(f"   Error type: {error_type}")
        
        if error_type == "rate_limit_429":
            # Standard rate limit - exponential backoff handled by caller
            print("   Strategy: Exponential backoff (handled by retry logic)")
            return current_request  # Same request, just wait
            
        elif error_type == "rate_limit":
            # Usage limit reached - might need different approach
            reset_timestamp = error_data.get("reset_timestamp")
            if reset_timestamp:
                reset_time = datetime.fromtimestamp(reset_timestamp / 1000)
                print(f"   Reset time: {reset_time}")
                
            # Can't really retry with same API key
            print("   Strategy: Cannot retry - usage limit reached")
            return current_request  # Will fail again, but documents the issue
            
        return current_request
    
    async def _handle_auth_error(
        self, 
        original_request: str, 
        current_request: str, 
        error_data: Dict[str, Any],
        attempt_number: int
    ) -> str:
        """Handle authentication error - can't retry with same request."""
        
        print(f"\n🔐 Authentication error strategy:")
        print("   Cannot retry - authentication credentials needed")
        
        # Can't fix auth errors by changing the request
        return current_request
    
    async def _handle_service_error(
        self, 
        original_request: str, 
        current_request: str, 
        error_data: Dict[str, Any],
        attempt_number: int
    ) -> str:
        """Handle service unavailable - retry with same request after delay."""
        
        print(f"\n🔧 Service error strategy:")
        print("   Strategy: Retry with exponential backoff")
        
        # Same request, just need to wait
        return current_request
    
    async def run_adaptive_tests(self, test_file: str):
        """Run all tests with adaptive error handling."""
        
        print("=" * 80)
        print("ADAPTIVE STRESS TEST RUNNER")
        print("=" * 80)
        print(f"WebSocket URL: {self.ws_url}")
        print(f"Token-aware handler: {self.use_token_aware}")
        print()
        
        # Load test definitions
        if not os.path.exists(test_file):
            print(f"❌ Test file not found: {test_file}")
            return
            
        with open(test_file) as f:
            test_data = json.load(f)
            
        # Run tests
        all_results = []
        categories = test_data.get("categories", {})
        
        for category_name, category_data in categories.items():
            print(f"\n{'='*80}")
            print(f"CATEGORY: {category_name}")
            print(f"Description: {category_data.get('description', 'N/A')}")
            print("=" * 80)
            
            tasks = category_data.get("tasks", [])
            
            for task in tasks:
                # Skip known problematic tests
                if task.get("id") in ["simple_1", "simple_2"]:
                    print(f"\n⚠️ Skipping {task['id']} - Known Claude CLI hang issue")
                    continue
                    
                # Run with adaptive retry
                result = await self.run_test_with_retry(task)
                all_results.append(result)
                
                # Print summary
                print(f"\n📊 Test Summary:")
                print(f"   Total attempts: {result['total_attempts']}")
                print(f"   Final success: {result['final_success']}")
                print(f"   Total duration: {result['total_duration']:.1f}s")
                if result['retry_strategies_used']:
                    print(f"   Retry strategies: {', '.join(result['retry_strategies_used'])}")
                    
                # Small delay between tests
                await asyncio.sleep(2)
                
        # Generate final report
        self._generate_report(all_results)
        
    def _generate_report(self, results: List[Dict[str, Any]]):
        """Generate comprehensive report of adaptive test results."""
        
        print("\n" + "=" * 80)
        print("ADAPTIVE TEST REPORT")
        print("=" * 80)
        
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r["final_success"])
        total_attempts = sum(r["total_attempts"] for r in results)
        
        print(f"\nOVERALL STATISTICS:")
        print(f"  Total tests: {total_tests}")
        print(f"  Successful: {successful_tests} ({successful_tests/total_tests*100:.1f}%)")
        print(f"  Total attempts: {total_attempts}")
        print(f"  Average attempts per test: {total_attempts/total_tests:.1f}")
        
        # Analyze retry strategies
        strategy_usage = {}
        for result in results:
            for strategy in result["retry_strategies_used"]:
                strategy_usage[strategy] = strategy_usage.get(strategy, 0) + 1
                
        if strategy_usage:
            print(f"\nRETRY STRATEGY USAGE:")
            for strategy, count in sorted(strategy_usage.items(), key=lambda x: x[1], reverse=True):
                print(f"  {strategy}: {count} times")
                
        # Show detailed results for tests that required retries
        retry_tests = [r for r in results if r["total_attempts"] > 1]
        if retry_tests:
            print(f"\nTESTS REQUIRING RETRIES ({len(retry_tests)}):")
            for result in retry_tests:
                print(f"\n  {result['test_id']} - {result['test_name']}:")
                print(f"    Attempts: {result['total_attempts']}")
                print(f"    Success: {result['final_success']}")
                print(f"    Strategies: {', '.join(result['retry_strategies_used'])}")
                
                # Show each attempt
                for i, attempt in enumerate(result["attempts"]):
                    print(f"    Attempt {i+1}:")
                    print(f"      Duration: {attempt['duration']:.1f}s")
                    print(f"      Success: {attempt['success']}")
                    if attempt.get("error_type"):
                        print(f"      Error: {attempt['error_type']} - {attempt.get('error_message', 'N/A')}")
                    if i < len(result["attempts"]) - 1:
                        print(f"      Modified request: {attempt['request'][:100]}...")
                        
        # Save detailed report
        report_file = f"adaptive_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                "summary": {
                    "total_tests": total_tests,
                    "successful_tests": successful_tests,
                    "success_rate": successful_tests/total_tests if total_tests > 0 else 0,
                    "total_attempts": total_attempts,
                    "average_attempts": total_attempts/total_tests if total_tests > 0 else 0,
                    "strategy_usage": strategy_usage
                },
                "detailed_results": results
            }, f, indent=2)
            
        print(f"\n📄 Detailed report saved to: {report_file}")


async def main():
    """Main entry point"""
    # Use the standard stress test file
    test_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "configs/basic.json"
    )
    
    runner = AdaptiveStressTestRunner(use_token_aware=True)
    await runner.run_adaptive_tests(test_file)


if __name__ == "__main__":
    asyncio.run(main())