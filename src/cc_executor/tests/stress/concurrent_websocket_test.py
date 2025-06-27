#!/usr/bin/env python3
"""
Concurrent Claude execution via multiple WebSocket connections.

This script demonstrates launching multiple Claude instances concurrently
using the WebSocket handler, with different creativity and max_turns parameters.
"""

import asyncio
import websockets
import json
import time
from typing import Dict, List, Any
import uuid
import random


class ClaudeInstance:
    """Manages a single Claude instance via WebSocket."""
    
    def __init__(self, instance_id: int, creativity: int, max_turns: int, prompt: str):
        self.instance_id = instance_id
        self.creativity = creativity
        self.max_turns = max_turns
        self.prompt = prompt
        self.session_id = str(uuid.uuid4())
        self.start_time = None
        self.end_time = None
        self.output = []
        self.ws = None
        
    async def connect_and_execute(self, uri: str = "ws://localhost:8003/ws/mcp"):
        """Connect to WebSocket and execute Claude command."""
        try:
            self.start_time = time.time()
            
            async with websockets.connect(uri) as websocket:
                self.ws = websocket
                
                # Prepare Claude command with parameters
                command = f'claude --creativity {self.creativity} --max-turns {self.max_turns} -p "{self.prompt}"'
                
                # Send execute command
                request = {
                    "jsonrpc": "2.0",
                    "method": "execute",
                    "params": {"command": command},
                    "id": self.instance_id
                }
                
                await websocket.send(json.dumps(request))
                print(f"[Instance {self.instance_id}] Started with creativity={self.creativity}, max_turns={self.max_turns}")
                
                # Collect output
                async for message in websocket:
                    data = json.loads(message)
                    
                    # Handle streaming output
                    if data.get("method") == "process.output":
                        output_data = data.get("params", {}).get("data", "")
                        self.output.append(output_data)
                    
                    # Handle completion
                    elif data.get("method") == "process.exit":
                        exit_code = data.get("params", {}).get("exitCode", -1)
                        self.end_time = time.time()
                        print(f"[Instance {self.instance_id}] Completed with exit code {exit_code}")
                        break
                        
        except Exception as e:
            print(f"[Instance {self.instance_id}] Error: {e}")
            self.end_time = time.time()
            
    def get_execution_time(self):
        """Get execution time in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0
        
    def get_output(self):
        """Get concatenated output."""
        return "".join(self.output)


async def run_concurrent_instances(
    num_instances: int = 5,
    base_prompt: str = "Create a function to reverse a string",
    creativity_range: tuple = (1, 5),
    max_turns_range: tuple = (1, 3)
):
    """Run multiple Claude instances concurrently."""
    
    print(f"=== Launching {num_instances} concurrent Claude instances ===\n")
    
    # Create instances with varying parameters
    instances = []
    for i in range(num_instances):
        creativity = random.randint(*creativity_range)
        max_turns = random.randint(*max_turns_range)
        
        instance = ClaudeInstance(
            instance_id=i + 1,
            creativity=creativity,
            max_turns=max_turns,
            prompt=f"{base_prompt} (Instance {i+1})"
        )
        instances.append(instance)
    
    # Launch all instances concurrently
    start_time = time.time()
    tasks = [instance.connect_and_execute() for instance in instances]
    await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    # Analyze results
    print(f"\n=== Results Summary ===")
    print(f"Total execution time: {total_time:.2f}s")
    print(f"\nIndividual instance times:")
    
    for instance in instances:
        exec_time = instance.get_execution_time()
        output_len = len(instance.get_output())
        print(f"  Instance {instance.instance_id}: {exec_time:.2f}s, "
              f"creativity={instance.creativity}, max_turns={instance.max_turns}, "
              f"output_size={output_len} chars")
    
    # Group by creativity level
    print(f"\nAverage time by creativity level:")
    creativity_times = {}
    for instance in instances:
        c = instance.creativity
        if c not in creativity_times:
            creativity_times[c] = []
        creativity_times[c].append(instance.get_execution_time())
    
    for creativity, times in sorted(creativity_times.items()):
        avg_time = sum(times) / len(times)
        print(f"  Creativity {creativity}: {avg_time:.2f}s (n={len(times)})")
    
    return instances


async def run_stress_test():
    """Run different concurrent execution scenarios."""
    
    print("CONCURRENT WEBSOCKET STRESS TEST")
    print("=" * 50)
    
    # Test 1: Small scale (5 instances)
    print("\nTest 1: Small scale concurrent execution")
    await run_concurrent_instances(
        num_instances=5,
        base_prompt="Write a haiku about programming",
        creativity_range=(1, 5),
        max_turns_range=(1, 2)
    )
    
    # Test 2: Medium scale (10 instances)
    print("\n\nTest 2: Medium scale concurrent execution")
    await run_concurrent_instances(
        num_instances=10,
        base_prompt="Create a sorting algorithm",
        creativity_range=(1, 5),
        max_turns_range=(1, 3)
    )
    
    # Test 3: Specific parameter testing
    print("\n\nTest 3: Specific parameter combinations")
    instances = []
    params = [
        (1, 1, "minimal creativity/turns"),
        (3, 2, "balanced approach"),
        (5, 3, "maximum creativity/turns"),
        (2, 1, "low creativity, minimal turns"),
        (4, 3, "high creativity, max turns")
    ]
    
    for i, (creativity, max_turns, desc) in enumerate(params):
        instance = ClaudeInstance(
            instance_id=i + 1,
            creativity=creativity,
            max_turns=max_turns,
            prompt=f"Create a calculator function ({desc})"
        )
        instances.append(instance)
    
    tasks = [instance.connect_and_execute() for instance in instances]
    await asyncio.gather(*tasks)
    
    print("\nParameter combination results:")
    for instance in instances:
        print(f"  Instance {instance.instance_id} (c={instance.creativity}, t={instance.max_turns}): "
              f"{instance.get_execution_time():.2f}s")


if __name__ == "__main__":
    # Run the stress test
    asyncio.run(run_stress_test())