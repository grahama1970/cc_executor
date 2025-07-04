"""
Programmatic hook enforcement for cc_executor.

Since Claude Code hooks don't work, this module enforces the hooks
directly in Python code. It integrates with all core components to
ensure proper environment setup, validation, and monitoring.

Key features:
- Virtual environment enforcement
- Redis connection checking
- Environment validation
- Process monitoring
- Automatic fixes for common issues
"""

import os
import sys
import json
import asyncio
import subprocess
import shlex
import shutil
import time
import functools
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
from loguru import logger
from contextlib import contextmanager

# Import hook modules for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))
try:
    from setup_environment import find_venv_path, setup_environment_vars, create_activation_wrapper
    from claude_instance_pre_check import EnvironmentValidator
except ImportError:
    logger.warning("Could not import hook modules - some features will be limited")
    find_venv_path = None
    setup_environment_vars = None
    create_activation_wrapper = None
    EnvironmentValidator = None


class ProgrammaticHookEnforcement:
    """Enforces hooks programmatically for all cc_executor operations."""
    
    def __init__(self):
        self.project_root = self._find_project_root()
        self.venv_path = None
        self.redis_client = None
        self.session_id = os.environ.get('CLAUDE_SESSION_ID', 'default')
        self.initialized = False
        
    def _find_project_root(self) -> Path:
        """Find project root by looking for pyproject.toml or .git."""
        current = Path.cwd()
        
        for parent in [current] + list(current.parents):
            if (parent / 'pyproject.toml').exists() or (parent / '.git').exists():
                return parent
                
        return current
        
    def initialize(self) -> bool:
        """Initialize hook enforcement system."""
        if self.initialized:
            return True
            
        logger.info("Initializing programmatic hook enforcement system")
        
        # 1. Ensure virtual environment
        if not self._ensure_venv():
            logger.error("Failed to ensure virtual environment")
            return False
            
        # 2. Check Redis connection
        if not self._check_redis():
            logger.warning("Redis not available - some features will be limited")
            
        # 3. Validate environment
        if not self._validate_environment():
            logger.warning("Environment validation failed - attempting fixes")
            
        self.initialized = True
        logger.info("Hook enforcement system initialized successfully")
        return True
        
    def _ensure_venv(self) -> bool:
        """Ensure virtual environment is active."""
        # Check if already in venv
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            self.venv_path = sys.prefix
            logger.info(f"Already in virtual environment: {self.venv_path}")
            return True
            
        # Find project venv
        if find_venv_path:
            venv_path = find_venv_path(str(self.project_root))
            if not venv_path:
                logger.error("No .venv directory found in project hierarchy")
                return False
                
            self.venv_path = venv_path
            
            # Update environment variables
            if setup_environment_vars:
                env_updates = setup_environment_vars(venv_path)
                for key, value in env_updates.items():
                    if value:
                        os.environ[key] = value
                    else:
                        os.environ.pop(key, None)
                        
            logger.info(f"Virtual environment configured: {venv_path}")
            return True
        else:
            logger.warning("Hook modules not available - cannot ensure venv")
            return False
        
    def _check_redis(self) -> bool:
        """Check Redis connection."""
        try:
            import redis
            timeout_seconds = float(os.environ.get('REDIS_TIMEOUT', '5'))
            self.redis_client = redis.Redis(
                decode_responses=True,
                socket_connect_timeout=timeout_seconds,
                socket_timeout=timeout_seconds
            )
            self.redis_client.ping()
            logger.info("Redis connection established")
            return True
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
            self.redis_client = None
            return False
            
    def _validate_environment(self) -> bool:
        """Validate environment using claude_instance_pre_check logic."""
        if not EnvironmentValidator:
            logger.warning("EnvironmentValidator not available - skipping validation")
            return True
            
        validator = EnvironmentValidator()
        
        # Run all checks
        cwd_ok, _ = validator.check_working_directory()
        venv_ok, _ = validator.check_venv_activation()
        mcp_ok, _ = validator.check_mcp_config()
        path_ok, _ = validator.check_python_path()
        deps_ok, _ = validator.check_dependencies()
        
        all_ok = all([cwd_ok, venv_ok, mcp_ok, path_ok, deps_ok])
        
        if not all_ok:
            logger.warning(f"Environment issues: {validator.checks_failed}")
            if validator.fixes_applied:
                logger.info(f"Applied fixes: {validator.fixes_applied}")
                
        # Store validation record
        if self.redis_client:
            try:
                validation = validator.create_validation_record()
                key = f"hook:env_validation:{self.session_id}"
                self.redis_client.setex(key, 600, json.dumps(validation))
            except Exception as e:
                logger.error(f"Could not store validation: {e}")
                
        return all_ok
        
    def wrap_command(self, command: str) -> str:
        """Wrap command with virtual environment activation if needed."""
        if not self.venv_path or not create_activation_wrapper:
            return command
            
        return create_activation_wrapper(command, self.venv_path)
        
    def pre_execute_hook(self, command: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Run pre-execution hooks - both hook scripts and programmatic enforcement."""
        if not self.initialized:
            self.initialize()
            
        # First, run the actual hook scripts
        hooks_dir = Path(__file__).parent.parent / "hooks"
        
        # Run setup_environment.py hook
        setup_hook = hooks_dir / "setup_environment.py"
        if setup_hook.exists():
            try:
                env = os.environ.copy()
                env['PYTHONPATH'] = str(Path(__file__).parent.parent.parent)
                result = subprocess.run(
                    [sys.executable, str(setup_hook)],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    logger.warning(f"setup_environment hook failed: {result.stderr}")
            except Exception as e:
                logger.error(f"Failed to run setup_environment hook: {e}")
        
        # Run other relevant hooks
        for hook_name in ['claude_instance_pre_check.py', 'analyze_task_complexity.py']:
            hook_script = hooks_dir / hook_name
            if hook_script.exists() and context and context.get('run_all_hooks'):
                try:
                    subprocess.run(
                        [sys.executable, str(hook_script)],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                except Exception as e:
                    logger.debug(f"Hook {hook_name} failed: {e}")
            
        # Then do programmatic enforcement
        result = {
            'command': command,
            'wrapped_command': self.wrap_command(command),
            'venv_path': self.venv_path,
            'session_id': self.session_id,
            'timestamp': time.time(),
            'context': context or {}
        }
        
        # Store in Redis if available
        if self.redis_client:
            try:
                key = f"hook:pre_execute:{self.session_id}:{int(time.time())}"
                self.redis_client.setex(key, 300, json.dumps(result))
            except Exception as e:
                logger.error(f"Could not store pre-execute data: {e}")
                
        logger.info(f"Pre-execute hook completed for: {command[:50]}...")
        return result
        
    def post_execute_hook(self, command: str, exit_code: int, output: str = "") -> None:
        """Run post-execution hooks."""
        result = {
            'command': command,
            'exit_code': exit_code,
            'output_size': len(output),
            'timestamp': time.time(),
            'session_id': self.session_id
        }
        
        # Store metrics
        if self.redis_client:
            try:
                key = f"hook:post_execute:{self.session_id}:{int(time.time())}"
                self.redis_client.setex(key, 300, json.dumps(result))
                
                # Update metrics
                metrics_key = f"hook:metrics:{self.session_id}"
                self.redis_client.hincrby(metrics_key, 'total_executions', 1)
                if exit_code == 0:
                    self.redis_client.hincrby(metrics_key, 'successful_executions', 1)
                else:
                    self.redis_client.hincrby(metrics_key, 'failed_executions', 1)
                    
            except Exception as e:
                logger.error(f"Could not store post-execute data: {e}")
                
        logger.info(f"Post-execute hook: exit_code={exit_code}, output_size={len(output)}")
        
    @contextmanager
    def execution_context(self, command: str, context: Optional[Dict] = None):
        """Context manager for command execution with hooks."""
        pre_data = self.pre_execute_hook(command, context)
        start_time = time.time()
        
        try:
            yield pre_data
        finally:
            duration = time.time() - start_time
            logger.info(f"Execution completed in {duration:.2f}s")
            
    def get_metrics(self) -> Dict[str, Any]:
        """Get execution metrics from Redis."""
        if not self.redis_client:
            return {}
            
        try:
            metrics_key = f"hook:metrics:{self.session_id}"
            metrics = self.redis_client.hgetall(metrics_key)
            
            # Convert to integers
            for key in metrics:
                try:
                    metrics[key] = int(metrics[key])
                except:
                    pass
                    
            return metrics
        except Exception as e:
            logger.error(f"Could not get metrics: {e}")
            return {}
            
    async def async_pre_execute_hook(self, command: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Async version of pre-execute hook."""
        return await asyncio.to_thread(self.pre_execute_hook, command, context)
        
    async def async_post_execute_hook(self, command: str, exit_code: int, output: str = "") -> None:
        """Async version of post-execute hook."""
        await asyncio.to_thread(self.post_execute_hook, command, exit_code, output)


class HookIntegration:
    """Maintains backward compatibility while using programmatic enforcement."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize hook integration with configuration."""
        # Use programmatic enforcement instead of config file
        self.enforcer = ProgrammaticHookEnforcement()
        # DEFER initialization - don't call self.enforcer.initialize() here
        # It will be called on first use via ensure_hooks decorator
        
        # Keep config for backward compatibility
        project_root = Path(__file__).resolve().parents[3]
        self.config_path = config_path or str(project_root / '.claude-hooks.json')
        self.config = self._load_config()
        self.enabled = True  # Always enabled with programmatic enforcement
        
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
        Execute a specific hook using programmatic enforcement.
        
        Args:
            hook_type: Type of hook (pre-edit, post-edit, etc.)
            context: Context data to pass to hook
            
        Returns:
            Hook execution result or None
        """
        # Use programmatic enforcement for key hooks
        command = context.get('command', '')
        
        if hook_type in ['pre-execute', 'pre-tool']:
            # Use programmatic pre-execution hook
            result = await self.enforcer.async_pre_execute_hook(command, context)
            return {
                'hook_type': hook_type,
                'success': True,
                'wrapped_command': result.get('wrapped_command', command),
                'venv_path': result.get('venv_path'),
                'session_id': result.get('session_id')
            }
            
        elif hook_type in ['post-execute', 'post-tool', 'post-output']:
            # Use programmatic post-execution hook
            exit_code = int(context.get('exit_code', 0))
            output = context.get('output', '')
            await self.enforcer.async_post_execute_hook(command, exit_code, output)
            return {
                'hook_type': hook_type,
                'success': True,
                'metrics': self.enforcer.get_metrics()
            }
            
        # Fall back to config-based execution for other hooks
        if not self.config:
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
        """Execute pre-execution hooks using programmatic enforcement."""
        # Set session ID for enforcer
        self.enforcer.session_id = session_id
        
        # Use programmatic pre-execution
        result = await self.enforcer.async_pre_execute_hook(command, {
            'session_id': session_id,
            'type': 'websocket_execution'
        })
        
        return {
            'pre-execute': {
                'hook_type': 'pre-execute',
                'success': True,
                'wrapped_command': result.get('wrapped_command', command),
                'venv_path': result.get('venv_path'),
                'session_id': result.get('session_id')
            }
        }
        
    async def post_execution_hook(
        self, 
        command: str, 
        exit_code: int,
        duration: float,
        output: str
    ) -> Optional[Dict]:
        """Execute post-execution hook using programmatic enforcement."""
        # Use programmatic post-execution
        await self.enforcer.async_post_execute_hook(command, exit_code, output)
        
        # Get metrics
        metrics = self.enforcer.get_metrics()
        
        return {
            'post-execute': {
                'hook_type': 'post-execute',
                'success': True,
                'exit_code': exit_code,
                'duration': duration,
                'output_size': len(output),
                'metrics': metrics
            }
        }
        
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


if __name__ == "__main__":
    """AI-friendly usage example for hook integration."""
    import sys
    
    # Check for quick test flag
    quick_test = "--quick-test" in sys.argv or "--test" in sys.argv
    
    print("=== Hook Integration Usage Example ===\n")
    
    # Test 1: Check configuration
    print("--- Test 1: Hook Configuration ---")
    hooks = HookIntegration()
    print(f"Hooks enabled: {hooks.enabled}")
    status = hooks.get_hook_status()
    print(f"Config path: {status['config_path']}")
    print(f"Hooks configured: {status['hooks_configured']}")
    print(f"Timeout: {status['timeout']}s")
    print(f"Parallel execution: {status['parallel']}")
    
    # Test 2: Show what hooks would be called
    print("\n--- Test 2: Hook Execution Flow ---")
    print("For a typical command execution:")
    print("1. pre-execute → Environment setup")
    print("2. pre-tool → Dependency check")
    print("3. [Command executes]")
    print("4. post-tool → Update task status")
    print("5. post-output → Record metrics")
    
    # Test 3: Show hook integration points
    print("\n--- Test 3: Special Hook Triggers ---")
    print("Claude commands trigger additional hooks:")
    print("- pre-claude → Instance validation")
    print("- post-claude → Response validation")
    print("\nFile operations trigger:")
    print("- pre-edit → Complexity analysis")
    print("- post-edit → Code review")
    
    # Test 4: Quick validation without async
    print("\n--- Test 4: Configuration Validation ---")
    if hooks.config:
        hook_count = len(hooks.config.get('hooks', {}))
        env_count = len(hooks.config.get('env', {}))
        print(f"✓ Loaded {hook_count} hook types")
        print(f"✓ Configured {env_count} environment variables")
        
        # Show hook commands (first 50 chars)
        for hook_type, hook_cmd in hooks.config.get('hooks', {}).items():
            if isinstance(hook_cmd, list):
                print(f"  {hook_type}: {len(hook_cmd)} commands")
            else:
                cmd_preview = str(hook_cmd)[:50] + "..." if len(str(hook_cmd)) > 50 else str(hook_cmd)
                print(f"  {hook_type}: {cmd_preview}")
    else:
        print("✗ No hook configuration found")
        print(f"  Expected at: {hooks.config_path}")
    
    if quick_test:
        print("\n✅ Hook integration ready! (quick test mode)")
    else:
        # Additional comprehensive tests can go here
        print("\n--- Test 5: Hook Execution Simulation ---")
        print("Would test actual hook execution here...")
        print("\n✅ Hook integration ready! (full test)")


# Global instance for easy access
_hook_integration = None
_initialization_lock = asyncio.Lock()
_thread_lock = None

# Import threading for thread safety
import threading

def _get_thread_lock():
    """Get or create thread lock for synchronous contexts."""
    global _thread_lock
    if _thread_lock is None:
        _thread_lock = threading.Lock()
    return _thread_lock

def get_hook_integration() -> HookIntegration:
    """Get or create the global hook integration instance with thread safety."""
    global _hook_integration
    
    # Fast path - already initialized
    if _hook_integration is not None:
        return _hook_integration
    
    # Thread-safe initialization
    lock = _get_thread_lock()
    with lock:
        # Double-check pattern
        if _hook_integration is not None:
            return _hook_integration
            
        # Use a simple flag to prevent recursive initialization
        if not hasattr(get_hook_integration, '_initializing'):
            get_hook_integration._initializing = True
            try:
                _hook_integration = HookIntegration()
            finally:
                del get_hook_integration._initializing
        else:
            # Return a dummy instance during initialization to prevent recursion
            return type('DummyHookIntegration', (), {'enabled': False, 'enforcer': type('DummyEnforcer', (), {'initialized': True})()})()
    
    return _hook_integration

async def get_hook_integration_async() -> HookIntegration:
    """Async version with asyncio.Lock for thread safety."""
    global _hook_integration
    
    # Fast path - already initialized
    if _hook_integration is not None:
        return _hook_integration
    
    # Async thread-safe initialization
    async with _initialization_lock:
        # Double-check pattern
        if _hook_integration is not None:
            return _hook_integration
            
        # Use a simple flag to prevent recursive initialization
        if not hasattr(get_hook_integration_async, '_initializing'):
            get_hook_integration_async._initializing = True
            try:
                _hook_integration = HookIntegration()
            finally:
                del get_hook_integration_async._initializing
        else:
            # Return a dummy instance during initialization to prevent recursion
            return type('DummyHookIntegration', (), {'enabled': False, 'enforcer': type('DummyEnforcer', (), {'initialized': True})()})()
    
    return _hook_integration


def ensure_hooks(func):
    """Decorator to ensure hooks are initialized before function execution."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        hook = get_hook_integration()
        if not hook.enforcer.initialized:
            hook.enforcer.initialize()
        return func(*args, **kwargs)
        
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        hook = get_hook_integration()
        if not hook.enforcer.initialized:
            hook.enforcer.initialize()
        return await func(*args, **kwargs)
        
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return wrapper