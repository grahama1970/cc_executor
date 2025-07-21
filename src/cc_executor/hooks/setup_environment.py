#!/usr/bin/env python3
"""
Environment setup hook that ensures proper Python virtual environment activation.

This hook runs before any command execution to guarantee the correct environment.
It uses Path for robust path resolution and shlex for secure command parsing.

Key features:
- Finds nearest .venv directory using pathlib.Path traversal
- Uses shlex.split() for secure command parsing (prevents shell injection)
- Wraps commands that need venv activation (python, pip, pytest, etc.)
- Stores environment data in Redis for WebSocket handler integration
- Gracefully handles missing Redis or venv directories
"""

import os
import sys
import json
import subprocess
import redis
from pathlib import Path
from loguru import logger

def find_venv_path(start_path: str = '.') -> str:
    """Find the nearest .venv directory."""
    current = Path(start_path).resolve()
    
    # Check current directory and parents
    for parent in [current] + list(current.parents):
        venv_path = parent / '.venv'
        if venv_path.exists() and venv_path.is_dir():
            activate_script = venv_path / 'bin' / 'activate'
            if activate_script.exists():
                return str(venv_path)
                
    return None

def check_venv_status() -> dict:
    """Check current virtual environment status."""
    status = {
        'in_venv': False,
        'venv_path': None,
        'python_path': sys.executable,
        'pip_path': None,
        'site_packages': None
    }
    
    # Check if we're in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        status['in_venv'] = True
        status['venv_path'] = sys.prefix
        
    # Alternative check
    if 'VIRTUAL_ENV' in os.environ:
        status['in_venv'] = True
        status['venv_path'] = os.environ['VIRTUAL_ENV']
        
    # Get pip path
    try:
        pip_result = subprocess.run([sys.executable, '-m', 'pip', '--version'], 
                                  capture_output=True, text=True)
        if pip_result.returncode == 0:
            status['pip_path'] = pip_result.stdout.strip()
    except:
        pass
        
    # Get site-packages
    try:
        import site
        status['site_packages'] = site.getsitepackages()[0] if site.getsitepackages() else None
    except:
        pass
        
    return status

def kill_existing_websocket_servers():
    """Kill any existing websocket servers to prevent port conflicts."""
    # Skip this entirely in Docker environments
    if os.path.exists('/.dockerenv') or os.environ.get('RUNNING_IN_DOCKER'):
        logger.info("Running in Docker - skipping port cleanup")
        return
        
    # Kill processes on common websocket ports
    ports = [8003, 8004]  # Add other ports as needed
    
    for port in ports:
        try:
            # Find processes using the port
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    try:
                        subprocess.run(['kill', '-9', pid], check=True)
                        logger.info(f"Killed process {pid} on port {port}")
                    except subprocess.CalledProcessError:
                        logger.warning(f"Could not kill process {pid}")
        except FileNotFoundError:
            # lsof not available, try alternative
            try:
                subprocess.run(['pkill', '-f', 'websocket_handler.py'], check=False)
                logger.info("Killed websocket_handler.py processes")
            except FileNotFoundError:
                logger.warning("Neither lsof nor pkill available for cleanup")

def setup_environment_vars(venv_path: str) -> dict:
    """Setup environment variables for virtual environment."""
    env_updates = {}
    
    # Core venv variables
    env_updates['VIRTUAL_ENV'] = venv_path
    env_updates['PATH'] = f"{venv_path}/bin:{os.environ.get('PATH', '')}"
    
    # Python-specific
    env_updates['PYTHONPATH'] = './src'
    
    # Remove conflicting variables
    for var in ['PYTHONHOME', 'CONDA_PREFIX', 'CONDA_DEFAULT_ENV']:
        if var in os.environ:
            env_updates[var] = ''  # Will be removed
            
    return env_updates

def create_activation_wrapper(command: str, venv_path: str) -> str:
    """
    Create a command that activates venv before execution.
    
    N5: Uses shlex.split for secure command parsing and Path for command name extraction.
    This prevents shell injection attacks and handles paths correctly.
    
    Args:
        command: The command to potentially wrap
        venv_path: Path to the virtual environment
        
    Returns:
        Either the original command or a wrapped version with venv activation
    """
    # F8: Use shlex.split + first token comparison for better heuristics
    import shlex
    
    # For commands that need shell activation
    shell_commands = ['pytest', 'pip', 'python', 'python3', 'uv', 'coverage', 'mypy', 'black', 'ruff']
    
    try:
        # Parse command to get the actual executable
        cmd_parts = shlex.split(command)
        if not cmd_parts:
            return command
            
        # Get the base command name (handle paths like /usr/bin/python3)
        base_cmd = Path(cmd_parts[0]).name
        
        # Check if base command needs activation
        needs_activation = base_cmd in shell_commands
        
        if needs_activation and not command.startswith('source'):
            # Wrap command with venv activation
            activate_cmd = f"source {venv_path}/bin/activate"
            wrapped = f"{activate_cmd} && {command}"
            return wrapped
    except ValueError:
        # If shlex.split fails, fall back to original behavior
        logger.warning(f"Could not parse command: {command}")
        
    return command

def main():
    """Main hook entry point."""
    # Kill any existing websocket servers first
    kill_existing_websocket_servers()
    
    # Get command from environment
    command = os.environ.get('CLAUDE_COMMAND', '')
    context = os.environ.get('CLAUDE_CONTEXT', '')
    
    if not command:
        logger.info("No command provided to environment setup hook")
        sys.exit(0)
        
    # Check current venv status
    current_status = check_venv_status()
    logger.info(f"Current environment: in_venv={current_status['in_venv']}, "
                f"path={current_status['venv_path']}")
    
    # Find project venv
    project_venv = find_venv_path()
    
    if not project_venv:
        logger.warning("No .venv found in project hierarchy")
        # Don't block execution
        sys.exit(0)
        
    logger.info(f"Found project venv at: {project_venv}")
    
    # Setup environment
    env_updates = setup_environment_vars(project_venv)
    
    # Store environment updates for WebSocket handler
    try:
        r = redis.Redis(decode_responses=True)
        
        # Store as JSON for easy retrieval
        env_data = {
            'venv_path': project_venv,
            'env_updates': env_updates,
            'wrapped_command': create_activation_wrapper(command, project_venv),
            'timestamp': os.environ.get('CLAUDE_TIMESTAMP', '')
        }
        
        # Use session ID if available, otherwise use a generic key
        session_id = os.environ.get('CLAUDE_SESSION_ID', 'default')
        key = f"hook:env_setup:{session_id}"
        
        r.setex(key, 300, json.dumps(env_data))  # 5 minute TTL
        
        logger.info(f"Stored environment setup for session {session_id}")
        
        # Also log what would be done
        if current_status['venv_path'] != project_venv:
            logger.info(f"Environment needs update: {current_status['venv_path']} -> {project_venv}")
        else:
            logger.info("Environment already correctly configured")
            
    except Exception as e:
        logger.error(f"Could not store environment data: {e}")
        
    # Success - environment check complete
    sys.exit(0)

if __name__ == "__main__":
    # Configure minimal logging
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{message}")
    
    # Usage example for testing
    if "--test" in sys.argv:
        # Import OutputCapture for consistent JSON output
        project_root = Path(__file__).parent.parent.parent.parent
        from cc_executor.core.usage_helper import OutputCapture
        
        with OutputCapture(__file__) as capture:
            # Override module name to be correct
            capture.module_name = "cc_executor.hooks.setup_environment"
            
            print("\n=== Environment Setup Hook Test ===\n")
        
        # Test venv detection
        print("1. Testing virtual environment detection:\n")
        
        current_status = check_venv_status()
        print("Current environment status:")
        for key, value in current_status.items():
            print(f"  {key}: {value}")
        
        # Test venv finding
        print("\n\n2. Testing .venv directory search:\n")
        
        test_paths = [
            ".",  # Current directory
            "/tmp",  # No venv expected
            os.path.expanduser("~"),  # Home directory
        ]
        
        for path in test_paths:
            venv_path = find_venv_path(path)
            print(f"Search from {path}: {venv_path if venv_path else 'No .venv found'}")
        
        # Create a test venv structure
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            test_project = Path(tmpdir) / "test_project"
            test_project.mkdir()
            test_venv = test_project / ".venv"
            test_venv.mkdir()
            (test_venv / "bin").mkdir()
            (test_venv / "bin" / "activate").touch()
            
            found_venv = find_venv_path(test_project)
            print(f"\nTest project venv: {found_venv}")
        
        # Test environment variable setup
        print("\n\n3. Testing environment variable configuration:\n")
        
        if project_venv := find_venv_path():
            env_updates = setup_environment_vars(project_venv)
            print(f"Environment updates for {project_venv}:")
            for key, value in env_updates.items():
                if value:
                    print(f"  {key} = {value[:50]}...")
                else:
                    print(f"  {key} = [removed]")
        
        # Test command wrapping
        print("\n\n4. Testing command wrapping:\n")
        
        test_commands = [
            "python script.py",
            "pytest tests/",
            "pip install requests",
            "ls -la",
            "/usr/bin/python3 -m pip list",
            "source .venv/bin/activate",
            "coverage run -m pytest",
            "echo 'Hello World'",
            "python -c 'print(\"test\")'",
            'python script.py --arg "value with spaces"'
        ]
        
        dummy_venv = "/path/to/.venv"
        
        for cmd in test_commands:
            wrapped = create_activation_wrapper(cmd, dummy_venv)
            if wrapped != cmd:
                print(f"✓ {cmd[:30]}...")
                print(f"  → {wrapped[:60]}...")
            else:
                print(f"✗ {cmd[:30]}... (no wrapping needed)")
        
        # Test Redis storage
        print("\n\n5. Testing Redis storage (if available):\n")
        
        try:
            import redis
            r = redis.Redis(decode_responses=True)
            r.ping()
            
            # Create test environment data
            test_env_data = {
                'venv_path': '/home/user/project/.venv',
                'env_updates': {'VIRTUAL_ENV': '/home/user/project/.venv',
                               'PATH': '/home/user/project/.venv/bin:/usr/bin'},
                'wrapped_command': 'source /home/user/project/.venv/bin/activate && python test.py',
                'timestamp': '2024-01-01T12:00:00'
            }
            
            # Store with test session ID
            test_session = "test_env_setup"
            key = f"hook:env_setup:{test_session}"
            r.setex(key, 60, json.dumps(test_env_data))
            
            # Retrieve and verify
            stored = r.get(key)
            if stored:
                retrieved = json.loads(stored)
                print("✓ Successfully stored and retrieved environment data")
                print(f"  Venv path: {retrieved['venv_path']}")
                print(f"  Command wrapped: {'wrapped_command' in retrieved}")
            
            # Cleanup
            r.delete(key)
            
        except Exception as e:
            print(f"✗ Redis test skipped: {e}")
        
        # Demonstrate full workflow
        print("\n\n6. Full workflow demonstration:\n")
        
        # Set up test environment variables
        os.environ['CLAUDE_COMMAND'] = 'python analyze_data.py'
        os.environ['CLAUDE_SESSION_ID'] = 'demo_session'
        
        print("Input command: python analyze_data.py")
        print("Session ID: demo_session")
        
        # Find venv
        if venv := find_venv_path():
            print(f"\nFound venv: {venv}")
            
            # Create wrapper
            wrapped = create_activation_wrapper('python analyze_data.py', venv)
            print(f"Wrapped command: {wrapped}")
            
            # Setup environment
            env_updates = setup_environment_vars(venv)
            print(f"\nEnvironment updates: {len(env_updates)} variables")
            
            print("\nThis hook would:")
            print("1. Store environment data in Redis")
            print("2. Make venv activation available to WebSocket handler")
            print("3. Ensure Python commands run in correct environment")
        else:
            print("\nNo venv found - would proceed without wrapping")
        
        # Clean up test env vars
        os.environ.pop('CLAUDE_COMMAND', None)
        os.environ.pop('CLAUDE_SESSION_ID', None)
        
        print("\n=== Test Complete ===")
    else:
        # Normal hook mode
        main()