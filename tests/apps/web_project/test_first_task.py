#!/usr/bin/env python3
"""Test just the first task."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cc_executor.core.client import WebSocketClient

async def main():
    client = WebSocketClient()
    
    # The prompt that tells Claude to read cc_execute.md and use it
    prompt = """Read the file /home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/cc_execute.md and follow its execution pattern to complete this task:

Task: Create a Python script that sets up a web project directory structure
Folders needed: templates, static, src, tests
Success criteria:
1. Must use os.makedirs or Path.mkdir
2. Creates all four directories
3. Handles existing directories gracefully
4. Includes executable main block

Use the cc_execute workflow from that file including prompt evaluation, timeout determination, execution, and success evaluation."""
    
    cmd = f'claude -p "{prompt}" --output-format stream-json --verbose --allowedTools all'
    
    print("Sending task to Claude via WebSocket...")
    print("Claude will read cc_execute.md and follow its pattern")
    print("-" * 60)
    
    result = await client.execute_command(cmd, timeout=300)
    
    if result['success']:
        print("✅ Task completed successfully!")
        print("\nOutput preview:")
        output = '\n'.join(result.get('output_data', []))
        
        # Try to extract just the code part
        if '```python' in output:
            start = output.find('```python')
            end = output.find('```', start + 10)
            if end > start:
                code = output[start:end+3]
                print(code)
        else:
            print(output[:1000] + "..." if len(output) > 1000 else output)
    else:
        print(f"❌ Failed: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(main())