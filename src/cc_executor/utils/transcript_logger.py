"""
Transcript logger that captures full, unabridged command outputs.

This module provides a solution to Claude's transcript truncation by logging
all command outputs to a separate file before they can be truncated.
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Optional, Any, Dict
from loguru import logger
import hashlib


class TranscriptLogger:
    """Logs full command outputs to prevent loss due to transcript truncation."""
    
    def __init__(self, log_dir: str = "logs/transcripts"):
        """
        Initialize transcript logger.
        
        Args:
            log_dir: Directory for transcript logs
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Create a session log file
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(log_dir, f"transcript_{session_id}.jsonl")
        
        logger.info(f"Transcript logger initialized: {self.log_file}")
        
    def log_command(self, command: str, working_dir: str, environment: Optional[Dict[str, str]] = None) -> str:
        """
        Log command execution start.
        
        Args:
            command: The command being executed
            working_dir: Working directory for the command
            environment: Environment variables (if any)
            
        Returns:
            Unique execution ID
        """
        exec_id = f"EXEC_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        entry = {
            "type": "command_start",
            "exec_id": exec_id,
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "working_dir": working_dir,
            "environment_modified": list(environment.keys()) if environment else []
        }
        
        self._write_entry(entry)
        return exec_id
        
    def log_output(self, exec_id: str, stream_type: str, data: str, 
                   line_number: int, byte_count: int) -> None:
        """
        Log command output (stdout/stderr).
        
        Args:
            exec_id: Execution ID from log_command
            stream_type: 'stdout' or 'stderr'
            data: The output data
            line_number: Line number in the stream
            byte_count: Cumulative byte count
        """
        # Calculate checksum for verification
        checksum = hashlib.md5(data.encode('utf-8')).hexdigest()
        
        entry = {
            "type": "output",
            "exec_id": exec_id,
            "timestamp": datetime.now().isoformat(),
            "stream": stream_type,
            "line_number": line_number,
            "byte_count": byte_count,
            "data_length": len(data),
            "checksum": checksum,
            "data": data  # Full, unabridged data
        }
        
        self._write_entry(entry)
        
    def log_completion(self, exec_id: str, exit_code: int, duration: float,
                      total_stdout_bytes: int, total_stderr_bytes: int) -> None:
        """
        Log command completion.
        
        Args:
            exec_id: Execution ID from log_command
            exit_code: Process exit code
            duration: Execution duration in seconds
            total_stdout_bytes: Total bytes written to stdout
            total_stderr_bytes: Total bytes written to stderr
        """
        entry = {
            "type": "command_complete",
            "exec_id": exec_id,
            "timestamp": datetime.now().isoformat(),
            "exit_code": exit_code,
            "duration_seconds": duration,
            "total_stdout_bytes": total_stdout_bytes,
            "total_stderr_bytes": total_stderr_bytes,
            "success": exit_code == 0
        }
        
        self._write_entry(entry)
        
    def log_error(self, exec_id: str, error: str) -> None:
        """
        Log command error.
        
        Args:
            exec_id: Execution ID from log_command
            error: Error message
        """
        entry = {
            "type": "error",
            "exec_id": exec_id,
            "timestamp": datetime.now().isoformat(),
            "error": error
        }
        
        self._write_entry(entry)
        
    def _write_entry(self, entry: Dict[str, Any]) -> None:
        """Write an entry to the transcript log."""
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write transcript entry: {e}")
            
    def search_transcript(self, search_term: str, exec_id: Optional[str] = None) -> list:
        """
        Search the transcript for specific content.
        
        Args:
            search_term: Text to search for
            exec_id: Optional execution ID to filter by
            
        Returns:
            List of matching entries
        """
        matches = []
        
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    
                    # Filter by exec_id if provided
                    if exec_id and entry.get('exec_id') != exec_id:
                        continue
                        
                    # Search in data field
                    if entry.get('type') == 'output' and search_term in entry.get('data', ''):
                        matches.append(entry)
                    # Search in command field
                    elif entry.get('type') == 'command_start' and search_term in entry.get('command', ''):
                        matches.append(entry)
                        
        except Exception as e:
            logger.error(f"Failed to search transcript: {e}")
            
        return matches
        
    def get_execution_summary(self, exec_id: str) -> Dict[str, Any]:
        """
        Get a summary of a specific execution.
        
        Args:
            exec_id: Execution ID to summarize
            
        Returns:
            Summary dictionary
        """
        summary = {
            "exec_id": exec_id,
            "command": None,
            "exit_code": None,
            "duration": None,
            "output_lines": 0,
            "total_bytes": 0,
            "has_errors": False
        }
        
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    
                    if entry.get('exec_id') != exec_id:
                        continue
                        
                    if entry['type'] == 'command_start':
                        summary['command'] = entry['command']
                    elif entry['type'] == 'output':
                        summary['output_lines'] += 1
                        summary['total_bytes'] += entry['data_length']
                    elif entry['type'] == 'command_complete':
                        summary['exit_code'] = entry['exit_code']
                        summary['duration'] = entry['duration_seconds']
                    elif entry['type'] == 'error':
                        summary['has_errors'] = True
                        
        except Exception as e:
            logger.error(f"Failed to get execution summary: {e}")
            
        return summary


# Global instance for easy access
_transcript_logger = None


def get_transcript_logger() -> TranscriptLogger:
    """Get or create the global transcript logger instance."""
    global _transcript_logger
    if _transcript_logger is None:
        _transcript_logger = TranscriptLogger()
    return _transcript_logger


if __name__ == "__main__":
    """Example usage and verification."""
    
    # Create logger
    logger_instance = TranscriptLogger()
    
    # Simulate command execution
    exec_id = logger_instance.log_command(
        command='claude -p "What is 2+2?" --output-format stream-json',
        working_dir="/home/user/project"
    )
    
    # Log some output
    logger_instance.log_output(exec_id, "stdout", '{"type": "init", "model": "claude"}', 1, 35)
    logger_instance.log_output(exec_id, "stdout", '{"type": "response", "text": "4"}', 2, 68)
    
    # Log completion
    logger_instance.log_completion(exec_id, 0, 2.5, 68, 0)
    
    # Search transcript
    print("\n=== Searching for '4' in transcript ===")
    results = logger_instance.search_transcript("4")
    for result in results:
        print(f"Found in {result['type']}: {result.get('data', '')[:100]}")
        
    # Get summary
    print(f"\n=== Execution Summary for {exec_id} ===")
    summary = logger_instance.get_execution_summary(exec_id)
    print(json.dumps(summary, indent=2))