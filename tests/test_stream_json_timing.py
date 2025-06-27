#!/usr/bin/env python3
"""Test if stream-json actually streams or outputs all at once"""

import subprocess
import json
import time
import sys

claude_path = "/home/graham/.nvm/versions/node/v22.15.0/bin/claude"
command = [claude_path, "-p", "--output-format", "stream-json", "Write 3 short haikus", "--verbose"]

print("Starting Claude with stream-json...")
start_time = time.time()

process = subprocess.Popen(
    command,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1
)

event_count = 0
first_output_time = None

# Read line by line (each JSON event is on its own line)
for line in iter(process.stdout.readline, ''):
    if not line.strip():
        continue
        
    current_time = time.time() - start_time
    
    if first_output_time is None:
        first_output_time = current_time
        print(f"\nFirst output at: {current_time:.2f}s")
    
    event_count += 1
    
    try:
        event = json.loads(line)
        event_type = event.get('type', 'unknown')
        
        print(f"\n[Event {event_count} at {current_time:.2f}s] Type: {event_type}")
        
        # Extract key information
        if event_type == 'assistant':
            content = event.get('message', {}).get('content', [])
            for item in content:
                if item.get('type') == 'text':
                    text = item.get('text', '')[:100]  # First 100 chars
                    print(f"  Text: {text}...")
                elif item.get('type') == 'tool_use':
                    print(f"  Tool: {item.get('name')}")
                    
        elif event_type == 'result':
            result = event.get('result', '')[:100]
            print(f"  Result: {result}...")
            
    except json.JSONDecodeError:
        print(f"  Invalid JSON: {line[:50]}...")

process.wait()
print(f"\nTotal time: {time.time() - start_time:.2f}s")
print(f"Total events: {event_count}")
print(f"All events received in: {current_time - first_output_time:.2f}s window")