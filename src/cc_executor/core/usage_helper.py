"""
Helper utilities for saving usage function outputs as prettified JSON.

This module provides a standardized way to save responses from if __name__ == "__main__"
blocks to prevent AI hallucination about execution results.
"""

import json
import io
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional


class OutputCapture:
    """Context manager for capturing print output and saving to JSON."""
    
    def __init__(self, module_file: str):
        """
        Initialize output capture.
        
        Args:
            module_file: __file__ from the calling module
        """
        self.module_path = Path(module_file)
        self.filename = self.module_path.stem
        self.module_name = f"cc_executor.core.{self.filename}"
        
        # Create responses directory
        self.responses_dir = self.module_path.parent / "tmp" / "responses"
        self.responses_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup capture
        self.output_buffer = io.StringIO()
        self._original_print = None
        self.start_time = None
        
    def print_and_capture(self, *args, **kwargs):
        """Print to both stdout and buffer."""
        # Print to stdout as normal
        self._original_print(*args, **kwargs)
        # Also print to buffer
        self._original_print(*args, **kwargs, file=self.output_buffer)
    
    def __enter__(self):
        """Start capturing output."""
        import builtins
        self._original_print = builtins.print
        builtins.print = self.print_and_capture
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop capturing and save to JSON."""
        import builtins
        
        # Restore original print
        builtins.print = self._original_print
        
        # Get captured output
        output_content = self.output_buffer.getvalue()
        
        # Generate timestamp
        timestamp = self.start_time.strftime('%Y%m%d_%H%M%S')
        
        # Save as prettified JSON
        response_file = self.responses_dir / f"{self.filename}_{timestamp}.json"
        
        response_data = {
            'filename': self.filename,
            'module': self.module_name,
            'timestamp': timestamp,
            'execution_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'duration_seconds': (datetime.now() - self.start_time).total_seconds(),
            'output': output_content,
            'line_count': len(output_content.strip().split('\n')) if output_content else 0,
            'success': '✅' in output_content,
            'has_error': 'error' in output_content.lower() or 'exception' in output_content.lower(),
            'exit_status': 'completed' if exc_type is None else f'failed: {exc_type.__name__}'
        }
        
        with open(response_file, 'w') as f:
            json.dump(response_data, f, indent=4, ensure_ascii=False)
        
        print(f"\n💾 Response saved: {response_file.relative_to(Path.cwd())}")
    
    def get_output(self) -> str:
        """Get the captured output so far."""
        return self.output_buffer.getvalue()


def save_response(output: str, module_file: str, extra_data: Optional[Dict[str, Any]] = None) -> Path:
    """
    Save output as prettified JSON response.
    
    Args:
        output: The output text to save
        module_file: __file__ from the calling module
        extra_data: Optional extra data to include in the JSON
        
    Returns:
        Path to the saved JSON file
    """
    module_path = Path(module_file)
    filename = module_path.stem
    module_name = f"cc_executor.core.{filename}"
    
    # Create responses directory
    responses_dir = module_path.parent / "tmp" / "responses"
    responses_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Build response data
    response_data = {
        'filename': filename,
        'module': module_name,
        'timestamp': timestamp,
        'execution_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'output': output,
        'line_count': len(output.strip().split('\n')) if output else 0,
        'success': '✅' in output,
        'has_error': 'error' in output.lower() or 'exception' in output.lower()
    }
    
    # Add extra data if provided
    if extra_data:
        response_data.update(extra_data)
    
    # Save as prettified JSON
    response_file = responses_dir / f"{filename}_{timestamp}.json"
    with open(response_file, 'w') as f:
        json.dump(response_data, f, indent=4, ensure_ascii=False)
    
    return response_file


if __name__ == "__main__":
    """Demonstrate OutputCapture usage and verify it works correctly."""
    
    print("=== Testing OutputCapture Helper ===")
    print()
    print("Test 1: Basic capture test")
    
    # Test the context manager
    with OutputCapture(__file__) as capture:
        print("This is a test message")
        print("Multiple lines are captured")
        print("Including special characters: ✅ ❌ 🚀")
        
        # Verify we can get output during capture
        current_output = capture.get_output()
        assert "This is a test message" in current_output
        print(f"✓ Captured {len(current_output)} characters so far")
        
        # Test with different output types
        print("\nTest 2: Different output types")
        print(f"Numbers: {42}")
        print(f"Lists: {[1, 2, 3]}")
        print(f"Dicts: {{'key': 'value'}}")
        
        print("\n✅ OutputCapture is working correctly!")
    
    # At this point, the file should have been saved
    import time
    time.sleep(0.1)  # Small delay to ensure file write completes
    
    # Verify the file was created
    from pathlib import Path
    responses_dir = Path(__file__).parent / "tmp" / "responses"
    files = list(responses_dir.glob("usage_helper_*.json"))
    
    if files:
        latest_file = max(files, key=lambda f: f.stat().st_mtime)
        print(f"\n✅ Verified file was saved: {latest_file.name}")
    else:
        print("\n❌ ERROR: No response file was created!")