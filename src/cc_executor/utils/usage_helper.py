#!/usr/bin/env python3
"""
Helper utilities for usage functions to save raw responses and prevent AI hallucination.

This module provides a context manager that captures all output from usage functions
and automatically saves it to tmp/responses/ directories.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from contextlib import contextmanager
from io import StringIO


class OutputCapture:
    """Captures stdout and stores it for saving."""
    
    def __init__(self, filename: str):
        self.filename = Path(filename).stem
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_lines: List[str] = []
        self.results: Dict[str, Any] = {}
        self._stdout = None
        self._buffer = None
        
    def __enter__(self):
        """Start capturing stdout."""
        self._stdout = sys.stdout
        self._buffer = StringIO()
        sys.stdout = self._buffer
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop capturing and save output."""
        sys.stdout = self._stdout
        
        # Get captured output
        captured = self._buffer.getvalue()
        if captured:
            self.output_lines.extend(captured.splitlines())
            
        # Save to files
        self._save_output()
        
        # Print original output
        for line in self.output_lines:
            print(line)
            
        # Show where output was saved
        print(f"\n💾 Raw response saved to: tmp/responses/{self.filename}_{self.timestamp}.json")
        
    def print(self, *args, **kwargs):
        """Capture print statements."""
        output = StringIO()
        print(*args, file=output, **kwargs)
        line = output.getvalue().rstrip('\n')
        self.output_lines.append(line)
        print(*args, **kwargs)  # Also print to actual stdout
        
    def add_result(self, key: str, value: Any):
        """Add a result to be saved."""
        self.results[key] = value
        
    def _save_output(self):
        """Save captured output to files."""
        # Create responses directory
        responses_dir = Path.cwd() / "tmp" / "responses"
        responses_dir.mkdir(parents=True, exist_ok=True)
        
        # Save as JSON
        json_file = responses_dir / f"{self.filename}_{self.timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump({
                'filename': self.filename,
                'timestamp': self.timestamp,
                'output': '\n'.join(self.output_lines),
                'results': self.results,
                'line_count': len(self.output_lines)
            }, f, indent=2)
            
        # Save as text
        text_file = responses_dir / f"{self.filename}_{self.timestamp}.txt"
        with open(text_file, 'w') as f:
            f.write(f"=== Raw Response: {self.filename} ===\n")
            f.write(f"Timestamp: {self.timestamp}\n")
            f.write("="*50 + "\n\n")
            f.write('\n'.join(self.output_lines))


@contextmanager
def capture_usage_output(filename: str):
    """
    Context manager to capture and save usage function output.
    
    Usage:
        with capture_usage_output(__file__) as capture:
            print("=== Component Usage Example ===")
            result = my_function()
            capture.add_result('main_result', result)
            print(f"Result: {result}")
    """
    capture = OutputCapture(filename)
    original_stdout = sys.stdout
    buffer = StringIO()
    
    # Start capturing
    sys.stdout = buffer
    
    try:
        yield capture
        
        # Get captured output
        sys.stdout = original_stdout
        captured = buffer.getvalue()
        if captured:
            capture.output_lines.extend(captured.splitlines())
        
        # Save output
        capture._save_output()
        
        # Print original output
        for line in capture.output_lines:
            print(line)
        
        # Show save location
        print(f"\n💾 Raw response saved to: tmp/responses/{capture.filename}_{capture.timestamp}.json")
        
    finally:
        sys.stdout = original_stdout


def save_usage_output(filename: str, output: str, results: Optional[Dict[str, Any]] = None):
    """
    Simple function to save usage output without context manager.
    
    Args:
        filename: The __file__ of the calling module
        output: The output string to save
        results: Optional dictionary of results
    """
    stem = Path(filename).stem
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create responses directory
    responses_dir = Path.cwd() / "tmp" / "responses"
    responses_dir.mkdir(parents=True, exist_ok=True)
    
    # Save as JSON
    json_file = responses_dir / f"{stem}_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump({
            'filename': stem,
            'timestamp': timestamp,
            'output': output,
            'results': results or {},
            'line_count': len(output.splitlines())
        }, f, indent=2)
        
    # Save as text
    text_file = responses_dir / f"{stem}_{timestamp}.txt"
    with open(text_file, 'w') as f:
        f.write(f"=== Raw Response: {stem} ===\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write("="*50 + "\n\n")
        f.write(output)
        
    return json_file


if __name__ == "__main__":
    # Demonstrate the usage helper
    print("=== Usage Helper Demonstration ===\n")
    
    # Method 1: Context manager with automatic capture
    print("--- Method 1: Context Manager ---")
    with capture_usage_output(__file__) as capture:
        print("This output is automatically captured")
        result = {"demo": "value", "count": 42}
        capture.add_result('demo_result', result)
        print(f"Result: {result}")
        print("✅ Context manager demonstration complete")
    
    print("\n--- Method 2: Manual Save ---")
    output = """Manual save demonstration
Result: {'manual': True}
✅ Manual save complete"""
    
    saved_file = save_usage_output(__file__, output, {"manual": True})
    print(output)
    print(f"\n💾 Raw response saved to: {saved_file.relative_to(Path.cwd())}")
    
    print("\n✅ Usage helper demonstration complete!")