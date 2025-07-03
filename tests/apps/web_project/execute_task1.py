#!/usr/bin/env python3
"""Execute Task 1: Create hello.py script via WebSocket."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cc_executor.core.client import WebSocketClient

async def execute_task1():
    """Execute Task 1 following cc_execute.md pattern."""
    
    print("Task 1: Create Hello World Script")
    print("-" * 50)
    
    # Step 1: Build Claude command
    prompt = "What is a Python script named hello.py that prints 'Hello from WebSocket execution!'? Show the complete code."
    cmd = f'claude -p "{prompt}" --output-format stream-json --verbose --allowedTools none --dangerously-skip-permissions'
    
    print("Executing via WebSocket...")
    
    # Step 2: Execute via WebSocket
    client = WebSocketClient(host="localhost", port=8004)
    result = await client.execute_command(cmd, timeout=60)
    
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
    
    # Step 4: Extract the Python code
    if '```python' in full_output:
        start = full_output.find('```python') + 9
        end = full_output.find('```', start)
        if end > start:
            code = full_output[start:end].strip()
            
            # Write hello.py
            with open('hello.py', 'w') as f:
                f.write(code)
            
            print("✅ Created hello.py")
            
            # Step 5: Evaluate success criteria
            criteria_met = []
            
            # Check 1: File exists
            if Path('hello.py').exists():
                criteria_met.append("✅ File hello.py exists")
            else:
                criteria_met.append("❌ File hello.py does not exist")
            
            # Check 2: Contains correct print statement
            with open('hello.py', 'r') as f:
                content = f.read()
                if "Hello from WebSocket execution!" in content:
                    criteria_met.append("✅ Contains correct print statement")
                else:
                    criteria_met.append("❌ Missing correct print statement")
            
            print("\nEvaluation:")
            for check in criteria_met:
                print(f"  {check}")
            
            return all("✅" in check for check in criteria_met)
    
    print("❌ Could not extract Python code from response")
    return False

if __name__ == "__main__":
    success = asyncio.run(execute_task1())
    sys.exit(0 if success else 1)