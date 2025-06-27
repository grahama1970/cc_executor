#!/usr/bin/env python3
"""Test Perplexity API through LiteLLM"""

import sys
import os
import json
from datetime import datetime

# CRITICAL: Must activate the llm_call virtual environment
if '/home/graham/workspace/experiments/llm_call/.venv' not in sys.executable:
    venv_python = '/home/graham/workspace/experiments/llm_call/.venv/bin/python'
    if os.path.exists(venv_python):
        os.execv(venv_python, [venv_python] + sys.argv)
    else:
        print("ERROR: Virtual environment not found", file=sys.stderr)
        sys.exit(1)

# Load environment variables
from dotenv import load_dotenv
load_dotenv('/home/graham/workspace/experiments/llm_call/.env')

from litellm import completion

# Test Perplexity
model = "perplexity/sonar"
query = "What are the latest features in Python 3.12? Provide specific examples with citations."
output_path = "/tmp/litellm_perplexity_test.md"

print(f"Testing {model}...", file=sys.stderr)

if "PERPLEXITY_API_KEY" not in os.environ:
    print("ERROR: PERPLEXITY_API_KEY not set", file=sys.stderr)
    sys.exit(1)

try:
    response = completion(
        model=model,
        messages=[{"role": "user", "content": query}],
        temperature=0.5,
        max_tokens=500
    )
    
    content = response.choices[0].message.content
    
    if not content:
        print("ERROR: Empty response", file=sys.stderr)
        sys.exit(1)
    
    # Save response
    with open(output_path, 'w', encoding='utf-8') as f:
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "query": query,
            "provider": "Perplexity"
        }
        
        f.write(f"# LiteLLM Response\n\n")
        f.write(f"## Metadata\n")
        f.write(f"```json\n{json.dumps(metadata, indent=2)}\n```\n\n")
        f.write(f"## Response\n\n")
        f.write(content)
    
    print(f"✓ Success! Response saved to: {output_path}")
    
    # Show if we got citations
    if "[" in content and "]" in content:
        print("✓ Response includes citations")
    
    print(f"\nMARKER_PERPLEXITY_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
except Exception as e:
    print(f"✗ Error: {e}", file=sys.stderr)
    sys.exit(1)