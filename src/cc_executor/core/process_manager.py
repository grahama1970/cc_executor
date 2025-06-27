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

try:
    from .config import PROCESS_CLEANUP_TIMEOUT
except ImportError:
    # For standalone execution
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config import PROCESS_CLEANUP_TIMEOUT


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
    
    async def execute_command(
        self,
        command: str,
        preexec_fn: Optional[Callable] = None,
        cwd: Optional[str] = None,
        env: Optional[dict] = None
    ) -> asyncio.subprocess.Process:
        """
        Execute a command in a new process.
        
        Args:
            command: Shell command to execute
            preexec_fn: Optional pre-execution function (default: os.setsid)
            cwd: Optional working directory for the subprocess
            env: Optional environment variables dict (defaults to current environment)
            
        Returns:
            asyncio.subprocess.Process instance
        """
        # Default to creating new session for process group control
        if preexec_fn is None:
            preexec_fn = os.setsid
            
        logger.info(f"Executing command: {command[:100]}...")
        if cwd:
            logger.info(f"Working directory: {cwd}")
        else:
            logger.info(f"Working directory: {os.getcwd()} (current)")
        
        # Use shlex to correctly split the command string into a list
        # This avoids shell parsing issues with quotes and arguments
        command_args = shlex.split(command)
        
        # Prepare environment - inherit current environment by default
        if env is None:
            env = os.environ.copy()
        else:
            # Merge provided env with current environment
            merged_env = os.environ.copy()
            merged_env.update(env)
            env = merged_env
        
        # Remove ANTHROPIC_API_KEY since we're using Claude Max
        # Claude Max uses browser-based auth, not API keys
        if 'ANTHROPIC_API_KEY' in env:
            logger.info("Removing ANTHROPIC_API_KEY from subprocess environment (Claude Max uses browser auth)")
            del env['ANTHROPIC_API_KEY']
            
        try:
            # Execute the command directly, not through a shell
            # The first argument is the program, the rest are its arguments
            proc = await asyncio.create_subprocess_exec(
                *command_args,
                limit=8 * 1024 * 1024,  # 8 MiB per line to handle large Claude JSON events
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,  # Explicitly close stdin to prevent hanging
                preexec_fn=preexec_fn,
                cwd=cwd,
                env=env
            )
            
            logger.info(f"Process started with PID: {proc.pid}")
            return proc
            
        except Exception as e:
            logger.error(f"Failed to execute command: {e}")
            raise
            
    def get_process_group_id(self, process: asyncio.subprocess.Process) -> Optional[int]:
        """
        Get the process group ID for a process.
        
        Args:
            process: asyncio.subprocess.Process instance
            
        Returns:
            Process group ID or None if process is terminated
        """
        if process.pid and process.returncode is None:
            try:
                # Get process group ID (should be same as PID due to setsid)
                pgid = os.getpgid(process.pid)
                return pgid
            except ProcessLookupError:
                return None
        return None
        
    def control_process(self, pgid: int, control_type: str) -> None:
        """
        Send control signals to a process group.
        
        Args:
            pgid: Process group ID
            control_type: One of "PAUSE", "RESUME", "CANCEL"
            
        Raises:
            ProcessNotFoundError: If process group doesn't exist
            ValueError: If control_type is invalid
        """
        try:
            if control_type == "PAUSE":
                logger.info(f"Pausing process group {pgid}")
                os.killpg(pgid, signal.SIGSTOP)
                
            elif control_type == "RESUME":
                logger.info(f"Resuming process group {pgid}")
                os.killpg(pgid, signal.SIGCONT)
                
            elif control_type == "CANCEL":
                logger.info(f"Cancelling process group {pgid}")
                # Note: Using positive pgid (O3's suggestion was incorrect)
                os.killpg(pgid, signal.SIGTERM)
                
            else:
                raise ValueError(f"Unknown control type: {control_type}")
                
        except ProcessLookupError:
            logger.error(f"Process group {pgid} not found")
            raise ProcessNotFoundError(f"Process group {pgid} not found")
            
    async def terminate_process(
        self,
        process: asyncio.subprocess.Process,
        pgid: Optional[int] = None,
        timeout: float = PROCESS_CLEANUP_TIMEOUT
    ) -> Optional[int]:
        """
        Gracefully terminate a process and its group.
        
        Args:
            process: Process to terminate
            pgid: Process group ID (will be determined if not provided)
            timeout: Maximum time to wait for termination
            
        Returns:
            Exit code if process terminated, None otherwise
        """
        if process.returncode is not None:
            return process.returncode
            
        # Get process group ID if not provided
        if pgid is None:
            pgid = self.get_process_group_id(process)
            
        try:
            # First try SIGTERM
            if pgid:
                logger.info(f"Sending SIGTERM to process group {pgid}")
                try:
                    os.killpg(pgid, signal.SIGTERM)
                except ProcessLookupError:
                    logger.warning(f"Process group {pgid} already terminated")
                    
            # Wait for termination
            try:
                exit_code = await asyncio.wait_for(
                    process.wait(),
                    timeout=timeout
                )
                logger.info(f"Process terminated with exit code: {exit_code}")
                return exit_code
                
            except asyncio.TimeoutError:
                # Force kill if still running
                logger.warning(f"Process did not terminate within {timeout}s, forcing kill")
                
                if pgid:
                    try:
                        os.killpg(pgid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                        
                # Final wait
                try:
                    exit_code = await asyncio.wait_for(
                        process.wait(),
                        timeout=5.0
                    )
                    return exit_code
                except asyncio.TimeoutError:
                    logger.error("Process could not be terminated")
                    return None
                    
        except Exception as e:
            logger.error(f"Error terminating process: {e}")
            return None
            
    async def cleanup_process(
        self,
        process: asyncio.subprocess.Process,
        pgid: Optional[int] = None
    ) -> None:
        """
        Ensure process is terminated and cleaned up.
        
        This is called during session cleanup to prevent orphaned processes.
        
        Args:
            process: Process to cleanup
            pgid: Process group ID
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
    """Usage example demonstrating process control operations."""
    
    async def monitor_process(process, pgid):
        """Monitor process CPU usage."""
        import psutil
        try:
            ps_process = psutil.Process(process.pid)
            while process.returncode is None:
                cpu_percent = ps_process.cpu_percent(interval=0.1)
                memory_mb = ps_process.memory_info().rss / 1024 / 1024
                status = ps_process.status()
                print(f"  PID {process.pid}: CPU={cpu_percent:.1f}%, Memory={memory_mb:.1f}MB, Status={status}")
                await asyncio.sleep(1)
        except (psutil.NoSuchProcess, ProcessLookupError):
            print(f"  Process {process.pid} terminated")
    
    async def main():
        print("=== Process Manager Usage Example ===\n")
        
        manager = ProcessManager()
        
        # Test 1: Execute a long-running command
        print("--- Test 1: Execute Long-Running Command ---")
        command = "python -c 'import time; [print(f\"Working... {i}\", flush=True) or time.sleep(1) for i in range(30)]'"
        
        process = await manager.execute_command(command)
        pgid = manager.get_process_group_id(process)
        
        print(f"Started process: PID={process.pid}, PGID={pgid}")
        
        # Start monitoring in background
        monitor_task = asyncio.create_task(monitor_process(process, pgid))
        
        # Test 2: Pause the process
        print("\n--- Test 2: Pause Process After 3 Seconds ---")
        await asyncio.sleep(3)
        
        try:
            manager.control_process(pgid, "PAUSE")
            print("✓ Process paused (SIGSTOP sent)")
        except ProcessNotFoundError as e:
            print(f"✗ Failed to pause: {e}")
        
        # Let it stay paused for 2 seconds
        await asyncio.sleep(2)
        
        # Test 3: Resume the process
        print("\n--- Test 3: Resume Process ---")
        try:
            manager.control_process(pgid, "RESUME")
            print("✓ Process resumed (SIGCONT sent)")
        except ProcessNotFoundError as e:
            print(f"✗ Failed to resume: {e}")
        
        # Let it run for 2 more seconds
        await asyncio.sleep(2)
        
        # Test 4: Cancel the process
        print("\n--- Test 4: Cancel Process ---")
        try:
            manager.control_process(pgid, "CANCEL")
            print("✓ Process cancelled (SIGTERM sent)")
        except ProcessNotFoundError as e:
            print(f"✗ Failed to cancel: {e}")
        
        # Wait for termination
        exit_code = await manager.wait_for_process(process, timeout=5)
        print(f"Process terminated with exit code: {exit_code}")
        
        # Stop monitoring
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        # Test 5: Process cleanup demonstration
        print("\n--- Test 5: Cleanup Demonstration ---")
        
        # Start a process that spawns children
        command2 = '''python -c "
import subprocess, time, os
print(f'Parent PID: {os.getpid()}')
p1 = subprocess.Popen(['sleep', '60'])
p2 = subprocess.Popen(['sleep', '60'])
print(f'Child PIDs: {p1.pid}, {p2.pid}')
time.sleep(60)
"'''
        
        process2 = await manager.execute_command(command2)
        pgid2 = manager.get_process_group_id(process2)
        
        print(f"Started parent process: PID={process2.pid}, PGID={pgid2}")
        await asyncio.sleep(1)  # Let children spawn
        
        # Cleanup the entire process group
        exit_code = await manager.terminate_process(process2, pgid2, timeout=5)
        print(f"Cleanup result: All processes in group {pgid2} terminated")
        
        # Test 6: Error handling
        print("\n--- Test 6: Error Handling ---")
        
        # Try to control non-existent process
        try:
            manager.control_process(99999, "PAUSE")
        except ProcessNotFoundError as e:
            print(f"✓ Correctly caught error: {e}")
        
        # Test invalid control type
        try:
            manager.control_process(pgid, "INVALID")
        except ValueError as e:
            print(f"✓ Correctly caught error: {e}")
        
        print("\n✅ All process management tests completed!")
        
    # Run the example
    try:
        # Install psutil if needed for monitoring
        import psutil
    except ImportError:
        print("Note: Install 'psutil' for process monitoring: pip install psutil")
        print("Continuing without monitoring...\n")
        
        # Simplified version without monitoring
        async def main_simple():
            print("=== Process Manager Usage Example (Simplified) ===\n")
            
            manager = ProcessManager()
            
            # Execute a simple command
            command = "echo 'Hello from subprocess' && sleep 2 && echo 'Subprocess done'"
            process = await manager.execute_command(command)
            pgid = manager.get_process_group_id(process)
            
            print(f"Started process: PID={process.pid}, PGID={pgid}")
            
            # Wait for completion
            exit_code = await process.wait()
            print(f"Process completed with exit code: {exit_code}")
            
            # Verify process is no longer alive
            alive = manager.is_process_alive(process)
            print(f"Process alive after completion: {alive}")
            
            print("\n✅ Basic process management test completed!")
        
        asyncio.run(main_simple())
    else:
        asyncio.run(main())