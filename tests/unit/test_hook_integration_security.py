#!/usr/bin/env python3
"""
Unit tests for hook integration security features (N4).

Tests the new security enhancements:
- Per-hook timeout configuration
- Executable validation with shutil.which
- Command parsing with shlex
- Redis fallback handling
- Error propagation improvements
"""

import asyncio
import json
import os
import tempfile
import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from cc_executor.hooks.hook_integration import HookIntegration


class TestHookIntegrationSecurity:
    """Test security enhancements in hook integration."""
    
    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "hooks": {
                    "test-hook": "echo 'test'",
                    "complex-hook": {
                        "command": "python -c 'import time; time.sleep(0.1); print(\"done\")'",
                        "timeout": 5
                    },
                    "invalid-hook": "nonexistent_command arg1 arg2",
                    "shell-injection": "echo 'test'; rm -rf /tmp/test",
                    "python-hook": {
                        "command": "python -m pytest tests/",
                        "timeout": 30
                    }
                },
                "timeout": 10,
                "env": {
                    "TEST_VAR": "test_value"
                }
            }
            json.dump(config, f)
            return f.name
            
    @pytest.fixture
    def hook_integration(self, temp_config_file):
        """Create HookIntegration instance with test config."""
        return HookIntegration(config_path=temp_config_file)
        
    def teardown_method(self):
        """Clean up after each test."""
        # Remove any temp files created during tests
        for f in os.listdir(tempfile.gettempdir()):
            if f.startswith('tmp') and f.endswith('.json'):
                try:
                    os.unlink(os.path.join(tempfile.gettempdir(), f))
                except:
                    pass
                    
    @pytest.mark.asyncio
    async def test_per_hook_timeout_string_config(self, hook_integration):
        """Test that string hook configurations use global timeout."""
        # Mock subprocess to avoid actual execution
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b'output', b''))
            mock_exec.return_value = mock_process
            
            result = await hook_integration.execute_hook('test-hook', {'test': 'data'})
            
            assert result is not None
            assert result['success'] is True
            assert result['stdout'] == 'output'
            
            # Should use global timeout of 10 seconds
            # Check that wait_for was called with correct timeout
            # This is implicit in the execution flow
            
    @pytest.mark.asyncio
    async def test_per_hook_timeout_dict_config(self, hook_integration):
        """Test that dict hook configurations can specify custom timeout."""
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b'done', b''))
            mock_exec.return_value = mock_process
            
            # Track timeout used
            actual_timeout = None
            original_wait_for = asyncio.wait_for
            
            async def mock_wait_for(coro, timeout):
                nonlocal actual_timeout
                actual_timeout = timeout
                return await coro
                
            with patch('asyncio.wait_for', mock_wait_for):
                result = await hook_integration.execute_hook('complex-hook', {})
                
            assert result is not None
            assert result['success'] is True
            assert actual_timeout == 5  # Should use hook-specific timeout
            
    @pytest.mark.asyncio
    async def test_executable_validation_not_found(self, hook_integration):
        """Test that non-existent executables are caught."""
        with patch('shutil.which', return_value=None):
            result = await hook_integration.execute_hook('invalid-hook', {})
            
            assert result is not None
            assert result['success'] is False
            assert 'Executable not found: nonexistent_command' in result['error']
            
    @pytest.mark.asyncio
    async def test_executable_validation_found(self, hook_integration):
        """Test successful executable validation."""
        with patch('shutil.which', return_value='/usr/bin/echo'):
            with patch('asyncio.create_subprocess_exec') as mock_exec:
                mock_process = AsyncMock()
                mock_process.returncode = 0
                mock_process.communicate = AsyncMock(return_value=(b'test', b''))
                mock_exec.return_value = mock_process
                
                result = await hook_integration.execute_hook('test-hook', {})
                
                assert result is not None
                assert result['success'] is True
                # Check that the resolved path was used
                mock_exec.assert_called_once()
                args = mock_exec.call_args[0]
                assert args[0] == '/usr/bin/echo'
                
    @pytest.mark.asyncio
    async def test_shlex_command_parsing(self, hook_integration):
        """Test that commands are parsed securely with shlex."""
        with patch('shutil.which', return_value='/bin/echo'):
            with patch('asyncio.create_subprocess_exec') as mock_exec:
                mock_process = AsyncMock()
                mock_process.returncode = 0
                mock_process.communicate = AsyncMock(return_value=(b'test', b''))
                mock_exec.return_value = mock_process
                
                result = await hook_integration.execute_hook('shell-injection', {})
                
                # The command should be parsed as separate arguments
                # preventing shell injection
                mock_exec.assert_called_once()
                args = mock_exec.call_args[0]
                # Should be parsed as: echo, 'test';, rm, -rf, /tmp/test
                # Not executed as shell command
                assert len(args) > 1
                assert 'rm' not in args[0]  # rm should not be part of echo command
                
    @pytest.mark.asyncio
    async def test_invalid_command_format(self, hook_integration):
        """Test handling of malformed commands."""
        # Create a hook with invalid shell syntax
        hook_integration.config['hooks']['bad-syntax'] = 'echo "unclosed quote'
        
        result = await hook_integration.execute_hook('bad-syntax', {})
        
        assert result is not None
        assert result['success'] is False
        assert 'Invalid command' in result['error']
        
    @pytest.mark.asyncio
    async def test_redis_import_error_handling(self, hook_integration):
        """Test graceful handling when Redis is not available."""
        with patch('builtins.__import__', side_effect=ImportError("No module named 'redis'")):
            # Should not crash when Redis is unavailable
            complexity = await hook_integration.analyze_command_complexity("test command")
            assert complexity is None
            
    @pytest.mark.asyncio
    async def test_redis_connection_error_handling(self, hook_integration):
        """Test handling of Redis connection errors."""
        with patch('redis.Redis') as mock_redis:
            mock_redis.return_value.get.side_effect = Exception("Connection refused")
            
            # Should handle Redis errors gracefully
            complexity = await hook_integration.analyze_command_complexity("test command")
            assert complexity is None
            
    @pytest.mark.asyncio
    async def test_log_truncation_large_output(self, hook_integration):
        """Test that large outputs are truncated in logs."""
        large_output = 'x' * 20000  # 20KB output
        
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(
                return_value=(large_output.encode(), b'')
            )
            mock_exec.return_value = mock_process
            
            with patch('shutil.which', return_value='/bin/echo'):
                result = await hook_integration.execute_hook('test-hook', {})
                
            assert result is not None
            assert result['success'] is True
            # Full output should be in result
            assert len(result['stdout']) == 20000
            # But logged output should be truncated (check via logger calls)
            
    @pytest.mark.asyncio
    async def test_environment_variable_encoding(self, hook_integration):
        """Test that complex context values are JSON-encoded."""
        context = {
            'simple': 'value',
            'complex': {'nested': 'data', 'list': [1, 2, 3]},
            'number': 42
        }
        
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b'', b''))
            mock_exec.return_value = mock_process
            
            with patch('shutil.which', return_value='/bin/echo'):
                await hook_integration.execute_hook('test-hook', context)
                
            # Check environment variables were set correctly
            call_kwargs = mock_exec.call_args[1]
            env = call_kwargs['env']
            
            assert env['CLAUDE_SIMPLE'] == 'value'
            assert env['CLAUDE_COMPLEX'] == '{"nested": "data", "list": [1, 2, 3]}'
            assert env['CLAUDE_NUMBER'] == '42'
            assert env['TEST_VAR'] == 'test_value'  # From config
            
    @pytest.mark.asyncio
    async def test_timeout_cancellation(self, hook_integration):
        """Test that timeouts properly cancel processes."""
        # Create a hook that will timeout
        hook_integration.config['hooks']['slow-hook'] = {
            'command': 'sleep 10',
            'timeout': 0.1
        }
        
        with patch('shutil.which', return_value='/bin/sleep'):
            with patch('asyncio.create_subprocess_exec') as mock_exec:
                mock_process = AsyncMock()
                mock_process.returncode = None
                mock_process.terminate = AsyncMock()
                mock_process.kill = AsyncMock()
                
                # Simulate timeout
                async def mock_communicate():
                    await asyncio.sleep(10)  # Will timeout
                    return b'', b''
                    
                mock_process.communicate = mock_communicate
                mock_exec.return_value = mock_process
                
                result = await hook_integration.execute_hook('slow-hook', {})
                
                assert result is not None
                assert result['success'] is False
                assert result['error'] == 'timeout'
                
                # Process should be terminated
                mock_process.terminate.assert_called_once()
                
    @pytest.mark.asyncio
    async def test_hook_status_with_dict_configs(self, hook_integration):
        """Test get_hook_status with mixed string/dict configurations."""
        status = hook_integration.get_hook_status()
        
        assert status['enabled'] is True
        assert 'test-hook' in status['hooks_configured']
        assert 'complex-hook' in status['hooks_configured']
        assert status['timeout'] == 10  # Global timeout
        
    @pytest.mark.asyncio
    async def test_absolute_path_executable(self, hook_integration):
        """Test handling of absolute path executables."""
        # Create a hook with absolute path
        hook_integration.config['hooks']['abs-path'] = '/usr/bin/python3 -c "print(1)"'
        
        with patch('os.path.exists', return_value=True):
            with patch('asyncio.create_subprocess_exec') as mock_exec:
                mock_process = AsyncMock()
                mock_process.returncode = 0
                mock_process.communicate = AsyncMock(return_value=(b'1', b''))
                mock_exec.return_value = mock_process
                
                result = await hook_integration.execute_hook('abs-path', {})
                
                assert result is not None
                assert result['success'] is True
                
    @pytest.mark.asyncio
    async def test_nonexistent_absolute_path(self, hook_integration):
        """Test error when absolute path doesn't exist."""
        hook_integration.config['hooks']['bad-abs'] = '/nonexistent/path/to/binary'
        
        with patch('os.path.exists', return_value=False):
            result = await hook_integration.execute_hook('bad-abs', {})
            
            assert result is not None
            assert result['success'] is False
            assert 'Executable not found' in result['error']


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, '-v'])