#!/usr/bin/env python3
import asyncio
import json
import time
from pathlib import Path
from datetime import datetime
import websockets

async def validate_stress_tests():
    """Validate all stress test JSON nodes work correctly"""
    
    # Load the JSON file
    json_path = Path("/home/graham/workspace/experiments/cc_executor/src/cc_executor/tasks/unified_stress_test_tasks.json")
    with open(json_path) as f:
        test_data = json.load(f)
    
    print(f"Loaded {json_path.name}")
    print(f"Categories: {list(test_data['categories'].keys())}")
    
    # Track results
    results = {}
    
    # Test each category
    for category, cat_data in test_data['categories'].items():
        print(f"\n{'='*60}")
        print(f"Testing category: {category}")
        print(f"Description: {cat_data['description']}")
        print(f"Tasks: {len(cat_data['tasks'])}")
        
        for task in cat_data['tasks']:
            task_id = task['id']
            print(f"\nTesting {task_id}: {task['name']}")
            
            # Build the execute command
            request = task['natural_language_request']
            metatags = task.get('metatags', '')
            
            execute_request = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {
                    "executable": "claude",
                    "args": [
                        "--print",
                        f"{metatags} {request}",
                        "--output-format", "stream-json",
                        "--verbose"
                    ]
                },
                "id": 1
            }
            
            # Execute via WebSocket
            try:
                ws_url = "ws://localhost:8003/ws/mcp"
                start_time = time.time()
                output_received = False
                patterns_found = []
                
                async with websockets.connect(ws_url) as websocket:
                    await websocket.send(json.dumps(execute_request))
                    
                    # Set timeout from task
                    timeout = task['verification']['timeout']
                    
                    while time.time() - start_time < timeout:
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            data = json.loads(response)
                            
                            # Check for streaming output
                            if "params" in data and "output" in data["params"]:
                                output_received = True
                                output = data["params"]["output"]
                                
                                # Check expected patterns
                                for pattern in task['verification']['expected_patterns']:
                                    if pattern.lower() in output.lower():
                                        if pattern not in patterns_found:
                                            patterns_found.append(pattern)
                            
                            # Check for completion
                            if "result" in data:
                                exit_code = data["result"].get("exit_code", -1)
                                duration = time.time() - start_time
                                
                                # Determine success
                                success = (
                                    exit_code == 0 and 
                                    output_received and 
                                    len(patterns_found) > 0
                                )
                                
                                results[task_id] = {
                                    "success": success,
                                    "duration": duration,
                                    "patterns_found": patterns_found,
                                    "exit_code": exit_code
                                }
                                
                                if success:
                                    print(f"  ✓ PASSED in {duration:.1f}s")
                                    print(f"    Found patterns: {patterns_found}")
                                else:
                                    print(f"  ✗ FAILED in {duration:.1f}s")
                                    print(f"    Exit code: {exit_code}")
                                    print(f"    Patterns found: {patterns_found}/{task['verification']['expected_patterns']}")
                                break
                                
                        except asyncio.TimeoutError:
                            continue
                    else:
                        # Timeout reached
                        results[task_id] = {
                            "success": False,
                            "duration": time.time() - start_time,
                            "error": "Timeout",
                            "patterns_found": patterns_found
                        }
                        print(f"  ✗ TIMEOUT after {timeout}s")
                        
            except Exception as e:
                results[task_id] = {
                    "success": False,
                    "error": str(e),
                    "duration": time.time() - start_time
                }
                print(f"  ✗ ERROR: {e}")
    
    # Generate summary
    print(f"\n{'='*60}")
    print("VALIDATION SUMMARY")
    print(f"{'='*60}")
    
    total = len(results)
    passed = sum(1 for r in results.values() if r.get('success', False))
    failed = total - passed
    
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success rate: {passed/total*100:.1f}%")
    
    # Show failed tests
    if failed > 0:
        print("\nFailed tests:")
        for task_id, result in results.items():
            if not result.get('success', False):
                print(f"  - {task_id}: {result.get('error', 'Unknown error')}")
    
    # Save detailed results
    output_file = f"stress_test_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "success_rate": passed/total
            },
            "results": results
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")
    
    return passed == total

if __name__ == "__main__":
    # Check websocket is running
    import requests
    try:
        resp = requests.get("http://localhost:8003/health", timeout=2)
        if resp.status_code != 200:
            print("WebSocket server not healthy!")
            exit(1)
    except:
        print("WebSocket server not running! Start it first.")
        exit(1)
    
    # Run validation
    success = asyncio.run(validate_stress_tests())
    exit(0 if success else 1)
