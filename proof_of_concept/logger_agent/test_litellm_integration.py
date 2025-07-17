#!/usr/bin/env python3
"""
test_litellm_integration.py - Test the LiteLLM integration for Logger Agent

Tests the complete flow of sending events with AI-powered summaries.
"""

import json
import subprocess
import time
import sys
from pathlib import Path

def run_test(test_name, event_data, extra_args=[]):
    """Run a single test case."""
    print(f"\n{'='*60}")
    print(f"Test: {test_name}")
    print(f"{'='*60}")
    
    # Prepare command
    cmd = [
        sys.executable,
        ".claude/hooks/send_event_litellm.py",
        "--source-app", "test",
        "--event-type", event_data.get("event_type", "PreToolUse"),
        "--server-url", "http://localhost:8002/events"
    ] + extra_args
    
    # Prepare input data
    input_data = {
        "tool_name": event_data.get("tool_name", "Unknown"),
        "session_id": event_data.get("session_id", "test123"),
        **event_data.get("payload", {})
    }
    
    print(f"Command: {' '.join(cmd)}")
    print(f"Input: {json.dumps(input_data, indent=2)}")
    
    # Run the command
    try:
        result = subprocess.run(
            cmd,
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=10
        )
        
        print(f"\nReturn code: {result.returncode}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Errors: {result.stderr}")
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("ERROR: Command timed out")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    """Run all test cases."""
    print("Testing LiteLLM Integration for Logger Agent")
    print("=" * 60)
    
    # Check if API server is running
    print("Checking API server...")
    try:
        import urllib.request
        response = urllib.request.urlopen("http://localhost:8002/health", timeout=2)
        if response.status == 200:
            print("✅ API server is running")
        else:
            print("❌ API server returned unexpected status")
            return 1
    except Exception as e:
        print(f"❌ API server not accessible: {e}")
        print("Please run: ./scripts/start_dashboard_background.sh")
        return 1
    
    # Test cases
    tests = [
        # Basic event without summary
        {
            "name": "Basic PreToolUse event",
            "data": {
                "event_type": "PreToolUse",
                "tool_name": "Bash",
                "session_id": "test_basic",
                "payload": {"command": "ls -la"}
            },
            "args": []
        },
        
        # Event with AI summary
        {
            "name": "PreToolUse with AI summary",
            "data": {
                "event_type": "PreToolUse",
                "tool_name": "Bash",
                "session_id": "test_summary",
                "payload": {"command": "find /tmp -name '*.log' -mtime +7 -delete"}
            },
            "args": ["--summarize"]
        },
        
        # PostToolUse event
        {
            "name": "PostToolUse event",
            "data": {
                "event_type": "PostToolUse",
                "tool_name": "Read",
                "session_id": "test_post",
                "payload": {
                    "file_path": "/home/user/test.py",
                    "result": "File contents here..."
                }
            },
            "args": []
        },
        
        # Stop event with summary
        {
            "name": "Stop event with completion message",
            "data": {
                "event_type": "Stop",
                "session_id": "test_stop",
                "payload": {
                    "duration": 45.2,
                    "success": True
                }
            },
            "args": ["--summarize"]
        },
        
        # Complex tool execution
        {
            "name": "Complex tool execution with summary",
            "data": {
                "event_type": "PreToolUse",
                "tool_name": "Edit",
                "session_id": "test_complex",
                "payload": {
                    "file_path": "/src/main.py",
                    "old_string": "def calculate():",
                    "new_string": "def calculate_total():",
                    "description": "Refactoring function name for clarity"
                }
            },
            "args": ["--summarize"]
        }
    ]
    
    # Run tests
    results = []
    for test_case in tests:
        success = run_test(
            test_case["name"],
            test_case["data"],
            test_case["args"]
        )
        results.append((test_case["name"], success))
        time.sleep(1)  # Small delay between tests
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())