#!/usr/bin/env python3
"""
WebSocket Test Executor for CC-Executor
Tests the actual WebSocket MCP interface with full response capture and verification.
"""

import asyncio
import json
import time
import websockets
from datetime import datetime
from pathlib import Path
import sys
import subprocess

class WebSocketTestExecutor:
    def __init__(self, ws_url="ws://localhost:8003/ws/mcp"):
        self.ws_url = ws_url
        self.results = []
        self.output_dir = Path("websocket_test_outputs")
        self.output_dir.mkdir(exist_ok=True)
        
    async def execute_command(self, command: str, marker: str) -> dict:
        """Execute a command via WebSocket and capture response"""
        result = {
            'marker': marker,
            'command': command,
            'start_time': time.time(),
            'response': [],
            'success': False,
            'error': None,
            'session_id': None
        }
        
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Wait for connection message
                connect_msg = await websocket.recv()
                connect_data = json.loads(connect_msg)
                
                print(f"DEBUG: Received connection message: {connect_data}")
                if connect_data.get('method') == 'connected':
                    result['session_id'] = connect_data['params']['session_id']
                    print(f"✓ Connected. Session: {result['session_id']}")
                
                # Send execute command with marker
                execute_msg = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "execute",
                    "params": {
                        "command": f"echo '{marker}' && {command}"
                    }
                }
                
                await websocket.send(json.dumps(execute_msg))
                print(f"→ Sent command: {command[:50]}...")
                
                # Collect all responses
                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=60)
                        response_data = json.loads(response)
                        result['response'].append(response_data)
                        
                        # Print status updates
                        if response_data.get('method') == 'process.output':
                            data = response_data['params'].get('data', '')
                            if data:
                                print(f"  Output: {data.strip()[:100]}")
                        elif response_data.get('method') == 'process.completed':
                            exit_code = response_data['params'].get('exit_code')
                            print(f"  Process completed with exit code: {exit_code}")
                            result['success'] = (exit_code == 0)
                            break
                        elif response_data.get('method') == 'process.started':
                            pid = response_data['params'].get('pid')
                            print(f"  Process started with PID: {pid}")
                        elif response_data.get('error'):
                            result['error'] = response_data['error']
                            print(f"  Error: {response_data['error']}")
                            break
                            
                    except asyncio.TimeoutError:
                        print("  Timeout waiting for response")
                        break
                        
        except Exception as e:
            result['error'] = str(e)
            print(f"❌ WebSocket error: {e}")
        
        result['end_time'] = time.time()
        result['duration'] = result['end_time'] - result['start_time']
        
        # Save full response
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"ws_test_{timestamp}_{marker}.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"  📄 Saved to: {output_file}")
        
        return result
    
    async def run_test_suite(self):
        """Run a suite of test commands"""
        tests = [
            {
                'name': 'simple_echo',
                'command': 'echo "Hello from WebSocket test"',
                'expected': 'Hello from WebSocket test'
            },
            {
                'name': 'python_calc',
                'command': 'python -c "print(42 * 17)"',
                'expected': '714'
            },
            {
                'name': 'code_analysis',
                'command': 'python -c "import ast; print(len(ast.parse(\'def foo(): return 42\').body))"',
                'expected': '1'
            },
            {
                'name': 'multi_line_output',
                'command': 'python -c "for i in range(5): print(f\'Line {i}\')"',
                'expected': 'Line 0'
            }
        ]
        
        print("="*80)
        print("WEBSOCKET TEST SUITE")
        print("="*80)
        print(f"Target: {self.ws_url}")
        print(f"Tests: {len(tests)}")
        print()
        
        for test in tests:
            marker = f"WS_TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{test['name']}"
            print(f"\n{'='*60}")
            print(f"Test: {test['name']}")
            print(f"Marker: {marker}")
            
            result = await self.execute_command(test['command'], marker)
            self.results.append(result)
            
            # Check if expected output was found
            full_output = self.extract_output(result)
            if test['expected'] in full_output:
                print(f"✅ Expected output found: '{test['expected']}'")
            else:
                print(f"❌ Expected output NOT found: '{test['expected']}'")
                print(f"   Actual output: {full_output[:200]}...")
            
            # Verify in transcript
            await self.verify_execution(marker)
    
    def extract_output(self, result: dict) -> str:
        """Extract all output from response messages"""
        output_parts = []
        for msg in result.get('response', []):
            if msg.get('method') == 'process.output':
                data = msg.get('params', {}).get('data', '')
                if data:
                    output_parts.append(data.strip())
        return '\n'.join(output_parts)
    
    async def verify_execution(self, marker: str):
        """Verify execution in transcript"""
        print(f"\n🔍 Verifying execution of '{marker}'...")
        
        # Use transcript helper
        result = subprocess.run(
            ['python', '/home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/commands/transcript_helper.py', marker],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ VERIFIED: Execution found in transcript")
        else:
            print(f"❌ NOT VERIFIED: Execution not found in transcript")
            print(f"   Stdout: {result.stdout}")
            print(f"   Stderr: {result.stderr}")
        
        # Also show the verification command
        print(f"\n📋 Manual verification command:")
        print(f"   python /home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/commands/transcript_helper.py {marker}")
        
        return result.returncode == 0
    
    def generate_report(self):
        """Generate summary report"""
        print(f"\n{'='*80}")
        print("TEST SUMMARY REPORT")
        print("="*80)
        
        total = len(self.results)
        successful = sum(1 for r in self.results if r['success'])
        
        print(f"Total Tests: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {total - successful}")
        print(f"Success Rate: {successful/total*100:.1f}%")
        
        print(f"\nDetailed Results:")
        for result in self.results:
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['marker']}: {result['duration']:.2f}s")
            if result['error']:
                print(f"   Error: {result['error']}")
        
        # Save summary
        summary_file = self.output_dir / f"ws_test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w') as f:
            json.dump({
                'total': total,
                'successful': successful,
                'success_rate': successful/total*100 if total > 0 else 0,
                'results': [
                    {
                        'marker': r['marker'],
                        'success': r['success'],
                        'duration': r['duration'],
                        'error': r['error']
                    }
                    for r in self.results
                ]
            }, f, indent=2)
        print(f"\n📊 Summary saved to: {summary_file}")


async def main():
    """Run the WebSocket test suite"""
    executor = WebSocketTestExecutor()
    await executor.run_test_suite()
    executor.generate_report()


if __name__ == "__main__":
    asyncio.run(main())