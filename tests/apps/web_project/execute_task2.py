#!/usr/bin/env python3
"""Execute Task 2: Run hello.py and verify output via WebSocket."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cc_executor.core.client import WebSocketClient

async def execute_task2():
    """Execute Task 2 following cc_execute.md pattern."""
    
    print("Task 2: Run and Verify Hello World")
    print("-" * 50)
    
    # Step 1: Build command to run hello.py
    # We need to ask Claude to run it and return the output
    prompt = "Run the command 'python hello.py' and show me the output. What does it print?"
    cmd = f'claude -p "{prompt}" --output-format stream-json --verbose --allowedTools Bash --dangerously-skip-permissions'
    
    print("Executing via WebSocket...")
    
    # Step 2: Execute via WebSocket
    client = WebSocketClient(host="localhost", port=8004)
    result = await client.execute_command(cmd, timeout=30)
    
    if not result['success']:
        print(f"❌ Execution failed: {result.get('error')}")
        return False
    
    # Step 3: Parse response
    output_lines = result.get('output_data', [])
    content = []
    
    for line in output_lines:
        try:
            data = json.loads(line)
            if data.get('type') == 'assistant' and 'content' in data.get('message', {}):
                for item in data['message']['content']:
                    if item.get('type') == 'text':
                        content.append(item['text'])
        except:
            pass
    
    full_output = '\n'.join(content)
    
    print("Output received from Claude:")
    print("-" * 30)
    print(full_output[:500] + "..." if len(full_output) > 500 else full_output)
    print("-" * 30)
    
    # Step 4: Evaluate success criteria
    criteria_met = []
    
    # Check 1: Output contains expected message
    if "Hello from WebSocket execution!" in full_output:
        criteria_met.append("✅ Output contains 'Hello from WebSocket execution!'")
    else:
        criteria_met.append("❌ Expected output not found")
    
    # Check 2: No error messages
    error_indicators = ["error", "Error", "ERROR", "failed", "Failed", "exception", "Exception"]
    has_error = any(indicator in full_output for indicator in error_indicators 
                    if f"No {indicator.lower()}" not in full_output.lower())
    
    if not has_error or "successfully" in full_output.lower():
        criteria_met.append("✅ No error messages detected")
    else:
        criteria_met.append("❌ Error messages detected")
    
    print("\nEvaluation:")
    for check in criteria_met:
        print(f"  {check}")
    
    return all("✅" in check for check in criteria_met)

if __name__ == "__main__":
    success = asyncio.run(execute_task2())
    sys.exit(0 if success else 1)