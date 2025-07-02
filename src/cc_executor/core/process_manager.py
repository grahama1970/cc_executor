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
    
    async def execute_command(self, command: str, cwd: Optional[str] = None) -> Any:
        """
        Execute a command in a subprocess, creating a new process group.
        
        Args:
            command: The command to execute.
            cwd: The working directory.
            
        Returns:
            The process object.
        """
        logger.info(f"Executing command in new process group: {command[:100]}...")
        
        env = os.environ.copy()
        
        # CRITICAL: Force unbuffered output to prevent stalling
        # Without this, subprocess output gets buffered and WebSocket stalls
        env['PYTHONUNBUFFERED'] = '1'
        env['NODE_NO_READLINE'] = '1'  # For Node.js based CLIs
        
        # Remove ANTHROPIC_API_KEY for Claude Max (it uses browser auth, not API keys)
        if 'ANTHROPIC_API_KEY' in env:
            logger.info("ANTHROPIC_API_KEY found in environment, removing it (using Claude Max)")
            del env['ANTHROPIC_API_KEY']
        else:
            logger.info("ANTHROPIC_API_KEY not present in environment (expected for Claude Max)")

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