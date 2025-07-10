#!/usr/bin/env python3
"""
Final WebSocket test for CC Executor.
This test addresses the specific issues mentioned:
1. No imports of cc_executor modules to avoid conflicts
2. Proper authentication headers for Docker
3. Correct JSON-RPC format for MCP server
"""

import asyncio
import json
import websockets
import uuid
import sys
import os
from datetime import datetime
from pathlib import Path


class WebSocketTester:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = []
        
    async def test_local_mcp(self):
        """Test local MCP server on port 8003."""
        print("\n🏠 Testing Local MCP Server (port 8003)...")
        
        # First, check if we need to start the server
        import subprocess
        try:
            # Check if port is in use
            result = subprocess.run(['lsof', '-ti:8003'], capture_output=True, text=True)
            if not result.stdout.strip():
                print("  ⚠️  Server not running, starting it...")
                # Start the server
                subprocess.Popen([
                    sys.executable, '-m', 'uvicorn', 
                    'cc_executor.core.main:app',
                    '--host', '127.0.0.1',
                    '--port', '8003'
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                await asyncio.sleep(3)  # Wait for server to start
        except:
            pass
        
        uri = "ws://localhost:8003/ws/mcp"
        
        try:
            async with websockets.connect(uri, ping_interval=None) as websocket:
                print(f"  ✅ Connected to {uri}")
                
                # Wait for connection message
                msg = await websocket.recv()
                data = json.loads(msg)
                session_id = data["params"]["session_id"]
                print(f"  📋 Session ID: {session_id}")
                
                # Test simple echo
                request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "execute",
                    "params": {
                        "command": "echo 'Test from MCP local'",
                        "timeout": 10
                    }
                }
                
                await websocket.send(json.dumps(request))
                
                # Collect response
                result = await self._collect_response(websocket, "Local MCP echo test")
                self.results.append({
                    "test": "Local MCP WebSocket",
                    "success": result['success'],
                    "output": result['output']
                })
                
        except ConnectionRefusedError:
            print(f"  ❌ Cannot connect to local MCP server")
            self.results.append({
                "test": "Local MCP WebSocket",
                "success": False,
                "error": "Connection refused"
            })
        except Exception as e:
            print(f"  ❌ Error: {e}")
            self.results.append({
                "test": "Local MCP WebSocket", 
                "success": False,
                "error": str(e)
            })
    
    async def test_docker_mcp(self):
        """Test Docker MCP server on port 8004 with authentication."""
        print("\n🐳 Testing Docker MCP Server (port 8004)...")
        
        # Get auth token from environment
        auth_token = os.environ.get('CC_EXECUTOR_AUTH_TOKEN', 'test-auth-token')
        
        uri = "ws://localhost:8004/ws/mcp"
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "X-API-Key": auth_token  # Try both header formats
        }
        
        try:
            async with websockets.connect(uri, extra_headers=headers, ping_interval=None) as websocket:
                print(f"  ✅ Connected to {uri} (with auth)")
                
                # Wait for connection message
                msg = await websocket.recv()
                data = json.loads(msg)
                session_id = data["params"]["session_id"]
                print(f"  📋 Session ID: {session_id}")
                
                # Test simple echo
                request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "execute",
                    "params": {
                        "command": "echo 'Test from Docker MCP'",
                        "timeout": 10
                    }
                }
                
                await websocket.send(json.dumps(request))
                
                # Collect response
                result = await self._collect_response(websocket, "Docker MCP echo test")
                self.results.append({
                    "test": "Docker MCP WebSocket",
                    "success": result['success'],
                    "output": result['output']
                })
                
        except ConnectionRefusedError:
            print(f"  ❌ Cannot connect to Docker MCP server")
            print(f"     Make sure Docker container is running:")
            print(f"     docker run -p 8004:8003 cc-executor:latest")
            self.results.append({
                "test": "Docker MCP WebSocket",
                "success": False,
                "error": "Connection refused - Docker container not running?"
            })
        except Exception as e:
            if "403" in str(e):
                print(f"  ❌ Authentication failed (403)")
                print(f"     Set CC_EXECUTOR_AUTH_TOKEN environment variable")
            else:
                print(f"  ❌ Error: {e}")
            self.results.append({
                "test": "Docker MCP WebSocket",
                "success": False,
                "error": str(e)
            })
    
    async def _collect_response(self, websocket, test_name, timeout=15):
        """Collect response from WebSocket."""
        full_output = ""
        success = False
        
        try:
            while True:
                msg = await asyncio.wait_for(websocket.recv(), timeout=timeout)
                data = json.loads(msg)
                
                if data.get("method") == "process.output":
                    params = data.get("params", {})
                    if params.get("type") == "stdout":
                        chunk = params.get("data", "")
                        full_output += chunk
                elif data.get("method") == "process.exit":
                    params = data.get("params", {})
                    exit_code = params.get("exit_code", -1)
                    success = (exit_code == 0)
                elif "result" in data:
                    success = True
                    if not full_output:
                        full_output = str(data.get("result", ""))
                    break
                elif "error" in data:
                    full_output = f"Error: {data['error']}"
                    break
                    
        except asyncio.TimeoutError:
            full_output = f"Timeout after {timeout}s"
            
        print(f"  {'✅' if success else '❌'} {test_name}: {full_output.strip()[:100]}")
        return {"success": success, "output": full_output.strip()}
    
    def generate_report(self):
        """Generate test report."""
        report_dir = Path("tests/stress_test_results")
        report_dir.mkdir(exist_ok=True)
        
        # Generate report
        report_file = report_dir / f"websocket_test_{self.timestamp}.md"
        with open(report_file, 'w') as f:
            f.write("# WebSocket Test Report\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            
            f.write("## Test Results\n\n")
            
            success_count = sum(1 for r in self.results if r.get('success', False))
            total_count = len(self.results)
            
            f.write(f"- **Total Tests:** {total_count}\n")
            f.write(f"- **Successful:** {success_count}\n")
            f.write(f"- **Failed:** {total_count - success_count}\n")
            f.write(f"- **Success Rate:** {(success_count/total_count*100) if total_count > 0 else 0:.1f}%\n\n")
            
            f.write("### Individual Test Results\n\n")
            for result in self.results:
                status = "✅" if result.get('success', False) else "❌"
                f.write(f"#### {result['test']} {status}\n\n")
                if result.get('success'):
                    f.write(f"Output: `{result.get('output', 'N/A')[:200]}`\n\n")
                else:
                    f.write(f"Error: {result.get('error', 'Unknown error')}\n\n")
            
            f.write("## Recommendations\n\n")
            
            # Check specific issues
            local_failed = any(r['test'] == 'Local MCP WebSocket' and not r.get('success') for r in self.results)
            docker_failed = any(r['test'] == 'Docker MCP WebSocket' and not r.get('success') for r in self.results)
            
            if local_failed:
                f.write("- **Local MCP Server**: Not running or misconfigured\n")
                f.write("  - Start with: `python -m uvicorn cc_executor.core.main:app --port 8003`\n")
                f.write("  - Check logs: `tail -f /tmp/cc_executor_mcp.log`\n\n")
                
            if docker_failed:
                f.write("- **Docker MCP Server**: Not accessible\n")
                f.write("  - Check if container is running: `docker ps | grep cc-executor`\n")
                f.write("  - Start container: `docker run -p 8004:8003 -e AUTH_TOKEN=your-token cc-executor:latest`\n")
                f.write("  - Set auth token: `export CC_EXECUTOR_AUTH_TOKEN=your-token`\n\n")
        
        print(f"\n📊 Report saved to: {report_file}")
        return report_file


async def main():
    """Run WebSocket tests."""
    print("🚀 CC Executor WebSocket Test Suite")
    print("=" * 60)
    
    tester = WebSocketTester()
    
    # Run tests
    await tester.test_local_mcp()
    await tester.test_docker_mcp()
    
    # Generate report
    report_file = tester.generate_report()
    
    # Summary
    success_count = sum(1 for r in tester.results if r.get('success', False))
    total_count = len(tester.results)
    
    print("\n" + "=" * 60)
    print(f"Summary: {success_count}/{total_count} tests passed")
    
    return success_count == total_count


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)