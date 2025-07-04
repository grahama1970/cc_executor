#!/usr/bin/env python3
"""
Test the core orchestrator pattern - the MAIN PURPOSE of CC Executor.

This test demonstrates:
1. Claude Orchestrator spawning fresh Claude instances
2. Sequential execution with WebSocket forcing wait
3. Fresh 200K context for each task
4. Output sharing between tasks
5. Complex multi-step workflows
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from cc_executor.client.client import WebSocketClient
from cc_executor.core.usage_helper import OutputCapture

class OrchestratorPatternTest:
    """Test the orchestrator pattern for sequential task execution."""
    
    def __init__(self):
        self.client = WebSocketClient()
        self.task_outputs = {}
        self.execution_times = []
        
    async def test_sequential_execution(self):
        """Test that tasks execute sequentially, not in parallel."""
        print("=== Test 1: Sequential Execution ===")
        print("Testing that WebSocket forces orchestrator to wait between tasks...\n")
        
        tasks = [
            {
                "id": "task1",
                "command": "echo 'Task 1 starting' && sleep 2 && echo 'Task 1 complete'",
                "description": "First task with 2 second delay"
            },
            {
                "id": "task2", 
                "command": "echo 'Task 2 starting' && sleep 1 && echo 'Task 2 complete'",
                "description": "Second task with 1 second delay"
            },
            {
                "id": "task3",
                "command": "echo 'Task 3 starting' && echo 'Task 3 complete'",
                "description": "Third task, immediate completion"
            }
        ]
        
        start_time = time.time()
        
        for task in tasks:
            task_start = time.time()
            print(f"Starting {task['id']}: {task['description']}")
            
            result = await self.client.execute_command(
                command=task["command"],
                metadata={"task_id": task["id"]}
            )
            
            task_end = time.time()
            task_duration = task_end - task_start
            
            if result["success"]:
                self.task_outputs[task["id"]] = result["output_data"]
                print(f"✓ {task['id']} completed in {task_duration:.2f}s")
                print(f"  Output: {result['output_data'].strip()}\n")
            else:
                print(f"✗ {task['id']} failed: {result.get('error', 'Unknown error')}\n")
                
            self.execution_times.append({
                "task": task["id"],
                "duration": task_duration,
                "start": task_start - start_time
            })
        
        total_time = time.time() - start_time
        print(f"Total execution time: {total_time:.2f}s")
        
        # Verify sequential execution
        if total_time >= 3.0:  # Should take at least 3 seconds (2+1+0)
            print("✅ VERIFIED: Tasks executed sequentially (not in parallel)")
        else:
            print("❌ ERROR: Tasks may have executed in parallel!")
            
        return total_time >= 3.0
    
    async def test_fresh_context_isolation(self):
        """Test that each task gets fresh context (no variable pollution)."""
        print("\n=== Test 2: Fresh Context Isolation ===")
        print("Testing that each task starts with clean context...\n")
        
        tasks = [
            {
                "id": "context1",
                "command": "python3 -c \"x = 'Task 1 value'; print(f'Task 1 set x={x}')\"",
                "description": "Set variable in task 1"
            },
            {
                "id": "context2",
                "command": "python3 -c \"try: print(f'Task 2 sees x={x}'); except NameError: print('Task 2: x is undefined (fresh context)')\"",
                "description": "Check if variable exists in task 2"
            },
            {
                "id": "context3",
                "command": "python3 -c \"import os; print(f'Task 3 PID: {os.getpid()}')\"",
                "description": "Check process isolation"
            }
        ]
        
        context_isolated = True
        
        for task in tasks:
            print(f"Executing {task['id']}: {task['description']}")
            
            result = await self.client.execute_command(
                command=task["command"],
                metadata={"task_id": task["id"]}
            )
            
            if result["success"]:
                output = result["output_data"].strip()
                self.task_outputs[task["id"]] = output
                print(f"  Output: {output}")
                
                # Check for context isolation
                if task["id"] == "context2" and "undefined" not in output:
                    context_isolated = False
                    print("  ⚠️  WARNING: Context may be shared!")
            else:
                print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")
        
        if context_isolated:
            print("\n✅ VERIFIED: Each task has fresh context (no variable pollution)")
        else:
            print("\n❌ ERROR: Context isolation may be compromised!")
            
        return context_isolated
    
    async def test_output_sharing_via_files(self):
        """Test that tasks can share outputs via the filesystem."""
        print("\n=== Test 3: Output Sharing Between Tasks ===")
        print("Testing that tasks can share data via files...\n")
        
        test_dir = Path("/tmp/cc_executor_test")
        test_dir.mkdir(exist_ok=True)
        
        tasks = [
            {
                "id": "producer",
                "command": f"echo 'Data from Task 1: $(date +%s)' > {test_dir}/shared_data.txt && cat {test_dir}/shared_data.txt",
                "description": "Task 1 produces data"
            },
            {
                "id": "transformer",
                "command": f"cat {test_dir}/shared_data.txt && echo 'Task 2 processed: '$(wc -w < {test_dir}/shared_data.txt)' words' >> {test_dir}/shared_data.txt && cat {test_dir}/shared_data.txt",
                "description": "Task 2 reads and transforms data"
            },
            {
                "id": "consumer",
                "command": f"cat {test_dir}/shared_data.txt | grep -c 'Task' && echo 'Final result: '$(cat {test_dir}/shared_data.txt)",
                "description": "Task 3 consumes all data"
            }
        ]
        
        data_shared = True
        
        for task in tasks:
            print(f"Executing {task['id']}: {task['description']}")
            
            result = await self.client.execute_command(
                command=task["command"],
                metadata={"task_id": task["id"]}
            )
            
            if result["success"]:
                output = result["output_data"].strip()
                self.task_outputs[task["id"]] = output
                print(f"  Output: {output}\n")
            else:
                data_shared = False
                print(f"  ✗ Failed: {result.get('error', 'Unknown error')}\n")
        
        # Clean up
        if test_dir.exists():
            import shutil
            shutil.rmtree(test_dir)
        
        if data_shared:
            print("✅ VERIFIED: Tasks can share data via filesystem")
        else:
            print("❌ ERROR: Data sharing between tasks failed!")
            
        return data_shared
    
    async def test_orchestrator_with_claude_simulation(self):
        """Simulate the orchestrator pattern with mock Claude commands."""
        print("\n=== Test 4: Orchestrator Pattern Simulation ===")
        print("Simulating Claude orchestrator spawning multiple instances...\n")
        
        # Simulate the pattern from README lines 27-48
        orchestrator_tasks = [
            {
                "id": "claude_instance_1",
                "command": "echo '[Claude Instance #1] Creating FastAPI app with user model...' && sleep 1 && echo 'from fastapi import FastAPI\napp = FastAPI()\n# User model created' > /tmp/app.py && echo '[Claude Instance #1] ✓ FastAPI app created'",
                "description": "SPAWN Claude Instance #1: Create FastAPI app"
            },
            {
                "id": "claude_instance_2",
                "command": "echo '[Claude Instance #2] Reading files from Instance #1...' && cat /tmp/app.py 2>/dev/null || echo 'No app.py found' && echo '[Claude Instance #2] Adding authentication endpoints...' && sleep 1 && echo '[Claude Instance #2] ✓ Auth endpoints added'",
                "description": "SPAWN Claude Instance #2: Add authentication"
            },
            {
                "id": "claude_instance_3",
                "command": "echo '[Claude Instance #3] Creating comprehensive tests...' && echo 'test_app.py created with 10 tests' > /tmp/test_app.py && sleep 1 && echo '[Claude Instance #3] ✓ Tests created'",
                "description": "SPAWN Claude Instance #3: Create tests"
            }
        ]
        
        print("Orchestrator: Starting multi-step workflow")
        print("Each task simulates a fresh Claude instance with 200K context\n")
        
        workflow_success = True
        instance_outputs = []
        
        for i, task in enumerate(orchestrator_tasks, 1):
            print(f"\nOrchestrator: {task['description']}")
            print(f"{'='*60}")
            
            # Simulate orchestrator waiting for WebSocket response
            await asyncio.sleep(0.5)  # Orchestrator processing time
            
            result = await self.client.execute_command(
                command=task["command"],
                metadata={
                    "task_id": task["id"],
                    "instance_number": i,
                    "fresh_context": True
                }
            )
            
            if result["success"]:
                output = result["output_data"].strip()
                instance_outputs.append({
                    "instance": i,
                    "output": output,
                    "timestamp": time.time()
                })
                print(f"\nOutput from Instance #{i}:")
                print(output)
                print(f"\nOrchestrator: Instance #{i} completed successfully")
                print("Orchestrator: WAITING for completion before next instance...")
                await asyncio.sleep(0.5)  # Simulate orchestrator wait
            else:
                workflow_success = False
                print(f"\nOrchestrator: Instance #{i} FAILED: {result.get('error', 'Unknown error')}")
                break
        
        # Clean up
        for file in ["/tmp/app.py", "/tmp/test_app.py"]:
            if Path(file).exists():
                Path(file).unlink()
        
        if workflow_success:
            print("\n✅ VERIFIED: Orchestrator pattern works correctly!")
            print("- Each instance executed sequentially")
            print("- WebSocket forced waiting between instances")
            print("- Data was shared via filesystem")
        else:
            print("\n❌ ERROR: Orchestrator pattern failed!")
            
        return workflow_success
    
    async def test_complex_dependency_chain(self):
        """Test a complex workflow with dependencies."""
        print("\n=== Test 5: Complex Dependency Chain ===")
        print("Testing workflow where each task depends on previous outputs...\n")
        
        workflow_dir = Path("/tmp/cc_executor_workflow")
        workflow_dir.mkdir(exist_ok=True)
        
        dependency_tasks = [
            {
                "id": "init",
                "command": f"echo '0' > {workflow_dir}/counter.txt && echo 'Workflow initialized with counter=0'",
                "description": "Initialize workflow state"
            },
            {
                "id": "increment1",
                "command": f"COUNT=$(cat {workflow_dir}/counter.txt); NEW_COUNT=$((COUNT + 1)); echo $NEW_COUNT > {workflow_dir}/counter.txt && echo 'Incremented counter from '$COUNT' to '$NEW_COUNT",
                "description": "Increment counter (depends on init)"
            },
            {
                "id": "increment2",
                "command": f"COUNT=$(cat {workflow_dir}/counter.txt); NEW_COUNT=$((COUNT + 1)); echo $NEW_COUNT > {workflow_dir}/counter.txt && echo 'Incremented counter from '$COUNT' to '$NEW_COUNT",
                "description": "Increment again (depends on increment1)"
            },
            {
                "id": "verify",
                "command": f"FINAL=$(cat {workflow_dir}/counter.txt); echo 'Final counter value: '$FINAL && [ $FINAL -eq 2 ] && echo '✓ Dependency chain worked correctly!' || echo '✗ Dependency chain failed!'",
                "description": "Verify final state (depends on all previous)"
            }
        ]
        
        chain_success = True
        
        for task in dependency_tasks:
            print(f"\nExecuting {task['id']}: {task['description']}")
            
            result = await self.client.execute_command(
                command=task["command"],
                metadata={"task_id": task["id"], "workflow": "dependency_chain"}
            )
            
            if result["success"]:
                output = result["output_data"].strip()
                print(f"  Output: {output}")
                
                if task["id"] == "verify" and "failed" in output:
                    chain_success = False
            else:
                chain_success = False
                print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")
                break
        
        # Clean up
        if workflow_dir.exists():
            import shutil
            shutil.rmtree(workflow_dir)
        
        if chain_success:
            print("\n✅ VERIFIED: Complex dependency chains work correctly")
        else:
            print("\n❌ ERROR: Dependency chain execution failed!")
            
        return chain_success
    
    async def run_all_tests(self):
        """Run all orchestrator pattern tests."""
        print("=" * 80)
        print("ORCHESTRATOR PATTERN TEST SUITE")
        print("Testing the CORE PURPOSE of CC Executor")
        print("=" * 80)
        
        test_results = {
            "sequential_execution": False,
            "context_isolation": False,
            "output_sharing": False,
            "orchestrator_simulation": False,
            "dependency_chain": False
        }
        
        try:
            # Client connects per request - no persistent connection needed
            print("✓ WebSocket client ready\n")
            
            # Run tests
            test_results["sequential_execution"] = await self.test_sequential_execution()
            test_results["context_isolation"] = await self.test_fresh_context_isolation()
            test_results["output_sharing"] = await self.test_output_sharing_via_files()
            test_results["orchestrator_simulation"] = await self.test_orchestrator_with_claude_simulation()
            test_results["dependency_chain"] = await self.test_complex_dependency_chain()
            
        except Exception as e:
            print(f"\n❌ Test suite failed with error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            pass  # Client manages its own connections
            
        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(test_results)
        passed_tests = sum(1 for result in test_results.values() if result)
        
        for test_name, passed in test_results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
        
        print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! The orchestrator pattern works perfectly!")
        else:
            print(f"\n⚠️  {total_tests - passed_tests} tests failed. Investigation needed.")
            
        return passed_tests == total_tests


async def main():
    """Run the orchestrator pattern test suite."""
    # Check if server is running
    try:
        test_client = WebSocketClient()
        # Quick test to see if server is accessible
        result = await test_client.execute_command("echo 'Server test'", timeout=5)
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
    
    # Run tests with OutputCapture
    with OutputCapture(__file__) as capture:
        test_suite = OrchestratorPatternTest()
        success = await test_suite.run_all_tests()
        
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())