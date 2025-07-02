#!/usr/bin/env python3
"""Test resource monitor integration with WebSocket handler.

This test verifies that timeouts are properly adjusted when system
load is high.
"""
import os
import sys
import asyncio
import json
import websockets
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cc_executor.core.resource_monitor import calculate_timeout_multiplier, adjust_timeout


async def test_resource_monitor_standalone():
    """Test the resource monitor functions directly."""
    print("=== Testing Resource Monitor Standalone ===")
    
    # Test with normal load
    with patch('src.cc_executor.core.resource_monitor.get_system_load') as mock_load:
        mock_load.return_value = (5.0, 10.0)  # 5% CPU, 10% GPU
        
        multiplier = calculate_timeout_multiplier()
        assert multiplier == 1.0, f"Expected 1.0 multiplier for low load, got {multiplier}"
        
        adjusted = adjust_timeout(30.0)
        assert adjusted == 30.0, f"Expected 30s timeout for low load, got {adjusted}"
        print("✅ Low load test passed: 1x multiplier")
    
    # Test with high CPU load
    with patch('src.cc_executor.core.resource_monitor.get_system_load') as mock_load:
        mock_load.return_value = (25.0, 10.0)  # 25% CPU, 10% GPU
        
        multiplier = calculate_timeout_multiplier()
        assert multiplier == 3.0, f"Expected 3.0 multiplier for high CPU, got {multiplier}"
        
        adjusted = adjust_timeout(30.0)
        assert adjusted == 90.0, f"Expected 90s timeout for high CPU, got {adjusted}"
        print("✅ High CPU load test passed: 3x multiplier")
    
    # Test with high GPU load
    with patch('src.cc_executor.core.resource_monitor.get_system_load') as mock_load:
        mock_load.return_value = (5.0, 20.0)  # 5% CPU, 20% GPU
        
        multiplier = calculate_timeout_multiplier()
        assert multiplier == 3.0, f"Expected 3.0 multiplier for high GPU, got {multiplier}"
        
        adjusted = adjust_timeout(30.0)
        assert adjusted == 90.0, f"Expected 90s timeout for high GPU, got {adjusted}"
        print("✅ High GPU load test passed: 3x multiplier")
    
    # Test with both high
    with patch('src.cc_executor.core.resource_monitor.get_system_load') as mock_load:
        mock_load.return_value = (30.0, 25.0)  # 30% CPU, 25% GPU
        
        multiplier = calculate_timeout_multiplier()
        assert multiplier == 3.0, f"Expected 3.0 multiplier for high load, got {multiplier}"
        print("✅ High CPU+GPU load test passed: 3x multiplier")
    
    # Test with no GPU
    with patch('src.cc_executor.core.resource_monitor.get_system_load') as mock_load:
        mock_load.return_value = (15.0, None)  # 15% CPU, no GPU
        
        multiplier = calculate_timeout_multiplier()
        assert multiplier == 3.0, f"Expected 3.0 multiplier for high CPU (no GPU), got {multiplier}"
        print("✅ No GPU test passed: 3x multiplier based on CPU only")


async def test_websocket_integration():
    """Test WebSocket handler with dynamic timeout adjustment."""
    print("\n=== Testing WebSocket Integration ===")
    
    # Enable stream timeout for testing
    os.environ['ENABLE_STREAM_TIMEOUT'] = 'true'
    os.environ['WEBSOCKET_PORT'] = '8005'  # Use different port for testing
    
    # Start test WebSocket server
    from src.cc_executor.core.websocket_handler import WebSocketHandler
    from src.cc_executor.core.session_manager import SessionManager
    from src.cc_executor.core.process_manager import ProcessManager
    from src.cc_executor.core.stream_handler import StreamHandler
    
    # Create server components
    session_manager = SessionManager(10)
    process_manager = ProcessManager()
    stream_handler = StreamHandler()
    handler = WebSocketHandler(session_manager, process_manager, stream_handler)
    
    # Mock the adjust_timeout function to verify it's called
    original_adjust_timeout = None
    adjust_timeout_called = False
    adjusted_value = None
    
    def mock_adjust_timeout(base_timeout):
        nonlocal adjust_timeout_called, adjusted_value
        adjust_timeout_called = True
        adjusted_value = base_timeout * 3.0  # Simulate high load
        return adjusted_value
    
    # Patch the module
    import src.cc_executor.core.websocket_handler as ws_handler_module
    original_adjust_timeout = ws_handler_module.adjust_timeout
    ws_handler_module.adjust_timeout = mock_adjust_timeout
    
    try:
        # Test WebSocket connection
        async with websockets.connect("ws://localhost:8005/ws", ping_timeout=None) as ws:
            # Send execute command
            await ws.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {"command": "echo 'Testing timeout adjustment'"},
                "id": "test-1"
            }))
            
            # Wait for response
            response_received = False
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                
                if data.get("id") == "test-1":
                    response_received = True
                    print(f"✅ Got response: {data}")
                
                if data.get("method") == "process.completed":
                    break
        
        assert response_received, "Did not receive response from WebSocket"
        assert adjust_timeout_called, "adjust_timeout was not called"
        assert adjusted_value == 1800.0, f"Expected 600*3=1800s adjusted timeout, got {adjusted_value}"
        
        print("✅ WebSocket integration test passed: timeout adjustment verified")
        
    finally:
        # Restore original function
        if original_adjust_timeout:
            ws_handler_module.adjust_timeout = original_adjust_timeout
        
        # Cleanup
        del os.environ['ENABLE_STREAM_TIMEOUT']


async def main():
    """Run all tests."""
    print("Resource Monitor Integration Tests")
    print("=" * 50)
    
    # Test standalone functions
    await test_resource_monitor_standalone()
    
    # Note: WebSocket integration test requires a running server
    print("\nNOTE: WebSocket integration test requires manual setup.")
    print("To test WebSocket integration:")
    print("1. Set ENABLE_STREAM_TIMEOUT=true")
    print("2. Run the WebSocket server")
    print("3. Execute a command and verify timeout adjustment in logs")
    
    print("\n✅ All tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())