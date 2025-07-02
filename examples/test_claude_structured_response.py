#!/usr/bin/env python3
"""
Demonstration of Claude structured response enforcement.
Shows how hooks prevent hallucination and ensure task completion.
"""

import asyncio
import json
import websockets
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from cc_executor.hooks.claude_structured_response import (
    StructuredClaudeExecutor, create_response_template, parse_claude_response
)

async def test_structured_claude_execution():
    """Test Claude execution with structured response enforcement."""
    
    print("=== Claude Structured Response Test ===\n")
    
    # Test task that often causes hallucination
    test_task = "Create a Python function called calculate_prime that checks if a number is prime"
    
    # Show the structured template
    print("1. Response Template Claude Must Follow:")
    print("-" * 60)
    print(create_response_template(test_task))
    print("-" * 60)
    
    # Prepare command with structure enforcement
    original_command = f'claude -p --output-format stream-json "{test_task}"'
    structured_command = StructuredClaudeExecutor.prepare_command(original_command)
    
    print("\n2. Enhanced Command with Structure:")
    print("-" * 60)
    print(structured_command[:500] + "...")
    print("-" * 60)
    
    # Test WebSocket execution
    try:
        async with websockets.connect("ws://localhost:3000/ws") as ws:
            print("\n3. Executing via WebSocket...")
            
            # Send execution request
            request = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {
                    "command": structured_command,
                    "timeout": 120
                },
                "id": 1
            }
            
            await ws.send(json.dumps(request))
            
            # Collect response
            full_output = []
            completed = False
            
            while not completed:
                response = await ws.recv()
                data = json.loads(response)
                
                # Handle different response types
                if 'result' in data:
                    print(f"\nExecution started: PID={data['result'].get('pid')}")
                    
                elif 'method' in data:
                    if data['method'] == 'process.output':
                        output = data['params']['data']
                        full_output.append(output)
                        # Print partial output
                        if len(full_output) % 10 == 0:
                            print(".", end="", flush=True)
                            
                    elif data['method'] == 'process.completed':
                        completed = True
                        exit_code = data['params'].get('exit_code', -1)
                        print(f"\n\nExecution completed: exit_code={exit_code}")
                        
                    elif data['method'] == 'error.token_limit_exceeded':
                        print("\n⚠️  Token limit exceeded!")
                        print(f"   Limit: {data['params'].get('limit')}")
                        print("   Suggestion: Request more concise output")
                        completed = True
                        
            # Analyze the response
            claude_output = ''.join(full_output)
            
            print("\n4. Response Validation:")
            print("-" * 60)
            
            # Parse structured response
            parsed = parse_claude_response(claude_output)
            
            if parsed:
                print(f"✓ Response follows structure")
                print(f"  Task: {parsed.task_description}")
                print(f"  Status: {parsed.status.value}")
                print(f"  Files created: {len(parsed.files_created)}")
                print(f"  Commands executed: {len(parsed.commands_executed)}")
                print(f"  Verification: {parsed.verification_performed}")
                
                # Validate
                valid, issues, _ = StructuredClaudeExecutor.validate_response(claude_output)
                
                if valid:
                    print("\n✅ Response passed all validations!")
                else:
                    print("\n❌ Validation issues found:")
                    for issue in issues:
                        print(f"   - {issue}")
                        
                    # Show retry prompt
                    print("\n5. Retry Prompt for Self-Reflection:")
                    print("-" * 60)
                    retry_prompt = StructuredClaudeExecutor.create_retry_prompt(test_task, issues)
                    print(retry_prompt[:500] + "...")
                    
            else:
                print("❌ Response does not follow required structure")
                print("   Claude likely hallucinated or only acknowledged")
                
            # Check hook results via Redis
            print("\n6. Hook Validation Results:")
            print("-" * 60)
            
            import redis
            r = redis.Redis(decode_responses=True)
            
            # Get validation result
            val_result = r.get("hook:claude_validation_result:default")
            if val_result:
                result = json.loads(val_result)
                print(f"  Quality: {result['quality']}")
                print(f"  Hallucination score: {result['hallucination_score']:.2f}")
                print(f"  Evidence found: {len(result.get('evidence', []))}")
                
                if result.get('suggestions'):
                    print("\n  Improvement suggestions:")
                    for sug in result['suggestions']:
                        print(f"    - {sug}")
                        
            # Get response quality stats
            stats = r.hgetall("claude:response_quality")
            if stats:
                print("\n7. Overall Response Quality Statistics:")
                print("-" * 60)
                total = sum(int(v) for v in stats.values())
                for quality, count in sorted(stats.items()):
                    pct = (int(count) / total * 100) if total > 0 else 0
                    print(f"  {quality}: {count} ({pct:.1f}%)")
                    
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        print("\nMake sure WebSocket server is running:")
        print("  cd /home/graham/workspace/experiments/cc_executor")
        print("  source .venv/bin/activate")
        print("  uvicorn src.cc_executor.servers.mcp_websocket_server:app --port 3000")


async def test_hallucination_detection():
    """Test detection of common hallucination patterns."""
    print("\n\n=== Hallucination Detection Test ===\n")
    
    # Simulate different response types
    test_responses = {
        "hallucinated": """I've successfully created the calculate_prime function 
that efficiently checks if a number is prime. The function has been 
implemented with optimal performance and includes comprehensive error handling.""",
        
        "acknowledged_only": """Sure, I'll help you create a Python function called 
calculate_prime that checks if a number is prime. Let me do that for you.""",
        
        "complete_valid": """# Task Execution Report

## Task: Create a Python function called calculate_prime
## Status: completed

### Steps Completed:
1. Created calculate_prime function
   Command: None
   Output: None
   File: /tmp/prime_checker.py
   Success: ✓

### Files Created:
- /tmp/prime_checker.py

### Files Modified:
- None

### Commands Executed:
- python /tmp/prime_checker.py

### Errors:
- None

### Verification:
Performed: Yes
Output: calculate_prime(17) = True, calculate_prime(18) = False

### Next Steps:
- None""",
        
        "partial": """I started working on the calculate_prime function but 
encountered an issue with the algorithm implementation. Here's what I have so far:

```python
def calculate_prime(n):
    # TODO: implement prime checking logic
    pass
```

I need to complete the implementation."""
    }
    
    # Test each response type
    for response_type, response in test_responses.items():
        print(f"\nTesting: {response_type}")
        print("-" * 40)
        
        # Set up environment for hook
        os.environ['CLAUDE_OUTPUT'] = response
        os.environ['CLAUDE_EXIT_CODE'] = '0'
        os.environ['CLAUDE_COMMAND'] = 'claude -p "Create calculate_prime function"'
        
        # Run validation hook
        from cc_executor.hooks.claude_response_validator import ClaudeResponseValidator
        
        validator = ClaudeResponseValidator(response, os.environ['CLAUDE_COMMAND'])
        result = validator.validate()
        
        print(f"Quality: {result.quality.value}")
        print(f"Hallucination score: {result.hallucination_score:.2f}")
        print(f"Evidence: {len(result.evidence)} items")
        print(f"Needs retry: {result.needs_retry}")
        
        if result.suggestions:
            print("Suggestions:")
            for sug in result.suggestions[:2]:
                print(f"  - {sug}")


async def main():
    """Run all tests."""
    # Test structured execution
    await test_structured_claude_execution()
    
    # Test hallucination detection
    await test_hallucination_detection()
    
    print("\n\n✅ All tests completed!")
    print("\nKey Benefits Demonstrated:")
    print("1. Structured responses prevent 'acknowledgment-only' replies")
    print("2. Validation catches hallucinated claims without evidence")
    print("3. Retry prompts force self-reflection and task completion")
    print("4. Hooks track quality metrics for continuous improvement")


if __name__ == "__main__":
    asyncio.run(main())