#!/usr/bin/env python3
"""
Unit tests for WebSocket handler error propagation (N2).

Tests improved error propagation when pre-execute hooks fail,
especially for invalid commands.
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from cc_executor.core.websocket_handler import WebSocketHandler
from cc_executor.core.session_manager import SessionManager
from cc_executor.core.process_manager import ProcessManager
from cc_executor.core.stream_handler import StreamHandler


class TestWebSocketErrorPropagation:
    """Test error propagation improvements in WebSocket handler."""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.client = "test_client"
        ws.application_state = "connected"
        ws.client_state = "connected"
        return ws
        
    @pytest.fixture
    def handler(self):
        """Create WebSocketHandler with mocked dependencies."""
        session_manager = SessionManager(max_sessions=10)
        process_manager = ProcessManager()
        stream_handler = StreamHandler()
        
        handler = WebSocketHandler(
            session_manager=session_manager,
            process_manager=process_manager,
            stream_handler=stream_handler,
            heartbeat_interval=30
        )
        
        # Mock hook integration
        handler.hooks = Mock()
        handler.hooks.enabled = True
        
        return handler
        
    @pytest.mark.asyncio
    async def test_pre_execute_hook_failure_notification(self, handler, mock_websocket):
        """Test that pre-execute hook failures send warning notifications."""
        session_id = "test-session"
        
        # Create session
        session = Mock()
        session.websocket = mock_websocket
        session.process = None
        session.pgid = None
        
        # Mock session manager
        handler.sessions.get_session = AsyncMock(return_value=session)
        
        # Mock hook failure
        hook_result = {
            'pre-execute': {
                'success': False,
                'error': 'Command not found: invalid_cmd',
                'stderr': 'bash: invalid_cmd: command not found\n',
                'hook_type': 'pre-execute'
            }
        }
        handler.hooks.pre_execution_hook = AsyncMock(return_value=hook_result)
        handler.hooks.analyze_command_complexity = AsyncMock(return_value=None)
        
        # Mock process execution
        mock_process = AsyncMock()
        mock_process.pid = 12345
        handler.processes.execute_command = AsyncMock(return_value=mock_process)
        handler.processes.get_process_group_id = Mock(return_value=12345)
        
        # Mock session update
        handler.sessions.update_session = AsyncMock()
        
        # Execute command
        params = {"command": "invalid_cmd --help", "timeout": None}
        await handler._handle_execute(session_id, params, msg_id=1)
        
        # Verify warning notification was sent
        calls = mock_websocket.send_json.call_args_list
        
        # Find the hook warning notification
        hook_warning_sent = False
        validation_warning_sent = False
        
        for call in calls:
            msg = call[0][0]
            if msg.get('method') == 'hook.warning':
                hook_warning_sent = True
                params = msg['params']
                assert params['hook_type'] == 'pre-execute'
                assert 'Command not found' in params['error']
                assert params['severity'] == 'warning'
                assert 'command not found' in params['stderr']
                
            elif msg.get('method') == 'command.validation_warning':
                validation_warning_sent = True
                params = msg['params']
                assert 'invalid_cmd' in params['command']
                assert 'invalid' in params['warning'].lower()
                
        assert hook_warning_sent, "Hook warning notification not sent"
        assert validation_warning_sent, "Command validation warning not sent"
        
    @pytest.mark.asyncio
    async def test_multiple_hook_failures(self, handler, mock_websocket):
        """Test handling of multiple hook failures."""
        session_id = "test-session"
        
        # Create session
        session = Mock()
        session.websocket = mock_websocket
        session.process = None
        session.pgid = None
        
        handler.sessions.get_session = AsyncMock(return_value=session)
        
        # Mock multiple hook failures
        hook_result = {
            'pre-execute': {
                'success': False,
                'error': 'Environment setup failed',
                'stderr': 'Error: venv not found',
                'hook_type': 'pre-execute'
            },
            'pre-tool': {
                'success': False,
                'error': 'Dependency check failed',
                'stderr': 'Missing required tool: git',
                'hook_type': 'pre-tool'
            }
        }
        handler.hooks.pre_execution_hook = AsyncMock(return_value=hook_result)
        handler.hooks.analyze_command_complexity = AsyncMock(return_value=None)
        
        # Mock process execution
        mock_process = AsyncMock()
        mock_process.pid = 12345
        handler.processes.execute_command = AsyncMock(return_value=mock_process)
        handler.processes.get_process_group_id = Mock(return_value=12345)
        handler.sessions.update_session = AsyncMock()
        
        # Execute command
        params = {"command": "pytest tests/", "timeout": None}
        await handler._handle_execute(session_id, params, msg_id=1)
        
        # Verify both warnings were sent
        calls = mock_websocket.send_json.call_args_list
        
        hook_warnings = []
        for call in calls:
            msg = call[0][0]
            if msg.get('method') == 'hook.warning':
                hook_warnings.append(msg['params'])
                
        assert len(hook_warnings) == 2
        
        # Check both warnings
        hook_types = [w['hook_type'] for w in hook_warnings]
        assert 'pre-execute' in hook_types
        assert 'pre-tool' in hook_types
        
    @pytest.mark.asyncio
    async def test_hook_success_no_warning(self, handler, mock_websocket):
        """Test that successful hooks don't send warnings."""
        session_id = "test-session"
        
        # Create session
        session = Mock()
        session.websocket = mock_websocket
        session.process = None
        session.pgid = None
        
        handler.sessions.get_session = AsyncMock(return_value=session)
        
        # Mock successful hooks
        hook_result = {
            'pre-execute': {
                'success': True,
                'stdout': 'Environment setup complete',
                'stderr': '',
                'hook_type': 'pre-execute'
            }
        }
        handler.hooks.pre_execution_hook = AsyncMock(return_value=hook_result)
        handler.hooks.analyze_command_complexity = AsyncMock(return_value=None)
        
        # Mock process execution
        mock_process = AsyncMock()
        mock_process.pid = 12345
        handler.processes.execute_command = AsyncMock(return_value=mock_process)
        handler.processes.get_process_group_id = Mock(return_value=12345)
        handler.sessions.update_session = AsyncMock()
        
        # Execute command
        params = {"command": "echo 'test'", "timeout": None}
        await handler._handle_execute(session_id, params, msg_id=1)
        
        # Verify no warning notifications
        calls = mock_websocket.send_json.call_args_list
        
        for call in calls:
            msg = call[0][0]
            assert msg.get('method') != 'hook.warning'
            assert msg.get('method') != 'command.validation_warning'
            
    @pytest.mark.asyncio
    async def test_stderr_truncation(self, handler, mock_websocket):
        """Test that long stderr output is truncated in notifications."""
        session_id = "test-session"
        
        # Create session
        session = Mock()
        session.websocket = mock_websocket
        session.process = None
        session.pgid = None
        
        handler.sessions.get_session = AsyncMock(return_value=session)
        
        # Mock hook with very long stderr
        long_stderr = "Error: " + "x" * 1000  # 1000+ character error
        hook_result = {
            'pre-execute': {
                'success': False,
                'error': 'Command failed',
                'stderr': long_stderr,
                'hook_type': 'pre-execute'
            }
        }
        handler.hooks.pre_execution_hook = AsyncMock(return_value=hook_result)
        handler.hooks.analyze_command_complexity = AsyncMock(return_value=None)
        
        # Mock process execution
        mock_process = AsyncMock()
        mock_process.pid = 12345
        handler.processes.execute_command = AsyncMock(return_value=mock_process)
        handler.processes.get_process_group_id = Mock(return_value=12345)
        handler.sessions.update_session = AsyncMock()
        
        # Execute command
        params = {"command": "test command", "timeout": None}
        await handler._handle_execute(session_id, params, msg_id=1)
        
        # Find hook warning
        calls = mock_websocket.send_json.call_args_list
        
        for call in calls:
            msg = call[0][0]
            if msg.get('method') == 'hook.warning':
                params = msg['params']
                # Stderr should be truncated to 500 chars
                assert len(params['stderr']) <= 500
                assert params['stderr'].startswith('Error: ')
                break
        else:
            pytest.fail("Hook warning not found")
            
    @pytest.mark.asyncio
    async def test_hook_exception_handling(self, handler, mock_websocket):
        """Test handling when hook execution throws exception."""
        session_id = "test-session"
        
        # Create session
        session = Mock()
        session.websocket = mock_websocket
        session.process = None
        session.pgid = None
        
        handler.sessions.get_session = AsyncMock(return_value=session)
        
        # Mock hook exception
        handler.hooks.pre_execution_hook = AsyncMock(
            side_effect=Exception("Hook system error")
        )
        
        # Mock process execution (should still work)
        mock_process = AsyncMock()
        mock_process.pid = 12345
        handler.processes.execute_command = AsyncMock(return_value=mock_process)
        handler.processes.get_process_group_id = Mock(return_value=12345)
        handler.sessions.update_session = AsyncMock()
        
        # Execute command - should not crash
        params = {"command": "echo 'test'", "timeout": None}
        await handler._handle_execute(session_id, params, msg_id=1)
        
        # Command should still execute
        handler.processes.execute_command.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_no_hooks_enabled(self, handler, mock_websocket):
        """Test behavior when hooks are disabled."""
        session_id = "test-session"
        
        # Disable hooks
        handler.hooks = None
        
        # Create session
        session = Mock()
        session.websocket = mock_websocket
        session.process = None
        session.pgid = None
        
        handler.sessions.get_session = AsyncMock(return_value=session)
        
        # Mock process execution
        mock_process = AsyncMock()
        mock_process.pid = 12345
        handler.processes.execute_command = AsyncMock(return_value=mock_process)
        handler.processes.get_process_group_id = Mock(return_value=12345)
        handler.sessions.update_session = AsyncMock()
        
        # Execute command
        params = {"command": "echo 'test'", "timeout": None}
        await handler._handle_execute(session_id, params, msg_id=1)
        
        # Should execute without any hook warnings
        calls = mock_websocket.send_json.call_args_list
        
        for call in calls:
            msg = call[0][0]
            assert 'hook' not in msg.get('method', '')


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, '-v'])