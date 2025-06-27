#!/usr/bin/env python3
"""Test different Claude CLI modes for streaming"""

import subprocess
import sys
import time

def test_mode(mode_name, command):
    """Test a specific Claude command mode"""
    print(f"\n{'='*60}")
    print(f"Testing: {mode_name}")
    print(f"Command: {command}")
    print(f"{'='*60}")
    
    start_time = time.time()
    chunk_count = 0
    
    # Run command and stream output
    process = subprocess.Popen(
        command, 
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1  # Line buffered
    )
    
    # Read output character by character
    while True:
        char = process.stdout.read(1)
        if not char:
            break
            
        if chunk_count == 0:
            print(f"\nFirst output at: {time.time() - start_time:.2f}s")
        
        chunk_count += 1
        print(char, end='', flush=True)
    
    # Wait for completion
    process.wait()
    print(f"\n\nTotal time: {time.time() - start_time:.2f}s")
    print(f"Exit code: {process.returncode}")
    print(f"Characters received: {chunk_count}")
    
    # Check for errors
    if process.returncode != 0:
        stderr = process.stderr.read()
        if stderr:
            print(f"Stderr: {stderr}")


# Test different modes
prompt = "Write a haiku about Python"
claude_path = "/home/graham/.nvm/versions/node/v22.15.0/bin/claude"

# Test 1: Regular print mode
test_mode(
    "Regular --print",
    f'echo "{prompt}" | {claude_path} --print'
)

# Test 2: Without --print (interactive mode in pipe)
test_mode(
    "Without --print (piped)",
    f'echo "{prompt}" | {claude_path}'
)

# Test 3: Using heredoc
test_mode(
    "Using heredoc",
    f'{claude_path} <<EOF\n{prompt}\nEOF'
)

# Test 4: Direct prompt
test_mode(
    "Direct prompt argument",
    f'{claude_path} --print "{prompt}"'
)