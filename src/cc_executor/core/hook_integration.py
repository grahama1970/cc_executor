"""
Hook integration module for WebSocket handler.

This module provides methods to execute Anthropic Claude Code hooks
at various lifecycle points during command execution.
"""

import os
import json
import asyncio
import subprocess
import shlex
import shutil
from typing import Dict, Optional, Any
from loguru import logger
from pathlib import Path

class HookIntegration:
    """Manages execution of Claude Code hooks."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize hook integration with configuration."""
        # F1: Fix brittle config path calculation using pathlib
        project_root = Path(__file__).resolve().parents[3]
        self.config_path = config_path or str(project_root / '.claude-hooks.json')
        self.config = self._load_config()
        self.enabled = bool(self.config)
        
    def _load_config(self) -> Optional[Dict]:
        """Load hook configuration from file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Loaded hook configuration from {self.config_path}")
                return config
            else:
                logger.debug(f"No hook configuration found at {self.config_path}")
                return None
        except Exception as e:
            logger.error(f"Error loading hook configuration: {e}")
            return None
            
    async def execute_hook(self, hook_type: str, context: Dict[str, Any]) -> Optional[Dict]:
        """
        Execute a specific hook if configured.
        
        Args:
            hook_type: Type of hook (pre-edit, post-edit, etc.)
            context: Context data to pass to hook
            
        Returns:
            Hook execution result or None
        """
        if not self.enabled or not self.config:
            return None
            
        hooks = self.config.get('hooks', {})
        hook_config = hooks.get(hook_type)
        
        if not hook_config:
            return None
            
        # Support arrays of hooks for a single event
        if isinstance(hook_config, list):
            # Execute multiple hooks in sequence
            results = []
            for hook_item in hook_config:
                result = await self._execute_single_hook(hook_type, hook_item, context)
                if result:
                    results.append(result)
            # Return combined results
            return {'hook_type': hook_type, 'results': results, 'multi': True} if results else None
        else:
            # Single hook execution
            return await self._execute_single_hook(hook_type, hook_config, context)
    
    async def _execute_single_hook(self, hook_type: str, hook_config: Any, context: Dict[str, Any]) -> Optional[Dict]:
        """Execute a single hook command."""
        # N1: Support both string and dict hook configurations
        if isinstance(hook_config, dict):
            hook_cmd = hook_config.get('command', '')
            if not hook_cmd:
                return None
        else:
            hook_cmd = hook_config
            
        try:
            # Build environment with context
            env = os.environ.copy()
            env.update(self.config.get('env', {}))
            
            # Add context as environment variables
            # F3: JSON-encode non-primitive context values
            for key, value in context.items():
                env_key = f"CLAUDE_{key.upper()}"
                if isinstance(value, (dict, list)):
                    env[env_key] = json.dumps(value)
                else:
                    env[env_key] = str(value)
                
            # Execute hook
            # N1: Support per-hook timeout with fallback to global timeout
            if isinstance(hook_config, dict):
                # Hook has configuration object
                timeout = hook_config.get('timeout', self.config.get('timeout', 60))
            else:
                # Hook is just a command string
                timeout = self.config.get('timeout', 60)
            
            # N6: Downgrade hook command logging from INFO to DEBUG
            logger.debug(f"Executing {hook_type} hook: {hook_cmd[:50]}...")
            
            # F2: Use asyncio.create_subprocess_exec with shlex.split for security
            # Parse command into args list to avoid shell injection
            try:
                cmd_args = shlex.split(hook_cmd)
            except ValueError as e:
                logger.error(f"Invalid hook command format: {e}")
                return {'hook_type': hook_type, 'error': f'Invalid command: {e}', 'success': False}
            
            # N7: Add executable validation using shutil.which
            import shutil
            executable = cmd_args[0]
            
            # Check if it's an absolute path or needs to be found in PATH
            if not os.path.isabs(executable):
                resolved_executable = shutil.which(executable)
                if not resolved_executable:
                    logger.error(f"Hook executable not found: {executable}")
                    return {'hook_type': hook_type, 'error': f'Executable not found: {executable}', 'success': False}
                cmd_args[0] = resolved_executable
            elif not os.path.exists(executable):
                logger.error(f"Hook executable does not exist: {executable}")
                return {'hook_type': hook_type, 'error': f'Executable not found: {executable}', 'success': False}
            
            # Use asyncio subprocess for non-blocking execution
            proc = await asyncio.create_subprocess_exec(
                *cmd_args,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )
                
                # N8: Add log truncation for large outputs
                stdout_str = stdout.decode() if stdout else ''
                stderr_str = stderr.decode() if stderr else ''
                
                # Truncate very large outputs for logging
                LOG_MAX_LENGTH = 10000
                stdout_truncated = stdout_str[:LOG_MAX_LENGTH] + '...' if len(stdout_str) > LOG_MAX_LENGTH else stdout_str
                stderr_truncated = stderr_str[:LOG_MAX_LENGTH] + '...' if len(stderr_str) > LOG_MAX_LENGTH else stderr_str
                
                result = {
                    'hook_type': hook_type,
                    'exit_code': proc.returncode,
                    'stdout': stdout_str,  # Keep full output in result
                    'stderr': stderr_str,  # Keep full output in result
                    'success': proc.returncode == 0
                }
                
                # Log truncated versions
                if stdout_truncated:
                    logger.debug(f"Hook {hook_type} stdout ({len(stdout_str)} bytes): {stdout_truncated[:500]}...")
                if stderr_truncated and proc.returncode != 0:
                    logger.debug(f"Hook {hook_type} stderr ({len(stderr_str)} bytes): {stderr_truncated[:500]}...")
                
                if proc.returncode != 0:
                    logger.warning(f"Hook {hook_type} failed with exit code {proc.returncode}")
                        
                return result
                
            except asyncio.TimeoutError:
                logger.error(f"Hook {hook_type} timed out after {timeout}s")
                try:
                    proc.terminate()
                    await asyncio.sleep(0.5)
                    if proc.returncode is None:
                        proc.kill()
                except:
                    pass
                return {'hook_type': hook_type, 'error': 'timeout', 'success': False}
                
        except Exception as e:
            logger.error(f"Error executing {hook_type} hook: {e}")
            return {'hook_type': hook_type, 'error': str(e), 'success': False}
            
    async def pre_execution_hook(self, command: str, session_id: str) -> Optional[Dict]:
        """Execute pre-execution hooks for environment setup and command analysis."""
        results = {}
        
        # First run environment setup hook
        env_context = {
            'command': command,
            'session_id': session_id
        }
        
        env_result = await self.execute_hook('pre-execute', env_context)
        if env_result:
            results['pre-execute'] = env_result
            
        # Run Claude-specific pre-check if it's a Claude command
        if 'claude' in command.lower():
            claude_result = await self.execute_hook('pre-claude', env_context)
            if claude_result:
                results['pre-claude'] = claude_result
            
        # Then run dependency check hook
        context = {
            'command': command,
            'session_id': session_id,
            'file': 'websocket_command',
            'context': json.dumps({'type': 'websocket_execution', 'command': command})
        }
        
        tool_result = await self.execute_hook('pre-tool', context)
        if tool_result:
            results['pre-tool'] = tool_result
            
        return results if results else None
        
    async def post_execution_hook(
        self, 
        command: str, 
        exit_code: int,
        duration: float,
        output: str
    ) -> Optional[Dict]:
        """Execute post-execution hook for metrics and analysis."""
        context = {
            'command': command,
            'exit_code': str(exit_code),
            'duration': str(duration),
            'output': output[:1000],  # Truncate long outputs
            'task': f"WebSocket command: {command[:100]}",
            'tokens': str(len(output.split()))  # Rough token estimate
        }
        
        # Execute both post-tool and post-output hooks
        results = {}
        
        tool_result = await self.execute_hook('post-tool', context)
        if tool_result:
            results['post-tool'] = tool_result
            
        output_result = await self.execute_hook('post-output', context)
        if output_result:
            results['post-output'] = output_result
            
        # Run Claude response validation if it was a Claude command
        if 'claude' in command.lower():
            claude_context = {
                'command': command,
                'output': output,
                'exit_code': str(exit_code),
                'session_id': context.get('session_id', 'default')
            }
            claude_result = await self.execute_hook('post-claude', claude_context)
            if claude_result:
                results['post-claude'] = claude_result
            
        return results if results else None
        
    async def analyze_command_complexity(self, command: str) -> Optional[Dict]:
        """
        Use pre-edit hook to analyze command complexity.
        
        Returns:
            Complexity analysis including estimated timeout
        """
        # Create a temporary file with the command for analysis
        import tempfile
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(f"# Task\n\n{command}\n")
                temp_file = f.name
                
            context = {
                'file': temp_file,
                'command': command
            }
            
            result = await self.execute_hook('pre-edit', context)
            
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
                
            if result and result.get('success'):
                # Try to read complexity data from Redis
                try:
                    # N3: Fix Redis absence handling - proper import check
                    import redis
                    r = redis.Redis(decode_responses=True)
                    
                    key = f"task:current:{os.path.basename(temp_file)}"
                    complexity_data = r.get(key)
                    
                    if complexity_data:
                        return json.loads(complexity_data)
                except ImportError:
                    logger.debug("Redis module not available - skipping complexity data retrieval")
                except Exception as e:
                    logger.debug(f"Could not read complexity data from Redis: {e}")
                    
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing command complexity: {e}")
            return None
            
    def get_hook_status(self) -> Dict[str, Any]:
        """Get current hook configuration status."""
        return {
            'enabled': self.enabled,
            'config_path': self.config_path,
            'hooks_configured': list(self.config.get('hooks', {}).keys()) if self.config else [],
            'timeout': self.config.get('timeout', 60) if self.config else None,
            'parallel': self.config.get('parallel', False) if self.config else False
        }


# Example usage
if __name__ == "__main__":
    async def test_hooks():
        """Test hook integration."""
        hooks = HookIntegration()
        
        print(f"Hooks enabled: {hooks.enabled}")
        print(f"Hook status: {hooks.get_hook_status()}")
        
        if hooks.enabled:
            # Test pre-execution hook
            result = await hooks.pre_execution_hook(
                "echo 'Hello from WebSocket'",
                "test-session-123"
            )
            print(f"Pre-execution result: {result}")
            
            # Test complexity analysis
            complexity = await hooks.analyze_command_complexity(
                "What is a FastAPI endpoint that adds two numbers and returns JSON?"
            )
            print(f"Complexity analysis: {complexity}")
            
            # Test post-execution hook
            result = await hooks.post_execution_hook(
                "echo 'Hello'",
                exit_code=0,
                duration=1.5,
                output="Hello\n"
            )
            print(f"Post-execution result: {result}")
            
    asyncio.run(test_hooks())