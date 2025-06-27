#!/usr/bin/env python3
"""
Test transcript logging functionality to ensure full outputs are captured.

This demonstrates that even when Claude's UI transcript truncates large outputs,
we have a complete record in our transcript logs.
"""

import asyncio
import os
import json
from datetime import datetime
from src.cc_executor.utils.process_executor import execute_with_transcript_logging
from src.cc_executor.utils.transcript_logger import get_transcript_logger


async def test_large_output_capture():
    """Test that large outputs are fully captured in transcript logs."""
    
    print("=== Testing Transcript Logging for Large Outputs ===\n")
    
    # Callback to track output
    output_lines = []
    total_bytes = 0
    
    async def capture_callback(stream_type: str, data: str):
        """Capture output for verification."""
        nonlocal total_bytes
        output_lines.append((stream_type, data))
        total_bytes += len(data.encode('utf-8'))
        
        # Only print summary for large outputs
        if len(output_lines) % 100 == 0:
            print(f"Received {len(output_lines)} lines, {total_bytes:,} bytes so far...")
    
    # Test 1: Generate a large output that would be truncated in Claude
    print("--- Test 1: 5000 Word Story Generation ---")
    
    command = '''claude -p "Write a detailed 5000 word story titled 'The Ghost in the Repository'. Include word count at the end. Mark sections with === for easy verification." --output-format stream-json --verbose'''
    
    print(f"Command: {command[:100]}...")
    print("This will take 5-10 minutes...\n")
    
    start_time = datetime.now()
    
    try:
        exit_code, exec_id = await execute_with_transcript_logging(
            command=command,
            callback=capture_callback,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            timeout=600  # 10 minute timeout
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        print(f"\n✅ Command completed!")
        print(f"Exit code: {exit_code}")
        print(f"Execution ID: {exec_id}")
        print(f"Duration: {duration:.1f}s")
        print(f"Total output: {len(output_lines)} lines, {total_bytes:,} bytes")
        
        # Get transcript logger
        transcript_logger = get_transcript_logger()
        
        # Get execution summary
        summary = transcript_logger.get_execution_summary(exec_id)
        print(f"\nExecution Summary from Transcript:")
        print(json.dumps(summary, indent=2))
        
        # Search for story markers in transcript
        print("\n--- Verifying Story Content in Transcript ---")
        
        markers = [
            "The Ghost in the Repository",
            "=== Chapter",
            "word count:",
            "5000"
        ]
        
        for marker in markers:
            results = transcript_logger.search_transcript(marker, exec_id)
            print(f"'{marker}': Found {len(results)} occurrences")
            if results and len(results[0]['data']) > 100:
                print(f"  Sample: {results[0]['data'][:100]}...")
        
        # Save the transcript log location
        print(f"\n📁 Full transcript saved to: {transcript_logger.log_file}")
        print("This file contains the COMPLETE output, even if Claude UI shows [truncated]")
        
        # Test 2: Verify we can retrieve the full content
        print("\n--- Test 2: Retrieving Full Content from Transcript ---")
        
        full_content = []
        with open(transcript_logger.log_file, 'r') as f:
            for line in f:
                entry = json.loads(line)
                if entry.get('exec_id') == exec_id and entry.get('type') == 'output':
                    full_content.append(entry['data'])
        
        reconstructed_text = ''.join(full_content)
        print(f"Reconstructed {len(reconstructed_text):,} characters from transcript")
        
        # Verify it contains the story
        if "The Ghost in the Repository" in reconstructed_text:
            print("✅ Story title found in reconstructed content")
        if "word count:" in reconstructed_text.lower():
            print("✅ Word count found in reconstructed content")
            
        # Save reconstructed content for manual verification
        output_file = f"test_outputs/transcript_reconstructed_{exec_id}.txt"
        os.makedirs("test_outputs", exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(reconstructed_text)
        print(f"\n📄 Reconstructed content saved to: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_transcript_search():
    """Test searching capabilities of transcript logger."""
    
    print("\n=== Testing Transcript Search Capabilities ===\n")
    
    # Generate some test output with markers
    async def dummy_callback(stream_type: str, data: str):
        pass
    
    # Run a command that generates predictable output
    command = '''python -c "
for i in range(10):
    print(f'MARKER_{i}: Test line with unique content {i * 100}')
    print(f'ERROR_{i}: Simulated error message {i}', file=__import__('sys').stderr)
"'''
    
    exit_code, exec_id = await execute_with_transcript_logging(
        command=command,
        callback=dummy_callback
    )
    
    transcript_logger = get_transcript_logger()
    
    # Search for specific markers
    print("--- Searching for Markers ---")
    
    # Search stdout markers
    stdout_results = transcript_logger.search_transcript("MARKER_5", exec_id)
    print(f"Found {len(stdout_results)} matches for 'MARKER_5'")
    if stdout_results:
        print(f"Content: {stdout_results[0]['data'].strip()}")
    
    # Search stderr markers
    stderr_results = transcript_logger.search_transcript("ERROR_7", exec_id)
    print(f"Found {len(stderr_results)} matches for 'ERROR_7'")
    if stderr_results:
        print(f"Stream: {stderr_results[0]['stream']}")
        print(f"Content: {stderr_results[0]['data'].strip()}")


async def main():
    """Run all transcript logging tests."""
    
    # Create unique marker for this test run
    test_marker = f"TRANSCRIPT_TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Test marker: {test_marker}\n")
    
    # Run tests
    await test_large_output_capture()
    await test_transcript_search()
    
    print("\n=== Transcript Logging Tests Complete ===")
    print("\nKey Benefits:")
    print("1. Full outputs are preserved even when Claude UI truncates")
    print("2. Searchable transcript for debugging and verification")
    print("3. Execution summaries with timing and byte counts")
    print("4. Checksums for data integrity verification")


if __name__ == "__main__":
    asyncio.run(main())