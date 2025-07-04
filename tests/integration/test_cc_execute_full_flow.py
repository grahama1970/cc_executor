#!/usr/bin/env python3
"""
Integration test for cc_execute_utils → websocket_handler full flow.

This test verifies the complete integration between:
- cc_execute_utils.execute_task_via_websocket()
- websocket_handler.py --execute mode
- Claude command execution with streaming
- JSON output collection
- Error handling and retry logic
"""
import os
import sys
import json
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# Import our modules
from cc_executor.prompts.cc_execute_utils import execute_task_via_websocket
from cc_executor.core.websocket_handler import execute_claude_command
from cc_executor.core.models import TimeoutError, RateLimitError


class MockClaudeResponse:
    """Mock Claude subprocess response for testing."""
    
    def __init__(self, stdout_lines=None, stderr_lines=None, returncode=0):
        self.stdout_lines = stdout_lines or []
        self.stderr_lines = stderr_lines or []
        self.returncode = returncode
        self._stdout_iter = iter(self.stdout_lines)
        self._stderr_iter = iter(self.stderr_lines)
        
        # Create mock stdout
        self.stdout = Mock()
        async def stdout_readline():
            try:
                line = next(self._stdout_iter)
                return (line + '\n').encode() if line else b''
            except StopIteration:
                return b''
        self.stdout.readline = stdout_readline
        
        # Create mock stderr  
        self.stderr = Mock()
        async def stderr_readline():
            try:
                line = next(self._stderr_iter)
                return (line + '\n').encode() if line else b''
            except StopIteration:
                return b''
        self.stderr.readline = stderr_readline
    
    async def wait(self):
        """Mock wait method."""
        return self.returncode


def test_simple_execution():
    """Test simple task execution through the full flow."""
    print("\n=== Test 1: Simple Execution ===")
    
    # Mock the subprocess execution
    with patch('subprocess.run') as mock_run:
        # Simulate successful Claude response
        mock_result = Mock()
        mock_result.stdout = json.dumps({
            "type": "message",
            "message": {
                "content": [{"type": "text", "text": "The answer is 4"}]
            }
        })
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        # Execute task
        result = execute_task_via_websocket(
            task="What is 2+2?",
            timeout=30,
            tools=[]
        )
        
        print(f"Success: {result['success']}")
        print(f"Exit code: {result['exit_code']}")
        print(f"Output lines: {len(result['output_lines'])}")
        print(f"Attempts: {result['attempts']}")
        
        assert result['success'] == True
        assert result['exit_code'] == 0
        assert result['attempts'] == 1
        assert mock_run.called
        
    print("✅ Simple execution test passed!")


def test_retry_on_transient_error():
    """Test retry logic for transient errors."""
    print("\n=== Test 2: Retry on Transient Error ===")
    
    call_count = 0
    
    def mock_subprocess_run(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        
        mock_result = Mock()
        if call_count < 3:  # Fail first 2 attempts
            mock_result.stdout = ""
            mock_result.stderr = "Connection reset by peer"
            mock_result.returncode = 1
        else:  # Succeed on 3rd attempt
            mock_result.stdout = json.dumps({
                "type": "message",
                "message": {
                    "content": [{"type": "text", "text": "Success after retry"}]
                }
            })
            mock_result.stderr = ""
            mock_result.returncode = 0
        
        return mock_result
    
    with patch('subprocess.run', side_effect=mock_subprocess_run):
        with patch('time.sleep'):  # Don't actually sleep in tests
            result = execute_task_via_websocket(
                task="Test retry logic",
                timeout=30,
                max_retries=3
            )
            
            print(f"Success: {result['success']}")
            print(f"Attempts: {result['attempts']}")
            print(f"Total calls: {call_count}")
            
            assert result['success'] == True
            assert result['attempts'] == 3
            assert call_count == 3
    
    print("✅ Retry logic test passed!")


def test_rate_limit_handling():
    """Test rate limit detection and retry."""
    print("\n=== Test 3: Rate Limit Handling ===")
    
    call_count = 0
    
    def mock_subprocess_run(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        
        mock_result = Mock()
        if call_count == 1:  # First attempt hits rate limit
            mock_result.stdout = ""
            mock_result.stderr = "Error: 429 Too Many Requests. Retry-After: 5"
            mock_result.returncode = 1
        else:  # Second attempt succeeds
            mock_result.stdout = json.dumps({
                "type": "message",
                "message": {
                    "content": [{"type": "text", "text": "Success after rate limit"}]
                }
            })
            mock_result.stderr = ""
            mock_result.returncode = 0
        
        return mock_result
    
    with patch('subprocess.run', side_effect=mock_subprocess_run):
        with patch('time.sleep') as mock_sleep:
            result = execute_task_via_websocket(
                task="Test rate limit",
                timeout=30,
                max_retries=2
            )
            
            print(f"Success: {result['success']}")
            print(f"Attempts: {result['attempts']}")
            
            # Check that we waited the requested time
            mock_sleep.assert_called_with(5)
            assert result['success'] == True
            assert result['attempts'] == 2
    
    print("✅ Rate limit handling test passed!")


def test_timeout_configuration():
    """Test that timeout is properly configured."""
    print("\n=== Test 4: Timeout Configuration ===")
    
    captured_args = None
    
    def capture_subprocess_args(*args, **kwargs):
        nonlocal captured_args
        captured_args = args[0]  # Get the command args
        
        mock_result = Mock()
        mock_result.stdout = '{"type": "done"}'
        mock_result.stderr = ""
        mock_result.returncode = 0
        return mock_result
    
    with patch('subprocess.run', side_effect=capture_subprocess_args):
        # Test with custom timeout
        result = execute_task_via_websocket(
            task="Test timeout",
            timeout=120
        )
        
        # Check that timeout was passed correctly
        assert "--timeout" in captured_args
        timeout_index = captured_args.index("--timeout")
        assert captured_args[timeout_index + 1] == "120"
        
        print(f"Timeout argument found: {captured_args[timeout_index:timeout_index+2]}")
    
    print("✅ Timeout configuration test passed!")


async def test_websocket_handler_direct():
    """Test websocket_handler execute_claude_command directly."""
    print("\n=== Test 5: Direct WebSocket Handler Test ===")
    
    # Mock the process manager and stream handler
    with patch('cc_executor.core.websocket_handler.ProcessManager') as MockPM:
        with patch('cc_executor.core.websocket_handler.StreamHandler') as MockSH:
            # Setup mocks
            mock_process = MockClaudeResponse(
                stdout_lines=[
                    '{"type": "message_start"}',
                    '{"type": "content_block_start"}',
                    '{"type": "content_block_delta", "delta": {"text": "Hello"}}',
                    '{"type": "content_block_delta", "delta": {"text": " World"}}',
                    '{"type": "content_block_stop"}',
                    '{"type": "message_stop"}'
                ],
                returncode=0
            )
            
            MockPM.return_value.execute_command = asyncio.coroutine(lambda *args, **kwargs: mock_process)
            
            # Mock stream handler to just collect output
            collected_output = []
            async def mock_multiplex(*args, **kwargs):
                callback = args[2]
                # Simulate streaming the stdout
                stdout = args[0]
                while True:
                    line = await stdout.readline()
                    if not line:
                        break
                    await callback('stdout', line.decode().strip())
            
            MockSH.return_value.multiplex_streams = mock_multiplex
            
            # Execute command
            result = await execute_claude_command(
                command='claude -p "Say hello"',
                description="Test direct execution",
                timeout=30
            )
            
            print(f"Exit code: {result['exit_code']}")
            print(f"Output lines: {len(result['output_lines'])}")
            print(f"Duration: {result['duration']:.2f}s")
            
            assert result['exit_code'] == 0
            assert len(result['output_lines']) > 0
            assert result['duration'] > 0
    
    print("✅ Direct WebSocket handler test passed!")


def test_error_propagation():
    """Test that errors are properly propagated."""
    print("\n=== Test 6: Error Propagation ===")
    
    def mock_subprocess_error(*args, **kwargs):
        mock_result = Mock()
        mock_result.stdout = ""
        mock_result.stderr = "Command 'rm -rf /' not allowed"
        mock_result.returncode = 1
        return mock_result
    
    with patch('subprocess.run', side_effect=mock_subprocess_error):
        result = execute_task_via_websocket(
            task="Delete everything",
            tools=["Bash"],
            max_retries=1  # Don't retry permission errors
        )
        
        print(f"Success: {result['success']}")
        print(f"Exit code: {result['exit_code']}")
        print(f"Error: {result['stderr']}")
        
        assert result['success'] == False
        assert result['exit_code'] == 1
        assert "not allowed" in result['stderr']
    
    print("✅ Error propagation test passed!")


def test_tool_configuration():
    """Test that tools are properly configured in the command."""
    print("\n=== Test 7: Tool Configuration ===")
    
    captured_command = None
    
    def capture_command(*args, **kwargs):
        nonlocal captured_command
        # The command is in the args list after "--execute"
        cmd_args = args[0]
        if "--execute" in cmd_args:
            exec_index = cmd_args.index("--execute")
            captured_command = cmd_args[exec_index + 1]
        
        mock_result = Mock()
        mock_result.stdout = '{"type": "done"}'
        mock_result.stderr = ""
        mock_result.returncode = 0
        return mock_result
    
    with patch('subprocess.run', side_effect=capture_command):
        # Test with specific tools
        result = execute_task_via_websocket(
            task="Test tools",
            tools=["Read", "Write", "Bash", "WebSearch"]
        )
        
        print(f"Captured command: {captured_command}")
        
        # Check that tools were included
        assert "--allowedTools" in captured_command
        assert "Read" in captured_command
        assert "Write" in captured_command
        assert "Bash" in captured_command
        assert "WebSearch" in captured_command
    
    print("✅ Tool configuration test passed!")


if __name__ == "__main__":
    print("=== CC Execute Full Flow Integration Tests ===")
    print("Testing the integration between cc_execute_utils and websocket_handler")
    
    # Set test environment
    os.environ["DEFAULT_EXECUTION_TIMEOUT"] = "600"
    
    try:
        # Run synchronous tests
        test_simple_execution()
        test_retry_on_transient_error()
        test_rate_limit_handling()
        test_timeout_configuration()
        test_error_propagation()
        test_tool_configuration()
        
        # Run async test
        print("\nRunning async tests...")
        asyncio.run(test_websocket_handler_direct())
        
        print("\n✅ All integration tests passed!")
        print("\nSummary:")
        print("- Simple execution: PASS")
        print("- Retry logic: PASS")
        print("- Rate limit handling: PASS")
        print("- Timeout configuration: PASS")
        print("- Direct handler execution: PASS")
        print("- Error propagation: PASS")
        print("- Tool configuration: PASS")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)