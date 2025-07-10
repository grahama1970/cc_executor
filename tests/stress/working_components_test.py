#!/usr/bin/env python3
"""
Test only the working components: Python API and Docker WebSocket
"""

import json
import time
import asyncio
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cc_executor.client.cc_execute import cc_execute, CCExecutorConfig

async def test_python_api():
    """Test Python API directly"""
    print("\n🐍 Testing Python API (cc_execute)...")
    results = []
    
    test_cases = [
        {"name": "Math", "task": "What is 25 * 4? Just the number."},
        {"name": "List", "task": "Name the first 5 US presidents, comma separated."},
        {"name": "Code", "task": "Write a Python function to reverse a string. Just the function."}
    ]
    
    for test in test_cases:
        print(f"  📝 {test['name']}...")
        start = time.time()
        
        try:
            config = CCExecutorConfig(timeout=60)
            result = await cc_execute(task=test['task'], config=config, stream=False)
            duration = time.time() - start
            
            results.append({
                "name": test['name'],
                "success": True,
                "duration": duration,
                "result": result.strip() if isinstance(result, str) else str(result)
            })
            print(f"    ✅ Success ({duration:.2f}s)")
            
        except Exception as e:
            duration = time.time() - start
            results.append({
                "name": test['name'],
                "success": False,
                "duration": duration,
                "error": str(e)
            })
            print(f"    ❌ Failed: {str(e)[:100]} ({duration:.2f}s)")
    
    return results

async def test_docker_direct():
    """Test Docker WebSocket using direct websocket connection"""
    print("\n🐳 Testing Docker WebSocket...")
    results = []
    
    try:
        import websockets
        uri = "ws://localhost:8004/ws/mcp"
        
        async with websockets.connect(uri) as websocket:
            print(f"  ✅ Connected to Docker WebSocket")
            
            test_cases = [
                {"name": "Math via Docker", "task": "What is 100 / 5? Just the number."},
                {"name": "Text via Docker", "task": "What's the opposite of 'hot'? One word."}
            ]
            
            for test in test_cases:
                print(f"  📝 {test['name']}...")
                start = time.time()
                
                try:
                    # Send request
                    request = {
                        "jsonrpc": "2.0",
                        "method": "execute",
                        "params": {"command": test['task']},
                        "id": test['name']
                    }
                    await websocket.send(json.dumps(request))
                    
                    # Get response
                    full_response = ""
                    while True:
                        try:
                            msg = await asyncio.wait_for(websocket.recv(), timeout=30)
                            data = json.loads(msg)
                            
                            # Handle streaming output
                            if data.get("method") == "process.output":
                                output = data.get("params", {})
                                if output.get("type") == "stdout":
                                    full_response += output.get("data", "")
                            
                            # Check for completion
                            elif "result" in data:
                                duration = time.time() - start
                                results.append({
                                    "name": test['name'],
                                    "success": True,
                                    "duration": duration,
                                    "result": full_response.strip() or "Started process"
                                })
                                print(f"    ✅ Success ({duration:.2f}s)")
                                break
                                
                        except asyncio.TimeoutError:
                            break
                            
                except Exception as e:
                    duration = time.time() - start
                    results.append({
                        "name": test['name'],
                        "success": False,
                        "duration": duration,
                        "error": str(e)
                    })
                    print(f"    ❌ Failed: {str(e)[:100]} ({duration:.2f}s)")
                    
    except Exception as e:
        print(f"  ❌ Cannot connect to Docker: {e}")
        results.append({
            "name": "Docker connection",
            "success": False,
            "duration": 0,
            "error": str(e)
        })
    
    return results

async def main():
    """Run tests and generate report"""
    print("🚀 CC Executor Working Components Test")
    print("=" * 50)
    
    # Run tests
    python_results = await test_python_api()
    docker_results = await test_docker_direct()
    
    # Generate report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = {
        "timestamp": datetime.now().isoformat(),
        "python_api": python_results,
        "docker_websocket": docker_results
    }
    
    # Save results
    output_dir = Path("tests/stress_test_results")
    output_dir.mkdir(exist_ok=True)
    
    report_file = output_dir / f"working_components_{timestamp}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    
    # Python API summary
    python_success = sum(1 for r in python_results if r.get("success"))
    print(f"\nPython API: {python_success}/{len(python_results)} tests passed")
    
    # Docker summary  
    docker_success = sum(1 for r in docker_results if r.get("success"))
    print(f"Docker WebSocket: {docker_success}/{len(docker_results)} tests passed")
    
    print(f"\n📄 Report saved to: {report_file}")

if __name__ == "__main__":
    asyncio.run(main())