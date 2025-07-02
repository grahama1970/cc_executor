#!/usr/bin/env python3
"""
Test script for WebSocket handler functionality.

This script demonstrates how to test the WebSocket handler both as a client
connecting to a running server and directly with mock objects.
"""

import json
import asyncio
import uuid
import socket
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import websockets
except ImportError:
    print("Please install websockets: pip install websockets")
    sys.exit(1)

from src.cc_executor.core.session_manager import SessionManager
from src.cc_executor.core.process_manager import ProcessManager
from src.cc_executor.core.stream_handler import StreamHandler
from src.cc_executor.core.websocket_handler import WebSocketHandler
from src.cc_executor.core.models import validate_command


async def test_claude_auth():
    """Test if Claude CLI is authenticated before running other tests."""
    print("=== Claude CLI Authentication Check ===\n")
    
    import subprocess
    try:
        # Quick test with timeout
        result = subprocess.run(
            ['claude', '-p', 'echo test', '--output-format', 'json'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("✅ Claude CLI is authenticated and working!")
            return True
        else:
            print("❌ Claude CLI command failed!")
            print(f"STDERR: {result.stderr}")
            print("\nPlease authenticate first: claude -p test")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Claude CLI timed out - not authenticated")
        print("\nPlease authenticate first: claude -p test")
        return False
    except FileNotFoundError:
        print("❌ Claude CLI not found!")
        print("Install with: npm install -g @anthropic-ai/claude-cli")
        return False


async def test_websocket_client():
    """Test client that exercises all WebSocket handler functionality."""
    
    print("=== WebSocket Handler Test Client ===\n")
    
    # Check Claude auth first
    if not await test_claude_auth():
        print("\n⚠️  Skipping Claude tests due to authentication issues\n")
        return False
    
    # Connect to test server
    uri = "ws://localhost:8003/ws/mcp"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            
            # Test 1: Execute command
            print("\n--- Test 1: Execute Command ---")
            execute_req = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {"command": "echo 'Hello from WebSocket'"},
                "id": 1
            }
            await websocket.send(json.dumps(execute_req))
            print(f"Sent: {execute_req}")
            
            # Receive connection confirmation
            response = await websocket.recv()
            print(f"Received: {response}")
            
            # Receive execute response
            response = await websocket.recv()
            print(f"Received: {response}")
            
            # Test 2: Invalid method
            print("\n--- Test 2: Invalid Method ---")
            invalid_req = {
                "jsonrpc": "2.0",
                "method": "unknown_method",
                "params": {},
                "id": 2
            }
            await websocket.send(json.dumps(invalid_req))
            print(f"Sent: {invalid_req}")
            
            response = await websocket.recv()
            print(f"Received: {response}")
            
            # Test 3: Execute long-running command
            print("\n--- Test 3: Long-Running Command ---")
            long_req = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {"command": "python -c 'import time; print(\"Starting\"); time.sleep(2); print(\"Done\")'"},
                "id": 3
            }
            await websocket.send(json.dumps(long_req))
            print(f"Sent: {long_req}")
            
            # Collect responses
            for _ in range(5):  # Expect multiple messages
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1)
                    print(f"Received: {response}")
                except asyncio.TimeoutError:
                    break
            
            # Test 4: Control command (CANCEL)
            print("\n--- Test 4: Control Command ---")
            control_req = {
                "jsonrpc": "2.0",
                "method": "control",
                "params": {"type": "CANCEL"},
                "id": 4
            }
            await websocket.send(json.dumps(control_req))
            print(f"Sent: {control_req}")
            
            response = await websocket.recv()
            print(f"Received: {response}")
            
            print("\n✅ All WebSocket tests completed!")
            
    except websockets.exceptions.ConnectionRefused:
        print("❌ Could not connect to WebSocket server")
        print("Make sure the server is running: docker compose up")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
        
    return True


async def test_handler_directly():
    """Test WebSocket handler without actual WebSocket connection."""
    
    print("\n=== Direct Handler Testing ===\n")
    
    # Mock WebSocket
    class MockWebSocket:
        def __init__(self):
            self.messages = []
            self.closed = False
            
        async def accept(self):
            pass
            
        async def send_json(self, data):
            self.messages.append(data)
            print(f"Would send: {json.dumps(data, indent=2)}")
            
        async def receive_text(self):
            if self.closed:
                from fastapi import WebSocketDisconnect
                raise WebSocketDisconnect()
            await asyncio.sleep(0.1)
            self.closed = True
            return '{"jsonrpc":"2.0","method":"execute","params":{"command":"echo test"},"id":1}'
            
        async def close(self, code=1000, reason=""):
            self.closed = True
    
    # Create handler components
    session_manager = SessionManager(max_sessions=2)
    process_manager = ProcessManager()
    stream_handler = StreamHandler()
    
    handler = WebSocketHandler(
        session_manager,
        process_manager,
        stream_handler
    )
    
    # Test 1: Normal connection
    print("--- Test 1: Normal Connection ---")
    mock_ws = MockWebSocket()
    session_id = str(uuid.uuid4())
    
    await handler.handle_connection(mock_ws, session_id)
    print(f"Messages sent: {len(mock_ws.messages)}")
    
    # Test 2: Session limit
    print("\n--- Test 2: Session Limit ---")
    
    # Fill up sessions
    for i in range(3):
        session_id = f"test-session-{i}"
        mock_ws = MockWebSocket()
        
        if i < 2:
            success = await session_manager.create_session(session_id, mock_ws)
            print(f"Session {i+1}: Created = {success}")
        else:
            # This should fail
            await handler.handle_connection(mock_ws, session_id)
            print(f"Session {i+1}: Rejected (limit reached)")
    
    # Test 3: Command validation
    print("\n--- Test 3: Command Validation ---")
    
    is_valid, error = validate_command("echo test", ["echo", "ls"])
    print(f"'echo test' with allowed ['echo', 'ls']: valid={is_valid}")
    
    is_valid, error = validate_command("rm -rf /", ["echo", "ls"])
    print(f"'rm -rf /' with allowed ['echo', 'ls']: valid={is_valid}, error={error}")
    
    print("\n✅ Direct handler tests completed!")


async def main():
    """Run all tests."""
    
    # Check if server is running
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_running = sock.connect_ex(('localhost', 8003)) == 0
    sock.close()
    
    if server_running:
        print("Server detected, running client tests...")
        await test_websocket_client()
    else:
        print("Server not running, testing handler directly...")
        await test_handler_directly()


if __name__ == "__main__":
    asyncio.run(main())