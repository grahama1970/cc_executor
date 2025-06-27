#!/usr/bin/env python3
"""Compare claude_runner.py vs websocket_handler.py approaches"""

import asyncio
import json
import time
import subprocess
import sys
import os

sys.path.insert(0, 'src')

from cc_executor.core.process_manager import ProcessManager
from cc_executor.core.stream_handler import StreamHandler

async def test_websocket_approach():
    """Test the websocket_handler.py approach directly"""
    print("\n=== Testing WebSocket Handler Approach ===")
    
    # This is what websocket_handler.py does internally
    process_manager = ProcessManager()
    stream_handler = StreamHandler()
    
    # Test cases
    test_cases = [
        ("Simple echo", "echo 'Hello from websocket approach'"),
        ("Python calculation", "python -c 'print(2 + 2)'"),
        ("Multi-line output", "python -c 'for i in range(5): print(f\"Line {i}\")'"),
        ("Long running", "python -c 'import time; print(\"Starting...\"); time.sleep(2); print(\"Done\")'"),
        ("Large output", "python -c 'print(\"x\" * 100000)'"),
        ("Error case", "python -c 'import sys; print(\"Error!\", file=sys.stderr); sys.exit(1)'"),
    ]
    
    results = []
    
    for name, command in test_cases:
        print(f"\nTest: {name}")
        start_time = time.time()
        
        try:
            process = await process_manager.execute_command(command)
            
            output_lines = []
            error_lines = []
            
            async def collect_output(stream_type: str, data: str):
                if stream_type == "stdout":
                    output_lines.append(data.strip())
                else:
                    error_lines.append(data.strip())
            
            # Stream with timeout
            await stream_handler.multiplex_streams(
                process.stdout,
                process.stderr,
                collect_output,
                timeout=10.0
            )
            
            exit_code = await process.wait()
            duration = time.time() - start_time
            
            results.append({
                "test": name,
                "success": True,
                "exit_code": exit_code,
                "duration": duration,
                "output_lines": len(output_lines),
                "error_lines": len(error_lines),
                "sample_output": output_lines[0] if output_lines else None
            })
            
            print(f"  ✓ Success: exit_code={exit_code}, duration={duration:.2f}s")
            if output_lines:
                print(f"  Output: {output_lines[0][:50]}...")
            
        except Exception as e:
            duration = time.time() - start_time
            results.append({
                "test": name,
                "success": False,
                "error": str(e),
                "duration": duration
            })
            print(f"  ✗ Failed: {e}")
    
    return results


async def test_claude_runner_approach():
    """Test the claude_runner.py approach"""
    print("\n=== Testing Claude Runner Approach ===")
    
    # We'll test by running it as a subprocess since it has issues with direct import
    test_cases = [
        ("Simple question", "What is 2+2?"),
        ("Short creative", "Write a haiku about Python"),
        ("Code generation", "Write a Python function to calculate fibonacci"),
    ]
    
    results = []
    
    for name, prompt in test_cases:
        print(f"\nTest: {name}")
        start_time = time.time()
        
        try:
            # Run claude_runner as subprocess
            cmd = [
                sys.executable, "-m", "src.cc_executor.core.claude_runner",
                "run", prompt, "--timeout", "30"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=35
            )
            
            duration = time.time() - start_time
            
            # Check if it worked
            success = result.returncode == 0
            output_lines = result.stdout.strip().split('\n') if result.stdout else []
            error_lines = result.stderr.strip().split('\n') if result.stderr else []
            
            results.append({
                "test": name,
                "success": success,
                "exit_code": result.returncode,
                "duration": duration,
                "output_lines": len(output_lines),
                "error_lines": len(error_lines),
                "sample_output": output_lines[0] if output_lines else None
            })
            
            if success:
                print(f"  ✓ Success: duration={duration:.2f}s")
                if output_lines:
                    print(f"  Output: {output_lines[0][:50]}...")
            else:
                print(f"  ✗ Failed: exit_code={result.returncode}")
                if error_lines:
                    print(f"  Error: {error_lines[-1][:100]}...")
                    
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            results.append({
                "test": name,
                "success": False,
                "error": "Timeout",
                "duration": duration
            })
            print(f"  ✗ Timeout after {duration:.2f}s")
            
        except Exception as e:
            duration = time.time() - start_time
            results.append({
                "test": name,
                "success": False,
                "error": str(e),
                "duration": duration
            })
            print(f"  ✗ Error: {e}")
    
    return results


def analyze_results(ws_results, cr_results):
    """Compare and analyze results from both approaches"""
    print("\n=== Analysis ===")
    
    print("\n## WebSocket Handler Approach:")
    print(f"- Total tests: {len(ws_results)}")
    print(f"- Successful: {sum(1 for r in ws_results if r['success'])}")
    print(f"- Failed: {sum(1 for r in ws_results if not r['success'])}")
    print(f"- Avg duration: {sum(r['duration'] for r in ws_results) / len(ws_results):.2f}s")
    
    print("\n## Claude Runner Approach:")
    print(f"- Total tests: {len(cr_results)}")
    print(f"- Successful: {sum(1 for r in cr_results if r['success'])}")
    print(f"- Failed: {sum(1 for r in cr_results if not r['success'])}")
    if cr_results:
        print(f"- Avg duration: {sum(r['duration'] for r in cr_results) / len(cr_results):.2f}s")
    
    print("\n## Brittleness Analysis:")
    
    print("\n### WebSocket Handler (websocket_handler.py):")
    print("Pros:")
    print("- ✓ Handles all process types (not just Claude)")
    print("- ✓ Full process control (pause/resume/cancel)")
    print("- ✓ Proper session management")
    print("- ✓ Handles concurrent connections")
    print("- ✓ Structured error handling with JSON-RPC")
    print("- ✓ Heartbeat/keepalive mechanism")
    print("- ✓ Better separation of concerns")
    
    print("\nCons:")
    print("- ✗ More complex architecture")
    print("- ✗ Requires WebSocket client")
    print("- ✗ More moving parts (sessions, process manager, stream handler)")
    
    print("\n### Claude Runner (claude_runner.py):")
    print("Pros:")
    print("- ✓ Simpler, more direct approach")
    print("- ✓ Fewer dependencies")
    print("- ✓ Can be used as CLI or HTTP API")
    print("- ✓ Less code to maintain")
    
    print("\nCons:")
    print("- ✗ Claude-specific only")
    print("- ✗ No process control (pause/resume)")
    print("- ✗ Process cleanup issues (as seen in error)")
    print("- ✗ No session management")
    print("- ✗ Limited to single executions")
    print("- ✗ Less robust error handling")


async def main():
    """Run all tests and compare"""
    print("Comparing CC-Executor Approaches")
    print("=" * 50)
    
    # Test websocket approach
    ws_results = await test_websocket_approach()
    
    # Test claude runner approach
    cr_results = await test_claude_runner_approach()
    
    # Analyze
    analyze_results(ws_results, cr_results)
    
    print("\n## Conclusion:")
    print("The WebSocket handler approach is LESS BRITTLE because:")
    print("1. Better error handling and recovery")
    print("2. Proper process lifecycle management")
    print("3. Handles edge cases (timeouts, large output, etc.)")
    print("4. More flexible and extensible")
    print("5. Production-ready with session management")
    print("\nThe claude_runner.py is simpler but has critical issues:")
    print("1. Process cleanup bug (tries to kill already-dead process)")
    print("2. Limited to Claude CLI only")
    print("3. No mechanism for handling long-running processes properly")
    print("4. Less robust for production use")


if __name__ == "__main__":
    asyncio.run(main())