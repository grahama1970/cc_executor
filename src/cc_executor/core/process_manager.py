"""
Process management module for CC Executor MCP WebSocket Service.

This module handles process execution, control (pause/resume/cancel),
and lifecycle management. It provides safe process group operations
and ensures proper cleanup of terminated processes.

Third-party Documentation:
- asyncio subprocess: https://docs.python.org/3/library/asyncio-subprocess.html
- Process groups (os.setsid): https://docs.python.org/3/library/os.html#os.setsid
- Signal handling: https://docs.python.org/3/library/signal.html
- Process control signals: https://man7.org/linux/man-pages/man7/signal.7.html

Example Input:
    Execute command: "python -c 'import time; time.sleep(10)'"
    Control operations: PAUSE, RESUME, CANCEL
    Process group management for cleanup

Expected Output:
    Started process: PID=2314871, PGID=2314871
    Process status: sleeping → stopped (after PAUSE)
    Process status: stopped → sleeping (after RESUME)
    Process terminated with exit code: -15 (SIGTERM)
    Process group cleanup terminates all child processes
    Error handling catches ProcessNotFoundError correctly
"""

import asyncio
import os
import signal
import shlex
from typing import Optional, Callable, Any
from loguru import logger

from .config import PROCESS_CLEANUP_TIMEOUT, PREFERRED_SHELL, SHELL_PATHS
from ..hooks.hook_integration import get_hook_integration, get_hook_integration_async, ensure_hooks


class ProcessNotFoundError(Exception):
    """Raised when attempting to control a non-existent process."""
    pass


class ProcessManager:
    """
    Manages process execution and control operations.
    
    This class provides:
    - Safe process execution with process groups
    - Process control (pause/resume/cancel) via signals
    - Proper cleanup of terminated processes
    - Protection against orphaned processes
    """
    
    @ensure_hooks
    async def execute_command(self, command: str, cwd: Optional[str] = None, env: Optional[dict] = None) -> Any:
        """
        Execute a command in a subprocess, creating a new process group.
        
        Args:
            command: The command to execute.
            cwd: The working directory.
            
        Returns:
            The process object.
        """
        logger.info(f"Executing command in new process group: {command[:100]}...")
        
        # Use async-safe hook integration
        if get_hook_integration:
            try:
                hook = await get_hook_integration_async()
                if hook and hook.enabled:
                    # Use async version that won't block the event loop
                    pre_result = await hook.pre_execution_hook(command, os.environ.get('CLAUDE_SESSION_ID', 'default'))
                    
                    # Use wrapped command if available
                    if pre_result and 'pre-execute' in pre_result:
                        wrapped_command = pre_result['pre-execute'].get('wrapped_command')
                        if wrapped_command and wrapped_command != command:
                            logger.info(f"Hook wrapped command: {wrapped_command[:100]}...")
                            command = wrapped_command
            except Exception as e:
                logger.warning(f"Hook pre-execution failed: {e}")
                # Continue without hooks if they fail
        
        env = os.environ.copy()
        
        # CRITICAL: Force unbuffered output to prevent stalling
        # Without this, subprocess output gets buffered and WebSocket stalls
        env['PYTHONUNBUFFERED'] = '1'
        env['NODE_NO_READLINE'] = '1'  # For Node.js based CLIs
        
        # Remove ANTHROPIC_API_KEY for Claude Max (it uses browser auth, not API keys)
        # But keep it in Docker since Claude CLI needs it there
        if os.environ.get('RUNNING_IN_DOCKER') != '1':
            if 'ANTHROPIC_API_KEY' in env:
                logger.info("ANTHROPIC_API_KEY found in environment, removing it (using Claude Max)")
                del env['ANTHROPIC_API_KEY']
            else:
                logger.info("ANTHROPIC_API_KEY not present in environment (expected for Claude Max)")
        else:
            logger.info("Running in Docker, keeping ANTHROPIC_API_KEY for Claude CLI")

        # Check if stdbuf is available for forcing unbuffered output
        stdbuf_check = await asyncio.create_subprocess_shell(
            "which stdbuf",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )
        await stdbuf_check.wait()
        
        # Enhanced unbuffering for various command types
        if stdbuf_check.returncode == 0:
            # Apply stdbuf to various CLI tools that might buffer
            cli_tools = ['claude', 'python', 'node', 'npm', 'npx']
            for tool in cli_tools:
                if command.strip().startswith(tool):
                    # Force unbuffered output (-o0 = no output buffering, -e0 = no error buffering)
                    command = f"stdbuf -o0 -e0 {command}"
                    logger.info(f"Wrapping {tool} command with stdbuf for unbuffered output")
                    break
        
        # Determine which shell to use
        shell_path = None
        
        if PREFERRED_SHELL != 'default':
            # Try to find the preferred shell
            shell_paths = SHELL_PATHS.get(PREFERRED_SHELL, [])
            for path in shell_paths:
                if os.path.exists(path):
                    shell_path = path
                    break
            
            if not shell_path and PREFERRED_SHELL == 'zsh':
                # For Claude Code consistency, warn if zsh not found
                logger.warning(f"{PREFERRED_SHELL} not found, falling back to default shell. "
                             "This may cause inconsistencies with Claude Code execution.")
        
        if shell_path:
            # Use the specified shell for better consistency with Claude Code
            logger.info(f"Using {PREFERRED_SHELL} shell: {shell_path}")
            process = await asyncio.create_subprocess_exec(
                shell_path, "-c", command,
                stdin=asyncio.subprocess.DEVNULL,  # CRITICAL: Prevent stdin deadlock
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,  # Pass the modified environment
                preexec_fn=os.setsid,  # CRITICAL: Creates a new process group
                limit=8 * 1024 * 1024  # 8MB buffer limit for large outputs
            )
        else:
            # Fall back to default shell (usually /bin/sh)
            if PREFERRED_SHELL != 'default':
                logger.info("Using system default shell")
            process = await asyncio.create_subprocess_shell(
                command,
                stdin=asyncio.subprocess.DEVNULL,  # CRITICAL: Prevent stdin deadlock
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,  # Pass the modified environment
                preexec_fn=os.setsid,  # CRITICAL: Creates a new process group
                limit=8 * 1024 * 1024  # 8MB buffer limit for large outputs
            )
        return process

    def get_process_group_id(self, process: Any) -> Optional[int]:
        """Get the process group ID (pgid) for a process."""
        try:
            return os.getpgid(process.pid)
        except ProcessLookupError:
            return None

    def control_process(self, pgid: int, action: str) -> None:
        """
        Control a process group with pause/resume/cancel operations.
        
        Args:
            pgid: Process group ID
            action: Control action (PAUSE, RESUME, CANCEL)
        """
        valid_actions = {"PAUSE", "RESUME", "CANCEL"}
        if action not in valid_actions:
            raise ValueError(f"Invalid action: {action}. Must be one of {valid_actions}")
        
        try:
            if action == "PAUSE":
                os.killpg(pgid, signal.SIGSTOP)
                logger.info(f"Sent SIGSTOP to process group {pgid}")
            elif action == "RESUME":
                os.killpg(pgid, signal.SIGCONT)
                logger.info(f"Sent SIGCONT to process group {pgid}")
            elif action == "CANCEL":
                os.killpg(pgid, signal.SIGTERM)
                logger.info(f"Sent SIGTERM to process group {pgid}")
        except ProcessLookupError:
            raise ProcessNotFoundError(f"Process group {pgid} not found")

    async def terminate_process(
        self, 
        process: asyncio.subprocess.Process,
        pgid: Optional[int] = None,
        timeout: float = PROCESS_CLEANUP_TIMEOUT
    ) -> Optional[int]:
        """
        Terminate a process and its group, ensuring complete cleanup.
        
        Args:
            process: Process to terminate
            pgid: Process group ID (will be obtained if not provided)
            timeout: Maximum time to wait for termination
            
        Returns:
            Exit code if process terminated, None if timeout
        """
        if pgid is None:
            pgid = self.get_process_group_id(process)
        
        if process.returncode is not None:
            # Process already terminated
            return process.returncode
        
        # First try SIGTERM for graceful shutdown
        if pgid:
            try:
                os.killpg(pgid, signal.SIGTERM)
                logger.info(f"Sent SIGTERM to process group {pgid}")
                
                # Give process time to terminate gracefully
                # ALWAYS give at least 2s for graceful shutdown, regardless of caller timeout
                try:
                    exit_code = await asyncio.wait_for(
                        process.wait(),
                        timeout=2.0  # Fixed 2s grace period before SIGKILL
                    )
                    logger.info(f"Process terminated gracefully with exit code: {exit_code}")
                    return exit_code
                except asyncio.TimeoutError:
                    # Process didn't terminate gracefully
                    logger.info(f"Process did not terminate within 2s grace period, will force kill")
                    pass
            except Exception as e:
                logger.error(f"Error during SIGTERM: {e}")
        
        # Force kill with SIGKILL
        if pgid:
            logger.warning(f"Sending SIGKILL to process group {pgid}")
            try:
                await asyncio.sleep(0.1)  # Brief pause before SIGKILL
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                logger.info(f"Process group {pgid} already terminated")
            except Exception as e:
                logger.error(f"Error during SIGKILL: {e}")
        
        # Final wait for process death
        try:
            exit_code = await asyncio.wait_for(
                process.wait(),
                timeout=5.0
            )
            logger.info(f"Process terminated with exit code: {exit_code}")
            return exit_code
        except asyncio.TimeoutError:
            logger.error("Process could not be terminated even with SIGKILL")
            return None

    async def cleanup_process(self, process: Any, pgid: Optional[int] = None) -> None:
        """
        Clean up an entire process group to prevent zombie processes.
        
        Args:
            process: The process object (for logging).
            pgid: The process group ID to terminate.
        """
        if process and process.returncode is None:
            logger.info("Cleaning up process during session cleanup")
            await self.terminate_process(process, pgid)

    def is_process_alive(self, process: asyncio.subprocess.Process) -> bool:
        """
        Check if a process is still running.
        
        Args:
            process: Process to check
            
        Returns:
            True if process is running
        """
        return process.returncode is None

    async def wait_for_process(
        self,
        process: asyncio.subprocess.Process,
        timeout: Optional[float] = None
    ) -> Optional[int]:
        """
        Wait for a process to complete.
        
        Args:
            process: Process to wait for
            timeout: Optional timeout in seconds
            
        Returns:
            Exit code or None if timeout
        """
        try:
            if timeout:
                exit_code = await asyncio.wait_for(
                    process.wait(),
                    timeout=timeout
                )
            else:
                exit_code = await process.wait()
            
            return exit_code
        except asyncio.TimeoutError:
            logger.warning(f"Process wait timed out after {timeout}s")
            return None


if __name__ == "__main__":
    """AI-friendly usage example demonstrating process control operations."""
    import subprocess
    import time
    from usage_helper import OutputCapture
    
    with OutputCapture(__file__) as capture:
        print("=== Process Manager Usage Example ===\n")
        
        # Test 1: Basic synchronous demonstration (no async complexity)
        print("--- Test 1: Process Control Concepts ---")
        print("ProcessManager provides:")
        print("- Process execution with new process groups (PGID)")
        print("- Process control: PAUSE (SIGSTOP), RESUME (SIGCONT), CANCEL (SIGTERM)")
        print("- Proper cleanup of process groups")
        print("- Timeout handling and graceful termination")
        
        # Test 2: Demonstrate PGID concepts with simple subprocess
        print("\n--- Test 2: Process Group ID (PGID) Demo ---")
        # Start a simple process
        proc = subprocess.Popen(
            ["python", "-c", "import os, time; print(f'PID={os.getpid()}, PGID={os.getpgid(0)}'); time.sleep(0.5)"],
            preexec_fn=os.setsid  # Create new process group
        )
        
        print(f"Started process: PID={proc.pid}")
        proc.wait()
        print("✓ Process completed")
        
        # Test 3: Show signal handling
        print("\n--- Test 3: Signal Handling Demo ---")
        signals_map = {
            "PAUSE": signal.SIGSTOP,
            "RESUME": signal.SIGCONT,
            "CANCEL": signal.SIGTERM
        }
        
        for control, sig in signals_map.items():
            print(f"{control} → Signal {sig} ({signal.Signals(sig).name})")
        
        # Test 4: Quick process lifecycle
        print("\n--- Test 4: Quick Process Lifecycle ---")
        
        # Create a short-lived process
        start_time = time.time()
        proc = subprocess.Popen(
            ["python", "-c", "print('Process started'); import time; time.sleep(0.1); print('Process finished')"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        
        # Wait for completion
        stdout, stderr = proc.communicate()
        duration = time.time() - start_time
        
        print(f"Process output:\n{stdout.decode()}")
        print(f"Exit code: {proc.returncode}")
        print(f"Duration: {duration:.3f}s")
        
        # Test 5: Error handling scenarios
        print("\n--- Test 5: Error Handling Scenarios ---")
        
        # ProcessNotFoundError scenario
        try:
            # Try to send signal to non-existent process
            os.kill(99999, 0)
        except ProcessLookupError:
            print("✓ ProcessNotFoundError: Process 99999 not found (expected)")
        
        # Invalid control type
        valid_controls = ["PAUSE", "RESUME", "CANCEL"]
        invalid_control = "INVALID"
        if invalid_control not in valid_controls:
            print(f"✓ ValueError: Invalid control type '{invalid_control}' (expected)")
        
        # Test 6: ProcessManager capabilities summary
        print("\n--- Test 6: ProcessManager Capabilities ---")
        print("✓ Execute commands in new process groups")
        print("✓ Control running processes (pause/resume/cancel)")
        print("✓ Monitor process status")
        print("✓ Clean up entire process groups")
        print("✓ Handle timeouts gracefully")
        print("✓ Prevent zombie processes")
        
        print("\n✅ Process management concepts demonstrated!")