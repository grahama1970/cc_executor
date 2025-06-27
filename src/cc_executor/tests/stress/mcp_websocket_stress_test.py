#!/usr/bin/env python3
"""
MCP WebSocket Stress Test - Uses bidirectional WebSocket for real-time updates
Tests the actual MCP protocol with progress notifications and status updates
"""

import json
import asyncio
import websockets
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
import uuid
import time

class MCPWebSocketStressTest:
    def __init__(self, ws_url: str = "ws://localhost:8003/ws/mcp"):
        self.ws_url = ws_url
        self.results = []
        
    async def send_mcp_request(self, websocket, method: str, params: Dict[str, Any], request_id: str = None):
        """Send an MCP JSON-RPC request"""
        if not request_id:
            request_id = str(uuid.uuid4())
            
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id
        }
        
        await websocket.send(json.dumps(request))
        return request_id
        
    async def execute_task_with_mcp(self, task: Dict[str, Any], category: str) -> Dict[str, Any]:
        """Execute a task using MCP WebSocket with bidirectional communication"""
        marker = f"MCP_MARKER_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{task['id']}"
        
        print(f"\n{'='*80}")
        print(f"Executing Task: {task['name']} (ID: {task['id']}) via MCP WebSocket")
        print(f"Category: {category}")
        print(f"Marker: {marker}")
        if 'command' in task:
            print(f"Command: {task['command'][:100]}...")
        else:
            print(f"Request: {task['natural_language_request'][:100]}...")
        
        start_time = time.time()
        full_response = ""
        status_updates = []
        progress_notifications = []
        task_completed = False
        verified = False
        
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Send execute request with marker
                if 'command' in task:
                    # Use direct command for testing
                    command = task['command']
                else:
                    # Use natural language request for Claude
                    command = f"claude --dangerously-skip-permissions -p {task['natural_language_request']}\n\nIMPORTANT: Include this marker in your response: {marker}"
                
                request_id = await self.send_mcp_request(
                    websocket,
                    "execute",
                    {"command": command},
                    f"task_{task['id']}"
                )
                
                print(f"📤 Sent MCP execute request: {request_id}")
                
                # Listen for bidirectional messages
                heartbeat_count = 0
                last_progress = time.time()
                
                while not task_completed:
                    try:
                        # Set a timeout for receiving messages
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        data = json.loads(message)
                        
                        # Handle different message types
                        if "method" in data:
                            # This is a notification from the server
                            method = data.get("method")
                            params = data.get("params", {})
                            
                            if method == "process.output":
                                # Real-time output streaming
                                output_type = params.get("type", "stdout")
                                data = params.get("data", "")
                                if output_type == "stdout":
                                    full_response += data
                                    print(".", end="", flush=True)
                                elif output_type == "stderr":
                                    print("!", end="", flush=True)
                                
                            elif method == "status_update":
                                # Status update from Claude
                                status = params.get("status", "unknown")
                                message = params.get("message", "")
                                status_updates.append({
                                    "time": time.time() - start_time,
                                    "status": status,
                                    "message": message
                                })
                                print(f"\n📊 Status: {status} - {message}")
                                
                            elif method == "progress":
                                # Progress notification
                                progress = params.get("progress", 0)
                                total = params.get("total", 100)
                                progress_notifications.append({
                                    "time": time.time() - start_time,
                                    "progress": progress,
                                    "total": total
                                })
                                print(f"\n📈 Progress: {progress}/{total}")
                                last_progress = time.time()
                                
                            elif method == "heartbeat":
                                # Heartbeat from server
                                heartbeat_count += 1
                                elapsed = time.time() - start_time
                                if heartbeat_count % 3 == 0:  # Print every 3rd heartbeat
                                    print(f"\n💓 Heartbeat #{heartbeat_count} ({elapsed:.0f}s elapsed)")
                            elif method == "process.started":
                                # Process started notification
                                pid = params.get("pid")
                                print(f"\n🚀 Process started with PID: {pid}")
                                
                            elif method == "process.completed":
                                # Process completed notification
                                exit_code = params.get("exit_code", -1)
                                if exit_code == 0:
                                    print(f"\n✅ Process completed successfully")
                                    # Check for task-specific marker if it has a command
                                    if 'command' in task and 'MCP_MARKER_TEST' in task['command']:
                                        # Extract the test marker from command
                                        import re
                                        test_marker_match = re.search(r'MCP_MARKER_TEST_\d+', task['command'])
                                        if test_marker_match:
                                            test_marker = test_marker_match.group()
                                            verified = test_marker in full_response
                                            print(f"Looking for test marker: {test_marker}")
                                    else:
                                        verified = marker in full_response
                                    
                                    if verified:
                                        print(f"✅ Marker verified in output!")
                                    else:
                                        print(f"⚠️ Marker not found in output")
                                        print(f"Output received: {full_response[:200]}...")
                                else:
                                    print(f"\n❌ Process failed with exit code: {exit_code}")
                                task_completed = True
                                
                            elif method == "process.error":
                                # Process error notification
                                error_msg = params.get("message", "Unknown error")
                                print(f"\n❌ Process error: {error_msg}")
                                task_completed = True
                                    
                        elif "result" in data or "error" in data:
                            # This is the response to our request
                            if data.get("id") == request_id:
                                if "result" in data:
                                    result = data["result"]
                                    status = result.get("status")
                                    if status == "started":
                                        print(f"\n🚀 Command started, PID: {result.get('pid')}")
                                        
                                elif "error" in data:
                                    error = data["error"]
                                    print(f"\n❌ MCP Error: {error.get('message', 'Unknown error')}")
                                    task_completed = True
                                
                        # Send periodic status requests
                        if time.time() - last_progress > 10:
                            await self.send_mcp_request(
                                websocket,
                                "get_status",
                                {},
                                f"status_{task['id']}_{int(time.time())}"
                            )
                            last_progress = time.time()
                            
                    except asyncio.TimeoutError:
                        # No message received in 5 seconds
                        elapsed = time.time() - start_time
                        if elapsed > task.get('verification', {}).get('timeout', 120):
                            print(f"\n⏱️ Task timeout reached ({elapsed:.0f}s)")
                            task_completed = True
                        else:
                            # Send a ping to check connection
                            await self.send_mcp_request(
                                websocket,
                                "ping",
                                {},
                                f"ping_{task['id']}_{int(time.time())}"
                            )
                            
                duration = time.time() - start_time
                
                result = {
                    'task_id': task['id'],
                    'task_name': task['name'],
                    'category': category,
                    'marker': marker,
                    'verified': verified,
                    'duration': duration,
                    'response_length': len(full_response),
                    'status_updates': len(status_updates),
                    'progress_notifications': len(progress_notifications),
                    'heartbeats': heartbeat_count,
                    'timestamp': datetime.now().isoformat(),
                    'protocol': 'mcp_websocket'
                }
                
                if verified:
                    print(f"\n✅ Task {task['id']} completed and verified in {duration:.2f}s")
                    print(f"   📊 Status updates: {len(status_updates)}")
                    print(f"   📈 Progress notifications: {len(progress_notifications)}")
                    print(f"   💓 Heartbeats: {heartbeat_count}")
                else:
                    print(f"\n❌ Task {task['id']} verification failed!")
                    
                return result
                
        except Exception as e:
            print(f"\n❌ Task {task['id']} failed with error: {str(e)}")
            return {
                'task_id': task['id'],
                'task_name': task['name'],
                'category': category,
                'marker': marker,
                'verified': False,
                'error': str(e),
                'duration': time.time() - start_time,
                'timestamp': datetime.now().isoformat(),
                'protocol': 'mcp_websocket'
            }
    
    async def run_test(self, task: Dict[str, Any], category: str = "test"):
        """Run a single test task"""
        result = await self.execute_task_with_mcp(task, category)
        self.results.append(result)
        return result
    
    async def run_category(self, category_name: str, tasks: List[Dict[str, Any]]):
        """Run all tasks in a category"""
        print(f"\n{'#'*80}")
        print(f"# Running MCP WebSocket Tests for Category: {category_name}")
        print(f"# Tasks: {len(tasks)}")
        print(f"{'#'*80}")
        
        for task in tasks:
            await self.run_test(task, category_name)
            await asyncio.sleep(2)  # Small delay between tasks
    
    def generate_report(self):
        """Generate test report"""
        if not self.results:
            print("No results to report")
            return
        
        total_tasks = len(self.results)
        successful_tasks = len([r for r in self.results if r.get('verified', False)])
        failed_tasks = total_tasks - successful_tasks
        
        print(f"\n{'='*80}")
        print("MCP WEBSOCKET TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Protocol: WebSocket (Bidirectional MCP)")
        print(f"Total Tasks: {total_tasks}")
        print(f"Successful: {successful_tasks}")
        print(f"Failed: {failed_tasks}")
        print(f"Success Rate: {(successful_tasks / total_tasks * 100) if total_tasks > 0 else 0:.1f}%")
        
        # Show bidirectional communication stats
        total_status_updates = sum(r.get('status_updates', 0) for r in self.results)
        total_progress = sum(r.get('progress_notifications', 0) for r in self.results)
        total_heartbeats = sum(r.get('heartbeats', 0) for r in self.results)
        
        print(f"\nBidirectional Communication Stats:")
        print(f"  Total Status Updates: {total_status_updates}")
        print(f"  Total Progress Notifications: {total_progress}")
        print(f"  Total Heartbeats: {total_heartbeats}")
        
        # Show failed tasks
        failed_results = [r for r in self.results if not r.get('verified', False)]
        if failed_results:
            print(f"\n{'='*80}")
            print("FAILED TASKS:")
            print(f"{'='*80}")
            for result in failed_results:
                print(f"\nTask: {result['task_id']} ({result['task_name']})")
                print(f"Error: {result.get('error', 'Verification failed')}")

async def main():
    parser = argparse.ArgumentParser(description='Run MCP WebSocket stress tests')
    parser.add_argument('--ws-url', default='ws://localhost:8003/ws/mcp', help='WebSocket URL')
    parser.add_argument('--task-id', help='Run specific task ID')
    
    args = parser.parse_args()
    
    # Example test tasks - using commands available in cc-executor container
    test_tasks = [
        {
            "id": "mcp_test_1",
            "name": "simple_echo",
            "command": "echo 'Testing MCP bidirectional communication: MCP_MARKER_TEST_1'",
            "verification": {"timeout": 10}
        },
        {
            "id": "mcp_test_2", 
            "name": "python_calculation",
            "command": "python -c \"print('42 * 17 =', 42 * 17); print('MCP_MARKER_TEST_2')\"",
            "verification": {"timeout": 10}
        },
        {
            "id": "mcp_test_3",
            "name": "streaming_output",
            "command": "python -c \"import time; [print(f'Progress: {i}/10') or time.sleep(0.5) for i in range(1, 11)]; print('MCP_MARKER_TEST_3')\"",
            "verification": {"timeout": 30}
        }
    ]
    
    tester = MCPWebSocketStressTest(ws_url=args.ws_url)
    
    if args.task_id:
        # Run specific task
        task = next((t for t in test_tasks if t['id'] == args.task_id), None)
        if task:
            await tester.run_test(task)
        else:
            print(f"Task {args.task_id} not found")
    else:
        # Run all test tasks
        await tester.run_category("mcp_bidirectional", test_tasks)
    
    tester.generate_report()

if __name__ == "__main__":
    asyncio.run(main())