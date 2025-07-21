#!/usr/bin/env python3
"""
Test JSON mode for mcp_llm_instance server.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the module
import mcp_llm_instance


async def test_json_direct():
    """Test JSON mode by calling internal functions directly."""
    print("Testing JSON mode with direct function calls...")
    
    # Test Claude with JSON mode
    print("\n1. Testing Claude with JSON mode (default schema):")
    try:
        config = mcp_llm_instance.get_llm_config("claude")
        
        # Prepare prompt with JSON instructions
        prompt = "What is the capital of France?"
        json_schema = json.dumps({
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The original question or prompt"},
                "answer": {"type": "string", "description": "The response to the question"}
            },
            "required": ["question", "answer"]
        })
        json_instruction = f"\n\nPlease respond with valid JSON that follows this schema:\n{json_schema}\n\nIMPORTANT: Return ONLY the JSON object, no markdown formatting or explanation."
        full_prompt = prompt + json_instruction
        
        # Build command
        command = await mcp_llm_instance.build_command(config, full_prompt, json_mode=True, stream=False)
        
        # Execute
        result = await mcp_llm_instance.execute_llm_with_retry(
            config=config,
            command=command,
            env=os.environ.copy(),
            timeout=60
        )
        
        print(f"   Success: {result['success']}")
        print(f"   Raw output: {result['output'][:200]}...")
        
        # Try to parse JSON
        try:
            output = result["output"].strip()
            parsed = None
            
            # Try direct parse
            try:
                parsed = json.loads(output)
            except:
                # Try to find JSON in the output
                import re
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', output, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
            
            if parsed:
                print(f"   Parsed JSON: {json.dumps(parsed, indent=2)}")
                # For Claude's streaming format, extract the actual result
                if isinstance(parsed, dict) and "result" in parsed:
                    try:
                        actual_result = json.loads(parsed["result"])
                        print(f"   Actual response: {json.dumps(actual_result, indent=2)}")
                    except:
                        pass
            else:
                print("   Could not parse JSON from output")
                
        except Exception as e:
            print(f"   JSON parsing error: {e}")
            
    except Exception as e:
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()


async def test_json_with_schema():
    """Test with custom schema."""
    print("\n2. Testing Claude with custom schema:")
    try:
        config = mcp_llm_instance.get_llm_config("claude")
        
        custom_schema = json.dumps({
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "country": {"type": "string"},
                "population": {"type": "number"},
                "facts": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["city", "country"]
        })
        
        prompt = "Tell me about Paris"
        json_instruction = f"\n\nPlease respond with valid JSON that follows this schema:\n{custom_schema}\n\nIMPORTANT: Return ONLY the JSON object, no markdown formatting or explanation."
        full_prompt = prompt + json_instruction
        
        command = await mcp_llm_instance.build_command(config, full_prompt, json_mode=True, stream=False)
        result = await mcp_llm_instance.execute_llm_with_retry(
            config=config,
            command=command,
            env=os.environ.copy(),
            timeout=60
        )
        
        print(f"   Success: {result['success']}")
        
        # Parse output
        output = result["output"].strip()
        try:
            # Try to extract JSON
            import re
            # Claude returns a streaming JSON wrapper, extract the result
            wrapper = None
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', output, re.DOTALL)
            if json_match:
                try:
                    wrapper = json.loads(json_match.group())
                except:
                    pass
            
            if wrapper and isinstance(wrapper, dict) and "result" in wrapper:
                # Extract the actual JSON from the result field
                try:
                    parsed = json.loads(wrapper["result"])
                    print(f"   Parsed JSON: {json.dumps(parsed, indent=2)}")
                except:
                    print(f"   Could not parse result field: {wrapper.get('result', '')[:200]}...")
            else:
                print("   No JSON found in output")
                print(f"   Raw output: {output[:200]}...")
        except Exception as e:
            print(f"   JSON parsing error: {e}")
            
    except Exception as e:
        print(f"   Error: {e}")


async def test_gemini_json():
    """Test Gemini with JSON mode."""
    print("\n3. Testing Gemini with JSON mode:")
    try:
        config = mcp_llm_instance.get_llm_config("gemini")
        
        # Simple test prompt
        prompt = "What is 2+2?"
        json_schema = json.dumps({
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "answer": {"type": "string"}
            },
            "required": ["question", "answer"]
        })
        json_instruction = f"\n\nPlease respond with valid JSON that follows this schema:\n{json_schema}\n\nIMPORTANT: Return ONLY the JSON object, no markdown formatting or explanation."
        full_prompt = prompt + json_instruction
        
        # Build command
        command = await mcp_llm_instance.build_command(config, full_prompt, json_mode=False, stream=False)
        
        # Execute
        result = await mcp_llm_instance.execute_llm_with_retry(
            config=config,
            command=command,
            env=os.environ.copy(),
            timeout=60
        )
        
        print(f"   Success: {result['success']}")
        if result['success']:
            output = result["output"].strip()
            print(f"   Raw output: {output[:200]}...")
            
            # Try to parse JSON
            import re
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', output, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                    print(f"   Parsed JSON: {json.dumps(parsed, indent=2)}")
                except Exception as e:
                    print(f"   JSON parsing error: {e}")
        else:
            print(f"   Error: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all JSON mode tests."""
    print("MCP LLM Instance JSON Mode Tests")
    print("=" * 50)
    
    await test_json_direct()
    await test_json_with_schema()
    await test_gemini_json()
    
    print("\n✅ All JSON tests completed!")


if __name__ == "__main__":
    asyncio.run(main())