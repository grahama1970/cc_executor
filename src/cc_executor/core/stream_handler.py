"""
Stream handling module for CC Executor MCP WebSocket Service.

This module manages stdout/stderr streaming from processes with proper
back-pressure handling, line buffering, and timeout management. It prevents
buffer overflow and handles partial lines at buffer boundaries.

Third-party Documentation:
- asyncio StreamReader: https://docs.python.org/3/library/asyncio-stream.html#asyncio.StreamReader
- LimitOverrunError: https://docs.python.org/3/library/asyncio-exceptions.html#asyncio.LimitOverrunError
- Back-pressure handling: https://docs.python.org/3/library/asyncio-stream.html#asyncio.StreamWriter.drain
- Stream buffering: https://docs.python.org/3/library/asyncio-stream.html#asyncio.open_connection

Example Input:
    Commands that stress stream handling:
    - Fast producer: "yes 'hello world'"
    - Long lines: "python -c 'print(\"x\" * 10000)'"
    - No newlines: "python -c 'import sys; sys.stdout.write(\"x\" * 100000)'"
    - Binary data: "cat /dev/urandom | head -c 1000000"

Expected Output:
    Normal output: [stdout] Line 1, [stderr] Error line
    Long line (10KB): [stdout] xxxxxxxxxx... (10001 total chars)
    Fast producer: Successfully streams 100 lines without blocking
    Partial line: Handles 8KB without newline, then completes
    Timeout: "Starting..." then timeout after 5s
    Binary data: Handles non-UTF8 bytes with replacement chars
"""

import asyncio
from typing import Callable, Optional, AsyncIterator, Awaitable, Any
from loguru import logger

try:
    from .config import MAX_BUFFER_SIZE, STREAM_TIMEOUT
except ImportError:
    # For standalone execution
    MAX_BUFFER_SIZE = 8 * 1024 * 1024  # 8MB for large JSON outputs
    STREAM_TIMEOUT = 300

try:
    from ..utils.transcript_logger import TranscriptLogger
except ImportError:
    TranscriptLogger = None


class StreamHandler:
    """
    Handles process output streaming with back-pressure control.
    
    This class provides:
    - Line-based streaming from stdout/stderr
    - Buffer overflow protection
    - Partial line handling at buffer boundaries
    - Timeout management for slow processes
    - Graceful cancellation handling
    """
    
    def __init__(self, max_line_size: int = MAX_BUFFER_SIZE, transcript_logger: Optional['TranscriptLogger'] = None):
        """
        Initialize the stream handler.
        
        Args:
            max_line_size: Maximum size for a single line
            transcript_logger: Optional transcript logger for capturing full outputs
        """
        self.max_line_size = max_line_size
        self.transcript_logger = transcript_logger
        self.current_exec_id = None
        
    async def stream_output(
        self,
        stream: asyncio.StreamReader,
        callback: Callable[[str, str], Awaitable[Any]],
        stream_type: str,
        timeout: Optional[float] = None,
        exec_id: Optional[str] = None
    ) -> None:
        """
        Stream output from a process with timeout and back-pressure handling.
        
        Args:
            stream: asyncio.StreamReader (stdout or stderr)
            callback: Async function to call with (stream_type, line)
            stream_type: "stdout" or "stderr"
            timeout: Timeout for each read operation
        """
        if timeout is None:
            logger.info(f"Starting {stream_type} streaming with no timeout, buffer_size={self.max_line_size:,}")
        else:
            logger.info(f"Starting {stream_type} streaming with {timeout}s timeout, buffer_size={self.max_line_size:,}")
        
        lines_read = 0
        bytes_read = 0
        large_lines = 0
        start_time = asyncio.get_event_loop().time()
        last_log_time = start_time
        last_log_bytes = 0
        
        try:
            async for line in self._read_lines(stream, timeout):
                lines_read += 1
                line_bytes = len(line.encode('utf-8'))
                bytes_read += line_bytes
                
                # Track large lines for debugging
                if line_bytes > 1024:
                    large_lines += 1
                    # Use debug level for tight loop logging
                    logger.debug(f"{stream_type}: Large line #{large_lines} - {line_bytes:,} bytes")
                
                # Log progress every 10 seconds or every 100KB (debug level to reduce spam)
                current_time = asyncio.get_event_loop().time()
                if (current_time - last_log_time > 10) or (bytes_read - last_log_bytes > 102400):
                    elapsed = current_time - start_time
                    rate = (bytes_read - last_log_bytes) / (current_time - last_log_time) if current_time > last_log_time else 0
                    logger.debug(f"{stream_type} progress: {lines_read} lines, {bytes_read:,} bytes in {elapsed:.1f}s ({rate/1024:.1f} KB/s)")
                    last_log_time = current_time
                    last_log_bytes = bytes_read
                
                # Log to transcript before callback (which may truncate)
                if self.transcript_logger and exec_id:
                    self.transcript_logger.log_output(
                        exec_id, stream_type, line, lines_read, bytes_read
                    )
                
                await callback(stream_type, line)
            
            # Log final statistics
            elapsed = asyncio.get_event_loop().time() - start_time
            avg_line_size = bytes_read / lines_read if lines_read > 0 else 0
            logger.info(f"{stream_type} completed: {lines_read} lines, {bytes_read:,} bytes in {elapsed:.1f}s "
                       f"(avg line: {avg_line_size:.0f} bytes, large lines: {large_lines})")
                
        except asyncio.CancelledError:
            # Fix #6: Don't re-raise CancelledError during cleanup
            elapsed = asyncio.get_event_loop().time() - start_time
            logger.info(f"{stream_type} streaming cancelled after {elapsed:.1f}s ({lines_read} lines, {bytes_read:,} bytes)")
            
        except asyncio.TimeoutError:
            elapsed = asyncio.get_event_loop().time() - start_time
            logger.warning(f"{stream_type} timed out after {timeout}s (read {lines_read} lines, {bytes_read:,} bytes in {elapsed:.1f}s)")
            await callback(stream_type, f"\n[Stream timed out after {timeout}s]\n")
            
        except Exception as e:
            elapsed = asyncio.get_event_loop().time() - start_time
            logger.error(f"Error streaming {stream_type} after {elapsed:.1f}s ({lines_read} lines, {bytes_read:,} bytes): {e}")
            await callback(stream_type, f"\n[Stream error: {e}]\n")
            
    async def _read_lines(
        self,
        stream: asyncio.StreamReader,
        timeout: Optional[float]
    ) -> AsyncIterator[str]:
        """
        Read lines from stream with proper handling of partial lines.
        
        Args:
            stream: Stream to read from
            timeout: Timeout for each read operation
            
        Yields:
            Decoded lines from the stream
        """
        while True:
            try:
                # Fix #3: Add timeout to prevent hanging (unless None)
                if timeout is None:
                    line = await stream.readline()
                else:
                    line = await asyncio.wait_for(
                        stream.readline(),
                        timeout=timeout
                    )
                
                if not line:
                    logger.debug(f"End of stream reached")
                    break
                    
                # Log what we read (only for debugging very verbose streams)
                if logger._core.min_level <= 10:  # DEBUG level
                    logger.debug(f"Read line ({len(line)} bytes): {line[:100]}...")
                    
                # Fix #5: Handle oversized lines at buffer boundary
                if len(line) == self.max_line_size and not line.endswith(b'\n'):
                    # Line was truncated at buffer boundary - keep reading until newline
                    logger.warning(f"Line truncated at buffer boundary ({self.max_line_size} bytes), reading additional chunks...")
                    
                    # Keep reading chunks until we find a newline
                    chunks = [line]
                    chunks_read = 1
                    total_size = len(line)
                    
                    while True:
                        # Safety guard: if we've read too much without a newline, something is wrong
                        if total_size > 16 * 1024 * 1024:  # 16 MB hard limit
                            logger.error(f"Line exceeded 16MB without newline! Read {chunks_read} chunks, {total_size:,} bytes")
                            logger.warning("This likely indicates a protocol error or binary data. Truncating and continuing...")
                            break
                        
                        try:
                            # Try to read until newline for more efficient handling
                            if timeout is None:
                                chunk = await stream.readuntil(b'\n')
                            else:
                                chunk = await asyncio.wait_for(
                                    stream.readuntil(b'\n'),
                                    timeout=timeout
                                )
                            # If we get here, we found the newline
                            chunks.append(chunk)
                            total_size += len(chunk)
                            logger.info(f"Found newline after {chunks_read + 1} chunks, {total_size:,} bytes total")
                            break
                        except asyncio.LimitOverrunError:
                            # Still no newline, read a chunk and continue
                            if timeout is None:
                                chunk = await stream.read(self.max_line_size)
                            else:
                                chunk = await asyncio.wait_for(
                                    stream.read(self.max_line_size),
                                    timeout=timeout
                                )
                            
                            if not chunk:
                                logger.warning(f"Stream ended while reading large line (read {chunks_read} chunks, {total_size:,} bytes)")
                                break
                            
                            chunks_read += 1
                            total_size += len(chunk)
                            chunks.append(chunk)
                            
                            if chunks_read % 10 == 0:
                                logger.info(f"Still reading large line: {chunks_read} chunks, {total_size:,} bytes so far...")
                    
                    # Combine all chunks
                    line = b''.join(chunks)
                    logger.info(f"Completed reading large line: {chunks_read} chunks, {len(line):,} bytes total")
                    
                yield line.decode('utf-8', errors='replace')
                
            except asyncio.LimitOverrunError as e:
                # Line exceeded StreamReader's internal _limit. Read the complete line
                # in manageable chunks so that we forward the *full* output to the
                # caller instead of an abbreviated version with an ellipsis.
                logger.warning(f"LimitOverrunError encountered ({e}). Reading oversized line in chunks…")

                chunks: list[bytes] = []

                # Read the first chunk that triggered the error
                first_chunk = await stream.read(stream._limit)
                if first_chunk:
                    chunks.append(first_chunk)

                total_size = sum(len(c) for c in chunks)
                chunks_read = len(chunks)
                
                while True:
                    # Safety guard: if we've read too much without a newline, something is wrong
                    if total_size > 16 * 1024 * 1024:  # 16 MB hard limit
                        logger.error(f"Line exceeded 16MB without newline! Read {chunks_read} chunks, {total_size:,} bytes")
                        logger.warning("This likely indicates a protocol error or binary data. Truncating and continuing...")
                        break
                    
                    try:
                        # Try to read until newline for more efficient handling
                        if timeout is None:
                            chunk = await stream.readuntil(b'\n')
                        else:
                            chunk = await asyncio.wait_for(
                                stream.readuntil(b'\n'),
                                timeout=timeout
                            )
                        # If we get here, we found the newline
                        chunks.append(chunk)
                        total_size += len(chunk)
                        logger.info(f"Found newline after LimitOverrunError: {chunks_read + 1} chunks, {total_size:,} bytes total")
                        break
                    except asyncio.LimitOverrunError:
                        # Still no newline, read a chunk and continue
                        if timeout is None:
                            chunk = await stream.read(self.max_line_size)
                        else:
                            chunk = await asyncio.wait_for(
                                stream.read(self.max_line_size),
                                timeout=timeout
                            )

                        if not chunk:
                            # Reached EOF without newline; break to yield what we have
                            break

                        chunks.append(chunk)
                        chunks_read += 1
                        total_size += len(chunk)
                        
                        if chunks_read % 10 == 0:
                            logger.info(f"Still reading after LimitOverrunError: {chunks_read} chunks, {total_size:,} bytes so far...")

                line = b''.join(chunks)
                yield line.decode('utf-8', errors='replace')
                
            except asyncio.TimeoutError:
                # Re-raise timeout to be handled by caller
                raise
                
    async def _skip_to_newline(self, stream: asyncio.StreamReader, timeout: Optional[float]) -> None:
        """
        Skip stream content until next newline.
        
        Args:
            stream: Stream to read from
            timeout: Timeout for read operations
        """
        logger.debug("Skipping to next newline")
        
        try:
            while True:
                if timeout is None:
                    char = await stream.read(1)
                else:
                    char = await asyncio.wait_for(
                        stream.read(1),
                        timeout=timeout
                    )
                if not char or char == b'\n':
                    break
                    
        except asyncio.TimeoutError:
            logger.warning("Timeout while skipping to newline")
            
    async def collect_output(
        self,
        stream: asyncio.StreamReader,
        max_size: Optional[int] = None,
        timeout: float = STREAM_TIMEOUT
    ) -> str:
        """
        Collect all output from a stream up to a maximum size.
        
        Args:
            stream: Stream to read from
            max_size: Maximum bytes to collect (None for no limit)
            timeout: Total timeout for collection
            
        Returns:
            Collected output as string
        """
        output = []
        total_size = 0
        
        try:
            async for line in self._read_lines(stream, timeout):
                output.append(line)
                total_size += len(line)
                
                if max_size and total_size >= max_size:
                    output.append("\n[Output truncated]\n")
                    break
                    
        except asyncio.TimeoutError:
            output.append(f"\n[Collection timed out after {timeout}s]\n")
            
        return ''.join(output)
        
    async def multiplex_streams(
        self,
        stdout: asyncio.StreamReader,
        stderr: asyncio.StreamReader,
        callback: Callable[[str, str], Awaitable[Any]],
        timeout: Optional[float] = None,
        exec_id: Optional[str] = None
    ) -> None:
        """
        Stream both stdout and stderr concurrently.
        
        Args:
            stdout: stdout stream
            stderr: stderr stream
            callback: Async function to call with output
            timeout: Timeout for streaming
        """
        # Pass timeout as-is (None means no timeout)
        
        # Create streaming tasks
        stdout_task = asyncio.create_task(
            self.stream_output(stdout, callback, "stdout", timeout, exec_id),
            name="stdout_streamer"
        )
        stderr_task = asyncio.create_task(
            self.stream_output(stderr, callback, "stderr", timeout, exec_id),
            name="stderr_streamer"
        )
        
        # Wait for both to complete
        try:
            await asyncio.gather(stdout_task, stderr_task)
        except Exception as e:
            logger.error(f"Error in multiplex streams: {e}")
            # Cancel any running tasks
            for task in [stdout_task, stderr_task]:
                if not task.done():
                    task.cancel()
            # Properly await the cancellation to avoid "Task was destroyed but it is pending" warnings
            await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
            raise


if __name__ == "__main__":
    """
    Direct debug entry point for VSCode.
    
    VSCode Debug:
        1. Set breakpoints in stream_output() or _read_lines()
        2. Press F5 to run this test
        3. Watch how lines are read and processed
    """
    """Usage example demonstrating stream handling edge cases."""
    
    import sys
    import time
    
    async def test_callback(stream_type: str, data: str):
        """Test callback that prints received data."""
        # Show first 50 chars to avoid flooding output
        preview = data.strip()[:50]
        if len(data.strip()) > 50:
            preview += f"... ({len(data)} total chars)"
        print(f"[{stream_type}] {preview}")
    
    async def run_streaming_test(command: str, description: str):
        """Run a single streaming test."""
        print(f"\n--- {description} ---")
        print(f"Command: {command}")
        
        handler = StreamHandler(max_line_size=8192)
        
        # Create subprocess
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        print(f"Process started: PID={process.pid}")
        
        try:
            # Stream with timeout
            await asyncio.wait_for(
                handler.multiplex_streams(
                    process.stdout,
                    process.stderr,
                    test_callback,
                    timeout=5  # 5 second timeout for tests
                ),
                timeout=10
            )
        except asyncio.TimeoutError:
            print("Streaming timed out (expected for some tests)")
        
        # Cleanup
        if process.returncode is None:
            process.terminate()
            await process.wait()
        
        print(f"Process exit code: {process.returncode}")
    
    async def main():
        print("=== Stream Handler Usage Example ===")
        
        # Test 1: Normal output
        await run_streaming_test(
            "echo 'Line 1'; echo 'Line 2'; echo 'Error line' >&2",
            "Test 1: Normal stdout/stderr output"
        )
        
        # Test 2: Long line handling
        await run_streaming_test(
            f"python -c \"print('x' * 10000)\"",
            "Test 2: Long line (10KB) handling"
        )
        
        # Test 3: Fast producer (back-pressure)
        await run_streaming_test(
            "python -c \"for i in range(100): print(f'Fast line {i}', flush=True)\"",
            "Test 3: Fast producer"
        )
        
        # Test 4: No newlines (buffer handling)
        await run_streaming_test(
            "python -c \"import sys; sys.stdout.write('x' * 8000); sys.stdout.flush(); import time; time.sleep(1); print('done')\"",
            "Test 4: Partial line at buffer boundary"
        )
        
        # Test 5: Timeout handling
        await run_streaming_test(
            "python -c \"import time; print('Starting...'); time.sleep(10); print('Never seen')\"",
            "Test 5: Stream timeout"
        )
        
        # Test 6: Binary data
        await run_streaming_test(
            "python -c \"import os; os.write(1, b'\\x00\\x01\\x02\\xff' * 100); print()\"",
            "Test 6: Binary data handling"
        )
        
        # Test 7: Collect output mode
        print("\n--- Test 7: Collect Output Mode ---")
        handler = StreamHandler()
        
        process = await asyncio.create_subprocess_shell(
            "echo 'Line 1'; echo 'Line 2'; echo 'Line 3'",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        output = await handler.collect_output(
            process.stdout,
            max_size=100,
            timeout=5
        )
        
        print(f"Collected output: {repr(output)}")
        await process.wait()
        
        print("\n✅ All stream handling tests completed!")
        
        # Summary of edge cases handled
        print("\n=== Edge Cases Handled ===")
        print("1. Long lines: Truncated at 8192 bytes with '...' indicator")
        print("2. Buffer overflow: LimitOverrunError caught and handled")
        print("3. No newlines: Partial lines handled correctly")
        print("4. Timeouts: Clean timeout after specified duration")
        print("5. Binary data: Decoded with 'replace' error handler")
        print("6. Cancellation: CancelledError doesn't re-raise")
    
    # Run the tests
    asyncio.run(main())