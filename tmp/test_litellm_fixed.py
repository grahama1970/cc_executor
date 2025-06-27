#!/usr/bin/env python3
"""Test the ask-litellm implementation with proper environment activation"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

# CRITICAL: Must activate the llm_call virtual environment
# This ensures litellm and all dependencies are available
if '/home/graham/workspace/experiments/llm_call/.venv' not in sys.executable:
    venv_python = '/home/graham/workspace/experiments/llm_call/.venv/bin/python'
    if os.path.exists(venv_python):
        # Re-execute this script with the correct Python interpreter
        os.execv(venv_python, [venv_python] + sys.argv)
    else:
        print("ERROR: Virtual environment not found. Please ensure /home/graham/workspace/experiments/llm_call/.venv exists", file=sys.stderr)
        sys.exit(1)

# Load environment variables - REQUIRED for API keys
from dotenv import load_dotenv
env_path = '/home/graham/workspace/experiments/llm_call/.env'
if not os.path.exists(env_path):
    print(f"ERROR: .env file not found at {env_path}", file=sys.stderr)
    print("This file must contain your API keys (OPENAI_API_KEY, PERPLEXITY_API_KEY, etc.)", file=sys.stderr)
    sys.exit(1)

load_dotenv(env_path)
print(f"✓ Loaded environment from {env_path}", file=sys.stderr)

try:
    from litellm import completion
    import litellm
    print("✓ LiteLLM imported successfully", file=sys.stderr)
except ImportError:
    print("ERROR: litellm not installed. Run: pip install litellm", file=sys.stderr)
    sys.exit(1)

# Test with a simple OpenAI call first
model = "gpt-3.5-turbo"
query = "Respond with exactly: 'LiteLLM integration successful!'"
output_path = "/tmp/litellm_test_result.md"

print(f"\nTesting with model: {model}", file=sys.stderr)

# Check API key
if "OPENAI_API_KEY" not in os.environ:
    print("ERROR: OPENAI_API_KEY not found in environment", file=sys.stderr)
    print("Available keys:", list(k for k in os.environ.keys() if "API" in k), file=sys.stderr)
    sys.exit(1)

# Try the completion
try:
    print("Calling OpenAI...", file=sys.stderr)
    
    response = completion(
        model=model,
        messages=[{"role": "user", "content": query}],
        max_tokens=50,
        temperature=0.1
    )
    
    content = response.choices[0].message.content
    
    # Verify we got a real response
    if not content or content.strip() == "":
        print("ERROR: Received empty response", file=sys.stderr)
        sys.exit(1)
    
    print(f"\n✓ Success! Response: {content}")
    
    # Save to file
    with open(output_path, 'w', encoding='utf-8') as f:
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "query": query,
            "success": True
        }
        
        f.write(f"# LiteLLM Response\n\n")
        f.write(f"## Metadata\n")
        f.write(f"```json\n{json.dumps(metadata, indent=2)}\n```\n\n")
        f.write(f"## Response\n\n")
        f.write(content)
    
    print(f"✓ Saved to: {output_path}")
    print(f"\nMARKER_LITELLM_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
except Exception as e:
    print(f"\n✗ Error calling {model}: {e}", file=sys.stderr)
    print(f"Error type: {type(e).__name__}", file=sys.stderr)
    
    # Try to provide helpful debugging
    import traceback
    traceback.print_exc()
    
    sys.exit(1)