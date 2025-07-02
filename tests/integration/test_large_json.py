#!/usr/bin/env python3
"""Test script to verify large JSON handling with the updated configuration."""

import asyncio
import sys
import json
import tempfile
import os

sys.path.insert(0, 'src')

from cc_executor.core.process_manager import ProcessManager
from cc_executor.core.stream_handler import StreamHandler


async def test_large_json_handling():
    """Test that we can handle large JSON objects without truncation."""
    
    # Create a temporary Python script that generates large JSON
    test_script = '''
import json
import sys

size_mb = int(sys.argv[1]) if len(sys.argv) > 1 else 2
large_text = "x" * (size_mb * 1024 * 1024)
data = {'type': 'test', 'size_mb': size_mb, 'content': large_text}
print(json.dumps(data))
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_script)
        script_path = f.name
    
    try:
        process_manager = ProcessManager()
        stream_handler = StreamHandler()
        
        print("Testing large JSON handling...")
        print("Creating JSON with ~2MB of content")
        
        command = f"python {script_path} 2"
        process = await process_manager.execute_command(command)
        
        output_lines = []
        total_bytes = 0
        
        async def collect_output(stream_type: str, data: str):
            nonlocal total_bytes
            if data.strip():
                output_lines.append(data.strip())
                total_bytes += len(data)
                print(f"Received line from {stream_type}: {len(data):,} bytes")
        
        # Stream with no timeout
        await stream_handler.multiplex_streams(
            process.stdout,
            process.stderr,
            collect_output,
            timeout=None
        )
        
        exit_code = await process.wait()
        
        print(f"\nProcess completed with exit code: {exit_code}")
        print(f"Total output: {len(output_lines)} lines, {total_bytes:,} bytes")
        
        # Verify we got the complete JSON
        if output_lines:
            try:
                parsed = json.loads(output_lines[0])
                content_len = len(parsed.get('content', ''))
                expected_len = 2 * 1024 * 1024
                print(f"Successfully parsed JSON with content length: {content_len:,} bytes")
                
                if content_len == expected_len:
                    print("✅ SUCCESS: Full JSON content received without truncation!")
                else:
                    print(f"❌ FAILURE: Expected {expected_len:,} bytes but got {content_len:,} bytes")
            except json.JSONDecodeError as e:
                print(f"❌ FAILURE: Could not parse JSON: {e}")
                print(f"First 100 chars: {output_lines[0][:100]}...")
                print(f"Last 100 chars: ...{output_lines[0][-100:]}")
    finally:
        os.unlink(script_path)


async def test_extreme_large_json():
    """Test with an even larger JSON object (5MB)."""
    
    print("\n\nTesting EXTREME large JSON handling...")
    
    # Create a temporary Python script
    test_script = '''
import json
import sys

size_mb = int(sys.argv[1]) if len(sys.argv) > 1 else 5
large_text = "y" * (size_mb * 1024 * 1024)
data = {'type': 'extreme_test', 'size_mb': size_mb, 'content': large_text}
print(json.dumps(data))
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_script)
        script_path = f.name
    
    try:
        process_manager = ProcessManager()
        stream_handler = StreamHandler()
        
        print("Creating JSON with ~5MB of content")
        
        command = f"python {script_path} 5"
        process = await process_manager.execute_command(command)
        
        output_lines = []
        total_bytes = 0
        
        async def collect_output(stream_type: str, data: str):
            nonlocal total_bytes
            if data.strip():
                output_lines.append(data.strip())
                total_bytes += len(data)
        
        # Stream with no timeout
        await stream_handler.multiplex_streams(
            process.stdout,
            process.stderr,
            collect_output,
            timeout=None
        )
        
        exit_code = await process.wait()
        
        print(f"\nProcess completed with exit code: {exit_code}")
        print(f"Total output: {len(output_lines)} lines, {total_bytes:,} bytes")
        
        # Verify we got the complete JSON
        if output_lines:
            try:
                parsed = json.loads(output_lines[0])
                content_len = len(parsed.get('content', ''))
                expected_len = 5 * 1024 * 1024
                print(f"Successfully parsed JSON with content length: {content_len:,} bytes")
                
                if content_len == expected_len:
                    print("✅ SUCCESS: Full 5MB JSON content received without truncation!")
                else:
                    print(f"❌ FAILURE: Expected {expected_len:,} bytes but got {content_len:,} bytes")
            except json.JSONDecodeError as e:
                print(f"❌ FAILURE: Could not parse JSON: {e}")
    finally:
        os.unlink(script_path)


async def test_with_claude_command():
    """Test with an actual Claude command that might produce large JSON."""
    
    print("\n\nTesting with Claude command simulation...")
    
    # Create a script that simulates Claude output with large tool use
    test_script = '''
import json

# Simulate Claude writing a large file
large_content = "\\n".join([f"Line {i}: " + "x" * 100 for i in range(20000)])
tool_use = {
    "type": "tool_use",
    "name": "Write",
    "input": {
        "file_path": "/tmp/large_file.txt",
        "content": large_content
    }
}

assistant_msg = {
    "type": "assistant",
    "message": {
        "content": [
            {"type": "text", "text": "I'll create a large file for you."},
            tool_use
        ]
    }
}

print(json.dumps(assistant_msg))
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_script)
        script_path = f.name
    
    try:
        process_manager = ProcessManager()
        stream_handler = StreamHandler()
        
        print("Simulating Claude output with large tool use...")
        
        command = f"python {script_path}"
        process = await process_manager.execute_command(command)
        
        output_lines = []
        total_bytes = 0
        
        async def collect_output(stream_type: str, data: str):
            nonlocal total_bytes
            if data.strip():
                output_lines.append(data.strip())
                total_bytes += len(data)
        
        # Stream with no timeout
        await stream_handler.multiplex_streams(
            process.stdout,
            process.stderr,
            collect_output,
            timeout=None
        )
        
        exit_code = await process.wait()
        
        print(f"\nProcess completed with exit code: {exit_code}")
        print(f"Total output: {len(output_lines)} lines, {total_bytes:,} bytes")
        
        # Verify we got the complete JSON
        if output_lines:
            try:
                parsed = json.loads(output_lines[0])
                
                # Check if we got the tool use content
                content_items = parsed.get('message', {}).get('content', [])
                tool_content = None
                
                for item in content_items:
                    if item.get('type') == 'tool_use' and 'input' in item:
                        tool_content = item['input'].get('content', '')
                        break
                
                if tool_content:
                    lines_in_content = tool_content.count('\n') + 1
                    print(f"Successfully parsed JSON with tool use content: {len(tool_content):,} bytes, {lines_in_content} lines")
                    
                    if lines_in_content == 20000:
                        print("✅ SUCCESS: Full tool use content received without truncation!")
                    else:
                        print(f"❌ FAILURE: Expected 20000 lines but got {lines_in_content} lines")
                else:
                    print("❌ FAILURE: Could not find tool use content in JSON")
                    
            except json.JSONDecodeError as e:
                print(f"❌ FAILURE: Could not parse JSON: {e}")
    finally:
        os.unlink(script_path)


if __name__ == "__main__":
    asyncio.run(test_large_json_handling())
    asyncio.run(test_extreme_large_json())
    asyncio.run(test_with_claude_command())