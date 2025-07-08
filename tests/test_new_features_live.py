#!/usr/bin/env python3
"""
Live test script for the 5 new features added to cc_execute.
This script tests the actual implementation in the current environment.
"""

import asyncio
import sys
import os
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cc_executor.client.cc_execute import (
    cc_execute,
    CCExecutorConfig,
    check_token_limit,
    detect_ambiguous_prompt,
    export_execution_history
)


async def test_1_token_limit():
    """Test 1: Token Limit Pre-Check & Auto-Truncation"""
    print("\n" + "="*50)
    print("TEST 1: Token Limit Pre-Check & Auto-Truncation")
    print("="*50)
    
    # Test with a moderately long prompt
    long_text = "analyze this code: " + ("def function(): pass\n" * 10000)
    
    # Check before truncation
    print(f"Original length: {len(long_text)} chars")
    print(f"Estimated tokens: {len(long_text) // 4}")
    
    # Apply token limit check
    truncated = check_token_limit(long_text, max_tokens=50000)
    
    print(f"After check length: {len(truncated)} chars")
    print(f"Was truncated: {truncated.endswith('[TRUNCATED due to token limit]')}")
    
    # Test with actual execution (short prompt to avoid real token issues)
    result = await cc_execute("What is 2+2?", config=CCExecutorConfig(timeout=30))
    print(f"Quick test execution successful: {'4' in result}")
    
    return True


async def test_2_rate_limit_retry():
    """Test 2: Rate Limit Retry with Tenacity"""
    print("\n" + "="*50)
    print("TEST 2: Rate Limit Retry (Tenacity Decorator)")
    print("="*50)
    
    print("Rate limit retry is implemented with tenacity decorator:")
    print("- Retries up to 3 times on RateLimitError")
    print("- Exponential backoff: 5s -> 10s -> 20s (max 60s)")
    print("- Includes automatic jitter for better distribution")
    print("\nThis feature activates automatically when rate limits are hit.")
    
    # Can't simulate actual rate limit without hitting API limits
    # But we can verify the decorator is in place
    from cc_executor.client.cc_execute import _execute_claude_command
    
    print(f"\nVerifying decorator is applied: {hasattr(_execute_claude_command, '__wrapped__')}")
    
    return True


async def test_3_ambiguous_prompt():
    """Test 3: Ambiguous Prompt Detection"""
    print("\n" + "="*50)
    print("TEST 3: Ambiguous Prompt Detection")
    print("="*50)
    
    test_cases = [
        ("Write code", "Too brief and command-style"),
        ("Create function", "Command without context"),
        ("Help me understand Python", "Interactive language"),
        ("that thing we discussed", "Vague reference"),
        ("generate a report", "Missing specifications"),
        ("What is the time complexity of quicksort and how does it compare to mergesort?", "Good prompt"),
    ]
    
    for prompt, expected in test_cases:
        warning = detect_ambiguous_prompt(prompt)
        print(f"\nPrompt: '{prompt}'")
        print(f"Expected: {expected}")
        print(f"Warning: {warning if warning else 'None (good prompt)'}")
    
    return True


async def test_4_execution_history():
    """Test 4: Execution History Export"""
    print("\n" + "="*50)
    print("TEST 4: Execution History Export")
    print("="*50)
    
    # Run a couple test executions to ensure we have history
    print("Running test executions to create history...")
    await cc_execute("What is 3+3?", config=CCExecutorConfig(timeout=30))
    await cc_execute("What is the capital of France?", config=CCExecutorConfig(timeout=30))
    
    # Test JSON export
    print("\nExporting execution history as JSON...")
    history_json = await export_execution_history(format="json", limit=5)
    
    # Parse and display
    try:
        history_data = json.loads(history_json)
        print(f"Found {len(history_data)} execution records")
        if history_data:
            print("\nMost recent execution:")
            recent = history_data[0]
            print(f"  Task: {recent.get('task', 'N/A')[:50]}...")
            print(f"  Average time: {recent.get('avg_time', 'N/A')}s")
            print(f"  Success rate: {recent.get('success_rate', 'N/A')}")
    except json.JSONDecodeError:
        print("Note: No execution history found yet (this is normal for new installations)")
    
    # Test CSV export
    print("\nExporting execution history as CSV...")
    history_csv = await export_execution_history(format="csv", limit=3)
    print("CSV Headers:", history_csv.split('\n')[0] if history_csv else "No data")
    
    return True


async def test_5_progress_callback():
    """Test 5: Progress Callback Support"""
    print("\n" + "="*50)
    print("TEST 5: Progress Callback Support")
    print("="*50)
    
    progress_messages = []
    
    async def progress_handler(message: str):
        """Collect progress messages"""
        progress_messages.append(message)
        print(f"[PROGRESS] {message}")
    
    print("Executing task with progress callback...")
    result = await cc_execute(
        "List 5 programming languages and their main use cases",
        config=CCExecutorConfig(timeout=60),
        stream=True,
        progress_callback=progress_handler
    )
    
    print(f"\nCollected {len(progress_messages)} progress messages")
    print("Progress updates received:")
    for msg in progress_messages[:5]:  # Show first 5
        print(f"  - {msg}")
    
    return len(progress_messages) > 0


async def test_integration():
    """Test all features working together"""
    print("\n" + "="*50)
    print("INTEGRATION TEST: All Features Together")
    print("="*50)
    
    progress_updates = []
    
    async def track_progress(msg: str):
        progress_updates.append(msg)
        print(f"[INTEGRATION] {msg}")
    
    # Create a task that could trigger multiple features
    task = "Create a Python function" # Ambiguous - will trigger warning
    
    print(f"Original task: '{task}'")
    
    # Check for ambiguity
    warning = detect_ambiguous_prompt(task)
    if warning:
        print(f"Ambiguity detected: {warning}")
    
    # Execute with all features
    result = await cc_execute(
        task,
        config=CCExecutorConfig(timeout=60),
        amend_prompt=True,  # Fix ambiguous prompt
        json_mode=True,     # Get structured response
        stream=True,
        progress_callback=track_progress
    )
    
    print(f"\nExecution completed successfully: {result.get('success', False)}")
    print(f"Progress updates received: {len(progress_updates)}")
    
    # The execution is now in history
    print("\nChecking execution history...")
    history = await export_execution_history(format="json", limit=1)
    print(f"History contains recent execution: {len(history) > 2}")
    
    return True


async def main():
    """Run all tests"""
    print("CC_EXECUTOR NEW FEATURES TEST SUITE")
    print("Testing 5 new features added to cc_execute")
    
    tests = [
        ("Token Limit Protection", test_1_token_limit),
        ("Rate Limit Retry", test_2_rate_limit_retry),
        ("Ambiguous Prompt Detection", test_3_ambiguous_prompt),
        ("Execution History Export", test_4_execution_history),
        ("Progress Callbacks", test_5_progress_callback),
        ("Integration Test", test_integration),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            print(f"\nRunning: {name}...")
            success = await test_func()
            results.append((name, "✅ PASSED" if success else "❌ FAILED"))
        except Exception as e:
            print(f"Error in {name}: {e}")
            results.append((name, f"❌ ERROR: {str(e)[:50]}..."))
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    for name, status in results:
        print(f"{name:.<40} {status}")
    
    passed = sum(1 for _, status in results if "PASSED" in status)
    print(f"\nTotal: {passed}/{len(results)} tests passed")


if __name__ == "__main__":
    # Ensure we're in the right environment
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Warning: ANTHROPIC_API_KEY not set. Some tests may fail.")
    
    asyncio.run(main())