"""
Enhanced process executor with transcript logging.

This module wraps the existing process execution with transcript logging
to capture full, unabridged outputs before Claude truncation.
"""

import asyncio
import os
from typing import Optional, Callable, Dict, Any, Tuple, Union, List, Awaitable
from loguru import logger
import time

from ..core.process_manager import ProcessManager
from ..core.stream_handler import StreamHandler
from ..utils.transcript_logger import get_transcript_logger


class ProcessExecutor:
    """Enhanced process executor with transcript logging."""
    
    def __init__(self):
        """Initialize the executor with process manager and transcript logger."""
        self.process_manager = ProcessManager()
        self.transcript_logger = get_transcript_logger()
        
    async def execute_with_logging(
        self,
        command: str,
        callback: Callable[[str, str], Awaitable[Any]],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> Tuple[int, str]:
        """
        Execute a command with full transcript logging.
        
        Args:
            command: Command to execute
            callback: Callback for output streaming
            cwd: Working directory
            env: Environment variables
            timeout: Execution timeout
            
        Returns:
            Tuple of (exit_code, exec_id)
        """
        # Log command start
        exec_id = self.transcript_logger.log_command(
            command=command,
            working_dir=cwd or os.getcwd(),
            environment=env
        )
        
        logger.info(f"Starting execution with transcript logging: {exec_id}")
        
        # Track bytes for completion logging
        stdout_bytes = 0
        stderr_bytes = 0
        line_counts = {"stdout": 0, "stderr": 0}
        
        async def logging_callback(stream_type: str, data: str):
            """Wrapper callback that logs to transcript before forwarding."""
            nonlocal stdout_bytes, stderr_bytes
            
            # Update counters
            line_counts[stream_type] += 1
            byte_count = len(data.encode('utf-8'))
            
            if stream_type == "stdout":
                stdout_bytes += byte_count
            else:
                stderr_bytes += byte_count
            
            # Log to transcript
            self.transcript_logger.log_output(
                exec_id=exec_id,
                stream_type=stream_type,
                data=data,
                line_number=line_counts[stream_type],
                byte_count=stdout_bytes if stream_type == "stdout" else stderr_bytes
            )
            
            # Forward to original callback
            await callback(stream_type, data)
        
        start_time = time.time()
        
        try:
            # Execute the command
            process = await self.process_manager.execute_command(
                command=command,
                cwd=cwd,
                env=env
            )
            
            # Create stream handler with transcript logger
            stream_handler = StreamHandler()
            
            # Stream output with logging
            if timeout:
                await asyncio.wait_for(
                    stream_handler.multiplex_streams(
                        process.stdout,
                        process.stderr,
                        logging_callback,
                        timeout=timeout
                    ),
                    timeout=timeout
                )
            else:
                await stream_handler.multiplex_streams(
                    process.stdout,
                    process.stderr,
                    logging_callback
                )
            
            # Wait for process completion
            exit_code = await process.wait()
            
            # Log completion
            duration = time.time() - start_time
            self.transcript_logger.log_completion(
                exec_id=exec_id,
                exit_code=exit_code,
                duration=duration,
                total_stdout_bytes=stdout_bytes,
                total_stderr_bytes=stderr_bytes
            )
            
            logger.info(f"Execution completed: {exec_id}, exit_code={exit_code}, duration={duration:.1f}s")
            
            return exit_code, exec_id
            
        except Exception as e:
            # Log error
            self.transcript_logger.log_error(exec_id, str(e))
            logger.error(f"Execution failed: {exec_id}, error={e}")
            raise


async def execute_with_transcript_logging(
    command: str,
    callback: Callable[[str, str], Awaitable[Any]],
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: Optional[float] = None
) -> Tuple[int, str]:
    """
    Convenience function to execute a command with transcript logging.
    
    Returns:
        Tuple of (exit_code, execution_id)
    """
    executor = ProcessExecutor()
    return await executor.execute_with_logging(
        command=command,
        callback=callback,
        cwd=cwd,
        env=env,
        timeout=timeout
    )


if __name__ == "__main__":
    """Example usage demonstrating transcript logging."""
    
    async def print_callback(stream_type: str, data: str):
        """Simple callback that prints output."""
        print(f"[{stream_type}] {data.strip()}")
    
    async def main():
        print("=== Process Executor with Transcript Logging ===\n")
        
        # Test 1: Simple command
        print("--- Test 1: Simple Command ---")
        exit_code, exec_id = await execute_with_transcript_logging(
            command='echo "Hello from transcript logger"',
            callback=print_callback
        )
        print(f"Exit code: {exit_code}, Execution ID: {exec_id}\n")
        
        # Test 2: Long output
        print("--- Test 2: Long Output ---")
        exit_code, exec_id = await execute_with_transcript_logging(
            command='python -c "for i in range(100): print(f\'Line {i}: \' + \'x\' * 100)"',
            callback=print_callback
        )
        print(f"Exit code: {exit_code}, Execution ID: {exec_id}\n")
        
        # Get execution summary
        transcript_logger = get_transcript_logger()
        summary = transcript_logger.get_execution_summary(exec_id)
        print(f"Execution Summary: {summary}\n")
        
        # Search transcript
        print("--- Searching Transcript ---")
        results = transcript_logger.search_transcript("Line 50")
        print(f"Found {len(results)} matches for 'Line 50'")
        if results:
            print(f"First match: {results[0]['data'][:100]}...")
    
    asyncio.run(main())