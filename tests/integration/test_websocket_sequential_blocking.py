#!/usr/bin/env python3
"""
Test that WebSocket connections truly block and force sequential execution.

This is CRITICAL to the orchestrator pattern - without this blocking behavior,
tasks would execute in parallel and break dependencies.
"""

import asyncio
import time
import sys
from pathlib import Path
from typing import List, Dict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from cc_executor.client.client import WebSocketClient

class WebSocketBlockingTest:
    """Test WebSocket blocking behavior for sequential execution."""
    
    def __init__(self):
        self.execution_log: List[Dict] = []
        
    async def test_single_connection_blocks(self):
        """Test that a single WebSocket connection blocks until command completes."""
        print("=== Test 1: Single Connection Blocking ===")
        print("Verifying that WebSocket waits for command completion...\n")
        
        client = WebSocketClient()
        
        try:
            await client.connect()
            
            # Command that takes exactly 3 seconds
            command = "echo 'Starting 3 second task' && sleep 3 && echo 'Task complete'"
            
            start_time = time.time()
            print(f"Sending command at {start_time:.2f}")
            
            # This should block for ~3 seconds
            result = await client.execute_command(command)
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"Response received at {end_time:.2f}")
            print(f"Total duration: {duration:.2f} seconds")
            
            if result["success"]:
                print(f"Output: {result['output_data'].strip()}")
                
            # Verify it actually blocked for ~3 seconds
            if 2.5 <= duration <= 3.5:
                print("✅ VERIFIED: WebSocket connection blocked for command duration")
                return True
            else:
                print(f"❌ ERROR: Expected ~3s blocking, got {duration:.2f}s")
                return False
                
        finally:
            await client.disconnect()
            
    async def test_sequential_commands_block(self):
        """Test that sequential commands on same connection execute in order."""
        print("\n=== Test 2: Sequential Commands Block ===")
        print("Verifying commands execute sequentially, not in parallel...\n")
        
        client = WebSocketClient()
        
        try:
            await client.connect()
            
            commands = [
                ("echo 'Task 1 start' && sleep 2 && echo 'Task 1 end'", 2),
                ("echo 'Task 2 start' && sleep 1 && echo 'Task 2 end'", 1),
                ("echo 'Task 3 start' && echo 'Task 3 end'", 0),
            ]
            
            total_start = time.time()
            
            for i, (command, expected_duration) in enumerate(commands, 1):
                start = time.time()
                print(f"Executing command {i}...")
                
                result = await client.execute_command(command)
                
                end = time.time()
                duration = end - start
                
                self.execution_log.append({
                    "command": i,
                    "start": start - total_start,
                    "end": end - total_start,
                    "duration": duration,
                    "output": result.get("output_data", "").strip() if result["success"] else "FAILED"
                })
                
                print(f"  Duration: {duration:.2f}s")
                print(f"  Output: {self.execution_log[-1]['output']}")
                
            total_duration = time.time() - total_start
            print(f"\nTotal duration: {total_duration:.2f}s")
            
            # Should take at least 3 seconds (2+1+0)
            if total_duration >= 3.0:
                print("✅ VERIFIED: Commands executed sequentially (blocked properly)")
                
                # Verify order
                for i in range(len(self.execution_log) - 1):
                    current = self.execution_log[i]
                    next_cmd = self.execution_log[i + 1]
                    if next_cmd["start"] < current["end"]:
                        print(f"❌ ERROR: Command {i+2} started before command {i+1} finished!")
                        return False
                        
                print("✅ VERIFIED: Command order maintained")
                return True
            else:
                print(f"❌ ERROR: Commands may have run in parallel (only took {total_duration:.2f}s)")
                return False
                
        finally:
            await client.disconnect()
            
    async def test_multiple_clients_independent(self):
        """Test that multiple WebSocket clients can execute in parallel."""
        print("\n=== Test 3: Multiple Clients Independence ===")
        print("Verifying different clients don't block each other...\n")
        
        clients = [WebSocketClient() for _ in range(3)]
        
        try:
            # Connect all clients
            for i, client in enumerate(clients):
                await client.connect()
                print(f"Client {i+1} connected")
                
            # Define tasks for parallel execution
            async def run_client_task(client_id: int, client: WebSocketClient, duration: int):
                command = f"echo 'Client {client_id} start' && sleep {duration} && echo 'Client {client_id} end'"
                start = time.time()
                
                result = await client.execute_command(command)
                
                end = time.time()
                return {
                    "client": client_id,
                    "duration": end - start,
                    "expected": duration,
                    "success": result["success"],
                    "output": result.get("output_data", "").strip() if result["success"] else "FAILED"
                }
            
            # Run all clients in parallel
            start_time = time.time()
            print("\nExecuting commands on all clients simultaneously...")
            
            tasks = [
                run_client_task(1, clients[0], 2),
                run_client_task(2, clients[1], 2),
                run_client_task(3, clients[2], 2),
            ]
            
            results = await asyncio.gather(*tasks)
            
            total_duration = time.time() - start_time
            
            print(f"\nTotal duration: {total_duration:.2f}s")
            
            for result in results:
                print(f"Client {result['client']}: {result['duration']:.2f}s - {result['output']}")
                
            # If truly parallel, should take ~2 seconds, not 6
            if total_duration <= 3.0:
                print("✅ VERIFIED: Multiple clients can execute in parallel")
                return True
            else:
                print(f"❌ ERROR: Clients may be blocking each other (took {total_duration:.2f}s)")
                return False
                
        finally:
            for client in clients:
                await client.disconnect()
                
    async def test_command_output_order(self):
        """Test that output from commands maintains order."""
        print("\n=== Test 4: Output Order Preservation ===")
        print("Verifying output chunks arrive in correct order...\n")
        
        client = WebSocketClient()
        
        try:
            await client.connect()
            
            # Command that outputs numbered lines
            command = "for i in {1..5}; do echo \"Line $i\"; sleep 0.5; done"
            
            print("Executing command that outputs 5 lines with delays...")
            result = await client.execute_command(command)
            
            if result["success"]:
                output_lines = result["output_data"].strip().split('\n')
                print(f"Received {len(output_lines)} lines:")
                
                for line in output_lines:
                    print(f"  {line}")
                    
                # Verify order
                expected = ["Line 1", "Line 2", "Line 3", "Line 4", "Line 5"]
                if output_lines == expected:
                    print("✅ VERIFIED: Output order preserved correctly")
                    return True
                else:
                    print("❌ ERROR: Output order corrupted!")
                    print(f"Expected: {expected}")
                    print(f"Got: {output_lines}")
                    return False
            else:
                print(f"❌ Command failed: {result.get('error', 'Unknown error')}")
                return False
                
        finally:
            await client.disconnect()
            
    async def run_all_tests(self):
        """Run all WebSocket blocking tests."""
        print("=" * 80)
        print("WEBSOCKET SEQUENTIAL BLOCKING TEST SUITE")
        print("Verifying the foundation of the orchestrator pattern")
        print("=" * 80)
        
        test_results = {
            "single_connection_blocks": False,
            "sequential_commands_block": False,
            "multiple_clients_independent": False,
            "command_output_order": False
        }
        
        try:
            test_results["single_connection_blocks"] = await self.test_single_connection_blocks()
            test_results["sequential_commands_block"] = await self.test_sequential_commands_block()
            test_results["multiple_clients_independent"] = await self.test_multiple_clients_independent()
            test_results["command_output_order"] = await self.test_command_output_order()
            
        except Exception as e:
            print(f"\n❌ Test suite failed with error: {e}")
            import traceback
            traceback.print_exc()
            
        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        for test_name, passed in test_results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
            
        passed_count = sum(1 for passed in test_results.values() if passed)
        total_count = len(test_results)
        
        print(f"\nTotal: {passed_count}/{total_count} tests passed")
        
        if passed_count == total_count:
            print("\n🎉 ALL TESTS PASSED! WebSocket blocking behavior is correct!")
        else:
            print(f"\n⚠️  {total_count - passed_count} tests failed.")
            
        return passed_count == total_count


async def main():
    """Run the WebSocket blocking test suite."""
    # Check if server is running
    try:
        test_client = WebSocketClient()
        result = await test_client.execute_command("echo 'WebSocket test'", timeout=5)
        if not result["success"]:
            print(f"❌ WebSocket server not responding: {result.get('error', 'Unknown error')}")
            print("Please start the server first:")
            print("  cc-executor server start")
            return
    except Exception as e:
        print(f"❌ WebSocket server connection failed: {e}")
        print("Please start the server first:")
        print("  cc-executor server start")
        return
        
    test_suite = WebSocketBlockingTest()
    success = await test_suite.run_all_tests()
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())